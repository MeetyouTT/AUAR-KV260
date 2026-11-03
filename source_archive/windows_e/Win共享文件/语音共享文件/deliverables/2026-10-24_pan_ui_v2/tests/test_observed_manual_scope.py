import copy
import hashlib
import json
from pathlib import Path
import tempfile
import time
import unittest

from board.motion.manual_release import observed_bounds
from board.motion.manual import ManualPan
from test_manual_pan import Hardware,wait_for

ROOT=Path(__file__).resolve().parents[1]


class ObservedScopeTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.root=Path(self.directory.name)
        self.trial=json.loads((ROOT/'observed-trial.json').read_text())
        self.human=json.loads((ROOT/'human_observation.json').read_text())
        self.config={'boot_id':self.trial['boot_id'],'maximum_step_us':20,'maximum_duration_s':2,
            'manual_minimum_us':1425,'manual_maximum_us':1445}
        self.release={'status':'OBSERVED_MANUAL_VSRV2','scope':'finite_manual_only',
            'external_waveform_verified':False,'physical_servo_response_verified':True,
            'dpu_coexistence_verified':True,'automatic_following_enabled':False,
            'boot_id':self.trial['boot_id'],'manual_minimum_us':1425,'manual_maximum_us':1445}
        self.persist()

    def persist(self):
        p=self.root/'observed-trial.json';p.write_text(json.dumps(self.trial,indent=2)+'\n')
        self.release['trial_sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
        self.human['trial_sha256']=self.release['trial_sha256']
        p=self.root/'human-observation.json';p.write_text(json.dumps(self.human,ensure_ascii=False,indent=2)+'\n')
        self.release['observation_sha256']=hashlib.sha256(p.read_bytes()).hexdigest()

    def validate(self):return observed_bounds(self.release,self.config,self.root)

    def test_confirmed_manual_scope_preserves_unmeasured_waveform(self):
        self.assertEqual(self.validate(),(1425,1445))
        self.assertFalse(self.release['external_waveform_verified'])

    def test_false_claim_of_external_measurement_is_not_this_profile(self):
        self.release['external_waveform_verified']=True
        with self.assertRaises(RuntimeError):self.validate()

    def test_other_kernel_boot_is_rejected(self):
        self.config['boot_id']='another-boot'
        with self.assertRaises(RuntimeError):self.validate()

    def test_unconfirmed_observation_is_rejected(self):
        self.human['movement_and_return_stop_observed']=False;self.persist()
        with self.assertRaises(RuntimeError):self.validate()

    def test_changed_evidence_is_rejected(self):
        (self.root/'observed-trial.json').write_text('{}')
        with self.assertRaises(RuntimeError):self.validate()

    def test_expanded_hardware_range_is_rejected(self):
        self.release.update(manual_minimum_us=1400,manual_maximum_us=1600)
        with self.assertRaises(RuntimeError):self.validate()

    def test_expanded_local_configuration_is_rejected(self):
        self.config['manual_maximum_us']=1500
        with self.assertRaises(RuntimeError):self.validate()

    def test_no_return_to_origin_is_rejected(self):
        self.trial['result']['commanded_sequence_us'][-1]=1445;self.persist()
        with self.assertRaises(RuntimeError):self.validate()

    def test_active_final_output_is_rejected(self):
        self.trial['result']['stopped']['flags']=15;self.persist()
        with self.assertRaises(RuntimeError):self.validate()

    def test_automatic_following_is_not_enabled_by_observation(self):
        self.release['automatic_following_enabled']=True
        with self.assertRaises(RuntimeError):self.validate()


class NarrowManualTests(unittest.TestCase):
    def test_one_step_and_return_stay_inside_observed_bounds(self):
        hardware=Hardware(1425)
        pan=ManualPan(lambda:hardware,duration_s=.06,minimum_us=1425,maximum_us=1445)
        self.addCleanup(pan.close);wait_for(lambda:pan.read()['state']=='READY')
        with self.assertRaises(ValueError):pan.jog('left',20)
        pan.jog('right',20);wait_for(lambda:len(pan.read()['history'])==1)
        self.assertEqual(pan.read()['pulse_us'],1445)
        with self.assertRaises(ValueError):pan.jog('right',5)
        pan.jog('left',20);wait_for(lambda:len(pan.read()['history'])==2)
        self.assertEqual(pan.read()['pulse_us'],1425)
        self.assertEqual(pan.read()['minimum_us'],1425)
        self.assertEqual(pan.read()['maximum_us'],1445)

    def test_reset_1500_is_not_a_current_physical_reference(self):
        hardware=Hardware(1500)
        pan=ManualPan(lambda:hardware,minimum_us=1425,maximum_us=1445)
        self.addCleanup(pan.close);wait_for(lambda:pan.read()['state']=='FAULT')
        with self.assertRaises(ValueError):pan.jog('left',20)
        self.assertNotIn('begin',hardware.calls)


if __name__=='__main__':unittest.main()
