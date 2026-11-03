"""Start the current user-authorized trial and immediately record its response."""
import collections,json,subprocess,time,urllib.request
from pathlib import Path
op=urllib.request.build_opener(urllib.request.ProxyHandler({}));base='http://127.0.0.1:8783'
def get(port,path):
 with op.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
def command(kind):
 q=urllib.request.Request(base+'/api/command',data=json.dumps({'type':kind}).encode(),headers={'Origin':base,'Content-Type':'application/json'})
 with op.open(q,timeout=3) as r:return json.load(r)
u=get(8783,'/api/state');m=u['manual_pan'];h=get(8790,'/health');s=h['dpu_schedule']
assert h['identity']['ready'] and not s['owner_fenced']
assert m['state']=='READY' and not m['automatic_following'] and m['readback']['flags']==0 and m['readback']['lease_left_ms']==0
for old in ['aura-face-pan-human-stop-38577326481905.timer']:
 subprocess.run(['systemctl','stop',old],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
stop_code="import json,urllib.request; b='http://127.0.0.1:8783'; q=urllib.request.Request(b+'/api/command',data=b'{\"type\":\"pan_stop\"}',headers={'Origin':b,'Content-Type':'application/json'}); o=urllib.request.build_opener(urllib.request.ProxyHandler({})); r=o.open(q,timeout=4); assert json.load(r).get('ok')"
unit='aura-face-pan-human-stop-'+str(time.monotonic_ns())
subprocess.run(['systemd-run','--quiet','--collect','--unit='+unit,'--on-active=180s','--timer-property=AccuracySec=1s','/usr/bin/python3','-B','-c',stop_code],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=6)
ack=command('pan_face_follow');assert ack.get('ok'),ack
time.sleep(1.)
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
