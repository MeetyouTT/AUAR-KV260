from pathlib import Path
import json
p=Path('/home/root/aura-dpu-vision-20261021/postpower-retry-live/cbee206f503bab01-105026/deployment-result.json')
d=json.loads(p.read_text());rows=d.get('samples',[])
idx=[i for i,s in enumerate(rows) if s.get('face_targets',{}).get('source_age_ms',-1)>=1000]
out={'scope':d.get('scope'),'passed':d.get('passed'),'sample_count':len(rows),'outlier_indices':idx,'samples':[]}
for i in idx:
 for j in range(max(0,i-1),min(len(rows),i+2)):
  s=rows[j];f=s.get('face_targets',{});sched=s.get('dpu_schedule',{});yun=sched.get('optional',{}).get('yunet',{})
  out['samples'].append({'index':j,'elapsed_s':s.get('elapsed_s'),'observation_age_ms':s.get('observation_age_ms'),'sampled_face_source_age_ms':f.get('source_age_ms'),'capture_hz':s.get('capture_hz'),'detection_hz':s.get('detection_hz'),'camera_error':s.get('camera_error'),'detector_error':s.get('detector_error'),'face_source_age_ms':f.get('source_age_ms'),'face_processed':f.get('processed'),'face_discarded':f.get('discarded'),'yu_calls':yun.get('calls'),'yu_max_ms':yun.get('maximum_ms'),'yu_overruns':yun.get('overruns'),'yu_disabled':yun.get('disabled')})
out['freshness_gates']=d.get('freshness_final',{}).get('counters')
out['rollback_verified']=d.get('rollback_verified')
print(json.dumps(out,separators=(',',':')))
