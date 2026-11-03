"""Ten-second read-only timing diagnosis; no follower or actuator imports."""
import collections,http.client,json,statistics,time
from pathlib import Path
def fetch(path):
 c=http.client.HTTPConnection('127.0.0.1',8790,timeout=.3);start=time.monotonic()
 try:
  c.request('GET',path);r=c.getresponse();raw=r.read(131073)
  assert r.status==200 and len(raw)<=131072
  return json.loads(raw),time.monotonic(),(time.monotonic()-start)*1000
 finally:c.close()
def health():
 h,_,_=fetch('/health');s=h['dpu_schedule'];i=h['identity'];f=i['face_targets']
 return {'pid':h['pid'],'frames':h['detected_frames'],'primary':s['primary_period_overruns'],
  'optional':{k:s['optional'][k]['overruns'] for k in ('yunet','sface')},
  'gaps':f['freshness_metrics']['counters']['observed_gap_intervals'],'fenced':s['owner_fenced']}
before=health();start=time.monotonic();states=collections.Counter();ages=[];latencies=[];new=[];worst=[];errors=[];previous=None;expired_samples=0
while time.monotonic()-start<10:
 try:
  d,now,latency=fetch('/v1/motion/observation');now_ms=int(now*1000)
  states[str(d.get('state'))]+=1;latencies.append(latency)
  fid=d.get('source_frame_id');stamp=d.get('source_mono_ms');key=(d.get('camera_epoch'),fid,stamp)
  if type(stamp) is int:
   age=now_ms-stamp;ages.append(age)
   if age>=250:expired_samples+=1
   if key!=previous:
    row={'received_ms':now_ms,'source_ms':stamp,'age_ms':age,'request_ms':round(latency,2),'state':d.get('state')}
    if new:
     row.update(source_interval_ms=stamp-new[-1]['source_ms'],receive_interval_ms=now_ms-new[-1]['received_ms'],old_source_age_at_new_ms=now_ms-new[-1]['source_ms'])
     worst.append(row)
    new.append(row);previous=key
 except Exception as e:errors.append(type(e).__name__)
 time.sleep(.03)
after=health();elapsed=time.monotonic()-start
def stats(values):
 if not values:return None
 v=sorted(values);return {'min':round(v[0],2),'p50':round(statistics.median(v),2),'p95':round(v[min(len(v)-1,int(len(v)*.95))],2),'max':round(v[-1],2)}
result={'elapsed_s':round(elapsed,3),'requests':sum(states.values()),'states':dict(states),'source_age_ms':stats(ages),'request_ms':stats(latencies),
 'distinct_sources':len(new),'expired_samples':expired_samples,'source_interval_ms':stats([x['source_interval_ms'] for x in worst]),
 'receive_interval_ms':stats([x['receive_interval_ms'] for x in worst]),'old_source_age_at_new_ms':stats([x['old_source_age_at_new_ms'] for x in worst]),
 'worst_new_source_arrivals':sorted(worst,key=lambda x:x['old_source_age_at_new_ms'],reverse=True)[:5],
 'errors':dict(collections.Counter(errors)),'camera_pid_same':before['pid']==after['pid'],'frames_delta':after['frames']-before['frames'],
 'primary_delta':after['primary']-before['primary'],'optional_delta':{k:after['optional'][k]-before['optional'][k] for k in before['optional']},
 'gaps_delta':after['gaps']-before['gaps'],'owner_fenced':after['fenced'],'register_writes':0}
print(json.dumps(result,sort_keys=True))
