import json,time,urllib.request
from pathlib import Path
o=urllib.request.build_opener(urllib.request.ProxyHandler({}));base='http://127.0.0.1:8783'
def state():
 with o.open(base+'/api/state',timeout=3) as f:return json.load(f)
before=state()['manual_pan']
q=urllib.request.Request(base+'/api/command',data=b'{"type":"pan_stop"}',headers={'Origin':base,'Content-Type':'application/json'})
with o.open(q,timeout=3) as f:reply=json.load(f)
end=time.monotonic()+10
while time.monotonic()<end:
 after=state()['manual_pan'];r=after.get('readback') or {}
 if not after['automatic_following'] and after['state']=='READY' and r.get('flags')==0 and r.get('lease_left_ms')==0:break
 time.sleep(.2)
assert not after['automatic_following'] and after['state']=='READY' and r['flags']==0 and r['lease_left_ms']==0
R=Path('/home/root/aura-pan-current-20261024/da36c36a');p=(after.get('face_follow') or {}).get('report');report=json.loads(Path(p).read_text()) if p else None
s=json.loads((R/'state.json').read_text());s.update(phase='CURRENT_FACE_STOPPED_FOR_LATCHED_RECENTER',automatic_following=False,current_last_command_us=r['width_us'],current_stopped_readback=r,last_face_report=p)
(R/'state.json').write_text(json.dumps(s,indent=2)+'\n')
print(json.dumps({'status':s['phase'],'stop_reply':reply,'before':before,'after':after,'report':report,'operator_stop_verified':True}))
