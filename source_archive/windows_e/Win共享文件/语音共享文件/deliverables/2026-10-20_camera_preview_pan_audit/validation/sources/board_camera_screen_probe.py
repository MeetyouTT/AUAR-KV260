"""Private live screen plus process CPU deltas; no hardware writes."""
import base64,gzip,hashlib,importlib.util,json,os,subprocess,time
from pathlib import Path
root=Path('/home/root/aura-voice-barge-in-20261020/candidate-667b70d586ca/runtime/aura')
def stats():
 out={}
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   raw=(p/'stat').read_text();tail=raw[raw.rfind(')')+2:].split();cmd=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
   if not cmd:continue
   out[p.name]={'ticks':int(tail[11])+int(tail[12]),'state':tail[0],'rss_kb':int(tail[21])*4,'threads':int(tail[17]),'cmd':cmd}
  except (OSError,ValueError):pass
 return out
a=stats();start=time.monotonic();time.sleep(2);b=stats();elapsed=time.monotonic()-start
rows=[]
for pid,val in b.items():
 if pid not in a:continue
 cpu=(val['ticks']-a[pid]['ticks'])/os.sysconf('SC_CLK_TCK')/elapsed*100
 if cpu>1 or 'aura' in val['cmd']:rows.append(dict(pid=pid,cpu=round(cpu,2),**val))
spec=importlib.util.spec_from_file_location('capture',str(root/'tools/board_screen_capture.py'));module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
dest=Path('/tmp/aura-camera-audit-private-screen.png');size=module.capture(dest)
from PIL import Image
with Image.open(str(dest)) as im:
 im.thumbnail((1024,600));im.save(str(dest),format='PNG',optimize=True)
data=dest.read_bytes();art={'screen-private.png':{'base64':base64.b64encode(data).decode(),'sha256':hashlib.sha256(data).hexdigest()}}
owners={}
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 for f in (p/'fd').glob('*'):
  try:
   target=os.readlink(str(f))
   if target.startswith('/dev/video') or target=='/run/aura-vsrv.lock':owners.setdefault(p.name,[]).append(target)
  except OSError:pass
kernel=subprocess.check_output(['dmesg'],text=True)
issues=[s for s in kernel.splitlines() if any(t in s.lower() for t in ['uvc','usb 1-','out of memory','oom-kill','segfault','drm','underflow'])][-50:]
print(json.dumps({'screen_size':size,'processes':sorted(rows,key=lambda x:-x['cpu']),'device_owners':owners,'kernel_relevant':issues,'artifacts':art}),flush=True)
