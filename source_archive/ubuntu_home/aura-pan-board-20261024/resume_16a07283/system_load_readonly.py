import json,os,subprocess,time
from pathlib import Path
def sample():
 result={}
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   raw=(p/'stat').read_text();v=raw.rsplit(')',1)[1].split()
   result[int(p.name)]=dict(name=raw.split('(',1)[1].rsplit(')',1)[0],ticks=int(v[11])+int(v[12]),birth=int(v[19]))
  except (OSError,ValueError):pass
 return result
begin=sample();start=time.monotonic();time.sleep(3);elapsed=time.monotonic()-start;hz=os.sysconf('SC_CLK_TCK')
rows=[]
for pid,v in sample().items():
 if pid in begin and begin[pid]['birth']==v['birth']:
  cpu=(v['ticks']-begin[pid]['ticks'])/hz/elapsed*100
  if cpu>.2:rows.append(dict(pid=pid,command=v['name'],cpu_percent_one_core=round(cpu,2)))
rows.sort(key=lambda x:x['cpu_percent_one_core'],reverse=True)
cpus={}
for p in Path('/sys/devices/system/cpu').glob('cpu[0-9]*'):
 values={}
 for n in ('online','cpufreq/scaling_cur_freq','cpufreq/scaling_governor'):
  q=p/n
  if q.exists():values[n]=q.read_text().strip()
 cpus[p.name]=values
affinity={}
for pid in (604389,137253):
 p=Path('/proc')/str(pid)/'status'
 if p.exists():affinity[str(pid)]=[x for x in p.read_text().splitlines() if x.startswith(('Cpus_allowed_list','Threads'))]
print(json.dumps(dict(elapsed_s=elapsed,processes=rows[:20],loadavg=Path('/proc/loadavg').read_text().strip(),cpus=cpus,affinity=affinity,actuator_commands=0)))
