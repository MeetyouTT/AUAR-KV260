import copy
import unittest
from unittest.mock import patch

import train_once_controller as controller


class GateTests(unittest.TestCase):
    def setUp(self):
        self.health=dict(pid=1291,native_critical=True,abi=2,owner_fenced=False,
            camera_error=False,worker_alive=True)
        self.display=dict(connector=dict(status='connected',enabled='enabled',dpms='On'))

    def test_ready_context(self):
        controller.validate_context('boot',1291,'boot',self.health,self.display)

    def test_stale_boot_is_rejected(self):
        with self.assertRaises(ValueError):
            controller.validate_context('old',1291,'new',self.health,self.display)

    def test_pid_is_checked(self):
        with self.assertRaises(ValueError):
            controller.validate_context('boot',2,'boot',self.health,self.display)

    def test_unavailable_business_is_rejected(self):
        for key,value in [('owner_fenced',True),('camera_error',True),('worker_alive',False),
                          ('native_critical',False),('abi',1)]:
            with self.subTest(key=key):
                changed=copy.deepcopy(self.health);changed[key]=value
                with self.assertRaises(ValueError):
                    controller.validate_context('boot',1291,'boot',changed,self.display)

    def test_inactive_connector_is_rejected_without_waking_it(self):
        for key,value in [('status','disconnected'),('enabled','disabled'),('dpms','Off')]:
            with self.subTest(key=key):
                changed=copy.deepcopy(self.display);changed['connector'][key]=value
                with self.assertRaises(ValueError):
                    controller.validate_context('boot',1291,'boot',self.health,changed)

    def test_unknown_load_is_never_unloaded(self):
        for started in (False,True):
            for returned in (False,True):
                self.assertFalse(controller.can_unload(False,started,returned))

    def test_unreturned_trigger_is_never_unloaded(self):
        self.assertFalse(controller.can_unload(True,True,False))

    def test_completed_trigger_can_be_unloaded(self):
        self.assertTrue(controller.can_unload(True,True,True))

    def test_loaded_module_without_action_can_be_unloaded(self):
        self.assertTrue(controller.can_unload(True,False,False))

    def test_default_cli_cannot_launch_or_load(self):
        with patch.object(controller,'kernel_check'),patch.object(controller,'camera',return_value=self.health),\
             patch.object(controller,'cached_display',return_value=self.display),\
             patch.object(controller,'boot',return_value='boot'),\
             patch.object(controller,'run') as command,patch.object(controller.subprocess,'run') as launch,\
             patch.object(controller,'worker') as worker,patch.object(controller,'trigger_child') as trigger,\
             patch('sys.argv',['controller.py']),patch('builtins.print'):
            self.assertEqual(controller.main(),0)
        command.assert_not_called();launch.assert_not_called();worker.assert_not_called();trigger.assert_not_called()


class SmokeCriteriaTests(unittest.TestCase):
    def setUp(self):
        self.report=dict(driver_call_returned=True,post_training_vblank_returned=True,
            module_removed=True,training_function_entries=1,encoder_enable_entries=0,
            encoder_disable_entries=0,same_camera_pid=True,cached_display_unchanged=True,
            new_optional_overruns=dict(yunet=0,sface=0),new_primary_overruns=0,new_camera_frames=5,
            after_camera=dict(owner_fenced=False,camera_error=False,worker_alive=True))

    def test_all_technical_checks_are_required(self):
        self.assertTrue(controller.smoke_passed(self.report))

    def test_postcall_exception_cannot_be_accepted(self):
        self.report['failure']='Read-only IRQ query failed'
        self.assertFalse(controller.smoke_passed(self.report))

    def test_vblank_must_return(self):
        self.report['post_training_vblank_returned']=False
        self.assertFalse(controller.smoke_passed(self.report))

    def test_face_worker_must_survive(self):
        self.report['after_camera']['worker_alive']=False
        self.assertFalse(controller.smoke_passed(self.report))

    def test_camera_must_make_progress(self):
        self.report['new_camera_frames']=0
        self.assertFalse(controller.smoke_passed(self.report))


if __name__=='__main__':
    unittest.main()
