import json,subprocess,urllib.request
from pathlib import Path
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8790/health',timeout=3) as f:h=json.load(f)
out={'read_only':True,'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 'camera':{k:h.get(k) for k in ('pid','capture_hz','detection_hz','camera_error','detector_error')},
 'face_targets':h.get('identity',{}).get('face_targets'),'schedule':h.get('dpu_schedule')}
out['units']={name:subprocess.check_output(['systemctl','show',name,'-p','MainPID','-p','ActiveState','-p','NRestarts'],timeout=3).decode().strip()
 for name in ('aura-camera-ui.service','aura-avatar-ui.service','xserver-nodm.service')}
print(json.dumps(out))
