import json,time,urllib.request
from pathlib import Path
R=Path('/home/root/aura-pan-current-20261024/16a07283')
P=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/continuous-v10r12')
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
def toggle():
 base='http://127.0.0.1:8783'
 q=urllib.request.Request(base+'/api/command',data=b'{"type":"pan_face_follow"}',headers={'Origin':base,'Content-Type':'application/json'})
 with o.open(q,timeout=4) as r:reply=json.load(r)
 assert reply.get('ok'),reply
 return reply
s=json.loads((R/'state.json').read_text())
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==s['boot']
assert s['face_source_version']==16
cfg=json.loads((R/'gui-manual-bound-v1/runtime/aura/config/pan_face.local.json').read_text())
assert cfg['release_root']==str(P)
h=get(8790,'/health');m=get(8783,'/api/state')['manual_pan']
assert h['pid']==s['current_camera_pid'] and not h['dpu_schedule']['owner_fenced']
assert m['state']=='READY' and not m['automatic_following']
assert m['readback']['flags']==0 and m['readback']['lease_left_ms']==0
tag=str(time.monotonic_ns());evidence=R/('r12-v16-supervised-'+tag+'.json')
data=dict(boot_id=s['boot'],before_manual=m,primary_before=h['dpu_schedule']['primary_period_overruns'],samples=[],report=None,physical_motion_verified=False)
began=time.monotonic();report=None;error=None;stop_error=None
try:
 data['start_reply']=toggle();began=time.monotonic()
 while time.monotonic()-began<30:
  m=get(8783,'/api/state')['manual_pan'];f=m.get('face_follow') or {}
  sample=dict(elapsed_s=round(time.monotonic()-began,3))
  if f.get('report'):
   p=Path(f['report']);assert str(p).startswith(str(P/'runs')+'/')
   if p.exists():
    report=json.loads(p.read_text());assert report['boot_id']==s['boot'] and report['consumer_manifest_sha256']==cfg['manifest_sha256']
    data['report']=str(p);sample['result']=report.get('result');sample['observations']=report.get('observation_trace',[])
  data['samples'].append(sample)
  if report and report.get('result',{}).get('fatal'):raise RuntimeError('Follow fatal: '+str(report['result'].get('reason')))
  if not m['automatic_following'] and time.monotonic()-began>2:raise RuntimeError('Follow ended early')
  time.sleep(.45)
except BaseException as exc:error=type(exc).__name__+': '+str(exc)[:200]
finally:
 try:
  m=get(8783,'/api/state')['manual_pan']
  if m['automatic_following']:data['stop_reply']=toggle()
  deadline=time.monotonic()+12
  while time.monotonic()<deadline:
   m=get(8783,'/api/state')['manual_pan'];rb=m.get('readback') or {}
   if not m['automatic_following'] and m['state']=='READY' and rb.get('flags')==0 and rb.get('lease_left_ms')==0:break
   time.sleep(.2)
  data['after_manual']=m
  assert not m['automatic_following'] and m['state']=='READY' and m['readback']['flags']==0 and m['readback']['lease_left_ms']==0
 except BaseException as exc:stop_error=type(exc).__name__+': '+str(exc)[:200]
 if data['report']:
  report=json.loads(Path(data['report']).read_text());data['final_report']=report
 data.update(error=error,stop_error=stop_error,elapsed_s=round(time.monotonic()-began,3))
 evidence.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
h=get(8790,'/health')
out=dict(status='STOPPED' if not stop_error else 'STOP_NOT_VERIFIED',error=error,stop_error=stop_error,
 evidence=str(evidence),report=data['report'],elapsed_s=data['elapsed_s'],after_manual=data.get('after_manual'),
 primary_before=data['primary_before'],primary_after=h['dpu_schedule']['primary_period_overruns'])
if report:
 for key in ('status','input_summary','input_timing'):out['follow_'+key]=report.get(key)
 r=report.get('result',{});out['result']={k:r.get(k) for k in ('state','reason','pulse_us','commands_accepted','motion_target_changes','segments','fatal','stopped')}
print(json.dumps(out))
assert not stop_error,stop_error
