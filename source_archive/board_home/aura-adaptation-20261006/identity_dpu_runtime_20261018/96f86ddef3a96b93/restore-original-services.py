
import json,subprocess,time,urllib.request
from pathlib import Path
root=Path('/home/root/aura-adaptation-20261006/identity_dpu_runtime_20261018/96f86ddef3a96b93')
report={'scope':'RESTORE_ORIGINAL_CONTINUOUS_DIALOGUE','boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
try:
 subprocess.run(['python3','-B',str(root/'rollback-final.py')],timeout=95,check=True)
 report['original_units_restored']=True
 opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 def get(port,path):
  with opener.open('http://127.0.0.1:%d%s'%(port,path),timeout=2) as r:return json.load(r)
 deadline=time.monotonic()+105
 while time.monotonic()<deadline:
  try:
   camera=get(8790,'/health');ui=get(8783,'/api/state')
   if (not camera['identity_recognition'] and not camera['camera_error'] and not camera['detector_error'] and camera.get('detected_frames',0)>3
       and ui.get('automatic_conversation',{}).get('can_start') and ui.get('local_transcription',{}).get('service',{}).get('streaming')):break
  except Exception:pass
  time.sleep(.5)
 else:raise RuntimeError('Original services did not become ready within 105s')
 report.update(status='PASS_ORIGINAL_SERVICES_RESTORED_DISPLAY_PHYSICAL_PENDING',camera_pid=camera['pid'],
  camera_identity_enabled=camera['identity_recognition'],observation_age_ms=camera['observation_age_ms'],
  automatic_turns_preserved=True,ui_phase=ui['phase'],physical_panel_verified=False)
except Exception as exc:report.update(status='BASELINE_RESTORE_NEEDS_DIAGNOSIS',error=str(exc))
(root/'baseline-restore-result.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report),flush=True)
