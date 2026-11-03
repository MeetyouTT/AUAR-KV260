"""Inspect X11 blanking/DPMS and wake display after user reports black screen."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
remote=r'''
import ctypes as C,ctypes.util,json,shutil,subprocess,os
x=C.CDLL(ctypes.util.find_library('X11'));P=C.c_void_p;I=C.c_int;U=C.c_ulong
x.XOpenDisplay.argtypes=[C.c_char_p];x.XOpenDisplay.restype=P
x.XDefaultRootWindow.argtypes=[P];x.XDefaultRootWindow.restype=U
x.XGetScreenSaver.argtypes=[P,*[C.POINTER(I)]*4]
x.XResetScreenSaver.argtypes=[P];x.XSync.argtypes=[P,I];x.XCloseDisplay.argtypes=[P]
d=x.XOpenDisplay(b':0');assert d
class Info(C.Structure):
 _fields_=[('window',U),('state',I),('kind',I),('til_or_since',U),('idle',U),('event_mask',U)]
s=None
if ctypes.util.find_library('Xss'):
 s=C.CDLL(ctypes.util.find_library('Xss'));s.XScreenSaverAllocInfo.restype=C.POINTER(Info)
 s.XScreenSaverQueryInfo.argtypes=[P,U,C.POINTER(Info)]
e=C.CDLL(ctypes.util.find_library('Xext'));e.DPMSCapable.argtypes=[P];e.DPMSInfo.argtypes=[P,C.POINTER(C.c_ushort),C.POINTER(I)]
e.DPMSForceLevel.argtypes=[P,C.c_ushort]
def state():
 a,b,c,f=I(),I(),I(),I();x.XGetScreenSaver(d,C.byref(a),C.byref(b),C.byref(c),C.byref(f))
 saver_state=idle=None
 if s:
  p=s.XScreenSaverAllocInfo();s.XScreenSaverQueryInfo(d,x.XDefaultRootWindow(d),p)
  saver_state=p.contents.state;idle=p.contents.idle
 level=C.c_ushort();enabled=I();capable=bool(e.DPMSCapable(d))
 if capable:e.DPMSInfo(d,C.byref(level),C.byref(enabled))
 return {'timeout_seconds':a.value,'interval_seconds':b.value,'screensaver_state':saver_state,
  'idle_ms':idle,'dpms_capable':capable,'dpms_level':level.value,'dpms_enabled':bool(enabled.value)}
try:
 before=state();x.XResetScreenSaver(d)
 if before['dpms_capable']:e.DPMSForceLevel(d,0)
 x.XSync(d,0);after=state()
 print(json.dumps({'before':before,'after':after,'camera_or_audio_touched':False}))
finally:x.XCloseDisplay(d)
'''
r=json.loads(ssh('python3 -B -',remote,timeout=15))
(HERE/'display_restore.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r))
