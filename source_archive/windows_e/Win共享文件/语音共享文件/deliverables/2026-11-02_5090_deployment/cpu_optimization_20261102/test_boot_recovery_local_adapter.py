"""Synthetic control-flow checks only; deliberately unusable Native evidence."""
import copy
import json
import unittest
from boot_recovery_local_adapter import RequiredMetadata, after_stop, plan_flow, propose_rebind


class FlowChecks(unittest.TestCase):
    def cold(self):
        return {'schema':'aura-boot-interface-observation-1','board_boot_id':'SYNTHETIC_NEW_KERNEL',
            'camera_running':False,'observation_provenance_required':True,
            'no_live_camera_owner_confirmed':True,'checkpoint_pin':'SYNTHETIC_NOT_A_REAL_PIN',
            'checkpoint_source_boot':'SYNTHETIC_OLD_KERNEL','allow_new_kernel_boot':True,
            'current_kernel_domain_consumed':False}

    def test_cold_skips_stop_and_same_boot_validator(self):
        result=plan_flow(self.cold());self.assertEqual(result['route'],'cold_no_camera_owner_new_kernel')
        self.assertNotIn('normal_stop_current_owner.explicit_stop_once',result['steps'])
        self.assertFalse(result['production_execution_allowed']);self.assertFalse(result['native_validation_passed'])

    def test_running_routes_through_original_stop(self):
        data=self.cold();data.update(camera_running=True,camera_owner='SYNTHETIC_OWNER')
        result=plan_flow(data);self.assertEqual(result['route'],'maintenance_running_camera')
        self.assertLess(result['steps'].index('normal_stop_current_owner.explicit_stop_once'),result['steps'].index('validate_fresh_final_history_readonly'))

    def test_consumed_kernel_is_not_reinitialized(self):
        data=self.cold();data['current_kernel_domain_consumed']=True
        with self.assertRaises(RequiredMetadata):plan_flow(data)

    def test_missing_seed_is_required(self):
        data=self.cold();del data['checkpoint_pin']
        with self.assertRaises(RequiredMetadata):plan_flow(data)

    def test_same_boot_requires_actual_stop_proof(self):
        data=self.cold();data['checkpoint_source_boot']=data['board_boot_id']
        with self.assertRaises(RequiredMetadata):plan_flow(data)

    def test_pending_stop_cannot_advance(self):
        with self.assertRaises(RequiredMetadata):after_stop({'status':'CAMERA_STOP_PENDING_NO_FORCE'})

    def rebind(self):
        before={'board_boot_id':'SYNTHETIC_OLD','camera_pid':1,'camera_start_ticks':'1',
            'camera_cmdline_sha256':'SYNTHETIC_NOT_A_SHA','camera_config':'/synthetic/old.json',
            'identity_config':'/synthetic/identity.json','model_policy':'KEEP',
            'source_sha256':{'/synthetic/old.json':'OLD','/synthetic/UI.py':'BEFORE'}}
        actual={'board_boot_id':'SYNTHETIC_NEW','camera_pid':2,'camera_start_ticks':'2',
            'camera_cmdline_sha256':'SYNTHETIC_NOT_A_SHA','camera_config':'/synthetic/new.json',
            'observation_provenance_pin':'SYNTHETIC_NOT_A_REAL_PIN'}
        observed={'/synthetic/old.json':'OLD','/synthetic/UI.py':'AFTER','/synthetic/new.json':'SYNTHETIC'}
        return before,actual,observed,{'/synthetic/UI.py':'AFTER'}

    def test_rebind_preserves_history_and_policy_without_approval_claim(self):
        before,actual,observed,delta=self.rebind();saved=copy.deepcopy(before)
        result=propose_rebind(before,actual,observed,delta)
        self.assertEqual(before,saved);self.assertEqual(result['source_count'],3)
        self.assertEqual(result['candidate']['model_policy'],'KEEP')
        self.assertIn('/synthetic/old.json',result['candidate']['source_sha256'])
        self.assertFalse(result['original_metadata_verify_passed']);self.assertFalse(result['production_apply_allowed'])

    def test_unapproved_change_and_missing_old_source_rejected(self):
        before,actual,observed,delta=self.rebind();observed['/synthetic/old.json']='UNAPPROVED'
        with self.assertRaises(RequiredMetadata):propose_rebind(before,actual,observed,delta)
        del observed['/synthetic/old.json']
        with self.assertRaises(RequiredMetadata):propose_rebind(before,actual,observed,delta)


if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(FlowChecks)
    result=unittest.TextTestRunner(verbosity=1).run(suite)
    print(json.dumps({'schema':'aura-boot-interface-local-control-flow-checks-1',
        'tests_run':result.testsRun,'passed':result.wasSuccessful(),'synthetic_only':True,
        'original_Native_validators_executed':False,'Native_proof_created':False,
        'board_or_model_access':False,'production_files_written':False}))
    raise SystemExit(0 if result.wasSuccessful() else 1)
