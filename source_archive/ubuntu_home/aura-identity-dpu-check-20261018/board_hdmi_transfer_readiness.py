"""Check a single scoped host artifact endpoint without downloading a kernel."""
import json,urllib.request,time,subprocess
from pathlib import Path
v={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'files_modified':0}
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
start=time.monotonic()
try:
 with opener.open('http://172.23.232.155:17643/ready.txt',timeout=4) as r:
  v['status']=r.status;v['body_valid']=r.read(100)==b'AURA HDMI candidate transfer readiness\n'
except Exception as e:v['error']=type(e).__name__+': '+str(e)
v['elapsed_seconds']=round(time.monotonic()-start,3)
v['route']=subprocess.run(['ip','route','get','172.23.232.155'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=2).stdout.strip()
print(json.dumps(v),flush=True)
