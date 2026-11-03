from device_host import *
if __name__=='__main__':
 stage=load(HERE/'candidate_physics/STAGE_INTENT.json')['stage'];files={p.name:base64.b64encode(p.read_bytes()).decode() for p in (HERE/'candidate_physics_v2/native').iterdir() if p.is_file()}
 script='STAGE='+repr(stage)+'\nFILES='+repr(files)+'\n'+'''from pathlib import Path
import base64,json
s=Path(STAGE)/'revision2b/native';s.mkdir(parents=True,exist_ok=False)
for name,data in FILES.items():(s/name).write_bytes(base64.b64decode(data))
print(json.dumps({'status':'REVISION2_STAGED','files':len(FILES)}))
'''
 print(board(script).decode())
