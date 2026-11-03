"""Read existing stage timings without enabling additional diagnostics."""
import json,urllib.request
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with o.open('http://127.0.0.1:8790/health',timeout=3) as r:h=json.load(r)
m=h.get('pipeline_metrics',{});s=m.get('stages',{})
keys=['capture.callback_prepare','yolo.source_age_at_start','yolo.schedule_wait','yolo.native_and_decode','yolo.track','yolo.path','yolo.publish_source_age','preview.render_encode_publish','preview.publish_source_age']
print(json.dumps({'pid':h['pid'],'metrics_enabled':m.get('enabled'),'capture_hz':h.get('capture_hz'),'detection_hz':h.get('detection_hz'),
 'stages':{k:s.get(k) for k in keys},'register_writes':0},sort_keys=True))
