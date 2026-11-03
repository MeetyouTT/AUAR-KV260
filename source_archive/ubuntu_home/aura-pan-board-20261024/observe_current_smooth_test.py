"""Record anonymous face position and actuator response during the live trial."""
import json,time,urllib.request
from pathlib import Path
op=urllib.request.build_opener(urllib.request.ProxyHandler({}));rows=[];start=time.monotonic()
def get(port,path):
 with op.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
while time.monotonic()-start<8:
 u=get(8783,'/api/state');m=u['manual_pan'];f=m.get('face_follow') or {};p=get(8790,'/v1/motion/face/observation');v=u['ui_runtime'].get('preview_metrics') or {}
 center=None
 if p.get('state')=='READY':
  x,y,w,h=p['target']['box'];center=(x+w/2)/p['frame_width']
 rows.append({'elapsed_s':round(time.monotonic()-start,3),'face_state':p['state'],'face_center':center,'following':m.get('automatic_following'),
  'phase':f.get('phase'),'reason':f.get('reason'),'commands':f.get('commands_accepted'),
  'pulse_us':m.get('pulse_us'),'readback':m.get('readback'),'preview_visible':v.get('frame_visible'),
  'identity_state':(u['ui_runtime'].get('snapshot') or {}).get('modules',{}).get('identity',{}).get('state')})
 if not m.get('automatic_following') and f.get('report'):break
 time.sleep(.2)
u=get(8783,'/api/state');m=u['manual_pan'];path=m.get('face_follow',{}).get('report');trial=json.loads(Path(path).read_text()) if path and Path(path).is_file() else None
h=get(8790,'/health');s=h['dpu_schedule']
print(json.dumps({'samples':rows,'manual':m,'trial':trial,'camera_pid':h['pid'],'identity_ready':h['identity']['ready'],'identity_error':h['identity']['error'],
 'primary':s['primary_period_overruns'],'optional':{k:s['optional'][k]['overruns'] for k in ('yunet','sface')},'physical_observation':'PENDING_USER'},sort_keys=True))
