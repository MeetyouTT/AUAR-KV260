import json,time,urllib.request
op=urllib.request.build_opener(urllib.request.ProxyHandler({}));rows=[]
def get(path):
 with op.open('http://127.0.0.1:8790'+path,timeout=3) as f:return json.load(f)
for _ in range(5):
 p=get('/v1/motion/face/observation');h=get('/health');idn=h['identity'];ft=idn.get('face_targets') or {};tracking=p.get('face_tracking') or {};det=p.get('detector_timing') or {};sch=h['dpu_schedule'];Y=sch['optional']['yunet'];Z=Y.get('recovery') or {}
 rows.append({'camera_pid':h['pid'],'capture_frames':h.get('capture_frames'),'capture_hz':h.get('capture_hz'),
 'camera_error':h.get('camera_error'),'identity_ready':idn.get('ready'),'face_worker_alive':ft.get('worker_alive'),
 'face_worker_error':ft.get('error'),'observation_state':p.get('state'),'tracking_reason':tracking.get('reason'),
 'anchor_age_ms':tracking.get('anchor_age_ms'),'source_age_ms':h.get('observation_age_ms'),
 'face_measurement':tracking.get('measurement_method'),'face_score':(p.get('target') or {}).get('score'),
 'detector_count':det.get('detector_count'),'native':det.get('native',{}).get('outcome'),
 'yunet':{k:Y.get(k) for k in ('calls','overruns','native_completed','disabled')},
 'yunet_recovery':{k:Z.get(k) for k in ('phase','faults','attempts','recoveries','reason')},
 'primary_overruns':sch['primary_period_overruns']})
 time.sleep(.3)
print(json.dumps({'scope':'face packet causes and numeric detector health; no boxes, names, embeddings, images, ARM or COMMIT',
 'samples':rows,'motor_commands':0,'MMIO_opened':False}))
