import collections,hashlib,json,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283');out=[]
for name in ('init1448-to1445.json','observed-20us-current.json'):
 p=R/name;t=json.loads(p.read_text());events=t['events'];summary=[];last=None
 for e in events:
  key=(e['target_us'],e['width_us'])
  if key!=last:summary.append(e);last=key
 out.append(dict(file=name,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),status=t['status'],
  events=len(events),target_us=sorted({e['target_us'] for e in events}),width_us=sorted({e['width_us'] for e in events}),
  transitions=summary,stopped=t['result']['stopped'],physical_motion_verified=t['physical_motion_verified']))
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with o.open('http://127.0.0.1:8790/health',timeout=3) as r:h=json.load(r)
print(json.dumps({'trials':out,'camera_pid':h['pid'],'identity_ready':h['identity']['ready'],
 'primary_overruns':h['dpu_schedule']['primary_period_overruns'],'optional_overruns':{k:h['dpu_schedule']['optional'][k]['overruns'] for k in ('yunet','sface')},
 'motion_commands_sent':0,'MMIO_opened':False}))
