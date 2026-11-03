"""Stream visibility, mouth gating, cancellation and full-playback acknowledgement."""
import hashlib
import tempfile
import wave
from pathlib import Path
import pytest
from tools.demo_script import create_demo_core
from tools.streaming_controller import StreamingController
from tests.test_realtime_stage import Jobs
from tests.framework.test_voice_channel import owner


class Output:
    def __init__(self):
        self.active=self.paused=False;self.duration=0.;self.pcm=[];self.hints=[]
        self.state={'clock':0.,'ready':False,'done':False,'error':'','audible':False,'track':None}
    def read(self):return dict(self.state)
    @property
    def ready(self):return self.state['ready']
    def position(self):return self.state['clock']
    def stop(self):self.active=False;self.paused=False
    def begin_stream(self):self.active=True
    def append_pcm(self,pcm,start):self.pcm.append(pcm)
    def feedback(self,value):self.hints.append(value)
    def end_stream(self):pass
    def finished(self):
        if self.active and self.state['done']:self.active=False;return True
        return False


@pytest.fixture(scope='module')
def core():return create_demo_core('reuse')


@pytest.fixture
def stream(core):
    core.fsm.reset();core.reset_playback()
    output=Output();clock=[100.]
    controller=StreamingController(core,Jobs(),output,clock=lambda:clock[0])
    meta=owner();controller.channel_event({'kind':'start'},b'',meta,{},100.)
    return controller,output,meta


def test_mouth_stays_closed_before_actual_sink_audio_and_while_buffering(stream):
    controller,output,meta=stream
    controller.channel_event({'kind':'text','text':'今天辛苦啦。'},b'',meta,{},100.)
    pcm=b'\x00\x20'*4800
    controller.channel_event({'kind':'audio','start_sample':0},pcm,meta,{},100.)
    first=controller.tick();assert first['speech_gain']==0
    output.state.update(clock=.05,ready=True,audible=True,track='answer')
    first=controller.tick();assert first['speech_gain']>0 and first['mouth_level']>0
    output.state['audible']=False
    assert controller.tick()['speech_gain']==0


def test_ack_is_not_emitted_on_network_completion_before_audio_completion(stream):
    controller,output,meta=stream
    result={'sample_count':480,'pcm_sha256':'a'*64,'reply_text':'回答'}
    controller.channel_complete(meta,result);controller.tick();assert controller.take_completion() is None
    output.state.update(done=True,clock=.1)
    controller.tick();assert controller.take_completion()==(meta,result)
    assert controller.take_completion() is None


def test_cancel_prevents_stale_stream_pcm_and_ack(stream):
    controller,output,meta=stream
    controller.cancel()
    controller.channel_event({'kind':'audio','start_sample':0},b'\x01\x00'*480,meta,{},100.)
    controller.channel_complete(meta,{'sample_count':480})
    assert output.pcm==[] and controller.take_completion() is None and controller.stream is None


def test_feedback_skipped_when_answer_arrives_first(stream):
    controller,output,meta=stream
    controller.channel_event({'kind':'audio','start_sample':0},b'\x01\x00'*480,meta,{},100.)
    controller.channel_event({'kind':'thinking','feedback_id':'thinking'},b'',meta,{},100.)
    assert output.hints==[]


def test_finished_feedback_returns_to_thinking_until_real_answer(stream,tmp_path):
    controller,output,meta=stream
    path=tmp_path/'thinking.wav'
    with wave.open(str(path),'wb') as audio:
        audio.setparams((1,2,24000,0,'NONE','not compressed'))
        audio.writeframes(b'\x00\x20'*4800)
    feedback={'thinking':{'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                          'reply_text':'我想一下，再回答你。'}}
    controller.channel_event({'kind':'thinking','feedback_id':'thinking'},b'',meta,feedback,100.)
    output.state.update(clock=.05,ready=True,audible=True,track='feedback')
    controller.tick()
    assert controller.phase=='THINKING_FEEDBACK'
    output.state.update(clock=.2,audible=False,track=None,answer_started_at=None)
    assert controller.tick()['speech_gain']==0
    assert controller.core.fsm.state.label=='THINKING'
    controller.channel_event({'kind':'text','text':'答案是174元。'},b'',meta,feedback,100.)
    controller.channel_event({'kind':'audio','start_sample':0},b'\x00\x20'*4800,meta,feedback,100.)
    output.state.update(clock=.25,audible=True,track='answer',answer_started_at=101.)
    assert controller.tick()['speech_gain']>0
    assert controller.phase=='SPEAKING'
