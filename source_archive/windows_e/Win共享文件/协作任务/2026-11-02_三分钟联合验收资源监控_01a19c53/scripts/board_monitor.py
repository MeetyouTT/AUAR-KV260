"""Passive numeric observer. Standard library only; no target filesystem writes."""
import os,json,time,urllib.request,re,sys,signal,argparse
from pathlib import Path
from datetime import datetime,timezone
os.nice(10)
STOP=False
def stop(*_):
 global STOP;STOP=True
signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)

def read(path):
 try:return Path(path).read_text().strip()
 except OSError:return None

def paths(root,pattern):
 try:return list(Path(root).glob(pattern))
 except OSError:return []

def cpu():
 result={}
 for line in (read('/proc/stat') or '').splitlines():
  k,*v=line.split()
  if k=='cpu' or re.fullmatch(r'cpu\d+',k):result[k]=list(map(int,v[:8]))
 return result

SCRIPT_CACHE={}
def processes():
 out={}
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   stat=(p/'stat').read_text();cut=stat.rfind(')');v=stat[cut+2:].split()
   birth=int(v[19]);cache_key=(p.name,birth)
   if cache_key not in SCRIPT_CACHE:
    args=(p/'cmdline').read_bytes().split(b'\0')
    SCRIPT_CACHE[cache_key]=next((Path(a.decode(errors='replace')).name for a in args if a.endswith(b'.py')),None)
   out[p.name]={'comm':stat[stat.find('(')+1:cut],'script_basename':SCRIPT_CACHE[cache_key],'ppid':int(v[1]),'start_ticks':birth,'ticks':int(v[11])+int(v[12]),'rss_kib':int(v[21])*os.sysconf('SC_PAGE_SIZE')/1024}
  except (OSError,ValueError,IndexError):pass
 return out

PRIVATE={'text','transcript','transcription','reply','reply_text','prompt','content','messages','history','audio','pcm','image','frame','images','faces','tracks','people','persons','templates','embedding','embeddings','features','name','names','person_name','speaker_name','owner','owner_id','person_id','identity_id','speaker_id','request_id','capture_id','ack_id','path','url','reference','token','tokens','turn_id','conversation_id','session_id','profile','profiles','score','scores','identity','identities'}
ENUMS={'IDLE','LISTENING','SPEAKING','THINKING','PAUSED','READY','RECORDING','TRANSCRIBING','WAITING_SPEECH','DISABLED','RUNNING','STOPPED','FAULT','QUIESCING','RECOVERING','PROBING','FENCED','idle','listening','speaking','thinking','paused','ready','recording','transcribing','waiting_speech','disabled','running','stopped','main','vision','yolo','yunet','sface','primary','optional','visible','hidden','playing','waiting','complete','completed','failed','queued'}
def numeric(v):
 if isinstance(v,(bool,int,float)) or v is None:return v
 if isinstance(v,str):return v if v in ENUMS else None
 if isinstance(v,list):return None
 if isinstance(v,dict):
  out={}
  for k,x in v.items():
   low=k.lower()
   if low in PRIVATE or low.endswith('_id') or any(z in low for z in ['password','secret','embedding','similarity','cosine','confidence','template']):continue
   if 'error' in low and isinstance(x,str):out[k+'_present']=bool(x);continue
   val=numeric(x)
   if val is not None or x is None:out[k]=val
  return out
 return None

opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 before=time.monotonic()
 try:
  with opener.open('http://127.0.0.1:%d%s'%(port,path),timeout=.75) as r:v=json.load(r)
  selected={k:v.get(k) for k in ['pid','capture_frames','detected_frames','capture_hz','detection_hz','capture_age_ms','observation_age_ms','last_inference_ms','camera_error','detector_error','dpu_schedule','pipeline_metrics']}
  identity=v.get('identity') or {}
  selected['identity_ready']=identity.get('ready') is True
  selected['identity_error_present']=bool(identity.get('error'))
  selected['face_targets']=numeric(identity.get('face_targets'))
  for k in ['feature_inference','sface_shadow','sface','dpu_sface','native_sface','face_backend_metrics']:
   if k in identity:selected[k]=numeric(identity[k])
  after=time.monotonic()
  return {'ok':True,'request_ms':(after-before)*1000,'request_started_monotonic_s':before,'request_finished_monotonic_s':after,'data':numeric(selected)}
 except Exception as exc:return {'ok':False,'request_ms':(time.monotonic()-before)*1000,'error_type':type(exc).__name__}

def sensors():
 out={}
 for p in paths('/sys/class/thermal','thermal_zone*'):
  value=read(p/'temp')
  if value:
   try:out[p.name]={'type':read(p/'type'),'celsius':float(value)/1000}
   except ValueError:pass
 return out

def net():
 out={}
 for line in (read('/proc/net/dev') or '').splitlines()[2:]:
  if ':' not in line:continue
  k,v=line.split(':',1);k=k.strip();v=v.split()
  if k!='lo':out[k]={'rx_bytes':int(v[0]),'tx_bytes':int(v[8]),'rx_errors':int(v[2]),'tx_errors':int(v[10]),'rx_dropped':int(v[3]),'tx_dropped':int(v[11])}
 return out

def main():
 global STOP
 parser=argparse.ArgumentParser();parser.add_argument('--duration',type=float,default=180);parser.add_argument('--expected-boot');parser.add_argument('--expected-camera-pid',type=int);args=parser.parse_args()
 assert 10<=args.duration<=600
 start=time.monotonic();boot=read('/proc/sys/kernel/random/boot_id');previous_cpu=cpu();previous_proc=processes();previous_net=net();n=0
 if args.expected_boot and boot!=args.expected_boot:raise RuntimeError('Boot does not match acceptance handoff')
 print(json.dumps({'event':'start','board_wall_utc_untrusted':datetime.now(timezone.utc).isoformat(),'monotonic_s':start,'boot_id':boot,'pid':os.getpid(),'camera':get(8790,'/health'),'interval_s':2,'api_interval_s':2,'max_seconds':args.duration,'scope':'USER_AUTHORIZED_PASSIVE_JOINT_ACCEPTANCE_NUMERIC_RESOURCES','no_production_writes':True,'no_model_requests':True,'no_dpu_stat_enable':True}),flush=True)
 while not STOP and time.monotonic()-start<args.duration:
  deadline=start+(n+1)*2
  time.sleep(max(0,deadline-time.monotonic()))
  if STOP:break
  began=time.monotonic();now_cpu=cpu();now_proc=processes();now_net=net();row={'event':'sample','n':n+1,'board_wall_utc_untrusted':datetime.now(timezone.utc).isoformat(),'board_monotonic_s':began,'elapsed_s':began-start,'cpu':{},'processes':[]}
  for key,v in now_cpu.items():
   if key not in previous_cpu:continue
   d=[a-b for a,b in zip(v,previous_cpu[key])];total=sum(d)
   row['cpu'][key]=100*(1-(d[3]+d[4])/total) if total>0 else None
  total=sum(now_cpu['cpu'])-sum(previous_cpu['cpu'])
  for pid,v in now_proc.items():
   prev=previous_proc.get(pid)
   pct=100*(v['ticks']-prev['ticks'])/total if prev and prev['start_ticks']==v['start_ticks'] and total>0 else None
   if pct or v['rss_kib']>16384:row['processes'].append({'pid':int(pid),**v,'cpu_percent_board':pct})
  row['processes'].sort(key=lambda x:x['cpu_percent_board'] or 0,reverse=True);row['processes']=row['processes'][:35]
  mem={}
  for line in (read('/proc/meminfo') or '').splitlines():
   k,v=line.split(':',1)
   if k in ['MemTotal','MemAvailable','MemFree','Buffers','Cached','SwapTotal','SwapFree','CmaTotal','CmaFree']:mem[k]=int(v.split()[0])
  row['memory_kib']=mem;row['loadavg']=(read('/proc/loadavg') or '').split()[:3];row['thermal']=sensors()
  row['cpu_frequency_khz']={p.parent.parent.name:read(p) for p in paths('/sys/devices/system/cpu','cpu[0-9]*/cpufreq/scaling_cur_freq')}
  row['network_counters']=now_net
  row['dpu_hw_statistics_readonly']={str(p):read(p) for p in paths('/sys/kernel/debug/dpu','CU.*/stat')}
  row['camera']=get(8790,'/health')
  actual_camera=(row['camera'].get('data') or {}).get('pid')
  if args.expected_camera_pid and actual_camera is not None and actual_camera!=args.expected_camera_pid:
   row['camera_owner_changed']=True;STOP=True
  if n%10==0:
   row['boot_id']=read('/proc/sys/kernel/random/boot_id')
   if row['boot_id']!=boot:row['boot_changed']=True;STOP=True
  row['observer_work_ms']=(time.monotonic()-began)*1000
  print(json.dumps(row,separators=(',',':')),flush=True)
  previous_cpu=now_cpu;previous_proc=now_proc;previous_net=now_net;n+=1
 print(json.dumps({'event':'end','board_wall_utc_untrusted':datetime.now(timezone.utc).isoformat(),'elapsed_s':time.monotonic()-start,'samples':n,'stopped_by_signal':STOP}),flush=True)

if __name__=='__main__':main()
