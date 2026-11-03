import hashlib,json,urllib.request
from pathlib import Path
root=Path('/home/root/aura-sface-formal-20261023/7b0f63f00dd263f7')
out={'report_exists':(root/'report.json').exists()}
if out['report_exists']:
 d=json.loads((root/'report.json').read_text())
 out.update({key:d.get(key) for key in ('phase','complete','passed','accepted','error','error_location',
  'restore_error','guard_left_armed','release','handoff_root','timer','new_database')})
 if d.get('migration'):out['migration']=d['migration']
 out['stages']=[{**{key:stage.get(key) for key in ('target','passed','observed_seconds','yolo_hz',
  'face_publish_hz','native_completed_delta','sface_native_completed_delta','sface_hz','known_correct_samples',
  'cpu_window','usb_warning_count')},'sample_count':len(stage.get('samples',[])),
  'latest':stage.get('samples',[])[-1] if stage.get('samples') else None} for stage in d.get('stages',[])]
 if d.get('restoration'):out['restoration']=d['restoration']
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
try:
 with op.open('http://127.0.0.1:8790/health',timeout=3) as response:h=json.load(response)
 identity=h.get('identity') or {};face=identity.get('face_targets') or {};schedule=h.get('dpu_schedule') or {}
 out['current']={'camera_pid':h['pid'],'capture_hz':h.get('capture_hz'),'yolo_hz':h.get('detection_hz'),
  'formal_identity_backend':identity.get('backend'),'face_backend':face.get('backend'),
  'source_age_ms':face.get('source_age_ms'),'gaps':face.get('freshness_metrics',{}).get('counters',{}).get('observed_gap_intervals'),
  'optional':schedule.get('optional'),'sface_wait':schedule.get('sface_slot_wait'),
  'feature_inference':identity.get('feature_inference'),'identity_ready':identity.get('ready'),'identity_error':identity.get('error')}
except Exception as e:out['current_health_error']=type(e).__name__
out['unit_sha256']=hashlib.sha256(Path('/etc/systemd/system/aura-camera-ui.service').read_bytes()).hexdigest()
print(json.dumps(out))
