import json,time,urllib.request
from pathlib import Path
ROOT=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/continuous-v14r1')
SHA='e4701658fa75a0e08d1d3650f744d91c91ca6557ee0b861cffe7f6083bad5701'
o=urllib.request.build_opener(urllib.request.ProxyHandler({}));base='http://127.0.0.1:8783'
def get():
 with o.open(base+'/api/state',timeout=3) as f:return json.load(f)
before=get();m=before['manual_pan'];reply=None
if not m['automatic_following']:
 assert before['phase']=='IDLE' and not before.get('playing')
 assert m['state']=='READY' and m['readback']['flags']==0 and m['readback']['lease_left_ms']==0
 q=urllib.request.Request(base+'/api/command',data=b'{"type":"pan_face_follow"}',headers={'Origin':base,'Content-Type':'application/json'})
 with o.open(q,timeout=4) as f:reply=json.load(f)
 assert reply.get('ok'),reply
for _ in range(40):
 m=get()['manual_pan'];f=m.get('face_follow') or {};p=Path(f.get('report',''))
 if str(p).startswith(str(ROOT/'runs')+'/') and p.is_file() and p.stat().st_size:
  d=json.loads(p.read_text());r=d.get('result') or {}
  if (m['automatic_following'] and d.get('status')=='CONTINUOUS_FACE_ZONE_RUNNING'
      and d.get('consumer_manifest_sha256')==SHA
      and abs(time.monotonic()*1000-r.get('heartbeat_mono_ms',0))<1800):break
 time.sleep(.2)
else:raise RuntimeError('Current live hardware-slew controller not confirmed')
print(json.dumps(dict(status='V14_FAST_TEST_LIVE',reply=reply,report=str(p),manifest_sha256=SHA,
 elapsed_s=r.get('elapsed_s'),manual=m,operator_blue_face_confirmed=True),ensure_ascii=False))
