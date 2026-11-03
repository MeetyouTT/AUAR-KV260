import json,subprocess,urllib.request
from pathlib import Path
root=Path('/home/root/aura-adaptation-20261006/identity_dpu_runtime_20261018/96f86ddef3a96b93')
p=root/'activation-retry-result.json'
if p.exists():
 result=json.loads(p.read_text())
 result['camera_samples_count']=len(result.pop('camera_samples',[]))
 print(json.dumps(result),flush=True)
else:
 status={unit:subprocess.run(['systemctl','is-active',unit],stdout=subprocess.PIPE,text=True,timeout=3).stdout.strip() for unit in ['aura-camera-ui.service','aura-avatar-ui.service']}
 print(json.dumps({'status':'ACTIVATION_RUNNING','services':status}),flush=True)
