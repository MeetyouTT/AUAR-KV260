"""Enable ordinary voice listening once through the original UI command."""
import hashlib
import http.client
import json
import os
from pathlib import Path
import time

E=json.loads('{"boot_id": "a6d4a069-e9b0-4065-8df7-dc23556b168e", "owners": [{"birth_ticks": "6513277", "command_sha256": "48a28efa32b2050901e73e85a80a30a90dcfbce0b7249bde5d6d90902740631d", "pid": 937589}, {"birth_ticks": "6516477", "command_sha256": "88e117d64f58aef6801cd827e74766426360a769074e418a9da34a58d71674d4", "pid": 937618}, {"birth_ticks": "2850120", "command_sha256": "acf3ee123d7674fdea6e90e79252909ca396249c870269169910879d940c27dd", "pid": 362659}], "startup_path": "/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json", "startup_sha256": "7d60ab0f83fc2484f59e065b720cec73cdb2dbe051cb34e366c08ebcbc8e785e", "transaction": "/home/root/aura-5090-recovery-20261102-a6d4a069/voice-per-utterance-20261103T050551Z-stop"}')
def verify():
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==E['boot_id']
    assert hashlib.sha256(Path(E['startup_path']).read_bytes()).hexdigest()==E['startup_sha256']
    for o in E['owners']:
        p=Path('/proc')/str(o['pid']);assert p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==o['birth_ticks'];assert hashlib.sha256(p.joinpath('cmdline').read_bytes()).hexdigest()==o['command_sha256']
def request(body=None):
    c=http.client.HTTPConnection('127.0.0.1',8783,timeout=3)
    try:
        headers={'Host':'127.0.0.1:8783','Origin':'http://127.0.0.1:8783'}
        if body is None:c.request('GET','/api/state',headers=headers)
        else:headers['Content-Type']='application/json';c.request('POST','/api/command',body=json.dumps(body).encode(),headers=headers)
        r=c.getresponse();data=r.read(2097153);assert r.status==200 and len(data)<=2097152;return json.loads(data)
    finally:c.close()
verify();v=request();h=v['handsfree_dialogue'];assert not v.get('playing') and not v.get('pending_job') and not v['manual_pan']['automatic_following'];assert v['board_business']['speaker']['conversation_address']['mode']=='PER_UTTERANCE'
sent=False
if not h['enabled']:
    p=Path(E['transaction'])/'enable-listening-intent.json';fd=os.open(str(p),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as f:f.write((json.dumps({'single_original_toggle':True,'target':True,'mono_ms':int(time.monotonic()*1000)})+'\n').encode());f.flush();os.fsync(f.fileno())
    request({'type':'conversation_toggle'});sent=True
for _ in range(40):
    v=request();h=v['handsfree_dialogue']
    if h['enabled'] and h['microphone_open']:break
    time.sleep(.2)
verify();s=v['board_business']['speaker'];assert h['enabled'] and h['microphone_open'] and v['ui_page']=='main' and s['conversation_address']['mode']=='PER_UTTERANCE'
print(json.dumps({'schema':'aura-per-utterance-voice-listening-ready-1','single_toggle_sent':sent,'listening_enabled':h['enabled'],'microphone_open':h['microphone_open'],'handsfree_state':h['state'],'speaker_mode':s['conversation_address']['mode'],'threshold':s['identity_match_threshold'],'runtime_fault_count':v['runtime_faults']['count'],'axis_following':v['manual_pan']['automatic_following'],'no_axis_or_model_commands':True}))
