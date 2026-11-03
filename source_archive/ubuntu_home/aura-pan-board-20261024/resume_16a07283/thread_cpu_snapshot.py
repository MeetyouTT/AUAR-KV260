import json,time,urllib.request,subprocess,os
from pathlib import Path
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with o.open('http://127.0.0.1:8790/health',timeout=3) as f:h=json.load(f)
camera=h['pid'];gui=int(subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True))
hz=os.sysconf('SC_CLK_TCK')
def snapshot(pid):
 out={}
 for p in (Path('/proc')/str(pid)/'task').iterdir():
  try:
   raw=(p/'stat').read_text();tail=raw.rsplit(')',1)[1].split();sched=[int(x) for x in (p/'schedstat').read_text().split()]
   out[int(p.name)]=dict(name=raw.split('(',1)[1].rsplit(')',1)[0],cpu_ticks=int(tail[11])+int(tail[12]),
    birth=int(tail[19]),run_ns=sched[0],wait_ns=sched[1],slices=sched[2])
  except (OSError,ValueError):pass
 return out
before={p:snapshot(p) for p in (camera,gui)};start=time.monotonic();time.sleep(5);elapsed=time.monotonic()-start
rows=[]
for pid in (camera,gui):
 for tid,v in snapshot(pid).items():
  a=before[pid].get(tid)
  if a and a['birth']==v['birth']:
   rows.append(dict(pid=pid,tid=tid,name=v['name'],cpu_percent_one_core=round((v['cpu_ticks']-a['cpu_ticks'])/hz/elapsed*100,2),
     scheduled_run_ms=round((v['run_ns']-a['run_ns'])/1e6,3),runnable_wait_ms=round((v['wait_ns']-a['wait_ns'])/1e6,3),
     schedule_slices=v['slices']-a['slices']))
rows.sort(key=lambda v:v['cpu_percent_one_core'],reverse=True)
with o.open('http://127.0.0.1:8790/health',timeout=3) as f:end=json.load(f)
print(json.dumps(dict(duration_s=round(elapsed,3),camera_pid=camera,gui_pid=gui,threads=rows[:40],
 pipeline_metrics=end.get('pipeline_metrics'),health_keys=list(end),primary_overruns=end['dpu_schedule']['primary_period_overruns'],
 optional_overruns={k:end['dpu_schedule']['optional'][k]['overruns'] for k in ('yunet','sface')},
 scope='per-thread CPU and scheduler runnable delay; not GIL or DPU execution timing',actuator_commands=0)))
