"""Exercise appsrc display negotiation without opening the USB camera."""
import json
import os
import time
import sys
from pathlib import Path
os.environ['DISPLAY'] = ':0'
os.environ['GST_DEBUG'] = '2'
release = Path(json.loads(Path('/home/root/aura-realtime-vision-20261007/staged.json').read_text())['release'])
sys.path.insert(0,str(release))
from x11_window import Window
import gi
gi.require_version('Gst','1.0')
gi.require_version('GstVideo','1.0')
from gi.repository import Gst,GstVideo
Gst.init(None)
result = []
for fps in ['0/1','30/1']:
    window = Window()
    pipeline = Gst.parse_launch('appsrc name=output is-live=true format=time do-timestamp=true block=false '
        'max-bytes=921600 caps="video/x-raw,format=BGR,width=640,height=480,framerate='+fps+'" ! '
        'queue max-size-buffers=1 max-size-bytes=0 max-size-time=0 leaky=downstream ! '
        'videoconvert ! videoscale ! video/x-raw,width=1024,height=768 ! '
        'identity name=count signal-handoffs=true ! ximagesink name=screen sync=false force-aspect-ratio=true')
    counts = [0]
    def seen(*_):
        counts[0] += 1
    pipeline.get_by_name('count').connect('handoff',seen)
    GstVideo.VideoOverlay.set_window_handle(pipeline.get_by_name('screen'),window.handle)
    try:
        pipeline.set_state(Gst.State.PLAYING)
        for _ in range(8):
            buffer = Gst.Buffer.new_allocate(None,640*480*3,None)
            buffer.fill(0,bytes([80])*640*480*3)
            pipeline.get_by_name('output').emit('push-buffer',buffer)
            time.sleep(.1)
        msg = pipeline.get_bus().timed_pop_filtered(Gst.SECOND,Gst.MessageType.ERROR)
        error = str(msg.parse_error()) if msg else None
        states = str(pipeline.get_state(Gst.SECOND))
        row = {'fps':fps,'error':error,'state':states,'rendered_frames':counts[0],'screen_size':[window.width,window.height],'source_caps':str(pipeline.get_by_name('output').get_property('caps')),
               'sink_accepts':pipeline.get_by_name('screen').get_static_pad('sink').query_caps(None).to_string()}
        result.append(row)
    finally:
        pipeline.set_state(Gst.State.NULL)
        window.close()
print(json.dumps({'camera_opened':False,'results':result},indent=2))
