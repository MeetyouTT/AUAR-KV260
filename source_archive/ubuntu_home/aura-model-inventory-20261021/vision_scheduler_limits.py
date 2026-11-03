import json,os,subprocess
from pathlib import Path
pid=int(subprocess.check_output(['systemctl','show','aura-camera-ui.service','-p','MainPID','--value'],text=True))
keys=('Nice','CPUSchedulingPolicy','CPUSchedulingPriority','CPUAffinity','AllowedCPUs','CPUQuotaPerSecUSec',
 'CPUQuotaPeriodUSec','CPUAccounting','CPUWeight','CPUShares','ControlGroup','Slice')
r={'pid':pid,'services':{},'cgroup_files':{},'threads':{},'kernel':{}}
for name in ('aura-camera-ui.service','aura-avatar-ui.service','system.slice','-.slice'):
 args=['systemctl','show']
 for key in keys:args+=['-p',key]
 args+=['--',name]
 raw=subprocess.check_output(args,text=True);r['services'][name]=dict(line.split('=',1) for line in raw.splitlines())
cg=(Path('/proc')/str(pid)/'cgroup').read_text();r['cgroup_membership']=cg
for line in cg.splitlines():
 _,controllers,relative=line.split(':',2)
 roots=[Path('/sys/fs/cgroup')] if not controllers else [Path('/sys/fs/cgroup/cpu'),Path('/sys/fs/cgroup/cpu,cpuacct')]
 for root in roots:
  path=root/relative.lstrip('/')
  while root==path or root in path.parents:
   for name in ('cpu.max','cpu.stat','cpu.cfs_quota_us','cpu.cfs_period_us','cpu.shares'):
    p=path/name
    if p.is_file():r['cgroup_files'][str(p)]=p.read_text().strip()
   if path==root:break
   path=path.parent
for p in (Path('/proc')/str(pid)/'task').iterdir():
 try:
  tid=int(p.name);f=(p/'stat').read_text().rsplit(')',1)[1].split()
  r['threads'][str(tid)]={'nice':os.getpriority(os.PRIO_PROCESS,tid),'affinity':sorted(os.sched_getaffinity(tid)),
   'policy':os.sched_getscheduler(tid),'last_cpu':int(f[36]),'schedstat':(p/'schedstat').read_text().strip()}
 except (OSError,ValueError,IndexError):pass
for name in ('/sys/devices/system/cpu/online','/proc/sys/kernel/sched_rt_runtime_us','/proc/sys/kernel/sched_rt_period_us'):
 p=Path(name)
 if p.exists():r['kernel'][name]=p.read_text().strip()
print(json.dumps(r))
