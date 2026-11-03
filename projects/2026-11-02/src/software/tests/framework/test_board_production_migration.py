"""Whole source/target migration fixtures only; no real DB, hardware or model."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import threading
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from common.board_memory import BoardMemoryStore
from common.board_memory_migration import migrate_legacy_snapshot, LegacyMigrationRejected
from common.board_observation_migration import migrate_observation_snapshot, TOPIC
from common import board_production_bootstrap as bootstrap
from common.timeline_observations import TimelineObservationStore
from common.timeline_conversations import TimelineConversationStore
from common.speaker_identity import SpeakerStore
from tools.speaker_device import SpeakerDevice
from common.anonymous_voice import AnonymousVoiceStore
from common.identity_links import IdentityLinkRegistry, ReceiptAuthority
from board.runtime.board_speaker_business import migrate_speaker_snapshots, inspect_speaker_snapshot
from board.runtime.visual_policy import LocalVisualQueries
from board.runtime.board_dialogue import BoardDialogueController
from common.model_inference_wire import Owner,audio_payload,make_response
from tools import board_production_import as importer

CID='a'*32
MODEL='ecapa-voxceleb-'+'b'*64


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def observation_fixture(path):
    clock=[1000.]
    old=TimelineObservationStore(path,device_id='public-camera',clock=lambda:clock[0])
    for frame,stamp,text in ((1,1000.,'相机观察到两个人。'),(2,1010.,'相机观察到两个人。'),
                             (3,1050.,'相机未观察到行人。')):
        clock[0]=stamp
        old.add(dict(board_boot_id='public-boot',camera_epoch='public-epoch',frame_id=frame),text,stamp)
    with old.db:
        old.db.execute("INSERT INTO observations(boot,epoch,frame,received,summary) VALUES('old-public-boot','old-public-epoch',9,900.,'相机观察到一把椅子。')")
        reference=old.db.execute('SELECT id FROM visual_timeline LIMIT 1').fetchone()[0]
        old.db.execute('INSERT INTO timeline_digests VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
            ('v:public-camera','public-digest','day','1970-01-01',0.,86400.,1000.,1050.,'可重建的公开摘录',json.dumps([reference]),2,0,None,1100.))
    old.close()


def conversation_fixture(path):
    source=TimelineConversationStore(path)
    meta=dict(request_id='public-request',generation=1,board_boot_id='public-boot',session_id='public-session')
    with patch('time.time',return_value=1000.):
        source.begin(CID,meta,'公开合成历史，尚未购买3本书。','公开合成历史，尚未购买3本书。')
        source.attach_sources(meta,[],mark_complete=True)
        source.generated(meta,'公开合成回答。',240,hashlib.sha256(b'pcm').hexdigest())
    with patch('time.time',return_value=1002.):source.played(meta,240,hashlib.sha256(b'pcm').hexdigest())


def schema(path):
    with sqlite3.connect(path) as db:return db.execute('SELECT type,name,sql FROM sqlite_master ORDER BY type,name').fetchall()


class PublicTTS:
    def __init__(self):self.calls=[]
    def request(self,kind,payload,**kwargs):
        assert kind=='tts'
        self.calls.append(payload)
        return make_response(Owner.from_dict(payload),result={'audio':audio_payload(b'\x01\x00'*240)})
    def cancel(self,owner):pass


def actual_visual_query(store,text,*,generation=1):
    timeline=SimpleNamespace(event_time=store.clock,monotonic=lambda:50.)
    worker=SimpleNamespace(scope={'kind':'device','id':'board-camera'},store=store,timeline=timeline,
        collector=SimpleNamespace(allow_fixture=False),record_current_observation=lambda:None)
    client=PublicTTS();policy=LocalVisualQueries(store,worker,timeline)
    controller=BoardDialogueController(store,client,board_boot_id='public-boot',system_prompt='公开测试',clock=timeline.monotonic)
    job=SimpleNamespace(scope={'kind':'conversation','id':CID},deadline=60.,
        meta={'session_id':'public-query-session','generation':generation,'request_id':'public-query-'+str(generation)})
    plan=policy(text,job=job,controller=controller,is_current=lambda:True,cancel_event=threading.Event())
    assert controller.acknowledge(plan,playback_token=plan.playback_token,sha256=plan.sha256,samples=plan.samples,complete=True)
    return client,policy


def test_visual_import_deduplicates_cache_and_actual_query_is_historical_device_only(tmp_path):
    source=tmp_path/'source.sqlite3';observation_fixture(source)
    target=BoardMemoryStore(tmp_path/'target.sqlite3',clock=lambda:2000.)
    before=source.read_bytes()
    report=migrate_observation_snapshot(source,target,expected_sha256=sha(source),target_device_id='board-camera')
    assert source.read_bytes()==before
    assert report['source_cache_rows']==4 and report['source_timeline_rows']==2
    assert report['covered_cache_rows']==3 and report['uncovered_cache_rows']==1 and report['imported_visual_events']==3
    assert report['reconstructable_digest_rows']==1
    worker=type('Worker',(),{})();worker.scope={'kind':'device','id':'board-camera'};worker.store=target
    timeline=type('Clock',(),{})();timeline.event_time=target.clock;timeline.monotonic=lambda:50.;worker.timeline=timeline
    worker.collector=type('Collector',(),{'allow_fixture':False})()
    policy=LocalVisualQueries(target,worker,timeline)
    result=policy.legacy_history(start=800.,end=1200.)
    assert len(result['items'])==3 and result['current'] is False and result['legacy_visual_only']
    assert target.history({'kind':'conversation','id':CID})==[]
    assert all(r['source']=='camera_observed' for r in result['items'])
    assert any('尚未' not in r['text'] and '椅子' in r['text'] for r in result['items'])
    assert migrate_observation_snapshot(source,target,expected_sha256=sha(source),target_device_id='board-camera')['idempotent']


def test_unique_visual_or_conversation_digest_is_not_silently_dropped(tmp_path):
    observation=tmp_path/'visual.sqlite3';observation_fixture(observation)
    with sqlite3.connect(observation) as db:db.execute("UPDATE timeline_digests SET sources='[\"missing-private-source\"]'")
    target=BoardMemoryStore(tmp_path/'target.sqlite3')
    with pytest.raises(LegacyMigrationRejected,match='unique_visual_digest'):
        migrate_observation_snapshot(observation,target,expected_sha256=sha(observation),target_device_id='board-camera')
    conversation=tmp_path/'conversation.sqlite3';conversation_fixture(conversation)
    with sqlite3.connect(conversation) as db:
        db.execute('INSERT INTO timeline_digests VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
            ('c:'+CID,'orphan','day','1970-01-01',0,86400,1000,1002,'唯一旧摘要','[]',1,0,None,1100))
    with pytest.raises(LegacyMigrationRejected,match='unique_legacy_digest'):
        migrate_legacy_snapshot(conversation,target,expected_sha256=sha(conversation))
    assert target.health()['active_bodies']==0


def test_imported_old_vision_is_available_in_actual_special_route_but_not_current_or_private_input(tmp_path):
    source=tmp_path/'visual.sqlite3';observation_fixture(source)
    target=BoardMemoryStore(tmp_path/'target.sqlite3',clock=lambda:3000.)
    migrate_observation_snapshot(source,target,expected_sha256=sha(source),target_device_id='board-camera')
    client,policy=actual_visual_query(target,'历史画面里有多少人，私人尾句不能写设备库')
    assert policy.last_kind=='historical_person_count' and policy.last_status['legacy_visual_status']['returned_count']==3
    assert '3条旧视觉记录' in json.dumps(client.calls,ensure_ascii=False)
    assert '不代表当前画面' in json.dumps(client.calls,ensure_ascii=False)
    assert '私人尾句' not in json.dumps(target.history({'kind':'device','id':'board-camera'}),ensure_ascii=False)
    current,_=actual_visual_query(target,'现在镜头前有多少人',generation=2)
    assert '无法取得新鲜' in json.dumps(current.calls,ensure_ascii=False)
    assert '两个人' not in json.dumps(current.calls,ensure_ascii=False)
    legacy=policy.legacy_history()
    target.forget({'kind':'device','id':'board-camera'},event_ids=[r['event_id'] for r in legacy['items']],operation_id='forget-old-camera')
    after,_=actual_visual_query(target,'历史画面里有多少人',generation=3)
    assert '未检索到有效人数记录' in json.dumps(after.calls,ensure_ascii=False)
    assert policy.legacy_history()['items']==[]


@pytest.mark.parametrize('operation',['forget','correct'])
def test_visual_compaction_keeps_summary_after_body_cleanup_and_source_changes_invalidate_it(tmp_path,operation):
    source=tmp_path/'visual.sqlite3';observation_fixture(source)
    target=BoardMemoryStore(tmp_path/'target.sqlite3',clock=lambda:3000.)
    migrate_observation_snapshot(source,target,expected_sha256=sha(source),target_device_id='board-camera')
    scope={'kind':'device','id':'board-camera'}
    if operation=='correct':
        target.correct(scope,'旧视觉判断','公开来源记录',source_event_ids=[r['event_id'] for r in target.history(scope,topic=TOPIC)],operation_id='first-public-fact')
    task=target.prepare_compaction(max_events=2)
    assert task
    candidate=dict(schema_version=1,scope=task['scope'],topic=task['topic'],start_utc=task['start_utc'],end_utc=task['end_utc'],
        source_refs=[dict(event_id=r['event_id'],revision=r['revision']) for r in task['sources'] if r['include_in_summary']],
        summary='相机历史观察到一把椅子，以及两个人。',keywords=['相机','历史'],claims=task['required_claims'])
    saved=target.commit_compaction(task['task_id'],task['lease_token'],candidate)
    assert saved['committed']
    with sqlite3.connect(target.path) as db:
        assert db.execute('SELECT count(*) FROM bm_summaries WHERE summary_id=?',(saved['summary_id'],)).fetchone()[0]==1
        assert db.execute('SELECT count(*) FROM bm_bodies WHERE event_id IN (SELECT event_id FROM bm_summary_sources WHERE summary_id=?)',(saved['summary_id'],)).fetchone()[0]==0
    assert any(r.get('summary_id')==saved['summary_id'] for r in target.history(scope,topic=TOPIC))
    if operation=='forget':
        target.forget(scope,event_ids=[candidate['source_refs'][0]['event_id']],operation_id='forget-public-legacy')
    else:
        target.correct(scope,'旧视觉判断','撤销旧判断，人数尚未核实',operation_id='correct-public-legacy')
    assert not any(r.get('summary_id')==saved['summary_id'] for r in target.history(scope,topic=TOPIC))


def _fixture_private_file(root,relative):
    path=root/relative
    if not path.is_file() or root not in path.resolve().parents:
        raise ValueError('fixture_private_file_missing')
    return path


def test_bootstrap_reopens_original_stores_and_survives_new_writes_without_old_live_hash(tmp_path,monkeypatch):
    # Windows host validates real schema/rows/markers, not POSIX permission
    # branches. Production verifier still requires the actual POSIX private root.
    monkeypatch.setattr(bootstrap,'_private_root',lambda root:Path(root).resolve())
    monkeypatch.setattr(bootstrap,'_private_file',_fixture_private_file)
    root=tmp_path/'target';root.mkdir();src=tmp_path/'sources';src.mkdir()
    conversation_fixture(src/'conversations.sqlite3');observation_fixture(src/'observations.sqlite3')
    store=BoardMemoryStore(root/'timeline.sqlite3',clock=lambda:3000.,data_origin='board')
    convo=migrate_legacy_snapshot(src/'conversations.sqlite3',store,expected_sha256=sha(src/'conversations.sqlite3'),source_data_origin='board')
    visual=migrate_observation_snapshot(src/'observations.sqlite3',store,expected_sha256=sha(src/'observations.sqlite3'),
        target_device_id='board-camera',source_data_origin='board')
    speaker=SpeakerStore(src/'speakers.sqlite3',MODEL,192,.7,.1,create=True);speaker.close()
    anon=AnonymousVoiceStore(src/'anonymous-voices.sqlite3',MODEL,192)
    authority=ReceiptAuthority(b'p'*32)
    registry=IdentityLinkRegistry(src/'identity-links.sqlite3',authority)
    (src/'identity-link-receipt.key').write_bytes(b'p'*32)
    expected={n:sha(src/n) for n in ('speakers.sqlite3','anonymous-voices.sqlite3','identity-links.sqlite3','identity-link-receipt.key')}
    migrate_speaker_snapshots(src,root/'speaker',expected_sha256=expected,expected_model_id=MODEL,
        single_writer_stopped=True,data_origin='synthetic')
    owner=root/'speaker/speaker-business-owner.json';data=json.loads(owner.read_text());data['data_origin']='board';owner.write_text(json.dumps(data))
    (root/'conversation_selection.json').write_text(json.dumps(dict(version=1,conversation_id=CID)))
    sources=dict(conversation=sha(src/'conversations.sqlite3'),observation=sha(src/'observations.sqlite3'),
        speaker=expected['speakers.sqlite3'],anonymous_voice=expected['anonymous-voices.sqlite3'],identity_links=expected['identity-links.sqlite3'])
    sealed=bootstrap.seal_production_bootstrap(root,root/'production-bootstrap.json',bundle_id='d'*32,
        conversation_import={k:convo[k] for k in ('import_id','source_sha256')},
        observation_import={k:visual[k] for k in ('import_id','source_sha256')},source_sha256=sources,
        speaker_model_id=MODEL,single_writer_stopped=True)
    verify=lambda:bootstrap.verify_production_bootstrap(root,root/'production-bootstrap.json',sealed['receipt_sha256'])
    assert verify()['conversation_selection_verified']
    # Actual original constructors and original strict board snapshot inspector.
    reopened=SpeakerStore(root/'speaker/speakers.sqlite3',MODEL,192,.7,.1,create=False);reopened.close()
    encoder=type('Encoder',(),{'model_id':MODEL,'dimension':192})()
    device=SpeakerDevice(encoder,root/'speaker/speakers.sqlite3',quality=lambda pcm:(pcm,{}))
    assert device.calibrated is False
    device.store.close()
    AnonymousVoiceStore(root/'speaker/anonymous-voices.sqlite3',MODEL,192)
    IdentityLinkRegistry(root/'speaker/identity-links.sqlite3',authority)
    for name in ('speakers.sqlite3','anonymous-voices.sqlite3','identity-links.sqlite3'):
        inspect_speaker_snapshot(root/'speaker'/name,name,model_id=MODEL)
    reopened_timeline=BoardMemoryStore(root/'timeline.sqlite3',clock=lambda:4000.,data_origin='board')
    initial=sha(root/'timeline.sqlite3')
    reopened_timeline.append_event({'kind':'conversation','id':CID},'new-public-event','user_said','板端新增公开内容。')
    assert sha(root/'timeline.sqlite3')!=initial and verify()['receipt_verified']
    assert migrate_legacy_snapshot(src/'conversations.sqlite3',reopened_timeline,
        expected_sha256=sources['conversation'],source_data_origin='board')['idempotent']
    assert '板端新增公开内容。' in json.dumps(reopened_timeline.history({'kind':'conversation','id':CID}),ensure_ascii=False)
    new_cid='e'*32
    bootstrap.register_anonymous_conversation(reopened_timeline,new_cid)
    (root/'conversation_selection.json').write_text(json.dumps(dict(version=1,conversation_id=new_cid)))
    updated=verify()
    assert updated['conversation_selection_verified'] and updated['conversation_selection_sha256']==sha(root/'conversation_selection.json')
    (root/'speaker/speakers.sqlite3').unlink()
    with pytest.raises((ValueError,FileNotFoundError)):
        verify()


def test_explicit_snapshot_and_full_preflight_only_touch_public_fixture_sources(tmp_path,monkeypatch):
    entry=Path(__file__).resolve().parents[3]/'deliverables/2026-10-30_board_owner/integration/production_memory_handoff/snapshot_windows_private.py'
    spec=importlib.util.spec_from_file_location('synthetic_snapshot_helper',entry)
    helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
    src=tmp_path/'sources';src.mkdir();snapshot=tmp_path/'snapshot';snapshot.mkdir()
    conversation_fixture(src/'conversations.sqlite3');observation_fixture(src/'observations.sqlite3')
    speaker=SpeakerStore(src/'speakers.sqlite3',MODEL,192,.8,.1,create=True);speaker.close()
    AnonymousVoiceStore(src/'anonymous-voices.sqlite3',MODEL,192)
    IdentityLinkRegistry(src/'identity-links.sqlite3',ReceiptAuthority(b'p'*32))
    (snapshot/'identity-link-receipt.key').write_bytes(b'p'*32)
    entries={}
    import time
    for kind,name in importer.NAMES.items():
        before=(src/name).read_bytes()
        helper.backup(src/name,snapshot/name,time.monotonic()+5.)
        assert (src/name).read_bytes()==before and helper.source_info(src/name)==helper.source_info(snapshot/name)
        entries[kind]=dict(path=name,sha256=sha(snapshot/name),bytes=(snapshot/name).stat().st_size,**helper.source_info(snapshot/name))
    manifest=snapshot/'private-snapshot.json'
    manifest.write_text(json.dumps(dict(schema=importer.SCHEMA,bundle_id='d'*32,source_writers_stopped_attested=True,
        cross_store_barrier='publisher_confirmed_all_writers_stopped',databases=entries,
        receipt_key=dict(path='identity-link-receipt.key',sha256=sha(snapshot/'identity-link-receipt.key'),bytes=32))))
    monkeypatch.setattr(importer,'_private_root',lambda root:Path(root).resolve())
    monkeypatch.setattr(importer,'_private_file',_fixture_private_file)
    private,bundle=importer.source_bundle(manifest,sha(manifest))
    pins,reports=importer.preflight(private,bundle,MODEL,3000.)
    assert set(pins)==set(importer.NAMES) and reports['conversation']['turns']==1
    assert reports['observation']['imported_visual_events']==3
    with pytest.raises(ValueError,match='manifest_fingerprint'):
        importer.source_bundle(manifest,'0'*64)
    (snapshot/'anonymous-voices.sqlite3').unlink()
    with pytest.raises(ValueError,match='fixture_private_file_missing'):
        importer.source_bundle(manifest,sha(manifest))


def test_explicit_saved_selection_preserves_only_mapped_anonymous_scope_and_can_be_idempotent(tmp_path,monkeypatch):
    monkeypatch.setattr(bootstrap,'_private_root',lambda root:Path(root).resolve())
    monkeypatch.setattr(bootstrap,'_private_file',_fixture_private_file)
    source=tmp_path/'conversation.sqlite3';conversation_fixture(source)
    root=tmp_path/'target';root.mkdir()
    store=BoardMemoryStore(root/'timeline.sqlite3',clock=lambda:3000.,data_origin='board')
    report=migrate_legacy_snapshot(source,store,expected_sha256=sha(source),source_data_origin='board')
    selection=tmp_path/'private-selection.json'
    selection.write_text(json.dumps(dict(version=1,conversation_id=CID)))
    assert bootstrap.stage_initial_conversation_selection(store,root,selection,import_id=report['import_id'])['conversation_selection_verified']
    assert bootstrap.stage_initial_conversation_selection(store,root,selection,import_id=report['import_id'])['idempotent']
    selection.write_text(json.dumps(dict(version=1,conversation_id='f'*32)))
    with pytest.raises(ValueError,match='not_an_imported_anonymous_scope'):
        bootstrap.stage_initial_conversation_selection(store,root,selection,import_id=report['import_id'])


def test_explicit_import_creates_private_target_before_existing_only_writer_lock(tmp_path,monkeypatch):
    # Windows host exercises lifecycle and refuses dangerous parents; real
    # POSIX owner/mode checks remain unchanged and must pass on the board.
    target=tmp_path/'new-private-parent'/'target'
    monkeypatch.setattr(importer,'_canonical_import_target',lambda p:Path(p).resolve())
    monkeypatch.setattr(importer,'_existing_directory_mode',lambda p:0o700 if p.is_dir() else (_ for _ in ()).throw(ValueError('not_directory')))
    monkeypatch.setattr(importer,'_private_root',lambda p:Path(p).resolve(strict=True))
    assert not target.exists()
    importer.prepare_import_target(target)
    class ExistingOnlyWriterLock:
        def __init__(self,path):
            if not path.is_dir():raise ValueError('Migrate before factory construction')
    ExistingOnlyWriterLock(target)
    assert list(target.iterdir())==[]  # Directory creation is not empty-DB creation.
    rejected=tmp_path/'rejected-target'
    monkeypatch.setattr(importer,'_existing_directory_mode',lambda p:0o777)
    with pytest.raises(ValueError,match='import_parent_writable_by_others'):
        importer.prepare_import_target(rejected)
    assert not rejected.exists()


def test_snapshot_invalid_bundle_has_controlled_error_without_private_source_access():
    helper=Path(__file__).resolve().parents[3]/'deliverables/2026-10-30_board_owner/integration/production_memory_handoff/snapshot_windows_private.py'
    result=subprocess.run([sys.executable,'-B',str(helper),'--bundle-id','invalid'],
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=5,text=True)
    assert result.returncode==2 and not result.stderr
    assert json.loads(result.stdout)==dict(status='REJECTED',error_code='windows_private_snapshot_bounds_required')
