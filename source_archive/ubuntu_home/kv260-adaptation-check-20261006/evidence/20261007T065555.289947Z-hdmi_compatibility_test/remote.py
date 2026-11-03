"""Temporarily test an advertised VGA fallback; always restore the old mode."""
import json
from pathlib import Path
import re
import subprocess
import time

results = []
def run(cmd):
    p = subprocess.run(cmd,capture_output=True,text=True,timeout=15)
    results.append({'command':cmd,'rc':p.returncode,'output':p.stdout+p.stderr})
    p.check_returncode()
    return p.stdout

text = run(['xrandr','--display',':0','--current'])
assert re.search(r'^DP-1 connected primary 1024x768\+0\+0',text,re.M)
assert re.search(r'^\s+640x480\s+59\.94',text,re.M)
state = json.loads(Path('/home/root/aura-realtime-vision-20261007/current.json').read_text())
status = Path(state['run_root'])/'status.json'
before = json.loads(status.read_text())
try:
    run(['xrandr','--display',':0','--output','DP-1','--mode','640x480','--rate','59.94','--primary'])
    run(['xset','-display',':0','dpms','force','on'])
    run(['xset','-display',':0','s','reset'])
    run(['xrandr','--display',':0','--current'])
    time.sleep(20)
finally:
    run(['xrandr','--display',':0','--output','DP-1','--mode','1024x768','--rate','60','--primary'])
time.sleep(2)
after = json.loads(status.read_text())
run(['xrandr','--display',':0','--current'])
print(json.dumps({'commands':results,'before_counts':{k:before[k] for k in ['capture_frames','detected_frames','rendered_frames']},'after_counts':{k:after[k] for k in ['capture_frames','detected_frames','rendered_frames']},'error':after['error'],'stopped':after['stopped'],'fpga_modified':False,'motion_command_emitted':False,'physical_screen_confirmed':False},indent=2))
assert not after['error'] and not after['stopped'] and after['rendered_frames']>before['rendered_frames']
