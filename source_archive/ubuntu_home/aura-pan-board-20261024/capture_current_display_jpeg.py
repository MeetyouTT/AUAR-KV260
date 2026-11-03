"""Private display capture for debugging preview placement, never shared."""
import base64,json,os
os.environ['DISPLAY']=':0'
import gi
gi.require_version('Gdk','3.0')
from gi.repository import Gdk
Gdk.init([]);root=Gdk.get_default_root_window();w=root.get_width();h=root.get_height()
image=Gdk.pixbuf_get_from_window(root,0,0,w,h);ok,raw=image.save_to_bufferv('jpeg',['quality'],['65']);assert ok
print(json.dumps({'width':w,'height':h,'jpeg_base64':base64.b64encode(raw).decode()}))
