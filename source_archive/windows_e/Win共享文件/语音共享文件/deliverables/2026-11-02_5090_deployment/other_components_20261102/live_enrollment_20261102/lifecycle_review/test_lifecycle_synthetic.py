"""Exact pinned methods with RAM-only fakes. No sockets, stores, audio or models."""
import ast
import copy
import importlib.util
import json
from pathlib import Path
import struct
import sys
import threading
from types import SimpleNamespace
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
RUNTIME=HERE.parent/'start_sync_fix/candidate_runtime'
sys.path.insert(0,str(RUNTIME))
spec=importlib.util.spec_from_file_location('tools.board_recording',HERE/'current_public/tools/board_recording.py')
actual_recording=importlib.util.module_from_spec(spec)
sys.modules['tools.board_recording']=actual_recording
spec.loader.exec_module(actual_recording)
from board.runtime.board_business import LocalIdentityReplies
from board.runtime.board_dialogue import DIALOGUE_ROUTE
from board.runtime.audio.board_dialogue_jobs import BoardDialogueJobs
from tools.voice_first_recording import VoiceFirstRecordingController
from tests.framework.test_simple_enrollment import snapshot

# Only the original cancel method is needed; do not import the store-bearing
# speaker runtime or manufacture replacements for its missing dependencies.
tree=ast.parse((RUNTIME/'board/runtime/board_speaker_business.py').read_text(encoding='utf-8'))
cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='LocalFaceExchange')
method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='cancel')
namespace={}
exec(compile(ast.Module(body=[method],type_ignores=[]),'pinned_LocalFaceExchange.cancel','exec'),namespace)
LocalFaceExchange=type('PinnedLocalFaceExchangeCancel',(),{'cancel':namespace['cancel']})

class Clock:
    now=1.
    def __call__(self):return self.now

class Player:
    def __init__(self):self.last_error='';self.cancel_calls=0
    def public(self):return dict(phase='IDLE',playing=False,paused=False,pending_job=None,audio_output_state='IDLE_READY')
    def cancel(self,*args,**kwargs):self.cancel_calls+=1

class Capture:
    counter=0
    def __init__(self,*args,**kwargs):self.state='IDLE';self.speech_active=False;self.cancelled=0
    def start(self):
        Capture.counter+=1;self.state='RECORDING';return 'synthetic-clip-'+str(Capture.counter)
    def snapshot(self):return dict(state=self.state,speech_active=self.speech_active)
    def cancel(self):self.cancelled+=1;self.state='IDLE'
    def close(self):self.state='CLOSED'

class Business:
    config={'enabled':False}
    def __init__(self):self.resets=0
    def reset(self):self.resets+=1
    def public(self):return {'active':False}
    def turn(self,*args,**kwargs):return None

class SequenceController:
    def __init__(self):self.store=SimpleNamespace();self.emits=[]
    def prepare_local_sequence(self,text,producer,reply_sink,**kwargs):
        def emit(reply,**options):self.emits.append((reply,options))
        return producer(emit)

def setup():
    clock=Clock();view=snapshot();commands=[]
    handler=LocalIdentityReplies('boot',lambda:copy.deepcopy(view),commands.append,
        clock=clock,now_ms=lambda:round(clock()*1000))
    business=Business();handler.business=business
    ctl=SimpleNamespace(board_boot_id='boot',asr=SimpleNamespace(),store=SimpleNamespace(),
        command_handler=None,context_builder=None)
    jobs=BoardDialogueJobs(ctl,dict(enabled=True,host='127.0.0.1',port=8797,timeout_ms=30000),'boot',
        scope_provider=lambda _:dict(kind='conversation',id='a'*32),
        special_handlers={'identity_enrollment':handler},clock=clock,start_worker=False)
    jobs.identity_snapshot=lambda:copy.deepcopy(view)
    player=Player()
    rec=VoiceFirstRecordingController(player,capture_factory=Capture,auto_capture_factory=Capture,
        transcriber=jobs,boot_id='boot',attention_provider=lambda:None,barge_capture_factory=lambda:None,
        clock=clock,barge_enabled=False,wake_word_required=False,visual_social=False)
    rec.monitor_enabled=True;rec.monitor_owned=True;rec.monitor_entered=True
    rec.monitor_key=('audio','boot','synthetic-session');rec.auto_enabled=True
    return clock,view,commands,handler,business,jobs,player,rec

def prepare(handler,view):
    value=handler.flow.handle('帮我登记身份，我叫小林',copy.deepcopy(view))
    assert value['code']=='prepare_name'
    assert handler.flow.public()=={'stage':'authorize','active':True}
    return handler.flow.epoch

def test_original_committed_ack_rearms_without_resetting_authorize():
    clock,view,commands,h,b,jobs,p,r=setup();epoch=prepare(h,view)
    jobs.last_ack={'request_id':'synthetic-reply','committed':True}
    r.transcription.update(state='ANSWERED',request_id='synthetic-reply')
    r.rearm_at=.5;r.ack_deadline=8.
    with patch('board.interaction.ui_contract.millis',return_value=1000):r._auto_tick()
    assert r.auto_state=='LISTENING' and r.capture.state=='RECORDING'
    assert h.flow.stage=='authorize' and h.flow.epoch==epoch and b.resets==0 and commands==[]
    assert jobs.capture_owners[r.listen_id]==view

def test_vad_overwrites_initial_no_face_snapshot_at_actual_speech_start():
    clock,view,commands,h,b,jobs,p,r=setup()
    view['modules']['vision']['people_count']=0
    view['modules']['target'].update(selected=None,tracks=[],state='NONE')
    with patch('board.interaction.ui_contract.millis',return_value=1000):cid=r._listen()
    assert jobs.capture_owners[cid]['modules']['target']['selected'] is None
    fresh=snapshot();fresh['sequence']=2;view.clear();view.update(fresh)
    with patch('board.interaction.ui_contract.millis',return_value=1000):r._speech_started()
    assert jobs.capture_owners[cid]==fresh
    assert r.speech_proof==(cid,r.monitor_key)
    assert r.monitor_stats['speech_starts']==1

def test_invalid_vad_source_does_not_reuse_initial_owner():
    clock,view,commands,h,b,jobs,p,r=setup()
    with patch('board.interaction.ui_contract.millis',return_value=1000):cid=r._listen()
    assert jobs.capture_owners[cid] is not None
    view['board_boot_id']='wrong-boot'
    with patch('board.interaction.ui_contract.millis',return_value=1000):r._speech_started()
    assert jobs.capture_owners[cid] is None

def test_submit_keeps_latest_vad_owner_across_generation_invalidation():
    clock,view,commands,h,b,jobs,p,r=setup()
    with patch('board.interaction.ui_contract.millis',return_value=1000):cid=r._listen()
    view['sequence']=2;view['modules']['target']['selected']['track_generation']=2
    with patch('board.interaction.ui_contract.millis',return_value=1000):r._speech_started()
    expected=copy.deepcopy(jobs.capture_owners[cid])
    pcm=struct.pack('<h',1000)*3200
    clip=SimpleNamespace(capture_id=cid,audio=SimpleNamespace(sample_count=3200),pcm=pcm)
    jobs.submit(clip)
    assert jobs.waiting.capture_snapshot==expected
    jobs.capture_owners[cid]['sequence']=999
    assert jobs.waiting.capture_snapshot==expected

def test_original_auto_fail_clears_cross_turn_authorize_without_sample_command():
    clock,view,commands,h,b,jobs,p,r=setup();epoch=prepare(h,view)
    r._auto_fail('synthetic-asr-failure')
    assert h.flow.public()=={'stage':'idle','active':False}
    assert h.flow.epoch!=epoch and b.resets==1 and p.cancel_calls==1
    assert commands==[]
    assert h.flow.handle('确认登记',copy.deepcopy(view)) is None

def test_post_error_bare_confirmation_returns_original_dialogue_route():
    clock,view,commands,h,b,jobs,p,r=setup();prepare(h,view)
    r._auto_fail('synthetic-asr-failure')
    ctl=SequenceController()
    job=SimpleNamespace(capture_snapshot=copy.deepcopy(view),meta=dict(request_id='synthetic-request',
        generation=2,session_id='synthetic-session'),pcm=b'\0\0'*3200,scope=dict(kind='conversation',id='a'*32),
        deadline=20.,context_source_id=None)
    result=h('确认登记',job=job,controller=ctl,is_current=lambda:True,
        cancel_event=threading.Event(),reply_sink=lambda *a:None)
    assert result is DIALOGUE_ROUTE and ctl.emits==[] and commands==[]

def test_blank_asr_is_generic_error_not_benign_entry_rejection():
    clock,view,commands,h,b,jobs,p,r=setup()
    for text in ('','   ',None):
        try:jobs._admit_text(SimpleNamespace(entry='visual',pcm=b'\0\0'*3200),text)
        except ValueError as exc:assert str(exc)=='No bounded board ASR text' and not getattr(exc,'entry_rejected',False)
        else:raise AssertionError('Blank ASR was accepted')

def test_original_generic_asr_error_to_service_error_clears_authorize():
    clock,view,commands,h,b,jobs,p,r=setup();prepare(h,view)
    r.transcription.update(state='TRANSCRIBING',request_id='synthetic-request',capture_id='synthetic-clip')
    jobs.progress.append(dict(error='ValueError',context=dict(request_id='synthetic-request',capture_id='synthetic-clip')))
    r._poll_transcription()
    assert r.transcription['state']=='ERROR' and h.flow.stage=='authorize'
    r._auto_tick()
    assert h.flow.stage=='idle' and r.auto_state=='ERROR'
    r._monitor_tick()
    assert r.monitor_state=='COOLDOWN' and r.monitor_reason=='SERVICE_ERROR'
    assert r.stop_reasons['SERVICE_ERROR']==1 and commands==[]

def test_benign_entry_rejection_rearms_without_reset():
    clock,view,commands,h,b,jobs,p,r=setup();epoch=prepare(h,view)
    r._entry_rejected()
    assert r.wake_rearm and h.flow.stage=='authorize' and h.flow.epoch==epoch and b.resets==0
    with patch('board.interaction.ui_contract.millis',return_value=1000):r._monitor_tick()
    assert not r.wake_rearm and r.capture.state=='RECORDING'
    assert h.flow.stage=='authorize' and b.resets==0

def test_silence_wait_before_30_seconds_does_not_reset():
    clock,view,commands,h,b,jobs,p,r=setup();epoch=prepare(h,view)
    r.capture=Capture();r.capture.state='RECORDING';r.listen_started=1.
    clock.now=29.;view['observed_mono_ms']=29000
    r._monitor_tick()
    assert h.flow.stage=='authorize' and h.flow.epoch==epoch and b.resets==0

def test_original_30_second_session_silence_closes_authorize():
    clock,view,commands,h,b,jobs,p,r=setup();prepare(h,view)
    r.capture=Capture();r.capture.state='RECORDING';r.listen_started=1.
    clock.now=31.;r._monitor_tick()
    assert r.monitor_reason=='CONVERSATION_SILENCE' and h.flow.stage=='idle' and b.resets==1
    assert commands==[]

def test_local_exchange_scope_close_does_not_reset_shared_flow():
    clock,view,commands,h,b,jobs,p,r=setup();epoch=prepare(h,view)
    exchange=object.__new__(LocalFaceExchange);exchange.closed=False;exchange.pcm=b'\0\0'
    exchange.cancel()
    assert exchange.closed and exchange.pcm is None
    assert h.flow.stage=='authorize' and h.flow.epoch==epoch and b.resets==0

def test_actual_missing_capture_owner_confirmation_rejects_and_clears_authorize():
    clock,view,commands,h,b,jobs,p,r=setup();prepare(h,view)
    result=h.flow.handle('确认登记',None)
    assert result['code']=='changed' and h.flow.stage=='idle' and commands==[]

def test_initial_owner_unavailable_even_fresh_current_rejects_start():
    clock,view,commands,h,b,jobs,p,r=setup()
    result=h.flow.handle('帮我登记身份，我叫小林',None)
    assert result['code']=='face_unavailable' and h.flow.stage=='idle' and commands==[]
