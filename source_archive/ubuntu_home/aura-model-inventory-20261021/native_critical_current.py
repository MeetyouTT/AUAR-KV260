import json,time,urllib.request
from pathlib import Path
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8790/health',timeout=4) as stream:h=json.load(stream)
s=h['dpu_schedule'];f=h['identity']['face_targets']
print(json.dumps({'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'mono_ns':time.monotonic_ns(),
 'pid':h['pid'],'yolo_hz':h['detection_hz'],'optional':s['optional'],'yunet_recovery':s['yunet_recovery'],
 'sface_recovery':s['sface_recovery'],'owner_fenced':s['owner_fenced'],'primary_overruns':s['primary_period_overruns'],
 'face_backend':f['backend'],'worker_alive':f['worker_alive'],'gaps':f['freshness_metrics']['counters']['observed_gap_intervals'],
 'feature_inference':h['identity']['feature_inference'],'fault_events':s['optional_diagnostics']['fault_events']}))
