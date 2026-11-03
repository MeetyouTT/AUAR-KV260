"""Read current bounded public state and pinned entry sources only."""
import base64
import hashlib
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh

REMOTE=r'''
import base64,hashlib,http.client,json,pathlib,subprocess
root=pathlib.Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
startup=(root/'startup/config.json').read_bytes()
assert hashlib.sha256(startup).hexdigest()==EXPECTED
assert pathlib.Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
pins=json.loads(startup)['component_sha256']
names={'voice_first_recording.py','board_recording.py','barge_in_recording.py','handsfree_recording.py',
 'board_business_gui.py','production_board_business_gui.py','production_listening.py','production_business_ui.py',
 'board_avatar_gtk.py','board_dialogue_jobs.py','handsfree_entry.py','yuki_jobs_candidate.py','board_business.py'}
sources={}
for rel,pin in pins.items():
 if pathlib.Path(rel).name not in names:continue
 path=root/'runtime/aura'/rel;assert path.is_file() and not path.is_symlink() and path.resolve()==path
 raw=path.read_bytes();assert hashlib.sha256(raw).hexdigest()==pin
 sources[rel]=dict(sha256=pin,base64=base64.b64encode(raw).decode())
c=http.client.HTTPConnection('127.0.0.1',8783,timeout=4)
try:
 c.request('GET','/api/state');r=c.getresponse();raw=r.read(1048577);assert r.status==200 and len(raw)<=1048576
 state=json.loads(raw)
finally:c.close()
h=state.get('handsfree_dialogue',{});d=state.get('safe_capture_diagnostics',{})
out=dict(startup_sha256=EXPECTED,boot_id=BOOT,component_pins=len(pins),
 source_manifest_sha256=hashlib.sha256((root/'production_source_manifest.json').read_bytes()).hexdigest(),
 listening={k:h.get(k) for k in ('enabled','state','conversation_entered','entry_mode','speech_detection','microphone_open')},
 capture_error=d.get('error_code'),playing=state.get('playing'),sources=sources)
print(json.dumps(out))
'''

if __name__=='__main__':
    spec=json.loads((HERE.parent/'production_business_acceptance/spec.json').read_text(encoding='utf-8'))
    result=json.loads(ssh('python3 -B -','EXPECTED='+repr(spec['startup_sha256'])+'\nBOOT='+repr(spec['boot_id'])+'\n'+REMOTE,timeout=25))
    sources=result.pop('sources');manifest={}
    for rel,item in sources.items():
        raw=base64.b64decode(item['base64']);assert hashlib.sha256(raw).hexdigest()==item['sha256']
        path=HERE/'before'/rel;path.parent.mkdir(parents=True,exist_ok=True)
        if path.exists():assert path.read_bytes()==raw
        else:path.write_bytes(raw)
        manifest[rel]=dict(sha256=item['sha256'],bytes=len(raw))
    result['sources']=manifest
    (HERE/'baseline.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result))
