import json,subprocess,urllib.request
from pathlib import Path
out={'jobs':{},'units':{}}
for p in Path('/home/root/aura-dpu-vision-20261021/live-validation').glob('*/progress.json'):
    out['jobs'][str(p)]=json.loads(p.read_text())
for n in ['aura-avatar-ui.service','aura-camera-ui.service','xserver-nodm.service']:
    out['units'][n]=subprocess.check_output(['systemctl','show',n,'-p','MainPID','-p','NRestarts','-p','ActiveState'],timeout=4).decode().strip()
try:
    with urllib.request.build_opener(urllib.request.ProxyHandler({})).open('http://127.0.0.1:8790/health',timeout=2) as r:s=json.load(r)
    out['camera']={k:s.get(k) for k in ['pid','detected_frames','capture_frames','capture_hz','detection_hz','observation_age_ms','camera_error','detector_error','dpu_schedule']}
    out['camera']['face_targets']=s.get('identity',{}).get('face_targets')
except Exception as e:out['camera_error']=type(e).__name__+': '+str(e)
print(json.dumps(out))
