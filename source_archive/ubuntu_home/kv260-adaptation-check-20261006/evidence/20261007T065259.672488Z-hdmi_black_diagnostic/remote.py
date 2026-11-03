"""Read physical display connector state and current scanout without mutation."""
import json
from pathlib import Path
import subprocess

def run(cmd):
    try:
        p = subprocess.run(cmd,capture_output=True,text=True,timeout=12)
        return {'rc':p.returncode,'output':(p.stdout+p.stderr)[-16000:]}
    except Exception as exc:
        return {'error':str(exc)}

files = {}
for p in Path('/sys/class/drm').glob('card*'):
    for name in ['status','enabled','dpms','modes','link_status']:
        f = p/name
        if f.exists():
            files[str(f)] = f.read_text()
    if (p/'edid').exists():
        files[str(p/'edid')] = {'bytes':len((p/'edid').read_bytes())}
for name in ['/sys/kernel/debug/dri/0/state','/sys/kernel/debug/dri/1/state','/sys/class/graphics/fb0/blank','/sys/class/graphics/fb0/name','/sys/class/graphics/fb0/mode']:
    p = Path(name)
    if p.exists():
        try:
            files[name]=p.read_text()[-16000:]
        except Exception as exc:
            files[name]=str(exc)
commands = [['xrandr','--display',':0','--verbose'],['xset','-display',':0','q'],['systemctl','is-active','xserver-nodm'],['modetest','-c'],['dmesg'],['ps','-eo','pid,comm,args']]
print(json.dumps({'files':files,'commands':{' '.join(c):run(c) for c in commands}},indent=2))
