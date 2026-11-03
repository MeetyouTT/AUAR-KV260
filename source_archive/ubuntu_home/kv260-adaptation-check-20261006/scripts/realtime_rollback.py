"""Stop only the owned vision process and restore the prior camera preview."""
import json
import os
from pathlib import Path
import signal
import subprocess
import time

new = Path('/home/root/aura-realtime-vision-20261007')
old = Path('/home/root/aura-camera-check-20261006')
state = json.loads((new/'current.json').read_text())
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==state['after']['boot_id']
pid = state['pid']
script = str(Path(state['release'])/'realtime_vision.py')
proc = Path('/proc')/str(pid)
if proc.exists() and (proc/'cmdline').read_bytes():
    assert script.encode() in (proc/'cmdline').read_bytes().split(b'\0')
    os.kill(pid,signal.SIGTERM)
    deadline = time.monotonic()+10
    while proc.exists() and (proc/'cmdline').read_bytes() and time.monotonic()<deadline:
        time.sleep(.1)
    assert not proc.exists() or not (proc/'cmdline').read_bytes()
for p in Path('/proc').iterdir():
    if not p.name.isdecimal():
        continue
    try:
        assert not any(fd.resolve()==Path('/dev/video0') for fd in (p/'fd').iterdir()), 'Another process owns camera'
    except (FileNotFoundError,PermissionError):
        pass
subprocess.run(['xset','-display',':0','dpms','force','on'],check=True,timeout=10)
with (old/'fullscreen.log').open('ab') as log:
    fallback = subprocess.Popen(['python3','-u',str(old/'fullscreen_preview.py')],env=dict(os.environ,DISPLAY=':0'),
                                stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
(old/'preview.pid').write_text(str(fallback.pid))
time.sleep(3)
before = json.loads((old/'fullscreen-status.json').read_text())
time.sleep(2)
after = json.loads((old/'fullscreen-status.json').read_text())
passed = fallback.poll() is None and after['frames']>before['frames'] and not after['error']
print(json.dumps({'passed':passed,'restored_pid':fallback.pid,'before':before,'after':after,'fpga_modified':False,'motion_command_emitted':False},indent=2))
assert passed
