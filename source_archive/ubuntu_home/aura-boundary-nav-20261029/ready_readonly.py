import hashlib,json,shutil,subprocess,urllib.request
from pathlib import Path
d={'units':subprocess.check_output(['systemctl','show','aura-avatar-ui.service','aura-face-zone-editor.service','-p','Id','-p','MainPID','-p','ActiveState','-p','SubState'],text=True),'socket_exists':Path('/run/aura-face-zone-visibility-v1.sock').exists(),'xwininfo':shutil.which('xwininfo')}
try:
 with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=3) as f:u=json.load(f)
 d['ui']={'page':u['ui_page'],'phase':u['phase'],'manual_state':u['manual_pan']['state'],'following':u['manual_pan']['automatic_following'],'range':[u['manual_pan']['minimum_us'],u['manual_pan']['maximum_us']],'readback':u['manual_pan'].get('readback'),'display':u['avatar_display']}
except Exception as e:d['error']=type(e).__name__
print(json.dumps(d))
