import json,subprocess,time,urllib.request
from pathlib import Path
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def sample():
 with op.open('http://127.0.0.1:8790/health',timeout=2) as r:s=json.load(r)
 return {'mono_s':time.monotonic(),'pid':s['pid'],'captured':s['capture_frames'],'detected':s['detected_frames'],
  'capture_hz_since_start':s['capture_hz'],'detection_hz_since_start':s['detection_hz'],
  'camera_error':s['camera_error'],'detector_error':s['detector_error'],
  'age_ms':s['observation_age_ms'],'schedule':s.get('dpu_schedule'),
  'face':s.get('identity',{}).get('face_targets'),
  'shadow':(s.get('identity',{}).get('feature_inference') or {}).get('shadow')}
values=[sample()]
for _ in range(3):time.sleep(5);values.append(sample())
for s in values:
 assert s['pid']==192540 and not s['camera_error'] and not s['detector_error'] and s['shadow'] is None
 assert s['face']['backend']=='DPU_YUNET_INT8' and s['face']['ready']
 assert not s['schedule']['optional']['yunet']['disabled'] and not s['schedule']['optional']['yunet']['overruns']
first,last=values[0],values[-1];duration=last['mono_s']-first['mono_s']
raw=subprocess.check_output(['journalctl','-k','-n','1000','-o','json','--no-pager'],timeout=5).decode()
recent=0;latest_warning=None
for line in raw.splitlines():
 try:r=json.loads(line)
 except ValueError:continue
 if "HC couldn't access mem fast enough for slot 4 ep 3" in r.get('MESSAGE',''):
  stamp=int(r['__MONOTONIC_TIMESTAMP'])/1e6;latest_warning=max(latest_warning or 0,stamp)
  recent+=int(stamp>=first['mono_s'])
assert recent==0
print(json.dumps({'scope':'Post-recovery15s health and bounded kernel-tail check; not a30min stability claim',
 'samples':values,'duration_s':duration,'yolo_hz':(last['detected']-first['detected'])/duration,
 'capture_hz':(last['captured']-first['captured'])/duration,'recent_matching_warnings_in_tail':recent,
 'latest_retained_warning_age_s':last['mono_s']-latest_warning if latest_warning else None,
 'report_excludes_images_names_embeddings_and_database':True}))
