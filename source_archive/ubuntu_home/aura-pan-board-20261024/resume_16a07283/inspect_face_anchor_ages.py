import json,time,urllib.request
o=urllib.request.build_opener(urllib.request.ProxyHandler({}));rows=[]
for _ in range(20):
 with o.open('http://127.0.0.1:8790/v1/motion/face/observation',timeout=3) as r:p=json.load(r)
 now=int(time.monotonic()*1000);source=p.get('source_mono_ms');anchor=p.get('face_detection_mono_ms');evaluated=p.get('evaluated_mono_ms')
 rows.append({'state':p['state'],'source':source,'anchor':anchor,'evaluated':evaluated,'receipt':now,
  'anchor_type':type(anchor).__name__,'source_type':type(source).__name__,
  'source_age_ms':now-source if type(source) is int else None,'anchor_age_ms':now-anchor if type(anchor) is int else None,
  'diagnostic':p.get('face_tracking',{}).get('reason')})
 time.sleep(.04)
print(json.dumps({'rows':rows,'MMIO_opened':False,'ARM':0,'COMMIT':0}))
