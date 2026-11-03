import bootstrap
import copy,hashlib,json,math,sqlite3
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from common.anonymous_voice import AnonymousVoiceStore,AnonymousPolicy,validate_alias
from common.identity_links import IdentityLinkRegistry,ReceiptAuthority,binding_intent,_guard
from common.binding_intent import face_enrollment_text
from common.speaker_turns import record,validate_record
from tools.progressive_speaker import ProgressiveSpeakerAnalyzer
from tools.speaker_device import SpeakerDevice
from tools.enrollment_receipts import SpeakerEnrollmentBridge,face_commit_payload,existing_face_payload
from tools.unified_identity_binding import UnifiedBindingRouter
from tools.binding_identity_stream import BindingIdentityReplyStream

def pcm(seed):return bytes((seed,0))*48000
def meta(seed,**changes):
    raw=pcm(seed)
    value=dict(protocol='aura-asr-1',board_boot_id='boot',session_id='session',request_id='request-'+str(seed),generation=seed,
      capture_id='capture-'+str(seed),sample_count=len(raw)//2,pcm_sha256=hashlib.sha256(raw).hexdigest(),budget_ms=60000)
    return dict(value,**changes)
def visual(owner,*,revision=0,person=None,epoch='camera',track=1):
    return dict(version=1,context=owner,source_kind='actual',state='FACE_AT_CAPTURE_BOUNDARIES',reason='NOT_ACTIVE_SPEAKER_PROOF',
      evidence=dict(service_epoch='service',camera_epoch=epoch,target=dict(camera_epoch=epoch,track_id=track,track_generation=1),gallery_revision=revision,
       face_identity_id=person,boundary_start_ms=1000,boundary_end_ms=4000,checked_ms=4000,source_start_ms=990,source_end_ms=3990,frame_start=1,frame_end=2))
FACE=dict(store_id='face-store',model_id='fake-face',revision=0)
VOICE=dict(store_id='voice-store',model_id='fake-voice',revision=0)
def fixture_registry(tmp_path,*,alias=True):
    clock=[1000.];store=AnonymousVoiceStore(tmp_path/'anonymous.sqlite','fake-voice',3,clock=lambda:clock[0])
    registry=IdentityLinkRegistry(tmp_path/'links.sqlite',ReceiptAuthority(b'synthetic-test-key-never-production'*2),
      anonymous_lookup=store.active,clock=lambda:clock[0])
    a=store.observe(meta(1),(1,0,0),voiced_ms=3000) if alias else None
    return registry,store,a,clock
def start_confirm(registry,alias=None,*,person=None):
    first=meta(1);second=meta(2);v1=visual(first,person=person);v2=visual(second,person=person)
    attempt=registry.start(first,'记住我，我叫小明',visual=v1,face_gallery=FACE,voice_gallery=VOICE,anonymous=alias)['attempt_id']
    assert registry.confirm(attempt,second,'确认登记',v2)
    return attempt
def receipt(registry,attempt,modality,*,state='COMMITTED',identity=None,fingerprint='a'*64,commit=None):
    committed=commit or meta(2 if modality=='face' else 6)
    row=registry.attempt(attempt,committed);gallery=json.loads(row[modality+'_gallery']);kind=modality
    value=dict(version=1,attempt_id=attempt,origin_context=json.loads(row['origin']),commit_context=committed,
      modality=kind,state=state,operation_id=kind+'-operation',store_id=gallery['store_id'],identity_id=identity or kind+'-identity',model_id=gallery['model_id'],
      revision_before=gallery['revision'],revision_after=gallery['revision']+(state=='COMMITTED'),template_fingerprint=fingerprint,display_name=row['name'],
      checks=dict(quality_passed=True,explicit_confirmation=True,original_policy=('original_face_match_and_explicit_link_consent' if state=='EXISTING_CONFIRMED' else 'original_face_enrollment') if kind=='face' else 'original_three_utterance_enrollment',single_speaker_verified=False),
      face_guard=json.loads(row['face_guard']),capture_ids=['capture-3','capture-4','capture-5'] if kind=='voice' else [],
      pcm_digests=[meta(i)['pcm_sha256'] for i in (3,4,5)] if kind=='voice' else [])
    return registry.authority.sign(value)
def activate(registry,attempt):
    registry.accept_receipt(attempt,meta(2),receipt(registry,attempt,'face'))
    return registry.accept_receipt(attempt,meta(6),receipt(registry,attempt,'voice'))
def proof(owner,kind,*,identity=None,revision=1,fingerprint='a'*64,now=1000.,calibrated=True):
    gallery=FACE if kind=='face' else VOICE
    return dict(context=owner,modality=kind,source_kind='actual',match_state='KNOWN',original_matcher_accepted=True,
      field_calibrated=calibrated,store_id=gallery['store_id'],identity_id=identity or kind+'-identity',model_id=gallery['model_id'],
      gallery_revision=revision,template_fingerprint=fingerprint,observed_at=now,expires_at=now+2)

@pytest.mark.parametrize('text,name',[('记住我，我叫小明','小明'),('我叫小明，请记住我','小明'),('请记住我，我的名字是Alex','Alex')])
def test_explicit_self_intent(text,name):assert binding_intent(text)==dict(kind='remember_self',name=name)
@pytest.mark.parametrize('text',['小明说他很累','他说记住我我叫小明','不要记住我','她叫小明','“记住我，我叫小明”','请记住我喜欢蓝色','我是谁'])
def test_mentions_quotes_negation_are_not_binding(text):assert binding_intent(text)['kind']=='ordinary'
def test_name_only_is_hint_and_board_translation_is_narrow():
    assert binding_intent('我叫小明')['kind']=='name_hint'
    assert face_enrollment_text('记住我，我叫小明')=='帮我登记身份，我叫小明'
    assert face_enrollment_text('小明说他很累')=='小明说他很累'
    assert face_enrollment_text('我叫小明',active=True)=='我叫小明'
    assert face_enrollment_text('我叫小明',active=False)=='帮我登记身份，我叫小明'
    assert face_enrollment_text('记住我')=='帮我登记身份'

def test_a_numbers_are_stable_internal_ids_distinct_and_not_identity(tmp_path):
    _,s,a,_=fixture_registry(tmp_path)
    b=s.observe(meta(2),(0,1,0),voiced_ms=3000)
    same=s.observe(meta(3),(.999,.01,0),voiced_ms=3000)
    assert a['code']=='a1' and b['code']=='a2' and same['cluster_id']==a['cluster_id']
    assert a['identity_verified'] is False and a['personal_memory_allowed'] is False
    assert len(a['cluster_id'])==32 and a['code']!=a['cluster_id']
def test_three_distinct_captures_and_pcm_replay_does_not_strengthen(tmp_path):
    _,s,a,_=fixture_registry(tmp_path)
    same=meta(1,request_id='replay-request',capture_id='different-capture',generation=2)
    assert s.observe(same,(1,0,0),voiced_ms=3000)['distinct_captures']==1
    s.observe(meta(3),(1,0,0),voiced_ms=3000)
    result=s.observe(meta(4),(1,0,0),voiced_ms=3000)
    assert result['state']=='STABLE_CANDIDATE' and result['identity_verified'] is False
def test_ambiguous_voice_does_not_take_top_identity(tmp_path):
    _,s,a,_=fixture_registry(tmp_path)
    s.observe(meta(2),(.8,.6,0),voiced_ms=3000)
    result=s.observe(meta(3),(.95,.31,0),voiced_ms=3000)
    assert result['state']=='AMBIGUOUS' and result['code'] is None
def test_frozen_anchor_prevents_drift(tmp_path):
    _,s,a,_=fixture_registry(tmp_path)
    s.observe(meta(2),(math.cos(math.radians(20)),math.sin(math.radians(20)),0),voiced_ms=3000)
    result=s.observe(meta(3),(math.cos(math.radians(35)),math.sin(math.radians(35)),0),voiced_ms=3000)
    assert result['cluster_id']!=a['cluster_id']
    with sqlite3.connect(s.path) as db:assert json.loads(db.execute('SELECT anchor FROM anonymous_anchors WHERE cluster_id=?',(a['cluster_id'],)).fetchone()[0])==[1.,0.,0.]
def test_ttl_erases_anchor_and_never_reuses_label(tmp_path):
    clock=[1000.];s=AnonymousVoiceStore(tmp_path/'a.sqlite','fake',3,policy=AnonymousPolicy(ttl_seconds=60),clock=lambda:clock[0])
    first=s.observe(meta(1),(1,0,0),voiced_ms=3000);clock[0]+=61
    second=s.observe(meta(2),(1,0,0),voiced_ms=3000)
    assert second['code']=='a2'
    with sqlite3.connect(s.path) as db:assert not db.execute('SELECT 1 FROM anonymous_anchors WHERE cluster_id=?',(first['cluster_id'],)).fetchone()
def test_delete_invalidates_inflight_revision_and_no_alias_code_reuse(tmp_path):
    _,s,a,_=fixture_registry(tmp_path);revision=s.revision;s.delete(a['cluster_id'])
    with pytest.raises(ValueError):s.observe(meta(2),(1,0,0),voiced_ms=3000,expected_revision=revision)
    assert s.observe(meta(3),(1,0,0),voiced_ms=3000)['code']=='a2'
def test_capacity_counts_old_boots_and_never_evicts_active_voice(tmp_path):
    s=AnonymousVoiceStore(tmp_path/'a.sqlite','fake',3,policy=AnonymousPolicy(max_clusters=1))
    s.observe(meta(1),(1,0,0),voiced_ms=3000)
    result=s.observe(meta(2,board_boot_id='new-boot'),(1,0,0),voiced_ms=3000)
    assert result['state']=='CAPACITY' and s.health()['active_clusters']==1
@pytest.mark.parametrize('vector,duration,overlap',[(1,0,'unknown'),(1,3000,'detected')])
def test_bad_quality_has_no_alias(tmp_path,vector,duration,overlap):
    _,s,_,_=fixture_registry(tmp_path)
    assert s.observe(meta(2),(1,0,0),voiced_ms=duration,overlap=overlap)['code'] is None
def test_rejects_other_app_db_and_model_change(tmp_path):
    path=tmp_path/'other.sqlite'
    with sqlite3.connect(path) as db:db.execute('CREATE TABLE keep(value)');db.execute('INSERT INTO keep VALUES(7)')
    with pytest.raises(ValueError):AnonymousVoiceStore(path,'fake',3)
    with sqlite3.connect(path) as db:assert db.execute('SELECT * FROM keep').fetchall()==[(7,)]
    s=AnonymousVoiceStore(tmp_path/'a.sqlite','one',3)
    with pytest.raises(ValueError):AnonymousVoiceStore(s.path,'two',3)

def test_pending_requires_both_original_commits_and_no_auth(tmp_path):
    r,s,a,_=fixture_registry(tmp_path);attempt=start_confirm(r,a)
    assert r.resolve(meta(2),[proof(meta(2),'face')])['state']=='UNKNOWN'
    first=r.accept_receipt(attempt,meta(2),receipt(r,attempt,'face'))
    assert first['unified_saved'] is False and first['face_already_saved']
    result=r.accept_receipt(attempt,meta(6),receipt(r,attempt,'voice'))
    assert result['state']=='ACTIVE' and result['personal_memory_allowed'] is False
    assert r.resolve(meta(7),[proof(meta(7),'voice')])['claim_scope']=='voice_candidate'
    assert r.resolve(meta(7),[proof(meta(7),'face')])['claim_scope']=='visible_person'
@pytest.mark.parametrize('mutation',[lambda p:p.update(state='ACK'),lambda p:p.update(display_name='别人'),
 lambda p:p.update(model_id='wrong'),lambda p:p.update(revision_before=8),lambda p:p['checks'].update(quality_passed=False),
 lambda p:p.update(version=True),lambda p:p.update(revision_before=False),lambda p:p['checks'].update(quality_passed=1)])
def test_missing_original_policy_or_changed_receipt_rejected(tmp_path,mutation):
    r,_,a,_=fixture_registry(tmp_path);attempt=start_confirm(r,a);payload=receipt(r,attempt,'face')['payload'];mutation(payload)
    with pytest.raises(ValueError):r.accept_receipt(attempt,meta(2),r.authority.sign(payload))
def test_unsigned_or_tampered_receipt_rejected(tmp_path):
    r,_,a,_=fixture_registry(tmp_path);attempt=start_confirm(r,a);signed=receipt(r,attempt,'face');signed['payload']['identity_id']='forged'
    with pytest.raises(ValueError):r.accept_receipt(attempt,meta(2),signed)
    with pytest.raises(ValueError):r.accept_receipt(attempt,meta(2),dict(payload={},mac='0'*64))
def test_lifecycle_change_cancels_before_writes(tmp_path):
    r,_,a,_=fixture_registry(tmp_path);first=meta(1)
    attempt=r.start(first,'记住我，我叫小明',visual=visual(first),face_gallery=FACE,voice_gallery=VOICE,anonymous=a)['attempt_id']
    assert not r.confirm(attempt,meta(2),'确认登记',visual(meta(2),epoch='other-camera'))
    assert r.attempt(attempt,meta(2))['state']=='CANCELLED'
def test_cancel_after_one_commit_is_explicit_partial_and_late_voice_cannot_link(tmp_path):
    r,_,a,_=fixture_registry(tmp_path);attempt=start_confirm(r,a);r.accept_receipt(attempt,meta(2),receipt(r,attempt,'face'))
    result=r.cancel(attempt,meta(6));assert result['state']=='PARTIAL_CANCELLED' and result['face_already_saved']
    with pytest.raises(ValueError):r.accept_receipt(attempt,meta(6),receipt(r,attempt,'voice'))
def test_expiry_survives_reopen_and_rejects_late_result(tmp_path):
    r,_,a,clock=fixture_registry(tmp_path);attempt=start_confirm(r,a);clock[0]+=181
    assert r.attempt(attempt,meta(8))['state']=='EXPIRED'
    reopened=IdentityLinkRegistry(r.path,r.authority,clock=lambda:clock[0])
    with pytest.raises(ValueError):reopened.accept_receipt(attempt,meta(9),receipt(r,attempt,'face'))
def test_same_name_requires_explicit_selection_not_automatic_merge(tmp_path):
    r,_,a,_=fixture_registry(tmp_path);attempt=start_confirm(r,a);activate(r,attempt)
    with pytest.raises(ValueError,match='EXPLICIT_EXISTING'):
        r.start(meta(8),'记住我，我叫小明',visual=visual(meta(8)),face_gallery=FACE,voice_gallery=VOICE)
def test_uncalibrated_foreign_stale_or_changed_template_cannot_name(tmp_path):
    r,_,a,_=fixture_registry(tmp_path);attempt=start_confirm(r,a);activate(r,attempt);owner=meta(8)
    for p in (proof(owner,'voice',calibrated=False),proof(meta(9),'voice'),proof(owner,'face',fingerprint='b'*64),proof(owner,'face',now=990)):
        assert r.resolve(owner,[p])['state']=='UNKNOWN'
def test_missing_template_fingerprint_requires_gallery_revision_recheck(tmp_path):
    r,_,a,_=fixture_registry(tmp_path);attempt=start_confirm(r,a)
    r.accept_receipt(attempt,meta(2),receipt(r,attempt,'face',fingerprint=None));r.accept_receipt(attempt,meta(6),receipt(r,attempt,'voice'))
    assert r.resolve(meta(8),[proof(meta(8),'face',revision=2)])['state']=='UNKNOWN'
def test_revocation_cannot_be_undone_by_old_recognition(tmp_path):
    r,_,a,_=fixture_registry(tmp_path);attempt=start_confirm(r,a);person=activate(r,attempt)['person_id']
    with pytest.raises(ValueError):r.revoke_person(person)
    assert r.revoke_person(person,confirmed=True)
    assert r.resolve(meta(8),[proof(meta(8),'voice')])['state']=='UNKNOWN'
def test_expired_alias_does_not_activate_and_retains_partial_receipts(tmp_path):
    r,s,a,_=fixture_registry(tmp_path);attempt=start_confirm(r,a);r.accept_receipt(attempt,meta(2),receipt(r,attempt,'face'));s.delete(a['cluster_id'])
    assert r.accept_receipt(attempt,meta(6),receipt(r,attempt,'voice'))['state']=='PARTIAL_CONFLICT'
    row=r.attempt(attempt,meta(6));assert row['voice_receipt'] is not None
    with sqlite3.connect(r.path) as db:assert db.execute('SELECT count(*) FROM linked_people').fetchone()[0]==0

class Encoder:
    model_id='fake-voice';dimension=3
    def __init__(self):self.calls=0
    def encode(self,raw):self.calls+=1;return (1.,raw[0]/1000.,0.)
def quality(raw):return raw,{'vad_speech_seconds':3.}
def test_anonymous_enabled_reuses_cpu_even_when_named_matching_uncalibrated(tmp_path):
    encoder=Encoder();device=SpeakerDevice(encoder,tmp_path/'speaker.sqlite');s=AnonymousVoiceStore(tmp_path/'a.sqlite',encoder.model_id,3)
    analyzer=ProgressiveSpeakerAnalyzer(device,s,enabled=True,quality=quality)
    voice,alias=analyzer.analyze(meta(1),pcm(1))
    assert voice['state']=='NOT_CALIBRATED' and voice['candidate_id'] is None and alias['code']=='a1' and encoder.calls==1
    encoded=record(meta(1),'a'*32,status='COMPLETE',reason='DESCRIPTIVE_EVIDENCE_ONLY',voice=voice,anonymous=alias)
    assert encoded['version']==2 and validate_record(encoded,meta(1),'a'*32)==encoded
    assert record(meta(2),'a'*32)['version']==1
def test_disabled_temporary_collection_retains_legacy_skip(tmp_path):
    encoder=Encoder();device=SpeakerDevice(encoder,tmp_path/'s.sqlite');s=AnonymousVoiceStore(tmp_path/'a.sqlite',encoder.model_id,3)
    voice,alias=ProgressiveSpeakerAnalyzer(device,s,enabled=False,quality=quality).analyze(meta(1),pcm(1))
    assert alias is None and encoder.calls==0 and voice['state']=='NOT_CALIBRATED'
def test_cancel_or_delete_while_encoding_does_not_write_anon(tmp_path):
    encoder=Encoder();device=SpeakerDevice(encoder,tmp_path/'s.sqlite');s=AnonymousVoiceStore(tmp_path/'a.sqlite',encoder.model_id,3)
    original=encoder.encode;current=[True]
    def cancelled(raw):v=original(raw);current[0]=False;return v
    encoder.encode=cancelled
    with pytest.raises(InterruptedError):ProgressiveSpeakerAnalyzer(device,s,enabled=True,quality=quality).analyze(meta(1),pcm(1),is_current=lambda:current[0])
    assert s.health()['active_clusters']==0
def test_v2_does_not_accept_foreign_or_auth_alias(tmp_path):
    _,s,a,_=fixture_registry(tmp_path)
    with pytest.raises(ValueError):record(meta(2),'a'*32,status='COMPLETE',anonymous=a)
    a['personal_memory_allowed']=True
    with pytest.raises(ValueError):record(meta(1),'a'*32,status='COMPLETE',anonymous=a)

def test_face_ack_or_registered_text_is_not_commit(tmp_path):
    with pytest.raises(ValueError):face_commit_payload(attempt_id='t',origin=meta(1),commit=meta(2),face_guard={},gallery=FACE,name='小明',
      command={'action':'identity_enroll','board_boot_id':'boot','params':{'confirmed':True,'display_name':'小明'}},
      ack={'accepted':True,'command_id':'cmd'},before={'db_version':0,'people':[]},after={'db_version':1,'people':[]})
def test_existing_face_is_read_only_confirmation_not_fake_commit(tmp_path):
    r,_,_,_=fixture_registry(tmp_path,alias=False);attempt=start_confirm(r,person='face-existing');guard=json.loads(r.attempt(attempt,meta(2))['face_guard'])
    identity=dict(state='KNOWN',person_id='face-existing',display_name='小明',db_version=0,people=[dict(person_id='face-existing',display_name='小明')])
    p=existing_face_payload(attempt_id=attempt,origin=meta(1),commit=meta(2),face_guard=guard,gallery=FACE,name='小明',identity=identity,confirmed_link=True)
    assert p['state']=='EXISTING_CONFIRMED' and p['revision_after']==p['revision_before']
    assert r.accept_receipt(attempt,meta(2),r.authority.sign(p))['state']=='SAMPLING_VOICE'

def test_one_intent_face_then_original_three_voice_samples_and_single_final_save(tmp_path):
    r,s,_,_=fixture_registry(tmp_path,alias=False);encoder=Encoder();device=SpeakerDevice(encoder,tmp_path/'speaker.sqlite')
    bridge=SpeakerEnrollmentBridge(device,anonymous_store=s);router=UnifiedBindingRouter(r,bridge,face_gallery=lambda:FACE,voice_gallery=lambda:VOICE)
    first=router.route(meta(1),'记住我，我叫小明',pcm(1),visual=visual(meta(1)))
    assert first['route']=='face_exchange' and first['skip_legacy_device_command'] and first['reply'] is None
    assert first['board_text']=='帮我登记身份，我叫小明'
    attempt=first['attempt_id']
    assert router.route(meta(2),'确认登记',pcm(2),visual=visual(meta(2)))['route']=='face_exchange'
    # Face commit is a scoped callback; the user never repeats a voice-start command.
    with patch('tools.speaker_device.voiced_pcm',quality):
        prompt=router.face_result(meta(2),pcm(2),attempt,{'code':'registered','name':''},receipt(r,attempt,'face'))
        assert '接下来' in prompt and device.state(meta(2))['active']
        for i in (3,4,5):
            out=router.route(meta(i),'公开合成测试句子'+str(i),pcm(i),visual=visual(meta(i),revision=1,person='face-identity'))
            assert out['route']=='device_reply' and not out['unified_saved']
        assert '确认保存身份关联' in out['reply']
        final=router.route(meta(6),'确认保存身份关联',pcm(6),visual=visual(meta(6),revision=1,person='face-identity'))
    assert final['unified_saved'] is True and r.attempt(attempt,meta(6))['state']=='ACTIVE'
    assert len(device.store.people())==1 and device.store.revision==1 and encoder.calls==3
    assert s.health()['active_clusters']==1
def test_ordinary_name_and_missing_camera_do_not_enter_legacy_speaker_flow(tmp_path):
    r,s,_,_=fixture_registry(tmp_path,alias=False);device=SpeakerDevice(Encoder(),tmp_path/'s.sqlite')
    router=UnifiedBindingRouter(r,SpeakerEnrollmentBridge(device),face_gallery=lambda:FACE,voice_gallery=lambda:VOICE)
    assert router.route(meta(1),'我叫小明',pcm(1))['route']=='ordinary'
    first=router.route(meta(2),'记住我，我叫小明',pcm(2))
    assert first['reason']=='BINDING_PRECONDITION_UNAVAILABLE' and not device.state(meta(2))['active']
def test_stream_final_matches_transformed_text_and_rejects_other_capture():
    owner=meta(1);stream=BindingIdentityReplyStream(owner,lambda value,receipt:'人脸已保存，声纹还未完成。')
    with pytest.raises(ValueError):stream.accept(meta(2),stream.token,{'code':'registered','name':''})
    stream.accept(owner,stream.token,{'code':'registered','name':''},final=True)
    rows=list(stream);assert rows[0][1]==rows[-1][1]['reply_text'] and '还未完成' in rows[-1][1]['reply_text']

def test_name_followup_only_after_same_face_remember_request(tmp_path):
    r,s,_,_=fixture_registry(tmp_path,alias=False);device=SpeakerDevice(Encoder(),tmp_path/'s.sqlite')
    router=UnifiedBindingRouter(r,SpeakerEnrollmentBridge(device),face_gallery=lambda:FACE,voice_gallery=lambda:VOICE)
    assert router.route(meta(1),'记住我',pcm(1),visual=visual(meta(1)))['reason']=='NAME_REQUIRED'
    assert router.route(meta(2),'我叫小明',pcm(2),visual=visual(meta(2)))['route']=='face_exchange'
    assert r.health()['pending']==1
def test_name_wait_cancellation_is_face_route_not_standalone_voice_reply(tmp_path):
    r,s,_,_=fixture_registry(tmp_path,alias=False);device=SpeakerDevice(Encoder(),tmp_path/'s.sqlite')
    router=UnifiedBindingRouter(r,SpeakerEnrollmentBridge(device),face_gallery=lambda:FACE,voice_gallery=lambda:VOICE)
    first=router.route(meta(1),'记住我',pcm(1),visual=visual(meta(1)))
    cancelled=router.route(meta(2),'取消登记',pcm(2),visual=visual(meta(2)))
    assert cancelled['route']=='face_exchange' and cancelled['attempt_id']==first['attempt_id']
    assert '已取消' in router.face_result(meta(2),pcm(2),first['attempt_id'],{'code':'cancelled','name':''})
    assert not router.name_waiting and not device.state(meta(2))['active']
def test_board_translation_arms_and_reuses_original_face_name_state():
    from board.identity.voice_enrollment import VoiceEnrollment
    from tests.framework.test_simple_enrollment import snapshot
    current=snapshot()
    flow=VoiceEnrollment('boot',lambda:current,lambda _:(_ for _ in ()).throw(AssertionError('No write expected')),now_ms=lambda:1000,simple=True)
    first=flow.handle(face_enrollment_text('记住我',active=False),current)
    assert first['code']=='ask_name' and flow.public()['active']
    second=flow.handle(face_enrollment_text('我叫小明',active=flow.public()['active']),current)
    assert second['code']=='prepare_name' and second['name']=='小明'
def test_name_followup_changed_face_cannot_start_binding(tmp_path):
    r,s,_,_=fixture_registry(tmp_path,alias=False);device=SpeakerDevice(Encoder(),tmp_path/'s.sqlite')
    router=UnifiedBindingRouter(r,SpeakerEnrollmentBridge(device),face_gallery=lambda:FACE,voice_gallery=lambda:VOICE)
    router.route(meta(1),'记住我',pcm(1),visual=visual(meta(1)))
    assert router.route(meta(2),'我叫小明',pcm(2),visual=visual(meta(2),track=2))['route']=='ordinary_skip_speaker'
    assert r.health()['pending']==0
def test_missing_face_pauses_registration_and_skips_old_speaker_adapter(tmp_path):
    r,s,_,_=fixture_registry(tmp_path,alias=False);device=SpeakerDevice(Encoder(),tmp_path/'s.sqlite')
    router=UnifiedBindingRouter(r,SpeakerEnrollmentBridge(device),face_gallery=lambda:FACE,voice_gallery=lambda:VOICE)
    attempt=router.route(meta(1),'记住我，我叫小明',pcm(1),visual=visual(meta(1)))['attempt_id']
    router.route(meta(2),'确认登记',pcm(2),visual=visual(meta(2)))
    with patch('tools.speaker_device.voiced_pcm',quality):
        router.face_result(meta(2),pcm(2),attempt,{'code':'registered','name':''},receipt(r,attempt,'face'))
        result=router.route(meta(3),'现在先聊点别的',pcm(3),visual=None)
        assert result['route']=='ordinary_skip_speaker' and result['skip_legacy_device_command']
        assert not device.sessions[device.key(meta(3))]['vectors']
        router.route(meta(4),'公开采样句子',pcm(4),visual=visual(meta(4),revision=1,person='face-identity'))
        assert len(device.sessions[device.key(meta(4))]['vectors'])==1
def test_existing_face_initial_reply_never_claims_full_binding(tmp_path):
    r,s,_,_=fixture_registry(tmp_path,alias=False);device=SpeakerDevice(Encoder(),tmp_path/'s.sqlite')
    router=UnifiedBindingRouter(r,SpeakerEnrollmentBridge(device),face_gallery=lambda:FACE,voice_gallery=lambda:VOICE)
    attempt=router.route(meta(1),'记住我，我叫小明',pcm(1),visual=visual(meta(1),person='face-existing'))['attempt_id']
    prompt=router.face_result(meta(1),pcm(1),attempt,{'code':'already_known','name':''})
    assert '请说“确认登记”' in prompt and r.attempt(attempt,meta(1))['state']=='AWAIT_CONFIRMATION'
    assert not device.state(meta(1))['active']
    confirmation=router.route(meta(2),'确认登记',pcm(2),visual=visual(meta(2),person='face-existing'))
    assert confirmation['board_text']=='帮我登记身份，我叫小明' and confirmation['reason']=='EXISTING_FACE_LINK_CONFIRMED'
    p=existing_face_payload(attempt_id=attempt,origin=meta(1),commit=meta(2),face_guard=json.loads(r.attempt(attempt,meta(2))['face_guard']),gallery=FACE,name='小明',
      identity=dict(state='KNOWN',person_id='face-existing',display_name='小明',db_version=0,people=[dict(person_id='face-existing',display_name='小明')]),confirmed_link=True)
    assert '接下来' in router.face_result(meta(2),pcm(2),attempt,{'code':'already_known','name':''},r.authority.sign(p))
    assert device.state(meta(2))['active']
def test_registered_word_without_commit_receipt_does_not_start_voice(tmp_path):
    r,s,_,_=fixture_registry(tmp_path,alias=False);device=SpeakerDevice(Encoder(),tmp_path/'s.sqlite')
    router=UnifiedBindingRouter(r,SpeakerEnrollmentBridge(device),face_gallery=lambda:FACE,voice_gallery=lambda:VOICE)
    attempt=router.route(meta(1),'记住我，我叫小明',pcm(1),visual=visual(meta(1)))['attempt_id']
    router.route(meta(2),'确认登记',pcm(2),visual=visual(meta(2)))
    prompt=router.face_result(meta(2),pcm(2),attempt,{'code':'registered','name':''})
    assert '还没有完成' in prompt and not device.state(meta(2))['active'] and r.health()['active_people']==0
def test_foreign_face_voice_identity_conflict_has_no_person(tmp_path):
    r,s,a,_=fixture_registry(tmp_path);attempt=start_confirm(r,a);activate(r,attempt)
    owner=meta(10)
    other=r.start(owner,'记住我，我叫李雷',visual=visual(owner),face_gallery=FACE,voice_gallery=VOICE)['attempt_id']
    r.confirm(other,meta(11),'确认登记',visual(meta(11)))
    r.accept_receipt(other,meta(11),receipt(r,other,'face',identity='face-other',commit=meta(11)))
    r.accept_receipt(other,meta(12),receipt(r,other,'voice',identity='voice-other',commit=meta(12)))
    resolved=r.resolve(meta(13),[proof(meta(13),'face'),proof(meta(13),'voice',identity='voice-other')])
    assert resolved['state']=='CONFLICT' and resolved['person_id'] is None
def test_original_face_commit_helper_uses_real_readback_identity():
    command=dict(action='identity_enroll',board_boot_id='boot',params={'confirmed':True,'display_name':'小明'})
    ack=dict(accepted=True,command_id='real-command')
    after=dict(db_version=1,people=[dict(person_id='new-face',display_name='小明')],last_operation=dict(command_id='real-command',action='identity_enroll',state='COMMITTED',db_version=1,detail='保存成功'))
    p=face_commit_payload(attempt_id='t',origin=meta(1),commit=meta(2),face_guard={},gallery=FACE,name='小明',command=command,ack=ack,before=dict(db_version=0,people=[]),after=after)
    assert p['identity_id']=='new-face' and p['state']=='COMMITTED'
    after['last_operation']['command_id']='unrelated-command'
    with pytest.raises(ValueError):face_commit_payload(attempt_id='t',origin=meta(1),commit=meta(2),face_guard={},gallery=FACE,name='小明',command=command,ack=ack,before=dict(db_version=0,people=[]),after=after)
def test_v2_evidence_persists_through_original_attribution_table(tmp_path):
    from common.timeline_conversations import TimelineConversationStore
    owner=meta(1);cid='b'*32;store=TimelineConversationStore(tmp_path/'conversation.sqlite')
    _,s,a,_=fixture_registry(tmp_path/'identity')
    store.begin(cid,owner,'public synthetic utterance','public synthetic utterance')
    store.attribution_pending(owner,cid)
    evidence=record(owner,cid,status='COMPLETE',reason='DESCRIPTIVE_EVIDENCE_ONLY',anonymous=a)
    assert store.attribution_merge(owner,cid,evidence)
    assert store.attribution_for_turn(owner,cid)['anonymous']['code']=='a1'
    assert store.records(cid)[0]['user']=='public synthetic utterance'

def test_hub_optional_analyzer_returns_v2_on_existing_single_cpu_worker(tmp_path):
    import threading,time
    from concurrent.futures import ThreadPoolExecutor
    from tools.speaker_turns import SpeakerTurns
    encoder=Encoder();s=AnonymousVoiceStore(tmp_path/'a.sqlite',encoder.model_id,3)
    with ThreadPoolExecutor(max_workers=1) as pool:
        # Production constructs SpeakerDevice on the same sole CPU executor;
        # keep the original SQLite thread-affinity guard in this integration test.
        device=pool.submit(SpeakerDevice,encoder,tmp_path/'s.sqlite').result()
        hub=SimpleNamespace(speaker=device,speaker_pool=pool,speaker_gate=threading.Lock(),
          progressive_speaker=ProgressiveSpeakerAnalyzer(device,s,enabled=True,quality=quality))
        service=SpeakerTurns(hub);service.submit(meta(1),pcm(1),'a'*32)
        until=time.monotonic()+1
        while time.monotonic()<until:
            result=service.result(meta(1),'a'*32)
            if result['status']!='PENDING':break
            time.sleep(.005)
        assert result['status']=='COMPLETE' and result['version']==2 and result['anonymous']['code']=='a1'
        assert result['voice']['state']=='NOT_CALIBRATED' and encoder.calls==1 and result['personal_memory_allowed'] is False
def test_private_gallery_reference_is_readonly_and_returns_only_hash(tmp_path):
    from tools.private_gallery_reference import private_gallery_reference,gallery_fields
    device=SpeakerDevice(Encoder(),tmp_path/'s.sqlite')
    device.store.enroll('voice-id','公开测试',(1,0,0),consent=True,expected_revision=0)
    before=hashlib.sha256(device.store.path.read_bytes()).hexdigest() if hasattr(device.store,'path') else hashlib.sha256((tmp_path/'s.sqlite').read_bytes()).hexdigest()
    reference=private_gallery_reference(tmp_path/'s.sqlite','fake-voice',3,identity_id='voice-id',expected_application_id=device.store.APPLICATION_ID)
    assert reference['revision']==1 and len(reference['template_fingerprint'])==64
    assert 'embedding' not in reference and 'path' not in reference and set(gallery_fields(reference))=={'store_id','model_id','revision'}
    assert hashlib.sha256((tmp_path/'s.sqlite').read_bytes()).hexdigest()==before
def test_stream_rejects_combined_text_beyond_existing_limit():
    owner=meta(1);stream=BindingIdentityReplyStream(owner,lambda v,r:'测'*130)
    stream.accept(owner,stream.token,{'code':'sample_auto','name':''},sequence=0,final=False)
    stream.accept(owner,stream.token,{'code':'registered','name':''},sequence=1,final=True)
    with pytest.raises(ValueError,match='bounded'):list(stream)

def test_active_anonymous_link_names_only_as_live_provisional_candidate(tmp_path):
    r,s,a,_=fixture_registry(tmp_path);attempt=start_confirm(r,a);activate(r,attempt)
    r.anonymous_evidence=s.evidence
    r.voice_reference=lambda identity:dict(identity_id=identity,store_id=VOICE['store_id'],model_id=VOICE['model_id'],revision=1,source_kind='actual',template_fingerprint='a'*64)
    s.observe(meta(3),(1,0,0),voiced_ms=3000)
    current=s.observe(meta(7),(1,0,0),voiced_ms=3000)
    result=r.resolve(meta(7),[],anonymous=current)
    assert result['state']=='PROVISIONAL_NAME_CANDIDATE' and result['name']=='小明' and not result['field_calibrated']
    assert result['identity_verified'] is False and result['personal_memory_allowed'] is False
    r.voice_reference=lambda _:(_ for _ in ()).throw(ValueError('Original voice was deleted'))
    assert r.resolve(meta(7),[],anonymous=current)['state']=='UNKNOWN'
    s.delete(current['cluster_id'])
    assert r.resolve(meta(7),[],anonymous=current)['state']=='UNKNOWN'

def test_forged_stable_alias_cannot_promote_a_single_private_observation(tmp_path):
    r,s,a,_=fixture_registry(tmp_path);attempt=start_confirm(r,a);activate(r,attempt);r.anonymous_evidence=s.evidence
    r.voice_reference=lambda identity:dict(identity_id=identity,store_id='voice-store',model_id='fake-voice',revision=1,source_kind='actual',template_fingerprint='a'*64)
    forged=s.observe(meta(7),(1,0,0),voiced_ms=3000);forged.update(state='STABLE_CANDIDATE',distinct_captures=3)
    assert r.resolve(meta(7),[],anonymous=forged)['state']=='UNKNOWN'

def test_uncalibrated_original_voice_has_three_capture_candidate_after_boot_change(tmp_path):
    from tools.provisional_voice import query_reply
    r,s,_,clock=fixture_registry(tmp_path,alias=False);device=SpeakerDevice(Encoder(),tmp_path/'speaker.sqlite')
    device.store.enroll('voice-identity','小明',(1,0,0),consent=True,expected_revision=0)
    fingerprint=hashlib.sha256(device.store.db.execute('SELECT embedding FROM templates').fetchone()[0].encode()).hexdigest()
    attempt=start_confirm(r);r.accept_receipt(attempt,meta(2),receipt(r,attempt,'face'))
    r.accept_receipt(attempt,meta(6),receipt(r,attempt,'voice',fingerprint=fingerprint))
    analyzer=ProgressiveSpeakerAnalyzer(device,s,enabled=True,quality=quality)
    for i in (10,11,12):
        owner=meta(i,board_boot_id='after-restart')
        voice,alias=analyzer.analyze(owner,pcm(i))
        p=analyzer.provisional.proof(owner,store_id='voice-store')
        result=r.resolve(owner,[p] if p else [])
        assert voice['state']=='NOT_CALIBRATED' and voice['candidate_id'] is None
        if i<12:assert result['state']=='UNKNOWN'
    assert result['state']=='PROVISIONAL_NAME_CANDIDATE' and result['name']=='小明' and device.encoder.calls==3
    assert query_reply('今天吃什么',result) is None
    assert '可能' in query_reply('我是谁',result) and '不能确认身份' in query_reply('我是谁',result)
    assert result['personal_memory_allowed'] is False and device.calibrated is False

def test_provisional_voice_replayed_pcm_does_not_strengthen_candidate(tmp_path):
    from tools.provisional_voice import ProvisionalVoiceMatcher
    device=SpeakerDevice(Encoder(),tmp_path/'speaker.sqlite');device.store.enroll('voice-id','小明',(1,0,0),consent=True,expected_revision=0)
    matcher=ProvisionalVoiceMatcher(device)
    for i in (1,2,3):
        owner=meta(1,request_id='different-'+str(i),capture_id='capture-'+str(i),generation=i)
        assert matcher.observe(owner,(1,0,0)) is None

def test_uncalibrated_voice_conflicts_with_different_fresh_face(tmp_path):
    r,s,a,_=fixture_registry(tmp_path);attempt=start_confirm(r,a);activate(r,attempt)
    owner=meta(10);other=r.start(owner,'记住我，我叫李雷',visual=visual(owner),face_gallery=FACE,voice_gallery=VOICE)['attempt_id']
    r.confirm(other,meta(11),'确认登记',visual(meta(11)))
    r.accept_receipt(other,meta(11),receipt(r,other,'face',identity='face-other',commit=meta(11)))
    r.accept_receipt(other,meta(12),receipt(r,other,'voice',identity='voice-other',commit=meta(12)))
    p=proof(meta(13),'voice',identity='voice-other',calibrated=False);p.update(match_state='PROVISIONAL_NAME_CANDIDATE',consecutive_distinct=3)
    result=r.resolve(meta(13),[proof(meta(13),'face'),p])
    assert result['state']=='CONFLICT' and result['name'] is None and not result['personal_memory_allowed']

def test_v3_identity_evidence_persists_with_strict_owner_and_no_profile(tmp_path):
    from common.timeline_conversations import TimelineConversationStore
    r,s,a,_=fixture_registry(tmp_path/'identity');attempt=start_confirm(r,a);activate(r,attempt);owner=meta(7);cid='a'*32
    p=proof(owner,'voice',calibrated=False);p.update(match_state='PROVISIONAL_NAME_CANDIDATE',consecutive_distinct=3)
    result=r.resolve(owner,[p]);evidence=record(owner,cid,status='COMPLETE',identity=result)
    assert evidence['version']==3 and evidence['identity']['state']=='PROVISIONAL_NAME_CANDIDATE'
    store=TimelineConversationStore(tmp_path/'conversation.sqlite');store.begin(cid,owner,'public','public');store.attribution_pending(owner,cid)
    assert store.attribution_merge(owner,cid,evidence) and store.attribution_for_turn(owner,cid)['identity']['name']=='小明'
    with pytest.raises(ValueError):validate_record(evidence,meta(8),cid)
    evidence['identity']['personal_memory_allowed']=True
    with pytest.raises(ValueError):validate_record(evidence,owner,cid)

def test_hub_emits_v3_provisional_link_without_calibrating_or_second_encoder(tmp_path):
    import threading,time
    from concurrent.futures import ThreadPoolExecutor
    from tools.speaker_turns import SpeakerTurns
    from tools.private_gallery_reference import private_gallery_reference
    r,s,a,clock=fixture_registry(tmp_path/'identity');attempt=start_confirm(r,a)
    encoder=Encoder()
    with ThreadPoolExecutor(max_workers=1) as pool:
        device=pool.submit(SpeakerDevice,encoder,tmp_path/'s.sqlite').result()
        pool.submit(lambda:device.store.enroll('voice-identity','小明',(1,0,0),consent=True,expected_revision=0)).result()
        reference=lambda identity:private_gallery_reference(tmp_path/'s.sqlite','fake-voice',3,identity_id=identity,expected_application_id=device.store.APPLICATION_ID)
        gallery=reference('voice-identity')
        # Use actual synthetic store metadata in the signed original receipt.
        with r._db(write=True) as db:db.execute('UPDATE binding_attempts SET voice_gallery=? WHERE attempt_id=?',(json.dumps({k:gallery[k] for k in ('store_id','model_id')}|{'revision':0}),attempt))
        r.accept_receipt(attempt,meta(2),receipt(r,attempt,'face'))
        r.accept_receipt(attempt,meta(6),receipt(r,attempt,'voice',fingerprint=gallery['template_fingerprint']))
        hub=SimpleNamespace(speaker=device,speaker_pool=pool,speaker_gate=threading.Lock(),identity_links=r,voice_reference=reference,
          progressive_speaker=ProgressiveSpeakerAnalyzer(device,s,enabled=True,quality=quality))
        service=SpeakerTurns(hub)
        for i in (10,11,12):
            service.submit(meta(i),pcm(i),'a'*32)
            until=time.monotonic()+2
            while time.monotonic()<until:
                result=service.result(meta(i),'a'*32)
                if result['status']!='PENDING':break
                time.sleep(.005)
            assert result['status']=='COMPLETE' and result['version']==3
        assert result['identity']['state']=='PROVISIONAL_NAME_CANDIDATE' and result['identity']['name']=='小明'
        assert result['voice']['state']=='NOT_CALIBRATED' and encoder.calls==3 and not device.calibrated

def test_receipt_current_capture_and_integral_protocol_versions_are_strict(tmp_path):
    r,s,a,_=fixture_registry(tmp_path);attempt=start_confirm(r,a)
    with pytest.raises(ValueError,match='another capture'):r.accept_receipt(attempt,meta(3),receipt(r,attempt,'face'))
    for version in (2.,3.):
        value=record(meta(1),'a'*32,status='COMPLETE',anonymous=a)
        if version==3.:value=record(meta(1),'a'*32,status='COMPLETE',anonymous=a,identity=r.resolve(meta(1),[]))
        value['version']=version
        with pytest.raises(ValueError):validate_record(value,meta(1),'a'*32)
