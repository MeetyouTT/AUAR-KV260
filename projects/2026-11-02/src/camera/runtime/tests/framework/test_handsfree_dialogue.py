"""Synthetic AV readiness, cancellation and HTTP first-turn rejection checks."""
import copy
import hashlib
import threading
from unittest.mock import MagicMock,patch

import pytest

from board.runtime.audio.attention_gate import AttentionGate,read_attention
from common.handsfree_entry import acceptable_entry,audio_candidate,EntryRejected
from tools.handsfree_recording import HandsFreeRecordingController
from tests.framework.test_simple_enrollment import snapshot
from tests.framework import test_automatic_conversation as automatic
from tests.framework import test_voice_channel as wire


def view(now=1000,fid=1):
    s=snapshot();s['observed_mono_ms']=now;s['sequence']=fid
    key={'camera_epoch':'camera','track_id':1,'track_generation':1}
    s['modules']['identity'].update(target_kind='face',face_count=1,face_target=key,
        face_targets=[{'key':key,'label':'face'}],face_attention={
            'version':1,'target':key,'frame_id':fid,'captured_mono_ms':now,'ttl_ms':1000,
            'yaw_ratio':0.,'roll_degrees':0.,'frontal':True})
    return s


def test_distinct_fresh_frames_and_hold_time_required_to_open_microphone():
    gate=AttentionGate('boot')
    assert gate.observe(view(),1000)[0] is None
    assert gate.observe(view(),1600)[0] is None  # Repeated snapshot is not a new frame.
    assert gate.observe(view(1600,2),1600)[0] is not None


@pytest.mark.parametrize('kind',['missing','stale','future','wrong_boot','fixture','side','multiple','bad_target','camera_lost'])
def test_invalid_visual_evidence_never_allows_entry(kind):
    s=view()
    if kind=='missing':s=None
    elif kind=='stale':s['modules']['identity']['face_attention']['captured_mono_ms']=0
    elif kind=='future':s['modules']['identity']['face_attention']['captured_mono_ms']=2000
    elif kind=='wrong_boot':s['board_boot_id']='other'
    elif kind=='fixture':s['source_kind']='fixture'
    elif kind=='side':s['modules']['identity']['face_attention'].update(yaw_ratio=.4,frontal=False)
    elif kind=='multiple':s['modules']['identity']['face_count']=2
    elif kind=='bad_target':s['modules']['identity']['face_attention']['target']=dict(camera_epoch='other',track_id=1,track_generation=1)
    elif kind=='camera_lost':s['modules']['camera']['state']='LOST'
    assert read_attention(s,'boot',1000)[0] is None


def test_unknown_identity_is_allowed_without_reading_personal_profile():
    s=view();assert s['modules']['identity']['state']=='UNKNOWN'
    assert read_attention(s,'boot',1000)[0] is not None


@pytest.mark.parametrize('text',['','嗯','1234','...','哈哈','谢谢观看','音乐'])
def test_vad_noise_or_empty_asr_is_not_a_first_turn(text):
    assert not acceptable_entry(text)


@pytest.mark.parametrize('text',['你好','今天有点累','我想聊聊天','帮我登记身份，我叫小林','hello'])
def test_normal_speech_does_not_require_character_name(text):
    assert acceptable_entry(text)


@pytest.mark.parametrize('pcm',[b'\0\0'*16000,b'\x01\0'*16000,b'\xe8\x03'*2560,b'odd'],
                         ids=['silence','low_energy','short_noise','odd_bytes'])
def test_raw_silence_low_energy_and_short_noise_rejected_before_asr(pcm):
    assert not audio_candidate(pcm)


def test_raw_sustained_activity_matches_existing_endpoint_floor():
    assert audio_candidate(b'\0\0'*3200+b'\xe8\x03'*2880+b'\0\0'*3200)


class Tx(automatic.FakeTranscriber):
    def __init__(self):
        super().__init__();self.selections=[];self.entries=[];self.starts=[];self.results=[]
    def select_conversation(self,*,resume):self.selections.append(resume)
    def mark_visual_entry(self,cid):self.entries.append(cid)
    def capture_started(self,cid):self.starts.append(cid)
    def poll(self):return self.results.pop(0) if self.results else None


def setup():
    now=[1.];source=[None];tx=Tx();inner=automatic.FakeController()
    owner=HandsFreeRecordingController(inner,transcriber=tx,boot_id='boot',
        attention_provider=lambda:copy.deepcopy(source[0]),clock=lambda:now[0],
        auto_capture_factory=automatic.FakeCapture)
    return now,source,tx,inner,owner


def arm(now,source,owner):
    source[0]=view(1000,1);owner.tick()
    now[0]=1.6;source[0]=view(1600,2);owner.tick()
    assert owner.capture.snapshot()['state']=='RECORDING'


def speech(owner):
    owner.capture.on_speech_start();owner.capture.state='READY';owner.tick()


def test_presence_only_arms_bounded_listener_never_submits_or_selects_conversation():
    now,source,tx,inner,owner=setup()
    try:
        owner.tick();assert owner.capture is None
        arm(now,source,owner)
        assert owner.public()['handsfree_dialogue']['state']=='WAITING_SPEECH'
        assert not owner.auto_enabled and tx.submitted==[] and tx.selections==[]
    finally:owner.close()


def test_visual_then_speech_enters_without_click_and_creates_new_anonymous_session():
    now,source,tx,inner,owner=setup()
    try:
        arm(now,source,owner);speech(owner)
        assert owner.auto_enabled and len(tx.submitted)==1
        assert tx.selections==[False] and tx.entries==['cap-1']
        assert tx.starts[-1]=='cap-1'
        assert owner.public()['handsfree_dialogue']['state']=='CHECKING_SPEECH'
    finally:owner.close()


def test_missing_audio_start_proof_discards_ready_clip():
    now,source,tx,inner,owner=setup()
    try:
        arm(now,source,owner);owner.capture.state='READY';owner.tick()
        assert not tx.submitted and not owner.auto_enabled
    finally:owner.close()


@pytest.mark.parametrize('at',['listening','processing','playing'])
def test_face_loss_cancels_owned_audio_and_rejects_late_reply(at):
    now,source,tx,inner,owner=setup()
    try:
        arm(now,source,owner)
        if at!='listening':speech(owner)
        if at=='playing':inner.state.update(phase='SPEAKING',playing=True)
        source[0]=None;owner.tick()
        assert not owner.auto_enabled and not owner.monitor_owned and not inner.state['playing']
        inner.completions.append(({'request_id':'req-1','capture_id':'cap-1'},{}));owner.tick()
        assert tx.ack_calls==[]
    finally:owner.close()


def test_end_button_pauses_monitor_and_cannot_automatically_reopen_mic():
    now,source,tx,inner,owner=setup()
    try:
        arm(now,source,owner);owner.conversation_stop()
        for index in range(3,8):
            now[0]+=1.;source[0]=view(round(now[0]*1000),index);owner.tick()
        assert not owner.monitor_enabled and owner.capture.state=='CANCELLED'
        assert owner.public()['handsfree_dialogue']['state']=='PAUSED'
    finally:owner.close()


def test_playback_does_not_open_mic_and_full_ack_then_tail_guard_still_required():
    now,source,tx,inner,owner=setup()
    try:
        arm(now,source,owner);speech(owner)
        inner.state.update(phase='SPEAKING',playing=True);owner.tick()
        assert owner.capture.counter==1 and not owner._recording()
        inner.state.update(phase='IDLE',playing=False);tx.pending=False
        inner.completions.append(({'request_id':'req-1','capture_id':'cap-1'},{}));owner.tick()
        assert owner.capture.counter==1
        tx.last_ack={'request_id':'req-1','committed':True}
        now[0]+=.6;source[0]=view(round(now[0]*1000),3);owner.tick()
        assert owner.capture.counter==2
        speech(owner);assert tx.selections==[False]  # Same conversation for subsequent turns.
    finally:owner.close()


def test_initial_asr_rejection_recovers_without_assistant_output():
    now,source,tx,inner,owner=setup()
    try:
        arm(now,source,owner);speech(owner)
        tx.results.append({'context':{'request_id':'req-1','capture_id':'cap-1'},'entry_rejected':True})
        owner.tick()
        assert not owner.auto_enabled and not owner.monitor_owned and not inner.state['playing']
        assert owner.monitor_enabled and owner.monitor_reason=='NO_VALID_INITIAL_SPEECH'
    finally:owner.close()


def test_silence_timeout_releases_mic_without_creating_empty_conversation():
    now,source,tx,inner,owner=setup()
    try:
        arm(now,source,owner)
        now[0]=32.;source[0]=view(32000,3);owner.tick()
        assert owner.capture.state=='CANCELLED' and tx.selections==[] and not tx.submitted
    finally:owner.close()


def test_entry_rejected_by_http_never_invokes_model_or_tts(tmp_path):
    from tools.asr_server import AsrServer
    from tools.board_model_host import ModelHandler
    from board.runtime.audio.voice_channel import VoiceChannel
    from tests.framework.test_long_conversation import host
    model=host(tmp_path);model.lock=threading.Lock();model.voice=MagicMock()
    class Engine:
        model_id='TEST_ONLY'
        def transcribe(self,pcm):return '嗯'
    server=AsrServer(('127.0.0.1',0),Engine(),handler=ModelHandler);server.models=model
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    channel=VoiceChannel('127.0.0.1',server.server_port)
    try:
        with patch('tools.voice_channel_source.serve_channel') as serve:
            with pytest.raises(EntryRejected):
                pcm=b'\xe8\x03'*3200
                meta=dict(wire.owner(),pcm_sha256=hashlib.sha256(pcm).hexdigest())
                channel.exchange(meta,pcm,lambda h,p:None,visual_entry=True,conversation='c'*32)
            serve.assert_not_called();model.voice.generate.assert_not_called()
        assert model.conversations.health()['turns']==0
    finally:channel.close();server.shutdown();server.server_close();thread.join(2)


def test_silence_cannot_be_promoted_by_hallucinated_asr_words(tmp_path):
    from tools.asr_server import AsrServer
    from tools.board_model_host import ModelHandler
    from board.runtime.audio.voice_channel import VoiceChannel
    from tests.framework.test_long_conversation import host
    model=host(tmp_path);model.lock=threading.Lock();model.voice=MagicMock()
    engine=MagicMock();engine.model_id='TEST_ONLY';engine.transcribe.return_value='嗯没有'
    server=AsrServer(('127.0.0.1',0),engine,handler=ModelHandler);server.models=model
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    channel=VoiceChannel('127.0.0.1',server.server_port);pcm=b'\0\0'*3200
    try:
        meta=dict(wire.owner(),pcm_sha256=hashlib.sha256(pcm).hexdigest())
        with pytest.raises(EntryRejected):
            channel.exchange(meta,pcm,lambda h,p:None,visual_entry=True,conversation='c'*32)
        engine.transcribe.assert_not_called();model.voice.generate.assert_not_called()
        assert model.conversations.health()['turns']==0
    finally:channel.close();server.shutdown();server.server_close();thread.join(2)


def test_valid_first_turn_http_negotiates_entry_and_uses_durable_conversation(tmp_path):
    from tools.asr_server import AsrServer
    from tools.board_model_host import ModelHandler
    from board.runtime.audio.voice_channel import VoiceChannel
    from tests.framework.test_long_conversation import host
    from tools.voice_channel_source import channel_frames
    model=host(tmp_path);model.lock=threading.Lock();model.latency_options={}
    model.voice=wire.VoiceChannelTests().fixture_models(tmp_path).voice
    class Engine:
        model_id='TEST_ONLY'
        def transcribe(self,pcm):return '你好呀'
    server=AsrServer(('127.0.0.1',0),Engine(),handler=ModelHandler);server.models=model
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    channel=VoiceChannel('127.0.0.1',server.server_port)
    def source(*args,**kwargs):
        return channel_frames(*args,**kwargs,stream_factory=wire.VoiceChannelTests.fake_stream)
    try:
        with patch('tools.voice_channel_source.channel_frames',source):
            pcm=b'\xe8\x03'*3200
            meta=dict(wire.owner(),pcm_sha256=hashlib.sha256(pcm).hexdigest())
            result=channel.exchange(meta,pcm,lambda h,p:None,visual_entry=True,conversation='c'*32)
        assert result['network_complete'] and not result['playback_verified']
        assert model.conversations.records('c'*32)[0]['status']=='generated'
    finally:channel.close();server.shutdown();server.server_close();thread.join(2)


def test_ui_primary_button_controls_monitor_without_start_dialog():
    from types import SimpleNamespace
    from tools.board_avatar_gtk import BoardAvatarStage
    stage=object.__new__(BoardAvatarStage);stage.config={'handsfree_dialogue':True,'automatic_turns':True}
    calls=[];stage.controller=SimpleNamespace(handsfree_toggle=lambda:calls.append('toggle') or 'id')
    assert stage.command({'type':'record_toggle'})['queued']
    assert calls==['toggle']


def test_face_metadata_uses_same_source_frame_and_does_not_change_matching_targets():
    from board.identity.face_targets import FaceTargetService
    face=[20.,20.,70.,80.,35.,40.,65.,40.,50.,58.,38.,78.,62.,78.,.99]
    now=[1000];packets=[]
    class Detector:
        def detect(self,image):return [face]
    service=FaceTargetService(Detector,lambda *args:packets.append(args),'camera',clock=lambda:now[0])
    service.ready=True
    service.process((None,1,1000),Detector());now[0]=1700
    service.process((None,2,1700),Detector())
    v=service.view();a=v['face_attention']
    assert v['face_count']==1 and a['target']==v['face_target']
    assert a['frame_id']==2 and a['captured_mono_ms']==1700 and a['frontal']
    assert packets[-1][-1]==v['face_target']
    now[0]=2700
    assert service.view()['face_attention'] is None
