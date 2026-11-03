"""Actual recording/stream/start/ACK/control components, synthetic IO only."""
import copy,hashlib,io,json,struct,time,traceback,uuid,wave
from pathlib import Path
from types import SimpleNamespace
import pytest
from base_composition import Composition,HERE,RELEASE
from tools.voice_first_recording import VoiceFirstRecordingController
from tools.formal_yuki import paired_recording_type,native_controller_type,create_native_core
from tools.production_listening import ProductionMonitorChoice,bind_automatic_listening
from tools.production_memory_presentation import bind_presentation
from tools.board_business_gui import GuiBoardBusiness
from board.runtime.audio.capture import CapturedAudio,FORMAT
from host.model_service.protocol import AudioRef
from common.voice_wire import wav_payload,PROTOCOL,REVISION

QUERY='你可以根据我的声音辨别我是谁吗'

class PolicyRuntime:
    """Only choose the production UI wrapper branch; actual Runtime/store stay synthetic.

    This adapter does not authorize board origin, bootstrap, filesystem access,
    actor selection or identity. All operational attributes delegate unchanged.
    """
    def __init__(self,runtime):self.actual=runtime;self.config=SimpleNamespace(data_origin='board')
    def __getattr__(self,name):return getattr(self.actual,name)

class Capture:
    serial=0
    def __init__(self,playback_active,**kwargs):
        self.playback_active=playback_active;self.state='IDLE';self.result=None;self.speech=False;self.on_speech_start=None
    def start(self):
        assert not self.playback_active()
        Capture.serial+=1;self.cid='synthetic-recording-'+str(Capture.serial);self.state='RECORDING';self.speech=False
        return self.cid
    def ready(self,index):
        assert self.state=='RECORDING'
        if self.on_speech_start:self.on_speech_start()
        raw=struct.pack('<h',1000+index)*48000
        self.result=CapturedAudio(self.cid,AudioRef(index,0,48000,FORMAT),raw,1000,4000)
        self.state='READY';self.speech=False
    def snapshot(self):return dict(state=self.state,error='',sample_count=48000 if self.result else 0,speech_active=self.speech)
    def take(self):
        value,self.result=self.result,None;self.state='IDLE';return value
    def cancel(self):self.state='CANCELLED';self.result=None
    def close(self):self.cancel()

class Output:
    def __init__(self,clock):
        self.clock=clock;self.active=False;self.paused=False;self.ready=True;self.duration=0.;self.raw=b'';self.ended=False;self.finish=False
        self.started_at=None;self.answer_started_at=None;self.error=''
    def stop(self):self.active=False;self.raw=b'';self.ended=False;self.finish=False
    def begin_stream(self):self.stop();self.active=True;self.started_at=self.clock();self.answer_started_at=None
    def append_pcm(self,raw,start_sample):
        assert start_sample==len(self.raw)//2
        self.raw+=raw;self.duration=len(self.raw)/48000.;self.answer_started_at=self.clock()
    def end_stream(self):self.ended=True
    def read(self):return dict(error=self.error,audible=self.active and bool(self.raw),track='answer' if self.raw else 'none',
        answer_clock=0.,answer_started_at=self.answer_started_at,started_at=self.started_at,device_state='PLAYING' if self.active else 'IDLE_READY')
    def position(self):return 0.
    def finished(self):
        if self.active and self.ended and self.finish:self.active=False;self.finish=False;return True
        return False
    def pause(self,value):self.paused=value

def feedback(path):
    buffer=io.BytesIO()
    with wave.open(buffer,'wb') as audio:audio.setparams((1,2,24000,0,'NONE','not compressed'));audio.writeframes(b'\0\0'*2400)
    raw=buffer.getvalue();path.write_bytes(raw)
    meta=dict(protocol=PROTOCOL,source_kind='actual',engine='omnivoice',revision=REVISION,num_step=16,
        reply_text='合成等待提示。',emotion='neutral',sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),duration_seconds=.1)
    return {'thinking':dict(wav_payload(meta,raw),path=str(path))}

class Integration:
    def __init__(self,path,monkeypatch):
        self.base=Composition(path,monkeypatch);self.runtime=self.base.runtime;self.speaker=self.base.business
        self.reset_calls=[];self.samples=[]
        original=self.runtime.jobs.reset_enrollment
        def reset():
            self.reset_calls.append([frame.name for frame in traceback.extract_stack(limit=14)])
            return original()
        self.runtime.jobs.reset_enrollment=reset
        # Register only in the fresh synthetic private store before opening the
        # real recording owner. No live/template source is consulted.
        self.base.say('登记声纹，我叫合成测试')
        for i in range(3):self.base.say('合成独立登记段'+str(i))
        self.base.say('确认保存声纹');assert self.base.voice_count()==1
        self.base.encoder.calls=0
        self.output=Output(self.base.mono)
        self.visual=native_controller_type()(create_native_core(),SimpleNamespace(cancel=lambda value:None),self.output,clock=self.base.mono)
        self.visual.render_requested=False
        self.gui=object.__new__(GuiBoardBusiness);self.gui.runtime=self.runtime;self.gui.recording=None
        self.gui.character_pair=self.runtime.character_pair
        owner_type=paired_recording_type(VoiceFirstRecordingController,self.runtime.character_pair)
        settings=ProductionMonitorChoice(path)
        self.recording=owner_type(self.visual,transcriber=self.runtime.jobs,boot_id='synthetic-boot',
            attention_provider=lambda:None,monitor_settings=settings,clock=self.base.mono,
            auto_capture_factory=Capture,capture_factory=Capture,barge_enabled=False,early_listen=False,
            wake_word_required=False,device_observer=False,visual_social=False)
        self.gui.bind_recording(self.recording);self.runtime.capture_idle=self.gui.capture_idle
        policy=SimpleNamespace(runtime=PolicyRuntime(self.runtime),character_pair=self.runtime.character_pair,recording=self.recording)
        self.stage=SimpleNamespace(board_business=policy,closed=False)
        bind_automatic_listening(self.recording,policy,self.runtime.character_pair)
        bind_presentation(self.stage,self.recording,clock=self.base.mono)
        assets=feedback(path/'synthetic-feedback.wav');self.runtime.jobs.feedback_provider=lambda:assets
        self.runtime.jobs.prepare_feedback();self.runtime.start()
        self.pump(lambda:self.recording.capture is not None and self.recording._recording())
        self.initial_resets=len(self.reset_calls)
    def pump(self,predicate,seconds=4.):
        until=time.monotonic()+seconds
        while time.monotonic()<until:
            self.recording.tick()
            self.speaker.pool.submit(lambda:None).result(timeout=2)
            if predicate():return
            time.sleep(.003)
        raise AssertionError('Synthetic integration phase did not reach its bounded target')
    def say(self,text,index):
        assert self.recording._recording()
        self.base.asr.text=text;self.recording.capture.ready(index)
        return self.finish_turn(index)
    def finish_turn(self,index):
        self.pump(lambda:self.visual.stream is not None and self.visual.stream['network'] is not None and self.output.ended)
        stream=self.visual.stream;receipt=stream['network']
        assert len(self.output.raw)//2==receipt['sample_count']
        assert hashlib.sha256(self.output.raw).hexdigest()==receipt['pcm_sha256']
        before=self.speaker.health()['self_match_probe']
        reply=self.visual.reply
        self.output.finish=True
        self.pump(lambda:self.recording.transcription['state']=='ANSWERED')
        self.pump(lambda:bool((self.runtime.jobs.public().get('last_playback_ack') or {}).get('committed')))
        self.base.mono.now+=.6
        self.pump(lambda:self.recording._recording())
        after=self.speaker.health()['self_match_probe']
        row=dict(index=index,before_playback_phase=before['phase'],after_rearm_phase=after['phase'],
            distinct=after['distinct_captures'],reset_calls=len(self.reset_calls)-self.initial_resets,
            committed=True,candidate_completed=after['candidate_completed'])
        self.samples.append(row)
        return reply,row
    def close(self):
        self.recording.close();self.runtime.close()

@pytest.fixture
def integration(tmp_path,monkeypatch):
    value=Integration(tmp_path/'synthetic-integration',monkeypatch)
    try:yield value
    finally:value.close()

def test_full_Runtime_init_and_actual_normal_record_stream_ACK_rearm_do_not_reset_probe(integration):
    value=integration
    for index in (1,2,3):
        reply,row=value.say(QUERY,index+10)
        assert row['reset_calls']==0
        assert row['distinct']==index
        assert row['after_rearm_phase']==('CANDIDATE' if index==3 else 'COLLECTING')
    assert value.base.encoder.calls==3
    assert '声音候选称呼是合成测试' in reply
    (HERE/'NORMAL_CHAIN_METADATA.json').write_text(json.dumps(dict(samples=value.samples,
        initial_session_reset_calls=value.initial_resets,normal_turn_reset_calls=0,
        full_Runtime_constructor_used=True,synthetic_IO=True,UI_production_branch_adapter=True,
        real_board_bootstrap_guard_tested=False,board_accessed=False),indent=2)+'\n',encoding='utf-8')

def test_explicit_recording_cancel_calls_original_reset_and_clears_probe(integration):
    value=integration;value.say(QUERY,20)
    count=len(value.reset_calls)
    value.recording.cancel();value.speaker.pool.submit(lambda:None).result(timeout=2)
    assert len(value.reset_calls)==count+1
    assert value.speaker.health()['self_match_probe']['phase']=='CANCELLED'

def test_real_auto_fail_calls_original_reset_without_becoming_a_runtime_fault(integration):
    value=integration;value.say(QUERY,30)
    count=len(value.reset_calls)
    value.recording._auto_fail('synthetic fixed failure')
    value.speaker.pool.submit(lambda:None).result(timeout=2)
    assert len(value.reset_calls)==count+1
    assert value.speaker.health()['self_match_probe']['phase']=='CANCELLED'

def test_original_thirty_second_silence_then_new_session_resets_twice(integration):
    value=integration;value.say(QUERY,40)
    count=len(value.reset_calls)
    value.base.mono.now+=30.1;value.recording.tick()
    value.speaker.pool.submit(lambda:None).result(timeout=2)
    assert value.recording.last_stop_reason=='CONVERSATION_SILENCE'
    assert len(value.reset_calls)==count+1
    assert value.speaker.health()['self_match_probe']['phase']=='CANCELLED'
    value.base.mono.now+=.21
    value.pump(lambda:value.recording._recording())
    assert len(value.reset_calls)==count+2 and value.base.voice_count()==1
    (HERE/'SILENCE_RESET_METADATA.json').write_text(json.dumps(dict(reason='CONVERSATION_SILENCE',
        reset_count_at_stop=1,reset_count_after_new_session=2,
        stop_stack=value.reset_calls[count],new_session_stack=value.reset_calls[count+1],
        formal_synthetic_voice_count=value.base.voice_count(),board_accessed=False),indent=2)+'\n',encoding='utf-8')

def test_public_status_collects_ready_audio_without_reset_then_normal_ACK(integration):
    value=integration;count=len(value.reset_calls)
    value.base.asr.text=QUERY;value.recording.capture.ready(50)
    value.recording.public()
    assert value.recording.transcription['state']=='TRANSCRIBING'
    assert len(value.reset_calls)==count
    reply,row=value.finish_turn(50)
    assert row['distinct']==1 and row['reset_calls']==0

def test_handled_output_error_resets_original_session_without_uncaught_tick_exception(integration):
    value=integration;count=len(value.reset_calls)
    value.base.asr.text=QUERY;value.recording.capture.ready(60)
    value.pump(lambda:value.visual.stream is not None and value.visual.stream['network'] is not None)
    assert value.speaker.health()['self_match_probe']['phase']=='COLLECTING'
    value.output.error='synthetic fixed output failure'
    value.recording.tick()
    value.speaker.pool.submit(lambda:None).result(timeout=2)
    assert len(value.reset_calls)>=count+1
    assert value.recording.last_stop_reason=='SERVICE_ERROR'
    assert value.speaker.health()['self_match_probe']['phase']=='CANCELLED'

def test_original_ACK_failure_reaches_auto_fail_and_reset(integration,monkeypatch):
    value=integration;count=len(value.reset_calls)
    def failed_ack(*args,**kwargs):raise ValueError('synthetic fixed ACK rejection')
    monkeypatch.setattr(value.runtime.controller,'acknowledge',failed_ack)
    value.base.asr.text=QUERY;value.recording.capture.ready(70)
    value.pump(lambda:value.visual.stream is not None and value.visual.stream['network'] is not None)
    value.output.finish=True
    value.pump(lambda:len(value.reset_calls)>count)
    value.speaker.pool.submit(lambda:None).result(timeout=2)
    assert value.speaker.health()['self_match_probe']['phase']=='CANCELLED'
