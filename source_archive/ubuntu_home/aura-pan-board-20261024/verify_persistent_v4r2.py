"""Keep the user-confirmed face follower enabled and audit its current release."""
import hashlib,json,subprocess,time,urllib.request
from pathlib import Path
F=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5')
N=Path('/home/root/aura-pan-current-20261024/463c9307/gui-face-edge-v5');A=N/'runtime/aura'
o=urllib.request.build_opener(urllib.request.ProxyHandler({}));base='http://127.0.0.1:8783'
def get(port,path):
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
cfg=json.loads((N/'startup/config.json').read_text());assert all(sha(A/n)==h for n,h in cfg['component_sha256'].items())
face=json.loads((A/'config/pan_face.local.json').read_text());assert face['release_root']==str(F/'continuous-v4r2')
consumer=F/'continuous-v4r2/deployment-manifest.json';assert sha(consumer)==face['manifest_sha256']=='613c48ab7d3277220f20cca87006f8f94879a93febb482fb73af550b5f485f6d'
assert all(sha(x['destination'])==x['sha256'] for x in json.loads(consumer.read_text())['files'])
source=F/'face-source-v9/deployment-manifest.json';assert sha(source)=='875f5c4fb3cde6c827063716eed52162a38caeb743b018f7e308a1a82da0055d'
assert all(sha(p)==h for p,h in json.loads(source.read_text())['pins'].items())
h=get(8790,'/health');assert h['identity']['ready'] and not h['dpu_schedule']['owner_fenced']
u=get(8783,'/api/state');m=u['manual_pan'];old=m.get('face_follow',{})
if old.get('report'):
 report=json.loads(Path(old['report']).read_text())
 assert report['consumer_manifest_sha256']==sha(consumer)
 assert not report.get('result',{}).get('fatal')
# This timer belongs only to our finite diagnostic window. The requested
# product mode stays active; source expiry and bounded segments remain live.
timer='aura-face-pan-human-stop-39027800634679.timer'
subprocess.run(['systemctl','stop',timer],stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
if not m.get('automatic_following'):
 assert m['state']=='READY' and m['readback']['flags']==0 and m['readback']['lease_left_ms']==0
 q=urllib.request.Request(base+'/api/command',data=b'{"type":"pan_face_follow"}',headers={'Origin':base,'Content-Type':'application/json'})
 with o.open(q,timeout=3) as r:assert json.load(r).get('ok')
 time.sleep(1.)
rows=[];began=time.monotonic()
while time.monotonic()-began<8:
 u=get(8783,'/api/state');m=u['manual_pan'];p=get(8790,'/v1/motion/face/observation')
 rows.append(dict(following=m.get('automatic_following'),phase=m.get('face_follow',{}).get('phase'),
  reason=m.get('face_follow',{}).get('reason'),pulse_us=m.get('pulse_us'),face_state=p['state'],
  face_tracking=p.get('face_tracking'),source_age_ms=int(time.monotonic()*1000)-p['source_mono_ms'] if p.get('source_mono_ms') else None,
  preview_visible=u['ui_runtime'].get('preview_metrics',{}).get('frame_visible')))
 if not m.get('automatic_following'):break
 time.sleep(.25)
u=get(8783,'/api/state');m=u['manual_pan'];report=json.loads(Path(m['face_follow']['report']).read_text())
h=get(8790,'/health');s=h['dpu_schedule']
print(json.dumps(dict(status='PERSISTENT_FACE_FOLLOW_AUDIT',pins=len(cfg['component_sha256']),consumer_sha256=sha(consumer),source_sha256=sha(source),
 camera_pid=h['pid'],gui_pid=int(subprocess.check_output(['systemctl','show','aura-avatar-ui.service','-p','MainPID','--value'],text=True)),
 identity_ready=h['identity']['ready'],identity_error=h['identity']['error'],owner_fenced=s['owner_fenced'],primary=s['primary_period_overruns'],
 optional={k:{'overruns':s['optional'][k]['overruns'],'state':s['optional'][k].get('state')} for k in ('yunet','sface')},
 manual=m,trial=report,rows=rows,cancelled_diagnostic_timer=timer,mode='continuous_face_zone',
 physical_confirmation='User confirmed sustained rotation; smoothness and return-to-zone awaiting response')))
