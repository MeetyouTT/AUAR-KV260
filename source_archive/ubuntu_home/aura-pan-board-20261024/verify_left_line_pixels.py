"""Check actual X11 pixels at the requested line; no image leaves the board."""
import json,os,urllib.request
os.environ['DISPLAY']=':0'
import gi
gi.require_version('Gdk','3.0')
from gi.repository import Gdk
Gdk.init([]);root=Gdk.get_default_root_window()
p=Gdk.pixbuf_get_from_window(root,0,0,root.get_width(),root.get_height())
pixels=p.get_pixels();stride=p.get_rowstride();channels=p.get_n_channels()
rows=[]
for y in range(125,400,5):
 values=[]
 for x in range(129,136):
  i=y*stride+x*channels;r,g,b=pixels[i:i+3]
  values.append(g>r+35 and g>b+35)
 rows.append(any(values))
assert sum(rows)>=len(rows)*.85,(sum(rows),len(rows))
print(json.dumps({'status':'LEFT_BOUNDARY_ACTUAL_SCREEN_PIXELS_PASS','x_center':132,'vertical_samples':len(rows),'green_samples':sum(rows),
 'image_saved':False,'motor_commands':0}))
