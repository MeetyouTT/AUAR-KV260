"""Capture only the named adjustment dialog, never the camera or desktop."""
import base64,ctypes as C,ctypes.util,hashlib,json,os
os.environ.setdefault('DISPLAY',':0')
import gi
gi.require_version('Gdk','3.0');gi.require_version('GdkX11','3.0')
from gi.repository import Gdk,GdkX11
x=C.CDLL(ctypes.util.find_library('X11'))
x.XOpenDisplay.argtypes=[C.c_char_p];x.XOpenDisplay.restype=C.c_void_p
x.XDefaultRootWindow.argtypes=[C.c_void_p];x.XDefaultRootWindow.restype=C.c_ulong
x.XFetchName.argtypes=[C.c_void_p,C.c_ulong,C.POINTER(C.c_void_p)]
x.XQueryTree.argtypes=[C.c_void_p,C.c_ulong,C.POINTER(C.c_ulong),C.POINTER(C.c_ulong),C.POINTER(C.POINTER(C.c_ulong)),C.POINTER(C.c_uint)]
x.XFree.argtypes=[C.c_void_p];x.XCloseDisplay.argtypes=[C.c_void_p]
d=x.XOpenDisplay(b':0');assert d
todo=[(x.XDefaultRootWindow(d),0)];found=None
while todo:
 wid,level=todo.pop();name=C.c_void_p()
 if x.XFetchName(d,wid,C.byref(name)) and name.value:
  label=C.string_at(name).decode('utf-8',errors='replace');x.XFree(name)
  if label=='转轴调节':found=wid;break
 if level>=3:continue
 root=C.c_ulong();parent=C.c_ulong();children=C.POINTER(C.c_ulong)();count=C.c_uint()
 if x.XQueryTree(d,wid,C.byref(root),C.byref(parent),C.byref(children),C.byref(count)):
  todo.extend((children[i],level+1) for i in range(count.value))
  if children:x.XFree(children)
x.XCloseDisplay(d)
result={'dialog_found':bool(found),'artifacts':{}}
if found:
 display=Gdk.Display.open(':0');window=GdkX11.X11Window.foreign_new_for_display(display,found)
 a,b,w,h=window.get_geometry();assert 0<w<=800 and 0<h<=500
 pix=Gdk.pixbuf_get_from_window(window,0,0,w,h);ok,raw=pix.save_to_bufferv('png',[],[]);assert ok
 result.update(dialog_size=[w,h]);result['artifacts']['dialog-only.png']={'base64':base64.b64encode(raw).decode(),'sha256':hashlib.sha256(raw).hexdigest()}
print(json.dumps(result),flush=True)
