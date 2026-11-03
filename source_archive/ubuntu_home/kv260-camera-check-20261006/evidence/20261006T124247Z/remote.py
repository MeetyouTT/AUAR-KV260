
import ctypes as C,ctypes.util,json,base64,os,subprocess
from pathlib import Path
assert Path('/sys/block/mmcblk1/device/cid').read_text().strip()=='0353445345333247805558c00401a100'
x=C.CDLL(ctypes.util.find_library('X11'))
def fun(n,r,args):
 f=getattr(x,n);f.restype=r;f.argtypes=args;return f
P=C.c_void_p;U=C.c_ulong;I=C.c_int
d=fun('XOpenDisplay',P,[C.c_char_p])(b':0');assert d
root=fun('XDefaultRootWindow',U,[P])(d)
width=fun('XDisplayWidth',I,[P,I])(d,0);height=fun('XDisplayHeight',I,[P,I])(d,0)
query=fun('XQueryTree',I,[P,U,C.POINTER(U),C.POINTER(U),C.POINTER(C.POINTER(U)),C.POINTER(C.c_uint)])
fetch=fun('XFetchName',I,[P,U,C.POINTER(C.c_char_p)])
free=fun('XFree',I,[P])
windows=[]
def walk(w,depth=0):
 name=C.c_char_p()
 if fetch(d,w,C.byref(name)) and name.value:
  windows.append({'id':int(w),'name':name.value.decode(errors='replace')});free(C.cast(name,P))
 if depth>2:return
 r=U();parent=U();children=C.POINTER(U)();count=C.c_uint()
 if query(d,w,C.byref(r),C.byref(parent),C.byref(children),C.byref(count)):
  for i in range(count.value):walk(children[i],depth+1)
  if children:free(children)
walk(root)
im=fun('XGetImage',P,[P,U,I,I,C.c_uint,C.c_uint,U,I])(d,root,0,0,width,height,U(-1).value,2)
assert im
pixel=fun('XGetPixel',U,[P,I,I])
import numpy as np,cv2
frame=np.empty((240,320,3),dtype=np.uint8)
for yy in range(240):
 for xx in range(320):
  p=pixel(im,xx*width//320,yy*height//240);frame[yy,xx]=(p&255,(p>>8)&255,(p>>16)&255)
fun('XDestroyImage',I,[P])(im)
ok,j=cv2.imencode('.jpg',frame,[cv2.IMWRITE_JPEG_QUALITY,65])
pidpath=Path('/home/root/aura-camera-check-20261006/preview.pid')
pid=pidpath.read_text().strip() if pidpath.exists() else ''
def run(a):
 p=subprocess.run(a,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=10);return {'rc':p.returncode,'output':p.stdout[-5000:]}
print(json.dumps({'windows':windows,'size':[width,height],'jpeg':base64.b64encode(j).decode(),'process':run(['ps','-p',pid,'-o','pid,stat,wchan:30,args']),'formats':run(['v4l2-ctl','-d','/dev/video0','--list-formats-ext']),'gi':run(['python3','-c','import gi;gi.require_version("Gst","1.0");from gi.repository import Gst;print("Gst GI available")'])}))
