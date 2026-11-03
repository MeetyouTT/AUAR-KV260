import json,time,urllib.request
from pathlib import Path
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with op.open('http://127.0.0.1:'+str(port)+path,timeout=3) as stream:return json.load(stream)
h=get(8790,'/health');s=h['dpu_schedule'];g=get(8783,'/api/state')
p=Path('/sys/class/drm/card0-DP-1')
pan=g.get('manual_pan') or {}
print(json.dumps({'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'mono_ns':time.monotonic_ns(),
 'camera':{'pid':h['pid'],'yolo_hz':h['detection_hz'],'detected_frames':h['detected_frames'],
 'native_critical':s.get('native_critical'),'owner_fenced':s['owner_fenced'],'primary_overruns':s['primary_period_overruns'],
 'optional':{k:{x:v.get(x) for x in ['calls','native_completed','native_failures','overruns','disabled','recovery']} for k,v in s['optional'].items()},
 'face_worker_alive':h['identity']['face_targets']['worker_alive'],'face_backend':h['identity']['face_targets']['backend'],
 'sface_ready':h['identity']['feature_inference']['ready'],'sface_completed':h['identity']['feature_inference']['completed'],
 'face_gaps':h['identity']['face_targets']['freshness_metrics']['counters']['observed_gap_intervals']},
 'gui':{k:g.get(k) for k in ['phase','ui_page','playing','audio_output_state']},
 'manual_pan':{k:pan[k] for k in ['state','status','ready','automatic_following','fault','fault_reason'] if k in pan},
 'display':{k:(p/k).read_text().strip() for k in ['status','enabled','dpms']}}))
