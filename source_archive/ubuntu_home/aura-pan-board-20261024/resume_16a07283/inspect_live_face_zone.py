"""Observe current face admission and zone only; no actuator imports."""
import collections,hashlib,json,sys,time,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283');P=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/continuous-v10r3')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(P/'deployment-manifest.json')=='56f4207a4dc033c9762f1476e8b8a4824bab513c02eae1df9dbaa2e706b34385'
assert all(sha(x['destination'])==x['sha256'] for x in json.loads((P/'deployment-manifest.json').read_text())['files'])
sys.path.insert(0,str(P));from continuous_face_control import FaceEdgeController,EdgeConfig
from face_zone import camera_zone
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip();zone=camera_zone(json.loads((R/'face-zone-settings.json').read_text()),boot)
ctrl=FaceEdgeController(boot,1445,polarity=-1,config=EdgeConfig(left_ratio=zone['left_ratio'],right_ratio=zone['right_ratio']))
o=urllib.request.build_opener(urllib.request.ProxyHandler({}));rows=[];states=collections.Counter()
for _ in range(90):
 with o.open('http://127.0.0.1:8790/v1/motion/face/observation',timeout=3) as stream:p=json.load(stream)
 assert p.get('target_kind')=='face'
 now=int(time.monotonic()*1000);value=ctrl.observe(p,now);states[p.get('state','MISSING')]+=1
 b=(p.get('target') or {}).get('box');w=p.get('frame_width');tracking=p.get('face_tracking') or {}
 rows.append(dict(state=p.get('state'),tracking_reason=tracking.get('reason'),decision=value['reason'],edge=value['edge'],
  confirmed_sources=value['confirmed_sources'],source_age_ms=now-p['source_mono_ms'] if type(p.get('source_mono_ms')) is int else None,
  face_left_ratio=b[0]/w if b and w else None,face_center_ratio=(b[0]+b[2]/2)/w if b and w else None,
  detection_age_ms=now-p['face_detection_mono_ms'] if type(p.get('face_detection_mono_ms')) is int else None))
 if ctrl.stopped:ctrl=FaceEdgeController(boot,1445,polarity=-1,config=EdgeConfig(left_ratio=zone['left_ratio'],right_ratio=zone['right_ratio']))
 time.sleep(.15)
print(json.dumps({'states':dict(states),'samples':rows,'zone':zone,'MMIO_opened':False,'motor_commands_sent':0}))
