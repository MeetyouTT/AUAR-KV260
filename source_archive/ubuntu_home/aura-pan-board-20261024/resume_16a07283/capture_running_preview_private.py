import base64,json,os,urllib.request
os.environ['DISPLAY']=':0'
import gi
gi.require_version('Gdk','3.0')
from gi.repository import Gdk
Gdk.init([]);root=Gdk.get_default_root_window();pix=Gdk.pixbuf_get_from_window(root,70,70,460,360)
ok,raw=pix.save_to_bufferv('jpeg',['quality'],['45']);assert ok
o=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with o.open('http://127.0.0.1:8790/v1/motion/face/observation',timeout=3) as r:packet=json.load(r)
with o.open('http://127.0.0.1:8783/api/state',timeout=3) as r:u=json.load(r)
assert u['manual_pan']['automatic_following']
print(json.dumps({'private_jpeg_base64':base64.b64encode(raw).decode(),'crop':[70,70,460,360],
 'face_packet':packet,'preview':u['ui_runtime'].get('preview_metrics'),'motor_commands_sent':0,'MMIO_opened':False}))
