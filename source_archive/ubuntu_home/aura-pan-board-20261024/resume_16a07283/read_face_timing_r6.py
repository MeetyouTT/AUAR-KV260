import collections,json,time,urllib.request
o=urllib.request.build_opener(urllib.request.ProxyHandler({}));samples=[]
for _ in range(15):
 began=time.monotonic()
 with o.open('http://127.0.0.1:8790/v1/motion/face/observation',timeout=2) as r:p=json.load(r)
 now=int(time.monotonic()*1000);source=p.get('source_mono_ms');anchor=p.get('face_detection_mono_ms');ev=p.get('evaluated_mono_ms')
 samples.append(dict(state=p.get('state'),http_ms=round((time.monotonic()-began)*1000,2),
  source_age_ms=now-source if type(source) is int else None,anchor_age_ms=now-anchor if type(anchor) is int else None,
  evaluated_to_received_ms=now-ev if type(ev) is int else None,tracking=p.get('face_tracking'),
  detection_miss=p.get('detection_miss'),detector_frame=p.get('detector_snapshot_frame_id'),latest_detection_frame=p.get('latest_detection_frame_id')))
 time.sleep(.05)
print(json.dumps({'samples':samples,'writes':0}))
