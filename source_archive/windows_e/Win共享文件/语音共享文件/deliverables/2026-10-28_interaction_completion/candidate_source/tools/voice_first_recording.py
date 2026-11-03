"""Wake-word conversation owner; vision never gates ordinary speech.

Reuses the existing single capture and verified echo/interruption path.
The inherited session key is an audio-session key, never a face identity.
"""
import uuid
from tools.barge_in_recording import BargeInRecordingController
from tools.board_recording import RecordingController


class VoiceFirstRecordingController(BargeInRecordingController):
    def __init__(self, *args, barge_enabled=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.barge_enabled = bool(barge_enabled)
        self.voice_first = True
        self.wake_rearm = False
        self.monitor_state = 'WAITING_WAKE' if self.monitor_enabled else 'PAUSED'
        self.monitor_reason = 'AUDIO_WAKE_WORD'
        self.last_voice_activity = self.clock()

    def _current(self):
        # The inherited interruption code needs a stable session owner, not
        # visual evidence. Do not query the camera, even if it is unavailable.
        if self.monitor_enabled and self.monitor_owned and self.monitor_key:
            return {'key': self.monitor_key}, 'AUDIO_SESSION'
        return None, 'NO_AUDIO_SESSION'

    def _queue_transcription(self):
        if self.monitor_owned and self.utterance is not None:
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

    def _entry_rejected(self):
        # Non-wake speech consumes no LLM/TTS/history and simply rearms the
        # same bounded audio listener. It is not a visual rejection/error.
        self.monitor_stats['entry_rejected'] += 1
        self.wake_rearm = True

    def _finish_session(self, *args, **kwargs):
        self.wake_rearm = False
        return super()._finish_session(*args, **kwargs)

    def cancel(self):
        self.wake_rearm = False
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

    def public(self):
        state = super().public()
        hf = state['handsfree_dialogue']
        hf.update(visual_bound=False, entry_mode='wake_word', visual_required=False,
                  speech_detection='vad_then_asr_wake_word', wake_words=['汐蓝', '欸', '哎'],
                  voice_barge_in=self.barge_enabled)
        state['voice_barge_in']['enabled'] = self.barge_enabled
        if 'listening_timing' in hf:
            hf['listening_timing'].update(entry_confirmed=self.monitor_entered,
                                          holding_utterance=False, visual_hold=False)
        return state
