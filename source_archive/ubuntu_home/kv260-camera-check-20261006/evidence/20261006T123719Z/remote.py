
import os,json,subprocess,time,base64
from pathlib import Path
assert os.uname().machine=='aarch64'
assert Path('/sys/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100'
assert Path('/dev/video0').exists()
root=Path('/home/root/aura-camera-check-20261006');root.mkdir(exist_ok=True)
def run(args):
 p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=18)
 return {'rc':p.returncode,'output':p.stdout}
pidfile=root/'preview.pid'
oldpid=int(pidfile.read_text()) if pidfile.exists() else 0
oldcmd=Path('/proc')/str(oldpid)/'cmdline'
if oldpid and oldcmd.exists() and b'gst-launch-1.0' in oldcmd.read_bytes() and b'device=/dev/video0' in oldcmd.read_bytes():
 result={'preview':{'status':'existing','pid':oldpid,'running':True},'wake':run(['xset','-display',':0','dpms','force','on']),'display':run(['xrandr','--display',':0','--current']),'windows':run(['sh','-c','DISPLAY=:0 xwininfo -root -tree']),'log':(root/'preview.log').read_text()[-1500:]}
 print(json.dumps(result));raise SystemExit(0)
capture=r"""
import cv2,time,json,base64
c=cv2.VideoCapture('/dev/video0',cv2.CAP_V4L2)
c.set(cv2.CAP_PROP_FRAME_WIDTH,640);c.set(cv2.CAP_PROP_FRAME_HEIGHT,480)
c.set(cv2.CAP_PROP_FPS,30)
frames=0;first=None;t=time.monotonic()
for i in range(30):
 ok,f=c.read()
 if not ok:break
 frames+=1;first=f
c.release()
assert first is not None,'No frame received'
cv2.imwrite('/home/root/aura-camera-check-20261006/latest.jpg',first)
ok,j=cv2.imencode('.jpg',cv2.resize(first,(320,240)),[cv2.IMWRITE_JPEG_QUALITY,45])
print(json.dumps({'frames':frames,'elapsed_s':time.monotonic()-t,'shape':list(first.shape),'jpeg':base64.b64encode(j).decode()}))
"""
result={'usb':run(['lsusb']),'capture':run(['python3','-c',capture])}
if result['capture']['rc']==0:
 result['capture']=json.loads(result['capture']['output'].splitlines()[-1])
 result['wake']=run(['xset','-display',':0','dpms','force','on'])
 result['sink']=run(['gst-inspect-1.0','ximagesink'])
 result['sink']['output']=result['sink']['output'][:500]
 if result['sink']['rc']==0:
  pidfile=root/'preview.pid'
  oldpid=int(pidfile.read_text()) if pidfile.exists() else 0
  oldcmd=Path('/proc')/str(oldpid)/'cmdline'
  if oldpid and oldcmd.exists():
   result['preview']={'status':'existing','pid':oldpid,'command':oldcmd.read_bytes().decode(errors='replace')}
  else:
   log=(root/'preview.log').open('ab',buffering=0)
   args=['gst-launch-1.0','-e','v4l2src','device=/dev/video0','!','video/x-raw,format=YUY2,width=640,height=480,framerate=30/1','!','videoconvert','!','ximagesink','sync=false']
   p=subprocess.Popen(args,env=dict(os.environ,DISPLAY=':0'),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
   pidfile.write_text(str(p.pid));time.sleep(3)
   result['preview']={'pid':p.pid,'running':p.poll() is None,'rc':p.poll(),'log':(root/'preview.log').read_text()[-2000:]}
print(json.dumps(result))
