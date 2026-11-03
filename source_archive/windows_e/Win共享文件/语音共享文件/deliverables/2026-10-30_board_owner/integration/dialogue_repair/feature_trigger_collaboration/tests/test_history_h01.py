"""Actual source selection before LIMIT/counts and unchanged original grants."""
import pytest
from common.board_memory import BoardMemoryStore, ScopeDenied


def setup(tmp_path):
    clock = [1793400000.]
    store = BoardMemoryStore(tmp_path/'public.sqlite3', clock=lambda:clock[0])
    scope = dict(kind='conversation', id='a'*32)
    store.append_event(scope, 'public-target', 'user_said', '公开历史标记：海鸥。')
    clock[0] += 1
    receipt = store.begin_turn(scope, 'current-query', '查询今天海鸥记录', generation=1)
    return store,scope,receipt


def test_current_query_filtered_before_limit_and_matching_count(tmp_path):
    store,scope,receipt = setup(tmp_path)
    before = store.history_with_status(scope, search='海鸥', limit=1)
    assert before['items'][0]['event_id']==receipt['user_event_id']
    assert before['status']['matching_count']==2 and before['status']['result_limited']
    after = store.history_with_status(scope, search='海鸥', limit=1,
                                       exclude_event_ids=(receipt['user_event_id'],))
    assert [r['event_id'] for r in after['items']]==['public-target']
    assert after['status']['matching_count']==after['status']['returned_count']==1
    assert not after['status']['result_limited'] and not after['status']['absence_proven']


def test_other_scope_and_missing_grant_never_get_query_authority(tmp_path):
    store,scope,receipt = setup(tmp_path)
    other = dict(kind='conversation', id='b'*32)
    assert not store.history_with_status(other,exclude_event_ids=(receipt['user_event_id'],))['items']
    with pytest.raises(ScopeDenied):
        store.history_with_status(dict(kind='profile',id='c'*32),exclude_event_ids=(receipt['user_event_id'],))
    assert len(store.history(scope))==2


@pytest.mark.parametrize('exclusions',[None, 'public-target', ['bad\nkey'], ['x']*17])
def test_internal_exclusions_fail_closed_on_unbounded_or_invalid_input(tmp_path,exclusions):
    store,scope,_ = setup(tmp_path)
    with pytest.raises(ValueError):
        store.history_with_status(scope,exclude_event_ids=exclusions)


def test_duplicate_exclusions_do_not_corrupt_sql_counts_and_punctuation_cannot_widen(tmp_path):
    store,scope,receipt = setup(tmp_path)
    excluded = (receipt['user_event_id'],)*2
    assert len(store.history(scope,exclude_event_ids=excluded))==1
    result = store.history_with_status(scope,search='。！',exclude_event_ids=excluded)
    assert result['items']==[] and result['status']['matching_count']==0
    assert result['status']['absence_proven'] is False


def test_indivisible_summaries_and_boundary_counts_obey_source_exclusion(tmp_path):
    from tests.framework.test_board_memory import Clock, candidate
    clock = Clock()
    store = BoardMemoryStore(tmp_path/'public-summary.sqlite3', clock=clock)
    scope = dict(kind='conversation',id='summary-scope')
    store.append_event(scope,'summarized-source','user_said','公开摘要来源海鸥')
    start=clock()
    clock.advance(1)
    store.append_event(scope,'second-summarized-source','user_said','公开摘要另一条海鸥来源')
    clock.advance(301)
    task=store.prepare_compaction(max_events=2)
    receipt=store.commit_compaction(task['task_id'],task['lease_token'],candidate(task,'公开摘要来源海鸥'))
    assert receipt['committed']
    assert store.history_with_status(scope)['status']['matching_count']==1
    selected=store.history_with_status(scope,exclude_event_ids=('summarized-source',),limit=1)
    assert selected['items']==[] and selected['status']['matching_count']==0
    assert store.history_with_status(scope,start=start+.1)['status']['boundary_omitted_summaries']==1
    assert store.history_with_status(scope,start=start+.1,exclude_event_ids=('summarized-source',))['status']['boundary_omitted_summaries']==0
