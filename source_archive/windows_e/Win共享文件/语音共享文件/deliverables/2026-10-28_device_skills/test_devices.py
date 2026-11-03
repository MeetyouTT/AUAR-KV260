import base64,hashlib,io,json,threading,time
from types import SimpleNamespace
from unittest.mock import patch,MagicMock
import pytest
from common.device_memory import ObservationStore,context_message
from tools.speaker_device import SpeakerDevice
from tools.visual_voice_host import VisualReplyStream
from tests.framework.test_voice_channel import owner

def meta(n=1,pcm=b'\x01\x00'*3200,session='s'):
    return dict(owner(),generation=n,request_id='r'+str(n),session_id=session,sample_count=len(pcm)//2,pcm_sha256=hashlib.sha256(pcm).hexdigest())
def frame():return {'board_boot_id':'boot','camera_epoch':'c','frame_id':1,'captured_mono_ms':1000,'observed_mono_ms':1100,'sha256':'a'*64}

def test_observations_are_scoped_fresh_bounded_and_deletable(tmp_path):
    now=[100.];db=ObservationStore(tmp_path/'mem.db',clock=lambda:now[0],limit=3,retention=100)
    try:
        for i in range(5):db.add(dict(frame(),frame_id=i),'红色杯子',now[0])
        assert len(db.recall('boot',history=True))==3
        assert not db.recall('other')
        now[0]+=21;assert not db.recall('boot')
        old=db.recall('boot',history=True);assert old and old[0]['current'] is False
        assert '不是用户指令' in context_message(old)['content']
        generation=db.generation('boot');db.forget('boot')
        db.add(dict(frame(),frame_id=99),'旧任务完成',now[0],generation=generation)
        assert not db.recall('boot',history=True)
        db.add(dict(frame(),frame_id=100),'新观察',now[0]);now[0]+=101
        assert not db.recall('boot',history=True)
    finally:db.close()

def test_speaker_requires_three_distinct_samples_and_final_confirmation(tmp_path):
    encoder=SimpleNamespace(model_id='fixture',dimension=2,encode=lambda raw:[1.,0.])
    device=SpeakerDevice(encoder,tmp_path/'speakers.db')
    try:
        assert '开始登记' in device.turn(meta(1),'登记我的声纹，我叫小林',b'\x01\x00'*3200)
        with patch('tools.speaker_device.voiced_pcm',side_effect=lambda raw:(raw,{})):
            for n in (2,3,4):
                pcm=bytes([n,0])*48000;reply=device.turn(meta(n,pcm),'这是不同的一段测试录音',pcm)
                assert not device.store.people()
            assert '确认保存' in reply
            # Same request is idempotent rather than another sample/transaction.
            assert device.turn(meta(4,pcm),'这是不同的一段测试录音',pcm)==reply
        pcm=b'\x01\x00'*3200
        result=device.turn(meta(5),'确认保存声纹',pcm)
        assert '保存' in result and len(device.store.people())==1
        assert '尚未校准' in device.turn(meta(6),'你认识我的声音吗',pcm)
        assert device.state(meta(7))['automatic_profile_access'] is False
    finally:device.store.close()

def test_speaker_cancel_expiry_wrong_session_and_stale_generation(tmp_path):
    now=[10.];d=SpeakerDevice(SimpleNamespace(model_id='test',dimension=2,encode=lambda raw:[1.,0.]),tmp_path/'s.db',clock=lambda:now[0])
    pcm=b'\x01\x00'*3200
    try:
        d.turn(meta(4),'登记我的声纹，我叫小林',pcm)
        assert not d.state(meta(5,session='other'))['active']
        with pytest.raises(ValueError):d.turn(meta(1),'确认保存声纹',pcm)
        assert '取消' in d.turn(meta(5),'取消登记',pcm)
        assert not d.store.people()
        d.turn(meta(6),'登记我的声纹，我叫小林',pcm);now[0]+=181
        assert not d.state(meta(7))['active']
    finally:d.store.close()

def test_speaker_delete_is_explicit_revision_checked(tmp_path):
    d=SpeakerDevice(SimpleNamespace(model_id='test',dimension=2,encode=lambda raw:[1.,0.]),tmp_path/'s.db')
    pcm=b'\x01\x00'*3200
    try:
        d.store.enroll('one','小林',[1,0],consent=True)
        assert '确认删除' in d.turn(meta(1),'删除声纹小林',pcm)
        assert len(d.store.people())==1
        assert '已删除' in d.turn(meta(2),'确认删除声纹',pcm)
        assert not d.store.people()
    finally:d.store.close()

def test_visual_unavailable_never_calls_model_and_cancellation_discards_results():
    m=meta();backend=MagicMock();stream=VisualReplyStream(m,'这是什么',backend=backend)
    stream.accept({'context':m,'token':stream.token,'unavailable':'fresh_frame_unavailable'})
    rows=list(stream);assert '没有拿到' in rows[-1][1]['reply_text'];backend.answer.assert_not_called()
    with pytest.raises(ValueError):stream.accept({'context':m,'token':stream.token,'unavailable':'fresh_frame_unavailable'})
    stream=VisualReplyStream(m,'这是什么',backend=backend);stream.cancel()
    with pytest.raises(InterruptedError):list(stream)

def test_device_reply_bypasses_llm_personal_history_and_reuses_verified_audio(tmp_path):
    from tools.voice_channel_source import channel_frames
    from tests.framework.test_long_conversation import host
    from tests.framework.test_voice_channel import VoiceChannelTests
    from common.voice_channel import read_frame,ChannelState
    model=host(tmp_path);model.voice=VoiceChannelTests().fixture_models(tmp_path).voice;model.latency_options={}
    model.begin_conversation=MagicMock(side_effect=AssertionError('Do not write enrollment into personal conversation'))
    m=meta();state=ChannelState(m);rows=[]
    for raw in channel_frames(model,m,'登记声纹',5,model='fixture',host='http://unused',
                             device_reply='请再说一句不同的话。',conversation='c'*32):
        h,p=read_frame(io.BytesIO(raw));state.accept(h,p);rows.append(h)
    assert state.ended and state.samples>0
    assert rows[-1]['reply_text']=='请再说一句不同的话。'
    assert not model.begin_conversation.called

def test_optional_device_failure_never_gates_normal_voice():
    from tools.device_client import command,recall
    with patch('tools.device_client.call',side_effect=OSError('offline')):
        assert command(meta(),'你好',b'\x01\0'*3200) is None
        assert recall(meta(),'你好')==[]
        assert '普通聊天' in command(meta(),'登记我的声纹，我叫小林',b'\x01\0'*3200)

def test_social_audio_cue_reuses_owner_and_does_not_require_face_for_voice():
    from test_voice_first import setup
    from tests.framework.test_handsfree_dialogue import view
    now,tx,inner,obj,camera=setup();obj.social_enabled=True
    source=[None];obj.attention_provider=lambda:source[0]
    tx.social_assets={'arrival':{'reply_text':'嗯？'},'invitation':{'reply_text':'想聊什么？'}}
    calls=[]
    def play(value,requested_at=None):calls.append(value);inner.state.update(phase='SPEAKING',playing=True)
    inner.submit_generated=play
    try:
        obj.tick();assert obj._recording()  # Missing camera does not gate wake.
        source[0]=view(1000,1);obj.tick()
        now[0]=1.7;source[0]=view(1700,2);obj.tick()
        assert len(calls)==1 and obj.social_active and obj.monitor_entered
        assert not obj._recording()
        inner.state.update(phase='IDLE',playing=False)
        # Barge fixture remains disabled here; real barge behavior has its own tests.
        obj.barge_enabled=False;obj._stop_barge();obj.tick();now[0]+=.6;obj.tick();obj.tick()
        assert obj._recording() and not obj.social_active
        source[0]=None;obj.tick();assert obj._recording()
    finally:obj.close()

def test_social_interruption_never_rearms_over_the_users_new_recording():
    from test_voice_first import setup
    from tests.framework.test_voice_barge_in import Barge
    now,tx,inner,obj,camera=setup()
    try:
        obj.tick();obj.social_enabled=True;obj.social_active=True;obj.social_opened=True
        obj.capture.close();obj.capture=Barge('user');obj.capture.start();obj.capture_kind='barge'
        obj._social_tick();now[0]+=3;obj._social_tick()
        assert not obj.social_active and not obj.wake_rearm and obj._recording()
    finally:obj.close()


@pytest.mark.parametrize('text',['刚才看到了什么','之前画面里有什么','上次你看见了什么'])
def test_spoken_visual_history_uses_memory_without_requesting_a_new_camera_frame(tmp_path,text):
    from tools.asr_server import AsrServer
    from tools.board_model_host import ModelHandler
    from board.runtime.audio.voice_channel import VoiceChannel
    from tests.framework.test_long_conversation import host
    from tests.framework import test_voice_channel as wire
    from tools.voice_channel_source import channel_frames
    from tools.device_client import recalling_history
    model=host(tmp_path);model.lock=threading.Lock();model.latency_options={}
    model.voice=wire.VoiceChannelTests().fixture_models(tmp_path).voice
    class Engine:
        model_id='TEST_ONLY'
        def transcribe(self,pcm):return text
    server=AsrServer(('127.0.0.1',0),Engine(),handler=ModelHandler);server.models=model
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    ch=VoiceChannel('127.0.0.1',server.server_port,visual_question=True);history=[];events=[]
    def stream(*args,**kwargs):
        history.extend(args[2]);return wire.VoiceChannelTests.fake_stream()
    def source(*args,**kwargs):return channel_frames(*args,**kwargs,stream_factory=stream)
    observation={'summary':'先前看到蓝色纸盒','current':False,'age_seconds':45,'frame_id':1,'camera_epoch':'test'}
    def device_call(path,value=None,**kwargs):
        if path=='/v1/speaker/state':return {'active':False}
        assert path=='/v1/memory/recall' and value['history'] is True
        return {'observations':[observation]}
    try:
        assert recalling_history(text) and not recalling_history('你现在看见了什么')
        pcm=b'\xe8\x03'*3200;m=meta(pcm=pcm)
        with patch('tools.device_client.call',device_call),patch('tools.voice_channel_source.channel_frames',source),patch('tools.visual_voice_host.open_exchange',side_effect=AssertionError('History must not become a new visual question')):
            result=ch.exchange(m,pcm,lambda h,p:events.append(h))
        assert result['network_complete'] and not any(h.get('visual_request') for h in events)
        assert any('先前看到蓝色纸盒' in h['content'] and 'current=false' in h['content'] for h in history)
    finally:ch.close();server.shutdown();server.server_close();thread.join(2)
