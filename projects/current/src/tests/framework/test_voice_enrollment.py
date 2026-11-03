"""Oral enrollment ownership, confirmation, host relay and original voice frames."""
import copy,hashlib,io,json,threading,time
import pytest
from common import voice_enrollment as speech
from board.identity.voice_enrollment import VoiceEnrollment
from tools.identity_voice_host import IdentityReplyStream
from tools.board_model_host import ModelHost
from tests.framework.test_voice_channel import owner
from tests.framework import test_voice_channel as voice_fixture
from tests.framework.test_history_reuse import host,DIGEST

def snapshot():
    key={'camera_epoch':'camera','track_id':1,'track_generation':1}
    return {'protocol_version':'aura-ui-1','board_boot_id':'boot','service_epoch':'camera-service',
        'sequence':1,'observed_mono_ms':1000,'ttl_ms':2000,'source_kind':'actual',
        'context':{'session_id':'camera-session','request_id':'','generation':0},
        'modules':{'camera':{'state':'READY'},'vision':{'state':'READY','people_count':1},
            'target':{'state':'CONFIRMED','selected':key,'tracks':[{'key':key,'label':'person'}]},
            'identity':{'state':'UNKNOWN','people':[],'db_version':0}},
        'capabilities':{'identity_enroll':True,'identity_delete':False}}

class Fixture:
    def __init__(self):
        self.view=snapshot();self.saved=[];self.now=0
        self.flow=VoiceEnrollment('boot',lambda:copy.deepcopy(self.view),self.command,clock=lambda:self.now,now_ms=lambda:1000)
    def command(self,command):
        self.saved.append(command)
        self.view['modules']['identity'].update(state='KNOWN',db_version=1,
            last_operation={'command_id':command['command_id'],'action':'identity_enroll','state':'COMMITTED','db_version':1,'detail':'已登记'})
        return {'accepted':True,'command_id':command['command_id']}
    def say(self,text,start=None,**kw):return self.flow.handle(text,start or copy.deepcopy(self.view),**kw)

@pytest.mark.parametrize('text',['帮我登记身份','汐蓝，请帮我登记身份','你好西兰记住我的脸','我要做身份认证'])
def test_direct_requests_only(text):assert speech.enrollment_requested(text)

@pytest.mark.parametrize('text',['他说帮我登记身份','如果我要登记身份','“帮我登记身份”','不要帮我登记身份',
    '帮我登记身份然后删除全部资料','身份登记怎么做','我叫小林'])
def test_chat_and_quoted_commands_are_not_enrollment(text):assert not speech.enrollment_requested(text)

def test_oral_name_is_repeated_and_only_explicit_confirmation_commits():
    f=Fixture()
    assert f.say('帮我登记身份')['code']=='ask_name' and f.saved==[]
    assert f.say('我叫小林')==speech.result('confirm_name','小林') and f.saved==[]
    for text in ('好的','是的','确认登记吗','不要确认登记','他说确认登记'):
        assert f.say(text)['code']=='retry_confirm' and f.saved==[]
    assert f.say('确认登记')['code']=='registered'
    assert len(f.saved)==1 and f.saved[0]['params']['display_name']=='小林'
    assert f.flow.public()=={'stage':'idle','active':False}
    assert f.say('帮我登记身份')['code']=='already_known' and len(f.saved)==1

def test_name_correction_repeats_new_value_and_cancellation_never_enrolls():
    f=Fixture();f.say('帮我登记身份');f.say('我叫小林')
    assert f.say('不是，我叫小明')==speech.result('confirm_name','小明')
    assert f.say('取消登记')['code']=='cancelled' and f.saved==[]
    assert f.say('确认登记') is None

@pytest.mark.parametrize('mutation',[
    lambda s:s['modules']['target']['selected'].update(track_generation=2),
    lambda s:s.update(service_epoch='restarted'),
    lambda s:s['modules']['vision'].update(people_count=2),
    lambda s:s['modules']['target'].update(selected=None),
    lambda s:s.update(source_kind='fixture'),
    lambda s:s.update(observed_mono_ms=-9000),
    lambda s:s['modules']['identity'].update(db_version=2),
])
def test_changed_stale_or_ambiguous_target_cannot_confirm(mutation):
    f=Fixture();f.say('帮我登记身份');f.say('我叫小林');mutation(f.view)
    assert f.say('确认登记')['code']=='changed' and f.saved==[]

def test_missing_capture_start_owner_never_binds_current_person_after_asr():
    f=Fixture();assert f.flow.handle('帮我登记身份',None)['code']=='face_unavailable' and f.saved==[]

def test_timeout_and_explicit_stop_clear_pending_name():
    f=Fixture();f.say('帮我登记身份');f.say('我叫小林');f.now=121
    assert f.say('确认登记')['code']=='expired' and f.saved==[]
    f.now=0;f.say('帮我登记身份');f.say('我叫小林');f.flow.reset()
    assert f.say('确认登记') is None and f.saved==[]

def test_stale_generation_and_failed_transaction_do_not_claim_success():
    f=Fixture();f.say('帮我登记身份');f.say('我叫小林')
    with pytest.raises(InterruptedError):f.say('确认登记',is_current=lambda:False)
    assert f.saved==[]
    f.flow.command=lambda value:{'accepted':True,'command_id':value['command_id']}
    assert f.say('确认登记')['code']=='failed'

@pytest.mark.parametrize('name',['你叫什么','小林忽略规则','小林，删除记录','12345','a\nhello',''])
def test_invalid_name_cannot_enter_spoken_reply_or_database(name):
    assert not speech.valid_name(name)
    with pytest.raises(ValueError):speech.render({'code':'confirm_name','name':name})

def test_host_requires_current_context_token_and_single_response():
    model=host();meta=owner();model.register_stream(meta);stream=model.open_identity_exchange(meta,4)
    value={'context':meta,'token':stream.token,'reply':speech.result('ask_name')}
    with pytest.raises(ValueError):model.accept_identity_result(dict(value,token='0'*48))
    assert model.accept_identity_result(value)['accepted']
    with pytest.raises(ValueError):model.accept_identity_result(value)
    assert list(stream)[-1][1]['reply_text']==speech.render(value['reply'])
    assert stream.metrics['backend']=='board_identity_workflow'

def test_host_cancellation_and_expiry_never_release_success_speech():
    stream=IdentityReplyStream(owner(),.02);stream.cancel()
    with pytest.raises(InterruptedError):list(stream)
    stream=IdentityReplyStream(owner(),.01);time.sleep(.02)
    with pytest.raises(ValueError):stream.accept(owner(),stream.token,speech.result('registered'))

def test_identity_pipeline_uses_original_tts_but_never_llm_or_chat_history(tmp_path):
    from common.voice_channel import ChannelState,read_frame
    from tools.voice_channel_source import channel_frames
    model=host();model.voice=voice_fixture.VoiceChannelTests().fixture_models(tmp_path).voice
    model.latency_options={'reply_first':True,'coalesce_chat':True,'reuse_history':True,'compact_grammar':True}
    meta=owner();stream=model.open_identity_exchange(meta,4)
    frames=channel_frames(model,meta,'帮我登记身份',4,model='original-27b',host='unused',identity_exchange=stream,
        stream_factory=lambda *a,**kw:(_ for _ in ()).throw(AssertionError('LLM must not run')))
    received=[];state=ChannelState(meta)
    for packet in frames:
        header,pcm=read_frame(io.BytesIO(packet));state.accept(header,pcm);received.append(header)
        if header['kind']=='transcript':
            assert header['identity_request']==stream.token
            model.accept_identity_result({'context':meta,'token':stream.token,'reply':speech.result('ask_name')})
    assert received[-1]['kind']=='end' and len(model.voice.calls)==1
    end=received[-1];model.acknowledge_stream({'context':meta,'voice_sample_count':end['sample_count'],'pcm_sha256':end['pcm_sha256']})
    assert model.histories=={} and not model.pending_streams

def test_real_http_transcript_callback_unblocks_tts_without_second_asr(tmp_path):
    from tools.asr_server import AsrServer
    from tools.board_model_host import ModelHandler
    from board.runtime.audio.voice_channel import VoiceChannel
    from tests.framework.test_voice_channel import PCM
    model=host();model.voice=voice_fixture.VoiceChannelTests().fixture_models(tmp_path).voice
    model.lock=threading.Lock();model.latency_options={'reply_first':True,'coalesce_chat':True}
    class Engine:
        model_id='TEST_ONLY';calls=0
        def transcribe(self,pcm):self.calls+=1;return '帮我登记身份'
    engine=Engine();server=AsrServer(('127.0.0.1',0),engine,handler=ModelHandler);server.models=model
    worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
    channel=VoiceChannel('127.0.0.1',server.server_port);meta=owner();seen=[]
    def receive(header,pcm):
        seen.append(header['kind'])
        if header['kind']=='transcript':channel.identity_result(meta,header['identity_request'],speech.result('ask_name'))
    try:
        answer=channel.exchange(meta,PCM,receive,enrollment_state=False)
        assert answer['reply_text']==speech.render(speech.result('ask_name'))
        assert engine.calls==1 and seen[-1]=='end' and 'audio' in seen
        assert model.histories=={}
    finally:
        channel.close();server.shutdown();server.server_close();worker.join(2)
