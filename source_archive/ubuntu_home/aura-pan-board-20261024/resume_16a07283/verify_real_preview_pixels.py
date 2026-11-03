"""Compare private X11 video pixels with actual camera frames; export metrics."""
import hashlib,json,os,time,urllib.request
os.environ['DISPLAY']=':0'
import cv2,numpy as np,gi
gi.require_version('Gdk','3.0')
from gi.repository import Gdk
Gdk.init([]);root=Gdk.get_default_root_window();op=urllib.request.build_opener(urllib.request.ProxyHandler({}));rows=[]
for _ in range(12):
 with op.open('http://127.0.0.1:8790/v1/ui/status',timeout=3) as r:s=json.load(r)
 p=s['preview'];url='http://127.0.0.1:8790/v1/ui/preview.jpg?camera_epoch='+p['camera_epoch']+'&frame_id='+str(p['frame_id'])
 with op.open(url,timeout=3) as r:raw=r.read(150000)
 expected=cv2.resize(cv2.imdecode(np.frombuffer(raw,np.uint8),cv2.IMREAD_COLOR),(400,300))
 pix=Gdk.pixbuf_get_from_window(root,92,112,400,300);channels=pix.get_n_channels();stride=pix.get_rowstride()
 pixels=np.frombuffer(pix.get_pixels(),np.uint8).reshape(300,stride)[:,:400*channels].reshape(300,400,channels)[:,:,:3]
 actual=pixels[:,:,::-1].copy();mask=np.ones((300,400),dtype=bool);mask[:,316:330]=False;mask[:,36:45]=False
 a,b=actual[mask].astype(float),expected[mask].astype(float)
 rows.append({'source_frame_id':p['frame_id'],'mean_absolute_difference':round(float(np.abs(a-b).mean()),3),
  'correlation':round(float(np.corrcoef(a.ravel(),b.ravel())[0,1]),5),'screen_roi_sha256':hashlib.sha256(actual.tobytes()).hexdigest()})
 time.sleep(.5)
with op.open('http://127.0.0.1:8783/api/state',timeout=3) as r:u=json.load(r)
print(json.dumps({'status':'ACTUAL_X11_PIXELS_CHECK','scope':'current static room camera; not physical HDMI scanout',
 'samples':rows,'all_camera_content_matches':all(r['mean_absolute_difference']<25 and r['correlation']>.9 for r in rows),
 'distinct_screen_frames':len({r['screen_roi_sha256'] for r in rows}),'native_canvas':u.get('native_canvas'),
 'preview':u['ui_runtime'].get('preview_metrics'),'manual_state':u['manual_pan']['state'],'automatic_following':u['manual_pan']['automatic_following'],'physical_commands':0,'MMIO_opened':False}))
