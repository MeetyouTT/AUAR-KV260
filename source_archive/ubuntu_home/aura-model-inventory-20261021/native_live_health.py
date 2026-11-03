import json,subprocess,time,urllib.request
from pathlib import Path
root=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
result={'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'mono_ns':time.monotonic_ns(),
 'state':json.loads((root/'state.json').read_text())}
try:
 with op.open('http://127.0.0.1:8790/health',timeout=4) as r:h=json.load(r)
 s=h.get('dpu_schedule');identity=h.get('identity') or {};face=identity.get('face_targets') or {}
 result['camera']={k:h.get(k) for k in ['pid','detection_hz','capture_hz','detected_frames','capture_frames','camera_error','detector_error','observation_age_ms']}
 result['schedule']=s
 result['identity']={k:identity.get(k) for k in ['ready','backend','error','feature_inference','feature_status']}
 result['face']={k:face.get(k) for k in ['ready','backend','worker_alive','error','fault_latched','source_age_ms','freshness_metrics','published','inference']}
 result['identity_error']=h.get('identity_error')
except Exception as e:result['health_error']=type(e).__name__+': '+str(e)
result['activation_status']=subprocess.check_output(['systemctl','show','aura-native-activate-be72669aa53de735.service','-p','ActiveState','-p','MainPID','-p','Result'],text=True)
print(json.dumps(result))
