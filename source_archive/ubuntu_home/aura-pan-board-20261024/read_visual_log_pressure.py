"""Inspect logging pressure and preview visibility; no configuration changes."""
import json,subprocess,time,urllib.request
from pathlib import Path
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
logs={}
for p in (Path('/var/log/messages'),Path('/var/log/syslog'),Path('/var/log/kern.log')):
 if p.is_file():
  size=p.stat().st_size
  with p.open('rb') as f:f.seek(max(0,size-12000));tail=f.read().decode(errors='replace')
  logs[str(p)]={'bytes':size,'tail':tail[-9000:]}
d=subprocess.run(['dmesg','--level','emerg,alert,crit,err,warn'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
samples=[]
for _ in range(30):
 with o.open('http://127.0.0.1:8783/api/state',timeout=3) as r:u=json.load(r)
 v=u['ui_runtime'];x=v.get('preview_metrics') or {};ref=x.get('frame_reference')
 samples.append({'mono':int(time.monotonic()*1000),'visible':x.get('frame_visible'),'frame_id':ref.get('frame_id') if ref else None,
 'age':int(time.monotonic()*1000)-ref['captured_mono_ms'] if ref else None,'hz':x.get('update_hz'),'link':v['link'],'error':x.get('error')})
 time.sleep(.1)
print(json.dumps({'logs':logs,'kernel_tail':d.stdout[-7000:],'samples':samples,'register_writes':0}))
