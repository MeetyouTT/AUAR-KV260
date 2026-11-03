import json,os,resource,time,sys,subprocess
from pathlib import Path
paths=['/proc/sys/kernel/sched_schedstats','/proc/thread-self/schedstat']
values={}
for name in paths:
 try:values[name]=Path(name).read_text()[:256].strip()
 except OSError as exc:values[name]={'error':type(exc).__name__}
r=resource.getrusage(resource.RUSAGE_THREAD)
units={name:subprocess.check_output(['systemctl','show',name,'-p','MainPID','-p','NRestarts','--value'],timeout=3).decode().strip() for name in ('aura-camera-ui.service','aura-avatar-ui.service','xserver-nodm.service')}
print(json.dumps({'read_only':True,'mono':time.monotonic(),'capabilities':values,'thread_usage_switches':{'voluntary':r.ru_nvcsw,'involuntary':r.ru_nivcsw},'gil_switch_interval_seconds':sys.getswitchinterval(),'affinity_cpu_ids':sorted(os.sched_getaffinity(0)),'units':units,'kernel':os.uname().release}))
