"""Diagnose unchanged scheduling: attempts are ordering history, never a cap."""
import sqlite3

from common.board_memory import BoardMemoryStore
from common.board_memory_backoff import BoardMemoryBackoffWorker


def candidate(prepared, cancelled):
    return dict(schema_version=prepared['schema_version'], scope=prepared['scope'], topic=prepared['topic'],
        start_utc=prepared['start_utc'], end_utc=prepared['end_utc'],
        source_refs=[dict(event_id=s['event_id'], revision=s['revision']) for s in prepared['sources'] if s['include_in_summary']],
        claims=prepared['required_claims'], summary='公开普通事件。', keywords=['公开'])


def test_poison_couples_other_event_in_same_atomic_segment_and_four_is_not_a_cap(tmp_path):
    event_clock = [1000.]
    retry_clock = [1.]
    store = BoardMemoryStore(tmp_path/'synthetic-poison.sqlite3', clock=lambda: event_clock[0])
    scope = dict(kind='conversation', id='synthetic-same-partition')
    store.append_event(scope, 'poison', 'user_said', '必须保留42。', metadata=dict(numbers=[42]))
    event_clock[0] += 1
    store.append_event(scope, 'healthy', 'user_said', '公开普通事件。')
    event_clock[0] = 1400.
    groups = []
    def summarize(prepared, cancelled):
        groups.append({source['event_id'] for source in prepared['sources']})
        return candidate(prepared, cancelled)
    worker = BoardMemoryBackoffWorker(store, summarize, idle=lambda: True, retry_clock=lambda: retry_clock[0])
    for delay in [3,6,12,24,48]:
        assert not worker.step()
        assert worker.health()['retry_backoff']['last_delay_seconds'] == delay
        before_calls = len(groups)
        assert not worker.step()  # Worker-wide cooldown stops all groups.
        assert len(groups) == before_calls
        retry_clock[0] += delay
    assert all(group == {'poison','healthy'} for group in groups)
    with sqlite3.connect(store.path) as db:
        assert db.execute('SELECT COUNT(*),MAX(attempts) FROM bm_tasks').fetchone() == (1,5)
        assert db.execute('SELECT COUNT(*) FROM bm_bodies').fetchone()[0] == 2
        assert db.execute('SELECT COUNT(*) FROM bm_summaries').fetchone()[0] == 0


def test_fewer_attempts_allows_a_different_closed_partition_after_global_cooldown(tmp_path):
    event_clock = [1000.]
    retry_clock = [1.]
    store = BoardMemoryStore(tmp_path/'synthetic-fair.sqlite3', clock=lambda: event_clock[0])
    store.append_event(dict(kind='conversation', id='synthetic-poison'), 'poison', 'user_said',
        '必须保留42。', metadata=dict(numbers=[42]))
    event_clock[0] += 1
    store.append_event(dict(kind='conversation', id='synthetic-healthy'), 'healthy', 'user_said', '公开普通事件。')
    event_clock[0] = 1400.
    worker = BoardMemoryBackoffWorker(store, candidate, idle=lambda: True, retry_clock=lambda: retry_clock[0])
    assert not worker.step()
    assert store.health()['backlog_events'] == 2
    assert not worker.step()  # Healthy work waits for that same 3-second timer.
    retry_clock[0] += 3
    assert worker.step()
    assert store.health()['backlog_events'] == 1
    assert store.history(dict(kind='conversation',id='synthetic-healthy'))[0]['source'] == 'timeline_summary'
    assert worker.health()['retry_backoff']['failure_streak'] == 0
