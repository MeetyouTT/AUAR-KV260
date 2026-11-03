"""Read native protection/recovery state after an audit gate changes."""
import json,urllib.request
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with o.open('http://127.0.0.1:8790/health',timeout=3) as r:h=json.load(r)
s=h['dpu_schedule'];i=h['identity'];f=i['face_targets']
print(json.dumps({'pid':h['pid'],'frames':h['detected_frames'],'detection_hz':h.get('detection_hz'),
 'camera_error':h.get('camera_error'),'detector_error':h.get('detector_error'),'identity_error':h.get('identity_error'),
 'native_critical':s.get('native_critical'),'owner_fenced':s.get('owner_fenced'),'quiesced':s.get('quiesced'),
 'primary_calls':s.get('primary_calls'),'primary_overruns':s.get('primary_period_overruns'),
 'optional':{k:{p:v.get(p) for p in ('calls','overruns','disabled','recovery','native_completed')} for k,v in s['optional'].items()},
 'identity_ready':i.get('ready'),'feature':{k:i['feature_inference'].get(k) for k in ('ready','completed','state','error')},
 'face':{k:f.get(k) for k in ('worker_alive','error','backend','state')},
 'gaps':f['freshness_metrics']['counters']['observed_gap_intervals']},ensure_ascii=False,sort_keys=True))
