"""One live ALSA pipeline; silent PCM keeps the device ready between utterances.

Published content time always comes from the sink query, not elapsed wall time.
This engine is opt-in; the accepted padded-WAV engine remains available.
"""
import base64
from collections import deque
import hashlib
import time
import wave

from tools.gstreamer_audio_engine import OUTPUT_CAPS, validate_clip

RATE=24000
FRAMES=480
TICK_NS=20000000
MAX_FRAMES=RATE*35


def build_live_pipeline(gst,device):
    pipeline=gst.Pipeline.new('aura-persistent-audio')
    elements=[]
    try:
        for name in ('appsrc','audioconvert','audioresample','capsfilter','alsasink'):
            element=gst.ElementFactory.make(name,'aura-live-'+name)
            if element is None:raise RuntimeError('Missing GStreamer element: '+name)
            pipeline.add(element);elements.append(element)
        source,convert,resample,caps,sink=elements
        source.set_property('caps',gst.Caps.from_string('audio/x-raw,format=S16LE,layout=interleaved,rate=24000,channels=1'))
        source.set_property('format',gst.Format.TIME)
        source.set_property('is-live',True)
        source.set_property('block',False)
        source.set_property('max-bytes',FRAMES*2*8)
        caps.set_property('caps',gst.Caps.from_string(OUTPUT_CAPS))
        sink.set_property('device',device);sink.set_property('sync',True)
        sink.set_property('buffer-time',80000);sink.set_property('latency-time',10000)
        for left,right in zip(elements,elements[1:]):
            if not left.link(right):raise RuntimeError('Cannot link persistent audio')
        return pipeline,source,sink
    except Exception:
        pipeline.set_state(gst.State.NULL)
        raise


class PersistentGstAudioEngine:
    def __init__(self,gst,device,*,clock=time.monotonic,pipeline_factory=build_live_pipeline):
        self.gst,self.device,self.clock=gst,device,clock
        self.pipeline,self.source,self.sink=pipeline_factory(gst,device)
        self.bus=self.pipeline.get_bus()
        self.next_pts=0
        self.queue=deque();self.intervals=deque()
        self.references=deque(maxlen=16);self.reference_sequence=0
        self.token=0;self.position=0.;self.answer_position=0.;self.duration=0.
        self.input_samples=0;self.answer_samples=0
        self.ready=self.done=self.paused=self.final=False
        self.active=False;self.error='';self.started_at=None;self.answer_started_at=None
        self.device_ready=False;self.audible=False;self.track=None
        self.underrun_packets=0;self.last_data_end=None
        if self.pipeline.set_state(gst.State.PLAYING)==gst.StateChangeReturn.FAILURE:
            self.release();raise RuntimeError('Persistent ALSA start failed')

    def release(self):
        if self.pipeline is not None:self.pipeline.set_state(self.gst.State.NULL)
        self.pipeline=self.source=self.sink=None
        self.device_ready=False

    def fail(self,error):
        self.error=str(error);self.active=False;self.queue.clear();self.intervals.clear();self.release()

    def _reset(self,token):
        self.token=token;self.queue.clear();self.intervals.clear()
        self.position=self.answer_position=self.duration=0.
        self.input_samples=self.answer_samples=0
        self.ready=self.done=self.paused=self.final=False
        self.active=False;self.audible=False;self.track=None
        self.started_at=self.answer_started_at=self.last_data_end=None

    def _append(self,pcm,track):
        if not isinstance(pcm,bytes) or not pcm or len(pcm)%2:raise ValueError('Expected nonempty PCM16')
        if self.input_samples+len(pcm)//2>MAX_FRAMES:raise ValueError('Persistent queue exceeds 35 seconds')
        for offset in range(0,len(pcm),FRAMES*2):
            part=pcm[offset:offset+FRAMES*2]
            self.queue.append((part,track,self.input_samples,self.answer_samples))
            self.input_samples+=len(part)//2
            if track=='answer':self.answer_samples+=len(part)//2
        self.duration=self.input_samples/RATE

    def _file(self,message,track):
        path,_=validate_clip(message['path'],message.get('sha256'))
        with wave.open(str(path),'rb') as audio:
            self._append(audio.readframes(audio.getnframes()),track)

    def command(self,message):
        token=message.get('token')
        if type(token) is not int or token<self.token:return False
        kind=message.get('type')
        if kind in ('play','stream','stop','close'):
            self._reset(token)
            if kind=='close':self.release();return True
            if kind=='stop':return True
            if not self.device_ready:raise RuntimeError('Persistent audio device is not ready')
            self.active=True
            if kind=='play':self._file(message,'answer');self.final=True
            return True
        if token!=self.token or not self.active:return False
        if kind=='pause':self.paused=bool(message.get('paused'))
        elif kind=='pcm':
            if self.final:raise ValueError('PCM after stream completion')
            if type(message.get('start_sample')) is not int or message['start_sample']!=self.answer_samples:raise ValueError('Out-of-order playback PCM')
            pcm=base64.b64decode(message.get('pcm',''),validate=True)
            if len(pcm)>FRAMES*2:raise ValueError('Playback packet exceeds 20ms')
            self._append(pcm,'answer')
        elif kind=='feedback':
            if self.answer_samples or self.final:return False
            if self.input_samples:return False  # At most one cached phrase per turn.
            self._file(message,'feedback')
        elif kind=='end':self.final=True
        else:raise ValueError('Unknown persistent audio command')
        return True

    def _push(self,pcm,pts,duration):
        gst=self.gst
        buffer=gst.Buffer.new_allocate(None,len(pcm),None)
        buffer.fill(0,pcm);buffer.pts=pts;buffer.dts=pts;buffer.duration=duration
        if self.source.emit('push-buffer',buffer)!=gst.FlowReturn.OK:
            raise RuntimeError('Persistent appsrc rejected PCM')
        # Speex's asynchronous API needs the far frame when it is QUEUED to
        # playback; delivering it after the audible frame makes it too late.
        # Playback/history clocks below still depend only on the real sink.
        self.reference_sequence+=1
        self.references.append({'sequence':self.reference_sequence,'pcm':pcm,
            'at':self.clock(),'queued_end_ns':pts+duration})

    def take_references(self):
        values=list(self.references);self.references.clear();return values

    def _observe(self,now_ns):
        self.device_ready=now_ns>=self.gst.SECOND
        self.audible=False;self.track=None
        while self.intervals and self.intervals[0][1]<=now_ns:
            start,end,token,offset,count,track,answer_offset=self.intervals.popleft()
            if token==self.token:
                if not self.ready:self.ready=True;self.started_at=self.clock()
                self.position=max(self.position,(offset+count)/RATE)
                if track=='answer':
                    self.answer_position=max(self.answer_position,(answer_offset+count)/RATE)
                    if self.answer_started_at is None:self.answer_started_at=self.clock()
        if self.intervals:
            start,end,token,offset,count,track,answer_offset=self.intervals[0]
            if token==self.token and start<=now_ns<end:
                sample=min(count,max(0,(now_ns-start)*RATE//self.gst.SECOND))
                self.position=max(self.position,(offset+sample)/RATE)
                self.audible=True;self.track=track
                if not self.ready:self.ready=True;self.started_at=self.clock()
                if track=='answer':
                    self.answer_position=max(self.answer_position,(answer_offset+sample)/RATE)
                    if self.answer_started_at is None:self.answer_started_at=self.clock()
        if self.active and self.final and not self.queue and self.last_data_end is not None and now_ns>=self.last_data_end:
            self.position=self.duration;self.answer_position=self.answer_samples/RATE
            self.done=True;self.active=False;self.audible=False;self.track=None
        elif self.active and self.final and not self.queue and self.last_data_end is None:
            self.done=True;self.active=False

    def poll(self):
        if self.pipeline is None:return self.snapshot()
        gst=self.gst
        message=self.bus.timed_pop_filtered(0,gst.MessageType.ERROR)
        if message is not None:
            error,_=message.parse_error();self.fail(error);return self.snapshot()
        clock=self.pipeline.get_clock()
        if clock is None:return self.snapshot()
        running=max(0,clock.get_time()-self.pipeline.get_base_time())
        # Recover scheduling lateness without dropping or skipping content PCM.
        if self.next_pts+100000000<running:
            self.next_pts=((running+TICK_NS-1)//TICK_NS)*TICK_NS
        for _ in range(8):
            if self.next_pts>=running+60000000:break
            pts=self.next_pts
            if self.active and not self.paused and self.queue:
                pcm,track,offset,answer_offset=self.queue.popleft()
                count=len(pcm)//2;duration=count*gst.SECOND//RATE
                self._push(pcm,pts,duration)
                self.intervals.append((pts,pts+duration,self.token,offset,count,track,answer_offset))
                self.last_data_end=pts+duration
            else:
                duration=TICK_NS;self._push(bytes(FRAMES*2),pts,duration)
                if self.active and self.ready and not self.paused and not self.final:self.underrun_packets+=1
            self.next_pts+=duration
        ok,position=self.sink.query_position(gst.Format.TIME)
        if ok and position>=0:
            self._observe(position)
        return self.snapshot()

    def snapshot(self):
        return {'token':self.token,'ready':self.ready,'clock':self.position,'done':self.done,'error':self.error,
                'started_at':self.started_at,'answer_started_at':self.answer_started_at,
                'answer_clock':self.answer_position,'audible':self.audible,'track':self.track,
                'duration':self.duration,'device_ready':self.device_ready,'persistent':True,
                'device_state':'ERROR' if self.error else 'IDLE_READY' if not self.active else 'PAUSED' if self.paused else 'PLAYING' if self.audible else 'WAITING_PCM',
                'clock_source':'GStreamer ALSA sink position query','output_caps':OUTPUT_CAPS,'device':self.device,
                'startup_silence_seconds':0.,'startup_warmup_seconds':1.,'underrun_packets':self.underrun_packets}
