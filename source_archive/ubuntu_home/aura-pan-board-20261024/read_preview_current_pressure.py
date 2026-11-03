"""Measure current USB warning rate and live preview source freshness."""
import json,os,time,urllib.request
from pathlib import Path
fd=os.open('/dev/kmsg',os.O_RDONLY|os.O_NONBLOCK);os.lseek(fd,0,os.SEEK_END);start=time.monotonic();count=0
try:
 while time.monotonic()-start<.3:
  try:
   if b"couldn't access mem fast enough" in os.read(fd,8192):count+=1
  except BlockingIOError:time.sleep(.002)
  except OSError:pass
finally:os.close(fd)
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
h=get(8790,'/health');u=get(8783,'/api/state');v=u['ui_runtime'];snap=v.get('snapshot') or {};camera=snap.get('modules',{}).get('camera')
print(json.dumps({'usb_warnings_300ms':count,'camera':{k:h.get(k) for k in ('pid','capture_age_ms','observation_age_ms','camera_error','preview_error','preview_hz')},
 'camera_module':camera,'preview':v.get('preview_metrics'),'manual':u['manual_pan'],'load':Path('/proc/loadavg').read_text().strip()}))
