import json,subprocess,time,urllib.request,os
from pathlib import Path
pid=int(subprocess.check_output(['pgrep','-f','^/usr/bin/python3 -B /home/root/aura-voice-barge-in-20261020/candidate-667b70d586ca/runtime/aura/tools/board_avatar_(gtk|pan).py']).split()[0])
def threads():
 result={}
 for p in Path('/proc/%d/task'%pid).iterdir():
  try:
   stat=(p/'stat').read_text().split(') ',1)[1].split();status=(p/'status').read_text()
   result[p.name]={'ticks':int(stat[11])+int(stat[12]),'name':(p/'comm').read_text().strip(),'sched':(p/'schedstat').read_text().split()}
  except OSError:pass
 return result
a=threads();start=time.monotonic();time.sleep(10);b=threads();dt=time.monotonic()-start;hz=os.sysconf('SC_CLK_TCK')
rows=[]
for tid,s in b.items():
 if tid not in a:continue
 old=a[tid];rows.append({'tid':tid,'name':s['name'],'cpu_percent':100*(s['ticks']-old['ticks'])/hz/dt,'run_ms':(int(s['sched'][0])-int(old['sched'][0]))/1e6,'runqueue_wait_ms':(int(s['sched'][1])-int(old['sched'][1]))/1e6})
print(json.dumps({'pid':pid,'command':Path('/proc/%d/cmdline'%pid).read_bytes().decode().split('\0'),'seconds':dt,'threads':sorted(rows,key=lambda x:-x['cpu_percent']),'affinity':list(os.sched_getaffinity(pid)),'memory':subprocess.getoutput('free -m'),'cpu':subprocess.getoutput('cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq'),'unit':subprocess.getoutput('systemctl cat aura-avatar-ui.service')}))
