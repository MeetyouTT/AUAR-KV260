import json,time,urllib.request
from pathlib import Path
o=urllib.request.build_opener(urllib.request.ProxyHandler({}));base='http://127.0.0.1:8783'
def get():
 with o.open(base+'/api/state',timeout=3) as r:return json.load(r)['manual_pan']
before=get();reply=None
if before['automatic_following']:
 q=urllib.request.Request(base+'/api/command',data=b'{"type":"pan_stop"}',headers={'Origin':base,'Content-Type':'application/json'})
 with o.open(q,timeout=3) as r:reply=json.load(r)
for _ in range(40):
 after=get();r=after.get('readback') or {}
 if not after['automatic_following'] and after['state']=='READY' and r.get('flags')==0 and r.get('lease_left_ms')==0:break
 time.sleep(.2)
else:raise RuntimeError('Motor stop was not confirmed')
f=after.get('face_follow') or {};p=Path(f.get('report',''));report=None
if p.is_file() and p.stat().st_size:report=json.loads(p.read_text())
print(json.dumps(dict(status='FACE_TEST_STOPPED',stop_reply=reply,manual=after,report=report,motor_stop_verified=True)))
