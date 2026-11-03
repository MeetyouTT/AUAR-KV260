"""Passive numeric throughput/reason observation, not another human accuracy test."""
import json,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'deliverables/2026-10-18_board_dialogue'))
from board_ssh import ssh
remote=r'''
import json,time,urllib.request,statistics
from collections import Counter
get=lambda path:json.load(urllib.request.urlopen('http://127.0.0.1:8790'+path,timeout=3))
first=get('/health');start=time.monotonic();end=start+10
counts=Counter();rows=[];targets=set();faces_seen=set();feature_seen=set()
while time.monotonic()<end:
 h=get('/health');s=get('/v1/ui/status');i=s['modules']['identity'];f=h['identity']['face_targets']
 age=f.get('source_age_ms');key=i.get('face_target');targets.add(json.dumps(key,sort_keys=True))
 count=i.get('face_count');counts['face_count_'+str(count)]+=1
 if key:counts['confirmed_target']+=1
 if i.get('face_preview'):counts['fresh_input']+=1;feature_seen.add(i['face_preview']['frame_id'])
 counts['state_'+i['state']]+=1
 # Keep no recognition names even if a passive sample happens to be KNOWN.
 reason=i.get('detail','') if i['state']!='KNOWN' else 'KNOWN'
 if i['state']!='KNOWN':counts['reason_'+reason]+=1
 rows.append({'elapsed_ms':round((time.monotonic()-start)*1000),'face_count':count,
  'has_confirmed_target':bool(key),'has_fresh_input':bool(i.get('face_preview')),
  'state':i['state'],'face_detector_ms':f['last_inference_ms'],'face_source_age_ms':age,
  'feature_ms':h['identity']['last_inference_ms'],'reason':reason})
 time.sleep(.22)
last=get('/health');duration=time.monotonic()-start
face_delta=last['identity']['face_targets']['processed']-first['identity']['face_targets']['processed']
feature_delta=last['identity']['processed']-first['identity']['processed']
dist=lambda values:{'min':round(min(values),2),'median':round(statistics.median(values),2),'max':round(max(values),2)} if values else None
print(json.dumps({'status':'PASSIVE_PIPELINE_THROUGHPUT_MEASURED','duration_seconds':round(duration,2),
 'face_detection_completed':face_delta,'face_detection_hz':round(face_delta/duration,3),
 'identity_inference_completed':feature_delta,'identity_inference_hz':round(feature_delta/duration,3),
 'face_detector_ms':dist([r['face_detector_ms'] for r in rows if r['face_detector_ms'] is not None]),
 'face_source_age_ms':dist([r['face_source_age_ms'] for r in rows if r['face_source_age_ms'] is not None]),
 'feature_ms':dist([r['feature_ms'] for r in rows if r['feature_ms'] is not None]),
 'poll_observations':dict(counts),'distinct_target_keys_including_none':len(targets),
 'distinct_fresh_feature_frames_observed':len(feature_seen),'samples':rows,
 'current_person_and_pose_not_declared':True,'not_a_new_registered_person_accuracy_test':True,
 'production_changed':False,'photos_names_or_embeddings_exported':False}))
'''
r=json.loads(ssh('python3 -B -',remote,timeout=27))
(HERE/'passive_pipeline.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in r.items() if k!='samples'},ensure_ascii=False))
