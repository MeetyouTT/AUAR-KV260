import json,subprocess,shutil,os
from pathlib import Path
out={}
root=Path('/sys/kernel/debug/usb/xhci')
out['xhci_debug_paths']=[str(p) for p in root.glob('*/*')][:35] if root.exists() else []
for name in ('/proc/asound/pcm','/proc/asound/cards'):
 p=Path(name)
 if p.exists():out[name]=p.read_text()
out['pcm_running']=[]
for p in Path('/proc/asound').glob('card*/pcm*/sub*/status'):
 try:out['pcm_running'].append(dict(path=str(p),status=p.read_text()[:800]))
 except OSError:pass
out['device_endpoints']=[]
for p in Path('/sys/bus/usb/devices/1-1.3').glob('*:*/ep_*'):
 row={'path':str(p)}
 for n in ('bEndpointAddress','bmAttributes','wMaxPacketSize','interval','type','direction'):
  q=p/n
  if q.exists():row[n]=q.read_text().strip()
 out['device_endpoints'].append(row)
if shutil.which('v4l2-ctl'):
 p=subprocess.run(['v4l2-ctl','--device','/dev/video0','--list-formats-ext'],capture_output=True,text=True,timeout=4)
 out['supported_formats']=p.stdout[:7500]
out['video_open_pids']=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  matches=[]
  for f in (p/'fd').iterdir():
   try:
    link=os.readlink(f)
    if link.startswith('/dev/video'):matches.append(link)
   except OSError:pass
  if matches:out['video_open_pids'].append({'pid':int(p.name),'devices':matches})
 except OSError:pass
print(json.dumps(out))
