"""Exercise appsrc display negotiation without opening the USB camera."""
import json
import os
import time
os.environ['DISPLAY'] = ':0'
import gi
gi.require_version('Gst','1.0')
from gi.repository import Gst
Gst.init(None)
result = []
for fps in ['0/1','30/1']:
    pipeline = Gst.parse_launch('appsrc name=output is-live=true format=time do-timestamp=true block=false '
        'max-bytes=921600 caps="video/x-raw,format=BGR,width=640,height=480,framerate='+fps+'" ! '
        'queue max-size-buffers=1 max-size-bytes=0 max-size-time=0 leaky=downstream ! '
        'videoconvert ! videoscale ! video/x-raw,width=1024,height=768 ! '
        'ximagesink name=screen sync=false force-aspect-ratio=true')
    try:
        pipeline.set_state(Gst.State.PLAYING)
        buffer = Gst.Buffer.new_allocate(None,640*480*3,None)
        pipeline.get_by_name('output').emit('push-buffer',buffer)
        msg = pipeline.get_bus().timed_pop_filtered(Gst.SECOND,Gst.MessageType.ERROR)
        error = str(msg.parse_error()) if msg else None
        states = str(pipeline.get_state(Gst.SECOND))
        row = {'fps':fps,'error':error,'state':states,'source_caps':str(pipeline.get_by_name('output').get_property('caps')),
               'sink_accepts':pipeline.get_by_name('screen').get_static_pad('sink').query_caps(None).to_string()}
        result.append(row)
    finally:
        pipeline.set_state(Gst.State.NULL)
print(json.dumps({'camera_opened':False,'results':result},indent=2))
