import unittest
from types import SimpleNamespace
import test_continuous_session as fixtures
from continuous_face_control import EdgeConfig
from continuous_session import ContinuousSession


class PrearmTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):fixtures.SessionTests.setUpClass()
    def scene(self,prearm):
        f=fixtures.SessionTests();f.setUp()
        c=EdgeConfig(left_ratio=.1,confirm_frames=2,maximum_correction_us=None,
            prearm_confirmed_face=prearm,maximum_speed_us_s=20.,velocity_gain_us=12.)
        f.s=ContinuousSession(f.device,'boot',c,lambda p:SimpleNamespace(reference_us=p),
            trajectory=f.trajectory,clock=lambda:f.now,allow_fixture=True,polarity=1)
        return f
    def test_inside_preparation_never_starts_pwm(self):
        f=self.scene(True);f.feed([.5]*50)
        self.assertEqual(f.device.arms,1);self.assertEqual(f.device.commands,[])
        self.assertFalse(f.s.status()['pwm_output_started'])
        self.assertEqual(f.device.pulse,1469)
    def test_preparation_reduces_first_outside_command_delay_without_old_source(self):
        delays=[]
        for prearm in (False,True):
            f=self.scene(prearm);f.feed([.79]*15);started=f.now;f.feed([.84]*12)
            moved=[x for x in f.device.commands if x['target']!=1469]
            self.assertTrue(moved);delays.append(moved[0]['now']-started)
            self.assertTrue(all(c['stamp']>f.device.reference_time for c in f.device.commands))
        self.assertLess(delays[1],delays[0])
    def test_face_loss_cancels_preparation_without_sending_any_pwm(self):
        f=self.scene(True);f.feed([.5]*8)
        f.s.step(f.packet(state='NO_TARGET',target=None))
        self.assertFalse(f.s.active);self.assertEqual(f.device.commands,[])
        self.assertEqual(f.device.status()['flags'],0)
