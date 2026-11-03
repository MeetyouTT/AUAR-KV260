"""Wake-word conversation owner; vision never gates ordinary speech.

Reuses the existing single capture and verified echo/interruption path.
The inherited session key is an audio-session key, never a face identity.
"""
import uuid
from tools.barge_in_recording import BargeInRecordingController
from tools.board_recording import RecordingController


class VoiceFirstRecordingController(BargeInRecordingController):
    def __init__(self, *args, barge_enabled=True, device_observer=False, visual_social=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.barge_enabled = bool(barge_enabled)
        self.voice_first = True
        self.wake_rearm = False
        self.monitor_state = 'WAITING_WAKE' if self.monitor_enabled else 'PAUSED'
        self.monitor_reason = 'AUDIO_WAKE_WORD'
        self.last_voice_activity = self.clock()
        from common.visual_social import VisualSocial
        self.social_policy=VisualSocial();self.social_enabled=bool(visual_social)
        self.social_active=False;self.social_opened=False;self.social_ended_at=None;self.social_count=0
        self.observer=None
        if device_observer:
            from board.runtime.device_observer import DeviceObserver
            self.observer=DeviceObserver(self.attention_gate.boot_id)

    def _current(self):
        # The inherited interruption code needs a stable session owner, not
        # visual evidence. Do not query the camera, even if it is unavailable.
        if self.monitor_enabled and self.monitor_owned and self.monitor_key:
            return {'key': self.monitor_key}, 'AUDIO_SESSION'
        return None, 'NO_AUDIO_SESSION'

    def _queue_transcription(self):
        if self.monitor_owned and self.utterance is not None:
            self.social_active=False;self.social_opened=False
            with self.proof_lock:
                proof = self.speech_proof
            if proof != (self.utterance.capture_id, self.monitor_key):
                self._finish_session('AUDIO_OWNER_CHANGED')
                return
            if not self.monitor_entered:
                self.transcriber.mark_wake_entry(self.utterance.capture_id)
            elif self.capture_kind == 'barge':
                # Legacy name denotes raw-audio/ASR validity, not a face gate.
                self.transcriber.mark_visual_entry(self.utterance.capture_id)
            self.last_voice_activity = self.clock()
        RecordingController._queue_transcription(self)

    def _wake_detected(self, *, wake_only=False):
        if not self.monitor_owned or not self.monitor_enabled:
            return
        self.monitor_entered = True
        self.auto_enabled = True
        self.last_voice_activity = self.clock()
        self.monitor_state = 'WAITING_SPEECH'
        self.monitor_reason = 'WAKE_ACCEPTED'
        self.wake_rearm = wake_only
        self.social_opened=False

    def _entry_rejected(self):
        # Non-wake speech consumes no LLM/TTS/history and simply rearms the
        # same bounded audio listener. It is not a visual rejection/error.
        self.monitor_stats['entry_rejected'] += 1
        self.wake_rearm = True

    def _finish_session(self, *args, **kwargs):
        self.wake_rearm = False
        self.social_active=False;self.social_opened=False
        return super()._finish_session(*args, **kwargs)

    def cancel(self):
        self.wake_rearm = False
        self.social_active=False;self.social_opened=False
        if getattr(self,'observer',None):self.observer.enabled=False
        return super().cancel()

    def handsfree_toggle(self):
        result = super().handsfree_toggle()
        if self.monitor_enabled:
            self.monitor_state = 'WAITING_WAKE'
            self.monitor_reason = 'AUDIO_WAKE_WORD'
        return result

    def _arm_barge(self):
        if self.barge_enabled:
            super()._arm_barge()

    def _auto_tick(self):
        if self.wake_rearm:
            return  # Rearm only after the network worker has released its job.
        super()._auto_tick()

    def _monitor_tick(self):
        if self.closed or not self.monitor_enabled:
            return
        if self.monitor_owned:
            if self.recording_state == 'ERROR' or self.transcription['state'] == 'ERROR' or self.auto_error:
                self.monitor_error = self.recording_error or self.transcription['error'] or self.auto_error
                self._finish_session('SERVICE_ERROR', 5.)
                return
            service = self.transcriber.public()
            if self.wake_rearm:
                if service.get('pending') or self._playback_active():
                    return
                try:
                    self._listen()
                    self.wake_rearm = False
                except Exception as exc:
                    self.monitor_error = str(exc)
                    self._finish_session('CAPTURE_ERROR', 5.)
                    return
            if self._recording():
                snapshot = self.capture.snapshot()
                if snapshot.get('speech_active'):
                    self.last_voice_activity = self.clock()
                # Expiry closes a conversation, not the wake listener. No
                # camera event can extend or terminate an audio conversation.
                if self.monitor_entered and self.clock()-self.listen_started >= 30 and not snapshot.get('speech_active'):
                    self._finish_session('CONVERSATION_SILENCE', .2)
                    return
                self.monitor_state = 'WAITING_SPEECH' if self.monitor_entered else 'WAITING_WAKE'
            else:
                self.monitor_state = 'CONVERSATION' if self.monitor_entered else 'CHECKING_WAKE'
            return
        if self.auto_enabled or self.clock() < self.cooldown_until:
            return
        if self._recording() or self._playback_active():
            self.monitor_state = 'WAITING_AUDIO_IDLE'
            return
        service = self.transcriber.public() if self.transcriber else {}
        if not service.get('feedback_ready') or service.get('pending') or not self.transcriber.enabled():
            self.monitor_state = 'WAITING_SERVICE'
            if self.transcriber and hasattr(self.transcriber, 'refresh_feedback'):
                self.transcriber.refresh_feedback()
            return
        try:
            # Automatic wake sessions start anonymous, independently of vision.
            # Explicit profile selection continues to use the existing token.
            self.transcriber.select_conversation(resume=False)
            self.monitor_owned = True
            self.monitor_key = ('audio', self.attention_gate.boot_id, uuid.uuid4().hex)
            self.monitor_entered = False
            self.entry_stable = True
            self.monitor_stats['armed'] += 1
            capture = self._capture_for(True)
            capture.on_speech_start = self._speech_started
            self.auto_error = self.last_error = self.monitor_error = ''
            self.auto_turns = 0
            self._listen()
            self.monitor_state = 'WAITING_WAKE'
        except Exception as exc:
            self.monitor_error = str(exc)
            self._finish_session('CAPTURE_ERROR', 5.)

    def _social_tick(self):
        if self.observer:self.observer.enabled=self.monitor_enabled and not self.closed
        if not self.social_enabled or not self.monitor_enabled or self.closed:return
        if self.social_active:
            if self._playback_active():self.social_ended_at=None;return
            if self.social_ended_at is None:self.social_ended_at=self.clock()
            if self.clock()-self.social_ended_at<.5:return
            # Preserve an interruption which is still being verified.
            if self.barge_capture:
                v=self.barge_capture.snapshot().get('speech_verification',{})
                if v.get('candidate') or v.get('pending'):return
            self._stop_barge();self.social_active=False;self.wake_rearm=True
            return
        from board.runtime.audio.attention_gate import read_attention
        current,_=read_attention(self._source(),self.attention_gate.boot_id,round(self.clock()*1000),require_frontal=False)
        snapshot=self.capture.snapshot() if self.capture else {}
        busy=(not self.monitor_owned or self.wake_rearm or self._playback_active()
              or self.transcriber.public().get('pending') or (self.monitor_entered and not self.social_opened))
        proposal=self.social_policy.observe(current['key'] if current else None,
            current['frame_id'] if current else None,self.clock(),busy=busy,
            speech_active=bool(snapshot.get('speech_active')))
        if proposal is None:return
        asset=getattr(self.transcriber,'social_assets',{}).get(proposal['kind'])
        if asset is None or not self._recording() or snapshot.get('speech_active'):return
        # Transfer the same audio input from idle capture to the existing
        # echo-verified interruption path while the cached cue plays.
        self.capture.cancel();self.transcriber.cancel()
        self.controller.submit_generated(asset,requested_at=self.clock())
        self.transcription=self._empty_transcription('PLAYING')
        self.transcription.update(request_id='social-'+uuid.uuid4().hex,text=proposal['text'])
        self.monitor_entered=True;self.auto_enabled=True;self.social_opened=True
        self.social_active=True;self.social_ended_at=None;self.social_count+=1

    def tick(self):
        result=super().tick()
        self._social_tick()
        return result

    def close(self):
        if self.observer:self.observer.close()
        super().close()

    def public(self):
        state = super().public()
        hf = state['handsfree_dialogue']
        hf.update(visual_bound=False, entry_mode='wake_word', visual_required=False,
                  speech_detection='vad_then_asr_wake_word', wake_words=['汐蓝', '欸', '哎'],
                  voice_barge_in=self.barge_enabled)
        state['voice_barge_in']['enabled'] = self.barge_enabled
        state['device_observer']=self.observer.public() if self.observer else {'enabled':False}
        state['visual_social']={'enabled':self.social_enabled,'active':self.social_active,'cues_played':self.social_count}
        if 'listening_timing' in hf:
            hf['listening_timing'].update(entry_confirmed=self.monitor_entered,
                                          holding_utterance=False, visual_hold=False)
        return state
