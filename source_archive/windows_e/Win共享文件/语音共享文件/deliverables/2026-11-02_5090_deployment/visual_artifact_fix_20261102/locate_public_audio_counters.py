import json,http.client,re
c=http.client.HTTPConnection('127.0.0.1',8783,timeout=4)
try:c.request('GET','/api/state');r=c.getresponse();assert r.status==200;v=json.loads(r.read(2097152))
finally:c.close()
allowed={'frame_bytes','capacity_frames','capacity_ms','queued_frames','peak_frames','frames_read','frames_delivered','source_read_mean_ms','source_read_max_ms','queue_mean_ms','queue_max_ms','frames','processed_samples','last_roundtrip_ms','max_roundtrip_ms','worker_pid','worker_generation','microphone_pid','worker_frame_wall_last_ms','worker_frame_wall_max_ms','worker_frame_wall_total_ms','worker_frame_cpu_last_ms','worker_frame_cpu_max_ms','worker_frame_cpu_total_ms','endpoint_feed_calls','endpoint_feed_wall_last_ms','endpoint_feed_wall_max_ms','endpoint_feed_wall_total_ms','endpoint_feed_cpu_last_ms','endpoint_feed_cpu_max_ms','endpoint_feed_cpu_total_ms','consumer_gap_last_ms','consumer_gap_max_ms','consumer_gap_total_ms','consumer_gap_count','enabled','eof','closed','cancelled','reader_alive','capture_lease_closed','worker_process_alive','worker_capture_process','nice','worker_nice','capture_failures'}
skip={'people','profiles','identities','history','messages','turns','transcript','transcripts','voice_enrollment','memories','conversation','conversation_address','candidates','matches','template','templates','embedding','embeddings'}
rows=[]
def walk(x,path='',depth=0):
 if depth>12:return
 if isinstance(x,dict):
  metrics={k:z for k,z in x.items() if k in allowed and type(z) in (int,float,bool)}
  if any(k in x for k in ('capacity_frames','worker_frame_wall_last_ms','worker_pid','consumer_gap_max_ms','processed_samples')):rows.append({'path':path,'metrics':metrics})
  for k,z in x.items():
   if k not in skip and re.fullmatch('[A-Za-z_][A-Za-z0-9_]*',k):walk(z,path+'/'+k,depth+1)
 elif isinstance(x,list) and len(x)<=32:
  for i,z in enumerate(x):
   if isinstance(z,(dict,list)):walk(z,path+'/'+str(i),depth+1)
walk(v)
print(json.dumps({'schema':'aura-public-frontend-counter-location-readonly-1','locations':rows,'local_recording_public_keys':[k for k in (v.get('local_recording') or {}) if re.fullmatch('[A-Za-z_][A-Za-z0-9_]*',k)],'no_scores_names_audio_frames_or_ids_exported':True,'state_changed':False}))
