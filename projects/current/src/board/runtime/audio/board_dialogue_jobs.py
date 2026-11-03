"""Opt-in board job/stream adapter; never opens a microphone or player.

Baseline: actual r3 channel_jobs.py SHA256 015e13d27db25819d002c4c87087802e02
e8b65ac10119bf467635871b458822 and the current 24kHz StreamingController.
This is a candidate, not a complete drop-in replacement for identity, calibrated
speaker attribution, visual entry, native reasoning or automatic interruption.
Missing board handlers fail closed; no legacy Windows business HTTP is used.
"""
from __future__ import annotations

from collections import deque
from contextlib import ExitStack
import copy
from dataclasses import dataclass, field
import hashlib
import math
import queue
import re
import threading
import time
import uuid

from board.runtime.board_dialogue import PlaybackPlan, StaleGeneration
from board.runtime.audio.transcription import configuration
from board.runtime.audio.board_asr import BoardNoSpeech
from common.asr_wire import PROTOCOL as ASR_PROTOCOL, context as validate_capture
from common.voice_channel import ChannelState, PROTOCOL as CHANNEL_PROTOCOL, MAX_SAMPLES, PACKET_SAMPLES


def _entry_parser_flags(parser):
    # Only fixed code-constant membership is exposed, never code paths/text.
    code = getattr(parser, '__code__', None)
    constants = getattr(code, 'co_consts', ())
    pending = list(constants[:128]) if type(constants) is tuple else []
    face = voice = False
    for _ in range(256):
        if not pending:break
        value = pending.pop()
        if type(value) is str:
            face = face or value == 'face_only'
            voice = voice or value == 'voice_only'
        elif type(value) in (tuple, frozenset):
            pending.extend(list(value)[:128])
    return dict(parser_code_known=code is not None,parser_face_only_const=face, parser_voice_only_const=voice)


def _entry_route_trace():
    return dict(version=1,asr_characters=0,asr_result_seen=False,binding_kind='not_evaluated',
        speaker_requested=False,enrollment_checked=False,enrollment_active=False,
        capability='not_selected',handler_available=False,handler_called=False,
        handler_result='not_called',error_class='none',outcome='started',
        parser_code_known=False,parser_face_only_const=False,parser_voice_only_const=False,
        has_register=False,has_voiceprint=False,has_voice=False,has_warming=False,
        has_face=False,has_my_name=False,has_level=False,has_i_want=False,has_i_would_like=False,
        has_a_bit=False,has_voice_word=False,has_identity=False,has_name_word=False)


def _entry_asr_trace(trace, raw):
    if not isinstance(raw,str):return
    trace.update(asr_characters=min(len(raw),4097),asr_result_seen=True,
        has_register='登记' in raw,has_voiceprint='声纹' in raw,has_voice='声音' in raw,
        has_warming='升温' in raw,has_face='人脸' in raw,has_my_name='我叫' in raw,has_level='等级' in raw,
        has_i_want='我要' in raw,has_i_would_like='我想' in raw,has_a_bit='一下' in raw,
        has_voice_word='声文' in raw,has_identity='身份' in raw,has_name_word='名字' in raw)


class BoardCapabilityNotReady(RuntimeError):
    def __init__(self, capability):
        self.capability = capability
        super().__init__('board_handler_not_ready:' + capability)


@dataclass(frozen=True)
class PlaybackPayload:
    """Explicit board conversion output for the existing 24kHz PCM player.

    A converter is an independently reviewed board policy, not automatic
    resampling. Native receipts remain bound to the controller plan, while this
    payload gets a separate digest/count checked at the player completion bridge.
    """
    pcm: bytes
    sample_rate: int = 24000
    converter_id: str = 'identity-24k'


@dataclass
class _Job:
    meta: dict
    pcm: bytes
    scope: dict
    deadline: float
    entry: str | None
    capture_snapshot: object = None
    context_source_id: str | None = None
    cancelled: threading.Event = field(default_factory=threading.Event)
    diagnostics: dict = field(default_factory=lambda: dict(guard_calls=0, guard_total_ms=0.,
        guard_thread_cpu_total_ms=0., guard_thread_cpu_max_ms=0.,
        progress_wait_ms=0., progress_wait_peak_ms=0., progress_queue_peak=0))


@dataclass
class _Playback:
    meta: dict
    plan: PlaybackPlan
    payload: PlaybackPayload
    result: dict


def _same_owner(left, right):
    return all(left.get(key) == right.get(key) for key in
               ('board_boot_id', 'session_id', 'generation', 'request_id', 'capture_id'))


class BoardDialogueJobs:
    """Latest waiting capture, one inference owner and bounded UI/action queues.

    `start_worker=False` permits deterministic candidate tests with run_next()
    and drain_actions(); it never starts background work. Production factories
    must explicitly inject local scope/profile, feedback and special handlers.

    `special_handlers[capability](text, *, job, controller, is_current, cancel_event)` must
    return a PlaybackPlan already owned by the same controller. This hook is for
    reviewed board handlers only. A missing hook is an explicit unavailable path.
    """
    def __init__(self, controller, config, boot_id, *, asr=None, conversation_path=None,
                 conversation_selection=None, scope_provider=None, profile_resolver=None,
                 profile_release=None, visual_entry_handler=None, special_handlers=None,
                 history_router=None, audio_converter=None, playback_invalidator=None,
                 feedback_provider=None, inference_reconfigure=None,
                 analysis_provider=None, visual_intent_matcher=None,
                 clock=time.monotonic, wall_clock=None, timezone='America/Los_Angeles',
                 start_worker=True):
        if controller.board_boot_id != boot_id:
            raise ValueError('Controller belongs to another board boot')
        self.controller, self.asr = controller, asr if asr is not None else controller.asr
        self.config, self.boot_id = configuration(config), boot_id
        self.clock, self.wall_clock, self.timezone = clock, wall_clock, timezone
        if conversation_path is not None and conversation_selection is not None:
            raise ValueError('Supply one board conversation selector')
        if conversation_path is not None:
            from common.conversation_selection import ConversationSelection
            conversation_selection = ConversationSelection(conversation_path)
        self.conversation_selection, self.scope_provider = conversation_selection, scope_provider
        self.profile_resolver, self.profile_release = profile_resolver, profile_release
        self.visual_entry_handler = visual_entry_handler
        self.special_handlers = dict(special_handlers or {})
        self.history_router, self.audio_converter = history_router, audio_converter
        self.playback_invalidator, self.feedback_provider = playback_invalidator, feedback_provider
        self.inference_reconfigure = inference_reconfigure
        self.analysis_provider, self.visual_intent_matcher = analysis_provider, visual_intent_matcher
        self.condition = threading.Condition(threading.RLock())
        self.session_id = uuid.uuid4().hex
        self.generation = 0
        self.waiting = self.active = self._active_job = self._playback = None
        self._stream_clock = None
        self.progress = deque()
        self.closed = False
        self.profile_selection = None
        self.identity_snapshot = None  # Set by the existing board UI service provider.
        self.capture_owners = {}
        self.visual_entry_capture = self.wake_entry_capture = None
        self.feedback_assets = {}; self.social_assets = {}; self.feedback_error = ''
        self.last_ack = self.last_voice_route = None
        self.next_feedback_refresh = 0.
        self.cleanup_error = ''
        self.latency_metrics = {}
        self.progress_diagnostics = {}
        self._actions = queue.Queue(maxsize=16)
        self._cancel_queued = set()
        self._ack_queued = set()
        self.thread = self.action_thread = None
        if start_worker:
            self.start()

    def start(self):
        """Explicit factory start after clock, GUI providers and sinks are bound."""
        with self.condition:
            if self.closed:
                raise RuntimeError('Board dialogue jobs are closed')
            if self.thread is not None:
                return
            self.thread = threading.Thread(target=self.work, name='board-dialogue-jobs', daemon=True)
            self.action_thread = threading.Thread(target=self._action_worker, name='board-dialogue-receipts', daemon=True)
            self.thread.start(); self.action_thread.start()

    def enabled(self):
        with self.condition:
            return self.config['enabled'] and not self.closed and not self.cleanup_error

    @property
    def idle(self):
        """Combine with controller.idle for the board memory-worker idle gate."""
        with self.condition:
            return not (self.waiting or self.active or self._playback or self._actions.unfinished_tasks)

    def _current(self, job):
        return (not self.closed and not job.cancelled.is_set()
                and job.meta['board_boot_id'] == self.boot_id
                and job.meta['session_id'] == self.session_id
                and job.meta['generation'] == self.generation)

    def _check(self, job):
        with self.condition:
            if not self._current(job):
                raise StaleGeneration('Recording no longer owns this job')
        if self.clock() >= job.deadline:
            raise TimeoutError('Original capture deadline expired')

    def _invalidate_presentation(self, reason, meta=None, playback_token=None):
        if self.playback_invalidator is not None:
            owner = {key: (meta or {}).get(key) for key in
                     ('board_boot_id', 'session_id', 'generation', 'request_id')}
            owner['playback_token'] = playback_token
            # The injected hook must only invalidate caches/state, without I/O.
            self.playback_invalidator(reason, owner)

    def _queue_action(self, value):
        try:
            self._actions.put_nowait(value)
            return True
        except queue.Full:
            # Never block the audio/render owner or accept a new turn when
            # cancellation/receipt processing cannot keep up.
            self.cleanup_error = 'board_receipt_queue_full'
            return False

    def _queue_cancel(self, meta):
        with self.condition:
            key = (meta['session_id'], meta['generation'])
            if key not in self._cancel_queued:
                if self._queue_action(('cancel', key)):
                    self._cancel_queued.add(key)

    def _invalidate(self):
        """Same immediate generation/progress invalidation as the accepted jobs.

        Remote cancellation and Store I/O run on the separate bounded action
        worker so a UI cancellation does not wait for network cleanup.
        """
        with self.condition:
            old = self._active_job
            if old is not None:
                old.cancelled.set(); self._queue_cancel(old.meta)
            if self.waiting is not None:
                self.waiting.cancelled.set()
            if self._playback is not None:
                media = self._playback
                self._queue_cancel(media.meta)
                self._invalidate_presentation('playback_cancelled', media.meta, media.plan.playback_token)
            else:
                self._invalidate_presentation('generation_changed', old.meta if old else None)
            self.generation += 1
            self.waiting = self._playback = None
            self._stream_clock = None
            self.progress.clear()
            self.condition.notify_all()

    def cancel(self):
        self._invalidate()

    def configure(self, values):
        values = configuration(values)
        with self.condition:
            if self.closed:
                raise ValueError('Board dialogue jobs are closed')
            if (values['host'], values['port']) != (self.config['host'], self.config['port']):
                if self.inference_reconfigure is None:
                    raise BoardCapabilityNotReady('inference_reconfiguration')
                self.inference_reconfigure(values)
            self.config = values
            self._invalidate()

    def _require_idle_selection(self):
        if self.closed or self.waiting or self.active or self._playback:
            raise ValueError('请先结束当前录音、生成和播放，再切换对话或档案')

    def select_conversation(self, *, resume):
        if type(resume) is not bool:
            raise ValueError('Expected explicit conversation selection')
        with self.condition:
            self._require_idle_selection()
            if self.profile_selection is not None:
                if not resume:
                    # The Store filters recent messages by this explicit local
                    # conversation source; profile facts/history remain scoped
                    # to the same live grant, without widening authorization.
                    self.profile_selection = dict(self.profile_selection, conversation_id=uuid.uuid4().hex)
                cid = self.profile_selection['conversation_id']
            else:
                if self.conversation_selection is None:
                    raise BoardCapabilityNotReady('conversation_selection')
                cid = self.conversation_selection.select(resume)
            self._invalidate()
            if self.profile_selection is None:
                self.session_id = uuid.uuid4().hex
            self.reset_enrollment()
            return cid

    def select_profile(self, value):
        with self.condition:
            self._require_idle_selection()
            if value is not None:
                if self.profile_resolver is None or self.profile_release is None:
                    raise BoardCapabilityNotReady('profile_selection')
                selected = self.profile_resolver(value, self.boot_id)
                if (not isinstance(selected, dict) or selected.get('scope', {}).get('kind') != 'profile'
                        or 'grant' not in selected['scope']
                        or not re.fullmatch(r'[A-Za-z0-9_-]{1,96}', selected.get('session_id', ''))
                        or not re.fullmatch(r'[0-9a-f]{32}', selected.get('conversation_id', ''))):
                    raise PermissionError('A live board-local profile grant is required')
            else:
                selected = None
            previous = self.profile_selection
            self._invalidate(); self.profile_selection = selected
            self.session_id = selected['session_id'] if selected is not None else uuid.uuid4().hex
            if selected is None and self.conversation_selection is not None:
                self.conversation_selection.select(False)
            if previous is not None and self.profile_release is not None:
                self._queue_action(('release_profile', previous))
            self.reset_enrollment()

    def _scope(self, meta):
        if self.profile_selection is not None:
            return dict(self.profile_selection['scope'])
        if self.scope_provider is not None:
            scope = self.scope_provider(meta)
            if not isinstance(scope, dict) or scope.get('kind') not in ('conversation', 'profile', 'device'):
                raise PermissionError('No board-authorized scope')
            return dict(scope)
        selection = self.conversation_selection
        if selection is None or selection.active is None:
            raise ValueError('请先选择继续上次对话或新对话')
        return dict(kind='conversation', id=selection.active)

    def capture_started(self, capture_id):
        # Only the in-memory board provider is consulted; no image/identity
        # request, network call or biometric template export is performed.
        from board.interaction.ui_contract import validate_snapshot, millis
        try:
            value = self.identity_snapshot() if self.identity_snapshot else None
            value = validate_snapshot(value, self.boot_id, millis())
        except (ValueError, KeyError, TypeError):
            value = None
        with self.condition:
            self.capture_owners = {capture_id: copy.deepcopy(value)}

    def mark_visual_entry(self, capture_id):
        with self.condition:
            self.visual_entry_capture = capture_id

    def mark_wake_entry(self, capture_id):
        with self.condition:
            self.wake_entry_capture = capture_id

    def submit(self, clip):
        with self.condition:
            if not self.enabled():
                raise ValueError('Board dialogue jobs are unavailable or disabled')
            self._invalidate()
            meta = dict(protocol=ASR_PROTOCOL, board_boot_id=self.boot_id, session_id=self.session_id,
                        request_id=uuid.uuid4().hex, generation=self.generation, capture_id=clip.capture_id,
                        sample_count=clip.audio.sample_count, pcm_sha256=hashlib.sha256(clip.pcm).hexdigest(),
                        budget_ms=self.config['timeout_ms'])
            validate_capture(meta, clip.pcm)
            scope = self._scope(meta)
            wake = self.wake_entry_capture == clip.capture_id
            visual = self.visual_entry_capture == clip.capture_id
            if wake and visual:
                raise ValueError('Conflicting capture entry modes')
            self.wake_entry_capture = self.visual_entry_capture = None
            self.waiting = _Job(meta, clip.pcm, scope, self.clock() + meta['budget_ms'] / 1000,
                                'wake' if wake else 'visual' if visual else None,
                                copy.deepcopy(self.capture_owners.get(clip.capture_id)),
                                ('conversation:' + self.profile_selection['conversation_id']
                                 if self.profile_selection is not None else
                                 'conversation:' + self.conversation_selection.active
                                 if self.conversation_selection is not None and self.conversation_selection.active else
                                 'conversation:' + scope['id'] if scope['kind'] == 'conversation' else None))
            self.condition.notify_all()
            return dict(meta)

    def poll(self):
        with self.condition:
            if not self.progress:
                return None
            value = self.progress.popleft(); self.condition.notify_all()
            return value

    def _wait_progress(self, job):
        # Called with the existing condition held; wait releases it as before.
        started = time.perf_counter()
        try:
            self.condition.wait(.05)
        finally:
            elapsed = (time.perf_counter() - started) * 1000
            metrics = job.diagnostics
            metrics['progress_wait_ms'] += elapsed
            metrics['progress_wait_peak_ms'] = max(metrics['progress_wait_peak_ms'], elapsed)

    @staticmethod
    def _diagnostic_error_class(exc):
        # Only fixed classes, never an arbitrary exception name or message.
        name = type(exc).__name__
        return name if name in {'BoardCapabilityNotReady', 'StaleGeneration', 'TimeoutError',
            'PermissionError', 'ValueError', 'RuntimeError', 'OSError', 'ConnectionError',
            'ModelRequestError', 'ReplyRejected', 'ScopeDenied', 'StaleTurn',
            'InterruptedError', 'MemoryError'} else 'other'

    def _put(self, job, value, *, admission_guard=None):
        if admission_guard is None:
            with self.condition:
                while len(self.progress) >= 128:
                    self._check(job); self._wait_progress(job)
                self._check(job)
                self.progress.append(dict(value, context=dict(job.meta)))
                job.diagnostics['progress_queue_peak'] = max(job.diagnostics['progress_queue_peak'], len(self.progress))
                self.condition.notify_all()
            return
        while True:
            started = time.perf_counter()
            thread_started = time.thread_time()
            try:
                admission_guard()  # SQL check outside the condition, including after every wait.
            finally:
                elapsed = (time.perf_counter() - started) * 1000
                thread_elapsed = (time.thread_time() - thread_started) * 1000
                with self.condition:
                    job.diagnostics['guard_calls'] += 1
                    job.diagnostics['guard_total_ms'] += elapsed
                    job.diagnostics['guard_thread_cpu_total_ms'] += thread_elapsed
                    job.diagnostics['guard_thread_cpu_max_ms'] = max(
                        job.diagnostics['guard_thread_cpu_max_ms'], thread_elapsed)
            with self.condition:
                self._check(job)
                if len(self.progress)<128:
                    self.progress.append(dict(value, context=dict(job.meta)))
                    job.diagnostics['progress_queue_peak'] = max(job.diagnostics['progress_queue_peak'], len(self.progress))
                    self.condition.notify_all()
                    return
                self._wait_progress(job)

    def _put_error(self, job, exc):
        with self.condition:
            # Controller failure also sets the shared cancellation Event. Only
            # explicit job invalidation changes the owner generation/session;
            # a current failure must still stop the player's partial stream.
            if (not self.closed and job.meta['board_boot_id'] == self.boot_id
                    and job.meta['session_id'] == self.session_id
                    and job.meta['generation'] == self.generation):
                # A failed partial stream must stop before queued stale PCM.
                self.progress.clear()
                self._stream_clock = None
                self._invalidate_presentation('stream_failed', job.meta)
                if getattr(exc, 'entry_rejected', False):
                    value = dict(entry_rejected=True)
                else:
                    value = dict(error=(str(exc) if isinstance(exc, BoardCapabilityNotReady)
                                        else type(exc).__name__))
                self.progress.append(dict(value, context=dict(job.meta)))
                self.condition.notify_all()

    @staticmethod
    def _entry_error():
        error = ValueError('Speech entry rejected')
        error.entry_rejected = True
        return error

    def _admit_text(self, job, raw_text):
        from common.handsfree_entry import audio_candidate, acceptable_entry
        from common.spoken_input import prepare_spoken_input
        from common.voice_wake import wake_request
        if not isinstance(raw_text, str) or len(raw_text) > 4096:
            raise ValueError('No bounded board ASR text')
        if any(ord(c) < 32 for c in raw_text):
            raise ValueError('ASR text cannot enter the stream protocol')
        if not raw_text.strip():
            raise self._entry_error()
        text = raw_text.strip()
        interpreted = prepare_spoken_input(text)
        if job.entry:
            if not audio_candidate(job.pcm):
                raise self._entry_error()
            if job.entry == 'wake':
                text = wake_request(interpreted['text'])
                if text is None:
                    raise self._entry_error()
                if not text:
                    return None
            else:
                if self.visual_entry_handler is None:
                    raise BoardCapabilityNotReady('visual_entry_authorization')
                accepted = self.visual_entry_handler(job.meta, job.capture_snapshot, text,
                                                    is_current=lambda: self._current(job))
                if accepted is not True or not acceptable_entry(text):
                    raise self._entry_error()
        # Preserve raw ASR for ordinary turns. A production context builder may
        # apply conservative vocative interpretation only to model input.
        return text

    def _publish_entry_route_trace(self, job, trace):
        with self.condition:
            last = self.last_voice_route
            if isinstance(last,dict) and last.get('generation') == job.meta['generation']:
                last['entry_trace'] = copy.deepcopy(trace)

    def _route(self, job, text, *, reply_sink=None):
        from common.voice_enrollment import (
            enrollment_requested, identity_query_requested, cancelled, confirmed, update_confirmed,
        )
        from common.binding_intent import binding_intent
        from common.feature_intents import speaker_requested,speaker_query_requested
        from common.thinking_policy import route
        from common.timeline import recall_requested, query
        from common.profile_memory import scoped_command
        from common.visual_question import requested as visual_requested
        from common.spoken_input import prepare_spoken_input
        from board.runtime.character import CHARACTER_NAME
        trace = getattr(job,'entry_route_trace',None)
        if trace is None:
            trace = _entry_route_trace();_entry_asr_trace(trace,text);job.entry_route_trace = trace
        trace.update(_entry_parser_flags(binding_intent))
        def enrollment_active():
            active = self._enrollment_state().get('active')
            trace.update(enrollment_checked=True,enrollment_active=bool(active))
            return active
        intent_text = prepare_spoken_input(text)['text']
        visual_requested_by_policy = bool(self.visual_intent_matcher is not None and
                                          self.visual_intent_matcher(intent_text))
        binding = binding_intent(intent_text)
        speaker_requested_by_policy = speaker_requested(intent_text)
        kind = binding.get('kind')
        trace.update(binding_kind=kind if type(kind) is str and kind in
            ('ordinary','remember_self','name_hint','invalid_name','face_only','voice_only') else 'other',
            speaker_requested=bool(speaker_requested_by_policy))
        self._publish_entry_route_trace(job,trace)
        command_text = re.sub(r'^\s*' + re.escape(CHARACTER_NAME) + r'[\s，,：:]*', '', intent_text, count=1)
        command, _ = scoped_command(command_text, job.scope.get('kind') == 'profile')
        if (command is not None and not speaker_requested_by_policy
                and binding['kind'] not in ('remember_self', 'name_hint', 'invalid_name', 'face_only', 'voice_only')):
            trace['capability'] = 'explicit_memory_commands'
            self._publish_entry_route_trace(job,trace)
            if self.controller.command_handler is None:
                raise BoardCapabilityNotReady('explicit_memory_commands')
            return None, None
        recalled = recall_requested(text)
        capability = None
        if speaker_query_requested(intent_text):
            capability = 'speaker_identity'
        elif (enrollment_active() or enrollment_requested(text)
                or cancelled(text) or confirmed(text) or update_confirmed(text)
                or binding['kind'] in ('remember_self', 'name_hint', 'invalid_name', 'face_only')):
            capability = 'identity_enrollment'
        elif identity_query_requested(text):
            capability = 'identity_query'
        elif speaker_requested_by_policy:
            capability = 'speaker_identity'
        elif (re.search(r'(?:删除|清除|清理).{0,12}(?:昨天|前天|历史|时间轴|记录)', text)
              or re.fullmatch(r'(?:确认|取消)(?:删除|清除)(?:记录|历史|时间轴)?[。！!？?]*', text)):
            capability = 'history_delete_preview'
        elif visual_requested_by_policy or not recalled and visual_requested(text):
            capability = 'structured_visual_query'
        elif route(text)['mode'] == 'reasoning':
            capability = 'reasoning_dialogue'
        trace['capability'] = capability or 'ordinary_dialogue'
        self._publish_entry_route_trace(job,trace)
        if capability:
            handler = self.special_handlers.get(capability)
            trace['handler_available'] = handler is not None
            self._publish_entry_route_trace(job,trace)
            if handler is None:
                raise BoardCapabilityNotReady(capability)
            self._check(job)
            kwargs = dict(job=job, controller=self.controller,
                          is_current=lambda: self._current(job), cancel_event=job.cancelled)
            if getattr(handler, 'streaming_reply', False):
                kwargs['reply_sink'] = reply_sink
            trace['handler_called'] = True
            trace['handler_result'] = 'calling'
            self._publish_entry_route_trace(job,trace)
            try:
                value = handler(text, **kwargs)
            except BaseException as exc:
                trace['handler_result'] = 'error'
                trace['error_class'] = self._diagnostic_error_class(exc)
                self._publish_entry_route_trace(job,trace)
                raise
            trace['handler_result'] = 'none' if value is None else 'returned'
            self._publish_entry_route_trace(job,trace)
            return value, None
        if self.history_router is not None:
            return None, self.history_router(text, scope=dict(job.scope),
                                             now=self.wall_clock() if self.wall_clock else None)
        if recalled:
            if self.wall_clock is None:
                raise BoardCapabilityNotReady('trusted_history_clock')
            selected = query(text, now=self.wall_clock(), zone=self.timezone)
            if selected.get('error'):
                raise BoardCapabilityNotReady('explicit_history_range')
            # Topic is an exact partition; search is the distinct pre-LIMIT
            # text/keyword filter. Keep the user's explicit subject in recall.
            return None, dict(start=selected['start'], end=selected['end'],
                              search=selected['topic'] or None, limit=20)
        return None, None

    def _stream_payload(self, plan):
        raw = plan.pcm
        if (len(raw) != plan.samples * 2 or hashlib.sha256(raw).hexdigest() != plan.sha256
                or plan.sample_rate not in range(8000, 96001)):
            raise ValueError('Controller plan audio receipt is invalid')
        if plan.sample_rate == 24000:
            payload = PlaybackPayload(raw)
        else:
            if self.audio_converter is None:
                raise BoardCapabilityNotReady('native_rate_playback_bridge')
            payload = self.audio_converter(plan)
        if (not isinstance(payload, PlaybackPayload) or payload.sample_rate != 24000
                or not isinstance(payload.pcm, bytes) or not payload.pcm or len(payload.pcm) % 2
                or len(payload.pcm) // 2 > MAX_SAMPLES
                or not isinstance(payload.converter_id, str) or not payload.converter_id
                or len(payload.converter_id) > 128):
            raise ValueError('Existing stream player requires bounded 24kHz mono PCM16')
        if abs((len(payload.pcm) // 2) / 24000 - plan.samples / plan.sample_rate) > 1 / 24000 + 1e-9:
            raise ValueError('Playback bridge changed audio duration')
        if len(plan.reply.text) > 240:
            raise BoardCapabilityNotReady('reply_over_legacy_stream_limit')
        return payload

    def _execute(self, job):
        job_started = self.clock()
        phase = dict(metadata_only=True,speaker_first_audio_measured=False,asr_calls=0,
                     asr_completed=False,wake_only=False,entry_rejected=False,complete=False,error_class='none')
        trace = _entry_route_trace();job.entry_route_trace = trace
        with self.condition:
            self.progress_diagnostics = job.diagnostics
            if (not self.closed and job.meta['generation']==self.generation
                    and job.meta['session_id']==self.session_id):
                self.last_voice_route = dict(generation=job.meta['generation'],transcript_characters=0,
                    board_owned=True,history_requested=False,entry_trace=copy.deepcopy(trace))
        def publish():
            self.latency_metrics = copy.deepcopy(phase)
        publish()
        guard_resources = ExitStack()
        try:
            self._check(job)
            # ASR runs before controller registration so its transcript can be
            # presented. Preempt existing summary work here, off the UI owner; the
            # factory must use jobs.idle to block new leases during capture/ASR.
            self.controller.store.preempt_compaction()
            self._check(job)
            if self.asr is None:
                raise BoardCapabilityNotReady('board_asr')
            stage_started = self.clock()
            phase['asr_calls'] += 1
            try:
                raw = self.asr.transcribe(job.pcm, sample_rate=16000, deadline=job.deadline,
                                          cancelled=job.cancelled.is_set)
            except BoardNoSpeech as exc:
                self._check(job)
                raise self._entry_error() from exc
            _entry_asr_trace(trace,raw)
            self._publish_entry_route_trace(job,trace)
            phase['asr_ms'] = (self.clock()-stage_started)*1000
            phase['asr_completed'] = True
            publish()
            self._check(job)
            stage_started = self.clock()
            text = self._admit_text(job, raw)
            phase['admission_ms'] = (self.clock()-stage_started)*1000
            publish()
            if text is None:
                phase['wake_only'] = True
                self._put(job, dict(wake_detected=True, wake_only=True))
                return
            state = ChannelState(job.meta)
            ordinary_requested = False
            ordinary_guard = None
            def emit(kind, pcm=b'', **fields):
                header = dict(fields, protocol=CHANNEL_PROTOCOL, request_id=job.meta['request_id'],
                              generation=job.meta['generation'], seq=state.seq, kind=kind)
                state.accept(header, pcm)
                self._put(job, dict(channel_event=header, pcm=pcm),admission_guard=ordinary_guard)
                if kind=='audio' and 'first_audio_queued_ms' not in phase:
                    phase['first_audio_queued_ms'] = (self.clock()-job_started)*1000
                    publish()
            if job.entry == 'wake':
                self._put(job, dict(wake_detected=True, wake_only=False))
            emit('start', context=dict(job.meta), sample_rate=24000, channels=1, sample_width=2,
                 thinking_mode='chat')
            emit('transcript', text=text)
            streamed = []
            def reply_sink(chunk, reply, start_sample, token):
                nonlocal ordinary_guard
                if ordinary_requested and ordinary_guard is None:
                    check = getattr(self.controller.store,'check_prepared_turn_current',None)
                    if not callable(check):raise RuntimeError('Prepared-turn streaming guard is unavailable')
                    scoped = getattr(self.controller.store,'prepared_turn_checker',None)
                    if callable(scoped):
                        ordinary_guard = guard_resources.enter_context(scoped(
                            job.meta['request_id'], generation=job.meta['generation']))
                    else:
                        ordinary_guard = lambda:check(job.meta['request_id'],generation=job.meta['generation'])
                self._check(job)
                if chunk.sample_rate != 24000 or start_sample != state.samples:
                    raise ValueError('Local sequence changed the existing playback timeline')
                if not streamed:
                    with self.condition:
                        self._check(job)
                        self._stream_clock = (dict(job.meta), token)
                    self._invalidate_presentation('playback_token_changed', job.meta, token)
                emit('text', text=chunk.text)
                emit('control', emotion=reply.emotion, action=reply.avatar_action,
                     at_sample=start_sample, playback_token=token)
                for offset in range(0, len(chunk.pcm), PACKET_SAMPLES*2):
                    part = chunk.pcm[offset:offset + PACKET_SAMPLES*2]
                    emit('audio', part, start_sample=start_sample + offset//2,
                         sha256=hashlib.sha256(part).hexdigest(), playback_token=token)
                streamed.append((chunk, token))
            stage_started = self.clock()
            plan, history = self._route(job, text, reply_sink=reply_sink)
            phase['route_ms'] = (self.clock()-stage_started)*1000
            phase['ordinary_prepare'] = plan is None
            publish()
            if self.analysis_provider is not None:
                self._check(job)
                stage_started = self.clock()
                self.analysis_provider(text, job=job, is_current=lambda: self._current(job), cancel_event=job.cancelled)
                phase['analysis_enqueue_ms'] = (self.clock()-stage_started)*1000
                publish()
            if plan is None:
                with self.condition:
                    self._check(job)
                    budget = int((job.deadline - self.clock()) * 1000)
                    if budget < 1:
                        raise TimeoutError('Original capture deadline expired before dialogue')
                ordinary_requested = self.audio_converter is None
                # Retire the previous turn's metadata before this invocation. The
                # controller fills this field in its own finally, including failure.
                self.controller.last_prepare_metrics = {}
                try:
                    plan = self.controller.prepare_text(text, scope=job.scope, session_id=job.meta['session_id'],
                        generation=job.meta['generation'], budget_ms=budget, turn_id=job.meta['request_id'],
                        history_query=history, cancel_event=job.cancelled,
                        metadata=dict(source_id=job.context_source_id, evidence='statement') if job.context_source_id else
                                 dict(evidence='statement'),
                        chunk_sink=reply_sink if self.audio_converter is None else None)
                finally:
                    allowed = {'metadata_only','streaming_enabled','context_ms','local_reply_ms','llm_rpc_ms',
                        'llm_calls','tts_rpc_ms','tts_calls','tts_max_rpc_ms','first_tts_ready_ms',
                        'first_chunk_emitted_ms','prepare_total_ms','streamed_chunks','complete',
                        'speaker_first_audio_measured'}
                    metrics = getattr(self.controller, 'last_prepare_metrics', {})
                    phase['prepare'] = {k:v for k,v in metrics.items()
                        if k in allowed and (type(v) is bool or type(v) in (int,float) and math.isfinite(v) and v>=0)}
                    publish()
            self._check(job)
            if (not isinstance(plan, PlaybackPlan) or plan.board_boot_id != self.boot_id
                    or plan.session_id != job.meta['session_id'] or plan.generation != job.meta['generation']
                    or plan.turn_id != job.meta['request_id']):
                raise StaleGeneration('Playback plan belongs to another recording')
            payload = self._stream_payload(plan)
            played_samples = len(payload.pcm) // 2
            played_sha = hashlib.sha256(payload.pcm).hexdigest()
            result = dict(reply_text=plan.reply.text, sample_count=played_samples, pcm_sha256=played_sha,
                          playback_token=plan.playback_token, sample_rate=24000,
                          source_receipt=dict(sample_rate=plan.sample_rate, samples=plan.samples, sha256=plan.sha256),
                          converter_id=payload.converter_id, network_complete=True, playback_verified=False)
            with self.condition:
                self._check(job)
                self._playback = _Playback(dict(job.meta), plan, payload, copy.deepcopy(result))
                self._stream_clock = None
                if not streamed:
                    self._invalidate_presentation('playback_token_changed', job.meta, plan.playback_token)
                self.last_voice_route = dict(generation=job.meta['generation'], transcript_characters=len(raw),
                                             board_owned=True, history_requested=history is not None,
                                             entry_trace=copy.deepcopy(trace))
            if streamed:
                if (tuple(chunk for chunk, _ in streamed) != plan.chunks
                        or any(token != plan.playback_token for _, token in streamed)
                        or state.samples != plan.samples or state.digest.hexdigest() != plan.sha256
                        or state.text != plan.reply.text or payload.converter_id != 'identity-24k'):
                    raise ValueError('Local cue stream does not match its complete playback receipt')
            else:
                emit('text', text=plan.reply.text)
                emit('control', emotion=plan.reply.emotion, action=plan.reply.avatar_action, at_sample=0,
                     playback_token=plan.playback_token)
                for offset in range(0, len(payload.pcm), PACKET_SAMPLES * 2):
                    part = payload.pcm[offset:offset + PACKET_SAMPLES * 2]
                    emit('audio', part, start_sample=offset // 2, sha256=hashlib.sha256(part).hexdigest(),
                         playback_token=plan.playback_token)
            emit('end', sample_count=played_samples, pcm_sha256=played_sha, reply_text=plan.reply.text,
                 playback_token=plan.playback_token)
            self._put(job, dict(network_complete=result),admission_guard=ordinary_guard)
            phase['complete'] = True
            trace['outcome'] = 'complete'

        except Exception as exc:
            trace.update(outcome='rejected' if getattr(exc,'entry_rejected',False) else 'error',
                         error_class=self._diagnostic_error_class(exc))
            phase['entry_rejected'] = bool(getattr(exc,'entry_rejected',False))
            phase['error_class'] = self._diagnostic_error_class(exc)
            raise
        finally:
            try:
                guard_resources.close()
            except Exception as exc:
                phase['complete'] = False
                phase['error_class'] = self._diagnostic_error_class(exc)
                raise
            finally:
                phase['worker_total_ms'] = (self.clock()-job_started)*1000
                self._publish_entry_route_trace(job,trace)
                publish()

    def run_next(self):
        """Process one latest waiting job; suitable for the explicit worker/tests."""
        with self.condition:
            if self.closed or self.waiting is None or self.active is not None:
                return False
            job, self.waiting = self.waiting, None
            self._active_job, self.active = job, job.meta['request_id']
        try:
            self._execute(job)
        except Exception as exc:
            self._queue_cancel(job.meta)
            self._put_error(job, exc)
        finally:
            with self.condition:
                if self._active_job is job:
                    self._active_job = self.active = None
                self.condition.notify_all()
        return True

    def work(self):
        while True:
            with self.condition:
                while not self.closed and (self.waiting is None or self.active is not None):
                    self.condition.wait()
                if self.closed:
                    return
            self.run_next()

    def acknowledge(self, meta, result):
        """Called only by the board player's complete-stream completion hook.

        The current player must have consumed the full 24k payload. We compare
        its carried payload receipt, then forward the original bound native
        receipt to the controller/Store. No Windows `/played` call exists here.
        """
        validate_capture(meta)
        if (not isinstance(result, dict) or type(result.get('sample_count')) is not int
                or not isinstance(result.get('pcm_sha256'), str)
                or not isinstance(result.get('playback_token'), str)):
            raise ValueError('A typed complete playback receipt is required')
        with self.condition:
            media = self._playback
            if (self.closed or media is None or not _same_owner(meta, media.meta)
                    or meta != media.meta or meta['generation'] != self.generation or result != media.result):
                raise StaleGeneration('Playback completion is foreign, partial or stale')
            token = media.plan.playback_token
            if token not in self._ack_queued:
                if not self._queue_action(('ack', media)):
                    raise RuntimeError('Playback receipt queue is unavailable')
                self._ack_queued.add(token)

    def playback_clock(self, meta, *, playback_token, position_seconds):
        """Use only the board sink's position clock, never native 48k counts."""
        with self.condition:
            media = self._playback
            owner = media.meta if media is not None else self._stream_clock[0] if self._stream_clock is not None else None
            token = media.plan.playback_token if media is not None else self._stream_clock[1] if self._stream_clock is not None else None
            if (owner is None or not _same_owner(meta, owner)
                    or meta['generation'] != self.generation or playback_token != token):
                raise StaleGeneration('Clock belongs to another playback owner')
            if (type(position_seconds) not in (int, float) or not math.isfinite(position_seconds)
                    or not 0 <= position_seconds <= 35):
                raise ValueError('Expected the board player position in seconds')
            return dict(board_boot_id=self.boot_id, session_id=meta['session_id'],
                        request_id=meta['request_id'], generation=meta['generation'],
                        playback_token=playback_token, audio_seconds=float(position_seconds),
                        audio_sample=round(position_seconds * 24000))

    def _perform_action(self, action):
        kind, value = action
        if kind == 'cancel':
            session_id, generation = value
            try:
                self.controller.cancel(session_id, generation=generation)
            except Exception:
                self.cleanup_error = 'board_cancel_failed'
            finally:
                with self.condition:
                    self._cancel_queued.discard(value)
        elif kind == 'ack':
            media = value
            try:
                with self.condition:
                    current = (not self.closed and self._playback is media
                               and media.meta['generation'] == self.generation)
                if not current:
                    return
                self.controller.acknowledge(media.plan, playback_token=media.plan.playback_token,
                    sha256=media.plan.sha256, samples=media.plan.samples, complete=True)
                with self.condition:
                    if self._playback is media:
                        self._playback = None
                        self.last_ack = dict(request_id=media.meta['request_id'], committed=True,
                                             playback_token=media.plan.playback_token)
            except Exception as exc:
                self.last_ack = dict(request_id=media.meta['request_id'], committed=False,
                                     error=type(exc).__name__)
            finally:
                with self.condition:
                    self._ack_queued.discard(media.plan.playback_token)
        elif kind == 'release_profile':
            try:
                self.profile_release(value)
            except Exception:
                self.cleanup_error = 'board_profile_release_failed'

    def drain_actions(self):
        """Explicit deterministic action draining when no action thread is used."""
        while True:
            try:
                action = self._actions.get_nowait()
            except queue.Empty:
                return
            try:
                self._perform_action(action)
            finally:
                self._actions.task_done()

    def _action_worker(self):
        while True:
            try:
                action = self._actions.get(timeout=.1)
            except queue.Empty:
                if self.closed:
                    return
                continue
            try:
                self._perform_action(action)
            finally:
                self._actions.task_done()
                action = None  # Retire consumed plan/PCM, keep ACK ordering.

    def reset_enrollment(self):
        handler = self.special_handlers.get('identity_enrollment')
        reset = getattr(handler, 'reset', None)
        if reset is not None:
            reset()

    def _enrollment_state(self):
        handler = self.special_handlers.get('identity_enrollment')
        public = getattr(handler, 'public', None)
        if public is None:
            return dict(active=False, available=handler is not None)
        value = public()
        if not isinstance(value, dict) or type(value.get('active')) is not bool:
            raise ValueError('Invalid board enrollment handler state')
        return dict(value, available=True)

    def prepare_feedback(self, config=None):
        if self.feedback_provider is None:
            self.feedback_error = 'board_feedback_not_configured'
            return False
        assets = self.feedback_provider()
        if not isinstance(assets, dict) or set(assets) - {'thinking', 'arrival', 'invitation'}:
            raise ValueError('Invalid board-owned cue assets')
        self.feedback_assets = {k: v for k, v in assets.items() if k == 'thinking'}
        self.social_assets = {k: v for k, v in assets.items() if k != 'thinking'}
        self.feedback_error = ''
        return bool(self.feedback_assets)

    def refresh_feedback(self):
        # Local approved assets only. Never fetch old Windows feedback routes.
        with self.condition:
            if self.closed or self.clock() < self.next_feedback_refresh:
                return
            self.next_feedback_refresh = self.clock() + 5
        self.prepare_feedback()

    def interruption_transport(self, config, meta, pcm, timeout):
        """Optional injection into the existing InterruptionVerifier transport.

        Merely supplying this callable does not validate barge-in echo/reference
        ownership or open capture; the GUI factory must inject its board path.
        """
        validate_capture(meta, pcm)
        if self.asr is None:
            raise BoardCapabilityNotReady('board_asr')
        started = self.clock()
        text = self.asr.transcribe(pcm, sample_rate=16000, deadline=started + timeout,
                                  cancelled=lambda: self.closed)
        model = getattr(self.asr, 'model_sha256', 'board-asr')
        return dict(context=dict(meta), source_kind='actual', text=text,
                    model_id='paraformer-' + model[:24], recognition_ms=(self.clock() - started) * 1000)

    def public(self):
        with self.condition:
            available = sorted(self.special_handlers)
            return dict(enabled=self.enabled(), pending=bool(self.waiting or self.active or self._playback),
                conversation=True, streaming=True, board_owned=True, drop_in_complete=False,
                host=self.config['host'], port=self.config['port'], feedback_ready=bool(self.feedback_assets),
                feedback_error=self.feedback_error, persistent_conversation=self.conversation_selection is not None,
                profile_memory=dict(mode='personal' if self.profile_selection else 'guest'),
                voice_enrollment=self._enrollment_state(),
                last_playback_ack=copy.deepcopy(self.last_ack), last_voice_route=copy.deepcopy(self.last_voice_route),
                cleanup_error=self.cleanup_error, latency=copy.deepcopy(self.latency_metrics),
                diagnostics=dict(self.progress_diagnostics),
                capabilities=dict(ordinary_dialogue=self.asr is not None,
                    explicit_memory=self.controller.command_handler is not None,
                    history_routing=self.wall_clock is not None or self.history_router is not None,
                    wake_entry=True, visual_entry=self.visual_entry_handler is not None,
                    profile_selection=self.profile_resolver is not None and self.profile_release is not None,
                    native_rate_bridge=self.audio_converter is not None,
                    available_special_handlers=available,
                    model_input_policy='injected_context_builder' if self.controller.context_builder else 'not_configured',
                    pending=['board_calibrated_speaker_attribution', 'barge_capture_factory_injection',
                             'incremental_llm_tts_overlap',
                             'full_identity_workflow_integration']))

    def close(self):
        with self.condition:
            if self.closed:
                return
            previous, self.profile_selection = self.profile_selection, None
            self._invalidate()
            if previous is not None and self.profile_release is not None:
                self._queue_action(('release_profile', previous))
            self.closed = True
            self.condition.notify_all()
        if self.action_thread is None:
            self.drain_actions()
        for thread in (self.thread, self.action_thread):
            if thread is not None and thread is not threading.current_thread():
                thread.join(timeout=.1)
