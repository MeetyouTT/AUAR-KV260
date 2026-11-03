import hashlib,json,urllib.request
from pathlib import Path
root=Path('/home/root/aura-slot-wait-release-20261023/a6a22198e4efd56b')
out={'report_exists':(root/'report.json').exists()}
if out['report_exists']:
 d=json.loads((root/'report.json').read_text())
 out.update({key:d.get(key) for key in ('scope','phase','complete','passed','accepted','error','error_location',
     'restore_error','guard_left_armed','release','camera_pid','audio_pid','handoff_root','timer')})
 out['stages']=[{**{key:stage.get(key) for key in ('target','passed','observed_seconds','yolo_hz',
     'face_publish_hz','native_completed_delta','cpu_window','usb_warning_count')},
     'samples':len(stage.get('samples',[])),
     'latest':stage.get('samples',[])[-1] if stage.get('samples') else None}
     for stage in d.get('stages',[])]
 if d.get('restoration'):out['restoration']=d['restoration']
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
try:
 with op.open('http://127.0.0.1:8790/health',timeout=3) as f:h=json.load(f)
 face=h.get('identity',{}).get('face_targets') or {}
 out['camera']={'pid':h.get('pid'),'capture_hz':h.get('capture_hz'),'detection_hz':h.get('detection_hz'),
     'face_backend':face.get('backend'),'source_age_ms':face.get('source_age_ms'),
     'formal_identity_backend':h.get('identity',{}).get('backend'),
     'yunet':h.get('dpu_schedule',{}).get('optional',{}).get('yunet'),
     'recovery':h.get('dpu_schedule',{}).get('yunet_recovery'),
     'slot_wait':h.get('dpu_schedule',{}).get('yunet_slot_wait'),
     'gaps':face.get('freshness_metrics',{}).get('counters',{}).get('observed_gap_intervals')}
except Exception as e:out['camera_read_error']=type(e).__name__
out['unit_sha256']=hashlib.sha256(Path('/etc/systemd/system/aura-camera-ui.service').read_bytes()).hexdigest()
print(json.dumps(out))
