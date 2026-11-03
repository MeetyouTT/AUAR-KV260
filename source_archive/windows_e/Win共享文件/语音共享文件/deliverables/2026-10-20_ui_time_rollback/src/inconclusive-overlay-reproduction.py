"""Real GTK/X11/GStreamer test of redraw conflicts in an isolated X server."""
import ctypes as C
import ctypes.util
import json
import sys
import time
import gi
gi.require_version('Gtk','3.0');gi.require_version('GdkX11','3.0')
gi.require_version('Gst','1.0');gi.require_version('GstVideo','1.0')
from gi.repository import Gtk,Gdk,GdkX11,Gst,GstVideo,GLib
Gst.init(None)

class XImage(C.Structure):
    _fields_=[(n,C.c_int) for n in ('width','height','xoffset','format')]+[('data',C.c_void_p)]+[(n,C.c_int) for n in ('byte_order','bitmap_unit','bitmap_bit_order','bitmap_pad','depth','bytes_per_line','bits_per_pixel')]
x=C.CDLL(ctypes.util.find_library('X11'));P=C.c_void_p;U=C.c_ulong
x.XOpenDisplay.argtypes=[C.c_char_p];x.XOpenDisplay.restype=P
x.XGetImage.argtypes=[P,U,C.c_int,C.c_int,C.c_uint,C.c_uint,U,C.c_int];x.XGetImage.restype=C.POINTER(XImage)
x.XDestroyImage.argtypes=[C.POINTER(XImage)];x.XCloseDisplay.argtypes=[P]
display=x.XOpenDisplay(None)
mode=sys.argv[1] if len(sys.argv)>1 else 'legacy'
window=Gtk.Window();window.set_default_size(360,260)
fixed=Gtk.Fixed();window.add(fixed)
area=Gtk.DrawingArea();area.set_size_request(160,120);fixed.put(area,40,40)
label=Gtk.Label(label='changing status');fixed.put(label,30,185)
if mode!='legacy':area.set_double_buffered(False)
if mode=='owned':
    area.set_app_paintable(True)
    area.connect('draw',lambda *_:True)
pipe=Gst.parse_launch('videotestsrc is-live=true pattern=solid-color foreground-color=4294901760 ! video/x-raw,format=RGB16,width=160,height=120,framerate=12/1 ! ximagesink name=sink sync=false handle-events=false force-aspect-ratio=false')
sink=pipe.get_by_name('sink');handle=None;counts={};started=time.monotonic();draws=[0]
def mapped(widget):
    global handle
    handle=GdkX11.X11Window.get_xid(area.get_window())
    Gdk.Display.get_default().sync()
    GstVideo.VideoOverlay.set_window_handle(sink,handle)
    pipe.set_state(Gst.State.PLAYING)
def invalidate():
    draws[0]+=1;label.set_text('changing status '+str(draws[0]));window.queue_draw()
    return True
def sample():
    elapsed=time.monotonic()-started
    if elapsed>3:
        Gtk.main_quit();return False
    if handle and elapsed>.7:
        image=x.XGetImage(display,handle,80,60,1,1,U(-1).value,2)
        if image:
            f=image.contents;raw=C.string_at(f.data,(f.bits_per_pixel+7)//8);n=int.from_bytes(raw,'little');x.XDestroyImage(image)
            counts[n]=counts.get(n,0)+1
    return True
area.connect('map',mapped);window.show_all()
GLib.timeout_add(37,invalidate);GLib.timeout_add(5,sample)
Gtk.main();pipe.set_state(Gst.State.NULL);window.destroy();x.XCloseDisplay(display)
total=sum(counts.values());red=counts.get(0xf800,0)
print(json.dumps({'mode':mode,'samples':total,'red':red,'overwritten':total-red,'pixels':counts,'redraws':draws[0]}),flush=True)
