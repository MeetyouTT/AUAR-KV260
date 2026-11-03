"""Opt-in spoken interruption using the same visual/session/cancellation owners."""
import threading
from tools.handsfree_recording import HandsFreeRecordingController


class BargeInRecordingController(HandsFreeRecordingController):
    def __init__(self,*args,barge_capture_factory=None,**kwargs):
        super().__init__(*args,**kwargs)
        if barge_capture_factory is None:
            from tools.barge_in_capture import BargeInCapture
            barge_capture_factory=lambda:BargeInCapture(self.controller.output)
        self.barge_factory=barge_capture_factory;self.barge_capture=None
        self.barge_id=None;self.barge_request=None;self.barge_attempt=None
        self.barge_lock=threading.Lock();self.barge_speech=None
        self.barge_error='';self.barge_interruptions=0;self.barge_last={}
        self.barge_onset_at=None;self.barge_stop_latency_ms=None

    def _stop_barge(self):
        capture=self.barge_capture;self.barge_capture=None
        with self.barge_lock:self.barge_speech=None
        if capture:
            snapshot=capture.snapshot()
            self.barge_last={k:snapshot[k] for k in ('state','echo_reference_ready','echo_reference_gaps') if k in snapshot}
            capture.close()

    def _finish_session(self,*args,**kwargs):
        self._stop_barge();return super()._finish_session(*args,**kwargs)

    def cancel(self):
        self._stop_barge();return super().cancel()

    def _barge_started(self,capture,request):
        if capture is not self.barge_capture or request!=self.transcription.get('request_id'):return
        current,_=self._current()
        if current and current['key']==self.monitor_key:
            with self.barge_lock:
                if self.barge_speech is None:self.monitor_stats['speech_starts']+=1
                self.barge_speech=(self.barge_id,request,self.monitor_key)
                self.barge_onset_at=self.clock()

    def _collect(self):
        capture=self.barge_capture
        if capture is not None:
            current,_=self._current()
            with self.barge_lock:proof=self.barge_speech
            if not current or current['key']!=self.monitor_key:
                self._stop_barge()  # Preserve the already accepted reply.
            elif proof:
                if proof!=(self.barge_id,self.transcription['request_id'],self.monitor_key):
                    self._stop_barge()
                else:
                    # Never call public cancel: it would pause monitoring, lose
                    # the conversation selection and discard the new utterance.
                    self.transcriber.cancel();self.controller.cancel()
                    if self.barge_onset_at is not None:
                        self.barge_stop_latency_ms=round((self.clock()-self.barge_onset_at)*1000)
                    if self.capture:self.capture.close()
                    self.capture=capture;self.capture_kind='barge';self.barge_capture=None
                    with self.barge_lock:self.barge_speech=None
                    self.listen_id=self.barge_id;self.listen_started=self.clock()
                    with self.proof_lock:self.speech_proof=(self.listen_id,self.monitor_key)
                    if hasattr(self.transcriber,'capture_started'):self.transcriber.capture_started(self.listen_id)
                    self.transcription=self._empty_transcription('IDLE');self.utterance=None
                    self.recording_state='RECORDING';self.recording_error=''
                    self.rearm_at=self.ack_deadline=None;self.barge_interruptions+=1
            elif capture.snapshot()['state'] in ('ERROR','READY'):
                self.barge_error=capture.snapshot().get('error','')
                self._stop_barge()
        super()._collect()

    def _auto_tick(self):
        if self.transcription['state']=='ANSWERED':self._stop_barge()
        super()._auto_tick()

    def _queue_transcription(self):
        # Apply the existing raw-PCM and initial-ASR validity checks to an
        # interruption too, without selecting a different conversation ID.
        if self.capture_kind=='barge' and self.utterance is not None and self.monitor_owned:
            self.transcriber.mark_visual_entry(self.utterance.capture_id)
        super()._queue_transcription()

    def _arm_barge(self):
        tx=self.transcription;request=tx.get('request_id')
        if (not self.monitor_enabled or not self.monitor_owned or not self.monitor_entered
                or not self.auto_enabled or self._recording() or self.barge_capture is not None
                or tx['state'] not in ('GENERATING','PLAYING') or not tx.get('text')
                or not request or request==self.barge_attempt):return
        if self.transcriber.public().get('voice_enrollment',{}).get('active'):return
        current,_=self._current()
        if not current or current['key']!=self.monitor_key:return
        self.barge_attempt=request;self.barge_request=request;self.barge_error=''
        try:
            capture=self.barge_factory();self.barge_capture=capture
            capture.on_speech_start=lambda:self._barge_started(capture,request)
            self.barge_id=capture.start()
        except Exception as exc:
            self.barge_error=type(exc).__name__+': '+str(exc);self._stop_barge()

    def tick(self):
        result=super().tick();self._arm_barge();return result

    def public(self):
        state=super().public()
        state['handsfree_dialogue']['voice_barge_in']=True
        capture=self.barge_capture;snapshot=capture.snapshot() if capture else {}
        if capture:state['handsfree_dialogue']['microphone_open']=True
        state['voice_barge_in']={'enabled':True,'listening':self.barge_capture is not None,
            'echo_reference_ready':snapshot.get('echo_reference_ready',False),
            'echo_reference_gaps':snapshot.get('echo_reference_gaps'),
            'interrupted_turns':self.barge_interruptions,'error':self.barge_error,
            'last_monitor':dict(self.barge_last),'last_detection_to_stop_ms':self.barge_stop_latency_ms,
            'echo_cancellation':'SpeexDSP reference from queued playback PCM',
            'speaker_binding_verified':False}
        return state
