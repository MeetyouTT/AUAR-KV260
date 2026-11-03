from common import *
if __name__=='__main__':
 e=load(HERE/'validation/FRESH_BEFORE_R3.json');assert not e['bad_pins']
 assert e['component_sha256']['tools/libaura_yuki.so']==load(HERE/'candidate/SOURCE_MANIFEST.json')['baseline_library_sha256']
 stage='/home/root/aura-avatar-animation-20261102/r3-'+sha(HERE/'candidate/native/secondary_motion.hpp')[:16]
 files={}
 for folder in ('baseline/native','candidate/native','tests'):
  for p in (HERE/folder).rglob('*'):
   if p.is_file():files[str(p.relative_to(HERE)).replace('\\','/')]=p.read_bytes()
 for name in ('build.py','DEVICE_HANDOFF_R3.json'):files[name]=(HERE/name).read_bytes()
 files['expected.json']=(json.dumps(e)+'\n').encode()
 original=PROJECT/'deliverables/2026-10-30_board_owner/integration/dialogue_repair/animation_thinking_collaboration/NATIVE_BASELINE.json'
 files['original_native_pins.json']=original.read_bytes()
 files['tests/native_original_policy.cpp']=(BASE/'tests/native_original_policy.cpp').read_bytes()
 audit=(BASE/'tests/native_physics_audit.cpp').read_text()
 assert audit.count('high[4]-low[4]>5.')==1 and audit.count('low[4]>=-10.50001&&high[4]<=10.50001')==1
 audit=audit.replace('high[4]-low[4]>5.','high[4]-low[4]>2.').replace('low[4]>=-10.50001&&high[4]<=10.50001','low[4]>=-4.00001&&high[4]<=4.00001')
 files['tests/native_physics_audit.cpp']=audit.encode()
 payload={k:base64.b64encode(v).decode() for k,v in files.items()}
 script='STAGE='+repr(stage)+'\nFILES='+repr(payload)+'\n'+'''from pathlib import Path
import base64,json
p=Path(STAGE);p.mkdir(parents=True,exist_ok=False)
for name,encoded in FILES.items():
 q=p/name;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(base64.b64decode(encoded))
print(json.dumps({'status':'R3_NEW_STAGE_CREATED','files':len(FILES)}))
'''
 save(HERE/'STAGE_INTENT.json',dict(stage=stage,files={k:hashlib.sha256(v).hexdigest() for k,v in files.items()},fresh_startup=e['startup_sha256'],handoff_id=load(HERE/'DEVICE_HANDOFF_R3.json')['handoff_id']))
 print(board(script).decode())
