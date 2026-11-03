"""Single MCP01 owner for one echo-cancelled interruption, keeping its pre-roll."""
import signal
from board.runtime.audio.automatic_capture import AutomaticMcp01Capture,SpeechEndpoint
from board.runtime.audio.echo_cancel import SpeexEcho


class BargeInCapture(AutomaticMcp01Capture):
    def __init__(self,output,*,echo_factory=SpeexEcho,**kwargs):
        # This opt-in adapter intentionally permits duplex. Only the barge-in
        # controller owns it; the ordinary capture adapter keeps its idle check.
        super().__init__(lambda:False,**kwargs)
        self.output=output;self.echo_factory=echo_factory;self.echo=None;self.unsubscribe=None;self.discarded_samples=0

    def _command(self):
        return super()._command()+['--buffer-time=80000','--period-time=20000']

    def start(self):
        self.echo=self.echo_factory()
        try:
            self.unsubscribe=self.output.subscribe_reference(self.echo.reference)
            return super().start()
        except Exception:self._release_echo();raise

    def _release_echo(self):
        if self.unsubscribe:self.unsubscribe();self.unsubscribe=None
        if self.echo:self.echo.close();self.echo=None

    def _capture_timer(self):
        self.discarded_samples=0
        timer=super()._capture_timer()
        self._new_endpoint()
        return timer

    def _new_endpoint(self):
        self.endpoint=SpeechEndpoint(self.max_seconds)
        # Longer onset rejects short echo remnants; retain the existing pre-roll.
        self.endpoint.vad.config.min_speech_ms=240
        self.endpoint.start_frames=12;self.endpoint.ring=__import__('collections').deque(maxlen=22)
    def _captured_start(self,started):
        return super()._captured_start(started)+round(self.discarded_samples*1000/16000)

    def snapshot(self):
        value=super().snapshot();echo=self.echo
        value['echo_reference_ready']=bool(echo and echo.healthy())
        value['echo_reference_gaps']=echo.reference_gaps if echo else None
        return value

    def _read_pcm(self,process):
        try:
            while True:
                raw=process.stdout.read(640)
                if not raw:
                    if self._cancelled:return b''
                    raise RuntimeError('Interruption microphone ended unexpectedly')
                if len(raw)!=640:raise RuntimeError('Truncated interruption capture')
                clean=self.echo.process(raw)
                if not self.echo.healthy():
                    # Never use unreferenced raw microphone energy to interrupt.
                    self.discarded_samples+=320+self.endpoint.total_samples
                    self._new_endpoint()
                    continue
                was_active=self.endpoint.active;result=self.endpoint.feed(clean)
                if self.endpoint.active and not was_active:
                    callback=getattr(self,'on_speech_start',None)
                    if callback:callback()
                with self._lock:
                    self._sample_count=self.endpoint.speech_samples
                    if self.endpoint.active and self._timer is None:
                        import threading
                        self._timer=threading.Timer(self.max_seconds+2,self._timeout)
                        self._timer.daemon=True;self._timer.start()
                    if result is not None:
                        if len(result)>self.max_samples*2:raise ValueError('Interruption exceeds capture budget')
                        self._stopping=True;self._signal(signal.SIGINT);return result
        finally:self._release_echo()
