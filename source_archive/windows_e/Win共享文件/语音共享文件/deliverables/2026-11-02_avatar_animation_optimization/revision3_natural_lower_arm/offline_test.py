from common import *
if __name__=='__main__':
 stage='/home/ghmd/aura-animation-r3-numeric-'+sha(HERE/'candidate/native/secondary_motion.hpp')[:12]
 paths=[HERE/'baseline/native/secondary_motion.hpp',HERE/'candidate/native/secondary_motion.hpp',HERE/'tests/motion_compare.cpp']
 payload={str(p.relative_to(HERE)).replace('\\','/'):base64.b64encode(p.read_bytes()).decode() for p in paths}
 model=Path('E:/AUAR_工程交付_20261102/aura/src/avatar/native_integration/candidate_core/include/nekomote/model/asset.hpp')
 payload['include/nekomote/model/asset.hpp']=base64.b64encode(model.read_bytes()).decode()
 script='STAGE='+repr(stage)+'\nFILES='+repr(payload)+'\n'+'''from pathlib import Path
import base64,subprocess,json
p=Path(STAGE);p.mkdir(parents=True,exist_ok=False)
for name,data in FILES.items():
 q=p/name;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(base64.b64decode(data))
r=subprocess.run(['g++','-std=c++17','-O2','-ffp-contract=off','-I'+str(p/'include'),str(p/'tests/motion_compare.cpp'),'-o',str(p/'test')],capture_output=True,timeout=30)
assert r.returncode==0,r.stderr.decode()
r=subprocess.run([str(p/'test')],capture_output=True,timeout=10);assert r.returncode==0,r.stderr.decode()
print(r.stdout.decode())
'''
 result=json.loads(remote(script,'aura-ubuntu',50));save(HERE/'validation/OFFLINE_MOTION_COMPARE.json',result);print(json.dumps(result))
