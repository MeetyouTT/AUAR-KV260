import hashlib,json,os,subprocess,time,urllib.request
from pathlib import Path
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8790/health',timeout=3) as f:s=json.load(f)
with op.open('http://127.0.0.1:8783/api/state',timeout=3) as f:u=json.load(f)
units={n:subprocess.check_output(['systemctl','show',n,'-p','MainPID','-p','NRestarts','-p','ActiveState'],timeout=3).decode().strip() for n in ('aura-avatar-ui.service','aura-camera-ui.service','xserver-nodm.service')}
pid=s['pid'];args=(Path('/proc')/str(pid)/'cmdline').read_bytes().split(b'\0');tasks=[]
for task in (Path('/proc')/str(pid)/'task').iterdir():
    try:tasks.append({'tid':int(task.name),'comm':(task/'comm').read_text().strip(),'cpus':sorted(os.sched_getaffinity(int(task.name)))})
    except (FileNotFoundError,ProcessLookupError):pass
print(json.dumps({'read_only':True,'mono':time.monotonic(),'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'pid':pid,'process_allowed_cpus':sorted(os.sched_getaffinity(pid)),'tasks':tasks,'camera_script':next(a.decode() for a in args if a.endswith(b'/board_camera_motion.py')),'units':units,'camera_error':s.get('camera_error'),'detector_error':s.get('detector_error'),'face_targets':s.get('identity',{}).get('face_targets'),'schedule':s.get('dpu_schedule'),'pipeline_metrics_disabled':s.get('pipeline_metrics') is None,'ui':{k:u.get(k) for k in ('phase','playing','paused','audio_output_state')},'recording_state':u.get('local_recording',{}).get('state'),'transcription_pending':u.get('local_transcription',{}).get('service',{}).get('pending'),'camera_unit_sha256':hashlib.sha256(Path('/etc/systemd/system/aura-camera-ui.service').read_bytes()).hexdigest()}))
