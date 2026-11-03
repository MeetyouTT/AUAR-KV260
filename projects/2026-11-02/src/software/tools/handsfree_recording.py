"""Optional visual+speech entry around the existing single audio owner.

This is a readiness heuristic, not gaze estimation, voice identity or ASD.
Entry requires a fresh stable frontal face; the same visible track can then
turn slightly, with a bounded detection-gap grace period. Playback remains
half duplex and uses the existing full-playback ACK and tail guard.
"""
import threading
from board.runtime.audio.attention_gate import AttentionGate,read_attention
from board.interaction.ui_contract import validate_snapshot
from tools.board_recording import RecordingController


class HandsFreeRecordingController(RecordingController):
    def __init__(self,*args,boot_id,attention_provider,monitor_settings=None,early_listen=False,**kwargs):
        super().__init__(*args,**kwargs)
        self.attention_provider=attention_provider;self.attention_gate=AttentionGate(boot_id)
        self.monitor_enabled=True;self.monitor_owned=False;self.monitor_entered=False
        self.monitor_state='WAITING_PERSON';self.monitor_reason='VISUAL_UNAVAILABLE';self.monitor_error=''
        self.monitor_key=None;self.cooldown_until=0.;self.listen_started=0.;self.listen_id=None
        self.proof_lock=threading.Lock();self.speech_proof=None
        self.last_presence=None
        self.early_listen=bool(early_listen);self.entry_stable=not self.early_listen
        self.awaiting_entry=False;self.entry_deadline=None;self.visual_hold_since=None
        self.last_stop_reason='';self.stop_reasons={}
        self.monitor_stats={'armed':0,'speech_starts':0,'submitted':0,'entry_rejected':0,'visual_stops':0}
        self.monitor_settings=monitor_settings;self._closing=False
        if monitor_settings:
            try:self.monitor_enabled=monitor_settings.read()
            except (OSError,ValueError,TypeError):
                self.monitor_enabled=False;self.monitor_error='免点击设置读取失败，已保持暂停'
        if not self.monitor_enabled:self.monitor_state='PAUSED'

    def _source(self):
        try:return self.attention_provider()
        except Exception:return None

    def _current(self):
        snapshot=self._source();now=round(self.clock()*1000)
        current,reason=read_attention(snapshot,self.attention_gate.boot_id,now,require_frontal=False)
        if current:
            if current['key']==self.monitor_key:self.last_presence=current
            return current,reason
        # Once frontal intent is established, a short zero-detection gap is not
        # a new speaker. Never bridge multiple faces, unconfirmed targets,
        # service changes or network/clock failure. The 1s bound equals the
        # existing face track's expiry and never authorizes identity operations.
        last=self.last_presence
        if self.monitor_owned and last and reason=='NO_SINGLE_FACE' and 0<=now-last['stamp']<1000:
            try:
                value=validate_snapshot(snapshot,self.attention_gate.boot_id,now)
                if (value['source_kind']=='actual' and value['service_epoch']==self.monitor_key[0]
                        and value['modules']['camera']['state']=='READY'
                        and (not value.get('preview') or value['preview']['camera_epoch']==self.monitor_key[1])
                        and value['modules']['identity']['face_count']==0):
                    return last,'BRIEF_DETECTION_GAP'
            except (ValueError,KeyError,TypeError):pass
        return None,reason

    def _finish_session(self,reason,delay=.8):
        # Private automatic stop does not revoke the user's monitoring choice.
        self.monitor_owned=False;self.monitor_entered=False;self.monitor_key=None
        self.last_presence=None
        self.entry_stable=not self.early_listen;self.awaiting_entry=False;self.entry_deadline=None;self.visual_hold_since=None
        self.last_stop_reason=reason;self.stop_reasons[reason]=self.stop_reasons.get(reason,0)+1
        if reason in ('NO_SINGLE_FACE','NOT_FRONTAL','TARGET_CHANGED','STALE_FACE','VISUAL_UNAVAILABLE'):
            self.monitor_stats['visual_stops']+=1
        with self.proof_lock:self.speech_proof=None
        RecordingController.cancel(self)
        self.attention_gate.reset();self.cooldown_until=self.clock()+delay
        self.monitor_reason=reason;self.monitor_state='COOLDOWN'

    def _visual_hold(self,reason):
        """Keep RAM capture briefly; stale visual evidence never submits speech."""
        if not self.early_listen or reason not in ('NO_SINGLE_FACE','NOT_FRONTAL'):return False
        try:
            value=validate_snapshot(self._source(),self.attention_gate.boot_id,round(self.clock()*1000))
            identity=value['modules']['identity']
            if (value['source_kind']!='actual' or value['service_epoch']!=self.monitor_key[0]
                    or value['modules']['camera']['state']!='READY'
                    or value.get('preview',{}).get('camera_epoch',self.monitor_key[1])!=self.monitor_key[1]
                    or identity.get('face_count') not in (0,1)):return False
        except (ValueError,KeyError,TypeError):return False
        if self.visual_hold_since is None:self.visual_hold_since=self.clock()
        return self.clock()-self.visual_hold_since<1.5

    def _speech_started(self):
        current,_=self._current()
        if current and self.monitor_owned and current['key']==self.monitor_key:
            self.monitor_stats['speech_starts']+=1
            proof=(self.listen_id,self.monitor_key)
            if self.transcriber and hasattr(self.transcriber,'capture_started'):
                self.transcriber.capture_started(self.listen_id)
            with self.proof_lock:self.speech_proof=proof

    def _listen(self):
        if self.monitor_owned:
            with self.proof_lock:self.speech_proof=None
        cid=super()._listen()
        self.listen_id=cid;self.listen_started=self.clock()
        return cid

    def _queue_transcription(self):
        if self.monitor_owned:
            current,_=self._current()
            if self.early_listen and (not current or not self.entry_stable):
                self.awaiting_entry=True
                if self.entry_deadline is None:self.entry_deadline=self.clock()+1.5
                self.recording_state='WAITING_VISUAL';self.monitor_state='CONFIRMING_SPEECH'
                return
            with self.proof_lock:proof=self.speech_proof
            if (not current or current['key']!=self.monitor_key or self.utterance is None
                    or proof!=(self.utterance.capture_id,self.monitor_key)):
                self._finish_session('VISUAL_SPEECH_NOT_BOUND');return
            if not self.monitor_entered:
                # Automatic entry always creates a new anonymous conversation.
                self.transcriber.select_conversation(resume=False)
                self.transcriber.mark_visual_entry(self.utterance.capture_id)
                self.monitor_entered=True;self.auto_enabled=True
                self.monitor_state='CHECKING_SPEECH'
            self.awaiting_entry=False;self.entry_deadline=None
        super()._queue_transcription()
        if self.monitor_owned and self.transcription['state']=='TRANSCRIBING':self.monitor_stats['submitted']+=1

    def _collect(self):
        # Visual intent gates acquisition/submission. Once accepted, finish
        # generating and playing this reply, rather than cutting it on a head
        # turn or lost face. Revalidate before opening the next listener.
        if self.monitor_owned and (self._recording() or self.awaiting_entry):
            current,reason=self._current()
            if not current or current['key']!=self.monitor_key:
                if current or not self._visual_hold(reason):
                    self._finish_session(reason if not current else 'TARGET_CHANGED');return
                self.monitor_state='CONFIRMING_SPEECH';self.monitor_reason='WAITING_FRESH_FACE'
            else:self.visual_hold_since=None
        super()._collect()

    def _auto_tick(self):
        if self.monitor_owned and self.auto_enabled and self.transcription['state']=='ANSWERED':
            ack=self.transcriber.public().get('last_playback_ack') or {}
            if (ack.get('request_id')==self.transcription['request_id'] and ack.get('committed')
                    and self.clock()>=self.rearm_at and not self._playback_active()
                    and not self.transcriber.public().get('pending')):
                current,reason=self._current()
                if not current or current['key']!=self.monitor_key:
                    self._finish_session(reason if not current else 'TARGET_CHANGED');return
        super()._auto_tick()

    def _entry_rejected(self):
        self.monitor_stats['entry_rejected']+=1
        self._finish_session('NO_VALID_INITIAL_SPEECH',1.5)

    def handsfree_toggle(self):
        if self.monitor_enabled:
            self.cancel()
        else:
            if self.monitor_settings:self.monitor_settings.write(True)
            self.monitor_enabled=True;self.monitor_error='';self.attention_gate.reset()
            self.cooldown_until=self.clock()+.5;self.monitor_state='WAITING_PERSON'
        return {'enabled':self.monitor_enabled}

    def cancel(self):
        self.monitor_enabled=False;self.monitor_owned=False;self.monitor_entered=False
        self.monitor_key=None;self.monitor_state='PAUSED'
        self.last_presence=None
        self.awaiting_entry=False;self.entry_deadline=None;self.visual_hold_since=None
        self.entry_stable=not self.early_listen
        if self.monitor_settings and not self._closing:
            try:self.monitor_settings.write(False)
            except OSError:self.monitor_error='已关闭麦克风，但暂停设置未能保存'
        with self.proof_lock:self.speech_proof=None
        return super().cancel()

    def _monitor_tick(self):
        if self.closed or not self.monitor_enabled:return
        if self.monitor_owned:
            if self.early_listen and not self.entry_stable:
                current,reason=self.attention_gate.observe(self._source(),round(self.clock()*1000))
                if current and current['key']==self.monitor_key:self.entry_stable=True
            if self.awaiting_entry:
                if self.clock()>=self.entry_deadline:
                    self._finish_session('SPEECH_TARGET_NOT_CONFIRMED');return
                current,reason=self._current()
                if current and current['key']==self.monitor_key and self.entry_stable:self._queue_transcription()
                if self.awaiting_entry:self.monitor_state='CONFIRMING_SPEECH';return
            if self.recording_state=='ERROR' or self.transcription['state']=='ERROR' or self.auto_error:
                self.monitor_error=self.recording_error or self.transcription['error'] or self.auto_error
                self._finish_session('SERVICE_ERROR',5.);return
            if (self._recording() and self.clock()-self.listen_started>=30.
                    and (not self.early_listen or not self.capture.snapshot().get('speech_active'))):
                if self.early_listen:self.listen_started=self.clock()  # Bounded PCM ring; no silent reopen gap.
                else:self._finish_session('SILENCE_TIMEOUT',1.5);return
            self.monitor_state=('PREPARING_SPEECH' if self._recording() and self.early_listen and not self.entry_stable else
                                'CONFIRMING_SPEECH' if self._recording() and self.visual_hold_since is not None else
                                'WAITING_SPEECH' if self._recording() else
                                'CONVERSATION' if self.transcription.get('text') else
                                'CHECKING_SPEECH' if self.monitor_entered else 'WAITING_SPEECH')
            return
        if self.auto_enabled:return  # Explicit manual mode retains its existing owner.
        if self.clock()<self.cooldown_until:return
        if self._recording() or self._playback_active():
            self.monitor_state='WAITING_AUDIO_IDLE';self.attention_gate.reset();return
        service=self.transcriber.public() if self.transcriber else {}
        if not service.get('feedback_ready') or service.get('pending') or not self.transcriber.enabled():
            self.monitor_state='WAITING_SERVICE';self.attention_gate.reset()
            if self.transcriber and hasattr(self.transcriber,'refresh_feedback'):self.transcriber.refresh_feedback()
            return
        source=self._source();current,reason=self.attention_gate.observe(source,round(self.clock()*1000))
        stable=current is not None
        if current is None and self.early_listen:
            current,_=read_attention(source,self.attention_gate.boot_id,round(self.clock()*1000))
        self.monitor_reason=reason
        if current is None:self.monitor_state='WAITING_PERSON';return
        try:
            self.monitor_owned=True;self.monitor_key=current['key'];self.monitor_entered=False
            self.entry_stable=stable;self.awaiting_entry=False;self.entry_deadline=None;self.visual_hold_since=None
            self.last_presence=current;self.monitor_stats['armed']+=1
            capture=self._capture_for(True);capture.on_speech_start=self._speech_started
            self.auto_error='';self.last_error='';self.monitor_error='';self.auto_turns=0
            self._listen();self.monitor_state='WAITING_SPEECH'
        except Exception as exc:
            self.monitor_error=str(exc);self._finish_session('CAPTURE_ERROR',5.)

    def tick(self):
        self._monitor_tick()
        result=super().tick()
        self._monitor_tick()
        return result

    def public(self):
        state=super().public()
        state['handsfree_dialogue']={'enabled':self.monitor_enabled,'state':self.monitor_state,
            'reason':self.monitor_reason,'error':self.monitor_error,
            'visual_bound':self.monitor_owned,'conversation_entered':self.monitor_entered,
            'microphone_open':self._recording(),'speech_detection':'energy_vad_then_asr',
            'diagnostics':dict(self.monitor_stats),
            'speaker_binding_verified':False,'voice_barge_in':False}
        if self.early_listen:
            snapshot=self.capture.snapshot() if self.capture else {}
            state['handsfree_dialogue']['listening_timing']={
                'enabled':True,'entry_confirmed':self.entry_stable and self.monitor_owned,
                'input_ready':self._recording() and snapshot.get('input_ready',True),
                'holding_utterance':self.awaiting_entry,'visual_hold':self.visual_hold_since is not None,
                'last_stop_reason':self.last_stop_reason,'stop_reasons':dict(self.stop_reasons)}
        return state

    def close(self):
        self._closing=True
        super().close()
