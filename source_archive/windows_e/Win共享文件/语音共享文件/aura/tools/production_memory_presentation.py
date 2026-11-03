"""Production-only, instance-bound presentation lifetime and private diagnostics.

No Store queries, audio control, files containing speech, or device imports.
Bind before the render owner starts. Only that owner retires consumed buffers.
"""
import json
import math
import os
from pathlib import Path
import stat
import threading
import time


_BODY_KEYS = frozenset(('text', 'reply', 'reply_text', 'transcript', 'turns', 'log',
                        'voice_reply', 'messages', 'prompt', 'content', 'body'))
_HISTORY_KEYS = frozenset(('turns', 'log', 'messages'))


def _clean(value):
    """Copy public metadata without reusing arbitrary body/error containers."""
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if key in _BODY_KEYS:
                result[key] = [] if key in _HISTORY_KEYS else None if key == 'voice_reply' else ''
            elif key in ('error', 'detail'):
                result[key] = 'operation_failed' if item else ''
            else:
                result[key] = _clean(item)
        return result
    if isinstance(value, (list, tuple)):
        return [_clean(item) for item in value]
    return value


def _owner(value):
    return tuple(value.get(k) for k in ('board_boot_id', 'session_id', 'generation', 'request_id'))


class PresentationLifecycle:
    """One current RAM display slot; repaint never renews its hard deadline.

    Lock ordering is presentation -> bridge. Never acquire the render-worker
    condition here: its existing writer calls recording.public under that
    condition. The audio owner
    calls business idle gates before acquiring this lock. Store postcommit
    hooks never acquire a Store, job, clock-quality, or audio lock.
    """
    def __init__(self, stage, recording, *, clock=time.monotonic, ttl=300.):
        if not 0 < ttl <= 300:
            raise ValueError('Presentation TTL must be at most five minutes')
        self.stage, self.recording, self.clock, self.ttl = stage, recording, clock, ttl
        self.lock = threading.RLock()
        self.epoch = 0
        self.current = None
        self.blocked = None
        self.confirmation_owner = None
        self.deadline = 0.
        self.invalidated_at = float('-inf')
        self.transcript = self.reply = ''
        self.expirations = self.invalidations = self.retirements = 0
        self.attached = False
        self.closed = False

    def _expire(self):
        if self.current is not None and self.clock() >= self.deadline:
            self.blocked, self.current = self.current, None
            self.confirmation_owner = None
            self.transcript = self.reply = ''
            self.epoch += 1
            self.expirations += 1

    def channel(self, header, owner, requested_at):
        key = _owner(owner)
        with self.lock:
            self._expire()
            kind = header['kind']
            if kind == 'start' and key != self.blocked and not self.closed:
                now = self.clock()
                if not isinstance(requested_at, (float, int)) or not math.isfinite(requested_at):
                    return
                admitted = min(now, requested_at)
                # A precommit progress item may still be queued when Store
                # invalidates. Its later start cannot create a fresh epoch.
                confirmation = key == self.confirmation_owner
                if admitted <= self.invalidated_at and not confirmation:
                    return
                deadline = admitted + self.ttl
                if self.current == key:
                    deadline = min(self.deadline, deadline)
                self.current = key
                self.deadline = deadline
                if not confirmation:
                    self.confirmation_owner = None
                self.transcript = self.reply = ''
                self.epoch += 1
            if self.current != key or self.closed:
                return
            if kind == 'transcript' and key != self.confirmation_owner:
                self.transcript = str(header.get('text', ''))[:4096]
            elif kind == 'text':
                value = self.reply + str(header.get('text', ''))
                self.reply = value if len(value) <= 16384 else ''
            self._expire()

    def _projection(self, state):
        self._expire()
        state = _clean(state)
        state['reply'] = self.reply
        local = state.setdefault('local_transcription', {})
        local['text'] = self.transcript
        local['voice_reply'] = None
        state['presentation_lifecycle'] = dict(epoch=self.epoch,
            showing=bool(self.transcript or self.reply), ttl_seconds=self.ttl,
            expirations=self.expirations, invalidations=self.invalidations,
            duplicate_buffers_retired=self.retirements, metadata_diagnostics_only=True)
        return state

    def project(self, state):
        with self.lock:
            return self._projection(state)

    def _purge_public_copies(self):
        """Called under our lock; these caches have no callback into us."""
        bridge = getattr(self.stage, 'bridge', None)
        if bridge is not None:
            with bridge.lock:
                bridge.state = _clean(self._projection(bridge.state))
        # Worker read() reprojects after releasing its own condition, and its
        # next public() publication replaces the cached state. Taking that
        # condition here would invert the original worker->public lock order.

    def invalidate(self, confirmation_owner=None):
        # Conservative scope-wide presentation invalidation: no names, IDs or
        # fact values are inspected. Confirmation audio/ACK remains untouched.
        with self.lock:
            self._expire()
            old = self.current
            if old != confirmation_owner:
                self.blocked, self.current = old or self.blocked, None
            # Only the current command whose Store commit actually returned
            # may show its new confirmation reply. Never restore its raw ASR.
            self.confirmation_owner = confirmation_owner
            self.transcript = self.reply = ''
            self.invalidated_at = self.clock()
            self.epoch += 1
            self.invalidations += 1
            self._purge_public_copies()
        glib = getattr(self.stage, 'GLib', None)
        if self.attached and glib is not None:
            try:
                glib.idle_add(self.repaint)
            except Exception:
                # A shutting-down GTK loop must not turn a committed memory
                # operation into a reported failure. Reads are already masked.
                pass

    def repaint(self):
        with self.lock:
            self._expire()
            stage = self.stage
            if getattr(stage, 'closed', False):
                return False
            transcript = self.transcript or '等待你的声音…'
            reply = self.reply
            if getattr(stage, 'transcript_label', None) is not None:
                stage.transcript_label.set_text(transcript)
                stage.transcript_label.set_tooltip_text(transcript)
            if getattr(stage, 'reply_view', None) is not None:
                stage.reply_view.get_buffer().set_text(reply)
            stage.reply_text = reply
            if getattr(stage, 'reply', None) is not None:
                stage.reply.set_text(reply)
            stage.runtime_view = _clean(getattr(stage, 'runtime_view', {}))
        return False

    def retire_consumed(self):
        """Audio owner only, after canonical commit/abort and all ACK actions.

        Keep capture/request IDs and auto-turn states for rearm, and never
        cancel/acknowledge or alter the active plan, queue, stream or clock.
        """
        runtime = self.stage.board_business.runtime
        visual = self.recording.controller
        # Do not take our mutex while entering any business/audio gate.
        idle = runtime._foreground_idle()
        if not idle or any(getattr(visual, key, None) is not None
                           for key in ('stream', 'pending', 'ready', 'audio_waiting')):
            return False
        if (visual.output.active or getattr(visual.output, 'paused', False)
                or visual.phase != 'IDLE'):
            return False
        visual.turns.clear()
        visual.log.clear()
        visual.reply = ''
        visual.core.reply_text = ''
        # A manual recording can be ready but not submitted yet. Its buffers
        # belong to the user until submitted/cancelled, even while jobs idle.
        if self.recording.transcription.get('state') == 'ANSWERED':
            self.recording.transcription['text'] = ''
            self.recording.transcription['voice_reply'] = None
            self.recording.utterance = None
            self.recording._public_utterance = None
            self.recording._public_metadata = None
        with self.lock:
            self.retirements += 1
            self._expire()
        return True


def _production(stage):
    business = getattr(stage, 'board_business', None)
    return business is not None and business.runtime.config.data_origin == 'board'


def bind_presentation(stage, recording, *, clock=time.monotonic, ttl=300.):
    """Before AvatarRenderWorker construction; no shared class/global patches."""
    if not _production(stage):
        return None
    if getattr(stage, 'production_presentation', None) is not None:
        raise RuntimeError('Presentation already bound')
    lifecycle = PresentationLifecycle(stage, recording, clock=clock, ttl=ttl)
    stage.production_presentation = lifecycle
    visual = recording.controller
    original_event, original_tick, original_public = visual.channel_event, recording.tick, recording.public

    def channel_event(header, pcm, owner, feedback_assets, requested_at):
        result = original_event(header, pcm, owner, feedback_assets, requested_at)
        stream = visual.stream
        if stream is not None and stream['owner'] == owner:
            lifecycle.channel(header, owner, requested_at)
        return result

    def tick():
        result = original_tick()
        lifecycle.retire_consumed()
        return result

    def public():
        return lifecycle.project(original_public())

    visual.channel_event, recording.tick, recording.public = channel_event, tick, public
    jobs = stage.board_business.runtime.jobs
    previous_invalidator = jobs.playback_invalidator
    def playback_invalidated(reason, owner):
        if reason in ('playback_cancelled', 'generation_changed', 'stream_failed'):
            lifecycle.invalidate()
        # A normal playback-token publication must not erase its own subtitle.
        if previous_invalidator is not None:
            previous_invalidator(reason, owner)
    jobs.playback_invalidator = playback_invalidated
    # Wrappers run only after the original transaction context has exited.
    # No Store state/content, exception, permission or return value is changed.
    store = stage.board_business.runtime.store
    def committed_command_owner(operation_turn_id):
        if not isinstance(operation_turn_id, str) or not operation_turn_id:
            return None
        # Read ownership before taking the presentation lock. Original Store
        # authorization/transaction has already succeeded; no grant is minted.
        with jobs.condition:
            job = jobs._active_job
            if (job is not None and jobs.active == operation_turn_id
                    and job.meta.get('request_id') == operation_turn_id and jobs._current(job)):
                return _owner(job.meta)
        return None
    for name in ('correct', 'forget', 'clear', 'commit_compaction'):
        original = getattr(store, name)
        def after_commit(*args, _original=original, _name=name, **kwargs):
            result = _original(*args, **kwargs)
            if _name != 'commit_compaction' or result.get('committed') is True:
                confirmed = (committed_command_owner(kwargs.get('operation_turn_id'))
                             if _name != 'commit_compaction' else None)
                lifecycle.invalidate(confirmed)
            return result
        setattr(store, name, after_commit)
    return lifecycle


def attach_presentation(stage):
    lifecycle = getattr(stage, 'production_presentation', None)
    if lifecycle is None:
        return
    bridge = stage.bridge
    original_publish = bridge.publish
    def publish(state, frame):
        with lifecycle.lock:
            # This localhost control API never serves user subtitles in
            # production. GTK alone projects the bounded current RAM slot.
            original_publish(_clean(lifecycle._projection(state)), frame)
    bridge.publish = publish
    worker = stage.controller
    original_worker_read = worker.read
    def read():
        packet = original_worker_read()
        packet['state'] = lifecycle.project(packet['state'])
        return packet
    worker.read = read
    # The UI service snapshot remains source-validated for identity business;
    # presentation reads cannot revive an old external subtitle.
    services = getattr(stage, 'services', None)
    if services is not None:
        original_service_read = services.read
        services.read = lambda: _clean(original_service_read())
    lifecycle.attached = True
    lifecycle.repaint()


def project_presentation(stage, state):
    lifecycle = getattr(stage, 'production_presentation', None)
    if lifecycle is None:
        return state
    result = lifecycle.project(state)
    lifecycle.repaint()
    return result


def close_presentation(stage):
    lifecycle = getattr(stage, 'production_presentation', None)
    if lifecycle is not None:
        with lifecycle.lock:
            lifecycle.closed = True
        lifecycle.invalidate()


def save_production_evidence(stage):
    """Return None only outside board-production; never call screen capture.

    A single bounded metadata file replaces raw stage/latest/window archives.
    No runtime dictionaries, exception strings, IDs, settings or paths from
    requests are serialised. Canonical private root was bootstrap-verified.
    """
    if not _production(stage):
        return None
    runtime = stage.board_business.runtime
    root = Path(runtime.config.private_root)
    if not root.is_absolute() or root.resolve(strict=True) != root or not root.is_dir():
        raise ValueError('Canonical private diagnostics root required')
    info = root.stat()
    if os.name != 'nt' and (info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077):
        raise ValueError('Private diagnostics permissions required')
    directory = root / 'diagnostics'
    directory.mkdir(mode=0o700, exist_ok=True)
    if directory.resolve(strict=True) != directory or not directory.is_dir():
        raise ValueError('Canonical private diagnostics directory required')
    info = directory.stat()
    if os.name != 'nt' and (info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077):
        raise ValueError('Private diagnostics permissions required')
    lifecycle = getattr(stage, 'production_presentation', None)
    if lifecycle is None:
        raise RuntimeError('Production presentation must bind before diagnostics')
    with lifecycle.lock:
        lifecycle._expire()
        report = dict(schema='aura.private-ui-metadata-1', metadata_only=True,
            body_saved=False, images_saved=False, ttl_seconds=lifecycle.ttl,
            epoch=lifecycle.epoch, expired_count=lifecycle.expirations,
            invalidated_count=lifecycle.invalidations,
            duplicate_buffers_retired=lifecycle.retirements,
            ui_closed=bool(getattr(stage, 'closed', False)),
            diagnostic_mono_ns=time.monotonic_ns())
    target = directory / 'latest_metadata.json'
    if target.is_symlink() or target.exists() and (not target.is_file() or target.stat().st_nlink != 1):
        raise ValueError('Unsafe diagnostics file')
    temp = directory / ('.metadata-' + str(time.monotonic_ns()) + '.tmp')
    fd = os.open(str(temp), os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write((json.dumps(report, sort_keys=True) + '\n').encode('ascii'))
        os.replace(str(temp), str(target))
    finally:
        if temp.exists():
            temp.unlink()
    stage.diagnostic_job = dict(state='COMPLETE', metadata_only=True)
    return dict(ok=True, queued=False, metadata_only=True, message='元数据诊断已保存')
