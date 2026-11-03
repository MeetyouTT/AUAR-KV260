"""Capture the user's held left position using face centers only, no actuation."""
import json,statistics,time,urllib.request,os
from pathlib import Path
F=Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5');D=F/'user-zone';o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=2) as r:return json.load(r)
u=get(8783,'/api/state');m=u['manual_pan'];assert m['state']=='READY' and not m['automatic_following'] and m['readback']['flags']==0 and m['readback']['lease_left_ms']==0
rows=[];seen=set();start=time.monotonic();context=None
while time.monotonic()-start<8 and len(rows)<10:
 p=get(8790,'/v1/motion/face/observation');now=int(time.monotonic()*1000)
 if p.get('state')=='READY' and p.get('target_kind')=='face' and 0<=now-p['source_mono_ms']<250:
  t=p['target'];key=(p['service_epoch'],p['camera_epoch'],t['track_id'],t['track_generation']);ident=p['source_frame_id']
  if context is None:context=key
  if key==context and ident not in seen:
   x,y,w,h=t['box'];rows.append({'center':(x+w/2)/p['frame_width'],'width':w/p['frame_width'],'source_frame_id':ident,'source_mono_ms':p['source_mono_ms']});seen.add(ident)
 time.sleep(.04)
if len(rows)<6:
 print(json.dumps({'status':'LEFT_NOT_CAPTURED','ready_sources':len(rows),'reason':'Face not continuously confirmed; hold face inside frame','movement_commands':0}));raise SystemExit(0)
centers=[x['center'] for x in rows];value=statistics.median(centers);assert max(centers)-min(centers)<.08
D.mkdir(mode=0o700,exist_ok=True);path=D/'calibration.json';assert not path.exists()
data={'schema':'aura-user-face-zone-1','state':'LEFT_CAPTURED_WAITING_RIGHT','boot_id':p['board_boot_id'],'camera_epoch':p['camera_epoch'],
 'frame_width':p['frame_width'],'frame_height':p['frame_height'],'mirror_horizontal':p['mirror_horizontal'],
 'reference_command_us':m['readback']['width_us'],'target_kind':'face','left_center_ratio':value,'left_samples':rows,'left_width_ratio':statistics.median([x['width'] for x in rows]),'created_mono_ns':time.monotonic_ns()}
with path.open('x') as f:json.dump(data,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
print(json.dumps({'status':data['state'],'left_center_ratio':round(value,4),'source_samples':len(rows),'spread':round(max(centers)-min(centers),4),'target_kind':'face','movement_commands':0}))
