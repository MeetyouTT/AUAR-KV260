import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

HERE = Path(__file__).resolve().parent
MIRROR = HERE.parent / 'mirror_current_reference_20261027'
sys.path.insert(0, str(HERE))
import board.motion
for name in ('vsrv_driver', 'vsrv_transport'):
    spec = importlib.util.spec_from_file_location('board.motion.' + name, HERE.parent / 'offline_host_driver' / (name + '.py'))
    module = importlib.util.module_from_spec(spec);sys.modules[spec.name] = module;spec.loader.exec_module(module)
    setattr(board.motion, name, module)
from board.motion import manual_vsrv as manual
from board.motion.current_reference_release import qualified_reference_stop, STATUS, SCOPE

sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


class CurrentReferenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        remote = json.loads((MIRROR / 'qualification/remote_paths.json').read_text())
        self.q = {}
        for key, name in (('reference','reference.json'),('control_report','control_report.json'),('observer_report','observer_report.json')):
            shutil.copyfile(MIRROR / 'qualification' / name, self.root / name)
            self.q[key] = dict(file=name, sha256=sha(self.root / name))
        self.q['control_report']['source_path'] = remote['control_report']
        self.ref = json.loads((self.root / 'reference.json').read_text())
        self.fixed = json.loads((self.root / 'control_report.json').read_text())['result']['stopped_readback']
        self.config = dict(boot_id=self.ref['boot_id'],fdt_sha256=self.ref['fdt_sha256'], enabled=True,
                           manual_minimum_us=1400,manual_maximum_us=1600,maximum_step_us=20,maximum_duration_s=2)
        self.release = dict(schema_version=1,abi=2,build_id=0x778d2512,app=manual.APP,status=STATUS,scope=SCOPE,
                            boot_id=self.ref['boot_id'],manual_motion_enabled=False,physical_range_verified=False,
                            mechanical_reference_calibrated=False,external_waveform_verified=False,
                            manual_minimum_us=1400,manual_maximum_us=1600,qualification=self.q,
                            payload_files={'libvsrv.so':'fixture'},runtime_files={})

    def qualify(self): return qualified_reference_stop(self.release,self.config,self.root)

    def change(self, key, mutate):
        path=self.root/self.q[key]['file'];value=json.loads(path.read_text());mutate(value)
        path.write_text(json.dumps(value));self.q[key]['sha256']=sha(path)

    def backend(self, release=None):
        value=manual.ManualVSRV(self.config)
        value.release_root=self.root;value.release=self.release if release is None else release
        value.verify_platform=Mock()
        return value

    def enter(self, state, *, face_receipt=False, release=None):
        value=self.backend(release);io=Mock();driver=Mock();driver.status.return_value=copy.deepcopy(state)
        with patch.object(manual,'NativeRegisters',return_value=io),patch.object(manual,'VSRVDriver',return_value=driver),\
             patch('board.motion.follow_readback.verified_stopped_face_command',return_value=face_receipt) as checked:
            value.__enter__()
        return value,io,driver,checked

    def test_actual_qualification_passes_without_claiming_human_angle_or_waveform(self):
        self.assertEqual(self.qualify(),self.fixed)
        self.assertFalse(self.release['external_waveform_verified'])
        self.assertFalse(self.release['mechanical_reference_calibrated'])

    def test_wrong_boot_fdt_and_scope_are_rejected(self):
        for key,val in (('boot_id','wrong-boot'),('fdt_sha256','wrong-fdt'),('maximum_step_us',21)):
            old=self.config[key];self.config[key]=val
            with self.assertRaises(RuntimeError):self.qualify()
            self.config[key]=old
        self.release['scope']='finite_manual_only'
        with self.assertRaises(RuntimeError):self.qualify()

    def test_changed_file_hash_and_symlink_are_rejected(self):
        path=self.root/'observer_report.json';path.write_text(path.read_text()+' ')
        with self.assertRaisesRegex(RuntimeError,'HASH'):self.qualify()
        self.q['observer_report']['sha256']=sha(path)
        renamed=self.root/'preserved.json';path.rename(renamed);path.symlink_to(renamed)
        with self.assertRaisesRegex(RuntimeError,'REGULAR'):self.qualify()

    def test_fake_camera_summary_without_numeric_motion_is_rejected(self):
        def mutate(value):
            for row in value['samples']:
                if row.get('state')=='MEASURED_BACKGROUND_SHIFT':row['dx_px']=0.
            value['maximum_abs_dx_px']=0.
        self.change('observer_report',mutate)
        with self.assertRaisesRegex(RuntimeError,'ACTUAL_BACKGROUND_SHIFT'):self.qualify()

    def test_wrong_run_and_weak_background_quality_are_rejected(self):
        self.change('observer_report',lambda o:o.update(control_report_path='/different-run'))
        with self.assertRaisesRegex(RuntimeError,'BOUND'):self.qualify()
        self.change('observer_report',lambda o:o.update(control_report_path=self.q['control_report']['source_path']))
        def weaken(o):
            next(r for r in o['samples'] if r.get('state')=='MEASURED_BACKGROUND_SHIFT')['inliers']=3
        self.change('observer_report',weaken)
        with self.assertRaisesRegex(RuntimeError,'QUALITY'):self.qualify()

    def test_wrong_fixed_stop_and_incomplete_command_trace_are_rejected(self):
        self.change('control_report',lambda r:r['result']['stopped_readback'].update(ack_seq=183))
        with self.assertRaises(RuntimeError):self.qualify()

    def test_exact_fixed_stop_connects_with_no_arm_or_commit(self):
        value,io,driver,checked=self.enter(self.fixed)
        self.assertFalse(value.stopped_face_resume);checked.assert_not_called();io.write.assert_not_called()
        driver.confirm_and_arm.assert_not_called();driver.submit.assert_not_called()

    def test_in_range_pulse_or_changed_epoch_does_not_make_connection_ready(self):
        for changed in (dict(width_us=1500,target_us=1500),dict(epoch=self.fixed['epoch']+1)):
            state=dict(self.fixed,**changed)
            with self.assertRaisesRegex(RuntimeError,'STOP'):
                self.enter(state)

    def test_later_stop_requires_existing_verified_face_receipt(self):
        state=dict(self.fixed,width_us=1450,target_us=1450,epoch=self.fixed['epoch']+1,ack_seq=12)
        value,io,driver,checked=self.enter(state,face_receipt=True)
        self.assertTrue(value.stopped_face_resume);checked.assert_called_once_with(self.config,state)
        io.write.assert_not_called()

    def test_no_jog_before_move_begin_or_commit_even_if_called_directly(self):
        value=self.backend();value.io=Mock();value.driver=Mock()
        for action in (lambda:value.before_move(),lambda:value.begin(self.fixed),lambda:value.commit(1421)):
            with self.assertRaises(ValueError):action()
        value.verify_platform.assert_not_called();value.io.write.assert_not_called();value.driver.status.assert_not_called()

    def test_connection_finish_only_uses_stop(self):
        value=self.backend();value.driver=Mock();value.driver.stop.return_value=self.fixed
        self.assertEqual(value.finish(),self.fixed);value.driver.stop.assert_called_once();value.driver.finish.assert_not_called()

    def test_legacy_range_based_connection_is_unchanged(self):
        state=dict(self.fixed,width_us=1500,target_us=1500)
        value,io,driver,checked=self.enter(state,release={'status':'QUALIFIED_VSRV2','scope':'legacy','payload_files':{'libvsrv.so':'fixture'},'runtime_files':{}})
        self.assertFalse(value.stopped_face_resume);checked.assert_not_called();io.write.assert_not_called()

    def test_legacy_finish_still_quiesces_and_legacy_before_move_keeps_camera_guard(self):
        value=self.backend({'status':'QUALIFIED_VSRV2','scope':'legacy'});value.driver=Mock();value.driver.finish.return_value=self.fixed
        self.assertEqual(value.finish(),self.fixed);value.driver.finish.assert_called_once();value.driver.stop.assert_not_called()
        with patch.object(manual.urllib.request,'build_opener',side_effect=OSError('camera guard reached')):
            with self.assertRaises(OSError):value.before_move()
        value.verify_platform.assert_called_once()

    def test_legacy_release_and_live_config_modules_are_byte_identical_to_mirror(self):
        for name in ('manual_release.py','manual_live_config.py','follow_readback.py'):
            self.assertEqual(sha(HERE/'board/motion'/name),sha(MIRROR/'board/motion'/name))


if __name__=='__main__':unittest.main()
