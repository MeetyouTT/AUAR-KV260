"""Read deployment prerequisites without opening camera or motion hardware."""
import hashlib
import json
from pathlib import Path
import subprocess
import time

root = Path('/home/root/aura-realtime-vision-20261007')
current = json.loads((root/'current.json').read_text())
release, run = Path(current['release']), Path(current['run_root'])
before = json.loads((run/'status.json').read_text())
time.sleep(3)
after = json.loads((run/'status.json').read_text())
boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
pid = current['pid']
command = (Path('/proc')/str(pid)/'cmdline').read_bytes().split(b'\0')
owners = []
for proc in Path('/proc').iterdir():
    if not proc.name.isdecimal():
        continue
    try:
        if any(fd.resolve() == Path('/dev/video0') for fd in (proc/'fd').iterdir()):
            owners.append(int(proc.name))
    except (FileNotFoundError, PermissionError):
        pass
apps = subprocess.run(['xmutil','listapps'],capture_output=True,text=True,timeout=10)
display = subprocess.run(['xset','-display',':0','q'],capture_output=True,text=True,timeout=10)
names = ['vision_core.py','x11_window.py','realtime_vision.py','test_vision_core.py','board_launch.py']
print(json.dumps({'current_release':str(release),'current_run':str(run),'pid':pid,
                  'boot_id':boot,'same_boot':after['boot_id']==boot,
                  'owned':str(release/'realtime_vision.py').encode() in command,
                  'owners':owners,'before':before,'after':after,
                  'hashes':{name:hashlib.sha256((release/name).read_bytes()).hexdigest() for name in names},
                  'apps_rc':apps.returncode,'apps':apps.stdout,'display_rc':display.returncode,
                  'display':display.stdout,'motion_command_emitted':False,'fpga_modified':False}))
