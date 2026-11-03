"""Video enters native X11 sinks independently of GTK/avatar frame scheduling."""
from collections import deque
import copy
import io
import threading
import time

from board.vision.local_preview import PIXELS, RawFrameReader


class CameraPreviewWorker:
    def __init__(self, services, *, raw_directory='/run'):
        import gi
        gi.require_version('Gst','1.0')
        gi.require_version('GstVideo','1.0')
        from gi.repository import Gst,GstVideo
        Gst.init(None)
        self.Gst,self.GstVideo,self.services=Gst,GstVideo,services
        self.raw_directory=raw_directory
        self.lock=threading.RLock()
        self.stop=threading.Event()
        self.outputs={}
        self.reader=self.reader_owner=self.last_key=None
        self.error=''
        self.thread=threading.Thread(target=self.work,name='aura-camera-display',daemon=True)
        self.thread.start()

    def attach(self, name, handle, width, height):
        self.detach(name)
        gst=self.Gst
        pipeline=gst.parse_launch('appsrc name=input is-live=true format=time block=false max-bytes=921600 '
            'caps="video/x-raw,format=BGR,width=640,height=480,framerate=0/1,pixel-aspect-ratio=1/1" ! '
            'queue max-size-buffers=1 max-size-bytes=0 max-size-time=0 leaky=downstream ! '
            'videoconvert ! videoscale ! video/x-raw,width='+str(width)+',height='+str(height)+
            ',pixel-aspect-ratio=1/1 ! identity name=count signal-handoffs=true ! '
            'ximagesink name=screen sync=false handle-events=false force-aspect-ratio=true')
        output={'pipeline':pipeline,'source':pipeline.get_by_name('input'),'reference':None,
                'handle':int(handle),'frames':{},'owner':None,'count':0,
                'times':deque(maxlen=120),'ages':deque(maxlen=120),'cleared':True,
                'lifecycle_lock':threading.Lock()}
        def handed_off(_, buffer):
            key=(int(buffer.offset),int(buffer.pts))
            with self.lock:
                if self.outputs.get(name) is not output:return
                packet=output['frames'].get(key)
                if packet is None:return
                output['reference']=packet
                if packet:
                    output['count']+=1
                    output['times'].append(time.monotonic())
                    output['ages'].append(round(time.monotonic()*1000-packet['captured_mono_ms'],2))
        def drop_stale(_, info):
            if not self.is_current(name,output):return gst.PadProbeReturn.DROP
            buffer=info.get_buffer()
            if buffer.offset and not -100<=time.monotonic()*1000-buffer.pts/gst.MSECOND<250:
                return gst.PadProbeReturn.DROP
            return gst.PadProbeReturn.OK
        counter=pipeline.get_by_name('count');pad=counter.get_static_pad('sink')
        output['counter'],output['sink_pad']=counter,pad
        output['probe_id']=pad.add_probe(gst.PadProbeType.BUFFER,drop_stale)
        output['handler_id']=counter.connect('handoff',handed_off)
        self.GstVideo.VideoOverlay.set_window_handle(pipeline.get_by_name('screen'),int(handle))
        with self.lock:self.outputs[name]=output
        if pipeline.set_state(gst.State.PLAYING)==gst.StateChangeReturn.FAILURE:
            self.detach(name);raise RuntimeError('Cannot start native camera display')
        # A new view receives the current frame even if the source is unchanged.
        self.last_key=None

    def detach(self, name):
        with self.lock:output=self.outputs.pop(name,None)
        if output:
            with output['lifecycle_lock']:
                output['pipeline'].set_state(self.Gst.State.NULL)
                output['counter'].disconnect(output['handler_id'])
                output['sink_pad'].remove_probe(output['probe_id'])

    def is_current(self, name, output):
        with self.lock:return self.outputs.get(name) is output

    def push(self, header, pixels):
        gst=self.Gst
        owner=tuple(header[k] for k in ('board_boot_id','service_epoch','camera_epoch'))
        reference={k:header[k] for k in ('camera_epoch','frame_id','captured_mono_ms')}
        with self.lock:outputs=list(self.outputs.items())
        for name,output in outputs:
            with output['lifecycle_lock']:
                if not self.is_current(name,output):continue
                if output['owner']!=owner:
                    if output['owner'] is not None:
                        output['pipeline'].set_state(gst.State.NULL)
                    with self.lock:
                        if self.outputs.get(name) is not output:continue
                        output['owner']=owner;output['frames'].clear();output['reference']=None
                    # Do not hold the callback lock while Gst waits for a task.
                    self.GstVideo.VideoOverlay.set_window_handle(
                        output['pipeline'].get_by_name('screen'),output['handle'])
                    if not self.is_current(name,output):continue
                    output['pipeline'].set_state(gst.State.PLAYING)
                if not self.is_current(name,output):continue
                if output['source'].get_property('current-level-bytes')>=PIXELS:
                    continue  # Gst 1.18 appsrc has no leaky-type; bound its input too.
                buffer=gst.Buffer.new_allocate(None,len(pixels),None);buffer.fill(0,pixels)
                buffer.offset=header['frame_id'];buffer.pts=header['captured_mono_ms']*gst.MSECOND
                key=(int(buffer.offset),int(buffer.pts))
                with self.lock:
                    if self.outputs.get(name) is not output:continue
                    output['frames'][key]=dict(reference)
                    while len(output['frames'])>4:output['frames'].pop(next(iter(output['frames'])))
                    output['cleared']=False
                flow=output['source'].emit('push-buffer',buffer)
                if flow!=gst.FlowReturn.OK and self.is_current(name,output):
                    raise RuntimeError('Native preview buffer was rejected')

    def clear(self):
        gst=self.Gst
        with self.lock:outputs=list(self.outputs.items())
        for name,output in outputs:
            with output['lifecycle_lock']:
                pts=int(time.monotonic()*1000)*gst.MSECOND
                with self.lock:
                    if self.outputs.get(name) is not output or output['cleared']:continue
                    output['cleared']=True;output['frames'].clear();output['reference']=None
                    output['frames'][(0,pts)]=None
                buffer=gst.Buffer.new_allocate(None,PIXELS,None)
                buffer.memset(0,0,PIXELS);buffer.offset=0;buffer.pts=pts
                output['source'].emit('push-buffer',buffer)

    @staticmethod
    def placeholder_visible(display, camera_state):
        if display.get('frame_visible'):
            return False
        # The native raw sink validates and clears pixels independently.
        # A delayed GTK metadata sample must not cover a running live sink.
        live_sink = (camera_state == 'READY' and display.get('sink_active')
                     and display.get('transport') == 'raw-local' and not display.get('error'))
        return not live_sink

    def read(self, name='main'):
        with self.lock:
            output=self.outputs.get(name)
            ref=copy.deepcopy(output['reference']) if output else None
            deadline=500 if self.reader_owner else 1500
            if ref and not -100<=time.monotonic()*1000-ref['captured_mono_ms']<deadline:ref=None
            times=[t for t in output['times'] if time.monotonic()-t<2] if output else []
            ages=sorted(output['ages']) if output else []
            return {'frame_reference':ref,'frame_visible':bool(ref),'error':self.error,
                'displayed_frames':output['count'] if output else 0,
                'update_hz':round((len(times)-1)/(times[-1]-times[0]),2) if len(times)>1 else 0,
                'entry_age_ms':{'median':ages[len(ages)//2],'p95':ages[int(.95*(len(ages)-1))]} if ages else None,
                'sink_active':output is not None,'active_outputs':sorted(self.outputs),
                'measurement_scope':'active_native_sink_entry_not_physical_scanout',
                'measurement':'native_video_sink_entry','transport':'raw-local' if self.reader_owner else 'jpeg-http'}

    def work(self):
        while not self.stop.wait(.01):
            try:
                with self.lock:
                    if not self.outputs:
                        self.reader=self.reader_owner=self.last_key=None
                        self.error=''
                        continue
                view=self.services.read();snapshot=view['snapshot']
                if not snapshot or snapshot['modules'].get('camera',{}).get('state')!='READY' or not snapshot.get('preview'):
                    self.reader=self.reader_owner=None;self.last_key=None;self.clear();continue
                owner={k:snapshot[k] for k in ('board_boot_id','service_epoch')}
                owner['camera_epoch']=snapshot['preview']['camera_epoch']
                if view.get('raw_preview'):
                    if owner!=self.reader_owner:
                        self.reader=RawFrameReader(owner,self.raw_directory);self.reader_owner=owner;self.last_key=None
                    packet=self.reader.read(int(time.monotonic()*1000))
                    if packet:
                        header,pixels=packet;self.push(header,pixels);self.last_key=header
                    elif self.last_key and time.monotonic()*1000-self.last_key['captured_mono_ms']>=250:
                        self.clear()
                else:
                    self.reader=self.reader_owner=None
                    key=snapshot['preview']
                    if view['preview'] and key!=self.last_key:
                        from PIL import Image
                        with Image.open(io.BytesIO(view['preview'])) as source:
                            if source.width>1920 or source.height>1080:raise ValueError('Preview dimensions exceeded')
                            if source.size!=(640,480):source=source.resize((640,480))
                            pixels=source.convert('RGB').tobytes('raw','BGR')
                        self.push(dict(owner,**{k:key[k] for k in ('frame_id','captured_mono_ms')}),pixels)
                        self.last_key=dict(key)
                    elif not view['preview']:self.clear()
                with self.lock:
                    outputs=list(self.outputs.items())
                for name,output in outputs:
                    if not self.is_current(name,output):continue
                    error=output['pipeline'].get_bus().pop_filtered(self.Gst.MessageType.ERROR)
                    if error and self.is_current(name,output):raise RuntimeError(str(error.parse_error()[0]))
                self.error=''
            except Exception as exc:
                self.error=type(exc).__name__+': '+str(exc)
                self.clear()

    def close(self):
        self.stop.set();self.thread.join(timeout=3)
        for name in list(self.outputs):self.detach(name)
