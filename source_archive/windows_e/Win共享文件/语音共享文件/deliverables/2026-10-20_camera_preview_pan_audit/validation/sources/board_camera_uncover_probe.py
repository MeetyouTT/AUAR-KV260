"""Dismiss the photographed pan dialog via its Return button; no jog."""
import base64,ctypes as C,ctypes.util,hashlib,importlib.util,json,time,urllib.request
from pathlib import Path
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def state():
 with opener.open('http://127.0.0.1:8783/api/state',timeout=.7) as r:v=json.load(r)
 p=v.get('ui_runtime',{}).get('preview_metrics',{})
 return {'sequence':v.get('sequence'),'page':v.get('ui_page'),'preview':p,'pulse':v.get('manual_pan',{}).get('pulse_us')}
before=state()
x=C.CDLL(ctypes.util.find_library('X11'));xt=C.CDLL(ctypes.util.find_library('Xtst'))
x.XOpenDisplay.argtypes=[C.c_char_p];x.XOpenDisplay.restype=C.c_void_p
x.XFlush.argtypes=[C.c_void_p];x.XCloseDisplay.argtypes=[C.c_void_p]
xt.XTestFakeMotionEvent.argtypes=[C.c_void_p,C.c_int,C.c_int,C.c_int,C.c_ulong]
xt.XTestFakeButtonEvent.argtypes=[C.c_void_p,C.c_uint,C.c_int,C.c_ulong]
d=x.XOpenDisplay(b':0');assert d
xt.XTestFakeMotionEvent(d,-1,700,440,0);xt.XTestFakeButtonEvent(d,1,1,0);xt.XTestFakeButtonEvent(d,1,0,0);x.XFlush(d);x.XCloseDisplay(d)
samples=[]
for i in range(32):
 time.sleep(.2);samples.append(state())
root=Path('/home/root/aura-voice-barge-in-20261020/candidate-667b70d586ca/runtime/aura')
spec=importlib.util.spec_from_file_location('cap',str(root/'tools/board_screen_capture.py'));cap=importlib.util.module_from_spec(spec);spec.loader.exec_module(cap)
p=Path('/tmp/aura-camera-uncovered-private.png');cap.capture(p)
from PIL import Image
with Image.open(str(p)) as im:im.save(str(p),optimize=True)
data=p.read_bytes()
print(json.dumps({'before':before,'samples':samples,'artifacts':{'uncovered-private.png':{'base64':base64.b64encode(data).decode(),'sha256':hashlib.sha256(data).hexdigest()}}}),flush=True)
