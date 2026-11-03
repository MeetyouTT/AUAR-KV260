"""Start the current user-authorized trial and immediately record its response."""
import collections,json,subprocess,time,urllib.request
from pathlib import Path
op=urllib.request.build_opener(urllib.request.ProxyHandler({}));base='http://127.0.0.1:8783'
def get(port,path):
 with op.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
def command(kind):
 q=urllib.request.Request(base+'/api/command',data=json.dumps({'type':kind}).encode(),headers={'Origin':base,'Content-Type':'application/json'})
 with op.open(q,timeout=3) as r:return json.load(r)
unit='aura-face-pan-human-stop-38753296190426'
rows=[];start=time.monotonic()
while time.monotonic()-start<20:
 u=get(8783,'/api/state');m=u['manual_pan'];f=m.get('face_follow') or {};p=get(8790,'/v1/motion/face/observation');now=int(time.monotonic()*1000)
 box=p.get('target',{}).get('box') if p.get('target') else None
 rows.append(dict(elapsed_s=round(time.monotonic()-start,3),face_state=p['state'],face_center=(box[0]+box[2]/2)/640 if box else None,
  source_age_ms=now-p['source_mono_ms'] if p.get('source_mono_ms') else None,tracking=p.get('face_tracking'),
  following=m.get('automatic_following'),phase=f.get('phase'),reason=f.get('reason'),commands=f.get('commands_accepted'),pulse_us=m.get('pulse_us'),
  preview_visible=(u['ui_runtime'].get('preview_metrics') or {}).get('frame_visible')))
 if not m.get('automatic_following') and f.get('report'):break
 time.sleep(.15)
u=get(8783,'/api/state');m=u['manual_pan'];path=m.get('face_follow',{}).get('report')
trial=json.loads(Path(path).read_text()) if path and Path(path).is_file() else None
h=get(8790,'/health');s=h['dpu_schedule']
print(json.dumps(dict(stop_timer=unit+'.timer',rows=rows,manual=m,trial=trial,camera_pid=h['pid'],identity_ready=h['identity']['ready'],
 primary=s['primary_period_overruns'],optional={k:s['optional'][k]['overruns'] for k in ('yunet','sface')},physical_human_acceptance='PENDING_USER')))
