import json,time,urllib.request
op=urllib.request.build_opener(urllib.request.ProxyHandler({}));rows=[]
for _ in range(8):
 with op.open('http://127.0.0.1:8790/v1/motion/face/observation',timeout=3) as r:p=json.load(r)
 now=int(time.monotonic()*1000);rows.append(dict(state=p['state'],age_ms=now-p['source_mono_ms'] if p.get('source_mono_ms') else None,anchor_age_ms=now-p['face_detection_mono_ms'] if p.get('face_detection_mono_ms') else None,diagnostics=p.get('face_tracking')));time.sleep(.1)
print(json.dumps({'rows':rows}))
