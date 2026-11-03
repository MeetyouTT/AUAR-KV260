import json,subprocess,time,urllib.request
from pathlib import Path
source_boot='a69299ef-17d0-446f-a0df-56c0a08cd2fb'
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
root=Path('/home/root/aura-native-coldboot-20261024/c6b338dc8423086d')
p=root/'shutdown.json';report=json.loads(p.read_text()) if p.exists() else None
result={'current_boot':boot,'previous_boot':source_boot,'kernel_changed':boot!=source_boot,
 'uptime_seconds':float(Path('/proc/uptime').read_text().split()[0]),'shutdown_report_exists':p.exists(),'shutdown_report':report}
units={}
for unit in ['aura-camera-ui.service','aura-avatar-ui.service','xserver-nodm.service']:
 text=subprocess.check_output(['systemctl','show',unit,'-p','ActiveState','-p','SubState','-p','MainPID','-p','Result','-p','NRestarts'],text=True)
 units[unit]=dict(line.split('=',1) for line in text.splitlines() if '=' in line)
result['services']=units
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
for name,port,path in [('camera',8790,'/health'),('gui',8783,'/api/state')]:
 try:
  with op.open('http://127.0.0.1:'+str(port)+path,timeout=4) as stream:h=json.load(stream)
  if name=='camera':
   s=h['dpu_schedule'];identity=h['identity'];face=identity.get('face_targets') or {}
   result['camera']={k:h.get(k) for k in ['pid','detection_hz','capture_hz','detected_frames','capture_frames','camera_error','detector_error','observation_age_ms']}
   result['native_schedule']=s;result['identity']={k:identity.get(k) for k in ['ready','backend','error','feature_inference','match_diagnostics']}
   result['face']={k:face.get(k) for k in ['ready','backend','worker_alive','error','source_age_ms','freshness_metrics']}
  else:result['gui']={k:h.get(k) for k in ['phase','audio_output_state','ui_page','playing','paused','backend']}
 except Exception as exc:result[name+'_unavailable']=type(exc).__name__+': '+str(exc)
print(json.dumps(result))
