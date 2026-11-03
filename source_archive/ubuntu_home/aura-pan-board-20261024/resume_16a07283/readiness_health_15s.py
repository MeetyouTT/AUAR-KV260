import json,time,urllib.request
o=urllib.request.build_opener(urllib.request.ProxyHandler({}));samples=[]
for i in range(4):
 with o.open('http://127.0.0.1:8790/health',timeout=3) as r:h=json.load(r)
 d=h['dpu_schedule'];samples.append(dict(pid=h['pid'],primary_calls=d['primary_calls'],primary_overruns=d['primary_period_overruns'],
  owner_fenced=d['owner_fenced'],identity_ready=h['identity']['ready'],
  optional_overruns={k:d['optional'][k]['overruns'] for k in ('yunet','sface')}))
 if i<3:time.sleep(5)
print(json.dumps({'scope':'15s ready-state health spot check, not sustained human workload','samples':samples,
 'primary_progress':samples[-1]['primary_calls']-samples[0]['primary_calls'],'new_primary_overruns':samples[-1]['primary_overruns']-samples[0]['primary_overruns'],'actuator_commands':0}))
