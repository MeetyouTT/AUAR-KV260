"""Honor the user's deferred test; leave original UI listening paused."""
import hashlib
import http.client
import json
import os
from pathlib import Path
import subprocess
import time

BOOT='a6d4a069-e9b0-4065-8df7-dc23556b168e'
STARTUP=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json')
SHA='7d60ab0f83fc2484f59e065b720cec73cdb2dbe051cb34e366c08ebcbc8e785e'
OWNERS=[(937589,'6513277','48a28efa32b2050901e73e85a80a30a90dcfbce0b7249bde5d6d90902740631d'),(937618,'6516477','88e117d64f58aef6801cd827e74766426360a769074e418a9da34a58d71674d4'),(362659,'2850120','acf3ee123d7674fdea6e90e79252909ca396249c870269169910879d940c27dd')]
def verify():
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
    assert hashlib.sha256(STARTUP.read_bytes()).hexdigest()==SHA
    for pid,birth,cmd in OWNERS:
        p=Path('/proc')/str(pid);assert p.joinpath('stat').read_text().rsplit(')',1)[1].split()[19]==birth;assert hashlib.sha256(p.joinpath('cmdline').read_bytes()).hexdigest()==cmd
def request(body=None):
    c=http.client.HTTPConnection('127.0.0.1',8783,timeout=3)
    try:
        h={'Host':'127.0.0.1:8783','Origin':'http://127.0.0.1:8783'}
        if body is None:c.request('GET','/api/state',headers=h)
        else:h['Content-Type']='application/json';c.request('POST','/api/command',body=json.dumps(body).encode(),headers=h)
        r=c.getresponse();data=r.read(2097153);assert r.status==200 and len(data)<=2097152;return json.loads(data)
    finally:c.close()
verify();v=request();sent=False
if v['handsfree_dialogue']['enabled']:
    p=Path('/home/root/aura-5090-recovery-20261102-a6d4a069/voice-per-utterance-20261103T050551Z-stop/defer-listening-intent.json')
    fd=os.open(str(p),os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as f:f.write((json.dumps({'user_requested_test_defer':True,'target_enabled':False,'single_original_toggle':True,'mono_ms':int(time.monotonic()*1000)})+'\n').encode());f.flush();os.fsync(f.fileno())
    request({'type':'conversation_toggle'});sent=True
for _ in range(35):
    v=request();h=v['handsfree_dialogue']
    if not h['enabled'] and not h['microphone_open']:break
    time.sleep(.2)
verify();assert not h['enabled'] and not h['microphone_open']
cfg=json.loads(STARTUP.read_bytes());aura=Path(cfg['runtime'])/'aura';pins=cfg['component_sha256']
for name in ('board/runtime/board_speaker_business.py','board/runtime/board_dialogue.py','tools/native_yuki.py','tools/libaura_yuki.so'):
    assert hashlib.sha256((aura/name).read_bytes()).hexdigest()==pins[name]
saved=json.loads(Path('/home/root/.local/share/aura-board-business/listening_preference.json').read_bytes());assert saved=={'version':1,'enabled':False}
speaker=v['board_business']['speaker'];pan=v['manual_pan'];rb=pan.get('readback') or {};assert not pan['automatic_following'];assert v['runtime_faults']['count']==0
u=subprocess.run(['systemctl','show','aura-avatar-ui.service','--property=Restart,KillMode,SendSIGKILL,TimeoutStopUSec'],capture_output=True,text=True,timeout=4);assert u.returncode==0;props=dict(x.split('=',1) for x in u.stdout.splitlines() if '=' in x);assert props=={'Restart':'no','KillMode':'mixed','SendSIGKILL':'yes','TimeoutStopUSec':'25s'}
print(json.dumps({'schema':'aura-voice-test-user-deferred-paused-1','status':'PER_UTTERANCE_DEPLOYED_LIVE_TWO_PERSON_TEST_DEFERRED_BY_USER','startup_sha256':SHA,'pause_toggle_sent':sent,'ui_page':v.get('ui_page'),'avatar_visible':v['avatar_display']['visible'],'pair_ready':v['character_pair']['state']=='READY','runtime_fault_count':0,'listening_enabled':h['enabled'],'microphone_open':h['microphone_open'],'handsfree_state':h['state'],'playing':bool(v.get('playing')),'pending_job':bool(v.get('pending_job')),'saved_listening_enabled':False,'speaker_mode':speaker['conversation_address']['mode'],'speaker_threshold':speaker['identity_match_threshold'],'field_calibrated':speaker['speaker_calibrated'],'automatic_following':False,'axis_readback':{k:rb.get(k) for k in ('flags','lease_left_ms','width_us','active','armed')},'GUI_properties_restored':True,'R4_library_and_adapter_preserved':True,'gui_owner':{'pid':937589,'birth_ticks':'6513277'},'gtk_owner':{'pid':937618,'birth_ticks':'6516477'},'camera_owner':{'pid':362659,'birth_ticks':'2850120'},'motion_or_model_or_library_or_database_mutations':0,'board_mono_ms':int(time.monotonic()*1000)}))
