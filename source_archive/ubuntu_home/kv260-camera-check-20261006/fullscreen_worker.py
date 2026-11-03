#!/usr/bin/env python3
"""Explicit full-screen X11 window and UVC MJPEG preview, with frame evidence."""
import ctypes as C
import ctypes.util
import json
import signal
import time
from pathlib import Path
import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstVideo', '1.0')
from gi.repository import Gst, GstVideo, GLib

ROOT = Path('/home/root/aura-camera-check-20261006')
STATUS = ROOT / 'fullscreen-status.json'
x = C.CDLL(ctypes.util.find_library('X11'))
def bind(name, result, args):
    f = getattr(x, name)
    f.restype, f.argtypes = result, args
    return f
P, U, I = C.c_void_p, C.c_ulong, C.c_int
bind('XInitThreads', I, [])()
d = bind('XOpenDisplay', P, [C.c_char_p])(b':0')
assert d, 'Cannot open X display :0'
root = bind('XDefaultRootWindow', U, [P])(d)
w = bind('XDisplayWidth', I, [P, I])(d, 0)
h = bind('XDisplayHeight', I, [P, I])(d, 0)
window = bind('XCreateSimpleWindow', U, [P, U, I, I, C.c_uint, C.c_uint, C.c_uint, U, U])(d, root, 0, 0, w, h, 0, 0, 0)
class Attributes(C.Structure):
    _fields_ = [('background_pixmap', U), ('background_pixel', U), ('border_pixmap', U), ('border_pixel', U), ('bit_gravity', I), ('win_gravity', I), ('backing_store', I), ('backing_planes', U), ('backing_pixel', U), ('save_under', I), ('event_mask', C.c_long), ('do_not_propagate_mask', C.c_long), ('override_redirect', I), ('colormap', U), ('cursor', U)]
attrs = Attributes()
attrs.override_redirect = 1
bind('XChangeWindowAttributes', I, [P, U, U, C.POINTER(Attributes)])(d, window, 1 << 9, C.byref(attrs))
bind('XStoreName', I, [P, U, C.c_char_p])(d, window, b'AURA USB Camera Preview')
bind('XMapRaised', I, [P, U])(d, window)
bind('XSync', I, [P, I])(d, 0)
Gst.init(None)
pipeline = Gst.parse_launch('v4l2src device=/dev/video0 io-mode=mmap ! video/x-raw,format=YUY2,width=640,height=480,framerate=30/1 ! videoconvert ! videoscale ! video/x-raw,width=%d,height=%d ! identity name=counter signal-handoffs=true ! ximagesink name=screen sync=false force-aspect-ratio=true' % (w, h))
sink = pipeline.get_by_name('screen')
GstVideo.VideoOverlay.set_window_handle(sink, window)
loop = GLib.MainLoop()
started = time.monotonic()
state = {'frames': 0, 'window': int(window), 'size': [w, h], 'device': '/dev/video0', 'error': None}
def frame(element, buffer):
    state['frames'] += 1
pipeline.get_by_name('counter').connect('handoff', frame)
def record():
    state['elapsed_s'] = round(time.monotonic() - started, 3)
    temporary = STATUS.with_suffix('.tmp')
    temporary.write_text(json.dumps(state))
    temporary.replace(STATUS)
    return True
def message(bus, msg):
    if msg.type == Gst.MessageType.ERROR:
        err, debug = msg.parse_error()
        state['error'] = str(err) + ': ' + str(debug)
        record()
        loop.quit()
    elif msg.type == Gst.MessageType.EOS:
        loop.quit()
bus = pipeline.get_bus()
bus.add_signal_watch()
bus.connect('message', message)
signal.signal(signal.SIGTERM, lambda *_: loop.quit())
signal.signal(signal.SIGINT, lambda *_: loop.quit())
GLib.timeout_add_seconds(1, record)
try:
    result = pipeline.set_state(Gst.State.PLAYING)
    assert result != Gst.StateChangeReturn.FAILURE, 'Cannot start camera pipeline'
    record()
    loop.run()
finally:
    pipeline.set_state(Gst.State.NULL)
    record()
    bind('XDestroyWindow', I, [P, U])(d, window)
    bind('XCloseDisplay', I, [P])(d)
