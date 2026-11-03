"""Re-enable only the currently active display output; preserve camera/PL."""
import json
from pathlib import Path
import re
import subprocess
import time

def run(args):
    p = subprocess.run(args,capture_output=True,text=True,timeout=15)
    results.append({'command':args,'rc':p.returncode,'output':p.stdout+p.stderr})
    p.check_returncode()
    return p.stdout

results = []
text = run(['xrandr','--display',':0','--current'])
assert re.search(r'^DP-1 connected primary 1024x768\+0\+0',text,re.M)
current = json.loads(Path('/home/root/aura-realtime-vision-20261007/current.json').read_text())
status = Path(current['run_root'])/'status.json'
before = json.loads(status.read_text())
enable = ['xrandr','--display',':0','--output','DP-1','--mode','1024x768','--rate','60','--primary']
try:
    run(['xrandr','--display',':0','--output','DP-1','--off'])
    time.sleep(1)
finally:
    run(enable)
run(['xset','-display',':0','dpms','force','on'])
run(['xset','-display',':0','s','reset'])
time.sleep(3)
after = json.loads(status.read_text())
run(['xrandr','--display',':0','--verbose'])
run(['xset','-display',':0','q'])
print(json.dumps({'commands':results,'before':before,'after':after,'edid_bytes':len(Path('/sys/class/drm/card0-DP-1/edid').read_bytes()),'camera_reopened':False,'fpga_modified':False,'motion_command_emitted':False},indent=2))
assert not after['error'] and not after['stopped'] and after['rendered_frames']>before['rendered_frames']
