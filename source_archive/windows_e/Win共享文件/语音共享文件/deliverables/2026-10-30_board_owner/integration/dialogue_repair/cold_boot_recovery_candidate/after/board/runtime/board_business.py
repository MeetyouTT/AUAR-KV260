"""Explicit assembly of board-owned dialogue, memory and local control.

Importing this module starts no device, network, model or task. The assembly is
an opt-in candidate: the Store's synthetic-data gate remains in force. Existing
GTK/recording/player owners are supplied, rather than copied or replaced here.
"""
from dataclasses import dataclass
from pathlib import Path
import copy
import json
import os
import re
import stat
import threading
import time
import uuid

from board.runtime.audio.board_dialogue_jobs import BoardDialogueJobs, BoardCapabilityNotReady
from board.runtime.board_dialogue import BoardDialogueController, BoardReply, StaleGeneration, DIALOGUE_ROUTE
from board.runtime.board_dialogue_client import InferenceHttpClient, ModelRequestError
from board.runtime.board_memory_policy import BoardContextBuilder, BoardMemoryCommands, BoardSummaryClient
from common.board_memory import BoardMemoryStore, BoardMemoryWorker
from common.board_memory_backoff import BoardMemoryBackoffWorker
from common.board_timeline_clock import StableTimelineClock, ClockUnavailable
from common.profile_access import ProfileAccess, identifier
from common.profile_selection import selection


@dataclass(frozen=True)
class BoardBusinessConfig:
    private_root: str
    utc_bounds: tuple
    model_host: str = '192.168.50.1'
    model_port: int = 8797
    timeout_ms: int = 120000
    timezone: str = 'America/Los_Angeles'
    entry_mode: str = 'voice_first'
    data_origin: str = 'synthetic'
    visual_device_id: object = None
    bootstrap_receipt: object = None
    bootstrap_receipt_sha256: object = None
    retention_enabled: bool = False

    def __post_init__(self):
        if type(self.retention_enabled) is not bool:
            raise ValueError('Retention requires an explicit configuration boolean')
        if self.data_origin == 'board' and (not isinstance(self.bootstrap_receipt, str)
                or not Path(self.bootstrap_receipt).is_absolute()
                or not isinstance(self.bootstrap_receipt_sha256, str)
                or re.fullmatch(r'[0-9a-f]{64}', self.bootstrap_receipt_sha256) is None):
            raise ValueError('Production requires its committed private migration receipt')
        if self.data_origin not in ('synthetic', 'board'):
            raise ValueError('Choose a distinct synthetic candidate or board-owned store')
        if not Path(self.private_root).is_absolute():
            raise ValueError('An absolute board-private candidate root is required')
        if self.model_host != '192.168.50.1' or type(self.model_port) is not int or not 1024 <= self.model_port <= 65535:
            raise ValueError('Use the pinned Ethernet model-only endpoint')
        if self.entry_mode not in ('voice_first', 'visual'):
            raise ValueError('Choose the explicit board entry policy')
        if type(self.timeout_ms) is not int or not 1000 <= self.timeout_ms <= 120000:
            raise ValueError('Invalid original turn deadline')
        if not isinstance(self.utc_bounds, (tuple, list)) or len(self.utc_bounds) != 2:
            raise ValueError('Explicit trusted UTC bounds are required')
        if self.visual_device_id is not None and (not isinstance(self.visual_device_id, str)
                or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,160}', self.visual_device_id)):
            raise ValueError('Invalid explicit visual device scope')


class LocalProfileSelections:
    """Use the existing ProfileAccess on the board, with no Windows endpoint.

    Local operator control calls issue() after authentication. The existing GTK
    selection file may carry its returned token; loading the file never selects
    a profile. resolve() checks the live, same-process grant when the user clicks.
    A name, face match or speaker candidate is never accepted as a grant.
    """
    def __init__(self, access, boot_id, require_profile, *, wall_clock):
        if not isinstance(access, ProfileAccess) or not callable(require_profile):
            raise TypeError('Board ProfileAccess and local profile catalogue are required')
        self.access, self.boot_id, self.require_profile = access, boot_id, require_profile
        self.wall_clock = wall_clock
        self.lock = threading.RLock()
        self.issued = {}

    def issue(self, profile_id, operator_key, *, ttl=900, profile_name='个人档案'):
        self.access.authenticate(operator_key)
        identifier(profile_id)
        self.require_profile(profile_id)
        if not isinstance(profile_name, str) or not 1 <= len(profile_name) <= 40 or any(ord(c) < 32 for c in profile_name):
            raise ValueError('Invalid profile display name')
        now = self.wall_clock()  # Check clock before issuing a capability.
        meta = dict(board_boot_id=self.boot_id, session_id=uuid.uuid4().hex)
        token, grant = self.access.issue(profile_id, meta, ttl=ttl)
        with self.lock:
            active = tuple(self.access.grants.values())
            self.issued = {old: record for old, record in self.issued.items()
                           if any(value is record[0] for value in active)}
            self.issued[token] = (grant, meta)
        return dict(mode='profile', **meta, profile_id=profile_id, profile_name=profile_name,
                    conversation_id=uuid.uuid4().hex, access_token=token,
                    expires_in_seconds=ttl, expires_unix=now + ttl)

    def resolve(self, value, boot_id):
        if boot_id != self.boot_id:
            raise PermissionError('Profile request belongs to another board boot')
        value = selection(value, self.boot_id)
        self.require_profile(value['profile_id'])
        grant = self.access.resolve(value['access_token'], value)
        if grant.profile_id != value['profile_id']:
            raise PermissionError('Profile token belongs to another profile')
        return dict(scope=dict(kind='profile', id=grant.profile_id, grant=grant),
                    session_id=value['session_id'], conversation_id=value['conversation_id'])

    def release(self, selected):
        grant = selected.get('scope', {}).get('grant')
        if grant is None:
            raise PermissionError('No original board profile grant')
        if grant.actor != (self.boot_id, selected['session_id']):
            raise PermissionError('Profile release belongs to another board interaction')
        with self.access.lock:
            # Releasing an obsolete selection must not revoke another grant.
            if any(value is grant for value in self.access.grants.values()):
                self.access.revoke(dict(board_boot_id=self.boot_id, session_id=selected['session_id']))
        with self.lock:
            self.issued = {key: value for key, value in self.issued.items() if value[0] is not grant}

    def close(self):
        with self.lock:
            issued, self.issued = tuple(self.issued.values()), {}
        with self.access.lock:
            for grant, meta in issued:
                if any(value is grant for value in self.access.grants.values()):
                    self.access.revoke(meta)


class LocalIdentityReplies:
    """Existing board face FSM, with its original consent/target checks.

    Private snapshots and enrollment commands remain local. Each stage uses the
    same ongoing channel and player; success is rendered only after the original
    flow has verified its commit receipt. No second microphone/player is opened.
    """
    streaming_reply = True
    def __init__(self, boot_id, snapshot, command, *, clock=time.monotonic, now_ms=None,
                 enrollment_factory=None):
        from board.identity.voice_enrollment import VoiceEnrollment
        from board.interaction.ui_contract import millis
        self.snapshot, self.clock = snapshot, clock
        self.original_command = command
        self.business = self.bridge = None
        self.flow = (enrollment_factory or VoiceEnrollment)(boot_id, snapshot, command,
            simple=True, clock=clock, now_ms=now_ms or millis)

    def attach_speaker_business(self, business, readback=None):
        if self.flow.public()['active']:
            raise RuntimeError('Attach board speaker business before starting a face workflow')
        from board.runtime.audio.face_binding_bridge import FaceBindingBridge
        self.business = business
        self.bridge = FaceBindingBridge(self.snapshot, self.original_command, readback,
                                        clock=lambda: round(self.clock()*1000))
        self.flow.snapshot, self.flow.command = self.bridge.snapshot, self.bridge.command

    def reset(self):
        self.flow.reset()
        if self.business is not None:
            self.business.reset()

    def public(self):
        state = self.flow.public()
        if self.business is not None:
            state = dict(state, active=state['active'] or self.business.public()['active'],
                         speaker=self.business.public())
        return state

    def _visual(self, job):
        from common.speaker_visual import build_visual, unavailable
        try:
            return build_visual(job.capture_snapshot, self.snapshot(), job.meta, round(self.clock()*1000))
        except (OSError, ValueError, KeyError, TypeError):
            return unavailable(job.meta, 'VISUAL_PROVIDER_UNAVAILABLE')

    def _gallery(self, job):
        if self.bridge is None or self.bridge.readback is None:
            return None
        try:
            return self.bridge.readback.read(job.meta, self.snapshot())
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def __call__(self, text, *, job, controller, is_current, cancel_event, reply_sink=None):
        from common.binding_intent import binding_intent, face_enrollment_text
        from common.voice_enrollment import render, result
        def current():
            if not is_current() or cancel_event.is_set() or self.clock() >= job.deadline:
                return False
            check = getattr(controller.store, 'check_turn_current', None)
            if check is not None:
                try:
                    check(job.meta['request_id'], generation=job.meta['generation'])
                except Exception:
                    return False
            return True
        def initial(interpreted=None):
            if not current():
                raise StaleGeneration('Identity turn is no longer current')
            intent = binding_intent(text)
            if intent['kind'] == 'invalid_name':
                value = result('bad_name')
            else:
                interpreted = interpreted or face_enrollment_text(text, active=self.flow.public()['active'])
                value = self.flow.handle(interpreted, copy.deepcopy(job.capture_snapshot),
                                         is_current=current)
                if value is None:
                    raise BoardCapabilityNotReady('identity_intent')
            return value
        budget = int((job.deadline - self.clock()) * 1000)
        if budget < 1:
            raise TimeoutError('Original capture deadline expired before local identity')
        kwargs = dict(scope=job.scope, session_id=job.meta['session_id'], generation=job.meta['generation'],
            budget_ms=budget, turn_id=job.meta['request_id'], cancel_event=cancel_event,
            metadata=dict(source_id=job.context_source_id, evidence='statement') if job.context_source_id else
                     dict(evidence='statement'))
        if reply_sink is None:
            raise BoardCapabilityNotReady('owned_identity_cue_stream')
        def produce(emit):
            from contextlib import nullcontext
            from common.binding_api import response as binding_response
            from common.voice_enrollment import enrollment_requested, identity_query_requested
            exchange = None
            board_text = None
            try:
                if self.business is not None:
                    options = dict(is_current=current, cancel_event=cancel_event, deadline=job.deadline)
                    from common.feature_intents import speaker_query_requested
                    if speaker_query_requested(text):
                        # Skip the unified enrollment router: a status question
                        # must not become one of its three captured samples.
                        spoken=self.business.turn(job.meta,text,job.pcm,**options)
                        if spoken is None:
                            raise BoardCapabilityNotReady('speaker_status_result')
                        emit(BoardReply(spoken,'friendly'),final_cue=True)
                        return
                    routed = (self.business.route(job.meta, text, job.pcm,
                                visual=self._visual(job), gallery_packet=self._gallery(job), **options)
                              if self.business.config['enabled'] else None)
                    decision = binding_response(routed, job.meta)['decision'] if routed is not None else None
                    route = decision['route'] if decision is not None else 'ordinary'
                    if route == 'device_reply':
                        emit(BoardReply(decision['reply'], 'friendly'), final_cue=True)
                        return
                    if route == 'ordinary_skip_speaker':
                        return DIALOGUE_ROUTE
                    if route == 'face_exchange':
                        exchange = self.business.begin_face_exchange(job.meta, job.pcm, routed, self.bridge,
                                    job.capture_snapshot, text, **options)
                        board_text = routed['binding_request']['board_text']
                    else:
                        spoken = self.business.turn(job.meta, text, job.pcm, **options)
                        if spoken is not None:
                            emit(BoardReply(spoken, 'friendly'), final_cue=True)
                            return
                        if (not self.flow.public()['active'] and not enrollment_requested(text)
                                and not identity_query_requested(text)):
                            # A bare self-name statement is ordinary dialogue,
                            # not consent to start an identity enrollment.
                            return DIALOGUE_ROUTE
                with exchange.scope() if exchange is not None else nullcontext():
                    value = initial(board_text)
                    guiding = value['code'] in ('sample_front', 'sample_auto')
                    def deliver(value, final):
                        if not current():
                            raise StaleGeneration('Sampling guide no longer owns this turn')
                        spoken = exchange.transform(value, final=final) if exchange is not None else render(value)
                        emit(BoardReply(spoken, 'friendly'), final_cue=final)
                    deliver(value, not guiding)
                    if guiding:
                        self.flow.guide(deliver, is_current=current)
            finally:
                if exchange is not None:
                    exchange.cancel()
        return controller.prepare_local_sequence(text, produce, reply_sink, **kwargs)


def board_entry_policy(mode, boot_id, snapshot, *, now_ms):
    """The historical 'visual' flag is also used by voice-first barge capture."""
    if mode == 'voice_first':
        # BoardDialogueJobs already validated current audio owner, PCM and ASR.
        # This path must not start requiring a face after wake-word acceptance.
        return lambda meta, captured, text, *, is_current: (
            meta.get('board_boot_id') == boot_id and is_current())
    if mode != 'visual' or not callable(snapshot):
        raise ValueError('A local visual provider is required for visual entry')
    def admit(meta, captured, text, *, is_current):
        from board.runtime.audio.attention_gate import read_attention
        if not is_current() or not isinstance(captured, dict):
            return False
        now = now_ms()
        stamp = captured.get('observed_mono_ms')
        if type(stamp) is not int or not 0 <= now - stamp <= 120000:
            return False
        before, _ = read_attention(captured, boot_id, stamp)
        current, _ = read_attention(snapshot(), boot_id, now)
        return bool(before and current and before['key'] == current['key'] and is_current())
    return admit


class _BoardWriterLock:
    """Kernel-held POSIX lifetime lock in the actual board-private directory."""
    def __init__(self, root, boot_id):
        if os.name != 'posix':
            raise RuntimeError('Real board storage requires the POSIX board runtime')
        import fcntl
        self.fd = None
        root = Path(root).absolute()
        if root.resolve() != root or any(part.casefold() == 'win共享文件' for part in root.parts):
            raise ValueError('Board memory cannot be stored through a shared/symlink directory')
        if not root.is_dir():
            raise ValueError('Migrate the private production directory before opening its writer')
        info = root.stat()
        if info.st_uid != os.getuid() or info.st_mode & 0o077 or not stat.S_ISDIR(info.st_mode):
            raise PermissionError('Board memory directory must be owned by this user and private')
        path = root/'writer.lock'
        fd = os.open(str(path), os.O_RDWR | os.O_CREAT | getattr(os, 'O_NOFOLLOW', 0), 0o600)
        try:
            info = os.fstat(fd)
            if info.st_uid != os.getuid() or info.st_mode & 0o077 or not stat.S_ISREG(info.st_mode):
                raise PermissionError('Invalid board writer lock')
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            os.ftruncate(fd, 0)
            os.write(fd, json.dumps(dict(pid=os.getpid(), boot_id=boot_id)).encode())
            os.fsync(fd)
            self.fd = fd
            self.root = root
        except BaseException:
            os.close(fd)
            raise

    def close(self):
        if self.fd is not None:
            import fcntl
            fd, self.fd = self.fd, None
            try:
                fcntl.flock(fd, fcntl.LOCK_UN)
            finally:
                os.close(fd)


def create_board_business_runtime(config, boot_id, **kwargs):
    """Acquire the production single writer before constructing/opening Store."""
    proof = None
    if config.data_origin == 'board':
        from common.board_production_bootstrap import (
            verify_production_bootstrap, verify_production_bootstrap_receipt)
        verify_production_bootstrap_receipt(config.private_root, config.bootstrap_receipt, config.bootstrap_receipt_sha256)
    lease = _BoardWriterLock(config.private_root, boot_id) if config.data_origin == 'board' else None
    try:
        if config.data_origin == 'board':
            from board.runtime.board_speaker_business import _WriterLease
            speaker_lease = _WriterLease(Path(config.private_root)/'speaker', data_origin='board')
            try:
                proof = verify_production_bootstrap(config.private_root, config.bootstrap_receipt,
                    config.bootstrap_receipt_sha256, recovery_leases=(lease, speaker_lease))
            finally:
                speaker_lease.close()
        return BoardBusinessRuntime(config, boot_id, writer_lock=lease, bootstrap_proof=proof, **kwargs)
    except BaseException:
        if lease is not None:
            lease.close()
        raise


class BoardBusinessRuntime:
    def __init__(self, config, boot_id, *, asr, system_prompt, conversation_selection,
                 identity_snapshot=None, identity_command=None, profile_access=None,
                 require_profile=None, feedback_provider=None, playback_invalidator=None,
                 capture_idle=None, extra_handlers=None, clock=time.monotonic,
                 client=None, timeline=None, store=None, worker_factory=BoardMemoryBackoffWorker, writer_lock=None, bootstrap_proof=None):
        self.config, self.boot_id, self.clock = config, boot_id, clock
        if config.data_origin == 'board' and (not isinstance(writer_lock, _BoardWriterLock)
                or writer_lock.fd is None or writer_lock.root != Path(config.private_root).absolute()):
            raise RuntimeError('Use create_board_business_runtime for the exclusive board writer')
        if config.data_origin == 'board' and (not isinstance(bootstrap_proof, dict)
                or bootstrap_proof.get('receipt_verified') is not True
                or bootstrap_proof.get('data_origin') != 'board'
                or bootstrap_proof.get('profiles_migration_verified') is not True):
            raise RuntimeError('The production factory requires verified committed migration provenance')
        self.bootstrap_proof = dict(bootstrap_proof or {})
        self.initial_selection = dict(mode='explicit_selection_required', session_is_fresh=True)
        self.writer_lock = writer_lock
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,96}', boot_id):
            raise ValueError('Invalid fresh board boot ID')
        self.client = client or InferenceHttpClient(config.model_host, config.model_port, clock=clock)
        if (self.client.host, self.client.port) != (config.model_host, config.model_port):
            raise ValueError('Model transport differs from configured pinned endpoint')
        root = Path(config.private_root)
        # One path per boot. A board restart cannot reload a former boot anchor.
        self.timeline = timeline or StableTimelineClock(boot_id, self.client.health_date_source_id(),
            self.client.validate_sample, utc_bounds=config.utc_bounds,
            anchor_path=root/'timeline'/('anchor-' + boot_id + '.json'), monotonic=clock)
        if self.timeline.boot_id != boot_id:
            raise ValueError('Timeline belongs to another board boot')
        self.access = profile_access or ProfileAccess(clock=clock)
        self.store = store or BoardMemoryStore(root/'timeline.sqlite3', clock=self.timeline.event_time,
                    profile_access=self.access, data_origin=config.data_origin)
        if self.store.clock != self.timeline.event_time or self.store.profile_access is not self.access:
            raise ValueError('Store must share the exact board clock and ProfileAccess')
        require_profile = require_profile or getattr(self.store, 'require_profile', None)
        self.profiles = (LocalProfileSelections(self.access, boot_id, require_profile,
                        wall_clock=self.timeline.event_time) if require_profile is not None else None)
        builder = BoardContextBuilder(system_prompt)
        capacity = min(768, builder.continuity_capacity())
        if capacity < 64:
            raise ValueError('The current persona leaves no stable continuity-summary capacity')
        self.controller = BoardDialogueController(self.store, self.client, board_boot_id=boot_id,
            system_prompt=system_prompt, asr=asr, clock=clock,
            context_builder=builder, command_handler=BoardMemoryCommands(self.store))
        handlers = dict(extra_handlers or {})
        self.identity_handler = None
        if identity_snapshot is not None and identity_command is not None:
            identity = LocalIdentityReplies(boot_id, identity_snapshot, identity_command, clock=clock,
                                            now_ms=lambda: round(clock()*1000))
            self.identity_handler = identity
            if {'identity_enrollment', 'identity_query'} & set(handlers):
                raise ValueError('One board identity handler owns the original face FSM')
            handlers.update(identity_enrollment=identity, identity_query=identity)
        self.jobs = BoardDialogueJobs(self.controller,
            dict(enabled=True, host=config.model_host, port=config.model_port, timeout_ms=config.timeout_ms),
            boot_id, asr=asr, conversation_selection=conversation_selection,
            profile_resolver=self.profiles.resolve if self.profiles else None,
            profile_release=self.profiles.release if self.profiles else None,
            visual_entry_handler=board_entry_policy(config.entry_mode, boot_id, identity_snapshot,
                                                    now_ms=lambda: round(clock()*1000)),
            special_handlers=handlers, feedback_provider=feedback_provider,
            playback_invalidator=playback_invalidator, clock=clock,
            wall_clock=self.timeline.event_time, timezone=config.timezone, start_worker=False)
        self.jobs.identity_snapshot = identity_snapshot
        self.capture_idle = capture_idle
        self.speaker_business = None
        self.speaker_analysis_error = ''
        self._clock_refresh_lock = threading.Lock()
        self._clock_refresh_next = clock() + 600.
        self._clock_refresh_failures = 0
        self.clock_refresh_error = ''
        self.summary = BoardSummaryClient(self.client, board_boot_id=boot_id, clock=clock,
                                         final_summary_max_utf8_bytes=capacity)
        self.memory_worker = worker_factory(self.store, self.summary, idle=self.idle,
            compaction_guard_factory=self.timeline.compaction_guard, before_step=self._memory_before_step)
        self.visual_memory = None
        self.visual_policy = None
        if config.visual_device_id is not None:
            from board.runtime.visual_memory import VisualTimelineWorker
            self.visual_memory = VisualTimelineWorker(boot_id, self.store, self.timeline,
                                device_id=config.visual_device_id, monotonic=clock)
            from board.runtime.visual_policy import LocalVisualQueries
            visual_policy = LocalVisualQueries(self.store, self.visual_memory, self.timeline, zone=config.timezone)
            self.visual_policy = visual_policy
            self.jobs.special_handlers['structured_visual_query'] = visual_policy
            self.jobs.visual_intent_matcher = visual_policy.requested
        self.started = False
        self.closed = False
        self.close_complete = False

    def attach_speaker_business(self, business, *, face_readback=None):
        """Attach the one board CPU/three-store owner before starting UI jobs."""
        if self.started or self.closed or self.speaker_business is not None:
            raise RuntimeError('Attach speaker business once before startup')
        if (business.boot != self.boot_id or business.clock is not self.clock
                or business.wall_clock != self.timeline.event_time or business.data_origin != self.config.data_origin):
            raise ValueError('Speaker business must share the exact board boot, clock and data origin')
        if self.identity_handler is None:
            raise BoardCapabilityNotReady('board_identity_provider')
        self.identity_handler.attach_speaker_business(business, face_readback)
        self.speaker_business = business
        self.jobs.special_handlers['speaker_identity'] = self.identity_handler
        self.jobs.analysis_provider = self._submit_speaker_analysis

    def _submit_speaker_analysis(self, text, *, job, is_current, cancel_event):
        source = job.context_source_id
        if self.speaker_business is None or not isinstance(source, str) or not source.startswith('conversation:'):
            return None
        cid = source[len('conversation:'):]
        if not re.fullmatch(r'[0-9a-f]{32}', cid):
            return None
        def evidence(value):
            if not is_current() or cancel_event.is_set() or value.get('status') != 'COMPLETE':
                return
            # Candidate IDs/vectors remain in the private speaker stores/RAM.
            # The shared timeline carries only the fact that this capture has
            # descriptive evidence, without inventing a confirmed speaker.
            self.store.append_event(job.scope, 'speaker:' + job.meta['request_id'], 'device_event',
                '本轮语音已形成归属线索，说话者身份仍未确认。', topic='语音归属',
                metadata=dict(source_id=source, evidence='device_confirmed', speaker_known=False,
                              claims=[dict(field='attribution', value='unconfirmed')]))
        try:
            result = self.speaker_business.submit_analysis(job.meta, job.pcm, cid,
                visual=self.identity_handler._visual(job), is_current=is_current,
                cancel_event=cancel_event, deadline=job.deadline, on_evidence=evidence)
            self.speaker_analysis_error = ''
            return result
        except (OSError, ValueError, RuntimeError) as exc:
            self.speaker_analysis_error = type(exc).__name__
            return None

    def initialize_clock(self, *, timeout=3., cancelled=lambda: False):
        if type(timeout) not in (int, float) or not 0 < timeout <= 10:
            raise ValueError('Use a bounded explicit Date sample')
        result = self.client.sample_health_date(self.timeline, deadline=self.clock() + timeout, cancelled=cancelled)
        self._clock_refresh_next = self.clock() + 600.
        self._clock_refresh_failures = 0
        self.clock_refresh_error = ''
        return result

    def _foreground_idle(self):
        return bool(not self.closed and callable(self.capture_idle) and self.capture_idle()
                    and self.jobs.idle and self.controller.idle
                    and (self.speaker_business is None or not self.speaker_business.health()['queued_or_active']))

    def _memory_before_step(self, cancelled):
        """Use the existing idle worker, outside every SQL/clock quality lease."""
        if cancelled() or not self._foreground_idle():
            return False
        if self.clock() < self._clock_refresh_next:
            return None
        if not self._clock_refresh_lock.acquire(blocking=False):
            return False
        try:
            self.client.sample_health_date(self.timeline, deadline=self.clock() + 1.,
                cancelled=lambda: cancelled() or not self._foreground_idle())
            self._clock_refresh_next = self.clock() + 600.
            self._clock_refresh_failures = 0
            self.clock_refresh_error = ''
            return True
        except (ModelRequestError, ClockUnavailable, OSError, ValueError) as exc:
            self._clock_refresh_failures += 1
            self._clock_refresh_next = self.clock() + min(60., 3.*2**min(self._clock_refresh_failures-1, 5))
            self.clock_refresh_error = type(exc).__name__
            return False
        finally:
            self._clock_refresh_lock.release()

    def idle(self):
        # Missing capture ownership must never permit destructive compaction.
        return self._foreground_idle() and self.timeline.safe_for_compaction()

    def start(self):
        if self.closed:
            raise RuntimeError('Board runtime is closed')
        self.timeline.event_time()  # No wall-clock fallback on first startup.
        if self.config.data_origin == 'board' and self.speaker_business is None:
            raise BoardCapabilityNotReady('board_speaker_business')
        if not self.started:
            self.jobs.start()
            if self.config.retention_enabled:
                self.memory_worker.start()
            if self.visual_memory is not None:
                self.visual_memory.start()
            self.started = True

    def make_barge_capture_factory(self, output, spoken_text, frontend_factory, *, capture_type=None,
                                  verifier_type=None):
        """Inject the existing echo/reference capture, using board ASR only."""
        def create():
            from board.runtime.audio.barge_verify import InterruptionVerifier
            from board.runtime.audio.board_capture import BoardBargeCapture
            verifier = (verifier_type or InterruptionVerifier)(lambda: dict(self.jobs.config), self.boot_id,
                transport=self.jobs.interruption_transport, clock=self.clock)
            try:
                return (capture_type or BoardBargeCapture)(output, frontend_factory=frontend_factory,
                                verifier=verifier, spoken_text=spoken_text)
            except Exception:
                verifier.close()
                raise
        return create

    def close(self):
        if self.close_complete:
            return
        self.closed = True
        visual_stopped = self.visual_memory.close() if self.visual_memory is not None else True
        self.jobs.close()
        self.memory_worker.close()
        speaker_stopped = self.speaker_business.close() if self.speaker_business is not None else True
        if self.profiles is not None:
            self.profiles.close()
        if self.writer_lock is not None:
            threads = (self.memory_worker.thread, self.jobs.thread, self.jobs.action_thread)
            if not visual_stopped or not speaker_stopped or any(thread is not None and thread.is_alive() for thread in threads):
                # Keep the kernel lock while an old worker could still touch
                # SQLite. The process exiting releases it automatically.
                raise RuntimeError('Board workers are still finishing; writer lock retained')
            self.writer_lock.close()
        if not visual_stopped:
            raise RuntimeError('Board visual worker is still finishing')
        if not speaker_stopped:
            raise RuntimeError('Board speaker worker is still finishing')
        self.close_complete = True

    def public(self):
        production = self.config.data_origin == 'board'
        held = self.writer_lock is not None and self.writer_lock.fd is not None
        proof = self.bootstrap_proof
        memory_thread = getattr(self.memory_worker, 'thread', None)
        return dict(mode='board-business-' + self.config.data_origin, data_origin=self.config.data_origin,
                    production_cutover=bool(production and self.started and held),
                    writer=dict(kind='board-local-single-writer', held=held, boot_id=self.boot_id),
                    receipt=dict(verified=bool(production and proof.get('receipt_verified') is True), data_origin=proof.get('data_origin'),
                        bundle_id=proof.get('bundle_id'), profiles_migration_verified=proof.get('profiles_migration_verified',False),
                        profiles_imported=proof.get('profiles_imported',0)),
                    retention=dict(enabled=self.config.retention_enabled,
                        running=bool(memory_thread and memory_thread.is_alive()),
                        initial_retention_enabled=proof.get('initial_retention_enabled',False)),
                    conversation_selection=dict(self.initial_selection),
                    started=self.started, closed=self.closed, clock=self.timeline.quality_snapshot(),
                    dialogue=self.jobs.public(), memory=self.memory_worker.health(),
                    close_complete=self.close_complete,
                    visual_timeline=self.visual_memory.public() if self.visual_memory is not None else dict(enabled=False),
                    visual_queries=self.visual_policy.public() if self.visual_policy is not None else dict(enabled=False),
                    speaker=self.speaker_business.health() if self.speaker_business is not None else dict(ready=False),
                    speaker_analysis_error=self.speaker_analysis_error,
                    clock_refresh=dict(error=self.clock_refresh_error,
                                       retry_in_seconds=max(0., self._clock_refresh_next-self.clock())))
