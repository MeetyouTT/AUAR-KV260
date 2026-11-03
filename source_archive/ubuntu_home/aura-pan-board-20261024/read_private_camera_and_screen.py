"""Compare source pixels with actual X11 screen, private captures only."""
import base64,json,os,shutil,subprocess,time,urllib.request
os.environ['DISPLAY']=':0'
import gi
gi.require_version('Gdk','3.0')
from gi.repository import Gdk
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8790/v1/ui/status',timeout=3) as r:s=json.load(r)
p=s['preview'];url='http://127.0.0.1:8790/v1/ui/preview.jpg?camera_epoch='+p['camera_epoch']+'&frame_id='+str(p['frame_id'])
with op.open(url,timeout=3) as r:camera=r.read(150000)
Gdk.init([]);root=Gdk.get_default_root_window();frames=[]
for _ in range(3):
 im=Gdk.pixbuf_get_from_window(root,0,0,1024,600);ok,data=im.save_to_bufferv('jpeg',['quality'],['45']);assert ok
 frames.append(base64.b64encode(data).decode());time.sleep(.13)
tree=subprocess.run(['xwininfo','-root','-tree'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True).stdout[-7000:] if shutil.which('xwininfo') else 'xwininfo unavailable'
print(json.dumps({'camera_jpeg_base64':base64.b64encode(camera).decode(),'screens_jpeg_base64':frames,'window_tree':tree}))
