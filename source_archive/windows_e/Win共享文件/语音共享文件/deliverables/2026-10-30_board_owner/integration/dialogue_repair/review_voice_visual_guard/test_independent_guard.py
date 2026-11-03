"""Independent public SQLite transaction/guard checks. No model or device IO."""
import copy
import sqlite3
import tempfile
import threading
from pathlib import Path
import unittest
from unittest.mock import patch

from common.board_memory import BoardMemoryStore, MemoryBusy, ScopeDenied


HERE = Path(__file__).resolve().parent
SCOPE = {'kind': 'conversation', 'id': 'public-independent-guard'}


class IndependentGuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='public-guard-', dir=HERE)
        self.root = Path(self.temp.name).resolve()
        assert self.root.is_relative_to(HERE.resolve())
        self.now = 1793400100.
        self.store = BoardMemoryStore(self.root / 'public.sqlite3', clock=lambda: self.now, sqlite_timeout=.5)

    def tearDown(self):
        self.temp.cleanup()

    def append(self, event='public-guard-event', **kwargs):
        return self.store.append_event(SCOPE, event, 'device_event', '公开合成归属观察',
            topic='公开测试', metadata={'occurred_utc': 1793400000., 'fact_keys': ['公开项目']}, **kwargs)

    def tables(self):
        with self.store._db() as db:
            return {name: [tuple(row) for row in db.execute('SELECT * FROM ' + name)]
                    for name in ('bm_scopes', 'bm_events', 'bm_bodies', 'bm_event_fact_keys')}

    def test_guard_rechecks_after_actual_begin_wait_for_cancel_owner_and_deadline(self):
        for mode in ('cancel', 'owner', 'deadline'):
            with self.subTest(mode=mode):
                event_id = 'public-wait-' + mode
                authority = {'cancel': False, 'owner': 'original', 'now': 10., 'deadline': 20.}
                blocker = sqlite3.connect(self.store.path, isolation_level=None)
                blocker.execute('BEGIN IMMEDIATE')
                begin = threading.Event()
                finished = threading.Event()
                errors, guard_calls = [], []
                connect = sqlite3.connect

                def traced(*args, **kwargs):
                    connection = connect(*args, **kwargs)
                    connection.set_trace_callback(lambda sql: begin.set() if sql == 'BEGIN IMMEDIATE' else None)
                    return connection

                def guard():
                    guard_calls.append(True)
                    if authority['cancel'] or authority['owner'] != 'original' or authority['now'] >= authority['deadline']:
                        raise ScopeDenied('public authority expired')

                def writer():
                    try:
                        self.append(event_id, guard=guard)
                    except Exception as exc:
                        errors.append(type(exc).__name__)
                    finally:
                        finished.set()

                thread = threading.Thread(target=writer)
                try:
                    with patch('sqlite3.connect', traced):
                        thread.start()
                        self.assertTrue(begin.wait(1.))
                        self.assertFalse(finished.is_set())
                        if mode == 'cancel':
                            authority['cancel'] = True
                        elif mode == 'owner':
                            authority['owner'] = 'replacement'
                        else:
                            authority['now'] = 20.
                        blocker.rollback()
                        self.assertTrue(finished.wait(2.))
                finally:
                    blocker.rollback()
                    blocker.close()
                    thread.join(2.)
                self.assertFalse(thread.is_alive())
                self.assertEqual(['ScopeDenied'], errors)
                self.assertEqual([True], guard_calls)
                self.assertEqual([], self.tables()['bm_events'])

    def test_guard_failure_after_insert_rolls_back_scope_body_and_fact_index(self):
        self.append('public-untouched')
        before = self.tables()
        calls = []
        original = self.store._insert_event
        inserted = []

        def insert(*args, **kwargs):
            row = original(*args, **kwargs)
            inserted.append(True)
            return row

        def guard():
            calls.append(True)
            if inserted:
                raise RuntimeError('public guard rejection after insertion')

        with patch.object(self.store, '_insert_event', side_effect=insert), self.assertRaisesRegex(RuntimeError, 'guard rejection'):
            self.append(guard=guard)
        self.assertEqual([True, True], calls)
        self.assertEqual(before, self.tables())

    def test_uncertain_postcommit_busy_retry_is_one_event_with_original_timestamp(self):
        calls = []
        def guard():
            calls.append(True)
        try:
            first = self.append(guard=guard)
            raise MemoryBusy('public postcommit transport uncertainty')
        except MemoryBusy:
            self.now += .05
            second = self.append(guard=guard)
        self.assertEqual(first, second)
        tables = self.tables()
        self.assertEqual(1, len(tables['bm_events']))
        self.assertEqual(1, len(tables['bm_bodies']))
        with self.store._db() as db:
            row = db.execute('SELECT revision,recorded_utc,occurred_utc FROM bm_events').fetchone()
            self.assertEqual((1, 1793400100., 1793400000.), tuple(row))
        self.assertEqual(4, len(calls))

    def test_idempotent_existing_event_still_checks_guard(self):
        self.append()
        before = self.tables()
        def denied():
            raise ScopeDenied('public stale replay')
        with self.assertRaises(ScopeDenied):
            self.append(guard=denied)
        self.assertEqual(before, self.tables())

    def test_two_concurrent_same_id_writers_commit_once(self):
        start = threading.Barrier(3)
        receipts, errors = [], []
        def writer():
            start.wait(timeout=2.)
            try:
                receipts.append(self.append(guard=lambda: None))
            except Exception as exc:
                errors.append(type(exc).__name__)
        threads = [threading.Thread(target=writer) for _ in range(2)]
        for thread in threads:
            thread.start()
        start.wait(timeout=2.)
        for thread in threads:
            thread.join(2.)
            self.assertFalse(thread.is_alive())
        self.assertEqual([], errors)
        self.assertEqual(2, len(receipts))
        self.assertEqual(receipts[0], receipts[1])
        self.assertEqual(1, len(self.tables()['bm_events']))

    def test_old_omitted_guard_and_none_are_identical(self):
        first = self.append(closed=False)
        before = self.tables()
        second = self.append(closed=False, guard=None)
        self.assertEqual(first, second)
        self.assertEqual(before, self.tables())
        with self.store._db() as db:
            self.assertIsNone(db.execute('SELECT closed_utc FROM bm_events').fetchone()[0])
        self.store.close_event(SCOPE, 'public-guard-event')
        with self.store._db() as db:
            self.assertEqual(1793400100., db.execute('SELECT closed_utc FROM bm_events').fetchone()[0])

    def test_invalid_guard_never_opens_database(self):
        for guard in (False, 1, 'public-invalid', {}, []):
            with self.subTest(type=type(guard).__name__), patch.object(self.store, '_db', side_effect=AssertionError('SQL reached')), self.assertRaises(ValueError):
                self.append(guard=guard)

    def test_real_busy_timeout_retains_original_memorybusy_exception(self):
        blocker = sqlite3.connect(self.store.path, isolation_level=None)
        blocker.execute('BEGIN IMMEDIATE')
        self.store.sqlite_timeout = .02
        calls = []
        try:
            with self.assertRaises(MemoryBusy):
                self.append(guard=lambda: calls.append(True))
        finally:
            blocker.rollback()
            blocker.close()
        self.assertEqual([], calls)
        self.assertEqual([], self.tables()['bm_events'])


if __name__ == '__main__':
    unittest.main()
