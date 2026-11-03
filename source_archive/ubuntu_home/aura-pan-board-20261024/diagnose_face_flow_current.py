"""Only numeric face-flow latency, affinities and new USB warnings."""
import json,os,time,urllib.request
from pathlib import Path
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
rows=[]
for _ in range(30):
 p=get(8790,'/v1/motion/face/observation');now=int(time.monotonic()*1000)
 rows.append({'state':p['state'],'age':now-p['source_mono_ms'] if p['source_mono_ms'] else None,'tracking':p.get('face_tracking')})
 time.sleep(.03)
h=get(8790,'/health');u=get(8783,'/api/state');f=h['identity']['face_targets'];cpus={}
for p in Path('/sys/devices/system/cpu').glob('cpu[0-9]/cpufreq/scaling_cur_freq'):cpus[str(p)]=p.read_text().strip()
affinity={}
for pid in (h['pid'],u['manual_pan'].get('backend_pid')):
 if pid:
  try:affinity[str(pid)]=list(os.sched_getaffinity(pid))
  except OSError:pass
print(json.dumps({'rows':rows,'face':f,'camera_pid':h['pid'],'primary':h['dpu_schedule']['primary_period_overruns'],
 'preview':u['ui_runtime']['preview_metrics'],'cpufreq':cpus,'affinity':affinity,'load':Path('/proc/loadavg').read_text().strip()}))
