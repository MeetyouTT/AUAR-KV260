import hashlib,json,re,subprocess,time,urllib.request
from pathlib import Path
base='http://127.0.0.1:8783';o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get():
 with o.open(base+'/api/state',timeout=3) as r:return json.load(r)
raw=subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','ExecStart','--value'],text=True)
sc=Path(re.search(r'--config (/[^ ;]+)',raw).group(1));startup=json.loads(sc.read_text());app=Path(startup['runtime'])/'aura'
assert all(hashlib.sha256((app/n).read_bytes()).hexdigest()==v for n,v in startup['component_sha256'].items())
manual_cfg=json.loads((app/'config/pan_manual.local.json').read_text())
cfg=json.loads(Path(manual_cfg['face_follow_config']).read_text())
assert cfg['release_root'].endswith('/continuous-v12r1') and cfg['duration_s']==60
before=get();m=before['manual_pan'];assert before['phase']=='IDLE' and not before.get('playing') and before.get('audio_output_state')=='IDLE_READY'
assert m['state']=='READY' and not m['automatic_following'] and m['readback']['flags']==0 and m['readback']['lease_left_ms']==0
q=urllib.request.Request(base+'/api/command',data=b'{"type":"pan_face_follow"}',headers={'Origin':base,'Content-Type':'application/json'})
with o.open(q,timeout=4) as r:reply=json.load(r)
assert reply.get('ok'),reply
root=Path(cfg['release_root']);after=None;report=None
try:
 for _ in range(40):
  time.sleep(.2);after=get()['manual_pan'];follow=after.get('face_follow') or {}
  if follow.get('report') and str(follow['report']).startswith(str(root/'runs')+'/'):
   p=Path(follow['report'])
   if p.is_file() and p.stat().st_size:
    report=json.loads(p.read_text())
    if report.get('consumer_manifest_sha256')==cfg['manifest_sha256'] and report.get('status')=='CONTINUOUS_FACE_ZONE_RUNNING':break
 else:raise RuntimeError('Current v12 report not confirmed; start rejected')
 assert after['automatic_following']
except BaseException:
 q=urllib.request.Request(base+'/api/command',data=b'{"type":"pan_stop"}',headers={'Origin':base,'Content-Type':'application/json'})
 with o.open(q,timeout=4) as r:r.read()
 raise
print(json.dumps(dict(status='V12_ATTENDED_WINDOW_ACTUAL_PROCESS_VERIFIED',reply=reply,duration_s=60,manual=after,consumer_manifest_sha256=report['consumer_manifest_sha256'],operator_present=True,mechanical_smoothness_verified=False),ensure_ascii=False))
