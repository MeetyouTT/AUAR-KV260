"""Bring the owned live vision window forward and reveal the boundary overlay."""
import ctypes,json,os,re,shutil,subprocess,time,urllib.request
from pathlib import Path
os.environ['DISPLAY']=':0';o=urllib.request.build_opener(urllib.request.ProxyHandler({}));base='http://127.0.0.1:8783'
def state():
 with o.open(base+'/api/state',timeout=3) as r:return json.load(r)
before=state();answers=[]
for typ in ('pan_dialog','pan_close'):
 q=urllib.request.Request(base+'/api/command',data=json.dumps({'type':typ}).encode(),headers={'Origin':base,'Content-Type':'application/json'})
 with o.open(q,timeout=3) as r:answers.append(json.load(r))
 time.sleep(.3)
N=Path('/home/root/aura-pan-current-20261024/463c9307/gui-face-edge-v5');log=(N/'runtime/stage.log').read_text();matches=re.findall(r'FOREGROUND (\{[^\n]+\})',log);assert matches
xid=int(json.loads(matches[-1])['own_window'],16);method=None
if shutil.which('wmctrl'):
 p=subprocess.run(['wmctrl','-ia',hex(xid)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);method={'tool':'wmctrl','rc':p.returncode,'error':p.stderr[-300:]}
elif shutil.which('xdotool'):
 p=subprocess.run(['xdotool','windowactivate','--sync',str(xid)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=5);method={'tool':'xdotool','rc':p.returncode,'error':p.stderr[-300:]}
else:
 x=ctypes.CDLL('libX11.so.6');x.XOpenDisplay.argtypes=[ctypes.c_char_p];x.XOpenDisplay.restype=ctypes.c_void_p
 x.XDefaultRootWindow.argtypes=[ctypes.c_void_p];x.XDefaultRootWindow.restype=ctypes.c_ulong
 x.XInternAtom.argtypes=[ctypes.c_void_p,ctypes.c_char_p,ctypes.c_int];x.XInternAtom.restype=ctypes.c_ulong
 class Data(ctypes.Union):_fields_=[('b',ctypes.c_char*20),('s',ctypes.c_short*10),('l',ctypes.c_long*5)]
 class Client(ctypes.Structure):_fields_=[('type',ctypes.c_int),('serial',ctypes.c_ulong),('send_event',ctypes.c_int),('display',ctypes.c_void_p),('window',ctypes.c_ulong),('message_type',ctypes.c_ulong),('format',ctypes.c_int),('data',Data)]
 class Event(ctypes.Union):_fields_=[('client',Client),('padding',ctypes.c_long*24)]
 d=x.XOpenDisplay(None);assert d;e=Event();e.client.type=33;e.client.send_event=1;e.client.display=d;e.client.window=xid;e.client.message_type=x.XInternAtom(d,b'_NET_ACTIVE_WINDOW',0);e.client.format=32;e.client.data.l[0]=2
 x.XSendEvent.argtypes=[ctypes.c_void_p,ctypes.c_ulong,ctypes.c_int,ctypes.c_long,ctypes.POINTER(Event)];x.XFlush.argtypes=[ctypes.c_void_p]
 x.XSendEvent(d,x.XDefaultRootWindow(d),0,(1<<19)|(1<<20),ctypes.byref(e));x.XFlush(d);method={'tool':'X11_active_window','requested':hex(xid)}
time.sleep(1);after=state()
print(json.dumps({'before_page':before.get('ui_page'),'after_page':after.get('ui_page'),'commands':answers,'foreground':method,
 'preview':after['ui_runtime'].get('preview_metrics'),'manual':{k:after['manual_pan'].get(k) for k in ('state','automatic_following','readback')},'editor_active':subprocess.run(['systemctl','is-active','aura-face-zone-editor.service'],stdout=subprocess.PIPE,text=True).stdout.strip()}))
