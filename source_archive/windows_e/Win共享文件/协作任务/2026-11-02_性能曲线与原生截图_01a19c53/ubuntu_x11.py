"""Capture actual Ubuntu X11 application pixels; minimal native input helpers."""
import argparse, ctypes as C, json, os, time
from pathlib import Path
from datetime import datetime, timezone
from PIL import Image

os.environ.setdefault('DISPLAY',':0')
X=C.CDLL('libX11.so.6');T=C.CDLL('libXtst.so.6')
X.XOpenDisplay.argtypes=[C.c_char_p];X.XOpenDisplay.restype=C.c_void_p
D=X.XOpenDisplay(None)
if not D:raise RuntimeError('Cannot open Ubuntu X display')
for name,args,ret in [
 ('XRaiseWindow',[C.c_void_p,C.c_ulong],C.c_int),
 ('XSetInputFocus',[C.c_void_p,C.c_ulong,C.c_int,C.c_ulong],C.c_int),
 ('XSync',[C.c_void_p,C.c_int],C.c_int),
 ('XGetGeometry',[C.c_void_p,C.c_ulong,C.POINTER(C.c_ulong),C.POINTER(C.c_int),C.POINTER(C.c_int),C.POINTER(C.c_uint),C.POINTER(C.c_uint),C.POINTER(C.c_uint),C.POINTER(C.c_uint)],C.c_int),
 ('XStringToKeysym',[C.c_char_p],C.c_ulong),('XKeysymToKeycode',[C.c_void_p,C.c_ulong],C.c_uint),
 ('XDestroyImage',[C.c_void_p],C.c_int)]:
 f=getattr(X,name);f.argtypes=args;f.restype=ret
T.XTestFakeMotionEvent.argtypes=[C.c_void_p,C.c_int,C.c_int,C.c_int,C.c_ulong]
T.XTestFakeButtonEvent.argtypes=[C.c_void_p,C.c_uint,C.c_int,C.c_ulong]
T.XTestFakeKeyEvent.argtypes=[C.c_void_p,C.c_uint,C.c_int,C.c_ulong]

class XImage(C.Structure):
 _fields_=[('width',C.c_int),('height',C.c_int),('xoffset',C.c_int),('format',C.c_int),('data',C.c_void_p),('byte_order',C.c_int),('bitmap_unit',C.c_int),('bitmap_bit_order',C.c_int),('bitmap_pad',C.c_int),('depth',C.c_int),('bytes_per_line',C.c_int),('bits_per_pixel',C.c_int),('red_mask',C.c_ulong),('green_mask',C.c_ulong),('blue_mask',C.c_ulong)]
X.XGetImage.argtypes=[C.c_void_p,C.c_ulong,C.c_int,C.c_int,C.c_uint,C.c_uint,C.c_ulong,C.c_int]
X.XGetImage.restype=C.POINTER(XImage)

def key(name,down):
 code=X.XKeysymToKeycode(D,X.XStringToKeysym(name.encode('ascii')))
 if not code:raise ValueError(name)
 T.XTestFakeKeyEvent(D,code,int(down),0)

def hotkey(names):
 for n in names:key(n,True)
 for n in reversed(names):key(n,False)
 X.XSync(D,False)

def capture(window,output,region=None):
 X.XRaiseWindow(D,window);X.XSetInputFocus(D,window,2,0);X.XSync(D,False);time.sleep(.5)
 root=C.c_ulong();x=C.c_int();y=C.c_int();w=C.c_uint();h=C.c_uint();b=C.c_uint();depth=C.c_uint()
 assert X.XGetGeometry(D,window,C.byref(root),C.byref(x),C.byref(y),C.byref(w),C.byref(h),C.byref(b),C.byref(depth))
 rx,ry,rw,rh=region if region else (0,0,w.value,h.value)
 assert rx>=0 and ry>=0 and rx+rw<=w.value and ry+rh<=h.value
 ptr=X.XGetImage(D,window,rx,ry,rw,rh,C.c_ulong(-1).value,2)
 assert ptr
 im=ptr.contents
 assert im.bits_per_pixel==32 and im.byte_order==0 and im.red_mask==0xff0000
 pixels=C.string_at(im.data,im.bytes_per_line*im.height)
 img=Image.frombytes('RGB',(im.width,im.height),pixels,'raw','BGRX',im.bytes_per_line,1)
 X.XDestroyImage(ptr)
 img.save(output)
 meta={'captured_utc':datetime.now(timezone.utc).isoformat(),'window_id':hex(window),'size':list(img.size),'window_region':[rx,ry,rw,rh],'source':'Actual Ubuntu X11 application window pixels','pixel_content_edited':False,'board_accessed':False}
 Path(output).with_suffix('.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
 print(json.dumps(meta))

def main():
 p=argparse.ArgumentParser();p.add_argument('--window',type=lambda s:int(s,0));p.add_argument('--output');p.add_argument('--region',nargs=4,type=int);p.add_argument('--click',nargs=2,type=int);p.add_argument('--key');p.add_argument('--type');a=p.parse_args()
 if a.window:X.XRaiseWindow(D,a.window);X.XSetInputFocus(D,a.window,2,0);X.XSync(D,False)
 if a.click:
  T.XTestFakeMotionEvent(D,-1,*a.click,0);T.XTestFakeButtonEvent(D,1,1,0);T.XTestFakeButtonEvent(D,1,0,0);X.XSync(D,False)
 if a.key:hotkey(a.key.split('+'))
 if a.type:
  shifted={'_':'minus',':':'semicolon','"':'apostrophe','+':'equal','{':'bracketleft','}':'bracketright'}
  plain={' ':'space','/':'slash','.':'period','-':'minus',';':'semicolon','=':'equal','(':'9',')':'0'}
  for ch in a.type:
   if ch in shifted:hotkey(['Shift_L',shifted[ch]])
   elif ch in '()':hotkey(['Shift_L',plain[ch]])
   elif ch.isupper():hotkey(['Shift_L',ch.lower()])
   else:hotkey([plain.get(ch,ch)])
 if a.output:capture(a.window,a.output,a.region)

if __name__=='__main__':main()
