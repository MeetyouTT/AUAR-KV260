"""One 25s actual-source idle trial; stop on any newly visible face."""
import json,time,urllib.request
from pathlib import Path
op=urllib.request.build_opener(urllib.request.ProxyHandler({}));base='http://127.0.0.1:8783'
def get(port,path):
 with op.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
def command(kind):
 q=urllib.request.Request(base+'/api/command',data=json.dumps({'type':kind}).encode(),headers={'Origin':base,'Content-Type':'application/json'})
 with op.open(q,timeout=3) as r:return json.load(r)
def health():
 h=get(8790,'/health');s=h['dpu_schedule'];return dict(pid=h['pid'],primary=s['primary_period_overruns'],
  optional={k:s['optional'][k]['overruns'] for k in ('yunet','sface')},identity_ready=h['identity']['ready'],fenced=s['owner_fenced'])
u=get(8783,'/api/state');m=u['manual_pan'];assert m['state']=='READY' and not m['automatic_following'] and m['readback']['flags']==0
face=get(8790,'/v1/motion/face/observation')
if face['state']!='NO_TARGET':print(json.dumps({'status':'NO_EMPTY_SCENE_NO_TEST_STARTED','source_state':face['state'],'movement_commands':0}));raise SystemExit(0)
before=health();ack=command('pan_face_follow');assert ack['ok'];start=time.monotonic();rows=[];interrupted=False
try:
 while time.monotonic()-start<25:
  u=get(8783,'/api/state');m=u['manual_pan'];f=m.get('face_follow',{});v=u['ui_runtime'].get('preview_metrics') or {}
  face=get(8790,'/v1/motion/face/observation')
  rows.append(dict(elapsed_s=round(time.monotonic()-start,3),following=m['automatic_following'],source_state=face['state'],
    phase=f.get('phase'),commands=f.get('commands_accepted'),flags=(m.get('readback') or {}).get('flags'),visible=v.get('frame_visible')))
  if face['state']=='READY' or f.get('commands_accepted',0):interrupted=True;break
  time.sleep(.2)
finally:command('pan_stop')
end=time.monotonic()+8
while time.monotonic()<end:
 u=get(8783,'/api/state');m=u['manual_pan']
 if m['state']=='READY' and not m['automatic_following']:break
 time.sleep(.1)
assert m['state']=='READY' and not m['automatic_following'] and m['readback']['flags']==0 and m['readback']['lease_left_ms']==0
after=health();path=m['face_follow'].get('report');trial=json.loads(Path(path).read_text()) if path else None
assert after['pid']==before['pid'] and not after['fenced']
print(json.dumps({'status':'CONTINUOUS_IDLE_TRIAL_STOPPED','interrupted_for_visible_face':interrupted,'samples':rows,
 'trial':trial,'manual':m,'before':before,'after':after,'primary_delta':after['primary']-before['primary'],
 'optional_delta':{k:after['optional'][k]-before['optional'][k] for k in before['optional']},'physical_tracking_acceptance':False},sort_keys=True))
