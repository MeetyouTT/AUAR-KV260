"""Exercise candidate code with real FSM/assets and deterministic sink time."""
import importlib.util
from pathlib import Path
import sys
import pytest

HERE=Path(__file__).resolve().parent
APP=HERE.parents[1]/'aura'
sys.path.insert(0,str(APP))

def load(name,relative):
    spec=importlib.util.spec_from_file_location(name,HERE/'action_sources'/relative)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

StreamingController=load('tools.motion_streaming_controller','tools/streaming_controller.py').StreamingController
RuntimeFSM=load('board.runtime.motion_fsm','board/runtime/fsm.py').RuntimeFSM
wire=load('common.motion_voice_channel','common/voice_channel.py')
from tools.demo_script import create_demo_core
class Output:
    def __init__(self):
        self.active=self.paused=False;self.duration=0.
        self.state=dict(clock=0.,ready=False,done=False,error='',audible=False,track=None)
    def read(self):return dict(self.state)
    @property
    def ready(self):return self.state['ready']
    def position(self):return self.state['clock']
    def stop(self):self.active=False;self.paused=False
    def begin_stream(self):self.active=True
    def append_pcm(self,pcm,start):pass
    def end_stream(self):pass
    def finished(self):
        if self.active and self.state['done']:self.active=False;return True
        return False

def owner():
    return dict(protocol='aura-asr-1',board_boot_id='test-boot',session_id='test-session',
                request_id='motion-test',generation=1,capture_id='test-capture',
                sample_count=3200,pcm_sha256='a'*64,budget_ms=5000)

@pytest.fixture(scope='module')
def core():
    core=create_demo_core('reuse');core.fsm=RuntimeFSM(publish_state_changes=False)
    return core

@pytest.fixture
def stream(core):
    core.fsm.reset();core.reset_playback();output=Output();clock=[100.]
    controller=StreamingController(core,object(),output,clock=lambda:clock[0]);meta=owner()
    controller.channel_event({'kind':'start'},b'',meta,{},100.)
    controller.channel_event({'kind':'text','text':'这是一次动作连接测试。'},b'',meta,{},100.)
    controller.channel_event({'kind':'audio','start_sample':0},b'\x00\x20'*24000,meta,{},100.)
    return controller,output,meta,clock

def control(c,meta,action,sample=0):
    c.channel_event(dict(kind='control',emotion='friendly',action=action,at_sample=sample),b'',meta,{},100.)

def audible(output,seconds=0):
    output.state.update(clock=seconds,answer_clock=seconds,ready=True,audible=True,
                        track='answer',answer_started_at=100.)

@pytest.mark.parametrize('action,state,asset',[
    ('ack_nod','ACK_NOD','ack_nod'),('deny_shake','DENY_SHAKE','deny_shake'),
    ('emo_surprised','AWAKE','emo_surprised'),('emo_puzzled','PUZZLED','emo_puzzled')])
def test_audible_control_routes_to_existing_material(stream,action,state,asset):
    c,out,meta,clock=stream;control(c,meta,action)
    c.tick();assert c.core.fsm.state.label=='THINKING'
    audible(out);frame=c.tick()
    assert c.core.fsm.state.label==state
    assert frame['asset']==asset
    assert c.log[-1]['event']=='speech_action_started'
    # The source advances in wall time instead of repeatedly restarting.
    clock[0]+=.3;out.state.update(clock=.3,answer_clock=.3)
    second=c.tick();assert second['index']!=frame['index']

def test_feedback_pause_and_future_pcm_do_not_trigger_reaction(stream):
    c,out,meta,clock=stream;control(c,meta,'ack_nod',24000)
    out.state.update(audible=True,track='feedback',ready=True,clock=2.)
    c.tick();assert not c.stream['actions']
    audible(out,.5);c.tick();assert not c.stream['actions']
    out.paused=True;audible(out,1.1);c.tick();assert not c.stream['actions']
    out.paused=False;c.tick();assert len(c.stream['actions'])==1

def test_cancel_drops_old_controls(stream):
    c,out,meta,clock=stream;control(c,meta,'ack_nod');c.cancel()
    control(c,meta,'deny_shake');audible(out);c.tick()
    assert c.stream is None
    assert not any(row['event']=='speech_action_started' for row in c.log)

def test_puzzled_returns_to_speaking_after_visible_budget(stream):
    c,out,meta,clock=stream;control(c,meta,'emo_puzzled');audible(out)
    c.tick();clock[0]+=1.;out.state.update(clock=1.,answer_clock=1.)
    c.tick();assert c.core.fsm.state.label.startswith('SPEAKING')

@pytest.mark.parametrize('action',['ack_nod','deny_shake','emo_surprised'])
def test_burst_finishes_once_then_resumes_audio_material(stream,action):
    c,out,meta,clock=stream;control(c,meta,action);audible(out)
    c.tick()
    for i in range(1,41):
        clock[0]=100.+i*.125;out.state.update(clock=i*.125,answer_clock=i*.125)
        frame=c.tick()
        if c.core.fsm.state.label.startswith('SPEAKING'):break
    assert c.core.fsm.state.label.startswith('SPEAKING')
    assert len(c.stream['actions'])==1
    out.state.update(done=True);c.channel_complete(meta,{'sample_count':24000})
    c.tick();assert c.phase=='IDLE'

def test_duplicate_control_does_not_restart_gesture(stream):
    c,out,meta,clock=stream;control(c,meta,'ack_nod');audible(out);c.tick()
    control(c,meta,'ack_nod');clock[0]+=.3;out.state.update(clock=.3,answer_clock=.3)
    c.tick();assert len(c.stream['actions'])==1

def test_live_speech_keeps_real_body_frames_and_local_mouth(stream):
    import numpy as np
    c,out,meta,clock=stream;c.core.idle_gain=0
    audible(out,.05);first=c.tick()
    assert first['body_asset']=='idle_normal'
    original=c.facials.body.sample(c.now())[0]['image']
    assert np.array_equal(np.asarray(first['image'])[165:],np.asarray(original)[165:])
    clock[0]+=.5;audible(out,.55);second=c.tick()
    assert second['body_source_position']!=first['body_source_position']
    assert not np.array_equal(np.asarray(first['image'])[165:],np.asarray(second['image'])[165:])
    c.core.idle_gain=1

@pytest.mark.parametrize('text,action',[
    ('好的，我记住这件事了。','ack_nod'),('抱歉，我不能这样做。','deny_shake'),
    ('哇，这个消息太棒了！','emo_surprised'),('我没听清，你能再说一遍吗？','emo_puzzled')])
def test_host_control_precedes_corresponding_audio(tmp_path,text,action):
    import hashlib,io,wave
    host=load('tools.motion_voice_source','tools/voice_channel_source.py')
    host.ChannelWriter=wire.ChannelWriter
    wav=tmp_path/'reply.wav'
    with wave.open(str(wav),'wb') as audio:
        audio.setparams((1,2,24000,0,'NONE','not compressed'));audio.writeframes(b'\x00\x20'*4800)
    class Voice:
        def generate(self,part):
            return dict(path=str(wav),sha256=hashlib.sha256(wav.read_bytes()).hexdigest())
    class Models:
        histories={};voice=Voice();latency_options={'coalesce_chat':True,'first_sentence_chat':True}
    class Reply:
        def __init__(self,*args,**kwargs):pass
        def __iter__(self):
            yield 'text',text
            yield 'speech_ready',None
            yield 'complete',dict(reply_text=text,emotion='friendly',avatar_action='')
        def cancel(self):pass
    frames=list(host.channel_frames(Models(),owner(),'测试',5,model='fixture',host='fixture',stream_factory=Reply,motion=True))
    decoded=[wire.read_frame(io.BytesIO(frame))[0] for frame in frames]
    assert decoded[-1]['kind']=='end',decoded[-1]
    first_audio=next(i for i,row in enumerate(decoded) if row['kind']=='audio')
    cue=next(row for row in decoded[:first_audio] if row['kind']=='control')
    assert cue['action']==action and cue['at_sample']==0

@pytest.mark.parametrize('action',['ack_nod','deny_shake','emo_surprised','emo_puzzled'])
def test_wire_accepts_all_four_whitelisted_actions(action):
    writer=wire.ChannelWriter(owner())
    writer.frame('start',context=owner(),sample_rate=24000,channels=1,sample_width=2)
    writer.frame('control',emotion='neutral',action=action,at_sample=0)
    with pytest.raises(ValueError):writer.frame('control',emotion='neutral',action='unknown',at_sample=0)
