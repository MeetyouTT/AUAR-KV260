"""RAM-only ASR→Jobs→FSM→cue/receipt→rearm tests, against either exact source set."""
import ast
import copy
import hashlib
import importlib.util
import os
from pathlib import Path
import struct
import sys
import threading
from types import SimpleNamespace
from unittest.mock import patch

import pytest

HERE=Path(__file__).resolve().parent
RUNTIME=HERE.parents[1]/'start_sync_fix/candidate_runtime'
MODE=os.environ.get('AURA_NO_SPEECH_REVIEW_MODE','candidate')
assert MODE in ('baseline','candidate')
sys.path.insert(0,str(RUNTIME))
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    sys.modules[name]=module;spec.loader.exec_module(module);return module
asr_module=load('board.runtime.audio.board_asr',HERE/MODE/'board/runtime/audio/board_asr.py')
jobs_module=load('board.runtime.audio.board_dialogue_jobs',HERE/MODE/'board/runtime/audio/board_dialogue_jobs.py')
recording_module=load('tools.board_recording',HERE.parent/'current_public/tools/board_recording.py')
from board.runtime.board_business import LocalIdentityReplies
from board.runtime.board_dialogue import BoardDialogueController
from board.runtime.audio.board_dialogue_jobs import BoardDialogueJobs
from common.model_inference_wire import Owner,audio_payload,make_response
from common.voice_channel import ChannelState
from tools.voice_first_recording import VoiceFirstRecordingController
from tests.framework.test_simple_enrollment import snapshot

class Clock:
    def __init__(self):self.now=1.
    def __call__(self):return self.now

class Samples:
    def astype(self,dtype):return self
    def __truediv__(self,divisor):return self

class NP:
    float32='synthetic-float32'
    def frombuffer(self,pcm,dtype):assert isinstance(pcm,bytes) and dtype=='<i2';return Samples()

class Recognizer:
    def __init__(self):self.text='';self.decodes=0;self.hook=None
    def create_stream(self):return SimpleNamespace(result=SimpleNamespace(text=self.text),accept_waveform=lambda *args:None)
    def decode_stream(self,stream):
        self.decodes+=1
        if self.hook:self.hook()

class ASR:
    def __init__(self,clock):
        self.real=object.__new__(asr_module.BoardParaformer)
        self.real.np=NP();self.real.clock=clock;self.real._lock=threading.Lock();self.real._recognizer=Recognizer()
        self.text='';self.direct=False;self.failure=None;self.hook=None;self.calls=0
        self.model_sha256='a'*64
    def transcribe(self,pcm,**kwargs):
        self.calls+=1
        if self.hook:self.hook()
        if self.failure:raise self.failure
        if self.direct:return self.text
        self.real._recognizer.text=self.text
        return self.real.transcribe(pcm,**kwargs)

class Store:
    def __init__(self):self.rows={};self.events=[];self.acks=[]
    def preempt_compaction(self):self.events.append('preempt')
    def begin_turn(self,scope,turn_id,text,*,generation,metadata):
        assert scope['kind']=='conversation'
        self.rows[turn_id]=dict(generation=generation,status='pending',user=text)
        self.events.append('begin');return dict(user_event_id='synthetic-user-'+turn_id)
    def check_turn_current(self,turn_id,*,generation):
        row=self.rows[turn_id]
        assert row['generation']==generation and row['status'] in ('pending','generated')
    def generated(self,turn_id,text,*,generation,**kwargs):
        self.check_turn_current(turn_id,generation=generation);self.rows[turn_id].update(status='generated',assistant=text)
        self.events.append('generated')
    def bind_audio_receipt(self,turn_id,**receipt):self.rows[turn_id]['receipt']=receipt;self.events.append('bound')
    def ack_played(self,turn_id,**receipt):
        assert receipt['complete'] is True
        assert {k:v for k,v in receipt.items() if k!='complete'}==self.rows[turn_id]['receipt']
        self.rows[turn_id]['status']='played';self.acks.append(turn_id);return {'status':'played'}
    def interrupt(self,turn_id,*,generation,reason):
        assert self.rows[turn_id]['generation']==generation
        self.rows[turn_id]['status']='interrupted';self.events.append('interrupt')

class Models:
    def __init__(self):self.calls=[];self.cancelled=[]
    def request(self,kind,payload,**kwargs):
        self.calls.append(kind)
        assert kind=='tts','No blank or identity turn may call LLM'
        return make_response(Owner.from_dict(payload),result=dict(audio=audio_payload(b'\1\0'*160,24000)))
    def cancel(self,owner):self.cancelled.append(owner)

class Camera:
    def __init__(self,clock):self.clock=clock;self.view=snapshot();self.commands=[];self.pending=None;self.collect_published=False
    def read(self):return copy.deepcopy(self.view)
    def sleep(self,duration):
        self.clock.now+=duration;self.view['observed_mono_ms']=round(self.clock()*1000);self.view['sequence']+=1
        if self.pending:
            sample=self.view['modules']['identity']['enrollment_sampling']
            if not self.collect_published:
                sample.update(session_id='synthetic-owned-sample',stage='collect',bound_target=copy.deepcopy(self.pending['params']['target']))
                self.view['capabilities'].update(identity_sample_start=False,identity_sample_cancel=True)
                self.collect_published=True
            else:
                sample.update(stage='ready',counts={'collect':10,'validate':5},total=15)
                self.view['capabilities']['identity_enroll']=True
    def command(self,command):
        self.commands.append(copy.deepcopy(command));action=command['action']
        if action=='identity_sample_start':self.pending=copy.deepcopy(command)
        elif action=='identity_enroll':
            assert command['params']['sampling_session_id']=='synthetic-owned-sample'
            assert command['params']['confirmed'] is True
            self.view['modules']['identity'].update(state='KNOWN',db_version=1,last_operation=dict(command_id=command['command_id'],
                action=action,state='COMMITTED',db_version=1,detail='synthetic saved'))
        elif action=='identity_sample_cancel':
            assert command['params']['session_id']=='synthetic-owned-sample'
        else:raise AssertionError('Unexpected camera command')
        fields=('protocol_version','board_boot_id','service_epoch','command_id','ui_epoch','ui_generation')
        return dict({k:command[k] for k in fields},accepted=True,detail='synthetic ack')

class Business:
    config={'enabled':False}
    def __init__(self):self.resets=0;self.turns=0;self.collected=0
    def public(self):return {'active':bool(self.collected)}
    def reset(self):self.resets+=1;self.collected=0
    def turn(self,*args,**kwargs):self.turns+=1;return None

class Handler(LocalIdentityReplies):
    def __init__(self,*a,**kw):super().__init__(*a,**kw);self.invocations=0
    def __call__(self,*a,**kw):self.invocations+=1;return super().__call__(*a,**kw)

class Player:
    def __init__(self):self.last_error='';self.cancelled=0;self.state=None;self.completion=None;self.events=[]
    def public(self):return dict(phase='IDLE',playing=False,paused=False,pending_job=None,audio_output_state='IDLE_READY')
    def cancel(self):self.cancelled+=1;self.completion=None
    def channel_event(self,event,pcm,owner,*args):
        if event['kind']=='start':self.state=ChannelState(owner)
        self.state.accept(event,pcm);self.events.append(event['kind'])
    def channel_complete(self,owner,result):
        assert self.state.ended and self.state.owner==owner
        assert result['sample_count']==self.state.samples and result['pcm_sha256']==self.state.digest.hexdigest()
        self.completion=(dict(owner),copy.deepcopy(result))
    def take_completion(self):value,self.completion=self.completion,None;return value
    def tick(self):return None

class Capture:
    counter=0
    def __init__(self,*a,**kw):self.state='IDLE'
    def start(self):Capture.counter+=1;self.state='RECORDING';return 'synthetic-clip-'+str(Capture.counter)
    def snapshot(self):return dict(state=self.state,speech_active=False)
    def cancel(self):self.state='IDLE'
    def close(self):self.state='CLOSED'

class Harness:
    def __init__(self):
        self.clock=Clock();self.camera=Camera(self.clock);self.asr=ASR(self.clock);self.store=Store();self.models=Models()
        self.controller=BoardDialogueController(self.store,self.models,board_boot_id='boot',system_prompt='synthetic current local control',asr=self.asr,clock=self.clock)
        self.handler=Handler('boot',self.camera.read,self.camera.command,clock=self.clock,now_ms=lambda:round(self.clock()*1000))
        self.business=Business();self.handler.business=self.business
        self.jobs=BoardDialogueJobs(self.controller,dict(enabled=True,host='127.0.0.1',port=8797,timeout_ms=30000),'boot',
            scope_provider=lambda _:dict(kind='conversation',id='a'*32),special_handlers={'identity_enrollment':self.handler},
            clock=self.clock,start_worker=False)
        self.jobs.identity_snapshot=self.camera.read;self.jobs.feedback_assets={'synthetic':True}
        self.player=Player()
        self.recording=VoiceFirstRecordingController(self.player,capture_factory=Capture,auto_capture_factory=Capture,
            transcriber=self.jobs,boot_id='boot',attention_provider=lambda:None,barge_capture_factory=lambda:None,
            clock=self.clock,barge_enabled=False,wake_word_required=False,visual_social=False)
        r=self.recording;r.monitor_enabled=r.monitor_owned=r.monitor_entered=r.auto_enabled=True
        r.monitor_key=('audio','boot','synthetic-session')
    def turn(self,text,*,direct=False,failure=None):
        self.asr.text=text;self.asr.direct=direct;self.asr.failure=failure
        r=self.recording
        self.camera.view['observed_mono_ms']=round(self.clock()*1000)
        with patch('board.interaction.ui_contract.millis',return_value=round(self.clock()*1000)):
            cid=r._listen();r._speech_started()
        r.capture.state='IDLE';r.recording_state='READY'
        pcm=struct.pack('<h',1000)*3200
        r.utterance=SimpleNamespace(capture_id=cid,audio=SimpleNamespace(sample_count=3200),pcm=pcm)
        r._queue_transcription()
        with patch('board.identity.voice_enrollment.time.sleep',self.camera.sleep):assert self.jobs.run_next()
        # Drive exact original recording receipt and half-duplex paths. The
        # player validates the real channel; it never opens an audio device.
        for _ in range(20):
            recording_module.RecordingController.tick(r)
            self.jobs.drain_actions()
            if not self.jobs.progress:break
        return r.transcription['state']
    def rearm(self):
        self.clock.now+=.6;self.camera.view['observed_mono_ms']=round(self.clock()*1000)
        with patch('board.interaction.ui_contract.millis',return_value=round(self.clock()*1000)):
            self.recording._auto_tick();self.recording._monitor_tick()
    def begin(self):
        assert self.turn('帮我登记身份，我叫小林')=='ANSWERED'
        assert self.handler.flow.stage=='authorize'
        assert self.camera.commands==[] and self.models.calls and set(self.models.calls)=={'tts'}
        self.rearm()
        assert self.recording.capture.state=='RECORDING' and self.handler.flow.stage=='authorize'
        return (self.handler.flow.epoch,copy.deepcopy(self.handler.flow.owner),self.handler.flow.until,
                self.handler.flow.name,self.recording.monitor_key,self.jobs.session_id)

@pytest.mark.parametrize('raw,direct',[('',False),('   ',False),('',True),(' \u3000 ',True)])
def test_prepare_blank_relisten_independent_confirmation_completes_original_face_flow(raw,direct):
    f=Harness();epoch,owner,until,name,key,session=f.begin()
    before=(len(f.store.rows),len(f.store.acks),len(f.models.calls),len(f.camera.commands),f.handler.invocations,f.business.turns)
    f.turn(raw,direct=direct)
    assert f.recording.wake_rearm,'No speech must use original benign rearm path'
    assert f.jobs.latency_metrics['entry_rejected'] is True
    f.rearm()
    assert (f.handler.flow.epoch,f.handler.flow.owner,f.handler.flow.until,f.handler.flow.name,
            f.recording.monitor_key,f.jobs.session_id)==(epoch,owner,until,name,key,session)
    assert before==(len(f.store.rows),len(f.store.acks),len(f.models.calls),len(f.camera.commands),f.handler.invocations,f.business.turns)
    assert f.handler.flow.stage=='authorize' and f.business.resets==0
    assert f.turn('确认登记')=='ANSWERED'
    assert [c['action'] for c in f.camera.commands]==['identity_sample_start','identity_enroll']
    assert f.handler.flow.stage=='idle' and f.camera.view['modules']['identity']['db_version']==1
    assert len(f.store.rows)==2 and len(f.store.acks)==2 and set(f.models.calls)=={'tts'}

def test_repeated_empty_results_do_not_extend_consent_or_consume_voice_samples():
    f=Harness();state=f.begin();f.business.collected=2
    before=(f.handler.invocations,f.business.turns,len(f.store.rows),len(f.models.calls))
    for raw in ('','  ','\u3000'):
        f.turn(raw);f.rearm()
        assert f.handler.flow.stage=='authorize' and f.business.collected==2 and f.business.resets==0
        assert (f.handler.flow.epoch,f.handler.flow.owner,f.handler.flow.until,f.handler.flow.name,
            f.recording.monitor_key,f.jobs.session_id)==state
    assert before==(f.handler.invocations,f.business.turns,len(f.store.rows),len(f.models.calls))
    assert f.camera.commands==[]

@pytest.mark.parametrize('failure',[ValueError('synthetic malformed ASR'),OSError('synthetic IO'),TimeoutError('synthetic deadline'),RuntimeError('synthetic unavailable')])
def test_real_failures_keep_original_error_and_clear_pending_authorize(failure):
    f=Harness();f.begin();f.turn(None,failure=failure)
    assert f.recording.transcription['state']=='ERROR' and f.handler.flow.stage=='idle'
    assert f.business.resets>=1 and f.camera.commands==[]

@pytest.mark.parametrize('raw',[None,False,123,b'', 'a'*4097,'\0','hello\0','\n','\t',' \r\n\u3000'])
def test_invalid_nonempty_protocol_output_is_not_treated_as_no_speech(raw):
    f=Harness();f.begin();f.turn(raw,direct=True)
    assert f.recording.transcription['state']=='ERROR' and f.handler.flow.stage=='idle'
    assert not f.recording.wake_rearm and f.camera.commands==[]

def test_original_explicit_pause_still_cancels_authorize():
    f=Harness();f.begin();f.recording.handsfree_toggle()
    assert not f.recording.monitor_enabled and f.handler.flow.stage=='idle' and f.business.resets==1
    assert f.camera.commands==[]

def test_original_explicit_cancel_still_cancels_authorize():
    f=Harness();f.begin();f.recording.cancel()
    assert f.handler.flow.stage=='idle' and not f.recording.monitor_owned and f.business.resets==1
    assert f.camera.commands==[]

def test_changed_target_after_benign_blank_is_still_rejected():
    f=Harness();f.begin();f.turn('');f.rearm()
    f.camera.view['modules']['target']['selected']['track_generation']+=1
    assert f.turn('确认登记')=='ANSWERED'
    assert f.handler.flow.stage=='idle' and f.camera.commands==[]

def test_original_authorize_expiry_is_not_extended_by_empty_result():
    f=Harness();original=f.begin();f.turn('');f.rearm()
    assert f.handler.flow.until==original[2]
    f.clock.now=original[2]+.001;f.camera.view['observed_mono_ms']=round(f.clock()*1000)
    assert f.handler.flow.handle('确认登记',f.camera.read())['code']=='expired'
    assert f.handler.flow.stage=='idle' and f.camera.commands==[]

def test_missing_new_capture_proof_is_still_rejected_after_no_speech():
    f=Harness();f.begin();f.turn('');f.rearm()
    assert f.handler.flow.handle('确认登记',None)['code']=='changed'
    assert f.handler.flow.stage=='idle' and f.camera.commands==[]

def test_no_speech_type_cannot_hide_expired_request_deadline():
    f=Harness();f.begin()
    error_type=getattr(asr_module,'BoardNoSpeech',ValueError)
    def late():f.clock.now+=31
    f.asr.hook=late
    f.turn('',failure=error_type('synthetic no speech'))
    assert f.recording.transcription['state']=='ERROR' and f.handler.flow.stage=='idle'
    expected='TimeoutError' if MODE=='candidate' else 'ValueError'
    assert f.jobs.latency_metrics['error_class']==expected and not f.recording.wake_rearm

def test_no_speech_type_cannot_rearm_explicitly_cancelled_capture():
    f=Harness();f.begin()
    error_type=getattr(asr_module,'BoardNoSpeech',ValueError)
    f.asr.hook=f.recording.cancel
    f.turn('',failure=error_type('synthetic no speech'))
    assert f.handler.flow.stage=='idle' and not f.recording.monitor_enabled
    assert not f.recording.wake_rearm and f.jobs.progress==__import__('collections').deque()

@pytest.mark.parametrize('raw',['','   ',None])
def test_actual_paraformer_empty_results_release_lock_and_are_typed_only_when_candidate(raw):
    clock=Clock();asr=ASR(clock);asr.text=raw
    with pytest.raises(ValueError) as captured:asr.transcribe(b'\1\0'*3200,sample_rate=16000,deadline=20,cancelled=lambda:False)
    if MODE=='candidate':assert type(captured.value) is asr_module.BoardNoSpeech
    else:assert type(captured.value) is ValueError
    assert not asr.real._lock.locked() and asr.real._recognizer.decodes==1

def test_actual_paraformer_normal_text_and_original_waveform_parameters_unchanged():
    clock=Clock();asr=ASR(clock);asr.text='  确认登记  '
    assert asr.transcribe(b'\1\0'*3200,sample_rate=16000,deadline=20,cancelled=lambda:False)=='确认登记'
    assert not asr.real._lock.locked() and asr.real._recognizer.decodes==1

def test_only_three_jobs_methods_or_imports_and_one_asr_method_class_change():
    def functions(path):
        tree=ast.parse(path.read_text(encoding='utf-8'));out={}
        for cls in tree.body:
            if isinstance(cls,ast.ClassDef):
                for node in cls.body:
                    if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):out[(cls.name,node.name)]=ast.dump(node,include_attributes=False)
        return out
    old=functions(HERE/'baseline/board/runtime/audio/board_dialogue_jobs.py');new=functions(HERE/'candidate/board/runtime/audio/board_dialogue_jobs.py')
    assert {k for k in old if old[k]!=new[k]}=={('BoardDialogueJobs','_admit_text'),('BoardDialogueJobs','_execute')}
    old=functions(HERE/'baseline/board/runtime/audio/board_asr.py');new=functions(HERE/'candidate/board/runtime/audio/board_asr.py')
    assert {k for k in old if old[k]!=new[k]}=={('BoardParaformer','transcribe')}
