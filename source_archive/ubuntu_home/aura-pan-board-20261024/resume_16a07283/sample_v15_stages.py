import collections,json,time,urllib.request
o=urllib.request.build_opener(urllib.request.ProxyHandler({}));records={};detectors={};states=collections.Counter();count=0
begin=time.monotonic()
for _ in range(24):
 with o.open('http://127.0.0.1:8790/v1/motion/face/observation',timeout=3) as f:p=json.load(f)
 states[p.get('state','INVALID')]+=1;count+=1
 for key,target in (('detector_stages',records),('detector_timing',detectors)):
  item=p.get(key)
  if isinstance(item,dict):target[(item['frame_id'],item['source_mono_ms'])]=item
 time.sleep(.1)
with o.open('http://127.0.0.1:8790/health',timeout=3) as f:h=json.load(f)
rows=[]
for key,r in records.items():rows.append(dict(stage=r,detector=detectors.get(key)))
print(json.dumps(dict(duration_s=round(time.monotonic()-begin,3),http_samples=count,states=dict(states),
 independent_stage_rounds=len(records),aligned_rounds=sum(v['detector'] is not None for v in rows),rounds=rows,
 camera_pid=h['pid'],primary_overruns=h['dpu_schedule']['primary_period_overruns'],
 optional_overruns={k:h['dpu_schedule']['optional'][k]['overruns'] for k in ('yunet','sface')},
 scope='same frame/source aligned wall and calling-thread CPU; nested stages overlap; not mechanical or pure DPU timing',
 actuator_commands=0)))
