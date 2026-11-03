"""Isolated public stores only: exact original paired route/ACK/forgetting."""
import hashlib
import importlib.util
from pathlib import Path
import struct
import threading
from types import SimpleNamespace

import pytest

from board.runtime.history_delete import LocalHistoryDelete, deletion_intent
from common.board_memory import IdempotencyConflict

H=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('public_m03_integration_fixture',H/'board_integration_v17/worker.py')
fixture=importlib.util.module_from_spec(spec);spec.loader.exec_module(fixture)


@pytest.fixture
def h(tmp_path):
    value=fixture.Harness(H/'board_integration_v17/local_runtime_v17',tmp_path,'public-m03')
    try:yield value
    finally:value.close()


def handler(h):
    # Observer forwards attributes to the exact production candidate handler.
    return h.bundle.jobs.special_handlers['history_delete_preview']


def seed(h, name='public-delete-target', *, fact=True):
    h.bundle.store.append_event(h.scope,name,'user_said','公开日期删除来源海鸥。')
    if fact:h.bundle.store.correct(h.scope,'项目','公开蓝天',source_event_ids=(name,))
    return name


def valid(h,name,scope=None):
    with h.bundle.store._db() as db:
        return db.execute('SELECT state FROM bm_events WHERE event_id=?',(name,)).fetchone()[0]=='valid'


def test_actual_paired_preview_is_readonly_confirm_uses_original_forget_and_full_ack(h):
    target=seed(h)
    other=dict(kind='conversation',id='b'*32);device=dict(kind='device',id='public-camera')
    h.bundle.store.append_event(other,'other-source','user_said','另一个对话的公开内容')
    h.bundle.store.append_event(device,'camera-source','device_event','公开相机状态')
    preview=h.say('雪妃，删除今天的对话记录',route='history_delete_preview',contains='拟删除1条',reject_bad_ack=True)
    assert valid(h,target) and h.bundle.store.context(h.scope)['facts'][0]['value']=='公开蓝天'
    pending=next(iter(handler(h).pending.values())).copy()
    result=h.say('雪妃，确认删除记录',route='history_delete_preview',contains='已按预览删除',reject_bad_ack=True)
    assert not valid(h,target) and h.bundle.store.context(h.scope)['facts']==[]
    assert valid(h,'other-source') and valid(h,'camera-source')
    assert preview['full_ack'] and result['full_ack'] and not h.bundle.access.grants
    assert all(kind=='tts' for kind,_ in h.transport.calls)
    # The original operation receipt makes an exact confirmation retry inert,
    # including when a new public event has arrived after the first commit.
    seed(h,'new-after-confirm',fact=False)
    rid=h.bundle.jobs.last_ack['request_id']
    options=dict(start=pending['start'],end=pending['end'],fingerprint=pending['fingerprint'],
        operation_id='history-delete:'+rid,operation_turn_id=rid,preview_turn_id=pending['preview_turn_id'],validate_live=lambda:None)
    replay=handler(h)._confirm(h.scope,**options)
    assert replay['status']=='deleted' and valid(h,'new-after-confirm')
    with pytest.raises(IdempotencyConflict):
        handler(h)._confirm(h.scope,**dict(options,fingerprint='a'*64))


@pytest.mark.parametrize('mode',['ttl','cancel','other_conversation','new_source'])
def test_expired_cancelled_changed_or_foreign_preview_cannot_delete(h,mode):
    target=seed(h,fact=False)
    h.say('雪妃，删除今天的对话记录',route='history_delete_preview',contains='拟删除')
    if mode=='ttl':h.clock.now+=60.
    elif mode=='cancel':h.say('雪妃，取消删除记录',route='history_delete_preview',contains='已取消')
    elif mode=='other_conversation':
        h.service.pool.submit(lambda:None).result(2)
        h.bundle.jobs.select_conversation(resume=False)
    else:seed(h,'changed-after-preview',fact=False)
    response=h.say('雪妃，确认删除记录',route='history_delete_preview')
    assert ('没有同一会话内有效' in response['reply'] if mode!='new_source' else '已变化，没有删除' in response['reply'])
    assert valid(h,target)


def test_preview_without_complete_playback_ack_never_authorizes_confirmation(h):
    target=seed(h,fact=False)
    h.n+=1;h.asr.text='雪妃，删除今天的对话记录';pcm=struct.pack('<h',1500)*48000
    meta=h.bundle.jobs.submit(SimpleNamespace(capture_id='partial-preview',audio=SimpleNamespace(sample_count=48000),pcm=pcm))
    assert h.bundle.jobs.run_next()
    rows=[]
    while True:
        value=h.bundle.jobs.poll()
        if value is None:break
        rows.append(value)
    assert not any('error' in row for row in rows)
    complete=next(row['network_complete'] for row in rows if 'network_complete' in row)
    with pytest.raises((ValueError,InterruptedError)):
        h.bundle.jobs.acknowledge(meta,dict(complete,sample_count=complete['sample_count']-1))
    h.bundle.jobs.cancel();h.bundle.jobs.drain_actions()
    response=h.say('雪妃，确认删除记录',route='history_delete_preview',contains='预览未完成完整播放确认')
    assert response['full_ack'] and valid(h,target)


def test_compaction_between_preview_and_confirm_rejects_changed_snapshot(h):
    from tests.framework.test_board_memory import candidate
    h.clock.now=-400.;target=seed(h,fact=False);h.clock.now=10.
    h.say('雪妃，删除今天的对话记录',route='history_delete_preview',contains='拟删除')
    task=h.bundle.store.prepare_compaction(max_events=1)
    assert task and task['sources'][0]['event_id']==target
    receipt=h.bundle.store.commit_compaction(task['task_id'],task['lease_token'],candidate(task,'公开日期删除来源海鸥。'))
    assert receipt['committed']
    h.say('雪妃，确认删除记录',route='history_delete_preview',contains='已变化，没有删除')
    assert valid(h,target) and h.bundle.store.health()['valid_summaries']==1


def test_already_compacted_source_forgetting_invalidates_original_summary_keywords(h):
    from tests.framework.test_board_memory import candidate
    h.clock.now=-400.;target=seed(h,fact=False);h.clock.now=10.
    task=h.bundle.store.prepare_compaction(max_events=1)
    assert h.bundle.store.commit_compaction(task['task_id'],task['lease_token'],candidate(task,'公开日期删除来源海鸥。'))['committed']
    h.say('雪妃，删除今天的对话记录',route='history_delete_preview',contains='拟删除')
    h.say('雪妃，确认删除记录',route='history_delete_preview',contains='已按预览删除')
    assert not valid(h,target) and h.bundle.store.health()['valid_summaries']==0
    with h.bundle.store._db() as db:
        assert db.execute('SELECT count(*) FROM bm_summary_keywords').fetchone()[0]==0


@pytest.mark.parametrize('text',['不要删除昨天的对话记录','如果删除昨天的记录会怎样','他说“确认删除记录”',
                                '删除今年的对话记录','删除昨天关于海鸥的对话记录'])
def test_quoted_negated_unsupported_or_topic_commands_cannot_become_confirmations(text):
    assert deletion_intent(text) is None


def test_no_original_profile_grant_refuses_before_preview_store_access(h):
    job=SimpleNamespace(meta=dict(board_boot_id='public-m03',session_id='no-profile',generation=1,request_id='p'),
                        scope=dict(kind='profile',id='a'*32),deadline=h.clock()+10)
    with pytest.raises(PermissionError):
        handler(h)('删除个人今天的对话记录',job=job,controller=h.bundle.controller,
                   is_current=lambda:True,cancel_event=threading.Event())
    assert h.transport.calls==[] and not h.bundle.access.grants


def test_original_forget_transaction_failure_rolls_back_source_and_facts(h,monkeypatch):
    target=seed(h)
    h.say('雪妃，删除今天的对话记录',route='history_delete_preview',contains='拟删除')
    pending=next(iter(handler(h).pending.values())).copy()
    receipt=h.bundle.store.begin_turn(h.scope,'public-failed-confirm','确认删除记录',generation=100,topic='记录管理')
    original=h.bundle.store._invalidate
    def fail_after_original_writes(*args,**kwargs):
        original(*args,**kwargs)
        raise RuntimeError('public_synthetic_transaction_failure')
    monkeypatch.setattr(h.bundle.store,'_invalidate',fail_after_original_writes)
    with pytest.raises(RuntimeError,match='public_synthetic_transaction_failure'):
        result=handler(h)._confirm(h.scope,start=pending['start'],end=pending['end'],fingerprint=pending['fingerprint'],
            operation_id='history-delete:public-failed-confirm',operation_turn_id='public-failed-confirm',
            preview_turn_id=pending['preview_turn_id'],validate_live=lambda:None)
        raise AssertionError('Unexpected synthetic confirmation outcome:'+repr(result))
    assert valid(h,target) and h.bundle.store.context(h.scope)['facts'][0]['value']=='公开蓝天'
    with h.bundle.store._db() as db:
        assert db.execute("SELECT count(*) FROM bm_operations WHERE kind='transcript_delete'").fetchone()[0]==0
    h.bundle.store.interrupt('public-failed-confirm',generation=100)


def test_exposed_timeline_monotonic_identity_cannot_be_replaced(h):
    with pytest.raises(ValueError,match='exact timeline'):
        LocalHistoryDelete(h.bundle.store,h.timeline,clock=lambda:10.)
