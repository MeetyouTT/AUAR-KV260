"""Read bounded /proc counters and CPU policy; no application payloads."""
import json
from pathlib import Path
import sys
HERE=Path(__file__).resolve().parent
PROJECT=HERE.parents[4]
sys.path.insert(0,str(PROJECT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
REMOTE=r'''
import json,os,pathlib,time
root=pathlib.Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
gtk=json.loads((root/'runtime/launch.json').read_bytes())['pid']
worker=[]
for p in pathlib.Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  raw=(p/'stat').read_text();f=raw[raw.rfind(')')+2:].split()
  if int(f[1])==gtk and b'board_frontend_process' in (p/'cmdline').read_bytes():worker.append(int(p.name))
 except OSError:pass
assert len(worker)==1
owners={'gtk':gtk,'frontend':worker[0],'camera':260102}
def read():
 cpu={}
 for line in pathlib.Path('/proc/stat').read_text().splitlines():
  fields=line.split()
  if fields[0].startswith('cpu'):
   ticks=list(map(int,fields[1:9]));cpu[fields[0]]=(sum(ticks),ticks[3]+ticks[4])
 threads={}
 for role,pid in owners.items():
  for task in (pathlib.Path('/proc')/str(pid)/'task').iterdir():
   try:
    raw=(task/'stat').read_text();f=raw[raw.rfind(')')+2:].split()
    sched={}
    for line in ((task/'sched').read_text().splitlines() if (task/'sched').exists() else []):
     if ':' in line:
      k,v=line.split(':',1)
      if k.strip() in ('se.nr_migrations','nr_switches'):sched[k.strip()]=int(v.strip())
    threads[(role,int(task.name))]=dict(ticks=int(f[11])+int(f[12]),nice=int(f[16]),core=int(f[36]),
      affinity=sorted(os.sched_getaffinity(int(task.name))),schedstat=(list(map(int,(task/'schedstat').read_text().split())) if (task/'schedstat').exists() else None),**sched)
   except (OSError,ValueError):pass
 return time.monotonic(),cpu,threads
a,ca,ta=read();time.sleep(5);b,cb,tb=read();duration=b-a;hz=os.sysconf('SC_CLK_TCK')
busy={k:round(100*(1-(cb[k][1]-ca[k][1])/(cb[k][0]-ca[k][0])),2) for k in ca if cb[k][0]>ca[k][0]}
rows=[]
for key,v in tb.items():
 if key not in ta:continue
 old=ta[key];percent=100*(v['ticks']-old['ticks'])/hz/duration
 if percent<1:continue
 rows.append(dict(role=key[0],tid=key[1],cpu_one_core_percent=round(percent,2),nice=v['nice'],core=v['core'],affinity=v['affinity'],
   migrations=v.get('se.nr_migrations',0)-old.get('se.nr_migrations',0),
   scheduling_wait_ms=(round((v['schedstat'][1]-old['schedstat'][1])/1e6,3) if v['schedstat'] is not None and old['schedstat'] is not None else None)))
policies=[]
for p in pathlib.Path('/sys/devices/system/cpu/cpufreq').glob('policy*'):
 row={}
 for name in ('scaling_governor','scaling_cur_freq','cpuinfo_max_freq','scaling_available_governors'):
  try:row[name]=(p/name).read_text().strip()
  except OSError:pass
 policies.append(row)
print(json.dumps(dict(seconds=duration,owners=owners,busy_percent=busy,threads=sorted(rows,key=lambda r:-r['cpu_one_core_percent']),policies=policies)))
'''
if __name__=='__main__':
    label=sys.argv[1] if len(sys.argv)>1 else 'combined_budget'
    assert label.replace('_','').isalnum()
    value=json.loads(ssh('python3 -B -',REMOTE,timeout=15))
    (HERE/(label+'.json')).write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(value))
