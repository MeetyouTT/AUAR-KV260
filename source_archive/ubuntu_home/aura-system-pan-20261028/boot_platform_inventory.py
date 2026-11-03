import json,subprocess
from pathlib import Path
d={}
for unit in ['aura-camera-ui.service','dfx-mgrd.service']:
 s=subprocess.check_output(['systemctl','show',unit,'-p','FragmentPath','-p','ExecStartPre','-p','After','-p','Requires','-p','Wants'],text=True)
 d[unit]=s
d['base_camera_unit']=Path('/etc/systemd/system/aura-camera-ui.service').read_text()
for p in [Path('/etc/dfx-mgrd/daemon.conf'),Path('/etc/dfx-mgrd/dfx-mgrd.conf')]:
 if p.exists():d[str(p)]=p.read_text()
print(json.dumps(d))
