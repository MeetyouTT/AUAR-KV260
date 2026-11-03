#!/usr/bin/env python3
"""Deploy one pinned GTK runtime from the user's KV260 USB; record UART evidence.

All board writes are confined to a new avatar directory. No camera, firmware,
system audio settings, or unrelated processes are modified.
"""
import argparse
import ast
import base64
import datetime
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import shlex
import sys
import textwrap

ROOT = Path(__file__).resolve().parent
TRANSPORT = Path('/home/ghmd/kv260-dfx-state-boardtest-20261004/scripts/uart_phase.py')
DEST = '/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009'
USB = '/run/media/sda1'
NAME = 'aura-board-avatar-gtk-runtime-20261009T112752Z-57fc8c.zip'
SHA = '1a8677ce385516b406344f5e22acfed72e1fd9ab1ffe79aa745760e1137917de'
SIZE = 217023529
PRELUDE = """
import hashlib,json,os,subprocess,time,zipfile
from pathlib import Path,PurePosixPath
root=Path(DEST)
usb=Path(USB)
source=usb/'AURA_AVATAR_20261009_1a8677ce'/NAME
def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
"""

PHASES = {
    'inspect': """
mounts=[line for line in Path('/proc/self/mountinfo').read_text().splitlines() if line.split()[4]==str(usb)]
assert len(mounts)==1 and ' - vfat /dev/sda1 ' in mounts[0],mounts
assert Path('/sys/class/block/sda/removable').read_text().strip()=='1'
assert 'usb' in str(Path('/sys/class/block/sda/device').resolve())
assert source.is_file() and not source.is_symlink()
assert source.stat().st_size==SIZE
actual=digest(source)
assert actual==SHA,actual
v=os.statvfs(root.parent)
assert v.f_bavail*v.f_frsize>1024*1024*1024
print(json.dumps({'usb_mount':mounts[0],'archive_sha256':actual,'archive_bytes':SIZE,
 'destination':str(root),'destination_exists':root.exists(),'root_free_bytes':v.f_bavail*v.f_frsize}))
""",
    'deploy': """
assert source.stat().st_size==SIZE and digest(source)==SHA
root.mkdir(exist_ok=False)
archive=root/'bundle.zip'
h=hashlib.sha256()
with source.open('rb') as r,archive.open('xb') as w:
 for b in iter(lambda:r.read(1024*1024),b''):
  w.write(b);h.update(b)
 w.flush();os.fsync(w.fileno())
assert h.hexdigest()==SHA and archive.stat().st_size==SIZE
assert digest(archive)==SHA
with zipfile.ZipFile(archive) as z:
 manifest=json.loads(z.read('runtime_manifest.json'))
 assert manifest['schema_version']=='aura-board-avatar-gtk-1' and manifest['profile']=='runtime'
 records=manifest['files']
 assert len(records)==871 and len(z.namelist())==872
 assert set(z.namelist())=={r['path'] for r in records}|{'runtime_manifest.json'}
 assert sum(r['bytes'] for r in records)==219714519
 for row in records:
  rel=PurePosixPath(row['path'])
  assert not rel.is_absolute() and '..' not in rel.parts and rel.parts[0] in ('aura','deliverables')
  p=root.joinpath(*rel.parts)
  p.parent.mkdir(parents=True,exist_ok=True)
  h=hashlib.sha256();n=0
  with z.open(row['path']) as r,p.open('xb') as w:
   for b in iter(lambda:r.read(1024*1024),b''):
    w.write(b);h.update(b);n+=len(b)
   w.flush();os.fsync(w.fileno())
  assert n==row['bytes'] and h.hexdigest()==row['sha256'],row['path']
  assert p.stat().st_size==row['bytes'] and digest(p)==row['sha256'],row['path']
 with (root/'runtime_manifest.json').open('x') as f:
  json.dump(manifest,f,indent=2);f.flush();os.fsync(f.fileno())
 result={'archive_sha256':SHA,'verified_payload_files':len(records),
  'payload_readback_verified':True,'destination':str(root),'usb_used_read_only_by_this_script':True}
 with (root/'DEPLOYMENT_VERIFIED.json').open('x') as f:json.dump(result,f,indent=2)
 print(json.dumps(result))
""",
    'check': """
assert json.loads((root/'DEPLOYMENT_VERIFIED.json').read_text())['archive_sha256']==SHA
env=dict(os.environ,DISPLAY=':0')
p=subprocess.run(['python3','-B','tools/board_avatar_gtk.py','--check'],cwd=str(root/'aura'),
 env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=45,text=True)
print(p.stdout,end='')
raise SystemExit(p.returncode)
""",
    'start': """
import socket
assert json.loads((root/'DEPLOYMENT_VERIFIED.json').read_text())['archive_sha256']==SHA
assert not (root/'launch.json').exists() and not (root/'run-evidence').exists()
with socket.socket() as s:s.bind(('127.0.0.1',8783))
env=dict(os.environ,DISPLAY=':0',PYTHONUNBUFFERED='1')
args=['python3','-B',str(root/'aura/tools/board_avatar_gtk.py'),'--evidence-root',str(root/'run-evidence')]
with (root/'stage.log').open('xb') as log:
 p=subprocess.Popen(args,cwd=str(root/'aura'),env=env,stdin=subprocess.DEVNULL,stdout=log,
  stderr=subprocess.STDOUT,start_new_session=True)
info={'pid':p.pid,'args':args,'evidence':str(root/'run-evidence'),
 'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
with (root/'launch.json').open('x') as f:json.dump(info,f,indent=2)
print(json.dumps(info))
""",
    'status': """
import urllib.request
info=json.loads((root/'launch.json').read_text());pid=info['pid']
result={'launch':info,'process_alive':Path('/proc/'+str(pid)).exists(),
 'stage_log':(root/'stage.log').read_text(errors='replace')[-12000:]}
try:
 with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=4) as r:result['state']=json.load(r)
except Exception as e:result['api_error']=str(e)
if result['process_alive']:
 result['process_status']=Path('/proc/'+str(pid)+'/status').read_text()
print(json.dumps(result,ensure_ascii=False))
""",
    'save': """
import urllib.request
req=urllib.request.Request('http://127.0.0.1:8783/api/command',
 data=json.dumps({'type':'save_evidence'}).encode(),
 headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8783'})
with urllib.request.urlopen(req,timeout=8) as r:print(r.read().decode())
""",
    'fetch-report': """
p=root/'run-evidence/latest_verification.json'
assert p.stat().st_size<256*1024
print(p.read_text())
""",
    'fetch-window': """
import base64,io
from PIL import Image
files=sorted((root/'run-evidence').glob('window_*.png'))
assert files
im=Image.open(files[-1]).convert('RGB');im.thumbnail((1024,600))
b=io.BytesIO();im.save(b,format='JPEG',quality=72)
data=b.getvalue()
assert len(data)<300000
print(json.dumps({'source':str(files[-1]),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),
 'jpeg_base64':base64.b64encode(data).decode()}))
""",
    'greeting': """
import urllib.request
info=json.loads((root/'launch.json').read_text())
assert str(root/'aura/tools/board_avatar_gtk.py').encode() in Path('/proc/'+str(info['pid'])+'/cmdline').read_bytes().split(bytes([0]))
def state():
 with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=5) as r:return json.load(r)
def command(data):
 req=urllib.request.Request('http://127.0.0.1:8783/api/command',data=json.dumps(data).encode(),
  headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8783'})
 with urllib.request.urlopen(req,timeout=8) as r:return json.load(r)
samples=[];accepted=command({'type':'demo','index':0});started=time.monotonic()
while time.monotonic()-started<12:
 s=state();samples.append({k:s.get(k) for k in ('phase','state','playing','audio_time','mouth_level','blink_active','error')})
 if s.get('error'):break
 if any(x['playing'] for x in samples) and s['phase']=='IDLE' and not s['playing']:break
 time.sleep(.25)
result={'accepted':accepted,'samples':samples,'final':state(),'record':command({'type':'save_evidence'})}
with (root/'run-evidence/greeting_check.json').open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2)
print(json.dumps(result,ensure_ascii=False))
assert not result['final']['error'] and any(x['playing'] for x in samples)
assert any(x['playing'] and x['mouth_level']>.1 for x in samples)
assert result['final']['phase']=='IDLE' and not result['final']['playing']
""",
    'repair-pillow': """
import signal
p=root/'aura/board/interaction/avatar_player.py';before=p.read_bytes()
assert hashlib.sha256(before).hexdigest()=='05f5be5e14888e61dccfec8fa088df35ad0497392fdf371f7d619c24816f4759'
after=before.replace(b'Image.Transform.AFFINE',b'getattr(Image, "Transform", Image).AFFINE')
after=after.replace(b'Image.Resampling.BILINEAR',b'getattr(Image, "Resampling", Image).BILINEAR')
assert hashlib.sha256(after).hexdigest()=='65993e32e7d59893f1906506d224c4c577dd7e6c17801b2213678c82a2f16e39'
info=json.loads((root/'launch.json').read_text());pid=info['pid']
assert info['boot_id']==Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert str(root/'aura/tools/board_avatar_gtk.py').encode() in Path('/proc/'+str(pid)+'/cmdline').read_bytes().split(bytes([0]))
backup=root/'patch-backup-pillow';backup.mkdir(exist_ok=False)
with (backup/'avatar_player.py').open('xb') as f:f.write(before);f.flush();os.fsync(f.fileno())
os.kill(pid,signal.SIGTERM)
deadline=time.monotonic()+5
while Path('/proc/'+str(pid)+'/stat').exists() and time.monotonic()<deadline:
 if Path('/proc/'+str(pid)+'/stat').read_text().split(') ')[1].startswith('Z '):break
 time.sleep(.1)
assert not Path('/proc/'+str(pid)+'/stat').exists() or Path('/proc/'+str(pid)+'/stat').read_text().split(') ')[1].startswith('Z ')
tmp=p.with_name('avatar_player.py.pillow-new')
with tmp.open('xb') as f:f.write(after);f.flush();os.fsync(f.fileno())
assert digest(p)==hashlib.sha256(before).hexdigest()
os.replace(str(tmp),str(p));assert digest(p)==hashlib.sha256(after).hexdigest()
for name in ['launch.json','stage.log','run-evidence']:(root/name).rename(backup/name)
result={'file':str(p),'before_sha256':hashlib.sha256(before).hexdigest(),
 'after_sha256':digest(p),'backup':str(backup),'stopped_only_owned_pid':pid}
with (root/'PILLOW_PATCH.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
""",
    'audio-controls': """
import urllib.request
info=json.loads((root/'launch.json').read_text())
assert str(root/'aura/tools/board_avatar_gtk.py').encode() in Path('/proc/'+str(info['pid'])+'/cmdline').read_bytes().split(bytes([0]))
samples=[];checks={};result={'complete':False,'checks':checks,'samples':samples}
def command(data):
 req=urllib.request.Request('http://127.0.0.1:8783/api/command',data=json.dumps(data).encode(),
  headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8783'})
 with urllib.request.urlopen(req,timeout=8) as r:return json.load(r)
def state():
 with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=5) as r:s=json.load(r)
 row={k:s.get(k) for k in ('phase','state','playing','paused','audio_time','visual_time','mouth_level','blink_active','error','generation','audio_output_state')}
 try:row['alsa_pcm_status']=Path('/proc/asound/MCP01/pcm0p/sub0/status').read_text()
 except OSError:pass
 samples.append(row)
 assert not s.get('error'),s.get('error')
 return s
def until(predicate,timeout):
 deadline=time.monotonic()+timeout
 while time.monotonic()<deadline:
  s=state()
  if predicate(s):return s
  time.sleep(.15)
 raise RuntimeError('Playback state deadline exceeded')
try:
 for index,name in [(1,'happy'),(2,'gentle'),(3,'long')]:
  assert command({'type':'demo','index':index})['ok']
  playing=until(lambda s:s['playing'],20)
  ended=until(lambda s:s['phase']=='IDLE' and not s['playing'],25)
  checks[name+'_eos']={'duration':ended['duration'],'audio_time':ended['audio_time'],'passed':True}
 assert command({'type':'demo','index':3})['ok']
 until(lambda s:s['playing'] and s['audio_time']>.5,20)
 command({'type':'pause'});until(lambda s:s['paused'],5);time.sleep(.4);p1=state()
 time.sleep(.7);p2=state();delta=abs(p2['audio_time']-p1['audio_time'])
 assert delta<.02 and p1['visual_time']==p2['visual_time'],(p1,p2)
 checks['pause_frozen']={'audio_delta_seconds':delta,'passed':True}
 command({'type':'pause'});until(lambda s:not s['paused'] and s['audio_time']>p2['audio_time']+.2,5)
 checks['resume']={'passed':True}
 before=state()['generation'];command({'type':'event','event':'cancel'})
 stopped=until(lambda s:s['phase']=='IDLE' and not s['playing'] and not s['paused'] and s['mouth_level']<.03,5)
 time.sleep(.7);late=state();assert not late['playing'] and late['generation']>before
 checks['cancel_and_no_late_restart']={'passed':True,'generation':late['generation']}
 assert any('state: RUNNING' in s.get('alsa_pcm_status','') for s in samples)
 checks['real_MCP01_PCM_running']={'passed':True}
 result['complete']=True
except Exception as e:result['error']=type(e).__name__+': '+str(e)
finally:
 if not result['complete']:
  try:command({'type':'event','event':'cancel'})
  except Exception:pass
 try:result['record']=command({'type':'save_evidence'})
 except Exception as e:result['save_error']=str(e)
 with (root/('run-evidence/controls_'+str(time.time_ns())+'.json')).open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2)
print(json.dumps({k:v for k,v in result.items() if k!='samples'},ensure_ascii=False))
assert result['complete'],result.get('error')
""",
    'performance-probe': """
import io,sys,statistics
sys.path.insert(0,str(root/'aura'))
from PIL import Image
from board.interaction.avatar_player import AvatarPlayer
from board.interaction.avatar_timing import idle_offsets
from tools.pillow_compat import LANCZOS
im=Image.open(root/'aura/assets/avatar/idle_normal/000000.png').convert('RGBA')
rgb=im.convert('RGB');other=im.copy();off=idle_offsets(2.5)
def measure(fn):
 rows=[]
 for i in range(8):
  t=time.perf_counter();fn();rows.append((time.perf_counter()-t)*1000)
 return {'median_ms':statistics.median(rows),'max_ms':max(rows)}
def jpeg():
 b=io.BytesIO();rgb.save(b,format='JPEG',quality=85)
ops={'affine':measure(lambda:AvatarPlayer._apply_offsets(im,off)),
 'blend':measure(lambda:Image.blend(im,other,.5)),
 'alpha':measure(lambda:Image.alpha_composite(im,other)),
 'resize':measure(lambda:rgb.resize((423,438),LANCZOS)),'jpeg':measure(jpeg)}
paths=['/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq','/sys/class/thermal/thermal_zone0/temp','/proc/loadavg']
readings={p:Path(p).read_text().strip() for p in paths if Path(p).exists()}
def cpu():
 result={}
 for pid in [json.loads((root/'launch.json').read_text())['pid'],16981,1097]:
  try:
   v=Path('/proc/'+str(pid)+'/stat').read_text().split(') ')[1].split();result[str(pid)]=int(v[11])+int(v[12])
  except OSError:pass
 return result
a=cpu();time.sleep(2);b=cpu();hz=os.sysconf('SC_CLK_TCK')
usage={p:(b[p]-a[p])/hz/2*100 for p in a if p in b}
print(json.dumps({'image_operations':ops,'system':readings,'cpu_percent_two_seconds':usage}))
""",
    'display-probe': """
import shutil
env=dict(os.environ,DISPLAY=':0')
result={}
for args in [['xset','q'],['xwininfo','-root','-tree'],['xprop','-root','_NET_ACTIVE_WINDOW','_NET_CLIENT_LIST_STACKING']]:
 if shutil.which(args[0]):
  p=subprocess.run(args,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=8,text=True)
  result[' '.join(args)]={'exit_code':p.returncode,'output':p.stdout[:18000]}
print(json.dumps(result))
""",
    'wake-display': """
env=dict(os.environ,DISPLAY=':0')
result=[]
for args in [['xset','s','reset'],['xset','dpms','force','on'],['xset','q']]:
 p=subprocess.run(args,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=5,text=True)
 result.append({'args':args,'exit_code':p.returncode,'output':p.stdout})
 assert p.returncode==0,p.stdout
print(json.dumps(result))
""",
    'repair-refresh': """
import signal
p=root/'aura/tools/board_avatar_gtk.py';before=p.read_bytes()
assert hashlib.sha256(before).hexdigest()=='b16234947d5798d5a49ebd016d3448038d38cf1a7593bc42b65581452dd4974a'
old=b"            self.timer = self.GLib.timeout_add(int(config['tick_ms']), self.tick)"+bytes([10])
new=bytes([10]).join([b"            # Slow ARM frames must yield to GTK's higher-priority redraw source.",
 b"            self.timer = self.GLib.timeout_add(int(config['tick_ms']), self.tick,",
 b"                                             priority=self.GLib.PRIORITY_DEFAULT_IDLE)",b''])
after=before.replace(old,new)
assert hashlib.sha256(after).hexdigest()=='d49b9ea86f0a8ff9be87e23cdca28bd5e5313b099fc504e57e566ccc387ff86c'
info=json.loads((root/'launch.json').read_text());pid=info['pid']
assert info['boot_id']==Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert str(p).encode() in Path('/proc/'+str(pid)+'/cmdline').read_bytes().split(bytes([0]))
backup=root/'patch-backup-refresh';backup.mkdir(exist_ok=False)
with (backup/'board_avatar_gtk.py').open('xb') as f:f.write(before);f.flush();os.fsync(f.fileno())
os.kill(pid,signal.SIGTERM);deadline=time.monotonic()+5
while Path('/proc/'+str(pid)+'/stat').exists() and time.monotonic()<deadline:
 if Path('/proc/'+str(pid)+'/stat').read_text().split(') ')[1].startswith('Z '):break
 time.sleep(.1)
assert not Path('/proc/'+str(pid)+'/stat').exists() or Path('/proc/'+str(pid)+'/stat').read_text().split(') ')[1].startswith('Z ')
tmp=p.with_name('board_avatar_gtk.py.refresh-new')
with tmp.open('xb') as f:f.write(after);f.flush();os.fsync(f.fileno())
assert digest(p)==hashlib.sha256(before).hexdigest()
os.replace(str(tmp),str(p));assert digest(p)==hashlib.sha256(after).hexdigest()
for name in ['launch.json','stage.log','run-evidence']:(root/name).rename(backup/name)
result={'file':str(p),'before_sha256':hashlib.sha256(before).hexdigest(),
 'after_sha256':digest(p),'backup':str(backup),'stopped_only_owned_pid':pid}
with (root/'REFRESH_PATCH.json').open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
""",
    'screen-capture': """
import base64,io,shutil
os.environ['DISPLAY']=':0'
import gi
gi.require_version('Gdk','3.0')
from gi.repository import Gdk
from PIL import Image
active=subprocess.run(['xprop','-root','_NET_ACTIVE_WINDOW'],stdout=subprocess.PIPE,text=True).stdout
props={}
for line in subprocess.run(['xprop','-root','_NET_CLIENT_LIST_STACKING'],stdout=subprocess.PIPE,text=True).stdout.splitlines():
 if '# ' in line:
  for xid in line.split('# ')[1].split(', '):
   p=subprocess.run(['xprop','-id',xid.strip(),'_NET_WM_PID','WM_CLASS','_NET_WM_NAME','WM_STATE','_NET_WM_STATE'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
   props[xid]=p.stdout
screen=Gdk.get_default_root_window()
pix=Gdk.pixbuf_get_from_window(screen,0,0,screen.get_width(),screen.get_height())
im=Image.frombytes('RGB' if not pix.get_has_alpha() else 'RGBA',(pix.get_width(),pix.get_height()),bytes(pix.get_pixels()),'raw','RGB' if not pix.get_has_alpha() else 'RGBA',pix.get_rowstride()).convert('RGB')
b=io.BytesIO();im.save(b,format='JPEG',quality=72);data=b.getvalue()
frames=sorted((root/'run-evidence').glob('frame_*.png'))
result={'active_window':active,'window_properties':props,'root_extrema':im.getextrema(),
 'source_frame_extrema':Image.open(frames[-1]).getextrema() if frames else None,
 'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'jpeg_base64':base64.b64encode(data).decode()}
print(json.dumps(result,ensure_ascii=False))
""",
    'raise-avatar': """
import ctypes as C,ctypes.util,re
env=dict(os.environ,DISPLAY=':0');info=json.loads((root/'launch.json').read_text());pid=info['pid']
assert str(root/'aura/tools/board_avatar_gtk.py').encode() in Path('/proc/'+str(pid)+'/cmdline').read_bytes().split(bytes([0]))
output=subprocess.check_output(['xprop','-root','_NET_CLIENT_LIST_STACKING'],env=env,text=True)
owned=[]
for xid in re.findall(r'0x[0-9a-fA-F]+',output):
 p=subprocess.run(['xprop','-id',xid,'_NET_WM_PID'],env=env,stdout=subprocess.PIPE,text=True)
 if re.search(r'= '+str(pid)+r'\s*$',p.stdout):owned.append(int(xid,16))
assert len(owned)==1,owned
x=C.CDLL(ctypes.util.find_library('X11'));P=C.c_void_p;U=C.c_ulong;I=C.c_int
x.XOpenDisplay.argtypes=[C.c_char_p];x.XOpenDisplay.restype=P
x.XDefaultRootWindow.argtypes=[P];x.XDefaultRootWindow.restype=U
x.XQueryTree.argtypes=[P,U,C.POINTER(U),C.POINTER(U),C.POINTER(C.POINTER(U)),C.POINTER(C.c_uint)];x.XQueryTree.restype=I
x.XFree.argtypes=[P];x.XFree.restype=I
x.XRaiseWindow.argtypes=[P,U];x.XRaiseWindow.restype=I
x.XSync.argtypes=[P,I];x.XCloseDisplay.argtypes=[P]
d=x.XOpenDisplay(b':0');assert d
try:
 screen=x.XDefaultRootWindow(d);target=owned[0];ancestors=[target]
 for i in range(8):
  r=U();parent=U();children=C.POINTER(U)();n=C.c_uint()
  assert x.XQueryTree(d,target,C.byref(r),C.byref(parent),C.byref(children),C.byref(n))
  if children:x.XFree(C.cast(children,P))
  if parent.value==screen:break
  assert parent.value not in (0,target);target=parent.value;ancestors.append(target)
 else:raise RuntimeError('Unexpected window ancestry')
 assert target!=screen
 x.XRaiseWindow(d,target);x.XSync(d,0)
 print(json.dumps({'owned_avatar_pid':pid,'avatar_window':hex(owned[0]),
  'raised_owned_ancestor':hex(target),'ancestor_chain':[hex(v) for v in ancestors],
  'vision_process_still_present':Path('/proc/16981').exists(),'no_process_stopped':True}))
finally:x.XCloseDisplay(d)
""",
    'unmount-usb': """
assert digest(root/'bundle.zip')==SHA
mounts=[line for line in Path('/proc/self/mountinfo').read_text().splitlines() if line.split()[4]==str(usb)]
assert len(mounts)==1 and ' - vfat /dev/sda1 ' in mounts[0],mounts
assert Path('/sys/class/block/sda/removable').read_text().strip()=='1'
p=subprocess.run(['umount',str(usb)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=10,text=True)
assert p.returncode==0,p.stdout
assert not any(line.split()[4]==str(usb) for line in Path('/proc/self/mountinfo').read_text().splitlines())
print(json.dumps({'usb_safely_unmounted':True,'device':'/dev/sda1','mountpoint':str(usb),
 'runtime_archive_still_present':True,'archive_sha256':SHA}))
""",
    'volume-read': """
p=subprocess.run(['amixer','-c','MCP01','scontents'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=5,text=True)
print(p.stdout,end='');raise SystemExit(p.returncode)
""",
    'volume-max': """
def mixer(*args):
 p=subprocess.run(['amixer','-c','MCP01']+list(args),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=5,text=True)
 assert p.returncode==0,p.stdout
 return p.stdout
before=mixer('sget','PCM');mic_before=mixer('sget','Mic')
changed=mixer('sset','PCM','100%','unmute');after=mixer('sget','PCM')
assert '[100%]' in after and '[on]' in after,after
assert mixer('sget','Mic')==mic_before
result={'requested_by_user':'MAXIMUM','card':'MCP01','control':'PCM','before':before,
 'after':after,'readback_verified':True,'microphone_unchanged':True}
with (root/('VOLUME_MAX_'+str(time.time_ns())+'.json')).open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result))
""",
    'touch-input': """
import shutil
inputs=[]
for event in sorted(Path('/sys/class/input').glob('event*')):
 d=event/'device';row={'event':event.name,'device_path':str(d.resolve())}
 for field in ['name','properties','capabilities/ev','capabilities/abs','capabilities/key']:
  try:row[field]=str((d/field).read_text().strip())
  except OSError:pass
 inputs.append(row)
result={'input_devices':inputs,'x11':{},'usb_devices':None}
env=dict(os.environ,DISPLAY=':0')
for args in [['xinput','list','--short'],['xrandr','--current'],['lsusb']]:
 if shutil.which(args[0]):
  p=subprocess.run(args,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=6,text=True)
  result['x11' if args[0]!='lsusb' else 'usb_devices'] = result['x11'] if args[0]!='lsusb' else {'exit_code':p.returncode,'output':p.stdout}
  if args[0]!='lsusb':result['x11'][args[0]]={'exit_code':p.returncode,'output':p.stdout}
print(json.dumps(result,ensure_ascii=False))
""",
    'ui-settings-check': """
import ctypes as C,ctypes.util,urllib.request
checks={}
def state():
 with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=5) as r:return json.load(r)
def command(data):
 req=urllib.request.Request('http://127.0.0.1:8783/api/command',data=json.dumps(data).encode(),headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8783'})
 with urllib.request.urlopen(req,timeout=8) as r:return json.load(r)
def until(predicate):
 end=time.monotonic()+7
 while time.monotonic()<end:
  s=state()
  if predicate(s):return s
  time.sleep(.15)
 raise RuntimeError('UI state deadline exceeded: '+str(state()))
P=C.c_void_p;I=C.c_int;U=C.c_ulong
x=C.CDLL(ctypes.util.find_library('X11'));xt=C.CDLL(ctypes.util.find_library('Xtst'))
x.XOpenDisplay.argtypes=[C.c_char_p];x.XOpenDisplay.restype=P;x.XFlush.argtypes=[P];x.XCloseDisplay.argtypes=[P]
xt.XTestFakeMotionEvent.argtypes=[P,I,I,I,U];xt.XTestFakeButtonEvent.argtypes=[P,C.c_uint,I,U]
d=x.XOpenDisplay(b':0');assert d
def move(a,b):xt.XTestFakeMotionEvent(d,0,a,b,0);x.XFlush(d)
def button(down):xt.XTestFakeButtonEvent(d,1,int(down),0);x.XFlush(d)
def click(a,b):move(a,b);button(True);time.sleep(.05);button(False);time.sleep(.4)
def settled(s):return not s['ui_settings']['pending'] and s['ui_settings']['available']
mic=subprocess.check_output(['amixer','-c','MCP01','sget','Mic'],text=True)
result={'complete':False,'input_method':'XTEST_POINTER_NOT_PHYSICAL_TOUCH','checks':checks}
try:
 click(430,80);until(lambda s:s.get('ui_page')=='settings');checks['settings_tab']=True
 click(40,188);until(lambda s:settled(s) and abs(s['ui_settings']['volume']-90)<=1);checks['volume_minus']=True
 click(545,188);until(lambda s:settled(s) and s['ui_settings']['volume']==100);checks['volume_plus']=True
 click(280,260);until(lambda s:settled(s) and s['ui_settings']['muted']);checks['mute']=True
 click(280,260);until(lambda s:settled(s) and not s['ui_settings']['muted']);checks['unmute']=True
 move(478,188);button(True)
 try:
  for a in [440,400,360,320,280]:move(a,188);time.sleep(.08)
 finally:button(False)
 s=until(lambda s:settled(s) and 30<=s['ui_settings']['volume']<=70)
 checks['slider_drag_volume']=s['ui_settings']['volume']
 click(430,368);until(lambda s:s['ui_settings']['economy']);checks['economy_toggle']=True
 click(140,368);until(lambda s:not s['ui_settings']['fullscreen']);checks['fullscreen_exit']=True
 command({'type':'ui_settings','values':{'fullscreen':True}});until(lambda s:s['ui_settings']['fullscreen'])
 time.sleep(.5);click(280,508)
 until(lambda s:settled(s) and s['ui_settings']['volume']==100 and not s['ui_settings']['muted'] and not s['ui_settings']['economy'])
 saved=json.loads((root/'avatar_user_settings.json').read_text())['values']
 assert saved=={'volume':100,'muted':False,'fullscreen':True,'economy':False},saved
 checks['restore_and_persist']=saved
 assert subprocess.check_output(['amixer','-c','MCP01','sget','Mic'],text=True)==mic
 checks['microphone_unchanged']=True
 result['complete']=True
except Exception as e:result['error']=type(e).__name__+': '+str(e)
finally:
 button(False);x.XCloseDisplay(d)
 command({'type':'ui_settings','values':{'volume':100,'muted':False,'fullscreen':True,'economy':False}})
 command({'type':'ui_page','page':'settings'})
 result['record']=command({'type':'save_evidence'})
 with (root/('run-evidence/settings_check_'+str(time.time_ns())+'.json')).open('x') as f:json.dump(result,f,indent=2)
print(json.dumps(result,ensure_ascii=False));assert result['complete'],result.get('error')
""",
    'ui-pointer-playback': """
import ctypes as C,ctypes.util,urllib.request
def get():
 with urllib.request.urlopen('http://127.0.0.1:8783/api/state',timeout=5) as r:return json.load(r)
def send(data):
 req=urllib.request.Request('http://127.0.0.1:8783/api/command',data=json.dumps(data).encode(),headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8783'})
 with urllib.request.urlopen(req,timeout=8) as r:return json.load(r)
def until(predicate):
 end=time.monotonic()+8
 while time.monotonic()<end:
  s=get()
  if predicate(s):return s
  time.sleep(.15)
 raise RuntimeError('Pointer playback deadline exceeded')
P=C.c_void_p;I=C.c_int;U=C.c_ulong
x=C.CDLL(ctypes.util.find_library('X11'));xt=C.CDLL(ctypes.util.find_library('Xtst'))
x.XOpenDisplay.argtypes=[C.c_char_p];x.XOpenDisplay.restype=P;x.XFlush.argtypes=[P];x.XCloseDisplay.argtypes=[P]
xt.XTestFakeMotionEvent.argtypes=[P,I,I,I,U];xt.XTestFakeButtonEvent.argtypes=[P,C.c_uint,I,U]
d=x.XOpenDisplay(b':0');assert d
def click(a,b):
 xt.XTestFakeMotionEvent(d,0,a,b,0);xt.XTestFakeButtonEvent(d,1,1,0);x.XFlush(d);time.sleep(.05)
 xt.XTestFakeButtonEvent(d,1,0,0);x.XFlush(d);time.sleep(.4)
result={'complete':False,'input_method':'XTEST_POINTER_NOT_PHYSICAL_TOUCH'}
try:
 click(150,80);until(lambda s:s['ui_page']=='main')
 click(150,264);until(lambda s:s['playing'] and s['audio_time']>.4)
 click(150,420);until(lambda s:s['paused']);a=get()['audio_time'];time.sleep(.5);b=get()['audio_time'];assert abs(a-b)<.02
 click(150,420);until(lambda s:not s['paused'] and s['audio_time']>b+.1)
 click(430,420);until(lambda s:s['phase']=='IDLE' and not s['playing'])
 click(430,80);until(lambda s:s['ui_page']=='settings')
 result.update(complete=True,play=True,pause_frozen_seconds=abs(a-b),resume=True,cancel=True)
except Exception as e:result['error']=type(e).__name__+': '+str(e)
finally:
 x.XCloseDisplay(d);send({'type':'event','event':'cancel'});send({'type':'ui_page','page':'settings'})
 result['record']=send({'type':'save_evidence'})
print(json.dumps(result));assert result['complete'],result.get('error')
""",
}


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def command_for(source, phase=None):
    if phase in ('audio-controls','ui-settings-check','ui-pointer-playback'):
        prelude='import hashlib,json,os,subprocess,time\nfrom pathlib import Path\nroot=Path('+repr(DEST)+')\n'
    else:
        prelude='DEST='+repr(DEST)+'\nUSB='+repr(USB)+'\nNAME='+repr(NAME)+'\nSHA='+repr(SHA)+'\nSIZE='+str(SIZE)+'\n'+textwrap.dedent(PRELUDE).strip()+'\n'
    source = prelude+textwrap.dedent(source).strip()+'\n'
    ast.parse(source)
    blob=base64.b64encode(gzip.compress(source.encode(),mtime=0)).decode()
    code='import base64,gzip;exec(gzip.decompress(base64.b64decode('+repr(blob)+')))'
    command='python3 -B -c '+shlex.quote(code)
    if len(base64.b64encode(command.encode()))+900>3800:
        raise ValueError('UART phase too long')
    return command


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--phase',choices=tuple(PHASES),default='inspect')
    parser.add_argument('--validate',action='store_true')
    args=parser.parse_args()
    commands={name:command_for(source,name) for name,source in PHASES.items()}
    if args.validate:
        print(json.dumps({'phases':list(commands),'destination':DEST,'board_accessed':False}))
        return 0
    spec=importlib.util.spec_from_file_location('reviewed_uart',str(TRANSPORT))
    transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)
    out=ROOT/'evidence'/datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-usb-runtime-'+args.phase)
    out.mkdir(parents=True)
    status={'started_utc':utc(),'phase':args.phase,'destination':DEST,'complete':False,
            'archive_sha256':SHA,'command':commands[args.phase]}
    (out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    uart=None
    with (out/'serial.raw').open('xb') as raw:
        try:
            uart=transport.UART(raw);uart.connect()
            print(json.dumps({'phase':args.phase,'root_shell_confirmed':True,'evidence':str(out)}),flush=True)
            rc,data,sha=uart.command(commands[args.phase],'UR001',180 if args.phase in ('deploy','audio-controls') else 60)
            (out/'response.output').write_bytes(data)
            status.update(exit_code=rc,bytes=len(data),response_sha256=sha,complete=rc==0)
            if args.phase in ('fetch-window','screen-capture') and rc==0:
                result=json.loads(data);jpeg=base64.b64decode(result.pop('jpeg_base64'))
                assert len(jpeg)==result['bytes'] and hashlib.sha256(jpeg).hexdigest()==result['sha256']
                (out/'board-window.jpg').write_bytes(jpeg)
                print(json.dumps(result),flush=True)
            else:
                print(data.decode(errors='replace')[:18000],flush=True)
        except Exception as exc:
            status['error']=type(exc).__name__+': '+str(exc)
            print(json.dumps({'error':status['error']}),flush=True)
        finally:
            if uart is not None:
                try:status['console_echo_restored']=uart.close()
                except Exception as exc:status['console_close_error']=str(exc)
    status['finished_utc']=utc()
    (out/'status.json').write_text(json.dumps(status,indent=2)+'\n')
    print(json.dumps({k:v for k,v in status.items() if k!='command'},ensure_ascii=False),flush=True)
    return 0 if status['complete'] and status.get('console_echo_restored') else 1


if __name__=='__main__':
    sys.exit(main())
