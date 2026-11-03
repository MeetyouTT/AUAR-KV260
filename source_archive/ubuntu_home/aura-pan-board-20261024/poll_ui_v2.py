ROOT='/home/root/aura-pan-ui-v2-20261024/observed-ecfbdef064d157b6'
PREFIX='aura-pan-ui-v2-ecfbdef064d157b6'
import json,subprocess,urllib.request
from pathlib import Path
root=Path(ROOT);result={'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'state':json.loads((root/'trial-state.json').read_text()) if (root/'trial-state.json').exists() else None}
for ending in ['activation.service','guard.timer','guard.service']:
 p=subprocess.run(['systemctl','show',PREFIX+'-'+ending,'--property=ActiveState,SubState,MainPID,Result,ExecMainStatus'],capture_output=True,text=True)
 result[ending]=dict(x.split('=',1) for x in p.stdout.splitlines() if '=' in x)
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
try:
 with op.open('http://127.0.0.1:8783/api/state',timeout=2) as response:g=json.load(response)
 result['gui']={k:g.get(k) for k in ['phase','audio_output_state','playing','manual_pan']}
except Exception as error:result['gui_error']=str(error)
try:
 with op.open('http://127.0.0.1:8790/health',timeout=2) as response:h=json.load(response)
 result['camera']={k:h.get(k) for k in ['pid','detected_frames','detection_hz']}
except Exception as error:result['camera_error']=str(error)
print(json.dumps(result))
