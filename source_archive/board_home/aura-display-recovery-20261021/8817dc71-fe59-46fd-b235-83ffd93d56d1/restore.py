import os,subprocess
from pathlib import Path
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()=='8817dc71-fe59-46fd-b235-83ffd93d56d1'
e=dict(os.environ,DISPLAY=':0')
subprocess.run(['xrandr','--fb','1024x600','--output','DP-1','--mode','1024x600','--rate','59.85','--primary','--pos','0x0'],env=e,check=True,timeout=8)
subprocess.run(['xset','dpms','force','on'],env=e,check=True,timeout=4)
