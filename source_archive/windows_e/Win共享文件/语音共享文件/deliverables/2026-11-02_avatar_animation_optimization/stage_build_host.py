from device_host import *
def main():
 expected=load(HERE/'baseline/FRESH_DEVICE_READ.json');assert not expected['bad_pins']
 source=HERE/'candidate_physics/native/yuki_host.cpp'
 stage='/home/root/aura-avatar-animation-20261102/'+sha(source)[:16]
 files={}
 for folder in ('baseline/actual_native','candidate_physics/native','tests'):
  for p in (HERE/folder).iterdir():
   if p.is_file():
    relative=str(p.relative_to(HERE)).replace('\\','/').replace('baseline/actual_native','baseline/native')
    files[relative]=p.read_bytes()
 files['expected.json']=(json.dumps(expected)+'\n').encode()
 old=PROJECT/'deliverables/2026-10-30_board_owner/integration/dialogue_repair/animation_thinking_collaboration/NATIVE_BASELINE.json'
 files['original_native_pins.json']=old.read_bytes()
 files['build_candidate_on_board.py']=(HERE/'build_candidate_on_board.py').read_bytes()
 payload={k:base64.b64encode(v).decode() for k,v in files.items()}
 script='''import json,base64,hashlib,subprocess
from pathlib import Path
p=Path(STAGE);p.mkdir(parents=True,exist_ok=False)
for name,encoded in FILES.items():
 path=p/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(base64.b64decode(encoded))
r=subprocess.run(['python3','-B',str(p/'build_candidate_on_board.py')],capture_output=True,timeout=560)
if r.returncode: raise RuntimeError((r.stderr+r.stdout).decode(errors='replace')[-7000:])
print(r.stdout.decode())
'''.replace('STAGE',repr(stage)).replace('FILES',repr(payload))
 save(HERE/'candidate_physics/STAGE_INTENT.json',dict(stage=stage,files={k:hashlib.sha256(v).hexdigest() for k,v in files.items()},expected_startup=expected['startup_sha256']))
 result=json.loads(board(script,timeout=590));save(HERE/'validation/BUILD_RECEIPT.json',result)
 print(json.dumps({k:v for k,v in result.items() if k not in ('steps','verified_original_native_inputs')},ensure_ascii=False))
if __name__=='__main__':main()
