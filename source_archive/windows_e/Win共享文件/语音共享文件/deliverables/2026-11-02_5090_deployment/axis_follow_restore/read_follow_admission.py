"""Snapshot original follow admission and existing rated-range branch; no execution."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
transport=HERE.parents[1]/'2026-10-18_board_dialogue/board_ssh.py'
assert hashlib.sha256(transport.read_bytes()).hexdigest()=='6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
spec=importlib.util.spec_from_file_location('axis_follow_admission_readonly',transport)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
SCRIPT=r'''
import hashlib,json
from pathlib import Path
app=Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/runtime/aura')
control=Path('/home/root/aura-pan-wide-20261028/control-10282601')
original=Path('/home/root/aura-face-follow-test-20261101-bebd3e7d-r2/original-entry')
paths=[control/'continuous_session.py',control/'hardware_slew_session.py',control/'face_zone.py',
 app/'board/motion/rated_range_release.py',app/'board/motion/current_reference_release.py',
 original/'manual-release/authorization.json',original/'manual-release/platform-proof.json']
out={'read_only':True,'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'sources':{}}
for p in paths:
 assert p.is_file() and not p.is_symlink()
 raw=p.read_bytes();assert len(raw)<100000
 out['sources'][str(p)]={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'text':raw.decode()}
print(json.dumps(out,ensure_ascii=False))
'''
start=datetime.datetime.now(datetime.timezone.utc).isoformat()
result=json.loads(module.ssh('python3 -B -',SCRIPT,timeout=30))
target=HERE/'original_follow_admission_readonly_01.json'
with target.open('x',encoding='utf-8') as stream:
 json.dump({'host_start_utc':start,'host_end_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
  'script_sha256':hashlib.sha256(SCRIPT.encode()).hexdigest(),'board_result':result},stream,ensure_ascii=False,indent=2)
 stream.write('\n')
print(json.dumps({'output':str(target),'boot_id':result['boot_id'],
 'sources':{p:{k:v for k,v in value.items() if k!='text'} for p,value in result['sources'].items()}},ensure_ascii=False))
