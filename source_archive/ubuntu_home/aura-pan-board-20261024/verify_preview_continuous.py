"""Thirty seconds of live preview plus private pixel hashes; no images exported."""
import hashlib,json,os,statistics,time,urllib.request
os.environ['DISPLAY']=':0'
import gi
gi.require_version('Gdk','3.0')
from gi.repository import Gdk
Gdk.init([]);window=Gdk.get_default_root_window()
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(port,path):
 with o.open('http://127.0.0.1:%d%s'%(port,path),timeout=3) as r:return json.load(r)
def health():
 h=get(8790,'/health');s=h['dpu_schedule']
 return {'pid':h['pid'],'frames':h['detected_frames'],'capture':h['capture_frames'],'primary':s['primary_period_overruns'],
  'optional':{k:s['optional'][k]['overruns'] for k in ('yunet','sface')},'camera_error':h['camera_error'],'fenced':s['owner_fenced']}
b=health();rows=[];pixels=[];start=time.monotonic();next_at=start
while time.monotonic()-start<30:
 u=get(8783,'/api/state');v=u['ui_runtime'];p=v.get('preview_metrics') or {};ref=p.get('frame_reference')
 rows.append({'elapsed_s':round(time.monotonic()-start,3),'page':u.get('ui_page'),'visible':p.get('frame_visible'),
  'frame_id':ref.get('frame_id') if ref else None,'hz':p.get('update_hz'),'error':p.get('error'),'active':p.get('sink_active'),
  'manual_state':u['manual_pan']['state'],'automatic_following':u['manual_pan']['automatic_following']})
 if len(pixels)==0 or len(pixels)==1 and time.monotonic()-start>=14 or len(pixels)==2 and time.monotonic()-start>=28:
  image=Gdk.pixbuf_get_from_window(window,20,130,530,250);raw=bytes(image.get_pixels());sample=raw[::97]
  pixels.append({'elapsed_s':round(time.monotonic()-start,3),'sha256':hashlib.sha256(raw).hexdigest(),'sample_stdev':round(statistics.pstdev(sample),2)})
 next_at+=.5;time.sleep(max(0,next_at-time.monotonic()))
a=health();u=get(8783,'/api/state');m=u['manual_pan'];r=m['readback']
fd=os.open('/dev/kmsg',os.O_RDONLY|os.O_NONBLOCK);os.lseek(fd,0,os.SEEK_END);count=0;until=time.monotonic()+.3
try:
 while time.monotonic()<until:
  try:
   if b"couldn't access mem fast enough" in os.read(fd,8192):count+=1
  except BlockingIOError:time.sleep(.002)
  except OSError:pass
finally:os.close(fd)
summary={'elapsed_s':round(time.monotonic()-start,3),'samples':len(rows),'visible_samples':sum(bool(x['visible']) for x in rows),
 'missing_samples':sum(not x['visible'] for x in rows),'error_samples':sum(bool(x['error']) for x in rows),
 'unique_displayed_source_frames':len({x['frame_id'] for x in rows if x['frame_id'] is not None}),
 'pixel_roi_samples':pixels,'pixel_hashes_unique':len({x['sha256'] for x in pixels}),
 'camera_pid':a['pid'],'camera_pid_unchanged':a['pid']==b['pid'],'detected_delta':a['frames']-b['frames'],'capture_delta':a['capture']-b['capture'],
 'primary_delta':a['primary']-b['primary'],'optional_delta':{k:a['optional'][k]-b['optional'][k] for k in ('yunet','sface')},
 'usb_warnings_300ms':count,'manual_state':m['state'],'flags':r['flags'],'lease_ms':r['lease_left_ms'],'automatic_following':m['automatic_following']}
print(json.dumps({'summary':summary,'rows':rows},sort_keys=True))
