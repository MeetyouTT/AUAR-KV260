"""Synthetic end-to-end memory lifecycle checks, using the pinned v24 runtime.

Every narrative, profile, credential and database here is newly fabricated.
The transport is a Python fake; it never opens a socket or calls a model.
"""
import copy
import json
from pathlib import Path
import sqlite3

import pytest

from common.board_memory import BoardMemoryStore, StaleTurn
from common.board_memory_backoff import BoardMemoryBackoffWorker
from common.model_inference_wire import Owner, make_response
from common.profile_access import ProfileAccess, ProfileGrant
from board.runtime.board_memory_policy import BoardContextBuilder, BoardMemoryCommands, BoardSummaryClient

HERE = Path(__file__).resolve().parent
SCOPE = {'kind': 'conversation', 'id': 'synthetic-conversation-a'}
OTHER = {'kind': 'conversation', 'id': 'synthetic-conversation-b'}
DIGEST = 'a'*64
BOOK_INPUT = '合成用户甲计划周末买3本书，尚未购买。'
BOOK_SUMMARY = '合成用户甲计划周末买3本书，尚未购买；助手已完整建议先列书单。'

class Clock:
    def __init__(self, value=1000.): self.value = value
    def __call__(self): return self.value
    def advance(self, seconds): self.value += seconds

class FakeSummaryTransport:
    def __init__(self, text):
        self.text, self.calls = text, []
    def request(self, kind, payload, **options):
        assert kind == 'llm' and payload['task'] == 'summary'
        self.calls.append(copy.deepcopy(payload))
        return make_response(Owner.from_dict(payload), result={'text': json.dumps(
            {'summary': self.text, 'keywords': ['书单']}, ensure_ascii=False)})
    def cancel(self, owner): return None

def played(store, clock, name, text, *, scope=SCOPE, source_id='synthetic-session-a', reply='好的，先列书单。', metadata=None):
    meta = {'source_id': source_id}
    meta.update(metadata or {})
    turn = store.begin_turn(scope, name, text, generation=1, metadata=meta)
    clock.advance(1.)
    store.generated(name, reply, generation=1)
    store.bind_audio_receipt(name, generation=1, playback_token='audio-'+name, sha256=DIGEST, samples=24000)
    clock.advance(1.)
    store.ack_played(name, generation=1, playback_token='audio-'+name, sha256=DIGEST, samples=24000)
    return turn

def candidate(prepared, text):
    return {'schema_version': 1, 'scope': prepared['scope'], 'topic': prepared['topic'],
            'start_utc': prepared['start_utc'], 'end_utc': prepared['end_utc'],
            'source_refs': [{'event_id': source['event_id'], 'revision': source['revision']}
                            for source in prepared['sources'] if source['include_in_summary']],
            'summary': text, 'keywords': ['合成'], 'claims': copy.deepcopy(prepared['required_claims'])}

def compact_all(store, text):
    count = 0
    while (prepared := store.prepare_compaction()) is not None:
        assert store.commit_compaction(prepared['task_id'], prepared['lease_token'], candidate(prepared, text))['committed']
        count += 1
        assert count < 20
    return count

def test_same_conversation_after_five_minutes_uses_durable_summary_in_next_prompt(tmp_path):
    clock = Clock()
    store = BoardMemoryStore(tmp_path/'synthetic-five-minutes.sqlite3', clock=clock)
    played(store, clock, 'synthetic-book-turn', BOOK_INPUT,
           metadata={'names': ['合成用户甲'], 'numbers': [3], 'negated': True, 'status': 'planned'})
    transport = FakeSummaryTransport(BOOK_SUMMARY)
    summary = BoardSummaryClient(transport, board_boot_id='offline-boot', clock=clock)
    worker = BoardMemoryBackoffWorker(store, summary, idle=lambda: True, retry_clock=clock)
    clock.advance(299.)
    assert worker.step() is False and transport.calls == []
    assert store.health()['active_bodies'] == 2
    clock.advance(1.)
    assert worker.step() is True
    assert len(transport.calls) == 1 and summary.metrics['complete_source_coverage'] is True
    assert store.health()['active_bodies'] == 0 and store.health()['valid_summaries'] == 1
    context = store.context(SCOPE, context_source_id='synthetic-session-a')
    assert context['messages'] == [] and context['summaries'][0]['text'] == BOOK_SUMMARY
    assert store.context(SCOPE, context_source_id='synthetic-other-session')['summaries'] == []
    found = store.history_with_status(SCOPE, search='书单')
    assert len(found['items']) == 1 and found['items'][0]['source'] == 'timeline_summary'
    assert found['items'][0]['detail_available'] is False
    builder = BoardContextBuilder('你是离线合成助手，按已有资料继续对话。')
    prompt = builder(context, '接着说刚才的书单')
    encoded = json.dumps(prompt, ensure_ascii=False)
    assert '合成用户甲' in encoded and '3本书' in encoded and '尚未购买' in encoded
    assert sum('合成用户甲' in message['content'] for message in prompt) == 1
    assert store.history(OTHER, search='书单') == []

def test_explicit_correction_and_forget_invalidate_old_summary_and_dependencies(tmp_path):
    clock = Clock()
    store = BoardMemoryStore(tmp_path/'synthetic-correction.sqlite3', clock=clock)
    source = store.append_event(SCOPE, 'synthetic-old-source', 'user_said', '离线合成旧项目')
    store.correct(SCOPE, '项目', '离线合成旧项目', source_event_ids=[source['event_id']], operation_id='synthetic-old')
    clock.advance(301.)
    assert compact_all(store, '用户明确记录项目是离线合成旧项目。') == 2
    assert store.history(SCOPE, search='离线合成旧项目')
    handler = BoardMemoryCommands(store)
    turn = store.begin_turn(SCOPE, 'synthetic-correct-command', '把我的项目改成离线合成新项目', generation=2)
    reply = handler('把我的项目改成离线合成新项目', SCOPE, turn_id='synthetic-correct-command', generation=2,
                    user_event_id=turn['user_event_id'])
    assert '离线合成新项目' in reply.text
    assert store.context(SCOPE)['facts'] == [{'key': '项目', 'revision': 2, 'value': '离线合成新项目'}]
    assert '离线合成旧项目' not in json.dumps(store.history(SCOPE, search='离线合成旧项目'), ensure_ascii=False)
    store.generated('synthetic-correct-command', reply.text, generation=2,
                    source_event_ids=[turn['user_event_id']], provenance_complete=True)
    store.bind_audio_receipt('synthetic-correct-command', generation=2, playback_token='synthetic-old-audio', sha256=DIGEST, samples=24000)
    forgetting = store.begin_turn(SCOPE, 'synthetic-forget-command', '忘记项目', generation=3)
    confirmed = handler('忘记项目', SCOPE, turn_id='synthetic-forget-command', generation=3,
                        user_event_id=forgetting['user_event_id'])
    assert '已忘记' in confirmed.text and store.context(SCOPE)['facts'] == []
    assert '离线合成新项目' not in json.dumps(store.history(SCOPE, search='离线合成新项目'), ensure_ascii=False)
    with pytest.raises(StaleTurn):
        store.ack_played('synthetic-correct-command', generation=2, playback_token='synthetic-old-audio', sha256=DIGEST, samples=24000)
    with sqlite3.connect(store.path) as db:
        assert db.execute("SELECT count(*) FROM bm_summaries WHERE state='valid'").fetchone()[0] == 0
        assert db.execute('SELECT count(*) FROM bm_summary_keywords').fetchone()[0] == 0

def test_profile_conversation_continuity_is_partitioned_but_authorized_facts_are_profile_wide(tmp_path):
    clock = Clock()
    access = ProfileAccess('9'*64, clock=clock)
    access.authenticate('9'*64)
    _, first = access.issue('a'*32, {'board_boot_id': 'offline-boot', 'session_id': 'synthetic-session-a'})
    _, second = access.issue('a'*32, {'board_boot_id': 'offline-boot', 'session_id': 'synthetic-session-b'})
    a = {'kind': 'profile', 'id': 'a'*32, 'grant': first}
    b = {'kind': 'profile', 'id': 'a'*32, 'grant': second}
    store = BoardMemoryStore(tmp_path/'synthetic-profile-partitions.sqlite3', clock=clock, profile_access=access)
    played(store, clock, 'synthetic-profile-a', '合成会话甲讨论书单', scope=a, source_id='synthetic-session-a')
    played(store, clock, 'synthetic-profile-b', '合成会话乙讨论天气', scope=b, source_id='synthetic-session-b')
    clock.advance(301.)
    prepared = store.prepare_compaction()
    assert store.commit_compaction(prepared['task_id'], prepared['lease_token'], candidate(prepared, '合成会话甲讨论书单'))['committed']
    prepared = store.prepare_compaction()
    assert store.commit_compaction(prepared['task_id'], prepared['lease_token'], candidate(prepared, '合成会话乙讨论天气'))['committed']
    store.correct(a, '项目', '离线合成个人事实', operation_id='synthetic-profile-fact')
    one = store.context(a, context_source_id='synthetic-session-a')
    two = store.context(b, context_source_id='synthetic-session-b')
    assert one['summaries'][0]['text'] == '合成会话甲讨论书单'
    assert two['summaries'][0]['text'] == '合成会话乙讨论天气'
    assert one['facts'] == two['facts'] and one['facts'][0]['value'] == '离线合成个人事实'
    assert store.context(SCOPE)['facts'] == [] and store.history(SCOPE, search='合成会话甲') == []
    assert store.history(a, search='合成会话乙')  # Explicit, authorized profile-wide history is intentional.

def test_profile_forged_wrong_expired_and_revoked_grants_are_denied(tmp_path):
    clock = Clock()
    access = ProfileAccess('9'*64, clock=clock)
    with pytest.raises(PermissionError): access.authenticate('8'*64)
    access.authenticate('9'*64)
    actor = {'board_boot_id': 'offline-boot', 'session_id': 'synthetic-session-a'}
    _, grant = access.issue('a'*32, actor, ttl=30)
    store = BoardMemoryStore(tmp_path/'synthetic-live-grants.sqlite3', clock=clock, profile_access=access)
    scope = {'kind': 'profile', 'id': 'a'*32, 'grant': grant}
    store.correct(scope, '项目', '离线合成个人事实', operation_id='synthetic-private')
    copy_grant = ProfileGrant(grant.profile_id, grant.actor, grant.nonce, grant.until)
    for bad in ({'kind': 'profile', 'id': 'a'*32}, dict(scope, grant=copy_grant), dict(scope, id='b'*32)):
        with pytest.raises(PermissionError): store.context(bad)
    store.append_event(SCOPE, 'synthetic-visible-face', 'device_event', '合成已知人脸与声纹候选', metadata={'speaker_known': True})
    with pytest.raises(PermissionError): store.context({'kind': 'profile', 'id': 'a'*32})
    clock.advance(30.)
    with pytest.raises(PermissionError): store.context(scope)
    _, live = access.issue('a'*32, actor)
    assert store.context(dict(scope, grant=live))['facts']
    access.revoke(actor)
    with pytest.raises(PermissionError): store.context(dict(scope, grant=live))

def test_rejected_summary_backoff_retains_body_then_valid_retry_recovers(tmp_path):
    clock = Clock()
    store = BoardMemoryStore(tmp_path/'synthetic-summary-retry.sqlite3', clock=clock)
    played(store, clock, 'synthetic-retry-turn', BOOK_INPUT,
           metadata={'names': ['合成用户甲'], 'numbers': [3], 'negated': True, 'status': 'planned'})
    clock.advance(300.)
    transport = FakeSummaryTransport('合成用户甲已经买4本书。')
    summary = BoardSummaryClient(transport, board_boot_id='offline-boot', clock=clock)
    worker = BoardMemoryBackoffWorker(store, summary, idle=lambda: True, retry_clock=clock)
    assert worker.step() is False
    assert store.health()['active_bodies'] == 2 and store.health()['valid_summaries'] == 0
    assert worker.health()['retry_backoff']['failure_streak'] == 1
    assert worker.health()['retry_backoff']['last_delay_seconds'] == 3.
    attempts = len(transport.calls)
    transport.text = BOOK_SUMMARY
    assert worker.step() is False and len(transport.calls) == attempts
    clock.advance(3.001)
    assert worker.step() is True
    assert store.health()['active_bodies'] == 0 and store.health()['valid_summaries'] == 1
    assert worker.health()['retry_backoff']['failure_streak'] == 0
    assert store.history(SCOPE, search='书单')[0]['text'] == BOOK_SUMMARY

def test_seed_only_synthetic_persistence_fixture_for_a_fresh_python_process():
    work = HERE/'test_work'
    path = work/'synthetic-persistent.sqlite3'
    assert not path.exists()
    clock = Clock()
    access = ProfileAccess('9'*64, clock=clock)
    access.authenticate('9'*64)
    _, grant = access.issue('a'*32, {'board_boot_id': 'offline-boot', 'session_id': 'offline-session'})
    store = BoardMemoryStore(path, clock=clock, profile_access=access)
    scope = {'kind': 'conversation', 'id': 'synthetic-persistent-conversation'}
    played(store, clock, 'synthetic-durable-books', '离线合成书单', scope=scope)
    store.correct(scope, '项目', '离线合成新项目', operation_id='synthetic-durable-fact')
    store.correct({'kind': 'profile', 'id': 'a'*32, 'grant': grant}, '项目', '离线合成个人事实', operation_id='synthetic-durable-profile')
    clock.advance(301.)
    assert compact_all(store, '离线合成书单，离线合成新项目，离线合成个人事实。') == 3
    assert store.health()['active_bodies'] == 0
    (work/'persistence_fixture.json').write_text(json.dumps({'old_grant_nonce': grant.nonce,
        'all_data_synthetic': True, 'real_profile_or_credential_used': False})+'\n', encoding='utf-8')
