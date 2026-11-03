import json,urllib.request
from pathlib import Path
out={'launches':{},'runs':{}}
for p in Path('/home/root/aura-dpu-vision-20261021/yunet-diagnostic-launches').glob('*/launch-result.json'):
 out['launches'][str(p)]=json.loads(p.read_text())
for p in Path('/home/root/aura-dpu-vision-20261021/yunet-diagnostics').glob('*/deployment-result.json'):
 d=json.loads(p.read_text());samples=d.pop('samples',[])
 d.pop('latest_camera_seen',None);d['sample_count']=len(samples)
 if samples:
  last=samples[-1];d['last_sample_summary']={k:last.get(k) for k in ['pid','elapsed_s','camera_error','detector_error','observation_age_ms','dpu_schedule']}
 out['runs'][str(p)]=d
try:
 with urllib.request.build_opener(urllib.request.ProxyHandler({})).open('http://127.0.0.1:8790/health',timeout=2) as r:s=json.load(r)
 out['camera']={k:s.get(k) for k in ['pid','detected_frames','camera_error','detector_error','observation_age_ms','dpu_schedule','pipeline_metrics']}
 out['camera']['face_targets']=s.get('identity',{}).get('face_targets')
except Exception as exc:out['camera_error']=type(exc).__name__+': '+str(exc)
print(json.dumps(out))
