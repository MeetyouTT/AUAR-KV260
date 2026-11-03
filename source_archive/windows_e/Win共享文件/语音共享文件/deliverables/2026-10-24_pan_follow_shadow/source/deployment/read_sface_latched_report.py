"""Preserve numeric native failure reports for the existing scheduling work."""
import json,urllib.request
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with o.open('http://127.0.0.1:8790/health',timeout=3) as r:h=json.load(r)
s=h['dpu_schedule'];tasks={}
for k in ('yunet','sface'):
 v=s['optional'][k];report=v.get('last_native_report',{})
 tasks[k]={'recovery':v['recovery'],'overruns':v['overruns'],'disabled':v['disabled'],
 'last_native_report':{name:value for name,value in report.items() if type(value) in (int,float,bool) or value is None or name in ('outcome','reason','failure_phase','status')}}
print(json.dumps({'pid':h['pid'],'owner_fenced':s['owner_fenced'],'tasks':tasks,'register_writes':0},sort_keys=True))
