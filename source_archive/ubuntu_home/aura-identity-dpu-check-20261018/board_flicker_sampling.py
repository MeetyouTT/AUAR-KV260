"""Sample a few X11 pixels over time; retain no image or personal data."""
import ctypes as C,ctypes.util,importlib.util,json,os,subprocess,time,urllib.request
from pathlib import Path
pid=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True).strip()
args=(Path('/proc')/pid/'cmdline').read_bytes().decode().split('\0');config=json.loads(Path(args[args.index('--config')+1]).read_text())
root=Path(config['runtime'])/'aura'
spec=importlib.util.spec_from_file_location('capture',str(root/'tools/board_screen_capture.py'));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
x=C.CDLL(ctypes.util.find_library('X11'));P=C.c_void_p;U=C.c_ulong
x.XOpenDisplay.argtypes=[C.c_char_p];x.XOpenDisplay.restype=P
x.XDefaultRootWindow.argtypes=[P];x.XDefaultRootWindow.restype=U
x.XGetImage.argtypes=[P,U,C.c_int,C.c_int,C.c_uint,C.c_uint,U,C.c_int];x.XGetImage.restype=C.POINTER(module.XImage)
x.XDestroyImage.argtypes=[C.POINTER(module.XImage)];x.XCloseDisplay.argtypes=[P]
display=x.XOpenDisplay(config.get('display',':0').encode());assert display
window=x.XDefaultRootWindow(display)
positions={'corner_tl':(0,0),'corner_tr':(1023,0),'corner_bl':(0,599),'corner_br':(1023,599),'panel':(580,250),'avatar_top':(795,150),'avatar_center':(795,350)}
values={name:[] for name in positions};started=time.monotonic()
try:
 for n in range(100):
  for name,(a,b) in positions.items():
   image=x.XGetImage(display,window,a,b,1,1,U(-1).value,2);assert image
   f=image.contents;raw=C.string_at(f.data,(f.bits_per_pixel+7)//8);number=int.from_bytes(raw,'little');x.XDestroyImage(image)
   values[name].append(number)
  time.sleep(.027+(n%5)*.003)
finally:x.XCloseDisplay(display)
result={}
for name,seq in values.items():result[name]={'changes':sum(a!=b for a,b in zip(seq,seq[1:])),'zero_count':seq.count(0),'most_common':sorted([[v,seq.count(v)] for v in set(seq)],key=lambda row:-row[1])[:6]}
activity=root/'tools/x11_display_activity.py';raw=activity.read_bytes()
import base64,hashlib
v={'samples':100,'elapsed_seconds':round(time.monotonic()-started,3),'pixels':result,'scope':'X pixels only; cannot observe physical HDMI blanking','files_modified':0,'display_commands_sent':0,'movement_commands_sent':0,'artifacts':{'x11_display_activity.py':{'base64':base64.b64encode(raw).decode(),'sha256':hashlib.sha256(raw).hexdigest()}}}
print(json.dumps(v),flush=True)
