"""Public SQLite and fake-summary acceptance. No hardware or service access."""
import ast
import copy
from contextlib import closing, contextmanager
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import types
import unittest

HERE = Path(__file__).resolve().parent
REPAIR = HERE.parents[1]
CANDIDATE = REPAIR / 'memory_source_cooldown_v25_candidate'
ARCHIVE = REPAIR / 'feature_trigger_collaboration/joint_m03_identity_arm_v2/stage_v19_final_06e5/public_runtime_v19'
MAPPING = json.loads((REPAIR / 'release_v24_memory_followup_candidate/memory_followup_evidence/source_mapping.json').read_bytes())
PUBLIC_ROOT = HERE / 'public_fixtures'
PUBLIC_ROOT.mkdir(exist_ok=True)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


package = types.ModuleType('common')
package.__path__ = [str(ARCHIVE / 'common')]
sys.modules['common'] = package
for relative in ('common/character_profile.py', 'common/memory_commands.py', 'common/board_timeline_clock.py'):
    assert sha(ARCHIVE / relative) == MAPPING['component_pins'][relative]
    load_module(relative[:-3].replace('/', '.'), ARCHIVE / relative)
memory = load_module('common.board_memory', CANDIDATE / 'after/common/board_memory.py')
backoff = load_module('common.board_memory_backoff', CANDIDATE / 'after/common/board_memory_backoff.py')
LOADED_PINS = {relative: sha(CANDIDATE / 'after' / relative) for relative in
               ('common/board_memory.py', 'common/board_memory_backoff.py')}


class Clock:
    def __init__(self, now):
        self.now = now

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


def accepted_candidate(prepared):
    eligible = [source for source in prepared['sources'] if source['include_in_summary']]
    return dict(schema_version=1, scope=prepared['scope'], topic=prepared['topic'],
                start_utc=prepared['start_utc'], end_utc=prepared['end_utc'],
                source_refs=[dict(event_id=s['event_id'], revision=s['revision']) for s in eligible],
                summary='。'.join(s['text'] for s in eligible), keywords=['公开测试'],
                claims=copy.deepcopy(prepared['required_claims']))


class CooldownAcceptance(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='independent-', dir=PUBLIC_ROOT)
        self.folder = Path(self.temporary.name).resolve()
        self.assertEqual(self.folder.parent, PUBLIC_ROOT.resolve())
        self.wall = Clock(1000.)
        self.mono = Clock(10.)
        self.store = memory.BoardMemoryStore(self.folder / 'public.sqlite3', clock=self.wall)
        self.calls = []
        self.idle = True

    def tearDown(self):
        self.assertEqual(self.folder.parent, PUBLIC_ROOT.resolve())
        self.temporary.cleanup()

    def query(self, statement, parameters=()):
        with closing(sqlite3.connect(self.store.path)) as db:
            return db.execute(statement, parameters).fetchall()

    def turn(self, name, *, scope='public-conversation', text='公开内容'):
        receipt = self.store.begin_turn(dict(kind='conversation', id=scope), name, text, generation=1)
        self.wall.advance(1.)
        self.store.generated(name, '公开回复', generation=1)
        self.store.bind_audio_receipt(name, generation=1, playback_token='audio-' + name,
                                      sha256='a' * 64, samples=24000)
        self.wall.advance(1.)
        self.store.ack_played(name, generation=1, playback_token='audio-' + name,
                              sha256='a' * 64, samples=24000)
        return receipt['user_event_id']

    def reject(self, prepared, cancelled):
        self.calls.append(tuple((s['event_id'], s['revision']) for s in prepared['sources']))
        raise memory.CandidateRejected('PUBLIC_EXCEPTION_MUST_STAY_PRIVATE', rejection_reasons=('negation_missing',))

    def worker(self, summarize=None, **kwargs):
        return backoff.BoardMemoryBackoffWorker(self.store, summarize or self.reject,
            idle=lambda: self.idle, retry_clock=self.mono, **kwargs)

    def test_bad_batch_cooldown_survives_healthy_commit_and_creates_no_more_leases(self):
        bad = self.turn('bad', scope='bad-scope', text='公开坏内容')
        self.turn('healthy', scope='healthy-scope', text='公开好内容')
        self.wall.advance(301.)
        def summarize(prepared, cancelled):
            if any(s['event_id'] == bad for s in prepared['sources']):
                return self.reject(prepared, cancelled)
            self.calls.append(tuple((s['event_id'], s['revision']) for s in prepared['sources']))
            return accepted_candidate(prepared)
        worker = self.worker(summarize)
        self.assertFalse(worker.step())
        initial = self.query('SELECT task_id,status,attempts FROM bm_tasks')
        self.assertEqual(len(self.calls), 1)
        self.assertTrue(worker.step())
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(worker.health()['source_cooldown']['cached_batches'], 1)
        for _ in range(5):
            self.mono.advance(30.)
            self.assertFalse(worker.step())
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(self.query('SELECT task_id,status,attempts FROM bm_tasks WHERE task_id=?', (initial[0][0],)), initial)
        self.assertEqual(self.query('SELECT count(*) FROM bm_events WHERE reserved_task IS NOT NULL'), [(0,)])
        self.assertEqual(self.store.health()['active_bodies'], 2)
        self.assertEqual(self.store.health()['valid_summaries'], 1)

    def test_selection_skips_entire_turns_before_old_limit(self):
        exclusions = []
        bad_turns = []
        for index in range(10):
            name = 'deferred-' + str(index)
            event = self.turn(name)
            revision = self.query('SELECT revision FROM bm_events WHERE event_id=?', (event,))[0][0]
            exclusions.append(((event, revision),))
            bad_turns.append(name)
        healthy = self.turn('healthy-last')
        self.wall.advance(301.)
        prepared = self.store.prepare_compaction(max_events=1, excluded_source_versions=tuple(exclusions))
        self.assertEqual({row[0] for row in self.query('SELECT turn_id FROM bm_events WHERE reserved_task=?', (prepared['task_id'],))}, {'healthy-last'})
        self.assertEqual(len(prepared['sources']), 2)
        self.assertIn(healthy, {s['event_id'] for s in prepared['sources']})
        self.assertEqual(self.query('SELECT count(*) FROM bm_tasks'), [(1,)])
        self.assertEqual(self.query("SELECT count(*) FROM bm_events WHERE turn_id != 'healthy-last' AND reserved_task IS NOT NULL"), [(0,)])

    def test_only_one_revision_change_unlocks_complete_failed_turn(self):
        event = self.turn('revision-turn')
        self.wall.advance(301.)
        worker = self.worker()
        self.assertFalse(worker.step())
        first = self.calls[0]
        with closing(sqlite3.connect(self.store.path)) as db:
            db.execute('UPDATE bm_events SET revision=revision+1 WHERE event_id=?', (event,))
            db.commit()
        self.assertFalse(worker.step())
        self.assertEqual(len(self.calls), 2)
        self.assertEqual(len(self.calls[1]), 2)
        self.assertEqual(dict(self.calls[1])[event], dict(first)[event] + 1)
        other = next(source for source in dict(first) if source != event)
        self.assertEqual(dict(self.calls[1])[other], dict(first)[other])

    def test_monotonic_exact_expiry_retries_and_utc_does_not_shortcut_it(self):
        self.turn('expiry')
        self.wall.advance(301.)
        worker = self.worker()
        self.assertFalse(worker.step())
        self.wall.advance(100000.)
        self.mono.advance(599.999)
        self.assertFalse(worker.step())
        self.assertEqual(len(self.calls), 1)
        self.mono.now = 610.
        self.assertFalse(worker.step())
        self.assertEqual(len(self.calls), 2)

    def test_cancelled_rejection_and_unsafe_clock_do_not_cache(self):
        self.turn('cancel')
        self.wall.advance(301.)
        def cancelled_rejection(prepared, cancelled):
            self.idle = False
            return self.reject(prepared, cancelled)
        worker = self.worker(cancelled_rejection)
        self.assertFalse(worker.step())
        self.assertEqual(worker.health()['source_cooldown']['cached_batches'], 0)
        self.assertEqual(worker.health()['retry_backoff']['failure_streak'], 0)
        self.idle = True
        unsafe = [False]
        @contextmanager
        def guard():
            if unsafe[0]:
                raise memory.ClockUnavailable('PUBLIC_CLOCK_FAILURE')
            yield
        def clock_rejection(prepared, cancelled):
            unsafe[0] = True
            return self.reject(prepared, cancelled)
        second = self.worker(clock_rejection, compaction_guard_factory=guard)
        self.assertFalse(second.step())
        self.assertEqual(second.health()['source_cooldown']['cached_batches'], 0)
        self.assertEqual(second.health()['retry_backoff']['failure_streak'], 0)

    def test_stale_source_after_summary_does_not_cache_or_publish(self):
        event = self.turn('stale')
        self.wall.advance(301.)
        def changed(prepared, cancelled):
            self.store.forget(dict(kind='conversation', id='public-conversation'),
                              event_ids=[event], operation_id='public-forget')
            return self.reject(prepared, cancelled)
        worker = self.worker(changed)
        self.assertFalse(worker.step())
        self.assertEqual(worker.health()['source_cooldown']['cached_batches'], 0)
        self.assertEqual(self.store.health()['valid_summaries'], 0)

    def test_preemption_between_current_check_and_failure_release_does_not_cache(self):
        self.turn('preempt-before-release')
        self.wall.advance(301.)
        original = self.store.fail_compaction
        release_results = []
        def preempt_then_release(task_id, token, reason):
            self.store.preempt_compaction()
            result = original(task_id, token, reason)
            release_results.append(result)
            return result
        self.store.fail_compaction = preempt_then_release
        worker = self.worker()
        self.assertFalse(worker.step())
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(release_results, [dict(released=False, reason='stale_lease')])
        self.assertEqual(self.query('SELECT status,error_code FROM bm_tasks'),
                         [('cancelled', 'dialogue_preempted')])
        self.assertEqual(worker.health()['source_cooldown']['cached_batches'], 0)
        self.assertEqual(worker.health()['retry_backoff']['failure_streak'], 0)

    def test_backend_preemption_before_failure_release_has_no_global_penalty(self):
        original = self.store.fail_compaction
        for error in (RuntimeError, TimeoutError):
            with self.subTest(error=error.__name__):
                self.turn('preempt-' + error.__name__)
                self.wall.advance(301.)
                release_results = []
                def preempt_then_release(task_id, token, reason):
                    self.store.preempt_compaction()
                    result = original(task_id, token, reason)
                    release_results.append(result)
                    return result
                def failing(prepared, cancelled):
                    raise error('PUBLIC_BACKEND_FAILURE')
                self.store.fail_compaction = preempt_then_release
                worker = self.worker(failing)
                self.assertFalse(worker.step())
                self.assertEqual(release_results, [dict(released=False, reason='stale_lease')])
                self.assertEqual(worker.health()['source_cooldown']['cached_batches'], 0)
                self.assertEqual(worker.health()['retry_backoff']['failure_streak'], 0)
                self.store.fail_compaction = original

    def test_database_busy_before_lease_retains_original_global_backoff(self):
        self.turn('busy-before-lease')
        self.wall.advance(301.)
        original = self.store.prepare_compaction
        def busy(**kwargs):
            raise memory.MemoryBusy('PUBLIC_DATABASE_BUSY')
        self.store.prepare_compaction = busy
        worker = self.worker()
        with self.assertRaises(memory.MemoryBusy):
            worker.step()
        self.assertEqual(worker.health()['retry_backoff']['failure_streak'], 1)
        self.assertEqual(worker.health()['retry_backoff']['last_delay_seconds'], 3.)
        self.assertEqual(worker.health()['source_cooldown']['cached_batches'], 0)
        self.assertEqual(len(self.calls), 0)
        self.assertEqual(self.query('SELECT count(*) FROM bm_tasks'), [(0,)])
        self.store.prepare_compaction = original

    def test_commit_validation_failure_also_gets_source_cooldown(self):
        self.turn('bad-candidate')
        self.wall.advance(301.)
        def invalid(prepared, cancelled):
            self.calls.append(prepared['task_id'])
            candidate = accepted_candidate(prepared)
            candidate['source_refs'] = []
            return candidate
        worker = self.worker(invalid)
        self.assertFalse(worker.step())
        self.assertFalse(worker.step())
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(worker.health()['source_cooldown']['cached_batches'], 1)
        self.assertEqual(self.store.health()['active_bodies'], 2)

    def test_capacity_is_64_and_health_has_no_identifiers_or_body(self):
        identifiers = []
        for index in range(65):
            identifiers.append(self.turn('bounded-' + str(index), scope='scope-' + str(index)))
        self.wall.advance(301.)
        worker = self.worker(max_events=2)
        for _ in range(65):
            self.assertFalse(worker.step())
        self.assertEqual(len(self.calls), 65)
        self.assertEqual(len(worker._source_cooldowns), 64)
        self.assertEqual(worker.health()['source_cooldown'], dict(cached_batches=64,
            retry_in_seconds=600., delay_seconds=600., capacity_batches=64))
        exported = json.dumps(worker.health())
        for identifier in identifiers:
            self.assertNotIn(identifier, exported)
        self.assertNotIn('PUBLIC_EXCEPTION_MUST_STAY_PRIVATE', exported)
        self.assertNotIn('公开内容', exported)
        self.mono.advance(600.)
        self.assertEqual(worker.health()['source_cooldown']['cached_batches'], 0)
        self.assertFalse(worker.step())
        self.assertEqual(len(worker._source_cooldowns), 1)

    def test_backend_global_backoff_original_sequence_and_success_reset(self):
        self.turn('backend')
        self.wall.advance(301.)
        fail = [True]
        def summarize(prepared, cancelled):
            self.calls.append(prepared['task_id'])
            if fail[0]:
                raise ConnectionError('PUBLIC_TRANSPORT_ERROR')
            return accepted_candidate(prepared)
        worker = self.worker(summarize)
        for expected in (3., 6., 12., 24., 48., 60., 60.):
            self.assertFalse(worker.step())
            state = worker.health()['retry_backoff']
            self.assertEqual(state['last_delay_seconds'], expected)
            self.assertEqual(worker.health()['source_cooldown']['cached_batches'], 0)
            count = len(self.calls)
            self.assertFalse(worker.step())
            self.assertEqual(len(self.calls), count)
            self.mono.advance(expected)
        fail[0] = False
        self.assertTrue(worker.step())
        self.assertEqual(worker.health()['retry_backoff']['failure_streak'], 0)
        self.assertEqual(worker.health()['retry_backoff']['last_delay_seconds'], 0.)

    def test_record_failure_validator_commit_delete_and_permissions_ast_preserved(self):
        before = ast.parse((CANDIDATE / 'before/common/board_memory.py').read_text(encoding='utf-8'))
        after = ast.parse((CANDIDATE / 'after/common/board_memory.py').read_text(encoding='utf-8'))
        def top(tree, name):
            return next(node for node in tree.body if getattr(node, 'name', None) == name)
        self.assertEqual(ast.dump(top(before, 'validate_compaction_text')), ast.dump(top(after, 'validate_compaction_text')))
        before_store = top(before, 'BoardMemoryStore');after_store = top(after, 'BoardMemoryStore')
        original = {node.name: node for node in before_store.body if isinstance(node, ast.FunctionDef)}
        current = {node.name: node for node in after_store.body if isinstance(node, ast.FunctionDef)}
        self.assertEqual(set(original), set(current))
        for name in original:
            if name != 'prepare_compaction':
                self.assertEqual(ast.dump(original[name]), ast.dump(current[name]), name)
        old = ast.parse((CANDIDATE / 'before/common/board_memory_backoff.py').read_text(encoding='utf-8'))
        new = ast.parse((CANDIDATE / 'after/common/board_memory_backoff.py').read_text(encoding='utf-8'))
        a = next(node for node in top(old, 'BoardMemoryBackoffWorker').body if getattr(node, 'name', '') == '_record_failure')
        b = next(node for node in top(new, 'BoardMemoryBackoffWorker').body if getattr(node, 'name', '') == '_record_failure')
        self.assertEqual(ast.dump(a), ast.dump(b))


if __name__ == '__main__':
    unittest.main(verbosity=2)
