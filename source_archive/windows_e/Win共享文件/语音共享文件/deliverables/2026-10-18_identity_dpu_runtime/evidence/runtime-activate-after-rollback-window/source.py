import base64,hashlib,json,subprocess
from pathlib import Path
root=Path('/home/root/aura-adaptation-20261006/identity_dpu_runtime_20261018/96f86ddef3a96b93')
p=root/'activation-final-result.json'
if p.exists():
 data=p.read_bytes();result=json.loads(data)
 result['camera_samples_count']=len(result.pop('camera_samples',[]))
 result['artifacts']={'activation-final-result.json':{'base64':base64.b64encode(data).decode(),'sha256':hashlib.sha256(data).hexdigest()}}
 print(json.dumps(result),flush=True)
else:
 status={unit:subprocess.run(['systemctl','show',unit,'-p','ActiveState','-p','WorkingDirectory','--value'],stdout=subprocess.PIPE,text=True,timeout=3).stdout.strip() for unit in ['aura-camera-ui.service','aura-avatar-ui.service']}
 p=root/'activation-final.log'
 log=p.read_text(errors='replace')[-2000:] if p.exists() else 'NOT_STARTED'
 print(json.dumps({'status':'ACTIVATION_RESULT_NOT_WRITTEN','services':status,'worker_log_tail':log}),flush=True)
