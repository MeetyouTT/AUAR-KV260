"""Synthetic production admission/appearance checks; no model/real DB/device."""
import ast
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import Mock,patch

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'candidate/aura'))
from board.runtime import board_business as business
from tools import production_board_business_gui as gui
from tools import production_business_ui as ui


def proof():
    return dict(data_origin='board',receipt_verified=True,bundle_id='bundle-public-fixture',profiles_migration_verified=True,
                profiles_imported=0,initial_retention_enabled=False)
def config():
    return business.BoardBusinessConfig(str(HERE.resolve()),(1793300000.,1793500000.),data_origin='board',
        bootstrap_receipt=str((HERE/'fixture-receipt.json').resolve()),bootstrap_receipt_sha256='a'*64)


class AdmissionTests(unittest.TestCase):
    def test_board_configuration_requires_explicit_receipt_and_real_origin(self):
        with self.assertRaises(ValueError):business.BoardBusinessConfig(str(HERE),(1.,2.),data_origin='board')
        self.assertFalse(config().retention_enabled)

    def test_production_precheck_precedes_writer_lock_and_store(self):
        events=[];verify=Mock(side_effect=lambda *a:(events.append('verify') or proof()))
        lease=SimpleNamespace(close=lambda:events.append('close'))
        def acquire(*args):events.append('lock');return lease
        def construct(*args,**kwargs):events.append('construct');self.assertEqual(kwargs['bootstrap_proof'],proof());return 'runtime'
        with patch.dict(sys.modules,{'common.board_production_bootstrap':SimpleNamespace(verify_production_bootstrap=verify)}), \
             patch.object(business,'_BoardWriterLock',side_effect=acquire),patch.object(business,'BoardBusinessRuntime',side_effect=construct):
            self.assertEqual(business.create_board_business_runtime(config(),'boot-fixture'),'runtime')
        self.assertEqual(events,['verify','lock','verify','construct'])

    def test_missing_receipt_never_opens_lock_or_constructs_store(self):
        module=SimpleNamespace(verify_production_bootstrap=Mock(side_effect=ValueError('receipt_missing')))
        with patch.dict(sys.modules,{'common.board_production_bootstrap':module}), \
             patch.object(business,'_BoardWriterLock') as lock,patch.object(business,'BoardBusinessRuntime') as ctor:
            with self.assertRaises(ValueError):business.create_board_business_runtime(config(),'boot-fixture')
        lock.assert_not_called();ctor.assert_not_called()

    def test_second_check_failure_releases_writer_without_store_creation(self):
        module=SimpleNamespace(verify_production_bootstrap=Mock(side_effect=[proof(),ValueError('receipt_changed')]))
        lease=SimpleNamespace(close=Mock())
        with patch.dict(sys.modules,{'common.board_production_bootstrap':module}), \
             patch.object(business,'_BoardWriterLock',return_value=lease),patch.object(business,'BoardBusinessRuntime') as ctor:
            with self.assertRaises(ValueError):business.create_board_business_runtime(config(),'boot-fixture')
        lease.close.assert_called_once_with();ctor.assert_not_called()

    def test_gui_rejects_before_asr_frontend_or_speaker_models(self):
        module=SimpleNamespace(verify_production_bootstrap=Mock(side_effect=ValueError('receipt_missing')))
        value=dict(enabled=True,private_root='/private/board',utc_bounds=[1.,2.],data_origin='board',
            asr_directory='/public/asr',frontend_directory='/public/frontend',feedback_manifest='/public/feedback',
            feedback_manifest_sha256='b'*64,bootstrap_receipt='/private/receipt',bootstrap_receipt_sha256='a'*64)
        with patch.dict(sys.modules,{'common.board_production_bootstrap':module}), \
             patch.object(gui,'load_private_face_readback') as face:
            with self.assertRaisesRegex(ValueError,'receipt_missing'):
                gui.ProductionGuiBoardBusiness(SimpleNamespace(),value,HERE)
        face.assert_not_called()

    def test_default_retention_starts_jobs_without_compaction(self):
        self.check_start(False)
    def test_explicit_retention_starts_existing_worker(self):
        self.check_start(True)
    def check_start(self,enabled):
        runtime=SimpleNamespace(closed=False,started=False,timeline=SimpleNamespace(event_time=lambda:1.),
            config=SimpleNamespace(data_origin='board',retention_enabled=enabled),speaker_business=object(),
            jobs=SimpleNamespace(start=Mock()),memory_worker=SimpleNamespace(start=Mock()),visual_memory=None)
        business.BoardBusinessRuntime.start(runtime)
        runtime.jobs.start.assert_called_once_with()
        self.assertEqual(runtime.memory_worker.start.call_count,int(enabled));self.assertTrue(runtime.started)

    def test_public_reports_real_writer_receipt_and_retention_without_ids(self):
        runtime=SimpleNamespace(config=SimpleNamespace(data_origin='board',retention_enabled=False),
            writer_lock=SimpleNamespace(fd=7),bootstrap_proof=proof(),boot_id='boot-fixture',started=True,closed=False,
            memory_worker=SimpleNamespace(health=lambda:{},thread=None),initial_selection={'mode':'saved_anonymous'},
            timeline=SimpleNamespace(quality_snapshot=lambda:{}),jobs=SimpleNamespace(public=lambda:{}),close_complete=False,
            visual_memory=None,visual_policy=None,speaker_business=SimpleNamespace(health=lambda:{'ready':True,'data_origin':'board'}),
            speaker_analysis_error='',clock_refresh_error='',_clock_refresh_next=10,clock=lambda:1)
        result=business.BoardBusinessRuntime.public(runtime)
        self.assertEqual(result['mode'],'board-business-board');self.assertTrue(result['production_cutover'])
        self.assertTrue(result['writer']['held']);self.assertTrue(result['receipt']['verified'])
        self.assertFalse(result['retention']['enabled']);self.assertFalse(result['retention']['running'])
        self.assertNotIn('profile_id',json.dumps(result))


class SelectionTests(unittest.TestCase):
    def test_new_anonymous_scope_is_registered_before_selection_file_is_published(self):
        from common.conversation_selection import ConversationSelection
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'selection.json';seen=[]
            def register(cid):
                self.assertFalse(path.exists());seen.append(cid)
            selected=ConversationSelection(path,before_publish=register)
            cid=selected.select(False)
            self.assertEqual(seen,[cid]);self.assertEqual(json.loads(path.read_bytes())['conversation_id'],cid)

    def test_failed_scope_registration_does_not_replace_existing_saved_reference(self):
        from common.conversation_selection import ConversationSelection
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'selection.json';raw=b'{"version":1,"conversation_id":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}'
            path.write_bytes(raw)
            def rejected(cid):raise PermissionError('not_anonymous')
            selected=ConversationSelection(path,before_publish=rejected)
            with self.assertRaises(PermissionError):selected.select(False)
            self.assertEqual(path.read_bytes(),raw)

    def test_saved_anonymous_reference_resumes_with_fresh_session_without_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'conversation_selection.json';raw=b'{"version":1,"conversation_id":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}'
            path.write_bytes(raw);runtime=SimpleNamespace(jobs=SimpleNamespace(conversation_selection=SimpleNamespace(path=path),
                select_conversation=Mock()),bootstrap_proof=dict(conversation_selection_verified=True,
                    conversation_selection_sha256=hashlib.sha256(raw).hexdigest()))
            gui.initialize_anonymous_selection(runtime,True)
            runtime.jobs.select_conversation.assert_called_once_with(resume=True)
            self.assertEqual(runtime.initial_selection['mode'],'saved_anonymous')
            self.assertFalse(runtime.initial_selection['profile_grant_imported'])

    def test_reference_change_never_silently_combines_or_selects_another_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'conversation_selection.json';path.write_bytes(b'{}')
            runtime=SimpleNamespace(jobs=SimpleNamespace(conversation_selection=SimpleNamespace(path=path),select_conversation=Mock()),
                bootstrap_proof=dict(conversation_selection_verified=True,conversation_selection_sha256='a'*64))
            with self.assertRaises(ValueError):gui.initialize_anonymous_selection(runtime,True)
            runtime.jobs.select_conversation.assert_not_called()

    def test_no_valid_saved_reference_creates_one_distinct_new_anonymous_scope(self):
        runtime=SimpleNamespace(jobs=SimpleNamespace(conversation_selection=None,select_conversation=Mock()),bootstrap_proof={})
        gui.initialize_anonymous_selection(runtime,True)
        runtime.jobs.select_conversation.assert_called_once_with(resume=False)
        self.assertEqual(runtime.initial_selection['mode'],'new_anonymous_no_saved_reference')


class AppearanceTests(unittest.TestCase):
    def source(self,relative):return (HERE/'candidate/aura'/relative).read_bytes()
    def test_latest_native_and_theme_are_byte_exact(self):
        for name in ('tools/libaura_yuki.so','tools/native_yuki.py','tools/formal_native_yuki.py','ui/ui_tokens.json'):
            with self.subTest(name=name):self.assertEqual(self.source(name),(HERE/'fresh/aura'/name).read_bytes())

    def test_current_css_window_and_full_423x516_geometry_are_preserved(self):
        from build_candidate import source_node
        source=self.source('tools/board_avatar_gtk.py').decode();fresh=(HERE/'fresh/aura/tools/board_avatar_gtk.py').read_text(encoding='utf8')
        self.assertEqual(source_node(source,'build_window','BoardAvatarStage'),source_node(fresh,'build_window','BoardAvatarStage'))
        self.assertIn("self.rect = dict(x=0, y=0, w=self.geometry['w'], h=self.geometry['h'])",source)
        self.assertIn("state['board_business']=self.board_business.runtime.public()",source)

    def test_profile_978b_and_formal_selected_identity_are_preserved(self):
        for name in ('config/character_profile.local.json','config/persona.xuefei.candidate.json','config/yuki_pair.formal.json','config/yuki_accepted_prompt.baseline.txt'):
            with self.subTest(name=name):self.assertEqual(self.source(name),(HERE/'fresh/aura'/name).read_bytes())
        text=self.source('tools/formal_yuki.py').decode();self.assertIn('production_selected=True',text)

    def test_raw_input_and_full_ack_integration_retains_frozen_audio_sources(self):
        base=HERE.parent/'resume_yuki_business_candidate_v2/candidate/aura'
        for name in ('tools/yuki_jobs_candidate.py','tools/streaming_controller.py','board/runtime/audio/board_pcm_queue.py',
                     'board/runtime/audio/board_capture.py','board/runtime/audio/board_gtcrn_fft.py','board/runtime/board_dialogue.py'):
            with self.subTest(name=name):self.assertEqual(self.source(name),(base/name).read_bytes())

    def test_every_candidate_python_file_parses_on39(self):
        for path in (HERE/'candidate/aura').rglob('*.py'):
            ast.parse(path.read_bytes(),feature_version=(3,9))


class BoardUiTests(unittest.TestCase):
    def test_legacy_connection_writes_are_refused_before_any_store_update(self):
        stage=SimpleNamespace(board_business=object(),transcription_store=SimpleNamespace(update=Mock()),
                              connection_store=SimpleNamespace(update=Mock()))
        for kind in ('asr_config','ui_edit','connection_apply','ui_service_config'):
            with self.subTest(kind=kind),self.assertRaises(ValueError):
                ui.guard_legacy_configuration(stage,{'type':kind,'values':{'port':8792}})
        stage.transcription_store.update.assert_not_called();stage.connection_store.update.assert_not_called()
        ui.guard_legacy_configuration(stage,{'type':'ui_refresh'})

    def test_board_model_labels_use_actual_new_job_not_old_service_preferences(self):
        stage=SimpleNamespace(board_business=SimpleNamespace(runtime=SimpleNamespace(config=
            SimpleNamespace(model_host='192.168.50.1',model_port=8797))),mode_label=Mock(),host_status_label=Mock(),
            host_entry=Mock(),port_entry=Mock(),controls={name:Mock() for name in ('edit_host','edit_port','connect','disconnect')},
            footer=Mock(),toast_until=0)
        state={'local_transcription':{'state':'ERROR','service':{'board_owned':True,'port':8797}},
               'ui_runtime':{'legacy_port':8792}}
        ui.project_business_ui(stage,state)
        label=stage.host_status_label.set_text.call_args.args[0]
        self.assertIn('8797',label);self.assertIn('失败',label);self.assertNotIn('8792',label)
        self.assertFalse(state['board_processing']['model_readiness_claimed'])
        self.assertFalse(state['board_processing']['legacy_business_ports_used'])
        for control in stage.controls.values():control.set_sensitive.assert_called_once_with(False)


if __name__=='__main__':unittest.main()
