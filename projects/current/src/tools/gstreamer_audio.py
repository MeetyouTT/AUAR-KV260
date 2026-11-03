"""Device audio isolated from GTK; the default PC Qt worker is unchanged."""
from pathlib import Path
import base64
import threading
from tools.realtime_audio import SelectedAudioOutput

DEFAULT_DEVICE = 'hw:CARD=MCP01,DEV=0'


class GStreamerAudioOutput(SelectedAudioOutput):
    def __init__(self, log_path=None, device=DEFAULT_DEVICE, *, persistent=False,echo_reference=False):
        self.send_lock=threading.Lock();self.streaming=False
        self.reference_lock=threading.RLock();self.reference_handler=None;self.reference_error=''
        super().__init__(log_path, worker_path=Path(__file__).with_name('gstreamer_audio_worker.py'),
                         worker_args=('--device', device, *(['--persistent'] if persistent else []),
                                      *(['--echo-reference'] if echo_reference else [])))

    def receive_reference(self,message):
        try:
            raw=base64.b64decode(message['pcm'],validate=True)
            if not raw or len(raw)>960 or len(raw)%2:raise ValueError('Invalid echo reference frame')
            with self.reference_lock:
                if self.reference_handler:self.reference_handler(raw,message['at'],message['sequence'])
        except (OSError,RuntimeError,ValueError,KeyError) as exc:self.reference_error=str(exc)

    def subscribe_reference(self,handler):
        with self.reference_lock:
            if self.reference_handler is not None:raise RuntimeError('Echo reference already has an owner')
            self.reference_handler=handler
        def release():
            with self.reference_lock:
                if self.reference_handler is handler:self.reference_handler=None
        return release

    def send(self,kind,**fields):
        with self.send_lock:super().send(kind,**fields)

    def begin_stream(self):
        self.stop();self.token+=1;self.streaming=True;self.active=True;self.duration=0.;self.last_time=0.
        with self.lock:self.snapshot={'ready':False,'clock':0.,'done':False,'error':''}
        self.send('stream')

    def append_pcm(self,pcm,start_sample):
        self.send('pcm',pcm=base64.b64encode(pcm).decode('ascii'),start_sample=start_sample)

    def feedback(self,value):self.send('feedback',path=value['path'],sha256=value['sha256'])

    def end_stream(self):self.send('end')

    def position(self):
        if self.streaming:
            state=self.read();self.duration=state.get('duration',self.duration)
            if self.active and not self.paused:self.last_time=max(self.last_time,state['clock'])
            return self.last_time
        return super().position()

    def stop(self):
        super().stop();self.streaming=False
