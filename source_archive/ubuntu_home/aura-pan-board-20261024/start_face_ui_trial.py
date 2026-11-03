"""Exercise the visible finite follow control and record only anonymous results."""
import json,time,urllib.request
from pathlib import Path
o=urllib.request.build_opener(urllib.request.ProxyHandler({}));base='http://127.0.0.1:8783'
def get(port,path):
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
def brief():
 h=get(8790,'/health');s=h['dpu_schedule']
 return {'pid':h['pid'],'frames':h['detected_frames'],'primary':s['primary_period_overruns'],
  'optional':{k:s['optional'][k]['overruns'] for k in ('yunet','sface')},'fenced':s['owner_fenced']}
u=get(8783,'/api/state');m=u['manual_pan'];r=m['readback'];b=brief();previous_report=m.get('face_follow',{}).get('report')
assert u['phase']=='IDLE' and m['state']=='READY' and r['flags']==0 and r['lease_left_ms']==0 and 'face_follow' in m
start=time.monotonic();req=urllib.request.Request(base+'/api/command',data=b'{"type":"pan_face_follow"}',headers={'Origin':base,'Content-Type':'application/json'})
with o.open(req,timeout=3) as reply:ack=json.load(reply);assert ack.get('ok'),ack
seen=False;rows=[];end=time.monotonic()+22;final=None
while time.monotonic()<end:
 u=get(8783,'/api/state');p=u['manual_pan'];v=u['ui_runtime'].get('preview_metrics') or {}
 seen=seen or p.get('automatic_following',False)
 rows.append({'elapsed_s':round(time.monotonic()-start,3),'state':p['state'],'following':p.get('automatic_following'),
  'preview_visible':v.get('frame_visible'),'preview_hz':v.get('update_hz')})
 follow=p.get('face_follow') or {}
 if (follow.get('report') and follow['report']!=previous_report and not p.get('automatic_following') and p['state']=='READY'):final=p;break
 time.sleep(.1)
assert final is not None,'Finite control did not restore manual readiness'
report=final['face_follow'].get('report');trial=json.loads(Path(report).read_text()) if report else None
a=brief();assert a['pid']==b['pid'] and not a['fenced'];r=final['readback'];assert r['flags']==0 and r['lease_left_ms']==0
print(json.dumps({'gui_control_ack':ack,'automatic_mode_seen':seen,'manual':final,'trial':trial,'samples':rows,
 'camera_pid':a['pid'],'primary_delta':a['primary']-b['primary'],
 'optional_delta':{k:a['optional'][k]-b['optional'][k] for k in ('yunet','sface')},'physical_observation':'PENDING_USER'},sort_keys=True))
