"""Select fine step in the observed controls; never click a jog button."""
import base64,ctypes as C,ctypes.util,hashlib,json,time,urllib.request
from pathlib import Path
from PIL import Image
op=urllib.request.build_opener(urllib.request.ProxyHandler({}));url='http://127.0.0.1:8783'
def api(data=None):
 req=url+'/api/state' if data is None else urllib.request.Request(url+'/api/command',data=json.dumps(data).encode(),headers={'Content-Type':'application/json','Origin':url})
 with op.open(req,timeout=2) as r:return json.load(r)
s=api();before=s['manual_pan']
assert s['ui_page']=='vision' and before['panel_open'] and before['state']=='READY'
assert before['minimum_us']<=before['pulse_us']+before['left_sign']*5<=before['maximum_us']
x=C.CDLL(ctypes.util.find_library('X11'));xt=C.CDLL(ctypes.util.find_library('Xtst'))
x.XOpenDisplay.argtypes=[C.c_char_p];x.XOpenDisplay.restype=C.c_void_p
x.XFlush.argtypes=[C.c_void_p];x.XCloseDisplay.argtypes=[C.c_void_p]
x.XKeysymToKeycode.argtypes=[C.c_void_p,C.c_ulong];x.XKeysymToKeycode.restype=C.c_ubyte
xt.XTestFakeMotionEvent.argtypes=[C.c_void_p,C.c_int,C.c_int,C.c_int,C.c_ulong]
xt.XTestFakeButtonEvent.argtypes=[C.c_void_p,C.c_uint,C.c_int,C.c_ulong]
xt.XTestFakeKeyEvent.argtypes=[C.c_void_p,C.c_uint,C.c_int,C.c_ulong]
d=x.XOpenDisplay(b':0');assert d
xt.XTestFakeMotionEvent(d,-1,700,244,0);xt.XTestFakeButtonEvent(d,1,1,0);xt.XTestFakeButtonEvent(d,1,0,0);x.XFlush(d);time.sleep(.3)
for sym in [0xff57,0xff0d]:
 key=x.XKeysymToKeycode(d,sym);xt.XTestFakeKeyEvent(d,key,1,0);xt.XTestFakeKeyEvent(d,key,0,0)
x.XFlush(d);x.XCloseDisplay(d);time.sleep(.4)
ack=api({'type':'save_evidence'});target=Path(ack['report'])
for _ in range(30):
 if target.exists():break
 time.sleep(.1)
report=json.loads(target.read_text());buttons={k:v for k,v in report['ui_geometry']['visible_controls'].items() if k in ['pan_left','pan_stop','pan_right']}
assert len(buttons)==3 and all(v['sensitive'] for v in buttons.values()),buttons
after=api()['manual_pan'];assert before['readback']==after['readback'] and before['history']==after['history']
dest=Path('/tmp/aura-pan-fine-panel-only.png')
with Image.open(report['screenshot_path']) as full:full.crop((593,0,1024,548)).save(str(dest),optimize=True)
data=dest.read_bytes()
print(json.dumps({'status':'FINE_SELECTED_LEFT_ENABLED','movement_commands_sent':0,'buttons':buttons,'readback_unchanged':True,'pan':after,
 'artifacts':{'fine-panel-only.png':{'base64':base64.b64encode(data).decode(),'sha256':hashlib.sha256(data).hexdigest()}}}),flush=True)
