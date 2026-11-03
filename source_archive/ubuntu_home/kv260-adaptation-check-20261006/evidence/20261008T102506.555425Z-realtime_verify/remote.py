"""Read current live status and the real X11 framebuffer; no camera open."""
import base64
import ctypes as C
import ctypes.util
import json
from pathlib import Path
import subprocess
import time

current = json.loads(Path('/home/root/aura-realtime-vision-20261007/current.json').read_text())
root = Path(current['run_root'])
before = json.loads((root/'status.json').read_text())
time.sleep(3)
after = json.loads((root/'status.json').read_text())
owners = []
for proc in Path('/proc').iterdir():
    if not proc.name.isdecimal():
        continue
    try:
        if any(fd.resolve()==Path('/dev/video0') for fd in (proc/'fd').iterdir()):
            owners.append(int(proc.name))
    except (FileNotFoundError,PermissionError):
        pass
display = subprocess.run(['xset','-display',':0','q'],capture_output=True,text=True,timeout=10)
x = C.CDLL(ctypes.util.find_library('X11'))
P, U, I = C.c_void_p, C.c_ulong, C.c_int
def bind(name,result,args):
    f = getattr(x,name)
    f.restype,f.argtypes = result,args
    return f
d = bind('XOpenDisplay',P,[C.c_char_p])(b':0')
assert d
window = bind('XDefaultRootWindow',U,[P])(d)
w = bind('XDisplayWidth',I,[P,I])(d,0)
h = bind('XDisplayHeight',I,[P,I])(d,0)
im = bind('XGetImage',P,[P,U,I,I,C.c_uint,C.c_uint,U,I])(d,window,0,0,w,h,U(-1).value,2)
assert im
class XImage(C.Structure):
    _fields_ = [('width',I),('height',I),('xoffset',I),('format',I),('data',P),('byte_order',I),('bitmap_unit',I),('bitmap_bit_order',I),('bitmap_pad',I),('depth',I),('bytes_per_line',I),('bits_per_pixel',I),('red_mask',U),('green_mask',U),('blue_mask',U)]
info = C.cast(im,C.POINTER(XImage)).contents
assert info.bits_per_pixel in [16,32] and info.byte_order in [0,1]
import numpy as np
import cv2
raw = C.string_at(info.data,info.bytes_per_line*h)
pixel_bytes = info.bits_per_pixel//8
dtype = ('<' if info.byte_order==0 else '>')+'u'+str(pixel_bytes)
pixels = np.ndarray((h,w),dtype=dtype,buffer=raw,strides=(info.bytes_per_line,pixel_bytes)).astype(np.uint32)
channels = []
for mask in [info.blue_mask,info.green_mask,info.red_mask]:
    shift = (mask&-mask).bit_length()-1
    channels.append((((pixels&mask)>>shift)*255//(mask>>shift)).astype(np.uint8))
image = cv2.resize(np.stack(channels,axis=2),(640,480))
bind('XDestroyImage',I,[P])(im)
bind('XCloseDisplay',I,[P])(d)
ok,jpeg = cv2.imencode('.jpg',image,[cv2.IMWRITE_JPEG_QUALITY,70])
assert ok
passed = all(after[k]>before[k] for k in ['capture_frames','detected_frames','display_frames','rendered_frames']) and not after['error'] and not after['stopped'] and owners==[current['pid']] and 'Monitor is On' in display.stdout
print(json.dumps({'passed':passed,'run_root':str(root),'before':before,'after':after,'camera_owners':owners,'display':display.stdout,'screen_size':[w,h],'desktop_jpeg':base64.b64encode(jpeg).decode(),'events_tail':(root/'events.jsonl').read_text()[-6000:],'motion_command_emitted':False,'fpga_modified':False}))
assert passed
