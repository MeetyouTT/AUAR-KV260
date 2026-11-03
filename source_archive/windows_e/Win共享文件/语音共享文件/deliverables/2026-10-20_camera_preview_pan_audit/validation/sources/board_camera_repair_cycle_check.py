"""Real UI page/panel cycles and 20 s freshness audit; no pan jog."""
import json,sys,time,urllib.request
from pathlib import Path
from PIL import Image,ImageChops,ImageStat
p=Path('/home/root/aura-pan-manual-ui-20261020/camera-fix-v3')
config=json.loads((p/'startup/config.json').read_text());root=Path(config['runtime'])/'aura';sys.path.insert(0,str(root))
from board.vision.local_preview import RawFrameReader
from tools.board_screen_capture import capture
op=urllib.request.build_opener(urllib.request.ProxyHandler({}));url='http://127.0.0.1:8783'
def api(data=None):
 req=url+'/api/state' if data is None else urllib.request.Request(url+'/api/command',data=json.dumps(data).encode(),headers={'Content-Type':'application/json','Origin':url})
 with op.open(req,timeout=1) as r:return json.load(r)
def pixels(name):
 with op.open('http://127.0.0.1:8790/v1/ui/status',timeout=1) as r:snap=json.load(r)
 owner={k:snap[k] for k in ['board_boot_id','service_epoch']};owner['camera_epoch']=snap['preview']['camera_epoch']
 header,data=RawFrameReader(owner).read(int(time.monotonic()*1000));target=p/(name+'-private.png');capture(target)
 with Image.open(str(target)) as screen:
  current=screen.crop((92,112,492,412)).resize((64,48))
  source=Image.frombytes('RGB',(640,480),data,'raw','BGR').resize((64,48))
  delta=sum(ImageStat.Stat(ImageChops.difference(current,source)).mean)/3
 assert delta<60,(name,delta)
 return {'source_frame':header['frame_id'],'mean_abs_rgb_difference':round(delta,3)}
v={'movement_commands_sent':0,'cycles':[],'samples':[],'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
before=api();v['pan_before']=before['manual_pan']
for i in range(2):
 acts=[api({'type':'pan_close'}),api({'type':'ui_page','page':'main'})]
 time.sleep(.3);acts.append(api({'type':'ui_page','page':'vision'}));time.sleep(.7)
 acts.append(api({'type':'pan_dialog'}));time.sleep(.2)
 assert all(a.get('ok') for a in acts),acts
 v['cycles'].append({'index':i,'actions':acts,'screen':pixels('cycle-'+str(i))})
start=time.monotonic()
for _ in range(40):
 time.sleep(.5);s=api();q=s.get('ui_runtime',{});r=q.get('preview_metrics',{});ref=r.get('frame_reference')
 v['samples'].append({'elapsed':round(time.monotonic()-start,3),'ui_sequence':s['sequence'],'tick_ms':s['ui_tick_ms'],'link':q.get('link'),
  'visible':r.get('frame_visible'),'error':r.get('error'),'frame_id':ref.get('frame_id') if ref else None,'update_hz':r.get('update_hz')})
after=api();pan=after['manual_pan'];v['pan_after']=pan;v['final_screen']=pixels('steady-final')
assert pan['state']=='READY' and pan['pulse_us']==v['pan_before']['pulse_us']
assert pan['readback']['flags']==0 and pan['readback']['lease_left_ms']==0
assert pan['readback']['epoch']==v['pan_before']['readback']['epoch'] and pan['history']==[]
assert all(not r['error'] and r['link']=='READY' for r in v['samples'])
assert v['samples'][-1]['ui_sequence']>v['samples'][0]['ui_sequence']
ids=[r['frame_id'] for r in v['samples'] if r['frame_id']]
assert len(set(ids))>=30 and ids[-1]>ids[0]
v.update(status='REAL_UI_CYCLES_AND_FRESHNESS_PASS',duration_seconds=round(time.monotonic()-start,3),fresh_samples=len(ids),unique_source_frames=len(set(ids)))
print(json.dumps(v),flush=True)
