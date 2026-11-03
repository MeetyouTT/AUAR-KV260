import json,subprocess,urllib.request
from pathlib import Path
out={'launches':{},'pilots':{},'units':{}}
for p in Path('/home/root/aura-dpu-vision-20261021/shadow-launches').glob('*/launch-result.json'):
    out['launches'][str(p)]=json.loads(p.read_text())
for p in Path('/home/root/aura-dpu-vision-20261021/shadow-pilots').glob('*/deployment-result.json'):
    value=json.loads(p.read_text());value.pop('samples',None);out['pilots'][str(p)]=value
for name in ['aura-camera-ui.service','aura-avatar-ui.service','xserver-nodm.service']:
    out['units'][name]=subprocess.check_output(['systemctl','show',name,'-p','ActiveState','-p','MainPID','-p','NRestarts'],timeout=3).decode().strip()
try:
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open('http://127.0.0.1:8790/health',timeout=3) as r:s=json.load(r)
    out['camera']={k:s.get(k) for k in ['pid','capture_hz','detection_hz','detected_frames','observation_age_ms','camera_error','detector_error','dpu_schedule']}
    identity=s.get('identity',{});out['camera']['identity_backend']=identity.get('backend');out['camera']['face_targets']=identity.get('face_targets');out['camera']['shadow']=(identity.get('feature_inference') or {}).get('shadow')
except Exception as e:out['camera_error']=type(e).__name__+': '+str(e)
print(json.dumps(out))
