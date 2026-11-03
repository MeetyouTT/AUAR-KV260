"""Local synthetic SQLite and fake-completion tests, without model or device IO."""
from collections import OrderedDict
from concurrent.futures import Future
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
REPAIR = HERE.parent
BASE = REPAIR / 'feature_trigger_collaboration/candidate_m03_v90_stage/public_runtime_v90'
sys.path.insert(0, str(BASE))
import common
common.__path__ = [str(HERE/'after/common'), str(BASE/'common')]

from common.board_memory import BoardMemoryStore, MemoryBusy, ScopeDenied, IdempotencyConflict
from common.board_timeline_clock import ClockUnavailable
from common.speaker_turns import record
from board.runtime.visual_memory import CameraHealthError, CameraHealthSample, VisualTimelineWorker


def load(relative, slot):
    name = 'public_replay_' + slot + '_' + Path(relative).stem
    if relative.startswith('common/'):
        name = 'common.' + name
    spec = importlib.util.spec_from_file_location(name, HERE / slot / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


BUSINESS = {slot: load('board/runtime/board_business.py', slot) for slot in ('before', 'after')}
SPEAKER = {slot: load('board/runtime/board_speaker_business.py', slot) for slot in ('before', 'after')}
BASE_MEMORY = load('common/board_memory.py', 'before')
BOOT = 'public-synthetic-boot'
CID = 'a' * 32


class Mono:
    def __init__(self):
        self.now = 100.

    def __call__(self):
        return self.now


class Timeline:
    def __init__(self, mono):
        self.boot_id = BOOT
        self.monotonic = mono
        self.calls = 0
        self.fail = False

    def event_time(self):
        self.calls += 1
        if self.fail:
            raise ClockUnavailable('public_fixture_clock_failure')
        return 1793400000. + self.monotonic()


class Cancel:
    def __init__(self, mono):
        self.mono = mono
        self.flag = False
        self.waits = []
        self.on_wait = None

    def is_set(self):
        return self.flag

    def set(self):
        self.flag = True

    def wait(self, delay):
        self.waits.append(delay)
        self.mono.now += delay
        if self.on_wait is not None:
            self.on_wait()
        return self.flag


class Fixture:
    def __init__(self, root, slot='after'):
        self.mono = Mono()
        self.timeline = Timeline(self.mono)
        self.cancel = Cancel(self.mono)
        self.current = True
        store_type = BASE_MEMORY.BoardMemoryStore if slot == 'before' else BoardMemoryStore
        self.store = store_type(root / 'public.sqlite3', clock=self.timeline.event_time, sqlite_timeout=.01)
        self.pcm = bytes(6400)
        self.meta = dict(protocol='aura-asr-1', board_boot_id=BOOT, session_id='public-session',
            request_id='public-request', generation=1, capture_id='public-capture', sample_count=3200,
            pcm_sha256=hashlib.sha256(self.pcm).hexdigest(), budget_ms=120000)
        self.job = SimpleNamespace(meta=self.meta, pcm=self.pcm, scope=dict(kind='conversation', id=CID),
            deadline=self.mono() + 120., context_source_id='conversation:' + CID)
        self.future = Future()
        self.speaker = SPEAKER[slot].BoardSpeakerBusiness.__new__(SPEAKER[slot].BoardSpeakerBusiness)
        self.speaker.lock = threading.RLock()
        self.speaker.clock = self.mono
        self.speaker.results = OrderedDict()
        self.speaker.latest = {(BOOT, self.meta['session_id']): self.meta}
        self.speaker.closing = threading.Event()
        self.speaker.counts = dict(evidence_errors=0, unavailable=0)
        self.speaker.last_evidence_error = None
        self.speaker.on_evidence = None
        self.speaker._submit = self.submit_future
        cls = BUSINESS[slot].BoardBusinessRuntime
        self.business = cls.__new__(cls)
        self.business.store = self.store
        self.business.timeline = self.timeline
        self.business.clock = self.mono
        self.business.speaker_business = self.speaker
        self.business.identity_handler = SimpleNamespace(_visual=lambda job: None, _gallery=lambda job: None)
        self.submissions = 0
        self.attempts = []
        self.original_append = self.store.append_event
        self.blocker = None

    def submit_future(self, operation, meta, pcm, **kwargs):
        self.submissions += 1
        job = dict(meta=meta, pcm=None, cancelled=kwargs['cancel_event'],
                   deadline=kwargs['deadline'], is_current=kwargs['is_current'])
        job['future'] = self.future
        return self.future, job

    def submit(self):
        return self.business._submit_speaker_analysis('公开合成句', job=self.job,
            is_current=lambda: self.current, cancel_event=self.cancel)

    def complete(self):
        self.future.set_result(record(self.meta, CID, status='COMPLETE', reason='DESCRIPTIVE_EVIDENCE_ONLY'))

    def count(self):
        with self.store._db() as db:
            return db.execute('SELECT count(*) FROM bm_events').fetchone()[0]

    def lock_database(self):
        self.blocker = sqlite3.connect(self.store.path, isolation_level=None)
        self.blocker.execute('BEGIN IMMEDIATE')

    def unlock_database(self):
        if self.blocker is not None:
            self.blocker.rollback()
            self.blocker.close()
            self.blocker = None

    def instrument(self, *, release_after_busy=False, after_busy=None, commit_then_busy=False,
                   exception=None, permanent_busy=False):
        def append(*args, **kwargs):
            self.attempts.append(copy.deepcopy((args, kwargs)))
            if exception is not None:
                raise exception
            if permanent_busy:
                raise MemoryBusy('public_fixture_persistent_contention')
            if commit_then_busy and len(self.attempts) == 1:
                self.original_append(*args, **kwargs)
                if after_busy is not None:
                    after_busy()
                raise MemoryBusy('public_fixture_uncertain_completed_commit')
            try:
                return self.original_append(*args, **kwargs)
            except (MemoryBusy, BASE_MEMORY.MemoryBusy):
                if release_after_busy:
                    self.unlock_database()
                if after_busy is not None:
                    after_busy()
                raise
        self.store.append_event = append


class SpeakerReplay(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='aura-public-evidence-retry-')
        self.root = Path(self.temp.name)
        self.fixtures = []

    def tearDown(self):
        for fixture in self.fixtures:
            fixture.unlock_database()
        self.temp.cleanup()

    def fixture(self, slot='after'):
        fixture = Fixture(self.root / str(len(self.fixtures)), slot)
        self.fixtures.append(fixture)
        return fixture

    def complete_while_sqlite_waits(self, f, invalidation):
        """The trace signals BEGIN before lock acquisition on a second connection."""
        reached_begin = threading.Event()
        finished = threading.Event()
        errors = []
        connect = sqlite3.connect
        def observed_connect(*args, **kwargs):
            connection = connect(*args, **kwargs)
            connection.set_trace_callback(lambda sql: reached_begin.set()
                if sql == 'BEGIN IMMEDIATE' else None)
            return connection
        def complete():
            try:
                f.complete()
            except BaseException as exc:
                errors.append(type(exc).__name__)
            finally:
                finished.set()
        f.store.sqlite_timeout = .15
        f.submit()
        f.lock_database()
        thread = threading.Thread(target=complete)
        try:
            with patch('sqlite3.connect', observed_connect):
                thread.start()
                self.assertTrue(reached_begin.wait(1.))
                self.assertFalse(finished.is_set())
                invalidation()
                f.unlock_database()
                self.assertTrue(finished.wait(1.))
                thread.join(1.)
        finally:
            f.unlock_database()
            if thread.ident is not None:
                thread.join(1.)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])

    def test_baseline_sqlite_wait_can_commit_after_cancel_owner_change_or_expiry(self):
        for mode in ('cancel', 'owner', 'deadline'):
            with self.subTest(mode=mode):
                f = self.fixture('before')
                f.instrument()
                invalidation = {
                    'cancel': f.cancel.set,
                    'owner': lambda: setattr(f, 'current', False),
                    'deadline': lambda: setattr(f.mono, 'now', f.job.deadline),
                }[mode]
                self.complete_while_sqlite_waits(f, invalidation)
                self.assertEqual(f.count(), 1)
                self.assertEqual(len(f.attempts), 1)
                self.assertEqual(f.speaker.counts['evidence_errors'], 0)

    def test_guard_rejects_cancel_owner_change_and_expiry_after_real_sqlite_wait(self):
        for mode in ('cancel', 'owner', 'deadline'):
            with self.subTest(mode=mode):
                f = self.fixture()
                f.instrument()
                invalidation = {
                    'cancel': f.cancel.set,
                    'owner': lambda: setattr(f, 'current', False),
                    'deadline': lambda: setattr(f.mono, 'now', f.job.deadline),
                }[mode]
                self.complete_while_sqlite_waits(f, invalidation)
                self.assertEqual(f.count(), 0)
                self.assertEqual(len(f.attempts), 1)
                self.assertEqual(f.speaker.counts['evidence_errors'], 0)

    def test_invalidation_after_insert_rolls_back_before_commit(self):
        for mode in ('cancel', 'owner', 'deadline'):
            with self.subTest(mode=mode):
                f = self.fixture()
                f.instrument()
                original = f.store._insert_event
                invalidation = {
                    'cancel': f.cancel.set,
                    'owner': lambda: setattr(f, 'current', False),
                    'deadline': lambda: setattr(f.mono, 'now', f.job.deadline),
                }[mode]
                def insert(*args, **kwargs):
                    row = original(*args, **kwargs)
                    invalidation()
                    return row
                f.store._insert_event = insert
                f.submit()
                f.complete()
                self.assertEqual(f.count(), 0)
                with f.store._db() as db:
                    self.assertEqual(db.execute('SELECT count(*) FROM bm_bodies').fetchone()[0], 0)
                    self.assertEqual(db.execute('SELECT count(*) FROM bm_scopes').fetchone()[0], 0)
                self.assertEqual(len(f.attempts), 1)
                self.assertEqual(f.speaker.counts['evidence_errors'], 0)

    def test_guard_none_preserves_existing_caller_results(self):
        before, after = self.fixture('before'), self.fixture()
        arguments = (dict(kind='device', id='public-device'), 'public-event', 'device_event', '公开合成事件')
        old = before.store.append_event(*arguments, metadata=dict(evidence='device_confirmed'))
        new = after.store.append_event(*arguments, metadata=dict(evidence='device_confirmed'))
        self.assertEqual(old, new)
        self.assertEqual(before.store.history(arguments[0]), after.store.history(arguments[0]))
        self.assertEqual(after.store.append_event(*arguments, metadata=dict(evidence='device_confirmed'), guard=None), new)
        self.assertEqual(after.count(), 1)

    def test_invalid_guard_types_are_rejected_before_database_access(self):
        f = self.fixture()
        for invalid in (False, 1, 'private-marker', {}, []):
            with self.subTest(type=type(invalid).__name__):
                with patch.object(f.store, '_db', side_effect=AssertionError('unexpected database access')):
                    with self.assertRaises(ValueError):
                        f.store.append_event(dict(kind='device', id='public-device'),
                            'public-event', 'device_event', '公开合成事件', guard=invalid)
        self.assertEqual(f.count(), 0)

    def test_baseline_real_sqlite_busy_loses_timeline_record_even_after_submit_retry(self):
        f = self.fixture('before')
        f.instrument(release_after_busy=True)
        f.submit()
        f.lock_database()
        f.complete()
        self.assertEqual(f.speaker.counts['evidence_errors'], 1)
        self.assertEqual(f.count(), 0)
        result = f.submit()
        self.assertEqual(result['status'], 'COMPLETE')
        self.assertEqual(f.count(), 0)
        self.assertEqual((f.submissions, len(f.attempts)), (1, 1))

    def test_real_sqlite_busy_retry_records_once(self):
        f = self.fixture()
        f.instrument(release_after_busy=True)
        f.submit()
        f.lock_database()
        f.complete()
        self.assertEqual((f.count(), len(f.attempts)), (1, 2))
        self.assertEqual(f.cancel.waits, [.025])
        self.assertEqual(f.speaker.counts['evidence_errors'], 0)
        self.assertEqual(f.attempts[0], f.attempts[1])
        self.assertIn('occurred_utc', f.attempts[0][1]['metadata'])

    def test_uncertain_success_keeps_one_event_and_identical_payload(self):
        f = self.fixture()
        f.instrument(commit_then_busy=True)
        f.submit()
        f.complete()
        self.assertEqual((f.count(), len(f.attempts)), (1, 2))
        self.assertEqual(f.attempts[0], f.attempts[1])
        self.assertEqual(f.speaker.counts['evidence_errors'], 0)

    def test_persistent_busy_has_three_total_attempts_and_static_diagnostic(self):
        f = self.fixture()
        f.instrument(permanent_busy=True)
        f.submit()
        f.complete()
        self.assertEqual((f.count(), len(f.attempts)), (0, 3))
        self.assertEqual(f.cancel.waits, [.025, .05])
        self.assertEqual(f.speaker.last_evidence_error,
                         dict(stage='evidence_callback', error='MemoryBusy'))

    def test_nontransient_exceptions_have_one_attempt(self):
        for error, code in [(ScopeDenied('private-marker'), 'ScopeDenied'),
                (IdempotencyConflict('private-marker'), 'IdempotencyConflict'),
                (sqlite3.OperationalError('private-marker'), 'SQLiteError'),
                (ClockUnavailable('private-marker'), 'ClockUnavailable'),
                (ValueError('private-marker'), 'ValueError')]:
            with self.subTest(code=code):
                f = self.fixture()
                f.instrument(exception=error)
                f.submit()
                f.complete()
                self.assertEqual((f.count(), len(f.attempts)), (0, 1))
                self.assertEqual(f.cancel.waits, [])
                self.assertEqual(f.speaker.last_evidence_error,
                                 dict(stage='evidence_callback', error=code))
                self.assertNotIn('private-marker', json.dumps(f.speaker.last_evidence_error))

    def test_deadline_insufficient_for_retry_does_not_wait_or_rewrite(self):
        f = self.fixture()
        f.job.deadline = f.mono() + .02
        f.instrument(permanent_busy=True)
        f.submit()
        f.complete()
        self.assertEqual(len(f.attempts), 1)
        self.assertEqual(f.cancel.waits, [])
        self.assertEqual(f.count(), 0)

    def test_expired_before_callback_never_writes(self):
        f = self.fixture()
        f.instrument()
        f.submit()
        f.mono.now = f.job.deadline
        f.complete()
        self.assertEqual((len(f.attempts), f.count()), (0, 0))

    def test_cancel_during_wait_prevents_second_write(self):
        f = self.fixture()
        f.instrument(permanent_busy=True)
        f.cancel.on_wait = f.cancel.set
        f.submit()
        f.complete()
        self.assertEqual((len(f.attempts), f.count()), (1, 0))

    def test_owner_replaced_during_wait_prevents_second_write(self):
        f = self.fixture()
        f.instrument(permanent_busy=True)
        f.cancel.on_wait = lambda: setattr(f, 'current', False)
        f.submit()
        f.complete()
        self.assertEqual((len(f.attempts), f.count()), (1, 0))

    def test_expiry_during_wait_prevents_second_write(self):
        f = self.fixture()
        f.instrument(permanent_busy=True)
        f.cancel.on_wait = lambda: setattr(f.mono, 'now', f.job.deadline)
        f.submit()
        f.complete()
        self.assertEqual((len(f.attempts), f.count()), (1, 0))

    def test_cancel_or_replaced_owner_before_callback_is_normal_skip(self):
        for cancelled in (False, True):
            with self.subTest(cancelled=cancelled):
                f = self.fixture()
                f.instrument()
                f.submit()
                if cancelled:
                    f.cancel.set()
                else:
                    f.current = False
                f.complete()
                self.assertEqual((len(f.attempts), f.count()), (0, 0))
                self.assertEqual(f.speaker.counts['evidence_errors'], 0)

    def test_permission_revocation_after_busy_fails_closed(self):
        from common.profile_access import ProfileAccess
        f = self.fixture()
        access = ProfileAccess(clock=f.mono)
        # The real profile Store checks access on every attempted transaction.
        f.store.profile_access = access
        _, selected = access.issue(CID, f.meta)
        f.job.scope = dict(kind='profile', id=CID, grant=selected)
        f.instrument(release_after_busy=True)
        f.cancel.on_wait = lambda: access.revoke(f.meta)
        f.submit()
        f.lock_database()
        f.complete()
        self.assertEqual(f.count(), 0)
        self.assertEqual(len(f.attempts), 2)
        self.assertEqual(f.speaker.last_evidence_error['error'], 'PermissionError')

    def test_actual_event_wait_is_interruptible(self):
        entered = threading.Event()
        class ObservedEvent(threading.Event):
            def wait(self, timeout=None):
                entered.set()
                return super().wait(timeout)
        f = self.fixture()
        f.cancel = ObservedEvent()
        f.instrument(permanent_busy=True)
        def cancel_when_waiting():
            if entered.wait(1.):
                f.cancel.set()
        canceller = threading.Thread(target=cancel_when_waiting)
        canceller.start()
        try:
            f.submit()
            f.complete()
            self.assertTrue(entered.is_set())
            self.assertTrue(f.cancel.is_set())
            self.assertEqual((len(f.attempts), f.count()), (1, 0))
        finally:
            canceller.join(1.)
        self.assertFalse(canceller.is_alive())


class Reader:
    source_kind = 'actual'

    def __init__(self, mono):
        self.clock = mono
        self.frame = 0
        self.count = 1
        self.error = None
        self.duplicate = False
        self.stale = False

    def read(self, **kwargs):
        if self.error is not None:
            raise self.error
        if not self.duplicate:
            self.frame += 1
        health = dict(board_boot_id=BOOT, service_epoch='public-service', camera_epoch='public-camera',
            role='DPU_YOLOX_PERSON_PREVIEW', timestamp_kind='appsink_dequeue_monotonic',
            observation_frame_id=self.frame, people_count=self.count,
            observation_age_ms=900 if self.stale else 10, capture_age_ms=10,
            detector=dict(count_kind='people'), camera_error=False, detector_error=False)
        return CameraHealthSample(health, self.clock()*1000, self.clock()*1000)


class VisualReplay(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='aura-public-visual-timeline-')
        self.mono = Mono()
        self.timeline = Timeline(self.mono)
        self.store = BoardMemoryStore(Path(self.temp.name) / 'public.sqlite3', clock=self.timeline.event_time)
        self.reader = Reader(self.mono)
        self.worker = VisualTimelineWorker(BOOT, self.store, self.timeline,
            reader=self.reader, monotonic=self.mono)

    def tearDown(self):
        self.temp.cleanup()

    def step(self):
        self.mono.now += .35
        return self.worker.step()

    def count(self):
        with self.store._db() as db:
            return db.execute('SELECT count(*) FROM bm_events').fetchone()[0]

    def test_unchanged_count_is_single_event(self):
        for _ in range(8):
            self.step()
        self.assertEqual(self.count(), 1)
        self.assertEqual(self.worker.public()['collector']['emitted_events'], 1)

    def test_write_failure_retries_next_new_frame(self):
        original = self.store.append_event
        attempts = []
        def append(*args, **kwargs):
            attempts.append(copy.deepcopy((args, kwargs)))
            if len(attempts) == 1:
                raise MemoryBusy('public_fixture')
            return original(*args, **kwargs)
        self.store.append_event = append
        self.step()
        self.step()
        self.assertEqual(self.step()['reason'], 'visual_store_write_failed')
        self.assertIsNone(self.worker.collector.committed_count)
        self.assertEqual(self.step()['status'], 'event_saved')
        self.assertEqual((self.count(), len(attempts)), (1, 2))
        self.assertEqual(attempts[0], attempts[1])
        self.assertEqual((self.worker.errors, self.worker.collector.rejected), (1, 0))

    def test_commit_then_exception_retries_without_duplicate(self):
        original = self.store.append_event
        attempts = []
        def append(*args, **kwargs):
            attempts.append(copy.deepcopy((args, kwargs)))
            value = original(*args, **kwargs)
            if len(attempts) == 1:
                raise MemoryBusy('public_fixture_after_commit')
            return value
        self.store.append_event = append
        for _ in range(4):
            self.step()
        self.assertEqual((self.count(), len(attempts)), (1, 2))
        self.assertEqual(attempts[0], attempts[1])

    def test_duplicate_frame_rejection_has_no_worker_error(self):
        self.step()
        self.reader.duplicate = True
        self.assertEqual(self.step()['reason'], 'duplicate_or_old_source_frame')
        self.assertEqual((self.worker.errors, self.worker.collector.rejected), (0, 1))

    def test_stale_sample_rejection_has_no_worker_error(self):
        self.reader.stale = True
        self.assertEqual(self.step()['reason'], 'stale_source')
        self.assertEqual((self.worker.errors, self.worker.collector.rejected), (0, 1))

    def test_reader_exception_increments_both_counters(self):
        self.reader.error = CameraHealthError('camera_health_io_failed')
        self.assertEqual(self.step()['reason'], 'camera_health_io_failed')
        self.assertEqual((self.worker.errors, self.worker.collector.rejected), (1, 1))

    def test_clock_failure_increments_both_counters(self):
        self.timeline.fail = True
        self.assertEqual(self.step()['reason'], 'clock_unavailable')
        self.assertEqual((self.worker.errors, self.worker.collector.rejected), (1, 1))


if __name__ == '__main__':
    unittest.main(verbosity=2)
