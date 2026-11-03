"""Device-only visual Q&A, real Store dependencies and synthetic TTS receipts."""
import json
import sqlite3
import threading
from types import SimpleNamespace

import pytest

from board.runtime.board_dialogue import BoardDialogueController,SourcedBoardReply
from board.runtime.visual_memory import CameraHealthSample,VisualTimelineWorker,_projection
from board.runtime.visual_policy import (ANSWER_TOPIC,OBSERVATION_TOPIC,LocalVisualQueries,
    historical_reply,requested)
from common.board_memory import BoardMemoryStore,StaleTurn
from common.board_timeline_clock import ClockUnavailable
from common.model_inference_wire import Owner,audio_payload,make_response
from common.profile_access import ProfileAccess


class Mono:
    def __init__(self):
        self.now = 1000.
    def __call__(self):
        return self.now


class Timeline:
    boot_id = 'boot'
    def __init__(self,mono):
        self.monotonic,self.anchored = mono,True
    def event_time(self):
        if not self.anchored:
            raise ClockUnavailable('synthetic_missing_anchor')
        return 1793400000.+self.monotonic()-1000.


class Reader:
    source_kind = 'fixture'
    def __init__(self,clock):
        self.clock,self.frame,self.count = clock,1,1
    def read(self,**kwargs):
        now = self.clock()*1000
        h = dict(board_boot_id='boot',service_epoch='service',camera_epoch='camera',
            role='DPU_YOLOX_PERSON_PREVIEW',detector={'count_kind':'people'},
            timestamp_kind='appsink_dequeue_monotonic',camera_error='',detector_error='',
            observation_frame_id=self.frame,people_count=self.count,observation_age_ms=10,capture_age_ms=5,
            identity={'person_id':'PRIVATE_PERSON'},jpeg_base64='PRIVATE_IMAGE')
        return CameraHealthSample(_projection(h),now,now,'fixture')
    def close(self):
        pass


class Client:
    def __init__(self):
        self.calls = []
    def request(self,kind,payload,**kwargs):
        assert kind == 'tts','Visual queries must never ask a language/vision model'
        self.calls.append((kind,payload))
        return make_response(Owner.from_dict(payload),result={'audio':audio_payload(b'\x01\x00'*2400)})
    def cancel(self,owner):
        pass


@pytest.fixture
def setup(tmp_path):
    clock = Mono()
    timeline = Timeline(clock)
    access = ProfileAccess('a'*64,clock=clock)
    store = BoardMemoryStore(tmp_path/'synthetic-visual-policy.sqlite3',clock=timeline.event_time,profile_access=access)
    reader = Reader(clock)
    worker = VisualTimelineWorker('boot',store,timeline,reader=reader,monotonic=clock,allow_fixture=True)
    policy = LocalVisualQueries(store,worker,timeline)
    client = Client()
    controller = BoardDialogueController(store,client,board_boot_id='boot',
        system_prompt='保持原三字段JSON与中文短回答。',clock=clock)
    value = SimpleNamespace(clock=clock,timeline=timeline,store=store,reader=reader,worker=worker,
        policy=policy,client=client,controller=controller,access=access)
    yield value
    for session,turn in list(controller._active.items()):
        controller.cancel(session,generation=turn.generation)
    worker.close()


def stabilize(value,count=1,start=1000.):
    for frame,stamp in [(1,start),(2,start+.35),(3,start+.7)]:
        value.reader.frame,value.reader.count,value.clock.now = frame,count,stamp
        value.worker.step()


def ask(value,text,generation=1,scope=None):
    job = SimpleNamespace(scope=scope or {'kind':'conversation','id':'PRIVATE_CID'},
        deadline=value.clock()+10,meta={'session_id':'session','generation':generation,
        'request_id':'visual-query-'+str(generation)})
    return value.policy(text,job=job,controller=value.controller,is_current=lambda:True,
                        cancel_event=threading.Event())


def ack(value,plan,complete=True):
    return value.controller.acknowledge(plan,playback_token=plan.playback_token,
        sha256=plan.sha256,samples=plan.samples,complete=complete)


@pytest.mark.parametrize('text',[
    '刚才看到几个人','现在镜头前有几个人','昨天画面里有多少人',
    '你看到了什么','最近5分钟摄像头有没有人','现在有人吗','这是什么颜色',
])
def test_explicit_visual_and_count_questions_are_routed(text):
    assert requested(text)


@pytest.mark.parametrize('text',[
    '我刚才说看到几个人','我们昨天聊了什么','记住我喜欢蓝色',
    '忘记视觉记录','删除昨天的视觉记录','项目有几个人参加','你好',
    '现在有没有人知道这个项目','现在有没有人看到你的错误',
])
def test_other_conversation_and_memory_intents_are_not_stolen(text):
    assert not requested(text)


def test_current_needs_new_fresh_stable_health_and_same_frame_retry_is_frozen(setup):
    value = setup
    assert value.worker.current_observation() is None
    stabilize(value)
    a = value.worker.record_current_observation()
    b = value.worker.record_current_observation()
    assert a == b and a['count'] == 1
    value.clock.now += .8
    assert value.worker.current_observation() is None
    plan = ask(value,'现在镜头前有几个人')
    assert '不能判断' in plan.reply.text and '0' not in plan.reply.text
    ack(value,plan)


def test_current_count_transition_is_not_reported_as_the_old_stable_count(setup):
    value = setup
    stabilize(value)
    value.clock.now += .35
    value.reader.frame,value.reader.count = 4,2
    value.worker.step()
    assert value.worker.current_observation() is None
    plan = ask(value,'现在镜头前有几个人')
    assert '不能判断' in plan.reply.text
    ack(value,plan)


def test_device_normalized_input_and_answer_never_copy_private_question_or_cid(setup):
    value = setup
    stabilize(value)
    private = '汐蓝，我是小明，刚才镜头里有几个人？'
    plan = ask(value,private)
    assert '1个人体目标' in plan.reply.text and len(plan.reply.text)<=48
    assert ack(value,plan)['status'] == 'played'
    assert [kind for kind,_ in value.client.calls] == ['tts']
    assert not value.store.context({'kind':'conversation','id':'PRIVATE_CID'})['messages']
    rows = value.store.history(value.worker.scope,topic=ANSWER_TOPIC)
    canonical = next(row for row in rows if row['source'] == 'device_event')
    assert canonical['text'].startswith('设备查询意图（规范化）：')
    assert {'field':'input_representation','value':'normalized_visual_query'} in canonical['metadata']['claims']
    with sqlite3.connect(value.store.path) as db:
        dump = '\n'.join(db.iterdump())
    assert '小明' not in dump and 'PRIVATE_CID' not in dump and private not in dump
    assert 'PRIVATE_IMAGE' not in dump and 'PRIVATE_PERSON' not in dump
    assert all(row['source']!='user_said' for row in rows)


def test_observation_forget_invalidates_derived_played_reply_without_cross_scope(setup):
    value = setup
    stabilize(value)
    plan = ask(value,'现在镜头前有几个人')
    assert ack(value,plan)['status'] == 'played'
    source = value.worker.record_current_observation()
    value.store.forget(value.worker.scope,event_ids=(source['event_id'],))
    answers = value.store.history(value.worker.scope,topic=ANSWER_TOPIC)
    assert all(row['text'] != plan.reply.text for row in answers)
    assert value.worker.record_current_observation() is None  # Same-frame forgotten tombstone not restored.


def test_forgotten_device_source_revokes_an_unplayed_complete_receipt(setup):
    value = setup
    stabilize(value)
    plan = ask(value,'现在镜头前有几个人')
    source = value.worker.record_current_observation()
    value.store.forget(value.worker.scope,event_ids=(source['event_id'],))
    with pytest.raises(StaleTurn):
        ack(value,plan)
    assert not any(row['source']=='assistant_played'
        for row in value.store.history(value.worker.scope,topic=ANSWER_TOPIC))


def test_same_scope_fact_correction_invalidates_dependent_visual_answer(setup):
    value = setup
    stabilize(value)
    plan = ask(value,'现在镜头前有几个人')
    ack(value,plan)
    source = value.worker.record_current_observation()
    value.store.correct(value.worker.scope,'人数','1',source_event_ids=(source['event_id'],),operation_id='visual-correction1')
    value.store.append_event(value.worker.scope,'new-correction-source','device_event','人工更正为2个目标。')
    value.store.correct(value.worker.scope,'人数','2',source_event_ids=('new-correction-source',),operation_id='visual-correction2')
    assert all(row['text'] != plan.reply.text
        for row in value.store.history(value.worker.scope,topic=ANSWER_TOPIC))


def test_partial_playback_never_records_the_local_reply_as_heard(setup):
    value = setup
    stabilize(value)
    plan = ask(value,'现在画面里有几个人')
    result = ack(value,plan,complete=False)
    assert result['status'] == 'interrupted'
    assert not any(row['source']=='assistant_played'
        for row in value.store.history(value.worker.scope,topic=ANSWER_TOPIC))


def test_historical_reply_cannot_recursively_read_previous_answers(setup):
    value = setup
    stabilize(value)
    one = ask(value,'刚才看到几个人')
    ack(value,one)
    two = ask(value,'刚才看到几个人',generation=2)
    ack(value,two)
    assert one.reply.text == two.reply.text
    public = value.policy.public()
    assert public['last_recall_status']['returned_count'] == 1
    assert public['last_kind'] == 'historical_person_count'


@pytest.mark.parametrize('text',[
    '5分钟前镜头里有几个人','昨天最近5分钟镜头里有几个人',
    '最近5分钟和最近10分钟的视觉人数历史','过去5天的视觉人数历史',
    '2026年10月的视觉人数历史',
])
def test_unsupported_or_ambiguous_past_time_never_becomes_current_or_unbounded_history(setup,text):
    value = setup
    stabilize(value)
    plan = ask(value,text)
    assert '请明确' in plan.reply.text and '1个人体目标' not in plan.reply.text
    assert value.policy.public()['last_kind'] == 'historical_person_count'
    assert value.policy.public()['last_recall_status']['range_rejected']
    ack(value,plan)


def test_chinese_recent_minutes_keeps_the_explicit_selected_range(setup):
    value = setup
    selected = value.policy._range('最近五分钟看到几个人',value.timeline.event_time())
    assert selected['end']-selected['start'] == 300
    assert selected['error'] is None
    assert value.policy._range('最近2天镜头里有几个人',value.timeline.event_time())['error'] is None


def test_fresh_stable_zero_remains_a_detection_limit_not_a_departure_claim(setup):
    value = setup
    stabilize(value,count=0)
    plan = ask(value,'现在镜头前有人吗')
    assert '未检测到' in plan.reply.text and '不能据此断定没人' in plan.reply.text
    assert '离开' not in plan.reply.text and len(plan.reply.text)<=48
    ack(value,plan)


def test_expired_profile_cannot_use_device_route_to_skip_original_admission(setup):
    value = setup
    token,grant = value.access.issue('b'*32,{'board_boot_id':'boot','session_id':'session'})
    value.access.revoke({'board_boot_id':'boot','session_id':'session'})
    with pytest.raises(PermissionError):
        ask(value,'现在镜头前有几个人',scope={'kind':'profile','id':'b'*32,'grant':grant})
    assert not value.client.calls and not value.store.history(value.worker.scope)


def test_history_empty_boundary_limit_and_summary_limits_are_spoken_within_48_chars():
    result = {'items':[],'status':{'boundary_incomplete':True,'result_limited':True}}
    reply = historical_reply(result)
    assert '不等于当时没人' in reply.text and '跨界摘要未列' in reply.text
    assert '结果限量' in reply.text and '细节不可还原' in reply.text and len(reply.text)<=48


def test_only_valid_person_claims_are_used_instead_of_free_summary_text():
    claims = [{'event_id':'camera1','field':key,'value':val} for key,val in
        dict(source='camera_observed',evidence='visual_observation',source_kind='actual',
             event_kind='person_count_observed',people_count=1000).items()]
    result = {'items':[{'source':'timeline_summary','summary_id':'summary1','claims':claims,
        'text':'PRIVATE invented identity and unrelated99 cups'}],
        'status':{'boundary_incomplete':True,'result_limited':True}}
    reply = historical_reply(result)
    assert '1000个人体目标' in reply.text and 'PRIVATE' not in reply.text and '99' not in reply.text
    assert reply.summary_ids == ('summary1',) and len(reply.text)<=48


def test_compacted_visual_summary_and_derived_answer_follow_same_scope_forgetting(setup):
    value = setup
    stabilize(value)
    value.clock.now += 301
    prepared = value.store.prepare_compaction(max_events=1)
    assert prepared
    candidate = dict(schema_version=1,scope=prepared['scope'],topic=prepared['topic'],
        start_utc=prepared['start_utc'],end_utc=prepared['end_utc'],
        source_refs=[{'event_id':s['event_id'],'revision':s['revision']}
                     for s in prepared['sources'] if s['include_in_summary']],
        summary='摄像头观察到1个人体目标。',keywords=['人体'],claims=prepared['required_claims'])
    committed = value.store.commit_compaction(prepared['task_id'],prepared['lease_token'],candidate)
    assert committed['committed']
    plan = ask(value,'刚才看到几个人')
    assert '1个人体目标' in plan.reply.text and '摘要细节不可还原' in plan.reply.text
    ack(value,plan)
    value.store.forget(value.worker.scope,event_ids=(prepared['sources'][0]['event_id'],))
    assert all(row['text'] != plan.reply.text
        for row in value.store.history(value.worker.scope,topic=ANSWER_TOPIC))


def test_unsupported_objects_use_local_bound_capability_reply(setup):
    value = setup
    plan = ask(value,'这是什么颜色')
    assert '仅记录镜头人体目标数量' in plan.reply.text and len(plan.reply.text)<=48
    assert [kind for kind,_ in value.client.calls] == ['tts']
    ack(value,plan)


def test_a_question_about_a_picture_cannot_use_the_live_camera_as_its_source(setup):
    value = setup
    stabilize(value)
    plan = ask(value,'图片里有几个人')
    assert '无法判断' in plan.reply.text and '1个人体目标' not in plan.reply.text
    assert value.policy.public()['last_kind'] == 'unsupported_visual'
    ack(value,plan)


def test_actual_jobs_routes_past_person_count_to_device_policy_before_generic_history(setup):
    from board.runtime.audio.board_dialogue_jobs import BoardDialogueJobs
    value = setup
    stabilize(value)
    jobs = BoardDialogueJobs(value.controller,
        dict(enabled=True,host='192.168.50.1',port=8797,timeout_ms=2000),'boot',
        asr=SimpleNamespace(transcribe=lambda *args,**kwargs:'刚才看到几个人'),
        scope_provider=lambda meta:{'kind':'conversation','id':'PRIVATE_CID'},
        special_handlers={'structured_visual_query':value.policy},
        visual_intent_matcher=value.policy.requested,clock=value.clock,
        wall_clock=value.timeline.event_time,start_worker=False)
    try:
        clip = SimpleNamespace(capture_id='public-fixture',pcm=b'\x10\x00'*3200,
                               audio=SimpleNamespace(sample_count=3200))
        meta = jobs.submit(clip)
        assert jobs.run_next()
        progress = []
        while True:
            item = jobs.poll()
            if item is None:
                break
            progress.append(item)
        complete = next(item['network_complete'] for item in progress if 'network_complete' in item)
        assert '1个人体目标' in complete['reply_text']
        assert [kind for kind,_ in value.client.calls] == ['tts']
        jobs.acknowledge(meta,complete)
        jobs.drain_actions()
        assert jobs.last_ack['committed']
        assert not value.store.context({'kind':'conversation','id':'PRIVATE_CID'})['messages']
        assert value.policy.public()['last_kind'] == 'historical_person_count'
    finally:
        jobs.close()
