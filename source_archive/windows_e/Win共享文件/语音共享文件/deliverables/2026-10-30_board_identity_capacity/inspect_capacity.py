"""Read-only board resources. No biometric content, runner or service changes."""
import datetime,json,sys
from pathlib import Path
H=Path(__file__).resolve().parent;P=H.parents[1]
sys.path[:0]=[str(P/'deliverables/2026-10-18_board_dialogue'),str(P/'deliverables/2026-10-29_audio_animation_polish')]
from board_ssh import ssh
from board_guard import capture,same
REMOTE=r'''
import importlib.util,json,os,platform,re,subprocess,sys,time,urllib.request
from pathlib import Path
os.nice(10)
def content(path,default=''):
 try:return Path(path).read_text().strip()
 except (OSError,ValueError):return default
def cmd(args):
 try:return subprocess.check_output(args,stderr=subprocess.PIPE,text=True,timeout=4).strip()
 except (OSError,subprocess.SubprocessError):return None
def unit(name):
 raw=cmd(['systemctl','show',name,'-p','MainPID','-p','ActiveState','-p','NRestarts','-p','ExecStart']) or ''
 return dict(line.split('=',1) for line in raw.splitlines() if '=' in line)
def http(path):
 try:
  with urllib.request.urlopen('http://127.0.0.1:'+path,timeout=2) as r:
   raw=r.read(262145)
   if len(raw)>262144:return {}
   return json.loads(raw)
 except Exception:return {}
def camera():
 h=http('8790/health');d=h.get('dpu_schedule',{});identity=h.get('identity',{})
 return dict(pid=h.get('pid'),detection_hz=h.get('detection_hz'),detected_frames=h.get('detected_frames'),
  dpu_primary_period_overruns=d.get('primary_period_overruns'),dpu_admission_floor_ms=d.get('admission_floor_ms'),
  sface_completed=identity.get('feature_inference',{}).get('completed'),
  face_processed=identity.get('face_targets',{}).get('processed'))
def ui():
 s=http('8783/api/state');hands=s.get('handsfree_dialogue',{});pan=s.get('manual_pan',{})
 return dict(phase=s.get('phase'),playing=s.get('playing'),audio_output_state=s.get('audio_output_state'),
  listening=hands.get('enabled'),microphone_open=hands.get('microphone_open'),automatic_following=pan.get('automatic_following'),
  mechanical_state=pan.get('state'),pulse_us=pan.get('pulse_us'),ui_tick_ms=s.get('ui_tick_ms'),
  avatar_display=s.get('avatar_display'),portrait_offload=s.get('portrait_offload'))
def memory():
 rows={}
 for line in content('/proc/meminfo').splitlines():
  key,value=line.split(':',1);parts=value.split()
  rows[key]=int(parts[0])*(1024 if len(parts)>1 and parts[1]=='kB' else 1)
 return {key:rows.get(key) for key in ('MemTotal','MemFree','MemAvailable','Buffers','Cached','SwapTotal','SwapFree','CmaTotal','CmaFree','Slab','SReclaimable','Dirty','Writeback')}
def snapshot():
 cpu={}
 for line in content('/proc/stat').splitlines():
  key,*rest=line.split()
  if re.fullmatch(r'cpu\d*',key):cpu[key]=[int(x) for x in rest[:8]]
 proc={}
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   raw=p.joinpath('stat').read_text();f=raw.rsplit(') ',1)[1].split()
   proc[int(p.name)]=dict(name=raw.split('(',1)[1].rsplit(')',1)[0],parent=int(f[1]),
     ticks=int(f[11])+int(f[12]),start_ticks=int(f[19]),rss_bytes=int(f[21])*os.sysconf('SC_PAGE_SIZE'))
  except (OSError,ValueError,IndexError):pass
 return dict(mono=time.monotonic(),cpu=cpu,processes=proc,memory=memory(),
  loadavg=content('/proc/loadavg').split()[:3],pressure={kind:content('/proc/pressure/'+kind) for kind in ('cpu','memory','io')})
def usage(a,b):
 result={}
 for key,x in a['cpu'].items():
  y=b['cpu'][key];delta=[n-m for n,m in zip(y,x)];total=sum(delta)
  result[key]=dict(busy_percent=round(100*(total-delta[3]-delta[4])/max(1,total),2),
   iowait_percent=round(100*delta[4]/max(1,total),2))
 return result
def disk(path):
 p=Path(path);s=os.statvfs(p)
 return dict(path=str(p),resolved=str(p.resolve()),total_bytes=s.f_blocks*s.f_frsize,
  available_bytes=s.f_bavail*s.f_frsize,free_bytes=s.f_bfree*s.f_frsize,
  used_bytes=(s.f_blocks-s.f_bfree)*s.f_frsize,inodes=s.f_files,inodes_free=s.f_favail,
  readonly=bool(s.f_flag&getattr(os,'ST_RDONLY',1)))
units={name:unit(name) for name in ('aura-camera-ui.service','aura-avatar-ui.service','xserver-nodm.service')}
runtime=None;config=None
try:
 argv=Path('/proc/'+units['aura-avatar-ui.service']['MainPID']+'/cmdline').read_bytes().decode().split('\0')
 config=Path(argv[argv.index('--config')+1]);cfg=json.loads(config.read_text());runtime=Path(cfg['runtime'])
except Exception:cfg={}
cpuinfo=[]
for block in content('/proc/cpuinfo').split('\n\n'):
 row={}
 for line in block.splitlines():
  if ':' in line:
   key,value=map(str.strip,line.split(':',1))
   if key in ('processor','model name','CPU implementer','CPU architecture','CPU variant','CPU part','CPU revision','Features'):row[key]=value
 if row:cpuinfo.append(row)
disks=[disk(path) for path in ('/','/home/root','/tmp','/dev/shm') if Path(path).exists()]
lsblk=cmd(['lsblk','-b','-J','-o','NAME,TYPE,SIZE,FSTYPE,MOUNTPOINT,ROTA,RM,RO'])
try:lsblk=json.loads(lsblk) if lsblk else None
except ValueError:pass
modules={}
for name in ('torch','torchaudio','speechbrain','onnxruntime','numpy','webrtcvad','sqlite3'):
 try:modules[name]=importlib.util.find_spec(name) is not None
 except (ImportError,ValueError):modules[name]=False
assets={}
if runtime is not None:
 assets['runtime']=str(runtime);assets['startup_config']=str(config);assets['component_pin_count']=len(cfg.get('component_sha256',{}))
 for name in ('common/identity_links.py','common/anonymous_voice.py','tools/binding_hub_runtime.py','board/runtime/audio/face_gallery_readback.py'):
  path=runtime/'aura'/name;assets[name]=dict(exists=path.is_file(),bytes=path.stat().st_size if path.is_file() else 0)
 facecfg=runtime/'aura/config/face_gallery_readback.local.json'
 if facecfg.is_file():
  info=json.loads(facecfg.read_text());db=Path(info['database'])
  # Stat files only: never read IDs, template hashes, vectors or table contents.
  assets['actual_face_store']={suffix:dict(exists=Path(str(db)+suffix).exists(),
   bytes=Path(str(db)+suffix).stat().st_size if Path(str(db)+suffix).is_file() else 0) for suffix in ('','-wal','-shm')}
temperatures={str(p):content(p) for p in Path('/sys/class/thermal').glob('thermal_zone*/temp')}
frequencies={str(p):content(p) for p in Path('/sys/devices/system/cpu').glob('cpu[0-9]*/cpufreq/scaling_cur_freq')}
first=snapshot();cam_before=camera();ui_before=ui();samples=[];prev=first
for i in range(1,31):
 time.sleep(max(0.,first['mono']+i-time.monotonic()))
 row=snapshot();samples.append(dict(elapsed_s=round(row['mono']-first['mono'],3),cpu=usage(prev,row),
  mem_available_bytes=row['memory']['MemAvailable'],loadavg=row['loadavg']));prev=row
last=prev;elapsed=last['mono']-first['mono'];rate=os.sysconf('SC_CLK_TCK');processes=[]
for pid,b in last['processes'].items():
 a=first['processes'].get(pid)
 if a is None or a['start_ticks']!=b['start_ticks']:continue
 percent=100*(b['ticks']-a['ticks'])/rate/elapsed
 processes.append(dict(pid=pid,name=b['name'],one_core_cpu_percent=round(percent,2),rss_bytes=b['rss_bytes'],parent=b['parent']))
processes.sort(key=lambda p:p['one_core_cpu_percent'],reverse=True)
pss={}
for row in processes[:8]:
 text=content('/proc/'+str(row['pid'])+'/smaps_rollup')
 selected={}
 for line in text.splitlines():
  if line.split(':')[0] in ('Rss','Pss','Private_Clean','Private_Dirty','Swap'):
   k,val=line.split(':',1);selected[k]=int(val.split()[0])*1024
 if selected:pss[str(row['pid'])]=selected
print(json.dumps(dict(status='PASS',scope='30_SECOND_CURRENT_WORKLOAD_READONLY_NOT_ACTIVE_DIALOGUE_CAPACITY',
 boot=content('/proc/sys/kernel/random/boot_id'),uptime_s=float(content('/proc/uptime').split()[0]),
 kernel=platform.release(),machine=platform.machine(),python=sys.version.split()[0],libc=platform.libc_ver(),
 board_model=Path('/proc/device-tree/model').read_bytes().rstrip(b'\0').decode() if Path('/proc/device-tree/model').exists() else None,
 cpu_count=os.cpu_count(),cpu_info=cpuinfo,cpu_usage=usage(first,last),processes=processes[:12],pss=pss,
 elapsed_s=elapsed,memory_before=first['memory'],memory_after=last['memory'],samples=samples,
 pressure_before=first['pressure'],pressure_after=last['pressure'],
 disk=disks,block_devices=lsblk,mounts=content('/proc/mounts'),units=units,assets=assets,
 modules_detected=modules,temperatures_millidegrees_c=temperatures,frequencies_khz=frequencies,
 camera_before=cam_before,camera_after=camera(),ui_before=ui_before,ui_after=ui(),
 biometric_content_read=False,face_metadata_transmitted=False,service_restarted=False,
 models_loaded=False,dpu_counter_controlled=False,storage_written=False)))
'''

report=dict(status='CHECKING',host_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),analysis_only=True)
try:
 before=capture()
 remote=json.loads(ssh('python3 -B -',REMOTE,timeout=48))
 after=capture();same(before,after)
 report.update(remote,board_guard_before_after_unchanged=True,guard_safe=after['safe'],
  actual_runtime=after['actual_runtime'],source_pin_count=len(after['pins']))
except Exception as exc:report.update(status='FAIL',error=type(exc).__name__+': '+str(exc))
(H/'capacity_snapshot.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:report.get(k) for k in ('status','board_model','cpu_count','cpu_usage','memory_after','disk','modules_detected','actual_runtime','error')},ensure_ascii=True))
raise SystemExit(0 if report['status']=='PASS' else 1)
