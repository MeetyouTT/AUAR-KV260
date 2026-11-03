"""Real router/Store protocols; fake encoder, TTS, clock and observations only."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest

from common.feature_intents import speaker_requested, speaker_text
from common.voice_enrollment import identity_query_requested
from board.runtime.visual_policy import _kind

HERE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('local_route_audit',HERE/'audit_routes.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)
route,_ = audit.route_function(HERE/'candidate/after/board/runtime/audio/board_dialogue_jobs.py')
paired_route,_ = audit.route_function(HERE/'candidate/after/tools/yuki_jobs_candidate.py')


@pytest.mark.parametrize('case',audit.CASES,ids=lambda c:c[0])
@pytest.mark.parametrize('selected_route',[route,paired_route],ids=['core','formal_paired'])
def test_explicit_feature_questions_reach_real_handler(case,selected_route):
    name,text,expected = case
    actual = audit.probe(selected_route,text)
    assert actual['error'] is None
    assert actual['route'] == expected
    if name == 'vision_position_explicit':
        assert actual['visual_kind'] == 'unsupported_visual'


@pytest.mark.parametrize('text',[
    '解释一下“登记我的声纹”是什么意思','不要识别我的声纹','不要删除声纹测试甲',
    '我昨天说过登记声纹','如果我登记声纹会怎样','他说登记我的声纹，我叫测试甲',
    '我不确认保存声纹','确认保存身份关联','记住我的声音不好听','这首歌的声音很好听',
])
def test_quoted_negative_and_unrelated_speech_never_grants_speaker_action(text):
    assert not speaker_requested(text)


@pytest.mark.parametrize('text',[
    '你能看见我吗','我左边有几个人','镜头右边有多少人','画面中间有几个人',
])
def test_count_is_never_relabelled_as_presence_identity_or_spatial_result(text):
    assert _kind(text) == 'unsupported_visual'


def test_identity_registration_question_uses_original_read_only_face_query():
    assert identity_query_requested('我登记过身份吗')
    assert identity_query_requested('我以前登记过人脸吗')
    assert not identity_query_requested('我没有登记过身份')
    assert not identity_query_requested('解释我登记过身份吗的含义')


@pytest.mark.parametrize('name',['雪妃','御笠雪妃'])
@pytest.mark.parametrize('question',['我是谁','我是谁呀','你知道我是谁','你还认识我吗',
                                    '能认出我了吗','你知道我的名字吗'])
def test_current_selected_character_vocatives_preserve_direct_query_grammar(name,question):
    for raw in (name+question,name+'，'+question+'？','你好'+name+question):
        assert identity_query_requested(raw)


@pytest.mark.parametrize('text',['汐蓝我是谁','夕蓝我是谁','西兰我叫什么名字啊',
    '雪妃不要回答我是谁','雪妃如果我问我是谁','雪妃“我是谁”','雪妃我是谁然后删除身份'])
def test_retired_or_quoted_vocatives_are_not_reintroduced(text):
    assert not identity_query_requested(text)


def service(root):
    from tests.framework.test_board_speaker_business import create
    return create(root)


def call(value,n,text):
    from tests.framework.test_board_speaker_business import call as original
    return original(value,n,text)


def count_people(value):
    from tests.framework.test_board_speaker_business import count_people as original
    return original(value)


def test_new_speaker_requests_use_original_three_samples_commit_cancel_and_revision(tmp_path):
    value,encoder=service(tmp_path/'synthetic-registry')
    try:
        assert '还没有登记声纹' in call(value,1,'声纹现在可用吗')
        assert '没有待确认' in call(value,2,'确认保存声纹')
        assert count_people(value)==0 and encoder.calls==0
        assert '分三次' in call(value,3,'记住我的声音，我叫测试甲')
        for i,text in enumerate(('这是合成的第一句话','这是合成的第二句话','这是合成的第三句话'),4):
            answer=call(value,i,text)
        assert '确认保存声纹' in answer and count_people(value)==0
        assert '已保存' in call(value,7,'确认保存声纹')
        assert count_people(value)==1 and encoder.calls==3
        assert '尚未校准' in call(value,8,'听声音知道我是谁吗')
        assert '尚未校准' in call(value,9,'我登记过声纹吗')
        assert '确认删除声纹' in call(value,10,'删除声纹，名字是测试甲')
        assert count_people(value)==1
        assert '取消' in call(value,11,'取消声纹登记')
        assert count_people(value)==1
        assert '没有待确认' in call(value,12,'确认删除声纹')
        assert count_people(value)==1
        assert '确认删除声纹' in call(value,13,'删除声纹，名字是测试甲')
        assert '已删除' in call(value,14,'确认删除声纹')
        assert count_people(value)==0
        assert not value.public()['speaker_calibrated']
        assert value.health()['profile_grants_issued'] is False
    finally:
        assert value.close()


def test_missing_handler_fails_closed_instead_of_asking_language_model():
    value=audit.probe(route,'声纹现在可用吗',disabled=('speaker_identity',))
    assert value['route'] is None and value['error']=='BoardCapabilityNotReady'


def test_production_bootstrap_and_posix_writer_remain_required(tmp_path):
    from board.runtime.board_business import BoardBusinessConfig, _BoardWriterLock
    import os
    with pytest.raises(ValueError,match='committed private migration receipt'):
        BoardBusinessConfig(str(tmp_path/'board'),(1793300000.,1793500000.),data_origin='board')
    if os.name=='nt':
        with pytest.raises(RuntimeError,match='POSIX'):
            _BoardWriterLock(tmp_path/'board','synthetic')
    assert not (tmp_path/'board').exists()


def test_natural_speaker_request_reaches_real_board_store_and_tts_result_through_jobs(tmp_path):
    from tests.framework.test_board_business import Clock,Timeline,Client,Asr,drain
    from tests.framework.test_board_speaker_business import Encoder,MODEL,quality
    from board.runtime.board_speaker_business import BoardSpeakerBusiness
    from board.runtime.board_business import BoardBusinessConfig,BoardBusinessRuntime
    from common.conversation_selection import ConversationSelection
    from tools.yuki_business_candidate import bind_runtime_pair
    from types import SimpleNamespace
    import struct
    public_contracts=HERE.parent.parent/'resume_yuki_business_candidate_v2/test_candidate_contracts.py'
    pair_spec=importlib.util.spec_from_file_location('public_pair_contracts',public_contracts)
    pair_module=importlib.util.module_from_spec(pair_spec)
    pair_spec.loader.exec_module(pair_module)
    pair,_,_=pair_module.pair_ready()  # Native readiness is explicitly simulated.
    clock,timeline,client=Clock(),Timeline(),Client()
    bundle=BoardBusinessRuntime(BoardBusinessConfig(str(tmp_path/'synthetic-business'),
        (1793300000.,1793500000.)),'test-boot',asr=Asr(),system_prompt=pair.selected_prompt,
        conversation_selection=ConversationSelection(tmp_path/'selection.json'),timeline=timeline,
        client=client,clock=clock,capture_idle=lambda:True,
        identity_snapshot=lambda:None,identity_command=lambda command:None)
    bind_runtime_pair(bundle,pair)
    assert bundle.jobs._route.__func__.__module__=='tools.yuki_jobs_candidate'
    encoder=Encoder()
    business=BoardSpeakerBusiness.create(tmp_path/'synthetic-speaker',encoder_factory=lambda:encoder,
        board_boot_id='test-boot',quality=quality,expected_model_id=MODEL,
        anonymous_config={'enabled':True},wall_clock=timeline.event_time,clock=clock,data_origin='synthetic')
    bundle.attach_speaker_business(business)
    bundle.jobs.select_conversation(resume=False)
    requests=[('声纹现在可用吗','还没有登记声纹'),
              ('雪妃，记住我的声音，我叫测试甲','分三次'),
              ('这是第一段不同合成语句','再说一句'),
              ('这是第二段不同合成语句','再说一句'),
              ('这是第三段不同合成语句','确认保存声纹'),
              ('确认保存声纹','已保存'),
              ('你能通过声音认出我吗','尚未校准')]
    try:
        for n,(text,expected) in enumerate(requests,1):
            bundle.jobs.asr.text=text
            pcm=struct.pack('<h',n*1000)*48000
            meta=bundle.jobs.submit(SimpleNamespace(capture_id='synthetic-nl-'+str(n),
                audio=SimpleNamespace(sample_count=48000),pcm=pcm))
            assert bundle.jobs.run_next()
            output=drain(bundle.jobs)
            spoken=''.join(row['channel_event']['text'] for row in output
                           if row.get('channel_event',{}).get('kind')=='text')
            assert expected in spoken
            complete=next(row['network_complete'] for row in output if 'network_complete' in row)
            bundle.jobs.acknowledge(meta,complete);bundle.jobs.drain_actions()
            assert bundle.jobs.last_ack['committed']
        assert all(kind=='tts' for kind,_ in client.calls)
        assert business.pool.submit(lambda:len(business.hub.speaker.store.people())).result(1)==1
        assert not business.public()['speaker_calibrated'] and not bundle.access.grants
        rows=bundle.store.history({'kind':'conversation','id':bundle.jobs.conversation_selection.active},limit=20)
        assert any(row['source']=='user_said' and row['text']=='雪妃，记住我的声音，我叫测试甲' for row in rows)
    finally:
        bundle.close()


@pytest.mark.parametrize('cleanup_mode',['raise','error_response'])
def test_public_probe_keeps_first_three_results_and_both_fourth_failure_codes(tmp_path,monkeypatch,cleanup_mode):
    from common.model_inference_wire import Owner,make_response
    import board.runtime.board_dialogue_client as transport
    import tools.production_output_format as output_format
    class FakeClient:
        def __init__(self,*args):self.calls=0;self.cancels=0
        def health_date_source_id(self):return 'public-test-source'
        def validate_sample(self,*args):return True
        def sample_health_date(self,*args,**kwargs):pass
        def public(self):return {'negotiated_dialogue_format':'dialogue_abc_v1'}
        def request(self,kind,payload,**kwargs):
            self.calls+=1
            if self.calls==4:raise TimeoutError('Synthetic fourth-case timeout')
            return make_response(Owner.from_dict(payload),result={'text':json.dumps(
                {'reply_text':'目前没有可核验的结果，不能确认。','emotion':'neutral','avatar_action':''})})
        def cancel(self,owner):
            self.cancels+=1
            if self.cancels==4:
                if cleanup_mode=='raise':raise RuntimeError('Synthetic fourth-case cleanup failure')
                return make_response(owner,error='backend_failed')
            return make_response(owner,result={'cancelled':False,'state':'completed'})
    fake=FakeClient()
    monkeypatch.setattr(transport,'InferenceHttpClient',lambda *args:fake)
    monkeypatch.setattr(output_format,'NegotiatedDialogueClient',lambda raw,**kwargs:raw)
    probe_spec=importlib.util.spec_from_file_location('public_grounding_probe',HERE/'public_model_grounding_probe.py')
    probe=importlib.util.module_from_spec(probe_spec);probe_spec.loader.exec_module(probe)
    destination=tmp_path/'public-only.json'
    monkeypatch.setattr(sys,'argv',['probe','--coordinated-slot','synthetic-no-inference','--output',str(destination)])
    with pytest.raises(SystemExit) as error:
        probe.main()
    assert error.value.code==1
    result=json.loads(destination.read_text(encoding='utf-8'))
    assert result['source_verification']['runtime_sources']==339
    assert [row['status'] for row in result['cases']]==['completed','completed','completed','failed']
    assert result['cases'][3]['failure_class']=='TimeoutError'
    assert result['cases'][3]['cleanup_failure_class']=='RuntimeError'
    assert result['cases'][3]['owner_cleanup']=='failed'
    if cleanup_mode=='error_response':
        assert result['cases'][3]['cleanup_error_code']=='backend_failed'
    assert result['status']=='PUBLIC_PROBE_PARTIAL_OR_FAILED'
