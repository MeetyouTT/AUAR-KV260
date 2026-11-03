import json,os,subprocess,time
from pathlib import Path
pid=int(subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','MainPID','--value'],timeout=3))
def cpu():
 rows={}
 for line in Path('/proc/stat').read_text().splitlines():
  parts=line.split()
  if parts and parts[0].startswith('cpu'):
   v=list(map(int,parts[1:9]));rows[parts[0]]=(sum(v),v[3]+v[4])
 return rows
first=cpu();started=time.monotonic();time.sleep(3);last=cpu();elapsed=time.monotonic()-started
rates={name:100*((last[name][0]-first[name][0])-(last[name][1]-first[name][1]))/(last[name][0]-first[name][0]) for name in first if last[name][0]>first[name][0]}
threads=[]
for path in (Path('/proc')/str(pid)/'task').glob('[0-9]*'):
 try:
  stat=(path/'stat').read_text();values=stat[stat.rfind(')')+2:].split();tid=int(path.name)
  threads.append({'tid':tid,'last_cpu':int(values[36]),'affinity_cpu_ids':sorted(os.sched_getaffinity(tid))})
 except (OSError,ValueError,IndexError):pass
print(json.dumps({'scope':'READONLY_3S_CPU_CONTEXT_NOT_OPTIMIZATION_GAIN','camera_pid':pid,'duration_seconds':elapsed,'busy_percent':rates,'camera_thread_count':len(threads),'threads':threads}))
