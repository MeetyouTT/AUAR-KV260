"""Finite read-only face timing check, no actuator access."""
import collections,http.client,json,statistics,time,urllib.request
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def health():
 with o.open('http://127.0.0.1:8790/health',timeout=3) as r:return json.load(r)
b=health();c=http.client.HTTPConnection('127.0.0.1',8790,timeout=.5)
c.request('GET','/v1/motion/face-stream?duration_ms=10000');r=c.getresponse();assert r.status==200
start=time.monotonic();states=collections.Counter();unique={};ages=[];rows=[]
while time.monotonic()-start<10.5:
 raw=r.readline(8193)
 if not raw:break
 p=json.loads(raw);now=int(time.monotonic()*1000);states[p['state']]+=1
 if p.get('source_mono_ms') is not None:
  age=now-p['source_mono_ms'];ages.append(age)
  if p['source_frame_id'] not in unique:
   unique[p['source_frame_id']]=p['source_mono_ms'];t=p.get('target')
   rows.append({'id':p['source_frame_id'],'stamp':p['source_mono_ms'],'age':age,'state':p['state'],'box':t['box'] if t else None})
c.close();a=health();s=a['dpu_schedule'];q=b['dpu_schedule'];f=a['identity']['face_targets']
print(json.dumps({'pid':a['pid'],'duration':round(time.monotonic()-start,3),'states':dict(states),'sources':rows,'age_max':max(ages) if ages else None,
 'face':{k:f.get(k) for k in ('processed','discarded','source_age_ms','last_inference_ms','worker_alive','backend','slot_retry')},
 'primary_delta':s['primary_period_overruns']-q['primary_period_overruns'],'optional_delta':{k:s['optional'][k]['overruns']-q['optional'][k]['overruns'] for k in ('yunet','sface')},'fenced':s['owner_fenced'],'register_writes':0}))
