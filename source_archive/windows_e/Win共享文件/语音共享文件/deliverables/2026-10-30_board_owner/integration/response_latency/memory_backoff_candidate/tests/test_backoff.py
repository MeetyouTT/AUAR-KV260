"""Synthetic Store, fake monotonic clock, no worker/device/model startup."""
import ast
import importlib.util
from pathlib import Path
import sqlite3
import sys

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[5]
sys.path.insert(0, str(ROOT / 'aura'))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


memory = load('common.backoff_test_memory', HERE.parents[1] /
              'memory_candidate/after/common/board_memory.py')
previous = sys.modules.get('common.board_memory')
sys.modules['common.board_memory'] = memory
try:
    backoff = load('common.backoff_test_wrapper', HERE.parent /
                   'after/common/board_memory_backoff.py')
finally:
    if previous is None: sys.modules.pop('common.board_memory', None)
    else: sys.modules['common.board_memory'] = previous


class Clock:
    def __init__(self): self.now = 10.
    def __call__(self): return self.now


def fixture(tmp_path, summary, *, idle=lambda: True):
    event_clock = [1000.]
    store = memory.BoardMemoryStore(tmp_path / 'public.sqlite3', clock=lambda: event_clock[0])
    store.append_event(dict(kind='conversation', id='public-scope'),
                       'public-event', 'user_said', '公开事实。')
    event_clock[0] = 1400.
    clock = Clock()
    worker = backoff.BoardMemoryBackoffWorker(store, summary, idle=idle, retry_clock=clock)
    return store, worker, clock


def fail(*args): raise ValueError('public-fixture-rejection')


def candidate(task, cancelled):
    return dict(schema_version=task['schema_version'], scope=task['scope'], topic=task['topic'],
        start_utc=task['start_utc'], end_utc=task['end_utc'], summary='公开事实。', keywords=['公开'],
        source_refs=[dict(event_id=s['event_id'], revision=s['revision']) for s in task['sources'] if s['include_in_summary']],
        claims=task['required_claims'])


def test_failure_schedule_caps_at_sixty_and_cooldown_never_calls_model_or_drops_body(tmp_path):
    calls = []
    def summarize(*args):
        calls.append(True)
        return fail(*args)
    store, worker, clock = fixture(tmp_path, summarize)
    assert worker.interval == 3.
    for index, delay in enumerate([3., 6., 12., 24., 48., 60., 60.], 1):
        assert worker.step() is False
        value = worker.health()['retry_backoff']
        assert value['failure_streak'] == index and value['last_delay_seconds'] == delay
        assert len(calls) == index
        for _ in range(2): assert worker.step() is False
        assert len(calls) == index and worker.health()['retry_backoff']['skipped_for_cooldown']
        clock.now += delay
    with sqlite3.connect(store.path) as db:
        assert db.execute('SELECT COUNT(*) FROM bm_bodies').fetchone()[0] == 1
        assert db.execute('SELECT COUNT(*) FROM bm_summaries').fetchone()[0] == 0
        assert db.execute('SELECT attempts FROM bm_tasks').fetchone()[0] == 7
    assert worker.completed == 0 and worker.discarded == 7


def test_success_resets_failure_streak_then_empty_work_does_not_count_failure(tmp_path):
    reject = [True]
    def summarize(task, cancelled):
        return fail() if reject[0] else candidate(task, cancelled)
    store, worker, clock = fixture(tmp_path, summarize)
    assert not worker.step()
    clock.now += 3.
    assert not worker.step()
    clock.now += 6.
    reject[0] = False
    assert worker.step()
    state = worker.health()['retry_backoff']
    assert state['failure_streak'] == state['retry_in_seconds'] == state['last_delay_seconds'] == 0
    assert state['last_failure_code'] == '' and worker.error == ''
    assert not worker.step() and worker.health()['retry_backoff']['failure_streak'] == 0


@pytest.mark.parametrize('exception,code,streak', [
    (InterruptedError, 'cancelled', 0),
    (TimeoutError, 'deadline_exceeded', 1),
    (RuntimeError, 'model_failed', 1),
])
def test_exception_type_classifies_interruption_without_text_parsing(tmp_path, exception, code, streak):
    def summarize(*args): raise exception('public-fixture-only')
    store, worker, clock = fixture(tmp_path, summarize)
    assert worker.step() is False
    assert worker.error == code
    assert worker.health()['retry_backoff']['failure_streak'] == streak


def test_source_or_foreground_invalidation_is_cancelled_even_if_transport_raises_oserror(tmp_path):
    store_ref = []
    def summarize(task, cancelled):
        store_ref[0].preempt_compaction()
        raise OSError('public-fixture-closed-transport')
    store, worker, clock = fixture(tmp_path, summarize)
    store_ref.append(store)
    assert worker.step() is False
    assert worker.error == 'cancelled'
    assert worker.health()['retry_backoff']['failure_streak'] == 0
    assert worker.health()['retry_backoff']['retry_in_seconds'] == 0
    assert store.health()['active_bodies'] == 1


def test_idle_false_and_no_work_do_not_invoke_summary_or_increase_failure(tmp_path):
    calls = []
    store, worker, clock = fixture(tmp_path, lambda *a: calls.append(True), idle=lambda: False)
    assert not worker.step() and calls == []
    assert worker.health()['retry_backoff']['failure_streak'] == 0
    store.clear(dict(kind='conversation', id='public-scope'))
    worker.idle = lambda: True
    assert not worker.step() and calls == []
    assert worker.health()['retry_backoff']['failure_streak'] == 0


def test_stale_commit_is_not_a_new_persistent_failure(tmp_path):
    store, worker, clock = fixture(tmp_path, candidate)
    store.commit_compaction = lambda *a: dict(committed=False, reason='stale_lease')
    assert not worker.step()
    assert worker.discarded == 1 and worker.health()['retry_backoff']['failure_streak'] == 0


def test_database_busy_before_lease_is_bounded_and_original_exception_remains_visible(tmp_path):
    store, worker, clock = fixture(tmp_path, candidate)
    def busy(**kwargs): raise memory.MemoryBusy('public-fixture-busy')
    store.prepare_compaction = busy
    with pytest.raises(memory.MemoryBusy): worker.step()
    assert worker.health()['retry_backoff']['failure_streak'] == 1
    assert not worker.step()


def test_stop_and_programming_errors_preserve_original_behavior(tmp_path):
    def programming_error(*args): raise TypeError('public-fixture-programming-error')
    store, worker, clock = fixture(tmp_path, programming_error)
    with pytest.raises(TypeError): worker.step()
    assert worker.health()['retry_backoff']['failure_streak'] == 0
    worker.stop.set()
    assert not worker.step()


def test_factory_only_imports_wrapper_and_changes_injectable_default():
    before = (HERE.parents[1] / 'source_before/board/runtime/board_business.py').read_text(encoding='utf-8')
    after = (HERE.parent / 'after/board/runtime/board_business.py').read_text(encoding='utf-8')
    restored = after.replace('from common.board_memory_backoff import BoardMemoryBackoffWorker\n', '')
    restored = restored.replace('worker_factory=BoardMemoryBackoffWorker,', 'worker_factory=BoardMemoryWorker,')
    assert ast.dump(ast.parse(restored)) == ast.dump(ast.parse(before))
