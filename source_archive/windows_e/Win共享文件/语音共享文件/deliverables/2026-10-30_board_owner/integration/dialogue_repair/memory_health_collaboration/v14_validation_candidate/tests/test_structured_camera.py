import copy
import json
import sqlite3

import pytest

import board.runtime.board_memory_policy as policy
from board.runtime.board_memory_policy import BoardSummaryClient
from board.visual_timeline import VisualTimelineCollector
from common.board_memory import BoardMemoryStore, BoardMemoryWorker, CandidateRejected, validate_compaction_text
from common.board_memory import NUMBER
from tests.framework.test_visual_timeline import feed


SCOPE = dict(kind='device', id='synthetic-camera-device')


class NoModel:
    def request(self, *args, **kwargs):
        raise AssertionError('Known typed camera events must not dispatch inference')

    def cancel(self, owner):
        raise AssertionError('No model request owns a cancellation')


def fixture(tmp_path, count=0):
    now = [1000.]
    store = BoardMemoryStore(tmp_path/'synthetic-camera.sqlite3', clock=lambda: now[0])
    collector = VisualTimelineCollector('boot', store.append_event, SCOPE, utc_clock=lambda: now[0])
    assert feed(collector,1,1000,count) is None
    assert feed(collector,2,1400,count) is None
    assert feed(collector,3,1800,count) is not None
    now[0] = 1400.
    return store, now


@pytest.mark.parametrize('count', [0,1,42,1000])
def test_valid_structured_camera_compaction_needs_no_model(tmp_path, count, monkeypatch):
    store, now = fixture(tmp_path, count)
    summary = BoardSummaryClient(NoModel(), board_boot_id='boot')
    calls = []
    original = policy.validate_compaction_text
    def check(text, sources):
        calls.append(True)
        return original(text, sources)
    monkeypatch.setattr(policy, 'validate_compaction_text', check)
    worker = BoardMemoryWorker(store, summary, idle=lambda: True)
    assert worker.step()
    assert calls and summary.metrics['model_calls'] == 0
    assert summary.failure_metadata()['method'] == 'structured_camera_counts'
    assert summary.metrics['complete_source_coverage']
    assert store.health()['backlog_events'] == store.health()['active_bodies'] == 0
    row = store.history(SCOPE)[0]
    assert row['text'].startswith('相机观察：') and str(count) in row['text']
    assert set(NUMBER.findall(row['text'])) == {str(count)}
    assert all(term not in row['text'] for term in ('离开','到来','进入','PRIVATE','摄像头视野内','source_frame_id'))
    assert row['claims'] and len(row['source_refs']) == 1
    # This is a summary rendered from typed counts, not a verbatim body archive.
    with sqlite3.connect(store.path) as db:
        assert db.execute('SELECT COUNT(*) FROM bm_bodies').fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM bm_tasks WHERE status='committed'").fetchone()[0] == 1


def test_known_camera_wording_can_fail_old_free_form_summary():
    source = dict(include_in_summary=True, text='摄像头视野内当前未检测到人体目标。',
        metadata=dict(numbers=[0], evidence='visual_observation'))
    with pytest.raises(CandidateRejected):
        validate_compaction_text('摄像头未检测到人体目标。', [source])


@pytest.mark.parametrize('mutation', ['unknown_text','extra_name','wrong_count','wrong_event_kind',
    'extra_claim','fixture_source','user_source','wrong_scope','wrong_topic','query_zero'])
def test_only_the_exact_typed_producer_contract_is_eligible(tmp_path, mutation):
    store, now = fixture(tmp_path)
    prepared = store.prepare_compaction(max_events=2)
    eligible = [copy.deepcopy(row) for row in prepared['sources'] if row['include_in_summary']]
    source = eligible[0]
    if mutation == 'unknown_text': source['text'] += 'SYNTHETIC_PRIVATE_SPEECH'
    elif mutation == 'extra_name': source['metadata']['names'] = ['SYNTHETIC_PRIVATE_NAME']
    elif mutation == 'wrong_count': source['metadata']['numbers'] = [1]
    elif mutation == 'wrong_event_kind': source['metadata']['claims'][0]['value'] = 'person_arrived'
    elif mutation == 'extra_claim': source['metadata']['claims'].append(dict(field='unknown', value='PRIVATE'))
    elif mutation == 'fixture_source': source['metadata']['claims'][-1]['value'] = 'fixture'
    elif mutation == 'user_source': source['source'] = 'user_said'
    elif mutation == 'wrong_scope': prepared['scope']['kind'] = 'profile'
    elif mutation == 'wrong_topic': prepared['topic'] = 'freeform'
    elif mutation == 'query_zero': source['text'] = '摄像头画面取样检测到0个人体目标，未检出人体。'
    summary = BoardSummaryClient(NoModel(), board_boot_id='boot')
    semantic = summary._structured_camera_summary(prepared, eligible)
    if mutation == 'query_zero':
        assert semantic is not None
        validate_compaction_text(semantic['summary'], eligible)
    else:
        assert semantic is None


@pytest.mark.parametrize('change', ['new_input','forget','lease_expired','publish_failure'])
def test_structured_path_still_respects_original_atomic_publication_guards(tmp_path, change, monkeypatch):
    store, now = fixture(tmp_path)
    summary = BoardSummaryClient(NoModel(), board_boot_id='boot')
    original = summary._structured_camera_summary
    def semantic(prepared, eligible):
        value = original(prepared, eligible)
        if change == 'new_input':
            store.begin_turn(dict(kind='conversation', id='synthetic-dialogue'), 'synthetic-new', '新问题。', generation=1)
        elif change == 'forget':
            store.forget(SCOPE, event_ids=[eligible[0]['event_id']])
        elif change == 'lease_expired':
            now[0] += 61
        elif change == 'publish_failure':
            with sqlite3.connect(store.path) as db:
                db.execute("CREATE TRIGGER reject_summary BEFORE INSERT ON bm_summaries BEGIN SELECT RAISE(ABORT,'synthetic'); END")
        return value
    monkeypatch.setattr(summary, '_structured_camera_summary', semantic)
    worker = BoardMemoryWorker(store, summary, idle=lambda: True)
    assert not worker.step()
    assert store.health()['valid_summaries'] == 0
    if change != 'forget': assert store.health()['active_bodies'] >= 1
