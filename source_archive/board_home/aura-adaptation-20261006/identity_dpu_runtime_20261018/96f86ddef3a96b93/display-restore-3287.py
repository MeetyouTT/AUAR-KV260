import os,subprocess
e=dict(os.environ,DISPLAY=':0')
subprocess.run(['xrandr','--output','DP-1','--mode','1024x600','--rate','59.85'],env=e,timeout=7,check=True)
subprocess.run(['xset','dpms','force','on'],env=e,timeout=5,check=True)
