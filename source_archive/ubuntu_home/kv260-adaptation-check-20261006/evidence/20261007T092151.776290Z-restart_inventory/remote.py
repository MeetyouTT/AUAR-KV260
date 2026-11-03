"""Inspect the current boot before restoring the preview."""
import hashlib
import json
from pathlib import Path
import subprocess

def run(cmd):
    p = subprocess.run(cmd,capture_output=True,text=True,timeout=12)
    return {'rc':p.returncode,'output':(p.stdout+p.stderr)[-7000:]}

root = Path('/home/root/aura-realtime-vision-20261007')
state = json.loads((root/'current.json').read_text())
staged = json.loads((root/'staged.json').read_text())
release = Path(state['release'])
hashes = {name:hashlib.sha256((release/name).read_bytes()).hexdigest() for name in staged['hashes']}
owners,previews = [],[]
for p in Path('/proc').iterdir():
    if not p.name.isdecimal():
        continue
    try:
        cmd = (p/'cmdline').read_bytes().split(b'\0')
        if str(release/'realtime_vision.py').encode() in cmd or b'/home/root/aura-camera-check-20261006/fullscreen_preview.py' in cmd:
            previews.append({'pid':int(p.name),'cmd':[s.decode(errors='replace') for s in cmd if s]})
        if any(fd.resolve()==Path('/dev/video0') for fd in (p/'fd').iterdir()):
            owners.append(int(p.name))
    except (FileNotFoundError,PermissionError):
        pass
commands = [['xrandr','--display',':0','--current'],['xset','-display',':0','q'],['systemctl','is-active','xserver-nodm'],['v4l2-ctl','--list-devices'],['xmutil','listapps']]
for p in Path('/dev').glob('video*'):
    commands.append(['v4l2-ctl','-d',str(p),'--list-formats-ext'])
print(json.dumps({'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'previous_boot':state['after']['boot_id'],'previous_pid':state['pid'],'release':str(release),'hashes_valid':hashes==staged['hashes'],'owners':owners,'previews':previews,'commands':{' '.join(c):run(c) for c in commands}},indent=2))
