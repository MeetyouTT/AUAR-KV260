from device_host import *
if __name__=='__main__':
 stage=load(HERE/'candidate_physics/STAGE_INTENT.json')['stage'];files={str(p.relative_to(HERE)).replace('\\','/'):base64.b64encode(p.read_bytes()).decode() for p in (HERE/'release').rglob('*') if p.is_file() and p.suffix!='.zip'}
 script='STAGE='+repr(stage)+'\nFILES='+repr(files)+'\n'+'''from pathlib import Path
import base64,json,hashlib
s=Path(STAGE)
for name,data in FILES.items():
 p=s/name;assert p.resolve().is_relative_to(s.resolve());p.parent.mkdir(parents=True,exist_ok=True);raw=base64.b64decode(data)
 if p.exists():assert p.read_bytes()==raw
 else:
  with p.open('xb') as f:f.write(raw)
print(json.dumps({'status':'REVIEWED_RELEASE_FILES_STAGED','files':len(FILES)}))
'''
 print(board(script).decode())
