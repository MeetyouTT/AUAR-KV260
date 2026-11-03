"""Synthetic PCM/fake encoder, real local enrollment and registry protocols.

No microphone, real biometric database, GPU, network or model is accessed.
"""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import sqlite3
import threading
import time

import pytest

from board.runtime.board_speaker_business import (BoardSpeakerBusiness, SpeakerNotReady,
    inspect_speaker_snapshot, migrate_speaker_snapshots)
from common.speaker_visual import unavailable
from tools.enrollment_receipts import existing_face_payload


MODEL = 'ecapa-voxceleb-' + 'a'*64
BOOT = 'public-synthetic-boot'
CID = 'b'*32


class Encoder:
    model_id = MODEL
    dimension = 192
    def __init__(self, vectors=None, hook=None):
        self.calls = 0; self.vectors = vectors; self.hook = hook
    def encode(self, pcm):
        self.calls += 1
        if self.hook:
            self.hook(self.calls)
        return self.vectors[self.calls-1] if self.vectors else [1.,0.] + [0.]*190


def quality(pcm):
    return pcm,{'vad_speech_seconds':3.}


def capture(n, *, boot=BOOT, pcm=None):
    pcm = pcm or int(n).to_bytes(2,'little')*48000
    return dict(protocol='aura-asr-1',board_boot_id=boot,session_id='public-session',request_id='request-'+str(n),
                generation=n,capture_id='capture-'+str(n),sample_count=len(pcm)//2,
                pcm_sha256=hashlib.sha256(pcm).hexdigest(),budget_ms=10000),pcm


def create(root, *, encoder=None, enabled=True, boot=BOOT):
    encoder = encoder or Encoder()
    return BoardSpeakerBusiness.create(root,encoder_factory=lambda:encoder,board_boot_id=boot,
        quality=quality,expected_model_id=MODEL,anonymous_config={'enabled':enabled},
        wall_clock=lambda:1000.,data_origin='synthetic'),encoder


def call(service,n,text,*,pcm=None):
    meta,raw = capture(n,boot=service.boot,pcm=pcm)
    return service.turn(meta,text,raw)


def count_people(service):
    return service.pool.submit(lambda:len(service.hub.speaker.store.people())).result(timeout=1.)


def enroll(service, *, start=1, name='小林'):
    assert '分三次' in call(service,start,'登记我的声纹，我叫'+name)
    assert '再说一句' in call(service,start+1,'我今天看了书')
    assert '再说一句' in call(service,start+2,'我正在准备午饭')
    assert '确认保存声纹' in call(service,start+3,'我晚上准备散步')
    assert count_people(service) == 0
    assert '不会据此自动打开私人记忆' in call(service,start+4,'确认保存声纹')


def test_constructor_is_inert_without_explicit_create_and_original_quality(tmp_path):
    root = tmp_path/'not-created'
    with pytest.raises(ValueError,match='Explicit'):
        BoardSpeakerBusiness(root,encoder_factory=Encoder,board_boot_id=BOOT)
    assert not root.exists()
    with pytest.raises(SpeakerNotReady):
        BoardSpeakerBusiness.create(root,encoder_factory=Encoder,board_boot_id=BOOT,
                                    quality=None,wall_clock=time.time)
    assert not root.exists()


def test_three_distinct_samples_require_final_consent_and_keep_calibration_false(tmp_path):
    service,encoder = create(tmp_path/'synthetic-private')
    try:
        enroll(service)
        assert count_people(service) == 1 and encoder.calls == 3
        assert not service.public()['speaker_calibrated']
        assert service.health()['profile_grants_issued'] is False
        # A second attempted name cannot silently replace the existing template.
        call(service,10,'登记我的声纹，我叫小明')
        for n in (11,12,13):
            call(service,n,'另一句不同的合成测试')
        assert '过于接近' in call(service,14,'确认保存声纹')
        assert count_people(service) == 1
    finally:
        assert service.close()


@pytest.mark.parametrize('mode',['cancel','replay','inconsistent'])
def test_cancel_replay_and_three_sample_failure_never_save(tmp_path,mode):
    a = [1.,0.]+[0.]*190; b = [0.,1.]+[0.]*190
    service,encoder = create(tmp_path/('synthetic-'+mode),encoder=Encoder(vectors=[a,a,b] if mode=='inconsistent' else None))
    try:
        call(service,1,'登记我的声纹，我叫小林')
        call(service,2,'第一段合成语音')
        if mode == 'cancel':
            assert '取消' in call(service,3,'取消登记')
        elif mode == 'replay':
            _,old = capture(2)
            assert '已经用过' in call(service,3,'不同文本不能把同PCM当不同样本',pcm=old)
            assert encoder.calls == 1
            call(service,4,'取消')
        else:
            call(service,3,'第二段合成语音')
            assert '不够一致' in call(service,4,'第三段合成语音')
        assert count_people(service) == 0 and not service.public()['active']
    finally:
        assert service.close()


def test_stale_owner_and_reused_capture_context_are_rejected(tmp_path):
    service,_ = create(tmp_path/'synthetic-ownership')
    try:
        meta,pcm = capture(2)
        service.turn(meta,'登记我的声纹，我叫小林',pcm)
        with pytest.raises(ValueError,match='Stale'):
            call(service,1,'取消')
        changed = dict(meta,capture_id='different')
        with pytest.raises(ValueError,match='Stale'):
            service.turn(changed,'取消',pcm)
        assert count_people(service) == 0
    finally:
        assert service.close()


def test_anonymous_three_distinct_captures_never_identify_or_grant_profile(tmp_path):
    service,_ = create(tmp_path/'synthetic-anonymous')
    try:
        results = []
        for n in (1,2,3):
            meta,pcm = capture(n)
            results.append(service.analyze(meta,pcm,conversation_id=CID))
        assert [row['anonymous']['state'] for row in results] == ['PROVISIONAL','PROVISIONAL','STABLE_CANDIDATE']
        assert len({row['anonymous']['code'] for row in results}) == 1
        assert all(row['identity']['state'] == 'UNKNOWN' and row['voice']['state'] == 'NOT_CALIBRATED' for row in results)
        assert all(row['personal_memory_allowed'] is False and row['anonymous']['identity_verified'] is False for row in results)
        meta,pcm = capture(4,pcm=capture(3)[1])
        repeated = service.analyze(meta,pcm,conversation_id=CID)
        assert repeated['anonymous']['distinct_captures'] == 3
        assert not list((tmp_path/'synthetic-anonymous').glob('*.wav'))
    finally:
        assert service.close()


def test_cancel_during_native_embedding_never_commits_anonymous_anchor(tmp_path):
    entered = threading.Event(); release = threading.Event()
    def hook(_):
        entered.set(); assert release.wait(2.)
    service,_ = create(tmp_path/'synthetic-cancel',encoder=Encoder(hook=hook))
    try:
        meta,pcm = capture(1)
        assert service.submit_analysis(meta,pcm,CID)['status'] == 'PENDING'
        assert entered.wait(1.)
        assert service.cancel_analysis(meta,CID)['status'] == 'CANCELLED'
        assert service.close(timeout=.01) is False  # Native call still owns its local argument/lease.
        release.set()
        assert service.close(timeout=2.)
        with sqlite3.connect(tmp_path/'synthetic-cancel/anonymous-voices.sqlite3') as db:
            assert db.execute('SELECT count(*) FROM anonymous_anchors').fetchone()[0] == 0
    finally:
        release.set(); service.close()


def visual(meta):
    return dict(version=1,context=meta,source_kind='actual',state='FACE_AT_CAPTURE_BOUNDARIES',
        reason='NOT_ACTIVE_SPEAKER_PROOF',evidence=dict(service_epoch='public-service',camera_epoch='public-camera',
        target=dict(camera_epoch='public-camera',track_id=1,track_generation=1),gallery_revision=7,face_identity_id='public-face',
        boundary_start_ms=1000,boundary_end_ms=1100,checked_ms=1200,source_start_ms=990,source_end_ms=1090,frame_start=1,frame_end=2))


def packet(meta):
    return dict(version=1,context=meta,gallery=dict(store_id='gallery-'+'f'*32,model_id='public-face-model',revision=7,source_kind='actual'),
                current=dict(identity_id='public-face',template_fingerprint='b'*64),inventory=[['public-face','b'*64]])


def route(service,n,text):
    meta,pcm = capture(n,boot=service.boot)
    return meta,pcm,service.route(meta,text,pcm,visual=visual(meta),gallery_packet=packet(meta))


class ExistingFaceBridge:
    def __init__(self):
        self.original_snapshot = lambda:None
    def exchange(self,meta,request,capture_snapshot,text,is_current):
        class Exchange:
            def receipt(self,value,snapshot):
                gallery = packet(meta)['gallery'].copy(); gallery.pop('source_kind')
                identity = dict(state='KNOWN',person_id='public-face',display_name='小林',db_version=7,
                                people=[dict(person_id='public-face',display_name='小林')])
                return existing_face_payload(attempt_id=request['attempt_id'],origin=request['origin_context'],commit=meta,
                    face_guard=request['face_guard'],gallery=gallery,name='小林',identity=identity,
                    confirmed_link=True,template_fingerprint='b'*64)
        return Exchange()
    @contextmanager
    def scope(self,exchange):
        yield exchange


def bind_existing_face_and_voice(service):
    _,_,start = route(service,1,'记住我，我叫小林')
    assert start['decision']['route'] == 'face_exchange'
    meta,pcm,confirm = route(service,2,'确认登记')
    assert confirm['binding_request']['confirmed_existing'] is True
    handle = service.begin_face_exchange(meta,pcm,confirm,ExistingFaceBridge(),{},'确认登记')
    assert len(handle.token) == 48  # Original binding_api.token, not a new protocol.
    with handle.scope():
        reply = handle.transform(dict(code='already_known',name=''))
    assert '接下来继续登记声纹' in reply and handle.pcm is None
    for n in (3,4,5):
        _,_,routed = route(service,n,'不同的合成声音句子')
        assert routed['decision']['route'] == 'device_reply'
    assert count_people(service) == 0
    _,_,saved = route(service,6,'确认保存身份关联')
    assert saved['decision']['unified_saved'] is True
    assert saved['decision']['personal_memory_allowed'] is False
    assert count_people(service) == 1


def test_original_binding_receipts_activate_only_after_face_and_three_voice_commits(tmp_path):
    service,_ = create(tmp_path/'synthetic-binding')
    try:
        bind_existing_face_and_voice(service)
        assert service.pool.submit(lambda:service.hub.binding.registry.health()['active_people']).result(timeout=1.) == 1
        assert not service.public()['speaker_calibrated']
    finally:
        assert service.close()


def test_readonly_snapshot_gates_and_namespace_preserving_private_migration(tmp_path):
    source = tmp_path/'synthetic-source'; target = tmp_path/'synthetic-target'
    service,_ = create(source)
    bind_existing_face_and_voice(service)
    assert service.close()
    names = ('speakers.sqlite3','anonymous-voices.sqlite3','identity-links.sqlite3','identity-link-receipt.key')
    expected = {name:hashlib.sha256((source/name).read_bytes()).hexdigest() for name in names}
    before = {name:(source/name).read_bytes() for name in names}
    with pytest.raises(ValueError,match='single-writer'):
        migrate_speaker_snapshots(source,target,expected_sha256=expected,expected_model_id=MODEL,data_origin='synthetic')
    imported = migrate_speaker_snapshots(source,target,expected_sha256=expected,expected_model_id=MODEL,
                                         data_origin='synthetic',single_writer_stopped=True)
    assert imported['active_namespace_preserved'] and imported['original_receipt_key_preserved']
    assert {name:(source/name).read_bytes() for name in names} == before
    assert {name:(target/name).read_bytes() for name in names} == before
    report = json.dumps(imported)
    assert '小林' not in report and 'public-face' not in report and 'store_id' not in report
    moved,_ = create(target,boot='new-public-boot')
    try:
        assert moved.pool.submit(lambda:moved.hub.binding.registry.health()['active_people']).result(timeout=1.) == 1
        with pytest.raises(OSError):
            migrate_speaker_snapshots(source,target,expected_sha256=expected,expected_model_id=MODEL,
                data_origin='synthetic',single_writer_stopped=True)
    finally:
        assert moved.close()
    assert migrate_speaker_snapshots(source,target,expected_sha256=expected,expected_model_id=MODEL,
        data_origin='synthetic',single_writer_stopped=True)['idempotent']


def test_foreign_schema_marker_is_rejected_without_mutation(tmp_path):
    path = tmp_path/'foreign.sqlite3'
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE turns(body TEXT)')
    before = path.read_bytes()
    with pytest.raises(ValueError,match='marker'):
        inspect_speaker_snapshot(path,'speakers.sqlite3',model_id=MODEL)
    assert path.read_bytes() == before


def test_owned_databases_cannot_be_reopened_under_other_model_or_origin(tmp_path):
    root = tmp_path/'synthetic-owned'
    service,_ = create(root); assert service.close()
    changed = Encoder(); changed.model_id = 'ecapa-voxceleb-'+'c'*64
    with pytest.raises(ValueError,match='model'):
        BoardSpeakerBusiness.create(root,encoder_factory=lambda:changed,board_boot_id=BOOT,quality=quality,
             anonymous_config={'enabled':True},wall_clock=lambda:1000.,data_origin='synthetic')


def test_anonymous_disabled_keeps_ordinary_voice_processing_unavailable_without_encoder(tmp_path):
    service,encoder = create(tmp_path/'synthetic-disabled',enabled=False)
    try:
        assert call(service,1,'普通聊天，不需要登记') is None
        meta,pcm = capture(2)
        result = service.analyze(meta,pcm,conversation_id=CID)
        assert result['voice']['state'] == 'NOT_CALIBRATED' and 'anonymous' not in result
        assert encoder.calls == 0
    finally:
        assert service.close()
    assert not service.health()['ready']


def test_cancel_during_enrollment_embedding_releases_unconfirmed_workflow(tmp_path):
    stop = threading.Event()
    service,_ = create(tmp_path/'synthetic-control-cancel',encoder=Encoder(hook=lambda _:stop.set()))
    try:
        call(service,1,'登记我的声纹，我叫小林')
        meta,pcm = capture(2)
        with pytest.raises(InterruptedError):
            service.turn(meta,'第一段样本',pcm,cancel_event=stop)
        service.pool.submit(lambda:None).result(timeout=1.)
        assert not service.public()['active'] and count_people(service) == 0
    finally:
        assert service.close()


def test_gallery_revision_change_rejects_late_enrollment_confirmation(tmp_path):
    service,_ = create(tmp_path/'synthetic-revision')
    try:
        call(service,1,'登记我的声纹，我叫小林')
        for n in (2,3,4):
            call(service,n,'合成不同样本')
        meta,pcm = capture(1)
        meta = dict(meta,session_id='another-public-session')
        service._call(lambda raw:service.hub.speaker.store.enroll('other','小明',[0.,1.]+[0.]*190,
                       consent=True,expected_revision=0),meta,pcm)
        with pytest.raises(ValueError,match='版本'):
            call(service,5,'确认保存声纹')
        assert count_people(service) == 1
    finally:
        assert service.close()


def test_explicit_policy_cannot_lower_operating_floors_or_assert_calibration(tmp_path):
    for index,calibration in enumerate(({'threshold':.79},{'margin':.09},{'consistency':.59},{'field_calibrated':True})):
        root = tmp_path/('synthetic-invalid-policy-'+str(index))
        with pytest.raises(ValueError,match='uncalibrated'):
            BoardSpeakerBusiness.create(root,encoder_factory=Encoder,board_boot_id=BOOT,quality=quality,
                 wall_clock=lambda:1000.,calibration=calibration,data_origin='synthetic')
        assert not root.exists()
