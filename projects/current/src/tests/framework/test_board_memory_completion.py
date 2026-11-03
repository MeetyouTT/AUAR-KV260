"""Synthetic-only lifecycle, multipart coverage and explicit board-mode gates.

No production data, model, network, microphone, player or device is accessed.
"""
import json
from pathlib import Path
import re
import sqlite3

import pytest

from board.runtime.board_memory_policy import BoardSummaryClient, message_cost
from common.board_memory import (BoardMemoryStore, BoardMemoryWorker, NUMBER,
                                 NEGATION, PLANNED)
from common.board_memory_migration import LegacyMigrationRejected, migrate_legacy_snapshot
from common.model_inference_wire import Owner, make_response
from common.profile_access import ProfileAccess
from tests.framework.test_board_memory import Clock, SCOPE, OTHER, played, candidate
from tests.framework.test_board_memory_migration import fingerprint, turn
from common.timeline_conversations import TimelineConversationStore


class FragmentClient:
    def __init__(self, *, clock=None, store=None, hook=None, constant=None):
        self.calls = []
        self.clock, self.store, self.hook, self.constant = clock, store, hook, constant

    def request(self, kind, payload, **options):
        assert kind == 'llm' and payload['task'] == 'summary'
        assert message_cost(payload['messages'], payload['options']['num_predict']) <= 2048
        self.calls.append(payload)
        if self.store is not None:
            with sqlite3.connect(self.store.path, isolation_level=None, timeout=.05) as db:
                db.execute('BEGIN IMMEDIATE')
                db.rollback()  # Inference never owns a database transaction.
        if self.hook is not None:
            self.hook(len(self.calls))
        records = json.loads(payload['messages'][-1]['content'])['sources']
        words = ['用户陈述']
        for record in records:
            text, meta = record.get('text', ''), record.get('protected', {})
            words.extend(meta.get('names', []))
            if '小林' in text:
                words.append('小林')
            if '架子' in text:
                words.append('杯子在架子上')
            if '继续' in text:
                words.append('约定继续')
            words.extend(str(number) for number in meta.get('numbers', []))
            words.extend(NUMBER.findall(text))
            if meta.get('negated') or NEGATION.search(text):
                words.append('尚未')
            if meta.get('status') == 'planned' or PLANNED.search(text):
                words.append('计划')
        summary = self.constant or '；'.join(dict.fromkeys(words))
        if self.clock is not None:
            self.clock.advance(20.)
        return make_response(Owner.from_dict(payload), result={'text':json.dumps(
            {'summary':summary, 'keywords':['合成']}, ensure_ascii=False)})

    def cancel(self, owner):
        pass


def long_text():
    return ('小林计划买3本书，尚未购买。' + '普通背景，' * 700 +
            '杯子在架子上。' + '普通背景，' * 700 + '约定17点继续。')


def test_long_closed_source_is_fully_covered_without_transcript_truncation(tmp_path):
    clock = Clock()
    store = BoardMemoryStore(tmp_path/'synthetic-long.sqlite3', clock=clock)
    text = long_text()
    store.append_event(SCOPE, 'private-source-id', 'user_said', text,
                       metadata={'names':['小林'], 'numbers':[3,17], 'negated':True, 'status':'planned',
                                 'source_id':'PRIVATE-CAMERA-SOURCE'})
    clock.advance(301.)
    client = FragmentClient(store=store)
    summary = BoardSummaryClient(client, board_boot_id='synthetic-boot')
    worker = BoardMemoryWorker(store, summary, idle=lambda:True)
    assert worker.step()
    assert summary.metrics['model_calls'] > 1 and summary.metrics['complete_source_coverage']
    assert summary.metrics['covered_utf8_bytes'] == len(text.encode('utf-8'))
    fragments = [record for call in client.calls
                 for record in json.loads(call['messages'][-1]['content'])['sources'] if 'part_start' in record]
    assert ''.join(record['text'] for record in sorted(fragments, key=lambda r:r['part_start'])) == text
    block = store.history(SCOPE)[0]
    assert all(word in block['text'] for word in ('小林', '3', '尚未', '计划', '杯子在架子上', '17', '约定继续'))
    assert block['source_refs'] == [{'event_id':'private-source-id', 'revision':1}]
    assert store.health()['active_bodies'] == 0
    sent = json.dumps(client.calls, ensure_ascii=False)
    assert all(private not in sent for private in ('private-source-id', 'PRIVATE-CAMERA-SOURCE', SCOPE['id'], 'lease_token'))
    assert not list(tmp_path.glob('*.wav')) and not list(tmp_path.glob('*.json'))


@pytest.mark.parametrize('mode', ['failure','new-input','bad-number','call-limit'])
def test_partial_long_summary_never_publishes_or_deletes_source(tmp_path, mode):
    clock = Clock(); store = BoardMemoryStore(tmp_path/'synthetic-failure.sqlite3', clock=clock)
    store.append_event(SCOPE, 'old', 'user_said', long_text())
    clock.advance(301.)
    def hook(count):
        if count != 2:
            return
        if mode == 'failure':
            raise OSError('synthetic inference failure')
        if mode == 'new-input':
            store.begin_turn(SCOPE, 'new', '新问题', generation=2)
    client = FragmentClient(hook=hook, constant='未保留数值' if mode == 'bad-number' else None)
    summary = BoardSummaryClient(client, board_boot_id='synthetic-boot', max_calls=1 if mode == 'call-limit' else 256)
    worker = BoardMemoryWorker(store, summary, idle=lambda:True)
    assert worker.step() is False
    assert store.health()['valid_summaries'] == 0
    with sqlite3.connect(store.path) as db:
        assert db.execute('SELECT text FROM bm_bodies WHERE event_id="old"').fetchone()[0] == long_text()


def test_multiple_model_calls_renew_short_leases_only_between_requests(tmp_path):
    clock = Clock(); store = BoardMemoryStore(tmp_path/'synthetic-renew.sqlite3', clock=clock)
    text = '普通背景，' * 200
    store.append_event(SCOPE, 'old', 'user_said', text)
    clock.advance(301.); started = clock()
    client = FragmentClient(clock=clock, store=store)
    summary = BoardSummaryClient(client, board_boot_id='synthetic-boot', clock=clock)
    worker = BoardMemoryWorker(store, summary, idle=lambda:True, lease_seconds=60)
    assert worker.step() and clock() - started > 60
    assert store.health()['active_bodies'] == 0


def test_expired_and_preempted_leases_cannot_be_renewed(tmp_path):
    clock = Clock(); store = BoardMemoryStore(tmp_path/'synthetic-stale-renew.sqlite3', clock=clock)
    store.append_event(SCOPE, 'old', 'user_said', '普通内容'); clock.advance(301.)
    first = store.prepare_compaction(lease_seconds=2)
    clock.advance(2.)
    assert not store.renew_compaction(first['task_id'], first['lease_token'])
    second = store.prepare_compaction()
    store.begin_turn(SCOPE, 'new', '新的问题', generation=2)
    assert not store.renew_compaction(second['task_id'], second['lease_token'])
    assert store.health()['active_bodies'] == 2


def test_irreducible_numeric_source_does_not_starve_other_closed_groups(tmp_path):
    clock = Clock(); store = BoardMemoryStore(tmp_path/'synthetic-fair.sqlite3', clock=clock)
    store.append_event(SCOPE, 'large-number', 'user_said', '9' * 2000)
    store.append_event(OTHER, 'other', 'user_said', '普通内容'); clock.advance(301.)
    client = FragmentClient()
    worker = BoardMemoryWorker(store, BoardSummaryClient(client, board_boot_id='synthetic-boot'), idle=lambda:True)
    assert worker.step() is False and client.calls == []
    assert worker.step() is True
    assert store.health()['active_bodies'] == 1
    assert store.history(OTHER)[0]['source'] == 'timeline_summary'


def test_large_fragment_aggregate_is_reduced_without_exceeding_context(tmp_path):
    clock = Clock(); store = BoardMemoryStore(tmp_path/'synthetic-reduce.sqlite3', clock=clock)
    store.append_event(SCOPE, 'large', 'user_said', '普通背景资料，' * 1400); clock.advance(301.)
    client = FragmentClient(constant='用户陈述普通背景资料。' * 10)
    summary = BoardSummaryClient(client, board_boot_id='synthetic-boot')
    worker = BoardMemoryWorker(store, summary, idle=lambda:True)
    assert worker.step()
    assert summary.metrics['reduction_rounds'] >= 1
    assert summary.metrics['final_summary_utf8_bytes'] <= 768


def test_boundary_omission_is_visible_without_returning_outside_narrative(tmp_path):
    clock = Clock(); store = BoardMemoryStore(tmp_path/'synthetic-boundary.sqlite3', clock=clock)
    played(store, clock, user='杯子在架子上', reply='已记下')
    clock.advance(301.); prepared = store.prepare_compaction()
    store.commit_compaction(prepared['task_id'], prepared['lease_token'], candidate(prepared, '杯子在架子上'))
    result = store.history_with_status(SCOPE, start=1001., end=1002., search='杯子')
    assert result['items'] == [] and result['status']['boundary_omitted_summaries'] == 1
    assert result['status']['boundary_incomplete'] and not result['status']['absence_proven']
    assert '杯子在架子上' not in json.dumps(result, ensure_ascii=False)
    assert store.history_with_status(SCOPE, start=1000., end=1002.)['items']
    assert not store.history_with_status(OTHER, start=1001., end=1002.)['status']['boundary_incomplete']
    assert not store.history_with_status(SCOPE, start=1001., end=1002., search='天气')['status']['boundary_incomplete']
    assert not store.history_with_status(SCOPE, start=1001., end=1002., search='%')['status']['boundary_incomplete']


def test_result_limit_has_visible_matching_count(tmp_path):
    store = BoardMemoryStore(tmp_path/'synthetic-limit.sqlite3')
    for index in range(5):
        store.append_event(SCOPE, 'event-' + str(index), 'user_said', '杯子在架子上')
    result = store.history_with_status(SCOPE, search='杯子', limit=2)
    assert len(result['items']) == 2
    assert result['status']['matching_count'] == 5 and result['status']['result_limited']


def test_explicit_board_origin_does_not_open_or_mutate_other_origins(tmp_path):
    path = tmp_path/'synthetic-values-explicit-board-mode.sqlite3'
    board = BoardMemoryStore(path, data_origin='board')
    board.append_event(SCOPE, 'old', 'user_said', '合成板端模式输入')
    assert board.health()['data_origin'] == 'board' and board.health()['production_enabled']
    before = path.read_bytes()
    with pytest.raises(ValueError):
        BoardMemoryStore(path)
    assert path.read_bytes() == before
    reopened = BoardMemoryStore(path, data_origin='board')
    assert reopened.health()['active_bodies'] == 1  # Opening never starts cleanup.
    synthetic_path = tmp_path/'synthetic-only.sqlite3'
    BoardMemoryStore(synthetic_path)
    before = synthetic_path.read_bytes()
    with pytest.raises(ValueError):
        BoardMemoryStore(synthetic_path, data_origin='board')
    assert synthetic_path.read_bytes() == before
    with pytest.raises(ValueError, match='clock quality guard'):
        BoardMemoryWorker(board, lambda p,c:None, idle=lambda:True)


def test_fragment_boundaries_never_cut_decimal_number_or_protected_name(tmp_path):
    text = '普通背景'*60 + '3.14159265' + '普通背景'*60 + '小林' + '普通背景'*60
    clock = Clock(); store = BoardMemoryStore(tmp_path/'synthetic-numeric-split.sqlite3', clock=clock)
    store.append_event(SCOPE, 'source', 'user_said', text, metadata={'names':['小林']})
    clock.advance(301.)
    prepared = store.prepare_compaction()
    summary = BoardSummaryClient(FragmentClient(), board_boot_id='synthetic-boot')
    summary.metrics = {'input_utf8_bytes':len(text.encode('utf-8'))}
    records = summary._fragments(prepared['sources'])
    pieces = [record[0]['text'] for record in records if 'part_start' in record[0]]
    assert ''.join(pieces) == text
    assert sum('3.14159265' in piece for piece in pieces) == 1
    assert sum('小林' in piece for piece in pieces) == 1


def test_board_origin_migration_requires_explicit_matching_origin_and_sha(tmp_path):
    source = TimelineConversationStore(tmp_path/'synthetic-legacy.sqlite3'); turn(source, 1)
    target = BoardMemoryStore(tmp_path/'synthetic-values-board-mode.sqlite3', clock=lambda:2000., data_origin='board')
    with pytest.raises(LegacyMigrationRejected, match='source_target_origin_mismatch'):
        migrate_legacy_snapshot(source.path, target, expected_sha256=fingerprint(source.path))
    with pytest.raises(LegacyMigrationRejected, match='source_fingerprint_mismatch'):
        migrate_legacy_snapshot(source.path, target, expected_sha256='0'*64, source_data_origin='board')
    assert target.health()['active_bodies'] == 0
    result = migrate_legacy_snapshot(source.path, target, expected_sha256=fingerprint(source.path), source_data_origin='board')
    assert result['production_enabled'] and not result['synthetic_only'] and result['issued_profile_grants'] == 0
    assert migrate_legacy_snapshot(source.path, target, expected_sha256=fingerprint(source.path), source_data_origin='board')['idempotent']


def test_local_profile_catalogue_requires_consent_and_does_not_issue_grant(tmp_path):
    store = BoardMemoryStore(tmp_path/'synthetic-catalogue.sqlite3')
    with pytest.raises(ValueError):
        store.create_profile('合成目录')
    profile_id = store.create_profile('合成目录', consent=True)
    assert store.profiles() == [{'id':profile_id, 'name':'合成目录'}]
    store.require_profile(profile_id)
    with pytest.raises(ValueError):
        store.require_profile('f'*32)
    with pytest.raises(PermissionError):
        store.context({'kind':'profile','id':profile_id})


def test_profile_recent_context_is_partitioned_before_limit_and_long_facts_remain(tmp_path):
    clock = Clock(); access = ProfileAccess('9'*64, clock=clock)
    store = BoardMemoryStore(tmp_path/'synthetic-conversations.sqlite3', clock=clock, profile_access=access)
    profile_id = store.create_profile('合成目录', consent=True)
    _, grant = access.issue(profile_id, {'board_boot_id':'synthetic-boot','session_id':'synthetic-session'})
    scope = {'kind':'profile','id':profile_id,'grant':grant}
    store.correct(scope, '项目', '长期值', operation_id='fact')
    store.begin_turn(scope, 'wanted', '这个会话的问题', generation=1, metadata={'source_id':'conversation:one'})
    store.interrupt('wanted', generation=1)
    for index in range(10):
        clock.advance(1.)
        store.begin_turn(scope, 'other-' + str(index), '另一个会话的问题', generation=1,
                         metadata={'source_id':'conversation:two'})
        store.interrupt('other-' + str(index), generation=1)
    context = store.context(scope, recent_turns=1, context_source_id='conversation:one')
    assert context['messages'] == [{'role':'user','content':'这个会话的问题'}]
    assert context['facts'][0]['value'] == '长期值'
    assert store.context(scope, context_source_id='conversation:empty')['messages'] == []
    assert store.history(scope, search='另一个会话')


def test_profile_continuity_summaries_cannot_cross_conversation_boundary(tmp_path):
    clock = Clock(); access = ProfileAccess('9'*64, clock=clock)
    store = BoardMemoryStore(tmp_path/'synthetic-summary-context.sqlite3', clock=clock, profile_access=access)
    pid = store.create_profile('合成目录', consent=True)
    _, grant = access.issue(pid, {'board_boot_id':'synthetic-boot','session_id':'synthetic-session'})
    scope = {'kind':'profile','id':pid,'grant':grant}
    played(store, clock, 'one', scope=scope, metadata={'source_id':'conversation:one'})
    clock.advance(301.)
    prepared = store.prepare_compaction()
    store.commit_compaction(prepared['task_id'], prepared['lease_token'], candidate(prepared))
    assert store.context(scope, context_source_id='conversation:one')['summaries']
    assert store.context(scope, context_source_id='conversation:two')['summaries'] == []
    played(store, clock, 'two', scope=scope, metadata={'source_id':'conversation:two'})
    played(store, clock, 'three', scope=scope, metadata={'source_id':'conversation:three'})
    clock.advance(301.)
    for _ in range(2):
        separate = store.prepare_compaction(max_events=4)
        assert len({s['metadata']['source_id'] for s in separate['sources'] if s['source'] == 'user_said'}) == 1
        store.commit_compaction(separate['task_id'], separate['lease_token'], candidate(separate))
    assert store.context(scope, context_source_id='conversation:two')['summaries']
    assert store.context(scope, context_source_id='conversation:three')['summaries']
    assert len(store.history(scope)) == 3  # Explicit history still spans all authorized conversations.
