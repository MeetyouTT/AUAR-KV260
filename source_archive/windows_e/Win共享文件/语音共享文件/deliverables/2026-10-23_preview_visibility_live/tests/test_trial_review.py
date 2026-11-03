"""Independent local controller guards; mocked services and owned temp files."""
import ast
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('reviewed_gui_trial',ROOT/'gui_trial.py')
trial=importlib.util.module_from_spec(spec);spec.loader.exec_module(trial)


class TrialGuardTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory(prefix='aura-video-review-')
        self.addCleanup(self.temporary.cleanup);self.folder=Path(self.temporary.name)
        network=patch.object(trial,'get',side_effect=AssertionError('No network in review tests'))
        network.start();self.addCleanup(network.stop)

    def metadata(self):
        override=self.folder/'owned.conf';override.write_bytes(b'owned-gui-only-override')
        meta={'camera_pid':51,'override':str(override),'override_sha256':trial.sha(override),'gui_transition_started':True,
              'original_page':'vision','original_command':['/usr/bin/python3','-B','/original/launcher.py'],
              'original_execstart':'{ path=/usr/bin/python3; argv[]=/usr/bin/python3 -B /original/launcher.py; pid=101; start_time=old }'}
        (self.folder/'session.json').write_text(json.dumps(meta));return meta

    def restoration_mocks(self):
        return patch.multiple(trial,verify=Mock(),idle=Mock(return_value={}),stop_gui=Mock(),start_gui=Mock(),set_page=Mock(),
            command=Mock(return_value=''),prop=Mock(side_effect=lambda unit,key:'active' if key=='ActiveState' else '202'),
            gui_command=Mock(return_value=[b'/usr/bin/python3',b'-B',b'/original/launcher.py']))

    def test_same_original_argv_after_new_pid_is_successful_restore(self):
        meta=self.metadata()
        with self.restoration_mocks():result=trial.restore(self.folder)
        self.assertTrue(result['restored']);self.assertEqual(result['gui_pid'],202)
        self.assertFalse(Path(meta['override']).exists())

    def test_read_only_restore_check_does_not_stop_start_or_write_dropin(self):
        meta=self.metadata();original=(self.folder/'session.json').read_bytes()
        with self.restoration_mocks():
            result=trial.restore(self.folder,'check')
            trial.stop_gui.assert_not_called();trial.start_gui.assert_not_called();trial.command.assert_not_called()
        self.assertTrue(result['read_only']);self.assertTrue(Path(meta['override']).exists())
        self.assertEqual((self.folder/'session.json').read_bytes(),original)

    def test_accepted_ordinary_guard_does_not_undo_candidate(self):
        meta=self.metadata();(self.folder/'accepted.json').write_text('{"accepted":true}')
        with self.restoration_mocks():
            result=trial.restore(self.folder,'guard');trial.stop_gui.assert_not_called();trial.start_gui.assert_not_called()
        self.assertTrue(result['no_action']);self.assertTrue(Path(meta['override']).exists())

    def test_manual_restore_guard_still_restores_even_with_accepted_marker(self):
        meta=self.metadata();meta['manual_restore_in_progress']=True
        (self.folder/'session.json').write_text(json.dumps(meta));(self.folder/'accepted.json').write_text('{"accepted":true}')
        with self.restoration_mocks():
            result=trial.restore(self.folder,'guard');trial.stop_gui.assert_called_once();trial.start_gui.assert_called_once()
        self.assertTrue(result['restored']);self.assertFalse(Path(meta['override']).exists())

    def test_manual_restore_arms_independent_timer_before_gui_stop(self):
        self.metadata();order=[]
        with self.restoration_mocks(),patch.object(trial,'idle',return_value={}):
            def command(args,**_):
                if args[0]=='systemd-run':order.append('arm')
                self.assertNotIn(trial.CAMERA,args);return ''
            trial.command.side_effect=command;trial.stop_gui.side_effect=lambda *_:order.append('stop')
            trial.restore(self.folder,'manual')
        self.assertLess(order.index('arm'),order.index('stop'))

    def test_python_symlink_clone_cannot_change_original_source(self):
        base=self.folder/'base';(base/'aura/tools').mkdir(parents=True)
        original=self.folder/'original.py';original.write_bytes(b'ORIGINAL = True\n')
        (base/'aura/tools/target.py').symlink_to(original)
        startup=base.parent/'gui-startup';startup.mkdir();(startup/'launcher.py').write_text('# fake preflight\n')
        (startup/'config.json').write_text(json.dumps({'runtime':str(base),'component_sha256':{}}))
        folder=self.folder/'stage';(folder/'candidate/aura/tools').mkdir(parents=True)
        candidate=folder/'candidate/aura/tools/target.py';candidate.write_bytes(b'CANDIDATE = True\n')
        with patch.object(trial,'BASE',base),patch.object(trial.subprocess,'run',return_value=SimpleNamespace(returncode=0,stderr='',stdout='')):
            try:trial.clone(folder,{'tools/target.py':trial.sha(candidate)})
            except (AssertionError,ValueError):pass
        self.assertEqual(original.read_bytes(),b'ORIGINAL = True\n')

    def stop_preference(self,after):
        preference=self.folder/'preference.json';original=b'{"enabled": false}\n';preference.write_bytes(original)
        (self.folder/'preference.original').write_bytes(original)
        meta={'owned_starting':False,'allowed_preference_hashes':[trial.sha(preference)]}
        states=iter(['active','inactive'])
        def stop(args,**_):
            self.assertEqual(args,['systemctl','stop',trial.GUI]);preference.write_bytes(after);return ''
        patches=patch.multiple(trial,PREF=preference,verify=Mock(),idle=Mock(),pcm_closed=Mock(),
                               prop=Mock(side_effect=lambda *_:next(states)),command=Mock(side_effect=stop))
        return preference,meta,patches

    def test_stop_rejects_semantically_changed_user_preference_without_overwrite(self):
        changed=b'{"enabled": true}\n';preference,meta,mocks=self.stop_preference(changed)
        with mocks:
            with self.assertRaisesRegex(AssertionError,'Preference semantics changed'):trial.stop_gui(self.folder,meta)
        self.assertEqual(preference.read_bytes(),changed)
        self.assertNotIn(trial.sha(preference),meta['allowed_preference_hashes'])

    def test_stop_accepts_only_equivalent_json_canonicalization(self):
        equivalent=b'{\n  "enabled": false\n}\n';preference,meta,mocks=self.stop_preference(equivalent)
        with mocks:trial.stop_gui(self.folder,meta)
        self.assertIn(trial.sha(preference),meta['allowed_preference_hashes'])
        self.assertEqual(preference.read_bytes(),equivalent)

    def test_independent_guard_precedes_first_baseline_page_mutation(self):
        tree=ast.parse((ROOT/'gui_trial.py').read_text());run=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='run')
        measures=[n.lineno for n in ast.walk(run) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='measure']
        arms=[]
        for n in ast.walk(run):
            if (isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='command' and n.args
                    and isinstance(n.args[0],ast.List) and n.args[0].elts and isinstance(n.args[0].elts[0],ast.Constant)
                    and n.args[0].elts[0].value=='systemd-run'):arms.append(n.lineno)
        self.assertTrue(measures and arms);self.assertLess(min(arms),min(measures))


class PreservedCameraTests(unittest.TestCase):
    def completed_latch(self):
        return {'pid':499773,'worker_alive':True,'identity_ready':True,'owner_fenced':False,
            'worker_faults':0,'diagnostic_failures':0,'gaps':0,'process_errors':0,
            'feature_inference':{'ready':True},'primary_overruns':1,
            'face_backend':'CPU_YUNET_FALLBACK_AFTER_DPU_OVERRUN',
            'optional':{'yunet':{'disabled':True,'overruns':2},'sface':{'disabled':False,'overruns':0}},
            'recovery':{'phase':'LATCHED','reason':'unsafe_or_unknown_completion','faults':2},
            'fault_events':[{'event_sequence':sequence,'task_code':1,'native_attempts':1,
                'native_completed':1,'native_status':0,'native_failed':0,'body_failed':0,
                'hardcap_exceeded':1,'guard_exceeded':int(sequence==2)} for sequence in (1,2)]}

    def final_gate(self,before,after):
        trial.assert_camera_unchanged(before,after)

    def test_completed_guard_latch_is_allowed_without_changing_its_counters(self):
        state=self.completed_latch();before=copy.deepcopy(state)
        trial.validate_preserved_camera(state);self.final_gate(before,state)
        self.assertEqual(state,before)

    def test_unknown_or_uncompleted_native_and_fenced_owner_are_rejected(self):
        for key,value in (('native_completed',0),('native_status',-1),('native_status',None),
                          ('native_failed',1),('body_failed',1)):
            with self.subTest(key=key,value=value):
                state=self.completed_latch();state['fault_events'][-1][key]=value
                with self.assertRaises((AssertionError,KeyError)):trial.validate_preserved_camera(state)
        state=self.completed_latch();state['owner_fenced']=True
        with self.assertRaises(AssertionError):trial.validate_preserved_camera(state)

    def test_missing_zero_or_duplicate_fault_evidence_is_rejected(self):
        variants=[]
        missing_count=self.completed_latch();missing_count['optional']['yunet'].pop('overruns');variants.append(missing_count)
        zero=self.completed_latch();zero['optional']['yunet']['overruns']=0;zero['fault_events']=[];variants.append(zero)
        missing_event=self.completed_latch();missing_event['fault_events'].pop();variants.append(missing_event)
        duplicate=self.completed_latch();duplicate['fault_events'][1]['event_sequence']=1;variants.append(duplicate)
        for index,state in enumerate(variants):
            with self.subTest(index=index):
                with self.assertRaises((AssertionError,KeyError)):trial.validate_preserved_camera(state)

    def test_sface_disabled_or_unavailable_is_not_an_allowed_preserved_degradation(self):
        disabled=self.completed_latch();disabled['optional']['sface']['disabled']=True
        unavailable=self.completed_latch();unavailable['feature_inference']['ready']=False
        for state in (disabled,unavailable):
            with self.assertRaises(AssertionError):trial.validate_preserved_camera(state)

    def test_new_completed_fault_changed_backend_pid_or_cleared_counters_are_rejected(self):
        before=self.completed_latch();new=copy.deepcopy(before)
        new['optional']['yunet']['overruns']=3;new['recovery']['faults']=3
        new['fault_events'].append(dict(new['fault_events'][-1],event_sequence=3))
        changed_backend=copy.deepcopy(before);changed_backend['face_backend']='DPU_YUNET_INT8'
        changed_backend['optional']['yunet']['disabled']=False;changed_backend['recovery']['phase']='RUNNING'
        new_pid=copy.deepcopy(before);new_pid['pid']+=1
        cleared=copy.deepcopy(changed_backend);cleared['optional']['yunet']['overruns']=0;cleared['fault_events']=[]
        for label,after in (('new fault',new),('backend',changed_backend),('pid',new_pid),('counter reset',cleared)):
            with self.subTest(label=label):
                with self.assertRaises(AssertionError):self.final_gate(before,after)

    def test_existing_gap_one_is_allowed_only_when_preserved_unchanged(self):
        before=self.completed_latch();before['gaps']=1;after=copy.deepcopy(before)
        trial.validate_preserved_camera(before);self.final_gate(before,after)
        self.assertEqual(before,after)
        self.assertEqual(after['gaps'],1)

    def test_gap_one_to_two_or_zero_is_rejected(self):
        before=self.completed_latch();before['gaps']=1
        for count in (2,0):
            with self.subTest(after_gaps=count):
                after=copy.deepcopy(before);after['gaps']=count
                with self.assertRaisesRegex(AssertionError,'freshness gaps changed'):self.final_gate(before,after)


if __name__=='__main__':unittest.main(verbosity=2)
