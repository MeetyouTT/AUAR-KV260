"""Independent candidate entry black boxes, with exact public original FSMs."""
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import threading
from types import SimpleNamespace
from unittest.mock import patch

import pytest

HERE=Path(__file__).resolve().parent
LIVE=HERE.parents[1]
CANDIDATE=HERE.parent/'candidate_runtime'
RUNTIME=LIVE/'start_sync_fix/candidate_runtime'
sys.path.insert(0,str(HERE));sys.path.insert(0,str(RUNTIME))
LOADED_SHA={}
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);mod=importlib.util.module_from_spec(spec)
    raw=path.read_bytes();LOADED_SHA[str(path)]=hashlib.sha256(raw).hexdigest()
    sys.modules[name]=mod;exec(compile(raw,str(path),'exec'),mod.__dict__);return mod
voice=load('split_original_voice_fixture',HERE/'test_original_voice_contract.py')
load('common.binding_intent',CANDIDATE/'common/binding_intent.py')
load('board.runtime.audio.board_asr',LIVE/'lifecycle_review/no_speech_fix/candidate/board/runtime/audio/board_asr.py')
jobs_module=load('board.runtime.audio.board_dialogue_jobs',CANDIDATE/'board/runtime/audio/board_dialogue_jobs.py')
business_module=load('board.runtime.board_business',CANDIDATE/'board/runtime/board_business.py')
from board.runtime.board_dialogue import DIALOGUE_ROUTE
from tests.framework.test_simple_enrollment import snapshot

class Sequence:
    def __init__(self):self.store=SimpleNamespace(check_turn_current=lambda *a,**kw:None);self.replies=[]
    def prepare_local_sequence(self,text,producer,reply_sink,**kwargs):
        def emit(reply,**options):self.replies.append(reply.text)
        return producer(emit)

class Readback:
    def __init__(self):self.calls=0
    def read(self,*args):self.calls+=1;return None

class Business:
    config={'enabled':True}
    def __init__(self,clock):
        self.fixture=voice.Fixture();self.fixture.clock=clock;self.fixture.device.clock=clock
        self.device=self.fixture.device;self.turns=[];self.routes=0;self.resets=0
        self.hub=SimpleNamespace(speaker=self.device)
    def public(self):
        actor=('synthetic-boot','synthetic-session');row=self.device.sessions.get(actor)
        if row and self.device.clock()>=row['until']:self.device.sessions.pop(actor)
        return dict(active=bool(self.device.sessions),ready=True,speaker_calibrated=False,automatic_profile_access=False)
    def turn(self,meta,text,pcm,**kwargs):
        if not kwargs['is_current']() or kwargs['cancel_event'].is_set():raise InterruptedError('synthetic original owner cancelled')
        self.turns.append(text)
        with patch.dict(sys.modules,{'webrtcvad':SimpleNamespace(Vad=voice.VAD)}):return self.device.turn(meta,text,pcm)
    def route(self,meta,text,pcm,**kwargs):
        self.routes+=1
        return dict(version=1,context=dict(meta),analysis_mode='TRACKER',binding_request=None,
            decision=dict(route='ordinary',reply=None,attempt_id=None,board_text=None,reason='SYNTHETIC_ORDINARY',
                skip_legacy_device_command=False,unified_saved=False,personal_memory_allowed=False))
    def reset(self):self.resets+=1;self.device.sessions.clear()

class Fixture:
    def __init__(self):
        self.clock=voice.Clock();self.view=snapshot();self.view['board_boot_id']='synthetic-boot'
        self.commands=[];self.source_reads=0;self.current_id=0;self.controller=Sequence();self.forbid_source=False
        self.business=Business(self.clock);self.readback=Readback()
        self.handler=business_module.LocalIdentityReplies('synthetic-boot',self.read,self.commands.append,
            clock=self.clock,now_ms=lambda:round(self.clock()*1000))
        self.handler.attach_speaker_business(self.business,self.readback)
    def read(self):
        self.source_reads+=1
        if self.forbid_source:raise AssertionError('Standalone voice queried face provider')
        return copy.deepcopy(self.view)
    def say(self,text,*,session='synthetic-session',current=True,controller=None,cancel_event=None):
        self.current_id+=1;self.view['observed_mono_ms']=round(self.clock()*1000)
        raw=voice.pcm(self.current_id);meta=voice.meta(self.current_id,raw);meta['session_id']=session
        job=SimpleNamespace(meta=meta,pcm=raw,capture_snapshot=None if self.forbid_source else copy.deepcopy(self.view),
            scope=dict(kind='conversation',id='a'*32),deadline=self.clock()+60,context_source_id=None)
        ctl=controller or self.controller
        return self.handler(text,job=job,controller=ctl,is_current=lambda:current,
            cancel_event=cancel_event or threading.Event(),reply_sink=lambda *args:None)
    def poll(self,count=200):
        for _ in range(count):self.clock.now+=.01;self.view['observed_mono_ms']=round(self.clock()*1000);self.handler.public()

@pytest.mark.parametrize('phrase',['登记声纹','帮我登记声纹'])
def test_bare_voice_arms_name_across_public_polling_without_face_or_unified(phrase):
    f=Fixture();f.forbid_source=True;f.say(phrase)
    assert not f.business.public()['active'] and f.handler.public()['entry_name_pending']
    f.poll();f.say('我叫合成声纹')
    assert f.business.device.sessions[('synthetic-boot','synthetic-session')]['name']=='合成声纹'
    assert f.business.device.sessions[('synthetic-boot','synthetic-session')]['vectors']==[]
    assert f.commands==[] and f.source_reads==0 and f.readback.calls==0 and f.business.routes==0

def test_named_voice_and_three_samples_save_without_face_or_automatic_link():
    f=Fixture();f.forbid_source=True;f.say('帮我登记声纹，我叫合成声纹')
    for phrase in ('合成样本一','合成样本二','合成样本三'):f.say(phrase)
    row=f.business.device.sessions[('synthetic-boot','synthetic-session')]
    assert row['stage']=='confirm' and len(row['vectors'])==3
    f.say('确认登记');assert f.business.fixture.store.enrolls==[]
    f.say('确认保存身份关联');assert f.business.fixture.store.enrolls==[]
    f.say('确认保存声纹')
    assert len(f.business.fixture.store.enrolls)==1
    assert f.commands==[] and f.business.routes==0 and f.source_reads==0 and f.readback.calls==0
    assert f.handler.public()['entry_mode'] is None

def test_bare_face_name_survives_polling_and_never_dispatches_voice():
    f=Fixture();f.say('登记人脸');f.poll();f.say('我叫合成人脸')
    assert f.handler.flow.stage=='authorize'
    assert f.business.turns==[] and f.business.routes==0 and f.business.fixture.store.enrolls==[]
    assert f.commands==[] and f.readback.calls==0

def test_named_face_is_only_original_face_flow():
    f=Fixture();f.say('帮我登记人脸，我叫合成人脸')
    assert f.handler.flow.stage=='authorize'
    assert f.business.turns==[] and f.business.routes==0 and f.commands==[] and f.readback.calls==0

def test_active_voice_face_entry_is_busy_without_consuming_pcm_or_cancelling():
    f=Fixture();f.forbid_source=True;f.say('登记声纹，我叫合成声纹');f.say('合成样本一')
    row=f.business.device.sessions[('synthetic-boot','synthetic-session')];before=copy.deepcopy(row);turns=len(f.business.turns)
    f.say('登记人脸，我叫合成人脸')
    assert row==before and len(f.business.turns)==turns and f.commands==[] and f.business.routes==0

def test_active_face_voice_entry_is_busy_without_cancelling_face():
    f=Fixture();f.say('登记人脸，我叫合成人脸');epoch=f.handler.flow.epoch;owner=copy.deepcopy(f.handler.flow.owner)
    f.say('登记声纹，我叫合成声纹')
    assert f.handler.flow.stage=='authorize' and f.handler.flow.epoch==epoch and f.handler.flow.owner==owner
    assert f.business.turns==[] and f.business.routes==0 and f.commands==[]

def test_unarmed_name_hint_does_not_start_any_enrollment():
    f=Fixture();result=f.say('我叫合成姓名')
    assert result is DIALOGUE_ROUTE and not f.handler.flow.public()['active'] and not f.business.public()['active']
    assert f.commands==[] and f.business.fixture.store.enrolls==[]

@pytest.mark.parametrize('ending',['cancel','reset','expire','other-session'])
def test_pending_voice_name_cannot_survive_cancel_reset_expiry_or_actor_change(ending):
    f=Fixture();f.say('登记声纹')
    if ending=='cancel':f.say('取消声纹登记')
    if ending=='reset':f.handler.reset()
    if ending=='expire':f.clock.now+=120.001
    result=f.say('我叫合成姓名',session='other-session' if ending=='other-session' else 'synthetic-session')
    assert result is DIALOGUE_ROUTE
    assert not f.handler.flow.public()['active'] and not f.business.public()['active'] and f.commands==[]

def test_completed_face_known_result_does_not_start_voice_or_unified():
    f=Fixture();f.view['modules']['identity']['state']='KNOWN'
    f.say('登记人脸，我叫合成人脸')
    assert not f.handler.flow.public()['active'] and f.handler.public()['entry_mode'] is None
    assert f.business.turns==[] and f.business.routes==0 and f.commands==[]

def test_cancelled_current_request_does_not_leave_pending_voice_entry():
    # A direct producer cancellation boundary is relevant because the original
    # controller has no check between successful begin_turn and producer().
    f=Fixture();f.forbid_source=True
    with pytest.raises(InterruptedError):f.say('登记声纹',current=False)
    assert not f.handler.public()['entry_name_pending']
    assert f.handler.public()['entry_mode'] is None

def test_cancel_during_exact_original_begin_turn_does_not_resurrect_name_authority():
    # Exact original controller plus RAM Store; cancellation occurs after its
    # pre-begin check but before producer executes. No device/model/DB opened.
    review=load('split_no_speech_ram_fixtures',LIVE/'lifecycle_review/no_speech_fix/test_no_speech_pipeline.py')
    # The helper imports old business/Jobs only for fixture declarations. Our
    # already-constructed candidate handler remains the object under test.
    f=Fixture();f.forbid_source=True;event=threading.Event();store=review.Store();models=review.Models()
    controller=review.BoardDialogueController(store,models,board_boot_id='synthetic-boot',system_prompt='synthetic local',clock=f.clock)
    original_begin=store.begin_turn
    def cancel_after_check(*args,**kwargs):
        receipt=original_begin(*args,**kwargs);f.handler.reset();event.set();return receipt
    store.begin_turn=cancel_after_check
    with pytest.raises(InterruptedError):f.say('登记声纹',controller=controller,cancel_event=event)
    assert not f.handler.public()['entry_name_pending']
    assert f.handler.public()['entry_mode'] is None
    assert f.business.device.sessions=={} and f.commands==[] and models.calls==[]

def test_real_original_guide_completion_then_first_voice_request_has_no_stale_mode_busy():
    review=load('split_no_speech_ram_fixtures_for_guide',LIVE/'lifecycle_review/no_speech_fix/test_no_speech_pipeline.py')
    f=Fixture();f.say('登记人脸，我叫合成人脸')
    assert f.handler.flow.stage=='authorize'
    camera=review.Camera(f.clock);camera.view['board_boot_id']='synthetic-boot'
    # Exercise the exact original FSM and guide outside LIR.producer.finally,
    # matching completion/reset that occurs after the entry turn has retired.
    f.handler.flow.snapshot=camera.read;f.handler.flow.command=camera.command
    with patch('board.identity.voice_enrollment.time.sleep',camera.sleep):
        assert f.handler.flow.handle('确认登记',camera.read())['code']=='sample_auto'
        results=[];f.handler.flow.guide(lambda value,final:results.append((value['code'],final)))
    assert results==[('registered',True)] and f.handler.flow.stage=='idle'
    assert [c['action'] for c in camera.commands]==['identity_sample_start','identity_enroll']
    f.forbid_source=True;f.say('登记声纹，我叫合成声纹')
    assert f.business.device.sessions[('synthetic-boot','synthetic-session')]['stage']=='samples'
    assert f.handler.public()['entry_mode']=='voice'

def test_original_voice_save_then_first_face_request_has_no_stale_mode_busy():
    f=Fixture();f.forbid_source=True;f.say('登记声纹，我叫合成声纹')
    for phrase in ('合成样本一','合成样本二','合成样本三'):f.say(phrase)
    # Exact original save is completed without another LIR.producer.finally.
    index=f.current_id+1;raw=voice.pcm(index);owner=voice.meta(index,raw)
    assert '已保存' in f.business.device.turn(owner,'确认保存声纹',raw)
    assert f.business.device.sessions=={} and len(f.business.fixture.store.enrolls)==1
    f.current_id=index;f.forbid_source=False;turns=len(f.business.turns)
    f.say('登记人脸，我叫合成人脸')
    assert f.handler.flow.stage=='authorize' and f.handler.public()['entry_mode']=='face'
    assert len(f.business.turns)==turns and f.business.routes==0

def test_record_exact_loaded_candidate_source_hashes():
    (HERE/'BLACKBOX_LOADED_SOURCES.json').write_text(json.dumps(LOADED_SHA,indent=2)+'\n',encoding='utf-8')

@pytest.mark.parametrize('phrase',['登记人脸','帮我登记人脸，我叫合成人脸','登记声纹','帮我登记声纹，我叫合成声纹'])
def test_actual_jobs_assembly_dispatches_both_explicit_standalone_entries(phrase):
    f=Fixture();calls=[]
    class Handler:
        def public(self):return {'active':False}
        def __call__(self,text,**kwargs):calls.append(text);return 'synthetic-local-plan'
    handler=Handler();ctl=SimpleNamespace(board_boot_id='synthetic-boot',asr=SimpleNamespace(),command_handler=None)
    jobs=jobs_module.BoardDialogueJobs(ctl,dict(enabled=True,host='127.0.0.1',port=8797,timeout_ms=30000),'synthetic-boot',
        scope_provider=lambda _:dict(kind='conversation',id='a'*32),clock=f.clock,start_worker=False,
        special_handlers=dict(identity_enrollment=handler,speaker_identity=handler))
    raw=voice.pcm(99);clip=SimpleNamespace(capture_id='synthetic-assembly',audio=SimpleNamespace(sample_count=len(raw)//2),pcm=raw)
    jobs.submit(clip);job=jobs.waiting
    assert jobs._route(job,phrase)==('synthetic-local-plan',None)
    assert calls==[phrase]

@pytest.mark.parametrize('phrase',['不要登记人脸','如果我要登记人脸，我叫合成','“登记人脸，我叫合成”',
    '不要登记声纹','如果我要登记声纹，我叫合成','“登记声纹，我叫合成”'])
def test_negative_hypothetical_and_quoted_phrases_do_not_arm_standalone_entry(phrase):
    from common.binding_intent import binding_intent
    assert binding_intent(phrase)['kind'] not in ('face_only','voice_only')

def test_old_joint_explicit_phrase_keeps_original_joint_kind():
    from common.binding_intent import binding_intent
    assert binding_intent('记住我，我叫合成姓名')['kind']=='remember_self'

def test_jobs_entire_ast_is_original_after_reverting_only_two_kind_set_additions():
    tree=ast.parse((CANDIDATE/'board/runtime/audio/board_dialogue_jobs.py').read_text(encoding='utf-8'))
    old=ast.parse((LIVE/'lifecycle_review/no_speech_fix/candidate/board/runtime/audio/board_dialogue_jobs.py').read_text(encoding='utf-8'))
    edits=0
    for node in ast.walk(tree):
        if isinstance(node,ast.Tuple) and any(isinstance(x,ast.Constant) and x.value=='face_only' for x in node.elts):
            node.elts=[x for x in node.elts if not (isinstance(x,ast.Constant) and x.value in ('face_only','voice_only'))];edits+=1
    assert edits==2 and ast.dump(tree,include_attributes=False)==ast.dump(old,include_attributes=False)
