"""Live playback ordering, interruption, frozen clocks and host-response guards."""
from pathlib import Path
import pytest
from tools.demo_script import create_demo_core
from tools.realtime_controller import RealtimeController
from tools.realtime_dialogue import DialogueConnection
from board.runtime.dialogue_client.adapter import DialogueResponse

def test_export_metrics_accept_numpy_activity_values():
    import json
    import numpy as np
    from tools.realtime_metrics import summarize
    row={'interval_ms':np.float64(16.5),'blink_active':True,'playing':True,'speech_gain':np.float64(1),'mouth_level':np.float64(.8)}
    result=summarize([row]);assert json.loads(json.dumps(result))['speech_open_mouth_samples']==1

class Jobs:
    root=Path('test-cache')
    def __init__(self):self.jobs={}
    def submit(self,text,emotion):
        key=str(len(self.jobs)+1);self.jobs[key]={'id':key,'status':'QUEUED','text':text};return self.jobs[key]
    def get(self,key):return self.jobs[key]
    def cancel(self,key):self.jobs[key]['status']='CANCELLED'
    def complete(self,key):
        self.jobs[key].update(status='COMPLETE',result={'key':'a'*64,'sha256':'verified','cache_hit':True,'duration_seconds':2.,
                                    'envelope':{'hop_seconds':.01,'gains':[1]*190+[0]*10,'levels':[.8]*190+[0]*10}})

class Output:
    def __init__(self,clock):self.clock=clock;self.active=False;self.paused=False;self.duration=0.;self.position_value=0.;self.play_calls=[]
    def play(self,path,sha256=None):
        self.active=True;self.paused=False;self.duration=2.;self.position_value=0.;self.started=self.clock[0];self.play_calls.append((path,sha256))
    def position(self):
        if self.active and not self.paused:self.position_value=min(self.duration,self.clock[0]-self.started)
        return self.position_value
    def finished(self):
        if self.active and not self.paused and self.position()>=self.duration:self.active=False;return True
        return False
    def stop(self):self.active=False;self.paused=False
    def pause(self,value):
        if value:self.position()
        else:self.started=self.clock[0]-self.position_value
        self.paused=value

@pytest.fixture(scope='module')
def core():return create_demo_core('reuse')

@pytest.fixture
def stage(core):
    core.fsm.reset();core.reset_playback();clock=[100.];jobs=Jobs();output=Output(clock)
    controller=RealtimeController(core,jobs,output,clock=lambda:clock[0]);controller.tick()
    return controller,jobs,output,clock

def test_voice_wait_stays_closed_then_uses_audio_output_time(stage):
    controller,jobs,output,clock=stage;key=controller.submit('你好。')
    clock[0]+=.1;meta=controller.tick();assert controller.phase=='VOICE_PREPARING' and not output.active
    assert meta['speech_gain']==meta['mouth_level']==0
    jobs.complete(key);controller.tick();assert output.active and output.play_calls[0][1]=='verified'
    clock[0]+=.2;meta=controller.tick();assert meta['mouth_level']==pytest.approx(.8) and meta['speech_gain']==1
    clock[0]+=3;controller.tick();assert not output.active and controller.phase=='IDLE'

@pytest.mark.parametrize('action,state',[('ack_nod','ACK_NOD'),('deny_shake','DENY_SHAKE'),('emo_surprised','AWAKE'),('emo_puzzled','PUZZLED')])
def test_one_shot_finishes_before_voice_start(stage,action,state):
    controller,jobs,output,clock=stage;key=controller.submit('我们继续吧。','happy',action)
    jobs.complete(key);controller.tick();assert controller.core.fsm.state.label==state and not output.active
    for _ in range(600):
        clock[0]+=1/60;controller.tick()
        if output.active:break
    assert output.active and controller.core.fsm.state.label=='SPEAKING'
    assert len(output.play_calls)==1 and controller.core.fsm.rejected_count==0

def test_cancel_pending_late_audio_and_old_dialogue_are_discarded(stage):
    controller,jobs,output,clock=stage;key=controller.submit('第一句。');old_generation=controller.core.talk_gen
    controller.cancel();jobs.complete(key);clock[0]+=1;controller.tick()
    assert not output.play_calls and controller.pending is None
    assert not controller.accept_dialogue(old_generation,'迟到的回复。')
    assert controller.metrics['late_results_dropped']==1

def test_pause_freezes_audio_mouth_and_blink_then_cancel_works(stage):
    controller,jobs,output,clock=stage;key=controller.submit('你好。');jobs.complete(key);controller.tick()
    clock[0]+=.4;controller.tick();controller.toggle_pause();before=controller.public()
    clock[0]+=20;controller.tick();paused=controller.public()
    for field in ('audio_time','visual_time','speech_gain','mouth_level','blink_phase'):assert paused[field]==before[field]
    controller.toggle_pause();clock[0]+=.1;controller.tick();assert controller.public()['audio_time']>before['audio_time']
    controller.cancel();assert not output.active and controller.pause_started is None

def test_idle_blinks_after_cancel_and_new_turn_does_not_reset_schedule(stage):
    controller,jobs,output,clock=stage;clock[0]+=1.43;assert controller.tick()['blink_active']
    schedule=controller.facials.eyes.schedule;starts=list(schedule.starts)
    controller.submit('一句话。');controller.cancel();assert schedule.starts==starts
    clock[0]+=.02;assert controller.tick()['blink_active'] and not output.active

def test_invalid_new_request_preserves_current_audio(stage):
    controller,jobs,output,clock=stage;key=controller.submit('正在说话。');jobs.complete(key);controller.tick()
    with pytest.raises(ValueError):controller.submit('新句子。',action='wave')
    assert output.active and len(output.play_calls)==1

def test_full_speech_queue_returns_to_idle_instead_of_stuck_thinking(stage):
    controller,jobs,output,clock=stage
    def reject(*args):raise ValueError('Speech queue is full')
    jobs.submit=reject
    with pytest.raises(ValueError,match='queue is full'):controller.submit('你好。')
    assert controller.core.fsm.state.label=='IDLE' and controller.phase=='IDLE' and controller.pending is None

def test_device_start_wait_has_closed_mouth_and_records_actual_audio_start(stage):
    controller,jobs,output,clock=stage;output.ready=False;key=controller.submit('你好。');jobs.complete(key)
    meta=controller.tick();assert controller.phase=='VOICE_STARTING' and meta['speech_gain']==0
    assert not controller.public()['playing'] and controller.turns==[]
    clock[0]+=.4;output.ready=True;output.started_at=clock[0];controller.tick()
    assert controller.phase=='SPEAKING' and controller.turns[0]['request_to_audio_seconds']==pytest.approx(.4)
    controller.tick();assert len(controller.turns)==1

def test_cancel_during_device_open_never_announces_old_audio_start(stage):
    controller,jobs,output,clock=stage;output.ready=False;key=controller.submit('你好。');jobs.complete(key);controller.tick()
    controller.cancel();output.ready=True;clock[0]+=.5;controller.tick()
    assert controller.audio_waiting is None and not controller.public()['playing'] and controller.turns==[]

class Host:
    is_connected=True
    def __init__(self,**changes):self.changes=changes
    def send_request(self,request,timeout_ms):return DialogueResponse(request_id=request.request_id,reply_text='你好。',emotion='friendly',**self.changes)
    def close(self):pass

def test_optional_host_preserves_contract_and_rejects_visual_claims():
    connection=DialogueConnection({'enabled':True});connection.adapter=Host()
    from board.runtime.dialogue_client.adapter import DialogueRequest
    request=DialogueRequest(request_id='test',allowed_emotions=['friendly'])
    try:
        connection._run(request,7);result=connection.results.get_nowait();assert result['generation']==7 and result['text']=='你好。'
        connection.adapter=Host(visual_claims=[{'object':'person'}]);connection._run(request,8)
        assert '视觉' in connection.results.get_nowait()['error']
        connection.adapter=Host(avatar_action='wave');connection._run(request,9)
        assert '不支持' in connection.results.get_nowait()['error']
    finally:connection.close()
