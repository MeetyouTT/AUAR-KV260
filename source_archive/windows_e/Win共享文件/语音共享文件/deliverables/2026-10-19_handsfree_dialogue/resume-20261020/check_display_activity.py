"""Check the real X11 wake API without blanking or changing idle settings."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
c=json.loads((HERE/'candidate.json').read_text(encoding='utf-8'))
remote=r'''
import ctypes as C,ctypes.util,json,os,sys
os.environ['DISPLAY']=':0';sys.path.insert(0,ROOT+'/aura')
from tools.x11_display_activity import DisplayActivity
x=C.CDLL(ctypes.util.find_library('X11'));P=C.c_void_p;I=C.c_int
x.XOpenDisplay.argtypes=[C.c_char_p];x.XOpenDisplay.restype=P
x.XGetScreenSaver.argtypes=[P,*[C.POINTER(I)]*4];x.XCloseDisplay.argtypes=[P]
e=C.CDLL(ctypes.util.find_library('Xext'));e.DPMSInfo.argtypes=[P,C.POINTER(C.c_ushort),C.POINTER(I)]
d=x.XOpenDisplay(None);assert d
def state():
 a,b,c,f=I(),I(),I(),I();x.XGetScreenSaver(d,C.byref(a),C.byref(b),C.byref(c),C.byref(f))
 level=C.c_ushort();enabled=I();assert e.DPMSInfo(d,C.byref(level),C.byref(enabled))
 return {'timeout_seconds':a.value,'interval_seconds':b.value,'blanking':c.value,'exposures':f.value,
  'dpms_level':level.value,'dpms_enabled':bool(enabled.value)}
try:
 before=state();activity=DisplayActivity();activity.tick(True);assert not activity.error,activity.error
 after=state();assert after['dpms_level']==0
 assert {k:v for k,v in before.items() if k!='dpms_level'}=={k:v for k,v in after.items() if k!='dpms_level'}
 print(json.dumps({'passed':True,'before':before,'after':after,'runtime':ROOT,
  'screen_forced_off_for_test':False,'camera_or_audio_touched':False}))
finally:x.XCloseDisplay(d)
'''.replace('ROOT',repr(c['runtime']))
r=json.loads(ssh('python3 -B -',remote,timeout=15))
(HERE/'display_activity_check.json').write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r))
