
import subprocess,json
from pathlib import Path
assert Path('/sys/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100'
def run(a):
 p=subprocess.run(a,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=15)
 return {'rc':p.returncode,'output':p.stdout}
r={}
r['wake']=run(['xset','-display',':0','dpms','force','on'])
r['display']=run(['xrandr','--display',':0','--verbose'])
text=r['display']['output']
if r['display']['rc']==0 and '1024x600' in text:
 r['native_mode']=run(['xrandr','--display',':0','--output','DP-1','--mode','1024x600'])
r['after']=run(['xrandr','--display',':0','--current'])
r['power']=run(['xset','-display',':0','q'])
print(json.dumps(r))
