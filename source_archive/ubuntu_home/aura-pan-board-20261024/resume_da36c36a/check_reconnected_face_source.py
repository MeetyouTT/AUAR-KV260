import json,time,urllib.request
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(path):
 with o.open('http://127.0.0.1:8790'+path,timeout=3) as f:return json.load(f)
rows=[]
for _ in range(3):
 p=get('/v1/motion/face/observation');h=get('/health');identity=h['identity'];targets=identity.get('face_targets') or {};d=h['dpu_schedule']
 rows.append({'camera_pid':h['pid'],'capture_frames':h.get('capture_frames'),'capture_hz':h.get('capture_hz'),
 'detection_hz':h.get('detection_hz'),'camera_error':h.get('camera_error'),'identity_ready':identity.get('ready'),
 'face_worker_alive':targets.get('worker_alive'),'face_worker_error':targets.get('error'),
 'packet_state':p.get('state'),'face_tracking':p.get('face_tracking'),'detector_timing':p.get('detector_timing'),
 'yunet':{k:d['optional']['yunet'].get(k) for k in ('calls','overruns','disabled','native_completed')},
 'primary_overruns':d['primary_period_overruns']})
 time.sleep(.5)
print(json.dumps({'samples':rows,'motor_commands':0,'MMIO_opened':False}))
