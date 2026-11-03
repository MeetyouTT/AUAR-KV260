"""Independent release/restore checks using temporary files and fake services.

Never calls real systemctl, UART, model runtimes, audio or production storage.
"""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import control
import handoff
import live_checks


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def healthy():
    return {'camera_error':'', 'detector_error':'', 'identity_backend':'DPU_SFACE_INT8',
        'identity_ready':True, 'identity_error':'', 'observation_age_ms':100,
        'feature_inference':{'kind':'DPU_SFACE_INT8', 'ready':True},
        'feature_status':{'ready':True},
        'face_targets':{'ready':True, 'error':'', 'source_age_ms':100,
            'backend':'DPU_YUNET_INT8', 'worker_alive':True, 'fault_latched':False,
            'worker_faults':0, 'inference':{'fallback_calls':0},
            'freshness_metrics':{'counters':{'observed_gap_intervals':0,'process_errors':0}}},
        'dpu_schedule':{'optional':{'yunet':{'disabled':False,'overruns':0},
                                  'sface':{'disabled':False,'overruns':0}},
            'yunet_recovery':{'phase':'RUNNING','faults':0,'attempts':0,'recoveries':0},
            'diagnostic_failures':0, 'diagnostic_snapshot_atomic_with_schedule':False,
            'owner_fenced':False,
            'optional_diagnostics':{'fault_events':[]}}}


def latched_parent():
    h=healthy()
    h['face_targets']['backend']='CPU_YUNET_FALLBACK_AFTER_DPU_OVERRUN'
    h['dpu_schedule']['optional']['yunet'].update(disabled=True,overruns=3)
    h['dpu_schedule']['yunet_recovery'].update(phase='LATCHED',faults=3,attempts=2,recoveries=2)
    h['dpu_schedule']['optional_diagnostics']['fault_events']=[
        {'native_completed':1,'native_status':0,'body_failed':0,'guard_exceeded':int(i==2)} for i in range(3)]
    return h


class ValidatorTests(unittest.TestCase):
    def test_loaded_sface_without_current_target_needs_no_submitted_job_row(self):
        state=healthy()
        state['dpu_schedule']['optional'].pop('sface')
        state['feature_inference']['completed']=0
        live_checks.validate_candidate_state(state)
        control.check_candidate(state)
        state['feature_inference']['ready']=False
        with self.assertRaises(AssertionError):live_checks.validate_candidate_state(state)

    def test_parent_sface_completed_fault_can_be_restarted_but_not_accepted_as_candidate(self):
        state=healthy();state['dpu_schedule']['optional']['sface'].update(disabled=True,overruns=1)
        event={'task_code':2,'native_completed':1,'native_status':0,'body_failed':0}
        state['dpu_schedule']['optional_diagnostics']['fault_events']=[event]
        live_checks.validate_parent_state(state)
        with self.assertRaises(AssertionError):live_checks.validate_candidate_state(state)
        event['native_status']=-1
        with self.assertRaises(AssertionError):live_checks.validate_parent_state(state)

    def test_recorded_parent_completed_guard_fault_is_allowed_only_as_parent(self):
        state=latched_parent()
        live_checks.validate_parent_state(state)
        with self.assertRaises(AssertionError):live_checks.validate_candidate_state(state)

    def test_unknown_parent_completion_is_not_authorized_for_transition(self):
        for key,value in (('native_status',-1),('native_completed',0),('body_failed',1)):
            with self.subTest(key=key):
                state=latched_parent();state['dpu_schedule']['optional_diagnostics']['fault_events'][-1][key]=value
                with self.assertRaises(AssertionError):live_checks.validate_parent_state(state)

    def test_parent_fault_counts_must_match_preserved_three_fault_record(self):
        state=latched_parent();state['dpu_schedule']['yunet_recovery']['faults']=4
        with self.assertRaises(AssertionError):live_checks.validate_parent_state(state)

    def test_candidate_cannot_accept_a_recovered_post_observation_fault(self):
        state=healthy();state['dpu_schedule']['optional']['yunet']['overruns']=1
        state['dpu_schedule']['yunet_recovery'].update(faults=1,attempts=1,recoveries=1)
        live_checks.validate_parent_state(state)
        with self.assertRaises(AssertionError):live_checks.validate_candidate_state(state)

    def test_candidate_rejects_worker_failure_and_backend_unavailability(self):
        for change in ('worker','sface','fallback','diagnostics'):
            with self.subTest(change=change):
                state=healthy()
                if change=='worker':state['face_targets']['worker_alive']=False
                elif change=='sface':state['feature_inference']['ready']=False
                elif change=='fallback':state['face_targets']['inference']['fallback_calls']=1
                else:state['dpu_schedule']['diagnostic_failures']=1
                with self.assertRaises(AssertionError):live_checks.validate_candidate_state(state)

    def test_candidate_does_not_require_diagnostic_subsnapshot_count_equality(self):
        state=healthy();state['dpu_schedule']['optional']['yunet']['calls']=10
        state['dpu_schedule']['optional_diagnostics']['counters']={'yunet':{'native_completed':9}}
        live_checks.validate_candidate_state(state)


class TransitionTests(unittest.TestCase):
    def fake(self, fail=None):
        calls=[]
        class Ops:
            def ready(self,target):calls.append('ready:'+target);return False
            def __getattr__(self,name):
                def record(*args):
                    calls.append(name+(':'+args[0] if args and isinstance(args[0],str) else ''))
                    if fail==name:raise RuntimeError('synthetic transition failure')
                return record
        return Ops(),calls

    def test_restore_guard_and_pcm_quiescence_precede_both_components(self):
        ops,calls=self.fake();handoff.transition(ops,'candidate')
        self.assertLess(calls.index('assert_guard_armed'),calls.index('stop_audio'))
        self.assertLess(calls.index('wait_pcm_closed'),calls.index('switch_gui:candidate'))
        self.assertLess(calls.index('switch_gui:candidate'),calls.index('switch_camera:candidate'))
        self.assertLess(calls.index('wait_camera:candidate'),calls.index('start_audio'))
        self.assertLess(calls.index('restore_preference'),calls.index('start_audio'))

    def test_failed_pcm_close_does_not_switch_camera_or_gui(self):
        ops,calls=self.fake('wait_pcm_closed')
        with self.assertRaises(RuntimeError):handoff.transition(ops,'candidate')
        self.assertFalse(any(name.startswith('switch_') for name in calls))
        self.assertNotIn('start_audio',calls)

    def test_guard_arm_uses_sealed_restore_entry_not_launcher(self):
        ops=handoff.BoardOps.__new__(handoff.BoardOps)
        ops.meta={'restore_entry':'/synthetic/restore_previous.py','wrapper':'/synthetic/controller.py',
                  'guard':'synthetic-guard','guard_armed':False}
        ops.verify=Mock();ops.save_meta=Mock();ops.assert_guard_armed=Mock()
        ops.m=SimpleNamespace(command=Mock())
        ops.arm()
        args=ops.m.command.call_args[0][0]
        self.assertEqual(args[-2:],['/synthetic/restore_previous.py','--guard'])
        self.assertIn('--on-active=600s',args)
        self.assertNotIn('/synthetic/controller.py',args)
        self.assertTrue(ops.meta['guard_armed'])


class DropinOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.drop=self.root/'drop';self.drop.mkdir()
        self.old=self.drop/'old.conf';self.old.write_text('old')
        self.own=self.drop/'own.conf'
        self.unit=self.root/'camera.service';self.unit.write_text('unit')
        self.wrapper=self.root/'wrapper.py';self.wrapper.write_text('wrapper')
        self.pref=self.root/'preference.json';self.pref.write_text('preference')
        self.boot=self.root/'boot';self.boot.write_text(handoff.BOOT)
        self.ops=handoff.BoardOps.__new__(handoff.BoardOps)
        self.ops.meta={'boot':handoff.BOOT,'protected':{str(self.old):digest(self.old)},
            'unit_hashes':{'original':digest(self.unit)},'wrapper':str(self.wrapper),
            'wrapper_sha256':digest(self.wrapper),'xserver_pid':123,
            'allowed_preference_hashes':[digest(self.pref)],'gui_dropin_paths':[str(self.old)],
            'gui_override':str(self.own),'gui_override_sha256':hashlib.sha256(b'owned').hexdigest()}
        self.ops.m=SimpleNamespace(UNIT=self.unit);self.ops.pid=Mock(return_value=123)
        self.ops.active=Mock(return_value=True)
        actual=Path
        def paths(value):
            if str(value)=='/proc/sys/kernel/random/boot_id':return self.boot
            if str(value)=='/etc/systemd/system/aura-avatar-ui.service.d':return self.drop
            return actual(value)
        self.addCleanup(patch.stopall)
        patch.object(handoff,'Path',side_effect=paths).start()
        patch.object(handoff,'PREF',self.pref).start()

    def test_original_and_owned_dropin_sets_are_valid(self):
        self.ops.verify();self.own.write_text('owned');self.ops.verify()

    def test_foreign_new_dropin_blocks_transition(self):
        (self.drop/'foreign.conf').write_text('foreign')
        with self.assertRaisesRegex(AssertionError,'drop-in set'):self.ops.verify()

    def test_mutating_original_dropin_blocks_transition(self):
        self.old.write_text('changed')
        with self.assertRaisesRegex(AssertionError,'Protected file'):self.ops.verify()

    def test_mutating_owned_dropin_blocks_removal(self):
        self.own.write_text('changed')
        with self.assertRaisesRegex(AssertionError,'Owned GUI'):self.ops.verify()

    def test_owned_symlink_is_refused(self):
        target=self.root/'target';target.write_text('owned');self.own.symlink_to(target)
        with self.assertRaises(AssertionError):self.ops.verify()


class GuiMutationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.session=self.root/'session';self.session.mkdir()
        self.drop=self.root/'drop';self.drop.mkdir()
        self.old=self.drop/'old.conf';self.old.write_text('original')
        self.own=self.drop/'own.conf';self.source=self.session/'gui.candidate.conf';self.source.write_text('candidate')
        self.ops=handoff.BoardOps.__new__(handoff.BoardOps);self.ops.folder=self.session
        self.ops.meta={'gui_override':str(self.own),'gui_override_sha256':digest(self.source)}
        self.ops.verify=Mock();self.ops.active=Mock(return_value=False);self.ops.service=Mock()
        self.ops.m=SimpleNamespace(atomic=lambda path,data:Path(path).write_bytes(data))

    def test_restore_removes_only_the_owned_override(self):
        self.own.write_bytes(self.source.read_bytes());self.ops.switch_gui('original')
        self.assertFalse(self.own.exists());self.assertEqual(self.old.read_text(),'original')
        self.ops.service.assert_called_once_with('daemon-reload')

    def test_modified_override_is_never_deleted(self):
        self.own.write_text('foreign replacement')
        with self.assertRaises(AssertionError):self.ops.switch_gui('original')
        self.assertEqual(self.own.read_text(),'foreign replacement')

    def test_active_gui_prevents_override_change(self):
        self.ops.active.return_value=True
        with self.assertRaises(AssertionError):self.ops.switch_gui('candidate')
        self.assertFalse(self.own.exists())

    def test_candidate_install_is_idempotent_and_exact(self):
        self.ops.switch_gui('candidate');self.ops.switch_gui('candidate')
        self.assertEqual(self.own.read_bytes(),self.source.read_bytes())
        self.ops.service.assert_called_once_with('daemon-reload')


class GuiCloneTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.runtime=self.root/'old-runtime';self.runtime.mkdir()
        (self.runtime/'aura/board/identity').mkdir(parents=True)
        self.query=self.runtime/'aura/board/identity/spoken_query.py';self.query.write_text('VALUE = "old"\n')
        (self.runtime/'aura/other.py').write_text('OTHER = 1\n')
        assets=self.root/'static-assets';assets.mkdir();(assets/'static.txt').write_text('static')
        (self.runtime/'aura/assets').symlink_to(assets,target_is_directory=True)
        (self.runtime/'deliverables').symlink_to(assets,target_is_directory=True)
        (self.runtime/'avatar_user_settings.json').write_text('{"volume":7}')
        (self.runtime/'managed-runs').mkdir();(self.runtime/'launch.json').write_text('private-launch')
        self.startup=self.root/'old-startup';self.startup.mkdir()
        (self.startup/'launcher.py').write_text('pass\n')
        self.cfg=self.startup/'config.json'
        self.config={'runtime':str(self.runtime),'display_recovery_marker':'existing-marker',
                     'component_sha256':{'other.py':digest(self.runtime/'aura/other.py')}}
        self.cfg.write_text(json.dumps(self.config))
        self.candidate=self.root/'new-query.py';self.candidate.write_text('VALUE = "new"\n')
        self.release=self.root/'release';self.release.mkdir()

    def patches(self):
        return (patch.object(control,'GUI_RUNTIME',self.runtime),
                patch.object(control,'GUI_QUERY_SHA',digest(self.query)),patch.object(handoff,'CFG',self.cfg),
                patch.object(control.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout='',stderr='')))

    def test_gui_clones_only_python_delta_preserving_resources_and_settings(self):
        a,b,c,d=self.patches()
        with a,b,c,d:
            runtime,startup,before,after=control.clone_gui(self.release,self.candidate)
        self.assertEqual([key for key in before if before[key]!=after[key]],['board/identity/spoken_query.py'])
        self.assertFalse((runtime/'aura/board/identity/spoken_query.py').is_symlink())
        self.assertEqual(self.query.read_text(),'VALUE = "old"\n')
        self.assertTrue((runtime/'aura/assets').is_symlink())
        self.assertTrue((runtime/'deliverables').is_symlink())
        self.assertFalse((runtime/'avatar_user_settings.json').is_symlink())
        self.assertEqual((runtime/'avatar_user_settings.json').read_bytes(),(self.runtime/'avatar_user_settings.json').read_bytes())
        self.assertFalse((runtime/'managed-runs').exists());self.assertFalse((runtime/'launch.json').exists())
        updated=json.loads((startup/'config.json').read_text())
        self.assertEqual(updated['display_recovery_marker'],self.config['display_recovery_marker'])
        self.assertEqual(updated['component_sha256']['other.py'],self.config['component_sha256']['other.py'])
        self.assertEqual(updated['component_sha256']['board/identity/spoken_query.py'],digest(self.candidate))
        self.assertEqual(json.loads(self.cfg.read_text()),self.config)

    def test_gui_clone_rejects_source_drift_before_copy_or_preflight(self):
        with patch.object(control,'GUI_RUNTIME',self.runtime),patch.object(control,'GUI_QUERY_SHA','0'*64),\
             patch.object(control.subprocess,'run') as command:
            with self.assertRaises(AssertionError):control.clone_gui(self.release,self.candidate)
        command.assert_not_called()
        self.assertEqual(self.query.read_text(),'VALUE = "old"\n')

    def test_gui_clone_never_reuses_old_stage_log_pointer(self):
        old_session=self.runtime/'managed-runs/old-session';old_session.mkdir()
        old_log=old_session/'stage.log';old_log.write_text('synthetic log')
        (self.runtime/'stage.log').symlink_to(old_log)
        a,b,c,d=self.patches()
        with a,b,c,d:
            runtime,_,_,_=control.clone_gui(self.release,self.candidate)
        self.assertFalse((runtime/'stage.log').is_symlink())
        self.assertFalse((runtime/'stage.log').exists())
        self.assertTrue((self.runtime/'stage.log').is_symlink())

    def test_gui_preflight_failure_has_no_system_service_side_effects(self):
        a,b,c,_=self.patches()
        with a,b,c,patch.object(control.subprocess,'run',return_value=SimpleNamespace(returncode=1,stdout='',stderr='fixture-rejection')) as command:
            with self.assertRaisesRegex(AssertionError,'fixture-rejection'):
                control.clone_gui(self.release,self.candidate)
        args=command.call_args[0][0]
        self.assertEqual(args[-1],'--preflight');self.assertNotIn('systemctl',args)
        self.assertEqual(json.loads(self.cfg.read_text()),self.config)


class ObservationFinalizeTests(unittest.TestCase):
    def state(self,*,after=False,primary=1):
        h=healthy();h.update(pid=100,capture_frames=100+(10 if after else 0),
                            detected_frames=100+(10 if after else 0))
        h['face_targets']['processed']=100+(4 if after else 0)
        h['feature_inference']['completed']=20+(5 if after else 0)
        h['dpu_schedule']['primary_period_overruns']=primary
        h['dpu_schedule']['optional']['yunet']['calls']=100+(100 if after else 0)
        h['dpu_schedule']['optional_diagnostics']['counters']={'yunet':{'native_completed':100+(100 if after else 0)}}
        return h

    def ops(self,final_primary):
        camera=Mock(side_effect=[self.state(),self.state(),self.state(after=True,primary=final_primary)])
        return SimpleNamespace(m=SimpleNamespace(camera=camera,cpu=lambda:0,cpu_delta=lambda *a:{},
                               audio_warnings=lambda *a:0),pid=lambda *a:200,verify=lambda:None,
                               meta={'quiescent_cursor':'fixture'},ready=lambda *a:True)

    def test_final_snapshot_primary_fault_is_rejected_after_last_sample_passed(self):
        report={}
        with patch.object(control.time,'monotonic',side_effect=[100.,100.1,101.]):
            with self.assertRaises(AssertionError):control.observe(self.ops(2),report,lambda:None,duration=0)
        self.assertEqual(report['observation']['initial_primary_period_overruns'],1)
        self.assertNotIn('passed',report['observation'])

    def test_success_uses_native_completed_delta_and_retains_primary_baseline(self):
        report={}
        with patch.object(control.time,'monotonic',side_effect=[100.,100.1,101.]):
            control.observe(self.ops(1),report,lambda:None,duration=0)
        self.assertEqual(report['observation']['initial_primary_period_overruns'],1)
        self.assertEqual(report['observation']['native_yunet_completed'],100)
        self.assertTrue(report['observation']['passed'])


if __name__=='__main__':unittest.main()
