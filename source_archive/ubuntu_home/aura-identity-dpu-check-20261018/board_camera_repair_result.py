"""Read installation outcome and current state; no motion or device access."""
import base64,gzip,hashlib,json,subprocess,urllib.request
from pathlib import Path
p=Path('/home/root/aura-pan-manual-ui-20261020/camera-fix-v3')
v={'complete':(p/'deployment-result.json').is_file(),'artifacts':{}}
for n in ['deployment-result.json','failure-traceback.txt']:
 q=p/n
 if q.is_file():
  raw=gzip.compress(q.read_bytes(),mtime=0);v['artifacts'][n+'.gz']={'base64':base64.b64encode(raw).decode(),'sha256':hashlib.sha256(raw).hexdigest()}
if v['complete']:v['deployment']=json.loads((p/'deployment-result.json').read_text())
v['units']={u:subprocess.check_output(['systemctl','show',u,'-p','ActiveState,SubState,MainPID,NRestarts,WorkingDirectory'],text=True) for u in ['aura-avatar-ui.service','aura-camera-ui.service']}
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
try:
 with op.open('http://127.0.0.1:8783/api/state',timeout=1) as r:s=json.load(r)
 v['gui']={k:s.get(k) for k in ['phase','playing','ui_page','error','manual_pan','ui_tick_ms','sequence']}
 v['preview']=s.get('ui_runtime',{}).get('preview_metrics')
except Exception as e:v['gui']={'unavailable':type(e).__name__}
try:
 with op.open('http://127.0.0.1:8790/health',timeout=1) as r:s=json.load(r)
 v['camera']={k:s.get(k) for k in ['pid','capture_frames','capture_hz','detection_hz','identity_recognition','camera_error','detector_error']}
except Exception as e:v['camera']={'unavailable':type(e).__name__}
print(json.dumps(v),flush=True)
