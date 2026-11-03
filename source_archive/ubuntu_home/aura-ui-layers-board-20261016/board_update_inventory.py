"""Read current UI release identities before preparing a reversible update."""
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import urllib.request

root = Path('/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009')
unit = Path('/etc/systemd/system/aura-avatar-ui.service')
pid = int(subprocess.check_output(['systemctl','show',unit.name,'-p','MainPID','--value'],text=True))
args = (Path('/proc')/str(pid)/'cmdline').read_bytes().decode().split('\0')
config_path = Path(args[args.index('--config')+1])
paths = ['tools/board_avatar_gtk.py','ui/board_touch_layout.json']
files = {}
for name in paths:
    p = root/'aura'/name
    files[name] = {'exists':p.is_file(),'sha256':hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None}
artifacts = {}
for name, p in [('installed_config.json',config_path),('installed_launcher.py',config_path.parent/'launcher.py'),
                ('installed_ui.service',unit)]:
    data = p.read_bytes()
    artifacts[name] = {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'base64':base64.b64encode(data).decode()}
with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=3) as r:
    state = json.load(r)
print(json.dumps({'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
    'runtime':str(root),'config_path':str(config_path),'files':files,
    'ui':{k:state.get(k) for k in ('phase','playing','paused','audio_output_state','ui_settings','error')},
    'artifacts':artifacts}))
