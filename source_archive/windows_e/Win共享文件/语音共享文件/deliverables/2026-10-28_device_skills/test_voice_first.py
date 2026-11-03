import hashlib
import threading
from unittest.mock import MagicMock, patch
import pytest
from common.voice_wake import wake_request
from tools.voice_first_recording import VoiceFirstRecordingController
from tests.framework.test_handsfree_dialogue import Tx, speech
from tests.framework import test_automatic_conversation as automatic
from tests.framework.test_voice_channel import owner as wire_owner


@pytest.mark.parametrize('text,expected', [('汐蓝',''),('汐蓝！',''),('欸',''),('哎。',''),
    ('汐蓝今天怎么样','今天怎么样'),('哎，你好','你好'),('欸 你在吗','你在吗'),
    ('哎呀真好',None),('那个汐蓝',None),('你好',None),('欸嘿',None),('',None), (None,None)])
def test_wake_word_is_explicit_and_preserves_following_request(text,expected):
    assert wake_request(text)==expected


class WakeTx(Tx):
    def __init__(self):super().__init__();self.wakes=[]
    def mark_wake_entry(self,cid):self.wakes.append(cid)


def setup():
    now=[1.];tx=WakeTx();inner=automatic.FakeController()
    # Any accidental visual dependency fails this test immediately.
    camera=MagicMock(side_effect=AssertionError('Voice must not query camera'))
    obj=VoiceFirstRecordingController(inner,transcriber=tx,boot_id='boot',
        attention_provider=camera,clock=lambda:now[0],early_listen=True,
        auto_capture_factory=automatic.FakeCapture,barge_capture_factory=MagicMock())
    return now,tx,inner,obj,camera


def test_no_face_no_camera_opens_wake_listener_and_submits_only_wake_gate():
    now,tx,inner,obj,camera=setup()
    try:
        obj.tick()
        assert obj._recording() and obj.monitor_state=='WAITING_WAKE'
        speech(obj)
        assert tx.wakes==['cap-1'] and not tx.entries and not obj.auto_enabled
        assert obj.public()['handsfree_dialogue']['visual_required'] is False
        camera.assert_not_called()
    finally:obj.close()


def test_wake_only_enters_listening_and_next_sentence_needs_no_wake_or_face():
    now,tx,inner,obj,camera=setup()
    try:
        obj.tick();speech(obj)
        tx.results.append({'context':{'request_id':'req-1','capture_id':'cap-1'},'wake_detected':True,'wake_only':True})
        obj.tick()
        assert obj.capture.counter==1  # Worker still owns the previous request.
        tx.pending=False;obj.tick()
        assert obj.capture.counter==2 and obj.monitor_entered and obj.auto_enabled
        speech(obj)
        assert len(tx.submitted)==2 and tx.wakes==['cap-1'] and tx.selections==[False]
        camera.assert_not_called()
    finally:obj.close()


def test_non_wake_rearms_without_entering_or_playing_and_pause_stays_closed():
    now,tx,inner,obj,camera=setup()
    try:
        obj.tick();speech(obj)
        tx.results.append({'context':{'request_id':'req-1','capture_id':'cap-1'},'entry_rejected':True})
        tx.pending=False;obj.tick()
        assert obj._recording() and not obj.monitor_entered and not obj.auto_enabled
        obj.cancel();now[0]+=100;obj.tick()
        assert not obj._recording() and not obj.monitor_enabled
        camera.assert_not_called()
    finally:obj.close()


def test_stale_wake_does_not_activate_new_audio_session():
    now,tx,inner,obj,camera=setup()
    try:
        obj.tick();speech(obj)
        tx.results.append({'context':{'request_id':'old','capture_id':'old'},'wake_detected':True,'wake_only':True})
        obj.tick();assert not obj.monitor_entered
    finally:obj.close()


def test_face_free_conversation_rearms_only_after_full_ack_and_tail():
    now,tx,inner,obj,camera=setup()
    try:
        obj.tick();speech(obj);obj._wake_detected()
        inner.state.update(phase='SPEAKING',playing=True)
        obj.tick();assert obj.capture.counter==1
        inner.state.update(phase='IDLE',playing=False);tx.pending=False
        inner.completions.append(({'request_id':'req-1','capture_id':'cap-1'},{}));obj.tick()
        assert obj.capture.counter==1
        tx.last_ack={'request_id':'req-1','committed':True};now[0]+=.6;obj.tick()
        assert obj.capture.counter==2 and obj.monitor_entered
        camera.assert_not_called()
    finally:obj.close()


def test_verified_interruption_keeps_audio_owner_without_any_face():
    from tests.framework.test_voice_barge_in import Barge, generating
    now,tx,inner,obj,camera=setup()
    cap=Barge('barge-1');obj.barge_factory=lambda:cap
    try:
        obj.tick();speech(obj);obj._wake_detected();generating(obj,inner)
        assert obj.barge_capture is cap
        cap.on_speech_start();obj.tick()
        assert obj.capture is cap and not inner.state['playing']
        cap.state='READY';obj.tick()
        assert tx.submitted[-1].capture_id=='barge-1'
        assert tx.wakes==['cap-1'] and tx.selections==[False]
        assert tx.entries==['barge-1']  # Acoustic validity only.
        camera.assert_not_called()
    finally:obj.close()


def test_silence_returns_to_wake_without_camera_and_without_disabling_monitor():
    now,tx,inner,obj,camera=setup()
    try:
        obj.tick();obj._wake_detected();now[0]+=31;obj.tick()
        assert not obj.monitor_entered and obj.monitor_enabled
        now[0]+=.3;obj.tick()
        assert obj._recording() and obj.monitor_state=='WAITING_WAKE'
        camera.assert_not_called()
    finally:obj.close()


def test_visual_social_is_optional_bounded_and_does_not_steal_voice_turns():
    from common.visual_social import VisualSocial
    p=VisualSocial()
    assert p.observe('face',1,0) is None
    assert p.observe('face',1,1) is None  # Repeated camera frame cannot trigger.
    assert p.observe('face',2,1)=={'kind':'arrival','text':'嗯？'}
    assert p.observe('face',3,4.9) is None
    assert p.observe('face',4,5)=={'kind':'invitation','text':'想和我聊点什么呀？'}
    assert p.observe('face',5,20) is None
    p.observe(None,None,21)
    p.observe('another',1,22)
    assert p.observe('another',2,23) is None  # Global greeting cooldown.


@pytest.mark.parametrize('field',['busy','speech_active'])
def test_visual_invitation_is_cancelled_when_voice_is_active(field):
    from common.visual_social import VisualSocial
    p=VisualSocial();p.observe('face',1,0);p.observe('face',2,1)
    assert p.observe('face',3,2,**{field:True}) is None
    assert p.observe('face',4,7) is None


def test_disabling_visual_or_losing_camera_cancels_only_the_social_proposal():
    from common.visual_social import VisualSocial
    p=VisualSocial();p.observe('face',1,0);p.observe('face',2,1)
    assert p.observe(None,None,3) is None
    assert p.observe(None,None,8) is None
    assert p.observe('face',5,10,enabled=False) is None


@pytest.mark.parametrize('recognized',['汐蓝，你好呀','西兰，你好呀','西蓝你好呀'])
def test_wake_plus_question_http_strips_only_prefix_and_streams_normally(tmp_path,recognized):
    from tools.asr_server import AsrServer
    from tools.board_model_host import ModelHandler
    from board.runtime.audio.voice_channel import VoiceChannel
    from tests.framework.test_long_conversation import host
    from tests.framework import test_voice_channel as wire
    from tools.voice_channel_source import channel_frames
    model=host(tmp_path);model.lock=threading.Lock();model.latency_options={}
    model.voice=wire.VoiceChannelTests().fixture_models(tmp_path).voice
    class Engine:
        model_id='TEST_ONLY'
        def transcribe(self,pcm):return recognized
    server=AsrServer(('127.0.0.1',0),Engine(),handler=ModelHandler);server.models=model
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    channel=VoiceChannel('127.0.0.1',server.server_port)
    events=[]
    def source(*args,**kwargs):return channel_frames(*args,**kwargs,stream_factory=wire.VoiceChannelTests.fake_stream)
    try:
        pcm=b'\xe8\x03'*3200;meta=dict(wire_owner(),pcm_sha256=hashlib.sha256(pcm).hexdigest())
        with patch('tools.voice_channel_source.channel_frames',source):
            result=channel.exchange(meta,pcm,lambda h,p:events.append(h),wake_entry=True,conversation='c'*32)
        assert result['network_complete'] and not result['playback_verified']
        assert [e['text'] for e in events if e['kind']=='transcript']==['你好呀']
        assert model.conversations.records('c'*32)[0]['status']=='generated'
    finally:channel.close();server.shutdown();server.server_close();thread.join(2)


@pytest.mark.parametrize('text,wake_only', [('汐蓝',True),('欸',True),('哎',True),('西兰',True),
    ('你好',False),('哎呀',False),('西兰花很好吃',False),('西来',False),('我叫西兰',False),
    ('西兰这个字怎么写',False),('你听错了，我说的是西兰',False)])
def test_real_http_wake_only_or_rejection_never_invokes_llm_tts_or_camera(tmp_path,text,wake_only):
    from tools.asr_server import AsrServer
    from tools.board_model_host import ModelHandler
    from board.runtime.audio.voice_channel import VoiceChannel
    from tests.framework.test_long_conversation import host
    from common.handsfree_entry import EntryRejected
    model=host(tmp_path);model.lock=threading.Lock();model.voice=MagicMock()
    class Engine:
        model_id='TEST_ONLY'
        def transcribe(self,pcm):return text
    server=AsrServer(('127.0.0.1',0),Engine(),handler=ModelHandler);server.models=model
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    channel=VoiceChannel('127.0.0.1',server.server_port)
    try:
        pcm=b'\xe8\x03'*3200;meta=dict(wire_owner(),pcm_sha256=hashlib.sha256(pcm).hexdigest())
        with patch('tools.voice_channel_source.serve_channel') as serve:
            if wake_only:
                assert channel.exchange(meta,pcm,lambda h,p:None,wake_entry=True,conversation='c'*32)=={'wake_only':True}
            else:
                with pytest.raises(EntryRejected):channel.exchange(meta,pcm,lambda h,p:None,wake_entry=True,conversation='c'*32)
            serve.assert_not_called();model.voice.generate.assert_not_called()
        assert model.conversations.health()['turns']==0
    finally:channel.close();server.shutdown();server.server_close();thread.join(2)
