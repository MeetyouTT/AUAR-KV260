import json,subprocess,time,urllib.request
from pathlib import Path
o=urllib.request.build_opener(urllib.request.ProxyHandler({}));base='http://127.0.0.1:8783'
def get():
 with o.open(base+'/api/state',timeout=3) as r:return json.load(r)
u=get();m=u['manual_pan'];p=m.get('face_follow',{}).get('report')
if p:
 r=json.loads(Path(p).read_text());assert r['consumer_manifest_sha256']=='613c48ab7d3277220f20cca87006f8f94879a93febb482fb73af550b5f485f6d' and not r['result']['fatal']
subprocess.run(['systemctl','stop','aura-face-pan-human-stop-39027800634679.timer'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
if not m.get('automatic_following'):
 assert m['state']=='READY' and m['readback']['flags']==0 and m['readback']['lease_left_ms']==0
 q=urllib.request.Request(base+'/api/command',data=b'{"type":"pan_face_follow"}',headers={'Origin':base,'Content-Type':'application/json'})
 with o.open(q,timeout=3) as r:assert json.load(r).get('ok')
 time.sleep(1.)
u=get();print(json.dumps({'manual':u['manual_pan'],'preview':u['ui_runtime'].get('preview_metrics'),'diagnostic_timer_removed':True,'scope':'continuous face following; source expiry and bounded segments unchanged'}))
