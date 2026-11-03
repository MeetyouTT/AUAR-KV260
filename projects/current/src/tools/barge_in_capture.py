"""Single MCP01 owner for one echo-cancelled interruption, keeping its pre-roll."""
import signal
from collections import deque
from board.runtime.audio.automatic_capture import AutomaticMcp01Capture,SpeechEndpoint
from board.runtime.audio.echo_cancel import SpeexEcho


class BargeInCapture(AutomaticMcp01Capture):
    buffer_time_us = 80000

    def __init__(self,output,*,echo_factory=SpeexEcho,verifier=None,spoken_text=lambda:'',**kwargs):
        # This opt-in adapter intentionally permits duplex. Only the barge-in
        # controller owns it; the ordinary capture adapter keeps its idle check.
        super().__init__(lambda:False,**kwargs)
        self.output=output;self.echo_factory=echo_factory;self.echo=None;self.unsubscribe=None;self.discarded_samples=0
        self.verifier=verifier;self.spoken_text=spoken_text
        self.confirm_ring=deque(maxlen=110);self.confirm_frames=0;self.confirm_pending=False
        self.confirmed=False;self.confirm_disabled=False;self.held_pcm=None;self.confirm_obsolete=False
        self.confirm_stats={'checks':0,'echo_rejections':0,'unclear_rejections':0,'confirmed':0,'errors':0}
        self.confirm_last={}
        self.input_samples=0

    def _command(self):
        return super()._command()

    def start(self):
        self.echo=self.echo_factory()
        try:
            self.unsubscribe=self.output.subscribe_reference(self.echo.reference)
            return super().start()
        except Exception:self._release_echo();raise

    def _release_echo(self):
        self._close_endpoint()
        if self.unsubscribe:self.unsubscribe();self.unsubscribe=None
        if self.echo:self.echo.close();self.echo=None
        if self.verifier:self.verifier.close()

    def _capture_timer(self):
        self.discarded_samples=0
        self.input_samples=0
        timer=super()._capture_timer()
        self._new_endpoint()
        return timer

    def _new_endpoint(self):
        self._close_endpoint()
        self.endpoint=self._endpoint()
        # Longer onset rejects short echo remnants; retain the existing pre-roll.
        self.endpoint.vad.config.min_speech_ms=240
        self.endpoint.start_frames=12
        self.endpoint.ring=deque(maxlen=self.endpoint.pre_frames+12)
    def _captured_start(self,started):
        return super()._captured_start(started)+round(self.discarded_samples*1000/16000)

    def snapshot(self):
        value=super().snapshot();echo=self.echo
        value['echo_reference_ready']=bool(echo and echo.healthy())
        value['echo_reference_gaps']=echo.reference_gaps if echo else None
        with self._lock:
            value['speech_verification']={'enabled':bool(self.verifier and not self.confirm_disabled),
                'candidate':bool(self.verifier and not self.confirmed and not self.confirm_disabled and (self.confirm_frames or self.held_pcm)),
                'pending':self.confirm_pending,'confirmed':self.confirmed,
                'stats':dict(self.confirm_stats),'last':dict(self.confirm_last)}
        return value

    def release_for_listening(self):
        # The ACK/tail owner may reuse this microphone only when no unresolved
        # playback-era utterance could leak through as a normal new question.
        with self._lock:
            if self.verifier and not self.confirmed and (self.confirm_frames or self.held_pcm or self.confirm_pending):
                return False
            self.confirm_disabled=True
            return True

    def _reject_candidate(self):
        prefix=list(self.confirm_ring)[-self.endpoint.pre_frames:]
        self.discarded_samples=max(0,self.input_samples-len(prefix)*320)
        self._new_endpoint()
        self.endpoint.ring.extend(prefix);self.endpoint.total_samples=len(prefix)*320
        self.confirm_frames=0;self.held_pcm=None

    def _confirm(self):
        if self.verifier is None or self.confirm_disabled or self.confirmed:
            return
        result=self.verifier.poll()
        if result is not None:
            self.confirm_pending=False
            if self.confirm_obsolete:
                self.confirm_obsolete=False
            else:
                self.confirm_last=result
                if result['decision']=='new_speech':
                    self.confirmed=True;self.confirm_stats['confirmed']+=1
                    callback=getattr(self,'on_speech_start',None)
                    if callback:callback()
                else:
                    key=('echo_rejections' if result['decision']=='echo' else
                         'errors' if result['decision']=='unavailable' else 'unclear_rejections')
                    self.confirm_stats[key]+=1
                    self._reject_candidate()
        if (not self.confirmed and not self.confirm_pending and
                (self.confirm_frames>=30 or self.held_pcm is not None)):
            pcm=(self.held_pcm[-64000:] if self.held_pcm is not None else
                 b''.join(list(self.confirm_ring)[-min(100,self.confirm_frames+10):]))
            if self.verifier.submit(pcm,self.spoken_text()):
                self.confirm_pending=True;self.confirm_stats['checks']+=1

    def _read_pcm(self,process):
        try:
            while True:
                raw=process.stdout.read(640)
                if not raw:
                    if self._cancelled:return b''
                    raise RuntimeError('Interruption microphone ended unexpectedly')
                if len(raw)!=640:raise RuntimeError('Truncated interruption capture')
                self.input_samples+=320
                self.input_ready=True
                clean=self.echo.process(raw)
                if getattr(self.echo,'reference_gaps',0):
                    raise RuntimeError('Echo reference discontinuity; keep playback and rearm normal listening')
                if not self.echo.healthy():
                    # Never use unreferenced raw microphone energy to interrupt.
                    self.discarded_samples=self.input_samples
                    self._new_endpoint()
                    self.confirm_ring.clear();self.confirm_frames=0;self.held_pcm=None
                    self.confirm_obsolete=self.confirm_pending
                    continue
                self.confirm_ring.append(clean)
                was_active=self.endpoint.active
                result=None if self.held_pcm is not None else self.endpoint.feed(clean)
                if self.endpoint.active and not was_active:
                    self.confirm_frames=12
                    if self.verifier is None or self.confirm_disabled:
                        callback=getattr(self,'on_speech_start',None)
                        if callback:callback()
                elif was_active:self.confirm_frames+=1
                if result is not None and self.verifier and not self.confirm_disabled and not self.confirmed:
                    self.held_pcm=result;result=None
                self._confirm()
                if self.confirmed and self.held_pcm is not None:
                    result=self.held_pcm;self.held_pcm=None
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
