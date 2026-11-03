"""Public synthetic SQLite and fake-clock checks. No devices or model clients."""
import ast
from contextlib import closing, contextmanager
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
REPAIR = HERE.parent
BASE = REPAIR / 'feature_trigger_collaboration/board_integration_v17/local_runtime_v17'
sys.path.insert(0, str(BASE))


def load(name, path):
    definition = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(definition)
    sys.modules[name] = module
    definition.loader.exec_module(module)
    return module


memory = load('common.board_memory', HERE / 'after/common/board_memory.py')
backoff = load('common.board_memory_backoff', HERE / 'after/common/board_memory_backoff.py')
SCOPE = dict(kind='conversation', id='public')


def candidate(prepared, cancelled):
    return dict(schema_version=prepared['schema_version'], scope=prepared['scope'],
        topic=prepared['topic'], start_utc=prepared['start_utc'], end_utc=prepared['end_utc'],
        summary=' '.join(source['text'] for source in prepared['sources'] if source['include_in_summary']),
        keywords=['公开'], source_refs=[dict(event_id=source['event_id'], revision=source['revision'])
            for source in prepared['sources'] if source['include_in_summary']],
        claims=prepared['required_claims'])


def reject(prepared, cancelled):
    raise memory.CandidateRejected('public rejected', rejection_reasons=('negation_missing',))


class SourceCooldownTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='public-source-cooldown-')
        self.addCleanup(self.directory.cleanup)
        self.wall = 1000.
        self.mono = 0.
        self.store = memory.BoardMemoryStore(Path(self.directory.name) / 'synthetic.sqlite3', clock=lambda: self.wall)

    def event(self, event_id, text='没有移动杯子。', topic=''):
        self.store.append_event(SCOPE, event_id, 'user_said', text, topic=topic)

    def turn(self, turn_id, text='没有移动杯子。'):
        self.store.begin_turn(SCOPE, turn_id, text)
        receipt = self.store.generated(turn_id, '收到。', generation=0, provenance_complete=True)
        self.store.bind_audio_receipt(turn_id, generation=0, playback_token='public-token', sha256='0' * 64, samples=1)
        self.store.ack_played(turn_id, generation=0, playback_token='public-token', sha256='0' * 64, samples=1)
        return receipt

    def worker(self, summary=reject, **kwargs):
        return backoff.BoardMemoryBackoffWorker(self.store, summary, idle=kwargs.pop('idle', lambda: True),
            retry_clock=lambda: self.mono, **kwargs)

    def query(self, sql, parameters=()):
        with closing(sqlite3.connect(self.store.path)) as database:
            return database.execute(sql, parameters).fetchall()

    def test_semantic_failure_cools_before_any_new_lease_until_six_hundred_seconds(self):
        for reject_in_model in (True, False):
            with self.subTest(reject_in_model=reject_in_model):
                event_id = 'public-event-' + str(reject_in_model)
                self.event(event_id, topic=str(reject_in_model))
                self.wall += 400.
                calls = []
                def summarize(prepared, cancelled):
                    calls.append(True)
                    if reject_in_model:
                        return reject(prepared, cancelled)
                    answer = candidate(prepared, cancelled)
                    answer['summary'] = '移动了杯子。'
                    return answer
                worker = self.worker(summarize, max_events=1)
                self.assertFalse(worker.step())
                task_count = self.query('SELECT count(*) FROM bm_tasks')[0][0]
                attempts = self.query('SELECT sum(attempts) FROM bm_tasks')[0][0]
                for seconds in (0., 3., 60., 599.99):
                    self.mono = seconds
                    self.assertFalse(worker.step())
                self.assertEqual(1, len(calls))
                self.assertEqual(task_count, self.query('SELECT count(*) FROM bm_tasks')[0][0])
                self.assertEqual(attempts, self.query('SELECT sum(attempts) FROM bm_tasks')[0][0])
                self.assertEqual(0, worker.health()['retry_backoff']['failure_streak'])
                self.assertEqual(1, worker.health()['source_cooldown']['cached_batches'])
                self.mono = 600.
                self.assertFalse(worker.step())
                self.assertEqual(2, len(calls))
                self.assertTrue(self.query('SELECT 1 FROM bm_bodies WHERE event_id=?', (event_id,)))
                self.store.forget(SCOPE, event_ids=(event_id,))
                self.mono = 0.

    def test_unrelated_success_keeps_bad_batch_cooled(self):
        self.event('public-bad', topic='bad')
        self.wall = 1400.
        calls = []
        def summarize(prepared, cancelled):
            calls.append(prepared['topic'])
            return reject(prepared, cancelled) if prepared['topic'] == 'bad' else candidate(prepared, cancelled)
        worker = self.worker(summarize)
        self.assertFalse(worker.step())
        self.event('public-good', '整理工具。', topic='good')
        self.wall = 1800.
        self.assertTrue(worker.step())
        self.assertFalse(worker.step())
        self.assertEqual(['bad', 'good'], calls)
        self.assertEqual(1, worker.health()['source_cooldown']['cached_batches'])
        self.assertEqual(1, self.query('SELECT count(*) FROM bm_summaries')[0][0])
        self.assertEqual([('public-bad',)], self.query('SELECT event_id FROM bm_bodies'))

    def test_all_cooled_turns_filtered_before_limit_and_without_partial_turn_lease(self):
        excluded = []
        for number in range(12):
            receipt = self.turn('public-cooled-' + str(number))
            revision = self.query('SELECT revision FROM bm_events WHERE event_id=?', (receipt['user_event_id'],))[0][0]
            excluded.append(((receipt['user_event_id'], revision),))
            self.wall += 1.
        healthy = self.turn('public-healthy', '整理工具。')
        self.wall += 400.
        prepared = self.store.prepare_compaction(max_events=1, excluded_source_versions=tuple(excluded))
        self.assertEqual({healthy['user_event_id'], healthy['assistant_event_id']},
                         {source['event_id'] for source in prepared['sources']})
        self.assertEqual(1, self.query('SELECT count(*) FROM bm_tasks')[0][0])
        self.assertEqual(2, self.query('SELECT count(*) FROM bm_events WHERE reserved_task IS NOT NULL')[0][0])

    def test_one_revision_change_unlocks_entire_multi_source_batch(self):
        receipt = self.turn('public-revision')
        self.wall += 400.
        reject_now = [True]
        def summarize(prepared, cancelled):
            return reject(prepared, cancelled) if reject_now[0] else candidate(prepared, cancelled)
        worker = self.worker(summarize)
        self.assertFalse(worker.step())
        self.assertEqual(2, len(worker._source_cooldowns[0][0]))
        with closing(sqlite3.connect(self.store.path)) as database:
            database.execute('UPDATE bm_events SET revision=revision+1 WHERE event_id=?', (receipt['user_event_id'],))
            database.commit()
        reject_now[0] = False
        self.assertTrue(worker.step())
        self.assertEqual(0, self.query('SELECT count(*) FROM bm_bodies')[0][0])

    def test_revoking_one_source_unlocks_remaining_source_of_batch(self):
        self.event('public-bad')
        self.event('public-other', '整理工具。')
        self.wall = 1400.
        reject_now = [True]
        def summarize(prepared, cancelled):
            return reject(prepared, cancelled) if reject_now[0] else candidate(prepared, cancelled)
        worker = self.worker(summarize)
        self.assertFalse(worker.step())
        self.store.forget(SCOPE, event_ids=('public-bad',))
        reject_now[0] = False
        self.assertTrue(worker.step())

    def test_cancel_stop_and_preemption_override_candidate_rejection(self):
        for kind in ('idle', 'stop', 'preempt'):
            with self.subTest(kind=kind):
                self.event('public-cancel-' + kind, topic=kind)
                self.wall += 400.
                idle = [True]
                def summarize(prepared, cancelled):
                    if kind == 'idle': idle[0] = False
                    elif kind == 'stop': worker.stop.set()
                    else: self.store.preempt_compaction()
                    return reject(prepared, cancelled)
                worker = self.worker(summarize, idle=lambda: idle[0], max_events=1)
                self.assertFalse(worker.step())
                self.assertEqual((), worker._source_cooldowns)
                self.assertEqual('cancelled', worker.error)
                self.assertEqual(0, worker.health()['retry_backoff']['failure_streak'])
                self.store.forget(SCOPE, event_ids=('public-cancel-' + kind,))

    def test_unsafe_clock_on_commit_or_cooldown_guard_exit_never_caches(self):
        for fail_on, after_yield in ((2, False), (3, True)):
            with self.subTest(fail_on=fail_on):
                self.event('public-clock-' + str(fail_on), topic=str(fail_on))
                self.wall += 400.
                entries = [0]
                @contextmanager
                def guard():
                    entries[0] += 1
                    entry = entries[0]
                    if entry == fail_on and not after_yield:
                        raise memory.ClockUnavailable('public unsafe clock')
                    yield
                    if entry == fail_on and after_yield:
                        raise memory.ClockUnavailable('public unsafe clock')
                worker = self.worker(compaction_guard_factory=guard, max_events=1)
                self.assertFalse(worker.step())
                self.assertEqual((), worker._source_cooldowns)
                self.assertEqual('clock_unverified', worker.error)
                self.assertEqual(0, worker.health()['retry_backoff']['failure_streak'])
                self.store.forget(SCOPE, event_ids=('public-clock-' + str(fail_on),))

    def test_preemption_between_current_check_and_failure_release_never_caches(self):
        original = self.store.fail_compaction
        def preempt_before_release(task_id, token, reason):
            self.store.preempt_compaction()
            return original(task_id, token, reason)
        self.store.fail_compaction = preempt_before_release
        for exception in (memory.CandidateRejected, RuntimeError, TimeoutError):
            with self.subTest(exception=exception):
                event_id = 'public-release-race-' + exception.__name__
                self.event(event_id)
                self.wall += 400.
                def summarize(prepared, cancelled):
                    raise exception('public failure then preemption')
                worker = self.worker(summarize)
                self.assertFalse(worker.step())
                self.assertEqual((), worker._source_cooldowns)
                self.assertFalse(worker._failure_released)
                self.assertEqual(0, worker.health()['retry_backoff']['failure_streak'])
                self.assertTrue(all(status == 'cancelled' for status, in self.query('SELECT status FROM bm_tasks')))
                self.store.forget(SCOPE, event_ids=(event_id,))

    def test_backend_exponential_backoff_still_three_through_sixty(self):
        for exception in (RuntimeError, TimeoutError):
            with self.subTest(exception=exception):
                self.event('public-backend-' + exception.__name__, topic=exception.__name__)
                self.wall += 400.
                calls = []
                def summarize(prepared, cancelled):
                    calls.append(True)
                    raise exception('public backend failure')
                worker = self.worker(summarize, max_events=1)
                for number, delay in enumerate((3., 6., 12., 24., 48., 60., 60.), 1):
                    self.assertFalse(worker.step())
                    self.assertEqual(delay, worker.health()['retry_backoff']['last_delay_seconds'])
                    self.assertFalse(worker.step())
                    self.assertEqual(number, len(calls))
                    self.assertEqual((), worker._source_cooldowns)
                    self.mono += delay
                self.store.forget(SCOPE, event_ids=('public-backend-' + exception.__name__,))

    def test_capacity_and_health_remain_bounded_metadata_only(self):
        for number in range(65):
            self.event('public-bound-' + str(number), topic=str(number))
        self.wall = 1400.
        worker = self.worker(max_events=1)
        for _ in range(65):
            self.assertFalse(worker.step())
        self.assertEqual(64, len(worker._source_cooldowns))
        for versions, due in worker._source_cooldowns:
            self.assertIsInstance(versions, tuple)
            self.assertEqual(600., due)
            self.assertTrue(all(isinstance(event_id, str) and type(revision) is int for event_id, revision in versions))
        health = worker.health()
        self.assertEqual({'cached_batches', 'retry_in_seconds', 'delay_seconds', 'capacity_batches'}, set(health['source_cooldown']))
        self.assertEqual(64, health['source_cooldown']['cached_batches'])
        self.assertNotIn('public-bound', json.dumps(health, ensure_ascii=False))
        self.assertNotIn('没有移动', json.dumps(health, ensure_ascii=False))
        self.assertEqual((), worker._source_versions)

    def test_fresh_worker_allows_same_source_immediately(self):
        self.event('public-restart')
        self.wall = 1400.
        self.assertFalse(self.worker().step())
        self.assertTrue(self.worker(candidate).step())

    def test_default_store_and_plain_worker_keep_original_entry_points(self):
        self.event('public-default')
        self.wall = 1400.
        prepared = self.store.prepare_compaction()
        self.assertEqual('public-default', prepared['sources'][0]['event_id'])
        self.store.fail_compaction(prepared['task_id'], prepared['lease_token'], 'cancelled')
        plain = memory.BoardMemoryWorker(self.store, candidate, idle=lambda: True)
        self.assertTrue(plain.step())

    def test_exclusion_bounds_reject_before_creating_tasks(self):
        invalid = ([], ((),), (((('valid', 1),) * 65),), ((('valid', True),),),
                   ((('invalid id', 1),),), ((('valid', 1),),) * 65)
        for excluded in invalid:
            with self.subTest(kind=repr(excluded)[:30]), self.assertRaises(ValueError):
                self.store.prepare_compaction(excluded_source_versions=excluded)
        self.assertEqual(0, self.query('SELECT count(*) FROM bm_tasks')[0][0])


class SourceBoundaryTests(unittest.TestCase):
    def test_global_record_failure_and_all_unrelated_methods_are_unchanged(self):
        def classes(raw):
            return {node.name: node for node in ast.parse(raw).body if isinstance(node, ast.ClassDef)}
        for relative, allowed in (
            ('common/board_memory.py', {'BoardMemoryStore': {'prepare_compaction'}, 'BoardMemoryWorker': {'step', '_prepare_compaction', '_fail_task'}}),
            ('common/board_memory_backoff.py', {'BoardMemoryBackoffWorker': {'__init__', '_prepare_compaction', '_record_source_failure', '_fail_task', 'step', 'health'}})):
            before = ast.parse((HERE / 'before' / relative).read_bytes())
            after = ast.parse((HERE / 'after' / relative).read_bytes())
            for tree in (before, after):
                if isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Constant):
                    tree.body.pop(0)
                for node in tree.body:
                    if isinstance(node, ast.ClassDef) and node.name in allowed:
                        if isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant):
                            node.body.pop(0)
                        node.body = [item for item in node.body if not isinstance(item, ast.FunctionDef) or item.name not in allowed[node.name]]
            self.assertEqual(ast.dump(before, include_attributes=False), ast.dump(after, include_attributes=False))
        before = classes((HERE / 'before/common/board_memory.py').read_bytes())['BoardMemoryWorker']
        after = classes((HERE / 'after/common/board_memory.py').read_bytes())['BoardMemoryWorker']
        old_step = next(node for node in before.body if isinstance(node, ast.FunctionDef) and node.name == 'step')
        new_step = next(node for node in after.body if isinstance(node, ast.FunctionDef) and node.name == 'step')
        old_call = next(node for node in ast.walk(old_step) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'prepare_compaction')
        new_call = next(node for node in ast.walk(new_step) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == '_prepare_compaction')
        new_call.func, new_call.args, new_call.keywords = old_call.func, old_call.args, old_call.keywords
        self.assertEqual(ast.dump(old_step, include_attributes=False), ast.dump(new_step, include_attributes=False))


if __name__ == '__main__':
    unittest.main(verbosity=2)
