"""Opt-in spoken interruption using the same visual/session/cancellation owners."""
import threading
from tools.handsfree_recording import HandsFreeRecordingController


class BargeInRecordingController(HandsFreeRecordingController):
    def __init__(self,*args,barge_capture_factory=None,**kwargs):
        super().__init__(*args,**kwargs)
        if barge_capture_factory is None:
            from tools.barge_in_capture import BargeInCapture
            from board.runtime.audio.barge_verify import InterruptionVerifier
            barge_capture_factory=lambda:BargeInCapture(self.controller.output,
                verifier=InterruptionVerifier(lambda:dict(self.transcriber.config),self.attention_gate.boot_id),
                spoken_text=lambda:getattr(self.controller,'reply',''))
        self.barge_factory=barge_capture_factory;self.barge_capture=None
        self.barge_id=None;self.barge_request=None;self.barge_attempt=None
        self.barge_lock=threading.Lock();self.barge_speech=None
        self.barge_error='';self.barge_interruptions=0;self.barge_last={}
        self.barge_onset_at=None;self.barge_stop_latency_ms=None
        self.tail_handoffs=0

    def _stop_barge(self):
        capture=self.barge_capture;self.barge_capture=None
        with self.barge_lock:self.barge_speech=None
        if capture:
            snapshot=capture.snapshot()
            self.barge_last={k:snapshot[k] for k in ('state','echo_reference_ready','echo_reference_gaps','speech_verification') if k in snapshot}
            capture.close()

    def _finish_session(self,*args,**kwargs):
        self._stop_barge();return super()._finish_session(*args,**kwargs)

    def cancel(self):
        self._stop_barge();return super().cancel()

    def _barge_started(self,capture,request):
        current,_=self._current()
        if current and current['key']==self.monitor_key:
            with self.barge_lock:
                if capture is not self.barge_capture or request!=self.transcription.get('request_id'):return
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
                elif self.early_listen and self.transcription['state']=='ANSWERED':
                    pass  # Keep the next utterance while the previous full ACK/tail settles.
                else:
                    # Never call public cancel: it would pause monitoring, lose
                    # the conversation selection and discard the new utterance.
                    self.transcriber.cancel();self.controller.cancel()
                    snapshot=capture.snapshot()
                    self.barge_last={k:snapshot[k] for k in ('state','echo_reference_ready','echo_reference_gaps','speech_verification') if k in snapshot}
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
        if (self.early_listen and self.monitor_owned and self.auto_enabled
                and self.transcription['state']=='ANSWERED' and self.barge_capture is not None):
            service=self.transcriber.public();ack=service.get('last_playback_ack') or {}
            matching=ack.get('request_id')==self.transcription['request_id']
            if (matching and not ack.get('committed') or self.clock()>=self.ack_deadline):
                self._stop_barge()
            elif (not matching or self.clock()<self.rearm_at or self._playback_active() or service.get('pending')):
                self.auto_state='SETTLING' if matching else 'WAITING_ACK'
                return
            else:
                current,reason=self._current()
                if not current or current['key']!=self.monitor_key:
                    self._finish_session(reason if not current else 'TARGET_CHANGED');return
                capture=self.barge_capture;snapshot=capture.snapshot()
                with self.barge_lock:proof=self.barge_speech
                verification=snapshot.get('speech_verification',{})
                if not proof and (verification.get('candidate') or verification.get('pending')):
                    self.auto_state='CONFIRMING_INTERRUPTION';return
                if snapshot['state']=='ERROR' or snapshot['state']=='READY' and not proof:
                    self._stop_barge()
                else:
                    if not proof and hasattr(capture,'release_for_listening') and not capture.release_for_listening():
                        self.auto_state='CONFIRMING_INTERRUPTION';return
                    if self.capture:self.capture.close()
                    with self.barge_lock:
                        self.barge_capture=None;self.barge_speech=None
                        capture.on_speech_start=self._speech_started
                    self.capture=capture;self.capture_kind='barge';self.listen_id=self.barge_id
                    self.listen_started=self.clock();self.utterance=None
                    with self.proof_lock:self.speech_proof=(self.listen_id,self.monitor_key) if proof else None
                    self.transcriber.cancel()
                    if proof and hasattr(self.transcriber,'capture_started'):self.transcriber.capture_started(self.listen_id)
                    self.transcription=self._empty_transcription('IDLE');self.recording_state='RECORDING'
                    self.recording_error='';self.rearm_at=self.ack_deadline=None
                    self.auto_state='LISTENING';self.tail_handoffs+=1
                    if not proof and capture.snapshot().get('speech_active'):self._speech_started()
                    return
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
        if capture and self.early_listen:
            state['handsfree_dialogue']['listening_timing']['input_ready']=bool(
                snapshot.get('input_ready',True) and snapshot.get('echo_reference_ready',False))
            state['automatic_conversation']['speech_active']=bool(
                snapshot.get('state')=='RECORDING' and snapshot.get('speech_active'))
        state['voice_barge_in']={'enabled':True,'listening':self.barge_capture is not None,
            'echo_reference_ready':snapshot.get('echo_reference_ready',False),
            'echo_reference_gaps':snapshot.get('echo_reference_gaps'),
            'interrupted_turns':self.barge_interruptions,'error':self.barge_error,
            'last_monitor':dict(self.barge_last),'last_detection_to_stop_ms':self.barge_stop_latency_ms,
            'continuation_listening':bool(self.early_listen and capture and self.transcription['state']=='ANSWERED'),
            'continuation_handoffs':self.tail_handoffs,
            'next_utterance_pending':bool(self.early_listen and capture and self.barge_speech),
            'speech_verification':snapshot.get('speech_verification',{}),
            'echo_cancellation':'SpeexDSP reference from queued playback PCM',
            'speaker_binding_verified':False}
        return state
