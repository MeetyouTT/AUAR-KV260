import json,time,urllib.request,subprocess,hashlib
from pathlib import Path
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
r={'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'uptime':float(Path('/proc/uptime').read_text().split()[0]),'snapshot_mono_ns':time.monotonic_ns()}
for unit in ('aura-camera-ui.service','aura-avatar-ui.service','xserver-nodm.service'):
 raw=subprocess.check_output(['systemctl','show',unit,'-p','MainPID','-p','NRestarts','-p','ActiveState','-p','ExecMainStartTimestamp'],text=True)
 r[unit]=dict(line.split('=',1) for line in raw.splitlines())
for name,port,path in [('camera',8790,'/health'),('ui',8783,'/api/state')]:
 try:
  with op.open('http://127.0.0.1:'+str(port)+path,timeout=4) as stream:d=json.load(stream)
  if name=='camera':
   r[name]={k:d.get(k) for k in ('pid','detection_hz','capture_hz','camera_error','detector_error','dpu_schedule')}
   r[name]['identity']={k:d.get('identity',{}).get(k) for k in ('ready','backend','feature_inference','error','processed')}
   f=d.get('identity',{}).get('face_targets') or {}
   r[name]['face_targets']={k:f.get(k) for k in ('ready','backend','processed','worker_faults','worker_alive','freshness_metrics')}
  else:r[name]={k:d.get(k) for k in ('phase','audio_output_state','ui_page','playing','paused','handsfree_dialogue') if k!='handsfree_dialogue'};r[name]['microphone_open']=(d.get('handsfree_dialogue') or {}).get('microphone_open')
 except Exception as e:r[name]={'error':type(e).__name__+': '+str(e)}
unit=Path('/etc/systemd/system/aura-camera-ui.service');r['camera_unit_sha256']=hashlib.sha256(unit.read_bytes()).hexdigest()
for name,key in [('aura-camera-ui.service','camera_command'),('aura-avatar-ui.service','gui_command')]:
 pid=int(r[name]['MainPID'])
 if pid:r[key]=(Path('/proc')/str(pid)/'cmdline').read_bytes().decode().split('\0')[:-1]
print(json.dumps(r))
