"""Current frozen worker behavior, synthetic SQLite and failing fake summary.

This is a diagnostic reproduction, not a retry-policy change.
"""
import importlib.util
from pathlib import Path
import sqlite3
import sys

import pytest

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[4]
sys.path.insert(0, str(PROJECT / 'aura'))
spec = importlib.util.spec_from_file_location('common.current_retry_review',
    HERE.parent / 'source_before/common/board_memory.py')
memory = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = memory
spec.loader.exec_module(memory)


@pytest.mark.parametrize('failure,expected', [
    (ValueError, 'candidate_rejected'),
    (TimeoutError, 'model_failed'),
    (InterruptedError, 'model_failed'),
])
def test_released_failure_retries_same_source_without_a_due_time(tmp_path, failure, expected):
    now = [1000.]
    scope = dict(kind='conversation', id='public-retry-scope')
    store = memory.BoardMemoryStore(tmp_path / 'public-retry.sqlite3', clock=lambda: now[0])
    store.append_event(scope, 'public-retry-event', 'user_said', '公开的合成事件。')
    now[0] = 1400.
    calls = []
    def summarize(prepared, cancelled):
        calls.append(prepared['task_id'])
        raise failure('public-synthetic-failure')
    worker = memory.BoardMemoryWorker(store, summarize, idle=lambda: True)
    assert worker.interval == 3.
    # The actual run loop waits interval=3 after every step. There is no due
    # time or failure-specific holdoff in prepare_compaction or step itself.
    for _ in range(4): assert worker.step() is False
    assert len(calls) == 4 and len(set(calls)) == 1
    assert worker.discarded == 4 and worker.completed == 0
    assert worker.error == expected
    with sqlite3.connect(store.path) as db:
        assert db.execute('SELECT status,attempts,error_code FROM bm_tasks').fetchone() == ('failed', 4, expected)
        assert db.execute('SELECT COUNT(*) FROM bm_bodies').fetchone()[0] == 1
        assert db.execute('SELECT COUNT(*) FROM bm_summaries').fetchone()[0] == 0


def test_foreground_idle_false_prevents_summary_call(tmp_path):
    now = [1000.]
    store = memory.BoardMemoryStore(tmp_path / 'public-idle.sqlite3', clock=lambda: now[0])
    store.append_event(dict(kind='conversation', id='public-idle-scope'),
                       'public-idle-event', 'user_said', '公开事件。')
    now[0] = 1400.
    calls = []
    worker = memory.BoardMemoryWorker(store, lambda *args: calls.append(True), idle=lambda: False)
    assert worker.step() is False and calls == []
