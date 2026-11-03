"""One character-only offscreen GLES owner; no audio/camera/model/business I/O."""
from pathlib import Path
import argparse,ctypes as C,json,math,os,time,sys
HERE=Path(__file__).resolve().parent
W,H=423,516
class EGL:
 def __init__(self):
  I,U,P=C.c_int,C.c_uint,C.c_void_p
  env=json.loads((HERE/'display_environment.json').read_bytes())
  assert set(env)<=set(('DISPLAY','XAUTHORITY')) and 'DISPLAY' in env
  os.environ.update(env)
  self.x=C.CDLL('libX11.so.6');self.x.XOpenDisplay.argtypes=[C.c_char_p];self.x.XOpenDisplay.restype=P;self.x.XCloseDisplay.argtypes=[P]
  self.e=C.CDLL('libEGL.so.1')
  for name,result,args in [('eglGetDisplay',P,[P]),('eglInitialize',I,[P,C.POINTER(I),C.POINTER(I)]),('eglBindAPI',I,[U]),('eglChooseConfig',I,[P,C.POINTER(I),C.POINTER(P),I,C.POINTER(I)]),('eglCreatePbufferSurface',P,[P,P,C.POINTER(I)]),('eglCreateContext',P,[P,P,P,C.POINTER(I)]),('eglMakeCurrent',I,[P,P,P,P]),('eglDestroyContext',I,[P,P]),('eglDestroySurface',I,[P,P]),('eglTerminate',I,[P])]:
   f=getattr(self.e,name);f.restype=result;f.argtypes=args
  self.xd=self.x.XOpenDisplay(None);assert self.xd
  self.d=self.e.eglGetDisplay(self.xd);assert self.e.eglInitialize(self.d,C.byref(I()),C.byref(I()));assert self.e.eglBindAPI(0x30A0)
  attrs=(I*13)(0x3033,1,0x3040,4,0x3024,8,0x3023,8,0x3022,8,0x3021,8,0x3038);cfg=P();count=I()
  assert self.e.eglChooseConfig(self.d,attrs,C.byref(cfg),1,C.byref(count)) and count.value
  self.s=self.e.eglCreatePbufferSurface(self.d,cfg,(I*5)(0x3057,W,0x3056,H,0x3038));self.c=self.e.eglCreateContext(self.d,cfg,None,(I*3)(0x3098,2,0x3038))
  assert self.s and self.c and self.e.eglMakeCurrent(self.d,self.s,self.s,self.c)
 def close(self):
  self.e.eglMakeCurrent(self.d,None,None,None);self.e.eglDestroyContext(self.d,self.c);self.e.eglDestroySurface(self.d,self.s);self.e.eglTerminate(self.d);self.x.XCloseDisplay(self.xd)
