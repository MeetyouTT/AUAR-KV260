"""Dynamic CPU / XRT busy sampler; no second inference runtime is opened."""
import json,os,time,urllib.request
from pathlib import Path
cu=Path('/sys/devices/platform/axi/axi:zyxclmm_drm/CU.3.auto')
def stat():
 v=list(map(int,(cu/'stat').read_text().split()));assert len(v)==8
 return {'t':time.monotonic(),'raw':v}
def cpu():
 a=list(map(int,Path('/proc/stat').read_text().splitlines()[0].split()[1:9]));ps={}
 for p in Path('/proc').glob('[0-9]*'):
  try:
   s=(p/'stat').read_text().split(') ')[1].split();args=(p/'cmdline').read_bytes().split(b'\0')
   scripts=[Path(x.decode(errors='replace')).name for x in args if x.endswith(b'.py')]
   ps[p.name]=(int(s[11])+int(s[12]),int(s[19]),scripts[0] if scripts else (p/'comm').read_text().strip())
  except (OSError,IndexError):pass
 return time.monotonic(),sum(a),a[3]+a[4],ps
def health():
 with urllib.request.urlopen('http://127.0.0.1:8790/health',timeout=2) as r:s=json.load(r)
 out={k:s.get(k) for k in ['pid','capture_frames','detected_frames','capture_hz','detection_hz','camera_error','detector_error','observation_age_ms','dpu_schedule']}
 out['face_targets']=s.get('identity',{}).get('face_targets');return out
out={'scope':'LIVE_PIPELINE_15S_CPU_AND_XRT_TASK_BUSY_NOT_MAC_UTILIZATION','health_before':health(),'samples':[]}
assert (cu/'base_paddr').read_text().strip()=='0xa0010000'
counter_before=stat();time.sleep(.35);counter_after=stat();health_mid=health()
assert health_mid['detected_frames']-out['health_before']['detected_frames']>=2,'No advancing YOLO workload for collector preflight'
assert counter_before['raw'][0]==counter_after['raw'][0],'Another CU collector is active'
out['inactive_collector_preflight']={'before':counter_before,'after':counter_after}
started=False
try:
 out['stats_begin']=(cu/'stats_begin').read_text().strip();started=True;time.sleep(1.1)
 last=stat();out['warmup']=last;first=cpu()
 for i in range(1,16):
  time.sleep(max(0,first[0]+i-time.monotonic()));s=stat();s['interval_s']=s['t']-last['t'];s['busy_percent']=100-s['raw'][7];assert 0<=s['busy_percent']<=100
  out['samples'].append(s);last=s
 end=cpu();dt=end[0]-first[0];total=end[1]-first[1]
 out['duration_s']=dt;out['cpu_percent_of_board']=100*(total-end[2]+first[2])/total
 processes=[]
 for pid,value in end[3].items():
  old=first[3].get(pid)
  if old and old[1]==value[1]:processes.append({'pid':int(pid),'name':value[2],'percent_of_board':100*(value[0]-old[0])/os.sysconf('SC_CLK_TCK')/dt/os.cpu_count()})
 out['processes']=sorted(processes,key=lambda x:x['percent_of_board'],reverse=True)[:10]
 out['dpu_task_busy_percent']=sum(x['interval_s']*x['busy_percent'] for x in out['samples'])/sum(x['interval_s'] for x in out['samples'])
 out['dpu_commands_completed']=last['raw'][0]-out['warmup']['raw'][0]
finally:
 if started:out['stats_end']=(cu/'stats_end').read_text().strip()
out['health_after']=health();out['stat_after_end']=stat();time.sleep(.25);out['stat_disabled_check']=stat()
out['statistics_disabled']=out['stat_after_end']['raw'][0]==out['stat_disabled_check']['raw'][0]
print(json.dumps(out))
