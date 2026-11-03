"""Root public failures reproduced and fixed at the actual bound board route."""
import importlib.util
import json
from pathlib import Path
import struct
from types import SimpleNamespace

import pytest

HERE=Path(__file__).resolve().parents[1]


def audit_module():
    spec=importlib.util.spec_from_file_location('feature_v2_audit',HERE/'audit_routes.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('text,expected',[
    ('你现在能确定我手里是什么物品吗？','structured_visual_query'),
    ('你已经帮我把声纹登记保存成功了吗？','speaker_identity'),
    ('你现在能确定镜头前的人就是正在说话的我吗？','structured_visual_query'),
    ('摄像头刚才断线了，这能证明现在没有人吗？','structured_visual_query'),
])
def test_four_actual_public_questions_have_controlled_paired_routes(text,expected):
    audit=audit_module();route,_=audit.route_function(HERE/'candidate_v2/after/tools/yuki_jobs_candidate.py')
    result=audit.probe(route,text)
    assert result['error'] is None and result['route']==expected


@pytest.mark.parametrize('text',[
    '你已经帮我把声纹登记保存成功了吗？','我的声纹保存成功了吗','声纹登记成功了吗',
    '你刚才给我把声纹保存好了吗',
])
def test_save_status_is_only_a_query_not_enrollment_or_confirmation(text):
    from common.feature_intents import speaker_text,speaker_query_requested
    assert speaker_text(text)=='查询声纹保存状态'
    assert speaker_query_requested(text)


@pytest.mark.parametrize('relative',['tools/yuki_jobs_candidate.py','board/runtime/audio/board_dialogue_jobs.py'])
def test_status_precedes_active_enrollment_intent(relative):
    audit=audit_module();route,_=audit.route_function(HERE/'candidate_v2/after'/relative)
    result=audit.probe(route,'你已经帮我把声纹登记保存成功了吗？',active=True)
    assert result['route']=='speaker_identity'


@pytest.mark.parametrize('invalidate',['expired','revision_changed','restart','cancel_new_attempt'])
def test_save_receipt_invalidation_means_unknown_not_unsaved(tmp_path,invalidate):
    from tools.speaker_device import SpeakerDevice
    from tests.framework.test_board_business import Clock
    from tests.framework.test_board_speaker_business import Encoder,quality,capture
    clock=Clock();path=tmp_path/'public-fake-speaker.sqlite3'
    device=SpeakerDevice(Encoder(),path,clock=clock,quality=quality)
    generation=0
    def say(text):
        nonlocal generation
        generation+=1;meta,raw=capture(generation)
        return device.turn(meta,text,raw)
    question='你已经帮我把声纹登记保存成功了吗？'
    try:
        say('登记我的声纹，我叫测试甲')
        for _ in range(3):say('不同的公开合成句子')
        assert '已保存' in say('确认保存声纹')
        assert '已收到声纹保存提交回执' in say(question)
        if invalidate=='expired':clock.now+=60.1
        elif invalidate=='revision_changed':
            with device.store.db:
                device.store.db.execute("UPDATE metadata SET value=value+1 WHERE key='revision'")
        elif invalidate=='restart':
            device.store.close()
            device=SpeakerDevice(Encoder(),path,clock=clock,quality=quality)
        else:
            say('登记我的声纹，我叫测试乙')
            say('取消声纹登记')
        answer=say(question)
        assert '不能判断' in answer and '没有可核对' in answer
        assert '未保存' not in answer and '设置' not in answer
        assert len(device.store.people())==1
    finally:
        device.store.close()


def test_failed_original_save_transaction_cannot_create_success_receipt(tmp_path,monkeypatch):
    from tools.speaker_device import SpeakerDevice
    from tests.framework.test_board_business import Clock
    from tests.framework.test_board_speaker_business import Encoder,quality,capture
    device=SpeakerDevice(Encoder(),tmp_path/'public-failed-save.sqlite3',clock=Clock(),quality=quality)
    def say(n,text):
        meta,raw=capture(n);return device.turn(meta,text,raw)
    try:
        say(1,'登记我的声纹，我叫测试甲')
        for n in (2,3,4):say(n,'不同的公开合成句子')
        def rejected(*args,**kwargs):raise ValueError('Synthetic transaction rejected before commit')
        monkeypatch.setattr(device.store,'enroll',rejected)
        with pytest.raises(ValueError):say(5,'确认保存声纹')
        assert not getattr(device,'save_receipts',{}) and not device.store.people()
        answer=say(6,'你已经帮我把声纹登记保存成功了吗？')
        assert '等待明确确认' in answer and '已收到' not in answer
    finally:
        device.store.close()


def test_status_query_before_during_after_commit_never_becomes_a_sample_or_claims_unknown_state(tmp_path,monkeypatch):
    from board.runtime.board_business import BoardBusinessConfig,BoardBusinessRuntime
    from board.runtime.board_speaker_business import BoardSpeakerBusiness
    from common.conversation_selection import ConversationSelection
    from tests.framework.test_board_business import Clock,Timeline,Client,Asr,drain
    from tests.framework.test_board_speaker_business import Encoder,MODEL,quality
    from tools.yuki_business_candidate import bind_runtime_pair
    source=HERE.parent.parent/'resume_yuki_business_candidate_v2/test_candidate_contracts.py'
    spec=importlib.util.spec_from_file_location('feature_v2_pair',source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    pair,_,_=module.pair_ready()
    clock,timeline,client=Clock(),Timeline(),Client()
    bundle=BoardBusinessRuntime(BoardBusinessConfig(str(tmp_path/'synthetic-business'),
        (1793300000.,1793500000.)),'test-boot',asr=Asr(),system_prompt=pair.selected_prompt,
        conversation_selection=ConversationSelection(tmp_path/'selection.json'),timeline=timeline,
        client=client,clock=clock,capture_idle=lambda:True,
        identity_snapshot=lambda:None,identity_command=lambda command:None)
    bind_runtime_pair(bundle,pair)
    encoder=Encoder()
    business=BoardSpeakerBusiness.create(tmp_path/'synthetic-speaker',encoder_factory=lambda:encoder,
        board_boot_id='test-boot',quality=quality,expected_model_id=MODEL,
        anonymous_config={'enabled':True},wall_clock=timeline.event_time,clock=clock,data_origin='synthetic')
    bundle.attach_speaker_business(business);bundle.jobs.select_conversation(resume=False)
    route_calls=[];old_route=business.route
    def route(*args,**kwargs):
        route_calls.append(True);return old_route(*args,**kwargs)
    monkeypatch.setattr(business,'route',route)
    generation=0
    def say(text):
        nonlocal generation
        generation+=1;bundle.jobs.asr.text=text
        pcm=struct.pack('<h',generation*1000)*48000
        meta=bundle.jobs.submit(SimpleNamespace(capture_id='v2-public-'+str(generation),
            audio=SimpleNamespace(sample_count=48000),pcm=pcm))
        assert bundle.jobs.run_next()
        values=drain(bundle.jobs)
        assert not any('error' in row for row in values),values
        spoken=''.join(row['channel_event']['text'] for row in values
            if row.get('channel_event',{}).get('kind')=='text')
        complete=next(row['network_complete'] for row in values if 'network_complete' in row)
        bundle.jobs.acknowledge(meta,complete);bundle.jobs.drain_actions()
        assert bundle.jobs.last_ack['committed']
        return spoken,meta
    def sample_state(meta):
        def get():
            device=business.hub.speaker
            row=device.sessions.get(device.key(meta))
            return (row['stage'],len(row['vectors'])) if row and 'vectors' in row else None
        return business.pool.submit(get).result(1)
    question='你已经帮我把声纹登记保存成功了吗？'
    try:
        answer,meta=say(question)
        assert '没有可核对' in answer and '不能判断' in answer and '设置' not in answer
        assert not route_calls and sample_state(meta) is None
        answer,meta=say('雪妃，登记我的声纹，我叫测试乙')
        assert '分三次' in answer
        assert sample_state(meta)==('samples',0)
        count=len(route_calls)
        answer,meta=say(question)
        assert '仍在采样' in answer and sample_state(meta)==('samples',0)
        assert len(route_calls)==count
        for i in range(3):
            say('这是第'+str(i+1)+'段不同的公开合成句子')
        count=len(route_calls)
        answer,meta=say(question)
        assert '等待明确确认' in answer and sample_state(meta)==('confirm',3)
        assert len(route_calls)==count
        answer,meta=say('确认保存声纹')
        assert '已保存' in answer
        answer,_=say(question)
        assert '已收到声纹保存提交回执' in answer and '身份已确认' in answer
        assert '不代表' in answer
        clock.now+=60.1
        answer,_=say(question)
        assert '没有可核对' in answer and '不能判断' in answer
        assert all(kind=='tts' for kind,_ in client.calls)
        assert business.pool.submit(lambda:len(business.hub.speaker.store.people())).result(1)==1
        assert not business.public()['speaker_calibrated'] and not bundle.access.grants
    finally:
        bundle.close()
