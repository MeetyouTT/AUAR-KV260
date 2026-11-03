"""Actual Jobs dispatch, original face/voice FSMs; synthetic RAM fixtures only."""
import copy
import importlib.util
from pathlib import Path
import sys
import threading
from types import SimpleNamespace

import pytest

HERE=Path(__file__).resolve().parent
RUNTIME=HERE/'candidate_runtime'
sys.path.insert(0,str(RUNTIME))
from common.binding_intent import binding_intent
from board.runtime.board_business import LocalIdentityReplies
from board.runtime.board_dialogue import DIALOGUE_ROUTE,StaleGeneration
from board.runtime.audio.board_dialogue_jobs import BoardDialogueJobs
from tests.framework.test_simple_enrollment import snapshot

old_path=list(sys.path)
spec=importlib.util.spec_from_file_location('split_original_voice_helpers',HERE/'independent_voice_review/test_original_voice_contract.py')
voice=importlib.util.module_from_spec(spec);spec.loader.exec_module(voice)
sys.path[:]=old_path

class Business:
    def __init__(self,clock):
        self.fixture=voice.Fixture();self.fixture.clock=clock;self.fixture.device.clock=clock
        self.calls=[];self.route_calls=0;self.resets=0;self.links=0;self.grants=0;self.forced_active=False
        self.config={'enabled':True}
    def public(self):
        return dict(active=bool(self.fixture.device.sessions) or self.forced_active,ready=True)
    def turn(self,meta,text,pcm,**kwargs):
        assert kwargs['is_current']() and not kwargs['cancel_event'].is_set()
        self.calls.append(text)
        return self.fixture.device.turn(meta,text,pcm)
    def route(self,*args,**kwargs):
        self.route_calls+=1
        raise AssertionError('Standalone entry must not reach unified router')
    def reset(self):
        self.resets+=1;self.fixture.device.sessions.clear()

class Controller:
    board_boot_id='boot';asr=None
    def __init__(self):
        self.store=SimpleNamespace(check_turn_current=lambda *a,**k:None)
        self.before_produce=None;self.generated=[]
    def prepare_local_sequence(self,text,producer,sink,**kwargs):
        if self.before_produce:self.before_produce()
        replies=[]
        def emit(reply,*,final_cue):replies.append((reply.text,final_cue))
        result=producer(emit)
        plan=SimpleNamespace(fallback=result is DIALOGUE_ROUTE,replies=replies)
        self.generated.append(plan);return plan

class Harness:
    def __init__(self,monkeypatch,*,known=False):
        self.clock=voice.Clock();self.view=snapshot();self.commands=[];self.pending=False;self.auto_ready=False
        if known:self.view['modules']['identity'].update(state='KNOWN',db_version=3,people=[{'person_id':'synthetic-person','display_name':'合成人脸'}])
        self.business=Business(self.clock);self.controller=Controller()
        monkeypatch.setitem(sys.modules,'webrtcvad',SimpleNamespace(Vad=voice.VAD))
        self.handler=LocalIdentityReplies('boot',self.read,self.command,clock=self.clock,
                                          now_ms=lambda:round(self.clock.now*1000))
        self.handler.business=self.business
        self.handler._visual=lambda job:pytest.fail('Standalone entry must not consult visual boundary provider')
        self.handler._gallery=lambda job:pytest.fail('Standalone entry must not consult face gallery')
        self.jobs=BoardDialogueJobs(self.controller,dict(enabled=True,host='192.168.50.1',port=8797,timeout_ms=120000),
            'boot',scope_provider=lambda meta:dict(kind='conversation',id='synthetic-conversation'),clock=self.clock,
            special_handlers={key:self.handler for key in ('identity_enrollment','identity_query','speaker_identity')},start_worker=False)
        self.counter=0;self.last_job=None
    def read(self):
        if self.pending:
            self.clock.now+=.001;self.view['sequence']+=1;self.view['observed_mono_ms']=round(self.clock.now*1000)
            self.view['modules']['identity']['enrollment_sampling'].update(session_id='synthetic-sampling',stage='collect',
                bound_target=copy.deepcopy(self.view['modules']['target']['selected']))
            self.pending=False
        elif self.auto_ready and self.view['modules']['identity']['enrollment_sampling']['stage']=='collect':
            self.view['modules']['identity']['enrollment_sampling'].update(stage='ready',counts={'collect':10,'validate':5},total=15)
            self.view['capabilities']['identity_enroll']=True
        return copy.deepcopy(self.view)
    def command(self,c):
        self.commands.append(copy.deepcopy(c))
        if c['action']=='identity_sample_start':self.pending=True
        elif c['action']=='identity_enroll':
            self.view['modules']['identity'].update(state='KNOWN',db_version=self.view['modules']['identity']['db_version']+1,
                last_operation=dict(command_id=c['command_id'],action=c['action'],state='COMMITTED',db_version=1,detail='synthetic'))
        elif c['action']=='identity_sample_cancel':
            self.view['modules']['identity']['enrollment_sampling'].update(stage='idle',session_id='')
        ack={k:c[k] for k in ('protocol_version','board_boot_id','service_epoch','command_id','ui_epoch','ui_generation')}
        return dict(ack,accepted=True,detail='synthetic')
    def say(self,text,*,seed=None,seconds=3):
        self.counter+=1;raw=voice.pcm(self.counter if seed is None else seed,seconds)
        clip=SimpleNamespace(capture_id='clip-'+str(self.counter),pcm=raw,audio=SimpleNamespace(sample_count=len(raw)//2))
        self.jobs.capture_owners={clip.capture_id:copy.deepcopy(self.view)}
        self.jobs.submit(clip);job=self.jobs.waiting;self.last_job=job
        plan,_=self.jobs._route(job,text,reply_sink=lambda *a:None)
        return plan
    def samples(self):
        for text in ('合成第一段测试语音','合成第二段测试语音','合成第三段测试语音'):self.say(text)

@pytest.mark.parametrize('text,kind',[
 ('登记人脸，我叫合成测试','face_only'),('帮我登记人脸，我叫合成测试','face_only'),
 ('请帮我登记人脸，我叫合成测试','face_only'),('登记人脸','face_only'),
 ('登记声纹，我叫合成测试','voice_only'),('请帮我登记声纹，我叫合成测试','voice_only'),
 ('帮我登记声纹','voice_only'),('记住我，我叫合成测试','remember_self')])
def test_full_sentence_intents(text,kind):assert binding_intent(text)['kind']==kind

@pytest.mark.parametrize('text',['不要登记人脸，我叫合成测试','如果登记人脸，我叫合成测试',
    '他说“登记人脸，我叫合成测试”','不要登记声纹，我叫合成测试','如果登记声纹，我叫合成测试',
    '他说登记声纹，我叫合成测试','关联我的人脸和声纹，我叫合成测试'])
def test_negative_quoted_hypothetical_and_new_joint_alias_do_not_arm_entry(text):
    assert binding_intent(text)['kind'] not in ('face_only','voice_only','remember_self')

def test_real_jobs_face_name_entry_never_touches_speaker_or_links(monkeypatch):
    h=Harness(monkeypatch);p=h.say('登记人脸，我叫合成测试')
    assert not p.fallback and h.handler.flow.stage=='authorize'
    assert h.business.calls==[] and h.business.route_calls==0 and h.commands==[]
    assert h.handler.public()['entry_mode']=='face'

def test_bare_face_and_name_followup_are_original_face_fsm(monkeypatch):
    h=Harness(monkeypatch);h.say('登记人脸')
    assert h.handler.flow.stage=='name'
    for _ in range(20):assert h.handler.public()['entry_mode']=='face'
    h.say('我叫合成测试');assert h.handler.flow.stage=='authorize'
    assert h.business.calls==[] and h.commands==[]

def test_voice_without_any_visual_three_distinct_samples_and_original_final_confirm(monkeypatch):
    h=Harness(monkeypatch,known=True);p=h.say('登记声纹，我叫合成测试')
    assert not p.fallback and h.business.fixture.encoder.calls==0
    h.samples();assert h.business.fixture.encoder.calls==3 and h.business.fixture.store.enrolls==[]
    h.say('确认保存身份关联');assert h.business.fixture.store.enrolls==[]
    h.say('确认登记');assert h.business.fixture.store.enrolls==[]
    h.say('确认保存声纹');assert len(h.business.fixture.store.enrolls)==1
    assert h.commands==[] and h.business.route_calls==0 and h.business.links==h.business.grants==0
    assert h.view['modules']['identity']['db_version']==3 and len(h.view['modules']['identity']['people'])==1

def test_bare_voice_survives_polling_and_only_explicit_name_followup_starts_original_device(monkeypatch):
    h=Harness(monkeypatch);h.say('登记声纹')
    assert h.business.fixture.device.sessions=={}
    for _ in range(20):
        state=h.handler.public();assert state['entry_mode']=='voice' and state['entry_name_pending'] is True
        assert state['speaker']['active'] is False
    h.say('我叫合成测试')
    row=next(iter(h.business.fixture.device.sessions.values()))
    assert row['stage']=='samples' and row['vectors']==[] and row['until']==181.
    assert h.business.calls[-1]=='登记我的声纹，我叫合成测试'

@pytest.mark.parametrize('action',['cancel','reset','expired','session'])
def test_bare_voice_name_authority_cannot_survive_cancel_reset_expiry_or_session_change(monkeypatch,action):
    h=Harness(monkeypatch);h.say('登记声纹')
    if action=='cancel':h.say('取消')
    elif action=='reset':h.handler.reset()
    elif action=='expired':h.clock.now+=121
    else:h.jobs.session_id='different-session'
    h.business.route=lambda *a,**k:None
    h.handler._visual=lambda job:None;h.handler._gallery=lambda job:None
    h.say('我叫合成测试')
    assert h.business.fixture.device.sessions=={} and h.business.fixture.store.enrolls==[]

def test_cross_modality_start_never_becomes_voice_sample(monkeypatch):
    h=Harness(monkeypatch);h.say('登记声纹，我叫合成测试');h.say('合成第一段测试语音')
    before=h.business.fixture.encoder.calls
    h.say('登记人脸，我叫合成人脸');h.say('记住我，我叫合成测试')
    assert h.business.fixture.encoder.calls==before==1
    assert h.commands==[] and h.business.route_calls==0

def test_voice_command_and_final_confirmation_cannot_touch_active_face(monkeypatch):
    h=Harness(monkeypatch);h.say('登记人脸，我叫合成测试')
    h.say('登记声纹，我叫合成声纹');h.say('确认保存声纹')
    assert h.handler.flow.stage=='authorize' and h.business.calls==[] and h.commands==[]

@pytest.mark.parametrize('text',['我是谁','听声音我是谁','声纹登记成功了吗'])
def test_identity_and_voice_status_queries_are_not_voice_samples(monkeypatch,text):
    h=Harness(monkeypatch);h.say('登记声纹，我叫合成测试');h.say('合成第一段测试语音')
    before=h.business.fixture.encoder.calls;h.say(text)
    assert h.business.fixture.encoder.calls==before==1

def test_original_quality_and_duplicate_pcm_rejection_are_retained(monkeypatch):
    h=Harness(monkeypatch);h.say('登记声纹，我叫合成测试')
    h.say('合成不足时长',seconds=2.5);assert h.business.fixture.encoder.calls==0
    h.say('合成第一个样本',seed=99);h.say('合成不同文字同一份音频',seed=99)
    assert h.business.fixture.encoder.calls==1 and h.business.fixture.store.enrolls==[]

def test_face_finished_asynchronously_first_voice_command_does_not_get_stale_busy(monkeypatch):
    h=Harness(monkeypatch);h.say('登记人脸，我叫合成测试')
    assert h.handler._standalone_entry['mode']=='face'
    h.handler.flow.reset();h.say('登记声纹，我叫合成测试')
    assert h.handler._standalone_entry['mode']=='voice'
    assert len(h.business.fixture.device.sessions)==1 and len(h.business.calls)==1

def test_voice_finished_asynchronously_first_face_command_does_not_get_stale_busy(monkeypatch):
    h=Harness(monkeypatch);h.say('登记声纹，我叫合成测试')
    h.business.fixture.device.sessions.clear();h.say('登记人脸，我叫合成测试')
    assert h.handler._standalone_entry['mode']=='face' and h.handler.flow.stage=='authorize'
    assert h.commands==[]

def test_original_face_start_and_guide_save_then_first_voice_command_are_separate(monkeypatch):
    h=Harness(monkeypatch);h.auto_ready=True
    h.say('登记人脸，我叫合成测试');p=h.say('确认登记')
    assert any('登记成功' in text for text,_ in p.replies)
    assert [c['action'] for c in h.commands]==['identity_sample_start','identity_enroll']
    assert h.handler.flow.stage=='idle' and h.handler._standalone_entry is None
    assert h.business.calls==[] and h.business.route_calls==0
    h.say('登记声纹，我叫合成测试')
    assert len(h.business.fixture.device.sessions)==1 and len(h.business.calls)==1
    assert len(h.commands)==2 and h.business.links==h.business.grants==0

def test_original_voice_save_then_first_face_command_are_separate(monkeypatch):
    h=Harness(monkeypatch);h.say('登记声纹，我叫合成测试');h.samples();h.say('确认保存声纹')
    assert len(h.business.fixture.store.enrolls)==1 and h.handler._standalone_entry is None
    before=len(h.business.calls);h.say('登记人脸，我叫合成人脸')
    assert h.handler.flow.stage=='authorize' and len(h.business.calls)==before
    assert h.business.route_calls==0 and h.business.links==h.business.grants==0

def test_repeating_bare_voice_does_not_extend_the_original_name_wait_window(monkeypatch):
    h=Harness(monkeypatch);h.say('登记声纹');deadline=h.handler._standalone_entry['until']
    h.clock.now+=60;h.say('登记声纹')
    assert h.handler._standalone_entry['until']==deadline
    h.clock.now=deadline+.001
    h.business.route=lambda *a,**k:None;h.handler._visual=lambda job:None;h.handler._gallery=lambda job:None
    h.say('我叫合成测试')
    assert h.business.fixture.device.sessions=={} and h.handler._standalone_entry is None

@pytest.mark.parametrize('cancel',['epoch_reset','generation_cancel'])
def test_cancel_between_begin_turn_and_producer_cannot_rearm_bare_voice(monkeypatch,cancel):
    h=Harness(monkeypatch)
    if cancel=='epoch_reset':h.controller.before_produce=h.handler.reset
    else:h.controller.before_produce=lambda:h.last_job.cancelled.set()
    with pytest.raises(StaleGeneration):h.say('登记声纹')
    assert h.handler._standalone_entry is None and h.business.calls==[]

def test_unified_compatibility_still_reaches_original_router_and_cannot_steal_standalone(monkeypatch):
    h=Harness(monkeypatch)
    class OriginalRouteReached(Exception):pass
    def original(*a,**k):raise OriginalRouteReached()
    h.business.route=original;h.handler._visual=lambda job:None;h.handler._gallery=lambda job:None
    with pytest.raises(OriginalRouteReached):h.say('记住我，我叫合成测试')
    assert h.handler._standalone_entry is None

def test_preexisting_unified_or_other_original_session_blocks_new_entry(monkeypatch):
    h=Harness(monkeypatch);h.business.forced_active=True
    p=h.say('登记声纹，我叫合成测试')
    assert not p.fallback and h.handler._standalone_entry is None
    assert h.business.calls==[] and h.business.fixture.store.enrolls==[]
