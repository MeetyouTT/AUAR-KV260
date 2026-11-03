"""Synthetic controller tests: no private store, model host, devices or PCM I/O."""
import hashlib
import json
from pathlib import Path
import sys
import threading

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from board.runtime.board_dialogue import (
    BoardDialogueController, BoardReply, ReplyRejected, StaleGeneration,
    split_sentences, validate_model_reply,
)
from common.model_inference_wire import Owner, audio_payload, make_response


class Clock:
    def __init__(self): self.now = 10.0
    def __call__(self): return self.now


class Store:
    def __init__(self):
        self.rows, self.events, self.history_calls = {}, [], []
    def preempt_compaction(self): self.events.append('preempt')
    def begin_turn(self, scope, turn_id, user_text, *, generation, metadata):
        if scope.get('kind') != 'conversation': raise PermissionError('No grant')
        self.rows[turn_id] = dict(scope=scope, user=user_text, generation=generation, status='pending')
        self.events.append('begin')
        return dict(user_event_id='user-event-'+turn_id)
    def context(self, scope):
        self.events.append('context')
        return dict(messages=[dict(role='user', content='早上好')], facts=[])
    def history(self, scope, **query):
        self.history_calls.append((scope, query)); return [dict(text='昨天计划买三本书，尚未购买',
            scope={'kind':'profile','id':'private-internal-profile-id'},event_id='private-source-id')]
    def generated(self, turn_id, text, *, generation, **provenance):
        row = self.rows[turn_id]; assert row['generation'] == generation
        row.update(assistant=text, status='generated'); self.events.append('generated')
    def bind_audio_receipt(self, turn_id, **receipt):
        self.rows[turn_id]['receipt'] = receipt; self.events.append('bound')
    def ack_played(self, turn_id, **receipt):
        row=self.rows[turn_id]
        assert {k:v for k,v in receipt.items() if k!='complete'} == row['receipt']
        row['status']='played' if receipt['complete'] else 'interrupted'
        return dict(status=row['status'])
    def interrupt(self, turn_id, *, generation, reason):
        self.rows[turn_id]['status']='interrupted'; self.events.append('interrupt')


class Models:
    def __init__(self, clock=None, reply=None):
        self.calls, self.cancelled = [], []
        self.clock, self.reply = clock, reply or '我会陪你慢慢聊。今天有什么新鲜事？'
        self.hook = None
    def request(self, kind, payload, **kwargs):
        self.calls.append((kind,payload,kwargs))
        if self.hook: return self.hook(kind,payload,kwargs)
        owner=Owner.from_dict(payload)
        if kind=='llm':
            text=json.dumps(dict(reply_text=self.reply,emotion='friendly',avatar_action=''),ensure_ascii=False)
            result=dict(text=text)
        else: result=dict(audio=audio_payload(b'\x01\x00'*160,24000))
        if self.clock: self.clock.now += .1
        return make_response(owner,result=result)
    def cancel(self, owner): self.cancelled.append(owner)


def setup(**kwargs):
    clock=Clock(); store=Store(); models=Models(clock)
    controller=BoardDialogueController(store,models,board_boot_id='synthetic-boot',
        system_prompt='测试人设：只返回reply_text/emotion/avatar_action三字段JSON',clock=clock,**kwargs)
    return controller,store,models,clock


def prepare(controller, generation=1, **kwargs):
    return controller.prepare_text('今天有点累',scope={'kind':'conversation','id':'synthetic-session'},
        session_id='synthetic-session',generation=generation,budget_ms=3000,**kwargs)


def ack(controller, plan, **kwargs):
    values=dict(playback_token=plan.playback_token,sha256=plan.sha256,samples=plan.samples)
    values.update(kwargs)
    return controller.acknowledge(plan,**values)


def test_order_receipt_and_complete_ack():
    controller,store,models,_=setup()
    plan=prepare(controller)
    assert [kind for kind,_,_ in models.calls] == ['llm','tts','tts']
    assert store.events == ['preempt','begin','context','generated','bound']
    assert plan.sha256 == hashlib.sha256(plan.pcm).hexdigest()
    assert plan.samples*2 == len(plan.pcm)
    assert not controller.idle
    assert store.rows[plan.turn_id]['status']=='generated'
    assert ack(controller,plan)['status']=='played'
    assert controller.idle
    with pytest.raises(StaleGeneration): ack(controller,plan)


@pytest.mark.parametrize('change',[{'samples':1},{'sha256':'0'*64},{'playback_token':'wrong'},{'samples':True}])
def test_partial_or_foreign_ack_cannot_become_heard(change):
    controller,store,_,_=setup(); plan=prepare(controller)
    with pytest.raises(ValueError): ack(controller,plan,**change)
    assert store.rows[plan.turn_id]['status']=='generated'
    assert not controller.idle


def test_cancel_and_new_generation_reject_late_playback():
    controller,store,_,_=setup(); old=prepare(controller)
    new=prepare(controller,generation=2)
    assert store.rows[old.turn_id]['status']=='interrupted'
    with pytest.raises(StaleGeneration): ack(controller,old)
    assert ack(controller,new)['status']=='played'
    with pytest.raises(StaleGeneration): prepare(controller,generation=2)


def test_explicit_incomplete_ack_closes_without_heard():
    controller,store,_,_=setup(); plan=prepare(controller)
    ack(controller,plan,complete=False)
    assert store.rows[plan.turn_id]['status']=='interrupted' and controller.idle


def test_deadline_is_not_renewed_between_llm_and_tts():
    controller,_,models,_=setup(); prepare(controller)
    assert len({call[2]['deadline'] for call in models.calls})==1
    budgets=[call[1]['budget_ms'] for call in models.calls]
    assert all(a>b for a,b in zip(budgets,budgets[1:]))
    owners=[Owner.from_dict(call[1]) for call in models.calls]
    assert len(set(o.request_id for o in owners))==3
    assert all((o.board_boot_id,o.session_id,o.generation)==('synthetic-boot','synthetic-session',1) for o in owners)


def test_stale_response_owner_is_rejected_before_tts():
    controller,store,models,_=setup()
    def hook(kind,payload,kwargs):
        other=dict(payload,generation=0)
        return make_response(Owner.from_dict(other),result=dict(text='{}'))
    models.hook=hook
    with pytest.raises(ValueError): prepare(controller)
    assert [kind for kind,_,_ in models.calls]==['llm']
    assert next(iter(store.rows.values()))['status']=='interrupted'


def test_model_failure_preserves_user_and_never_emits_ack():
    controller,store,models,_=setup()
    def hook(kind,payload,kwargs):
        return make_response(Owner.from_dict(payload),error='busy',retryable=True)
    models.hook=hook
    with pytest.raises(RuntimeError): prepare(controller)
    row=next(iter(store.rows.values()))
    assert row['user']=='今天有点累' and row['status']=='interrupted'
    assert 'receipt' not in row and controller.idle


def test_history_only_on_explicit_board_query():
    controller,store,models,_=setup(); plan=prepare(controller); ack(controller,plan)
    assert store.history_calls==[]
    prepare(controller,generation=2,history_query={'topic':'买书','limit':2})
    assert len(store.history_calls)==1
    assert store.history_calls[0][0]['id']=='synthetic-session'
    assert '尚未购买' in str(models.calls[-3][1]['messages'])
    assert 'private-internal-profile-id' not in str(models.calls[-3][1]['messages'])
    assert 'private-source-id' not in str(models.calls[-3][1]['messages'])


def test_profile_candidate_does_not_grant_scope():
    controller,store,models,_=setup()
    with pytest.raises(PermissionError):
        controller.prepare_text('我的名字是什么',scope={'kind':'profile','id':'candidate-face'},
            session_id='synthetic-session',generation=1,budget_ms=1000)
    assert not models.calls and not store.rows and controller.idle


def test_asr_receives_original_deadline_then_only_text_crosses_wire():
    class Asr:
        def transcribe(self,pcm,**kwargs):
            assert pcm==b'\0\0'*100
            assert kwargs['sample_rate']==16000 and kwargs['deadline']==13
            return '今天有点累'
    controller,_,models,_=setup(asr=Asr())
    controller.prepare_pcm(b'\0\0'*100,scope={'kind':'conversation','id':'synthetic-session'},
        session_id='synthetic-session',generation=1,budget_ms=3000)
    assert all('pcm' not in payload and 'scope' not in payload for _,payload,_ in models.calls)


def test_cancellation_during_model_request_discards_result():
    controller,store,models,_=setup()
    def hook(kind,payload,kwargs):
        controller.cancel('synthetic-session',generation=1)
        return make_response(Owner.from_dict(payload),result=dict(text='{}'))
    models.hook=hook
    with pytest.raises(StaleGeneration): prepare(controller)
    assert len(models.cancelled)==1
    assert next(iter(store.rows.values()))['status']=='interrupted'
    assert controller.idle


def test_question_echo_correction_has_one_attempt_and_same_deadline():
    controller,_,models,_=setup(); count=[0]
    def hook(kind,payload,kwargs):
        if kind=='llm':
            count[0]+=1
            text='今天的天气怎么样我应该穿什么' if count[0]==1 else '出门前看一下天气预报吧。'
            return make_response(Owner.from_dict(payload),result=dict(text=json.dumps(dict(
                reply_text=text,emotion='friendly',avatar_action=''),ensure_ascii=False)))
        return make_response(Owner.from_dict(payload),result=dict(audio=audio_payload(b'\0\0'*10)))
    models.hook=hook
    plan=controller.prepare_text('今天的天气怎么样我应该穿什么',scope={'kind':'conversation','id':'synthetic-session'},
        session_id='synthetic-session',generation=1,budget_ms=3000)
    assert count[0]==2 and plan.reply.text=='出门前看一下天气预报吧。'
    assert len({kwargs['deadline'] for _,_,kwargs in models.calls})==1


@pytest.mark.parametrize('raw',['思考过程','{"reply_text":"你好"}',
    '{"reply_text":"你好","emotion":"friendly","avatar_action":"move_servo"}',
    '{"reply_text":"<think>秘密</think>","emotion":"neutral","avatar_action":""}'])
def test_unvalidated_model_fields_never_become_speech(raw):
    with pytest.raises(ReplyRejected): validate_model_reply(raw,'你好')


def test_segmentation_preserves_order_and_wire_bound():
    text='好。'+('这是长度可控的完整短语，'*30)+'！'
    sentences=split_sentences(text)
    assert ''.join(sentences)==text and max(map(len,sentences))<=220
    with pytest.raises(ReplyRejected):split_sentences('长'*241)


def test_memory_control_hook_stays_board_local():
    controller,store,models,_=setup(command_handler=lambda text,scope,**kwargs:BoardReply('已记下这次更正。'))
    prepare(controller)
    assert [kind for kind,_,_ in models.calls]==['tts']
    assert 'context' not in store.events


def test_visual_event_uses_only_injected_sink():
    seen=[]
    controller,_,_,_=setup(visual_event_sink=lambda event:seen.append(event))
    controller.append_visual_event({'kind':'person_visible','count':1})
    assert seen==[{'kind':'person_visible','count':1}]


def test_actual_candidate_store_uses_verified_playback_only(tmp_path):
    from common.board_memory import BoardMemoryStore
    clock=Clock();store=BoardMemoryStore(tmp_path/'synthetic.db',clock=lambda:1000.)
    models=Models(clock)
    controller=BoardDialogueController(store,models,board_boot_id='synthetic-boot',
        system_prompt='测试',clock=clock)
    scope={'kind':'conversation','id':'synthetic-session'}
    plan=prepare(controller)
    assert all(m['role']!='assistant' for m in store.context(scope)['messages'])
    ack(controller,plan)
    assert any(m['role']=='assistant' for m in store.context(scope)['messages'])
    next_plan=prepare(controller,generation=2)
    store.forget(scope,event_ids=[store.context(scope)['event_refs'][0]['event_id']])
    with pytest.raises((ValueError,PermissionError)):ack(controller,next_plan)
    assert controller.cancel('synthetic-session',generation=2)


def test_preempt_storage_failure_leaves_no_active_controller():
    controller,store,models,_=setup()
    def fail():raise RuntimeError('synthetic storage fault')
    store.preempt_compaction=fail
    with pytest.raises(RuntimeError):prepare(controller)
    assert controller.idle and not models.calls


def test_transport_failure_has_bounded_best_effort_remote_cancel():
    controller,store,models,_=setup()
    def fail(kind,payload,kwargs):raise TimeoutError('synthetic timeout')
    models.hook=fail
    with pytest.raises(TimeoutError):prepare(controller)
    assert len(models.cancelled)==1
    assert next(iter(store.rows.values()))['status']=='interrupted'
