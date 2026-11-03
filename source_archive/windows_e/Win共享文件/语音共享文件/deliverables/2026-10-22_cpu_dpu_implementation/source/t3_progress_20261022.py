import json,subprocess,urllib.request
from pathlib import Path
out={'launches':{},'runs':{}}
for p in Path('/home/root/aura-dpu-vision-20261021/shadow-long-launches').glob('*/launch-result.json'):
 out['launches'][str(p)]=json.loads(p.read_text())
for p in Path('/home/root/aura-dpu-vision-20261021/shadow-long').glob('*/deployment-result.json'):
 d=json.loads(p.read_text());samples=d.pop('samples',[])
 d['sample_count']=len(samples);d['last_sample']=samples[-1] if samples else None
 out['runs'][str(p)]=d
try:
 with urllib.request.build_opener(urllib.request.ProxyHandler({})).open('http://127.0.0.1:8790/health',timeout=3) as r:s=json.load(r)
 out['camera']={k:s.get(k) for k in ('pid','capture_frames','detected_frames','camera_error','detector_error','observation_age_ms','dpu_schedule')}
 identity=s.get('identity',{});out['camera']['face_targets']=identity.get('face_targets')
 out['camera']['shadow']=(identity.get('feature_inference') or {}).get('shadow')
except Exception as exc:out['camera_error']=type(exc).__name__+': '+str(exc)
print(json.dumps(out))
