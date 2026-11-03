"""Verify actual X11 map states after page commands; no screenshots or motion."""
import ctypes as C,ctypes.util,json,os,re,subprocess,time,urllib.request
from pathlib import Path
R=Path('/home/root/aura-boundary-nav-20261029');s=json.loads((R/'state.json').read_text());base='http://127.0.0.1:8783'
def get():
 with urllib.request.urlopen(base+'/api/state',timeout=2) as f:return json.load(f)
def command(page):
 q=urllib.request.Request(base+'/api/command',data=json.dumps({'type':'ui_page','page':page}).encode(),headers={'Origin':base,'Content-Type':'application/json'})
 with urllib.request.urlopen(q,timeout=3) as f:return json.load(f)
until=time.monotonic()+55
while time.monotonic()<until:
 try:
  u=get()
  if u.get('manual_pan',{}).get('state')=='READY' and Path('/run/aura-face-zone-visibility-v1.sock').exists():break
 except Exception:pass
 time.sleep(.5)
else:raise RuntimeError('Page-sync GUI/editor not ready')
assert not u['manual_pan']['automatic_following'] and u['manual_pan']['readback']['flags']==0
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==s['boot_id']
class Attributes(C.Structure):
 _fields_=[('x',C.c_int),('y',C.c_int),('width',C.c_int),('height',C.c_int),('border_width',C.c_int),('depth',C.c_int),('visual',C.c_void_p),('root',C.c_ulong),('c_class',C.c_int),('bit_gravity',C.c_int),('win_gravity',C.c_int),('backing_store',C.c_int),('backing_planes',C.c_ulong),('backing_pixel',C.c_ulong),('save_under',C.c_int),('colormap',C.c_ulong),('map_installed',C.c_int),('map_state',C.c_int),('all_event_masks',C.c_long),('your_event_mask',C.c_long),('do_not_propagate_mask',C.c_long),('override_redirect',C.c_int),('screen',C.c_void_p)]
x=C.CDLL(ctypes.util.find_library('X11'));x.XOpenDisplay.argtypes=[C.c_char_p];x.XOpenDisplay.restype=C.c_void_p
x.XDefaultRootWindow.argtypes=[C.c_void_p];x.XDefaultRootWindow.restype=C.c_ulong
x.XQueryTree.argtypes=[C.c_void_p,C.c_ulong,C.POINTER(C.c_ulong),C.POINTER(C.c_ulong),C.POINTER(C.POINTER(C.c_ulong)),C.POINTER(C.c_uint)];x.XQueryTree.restype=C.c_int
x.XFetchName.argtypes=[C.c_void_p,C.c_ulong,C.POINTER(C.c_void_p)];x.XFetchName.restype=C.c_int
x.XGetWindowAttributes.argtypes=[C.c_void_p,C.c_ulong,C.POINTER(Attributes)];x.XGetWindowAttributes.restype=C.c_int
x.XFree.argtypes=[C.c_void_p];x.XCloseDisplay.argtypes=[C.c_void_p]
display=x.XOpenDisplay(b':0');assert display
def windows():
 result={};stack=[x.XDefaultRootWindow(display)]
 while stack:
  parent=stack.pop();root=C.c_ulong();up=C.c_ulong();children=C.POINTER(C.c_ulong)();count=C.c_uint()
  if not x.XQueryTree(display,parent,C.byref(root),C.byref(up),C.byref(children),C.byref(count)):continue
  ids=[children[i] for i in range(count.value)]
  if children:x.XFree(children)
  for wid in ids:
   name=C.c_void_p()
   if x.XFetchName(display,wid,C.byref(name)) and name:
    text=C.string_at(name).decode(errors='replace');x.XFree(name)
    if text.startswith('AURA_FACE_'):result[text]=wid
   stack.append(wid)
 return result
def mapped(ids):
 result={}
 for title,wid in ids.items():
  a=Attributes();assert x.XGetWindowAttributes(display,wid,C.byref(a));result[title]=a.map_state
 return result
rows=[];ids={};names=['AURA_FACE_LEFT_BOUNDARY','AURA_FACE_RIGHT_BOUNDARY']
try:
 for index in range(4):
  assert command('vision')['ok'];until=time.monotonic()+2
  while time.monotonic()<until:
   ids=windows();state=mapped(ids)
   if all(state.get(n)==2 for n in names):break
   time.sleep(.02)
  else:raise RuntimeError('Both boundaries not shown on vision page')
  assert command('main')['ok'];returned=time.monotonic();immediate=mapped(ids)
  receipt=json.loads(Path('/run/aura-face-zone-last-page.json').read_text())
  assert receipt['page']=='main' and receipt['acknowledged'] and receipt['waited_for_hide']
  assert all(immediate[n]==0 for n in names),'Boundary still mapped after page command'
  time.sleep(.65);later=mapped(ids);assert all(later[n]==0 for n in names),'Stale polling reopened a boundary'
  rows.append({'cycle':index,'immediate_map_states':immediate,'delayed_map_states':later,'hide_ack_ms':receipt['elapsed_ms'],'post_reply_sample_ms':round((time.monotonic()-returned)*1000,3)})
 # Exercise page events faster than the previous half-second UI poll.
 for page in ['vision','main','vision','main']:assert command(page)['ok']
 fast=mapped(windows());assert all(fast[n]==0 for n in names)
 assert command(s['previous_page'])['ok']
 u=get();camera=int(subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','MainPID','--value'],text=True));assert camera==s['camera_pid']
 result={'status':'PAGE_HIDE_ACK_AND_NATIVE_UNMAP_PASS','boot_id':s['boot_id'],'cycles':rows,'fast_switch_final_map_states':fast,'page_restored':s['previous_page'],'camera_pid_unchanged':camera,'manual_range_us':[u['manual_pan']['minimum_us'],u['manual_pan']['maximum_us']],'readback_after':u['manual_pan']['readback'],'motion_commands_sent':0,'pixel_or_physical_monitor_measurement':False}
 (R/'live-verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
finally:x.XCloseDisplay(display)
