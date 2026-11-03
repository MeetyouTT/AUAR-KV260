"""Diagnostics, privacy and original admission behavior; synthetic data only."""
import copy
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import threading
from types import SimpleNamespace

import pytest

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'candidate_runtime_v2'))
from board.identity.voice_enrollment import VoiceEnrollment
from board.runtime.board_business import LocalIdentityReplies
from board.runtime.board_speaker_business import BoardSpeakerBusiness
from common.identity_links import IdentityLinkRegistry,ReceiptAuthority
from common.speaker_visual import unavailable
from tests.framework.test_simple_enrollment import snapshot

SECRET='PRIVACY_SENTINEL_NAME_ID_TEXT_EMBEDDING_DO_NOT_RETAIN'
PHASES={'idle','name','authorize','sampling','confirm'}
FACE_KEYS={'version','phase_enter','phase_exit','gate','reply_code','exception','capture_present',
    'capture_actual','current_snapshot_valid','current_actual','capture_single','current_single',
    'capture_current_owner_equal','workflow_owner_equal','identity_enroll','identity_sample_start',
    'reset_count','reset_internal_count','reset_external_count','reset_source','reset_phase','reset_gate','reset_had_sampling'}
LINK_KEYS={'version','gate','phase','outcome','visual_state','visual_reason','visual_present','visual_actual',
    'visual_context_matches','visual_guard_valid','actor_matches','generation_not_old','request_distinct',
    'capture_distinct','pcm_distinct','explicit_confirmation','service_epoch_same','camera_epoch_same','target_same',
    'gallery_revision_same','face_identity_same','guard_same'}

def assert_scalar_trace(trace,keys):
    assert set(trace)==keys
    assert all(value is None or type(value) in (int,bool,str) for value in trace.values())
    assert SECRET not in json.dumps(trace)

def face_flow():
    view=snapshot();commands=[]
    flow=VoiceEnrollment('boot',lambda:copy.deepcopy(view),commands.append,
                         simple=True,clock=lambda:1.,now_ms=lambda:1000)
    return flow,view,commands

def activate(flow,view):
    reply=flow.handle('帮我登记身份，我叫合成测试',copy.deepcopy(view))
    assert reply['code']=='prepare_name'
    assert flow.stage=='authorize'

@pytest.mark.parametrize('kind,gate',[
    ('missing','CAPTURE_MISSING'),('not_actual','CAPTURE_NOT_ACTUAL'),
    ('current_invalid','CURRENT_SNAPSHOT'),('current_fixture','CURRENT_NOT_ACTUAL'),
    ('owner','CAPTURE_CURRENT_OWNER'),('capture_multiple','CAPTURE_SINGLE'),
    ('current_multiple','CURRENT_SINGLE'),('capability','CAPABILITY'),('workflow_owner','WORKFLOW_OWNER'),
])
def test_face_failure_gate_and_original_reset_are_visible(kind,gate):
    flow,view,commands=face_flow();activate(flow,view);captured=copy.deepcopy(view)
    if kind=='missing':captured=None
    elif kind=='not_actual':captured['source_kind']='fixture'
    elif kind=='current_invalid':view['observed_mono_ms']=5000
    elif kind=='current_fixture':view['source_kind']='fixture'
    elif kind=='owner':captured['modules']['target']['selected']['track_generation']=2
    elif kind=='capture_multiple':captured['modules']['vision']['people_count']=2
    elif kind=='current_multiple':view['modules']['vision']['people_count']=2
    elif kind=='capability':view['capabilities']['identity_sample_start']=False
    elif kind=='workflow_owner':flow.owner=('boot','other-service',flow.owner[2],flow.owner[3])
    reply=flow.handle('确认登记',captured)
    assert reply['code'] in ('changed','face_unavailable')
    trace=flow.confirmation_diagnostics();assert_scalar_trace(trace,FACE_KEYS)
    assert trace['gate']==gate
    assert trace['phase_enter']=='authorize' and trace['phase_exit']=='idle'
    assert trace['reset_source']=='INTERNAL' and trace['reset_phase']=='authorize'
    assert commands==[]

def test_external_recording_cleanup_reset_is_distinct_and_keeps_previous_trace():
    flow,view,commands=face_flow();activate(flow,view)
    before=flow.confirmation_diagnostics();flow.reset();after=flow.confirmation_diagnostics()
    assert after['reset_source']=='EXTERNAL' and after['reset_phase']=='authorize'
    assert after['reset_external_count']==before['reset_external_count']+1
    assert after['reply_code']=='prepare_name' and after['gate']==before['gate']
    assert flow.public()=={'stage':'idle','active':False}
    assert commands==[]

def test_internal_failure_trace_survives_followup_external_reset():
    flow,view,_=face_flow();activate(flow,view);flow.handle('确认登记',None)
    failed=flow.confirmation_diagnostics();flow.reset();last=flow.confirmation_diagnostics()
    assert last['gate']==failed['gate']=='CAPTURE_MISSING'
    assert last['reply_code']=='changed'
    assert last['reset_source']=='EXTERNAL' and last['reset_phase']=='idle'
    assert last['reset_internal_count']>=1

def test_unrelated_ordinary_chat_does_not_overwrite_latched_failure_or_reset():
    flow,view,_=face_flow();activate(flow,view);flow.handle('确认登记',None);flow.reset()
    before=flow.confirmation_diagnostics()
    assert flow.handle('今天心情不错',copy.deepcopy(view)) is None
    assert flow.confirmation_diagnostics()==before

def test_unrelated_chat_before_any_enrollment_has_no_fake_confirmation_gate():
    flow,view,_=face_flow();before=flow.confirmation_diagnostics()
    assert flow.handle('今天心情不错',copy.deepcopy(view)) is None
    assert flow.confirmation_diagnostics()==before

def test_valid_face_mode_uses_face_count_with_two_body_detections():
    flow,view,commands=face_flow();key=copy.deepcopy(view['modules']['target']['selected'])
    view['modules']['vision']['people_count']=2
    view['modules']['identity'].update(target_kind='face',face_count=1,face_target=key,
                                      face_targets=[{'key':key,'label':'face'}])
    reply=flow.handle('帮我登记身份，我叫合成测试',copy.deepcopy(view))
    assert reply['code']=='prepare_name'
    trace=flow.confirmation_diagnostics()
    assert trace['capture_single'] is True and trace['current_single'] is True
    assert commands==[]

def test_metadata_writer_and_reader_reject_raw_fields_and_unmapped_enums():
    flow,_,_=face_flow()
    flow._trace_confirmation(name=SECRET,owner={'id':SECRET},text=SECRET,pcm=b'bad',
        gate=SECRET,phase_enter=SECRET,reply_code=SECRET,exception=SECRET,capture_single=SECRET)
    assert SECRET not in repr(flow._confirmation_trace)
    assert_scalar_trace(flow.confirmation_diagnostics(),FACE_KEYS)
    flow._confirmation_trace.update(name=SECRET,gate={'name':SECRET},reply_code=[SECRET])
    assert_scalar_trace(flow.confirmation_diagnostics(),FACE_KEYS)

def pcm(seed):return bytes((seed,0))*4800
def owner(seed):
    raw=pcm(seed)
    return dict(protocol='aura-asr-1',board_boot_id='boot',session_id='session',request_id='request-'+str(seed),
        generation=seed,capture_id='capture-'+str(seed),sample_count=len(raw)//2,
        pcm_sha256=hashlib.sha256(raw).hexdigest(),budget_ms=60000)
def visual(meta):
    return dict(version=1,context=dict(meta),source_kind='actual',state='FACE_AT_CAPTURE_BOUNDARIES',
        reason='NOT_ACTIVE_SPEAKER_PROOF',evidence=dict(service_epoch='service',camera_epoch='camera',
            target=dict(camera_epoch='camera',track_id=1,track_generation=1),gallery_revision=2,
            face_identity_id=None,boundary_start_ms=1000,boundary_end_ms=4000,checked_ms=4000,
            source_start_ms=990,source_end_ms=3990,frame_start=1,frame_end=2))

@pytest.fixture
def registry(tmp_path):
    clock=[1000.]
    r=IdentityLinkRegistry(tmp_path/'synthetic-links.sqlite3',ReceiptAuthority(b'synthetic-key-only-'*3),clock=lambda:clock[0])
    first=owner(1)
    attempt=r.start(first,'记住我，我叫合成测试',visual=visual(first),
        face_gallery=dict(store_id='face',model_id='synthetic-face',revision=2),
        voice_gallery=dict(store_id='voice',model_id='synthetic-voice',revision=0))['attempt_id']
    return r,attempt,clock

@pytest.mark.parametrize('kind,gate',[
    ('foreign_visual','VISUAL'),('unavailable','VISUAL'),('stale','VISUAL'),
    ('request','DISTINCT_CAPTURE'),('capture','DISTINCT_CAPTURE'),('pcm','DISTINCT_CAPTURE'),
    ('old_generation','OLD_GENERATION'),('foreign_actor','FOREIGN_ATTEMPT'),('expired','STATE'),
])
def test_registry_precise_gate_without_exception_text_or_raw_values(registry,kind,gate):
    r,attempt,clock=registry;m=owner(2);v=visual(m)
    if kind=='foreign_visual':v=visual(owner(1))
    elif kind=='unavailable':v=unavailable(m,'NO_SINGLE_FACE')
    elif kind=='stale':v['evidence']['checked_ms']=8000
    elif kind=='request':m['request_id']=owner(1)['request_id'];v=visual(m)
    elif kind=='capture':m['capture_id']=owner(1)['capture_id'];v=visual(m)
    elif kind=='pcm':m['pcm_sha256']=owner(1)['pcm_sha256'];v=visual(m)
    elif kind=='old_generation':m['generation']=0;v=visual(m)
    elif kind=='foreign_actor':m['session_id']='other';v=visual(m)
    elif kind=='expired':clock[0]+=181
    with pytest.raises(ValueError):r.confirm(attempt,m,'确认登记',v)
    trace=r.confirmation_diagnostics();assert_scalar_trace(trace,LINK_KEYS)
    assert trace['gate']==gate and trace['outcome']=='ValueError'
    if kind=='foreign_visual':assert trace['visual_context_matches'] is False
    if kind=='unavailable':assert trace['visual_reason']=='NO_SINGLE_FACE'

def test_registry_same_face_confirmation_retains_all_original_guard_requirements(registry):
    r,attempt,_=registry
    assert r.confirm(attempt,owner(2),'确认登记',visual(owner(2))) is True
    trace=r.confirmation_diagnostics();assert_scalar_trace(trace,LINK_KEYS)
    assert trace['gate']=='CONFIRMED' and trace['phase']=='SAMPLING_FACE' and trace['outcome']=='TRUE'
    assert all(trace[key] is True for key in ('request_distinct','capture_distinct','pcm_distinct','guard_same',
        'service_epoch_same','camera_epoch_same','target_same','gallery_revision_same','face_identity_same'))

def test_registry_lifecycle_cancel_keeps_original_state_transition(registry):
    r,attempt,_=registry;v=visual(owner(2));v['evidence']['target']['track_id']=2
    assert r.confirm(attempt,owner(2),'确认登记',v) is False
    trace=r.confirmation_diagnostics();assert trace['gate']=='LIFECYCLE_CHANGED'
    assert trace['target_same'] is False and trace['phase']=='CANCELLED'
    assert r.attempt(attempt,owner(2))['state']=='CANCELLED'

def test_registry_non_confirmation_does_not_gain_consent(registry):
    r,attempt,_=registry
    assert r.confirm(attempt,owner(2),'好的',visual(owner(2))) is False
    assert r.confirmation_diagnostics()['gate']=='NOT_CONFIRMATION'
    assert r.attempt(attempt,owner(2))['state']=='AWAIT_CONFIRMATION'

def test_trace_does_not_add_key_error_to_original_malformed_guard_rejection(registry):
    r,attempt,_=registry
    with r._db(write=True) as db:
        db.execute('UPDATE binding_attempts SET face_guard=? WHERE attempt_id=?',('{}',attempt))
    assert r.confirm(attempt,owner(2),'确认登记',visual(owner(2))) is False
    trace=r.confirmation_diagnostics()
    assert trace['gate']=='LIFECYCLE_CHANGED' and trace['guard_same'] is False
    assert r.attempt(attempt,owner(2))['state']=='CANCELLED'

def test_registry_busy_is_a_distinct_timeout_gate(registry):
    r,attempt,_=registry;locked=threading.Event();release=threading.Event()
    def hold():
        with r.lock:locked.set();release.wait(1)
    worker=threading.Thread(target=hold);worker.start();assert locked.wait(.5)
    try:
        with pytest.raises(TimeoutError):r.confirm(attempt,owner(2),'确认登记',visual(owner(2)))
    finally:release.set();worker.join(1)
    trace=r.confirmation_diagnostics()
    assert trace['gate']=='EXPIRE' and trace['outcome']=='TimeoutError'

@pytest.mark.parametrize('bad', [SECRET, {'name':SECRET}, [SECRET]])
def test_registry_unmapped_reason_never_leaks_or_changes_original_value_error(registry,bad):
    r,attempt,_=registry;v=visual(owner(2));v['reason']=bad
    # A syntactically allowed but unsupported reason is rejected by original policy.
    with pytest.raises(ValueError):r.confirm(attempt,owner(2),'确认登记',v)
    assert SECRET not in repr(getattr(r,'_confirmation_trace',{}))
    assert_scalar_trace(r.confirmation_diagnostics(),LINK_KEYS)

def test_actual_public_projection_is_ram_only_and_keeps_independent_face_and_unified_gate(registry,monkeypatch):
    r,attempt,_=registry
    with pytest.raises(ValueError):r.confirm(attempt,owner(2),'确认登记',visual(owner(1)))
    flow,view,_=face_flow();activate(flow,view);flow.reset()
    speaker=object.__new__(BoardSpeakerBusiness)
    speaker.hub=SimpleNamespace(speaker=SimpleNamespace(sessions={}),binding=SimpleNamespace(
        registry=r,router=SimpleNamespace(active={},name_waiting={})))
    speaker.lock=threading.RLock();speaker._refresh_public()
    handler=object.__new__(LocalIdentityReplies);handler.flow=flow;handler.business=speaker
    monkeypatch.setattr(sqlite3,'connect',lambda *a,**k:pytest.fail('Public trace must not open a database'))
    value=handler.public();trace=value['confirmation_trace']
    assert_scalar_trace(trace['face'],FACE_KEYS);assert_scalar_trace(trace['unified'],LINK_KEYS)
    assert trace['face']['reset_source']=='EXTERNAL'
    assert trace['unified']['gate']=='VISUAL' and trace['unified']['visual_context_matches'] is False
    assert SECRET not in json.dumps(value)
