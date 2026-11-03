import json,os,time,urllib.request
from pathlib import Path
os.environ['DISPLAY']=':0'
import gi,numpy as np
gi.require_version('Gdk','3.0')
from gi.repository import Gdk
Gdk.init([]);root=Gdk.get_default_root_window();rows=[]
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
for _ in range(3):
 pix=Gdk.pixbuf_get_from_window(root,92,112,400,300);stride=pix.get_rowstride();channels=pix.get_n_channels()
 rgb=np.frombuffer(pix.get_pixels(),np.uint8).reshape(300,stride)[:,:400*channels].reshape(300,400,channels)[:,:,:3].astype(np.int16)
 green=np.max(np.abs(rgb[:,36:45]-np.array([67,209,122])),axis=2)<35
 orange=np.max(np.abs(rgb[:,316:330]-np.array([249,168,37])),axis=2)<35
 with o.open('http://127.0.0.1:8783/api/state',timeout=3) as f:u=json.load(f)
 metric=u['ui_runtime'].get('preview_metrics') or {}
 rows.append(dict(green_pixels=int(green.sum()),orange_pixels=int(orange.sum()),
  frame_id=(metric.get('frame_reference') or {}).get('frame_id'),preview_error=metric.get('error'),sink_active=metric.get('sink_active'),
  page=u['ui_page'],automatic_following=u['manual_pan']['automatic_following']))
 time.sleep(.3)
assert all(r['green_pixels']>700 and r['orange_pixels']>1000 and r['sink_active'] for r in rows)
assert len({r['frame_id'] for r in rows})>1 and not any(r['automatic_following'] for r in rows)
status=json.loads(Path('/home/root/aura-pan-current-20261024/da36c36a/face-zone-display-status.json').read_text())
print(json.dumps({'status':'VIDEO_AND_BOTH_ORIGINAL_BOUNDARIES_VISIBLE_IN_X11','samples':rows,'face_display':status,
 'motor_commands':0,'MMIO_opened':False,'scope':'X11 pixels and advancing preview references; physical monitor view not asserted'}))
