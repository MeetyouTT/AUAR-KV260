import unittest
from types import SimpleNamespace
import test_continuous_session as fixtures
from continuous_face_control import EdgeConfig
from continuous_session import ContinuousSession


class ResponsiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):fixtures.SessionTests.setUpClass()
    def scene(self,responsive=True):
        f=fixtures.SessionTests();f.setUp()
        c=EdgeConfig(left_ratio=.1,confirm_frames=2,maximum_correction_us=None,
                     maximum_speed_us_s=20. if responsive else 10.,velocity_gain_us=12. if responsive else 0.)
        f.s=ContinuousSession(f.device,'boot',c,lambda p:SimpleNamespace(reference_us=p),
            trajectory=f.trajectory,clock=lambda:f.now,allow_fixture=True,polarity=1)
        return f
    def test_fast_outward_face_gets_more_speed_without_large_steps(self):
        baseline=self.scene(False);responsive=self.scene(True)
        values=[.79]*10+[.8+i*.004 for i in range(30)]
        for f in (baseline,responsive):f.feed(values)
        self.assertGreater(responsive.device.pulse,baseline.device.pulse)
        self.assertTrue(all(abs(x['delta_us'])<=4 for x in responsive.s.command_trace))
        self.assertTrue(all(abs(x['velocity_us_s'])<=20.0001 for x in responsive.s.command_trace))
        self.assertFalse(responsive.s.fatal)
    def test_inside_motion_does_not_use_speed_feedback_to_move_the_axis(self):
        f=self.scene();f.feed([.2+i*.01 for i in range(45)]+[.65-i*.01 for i in range(45)])
        self.assertEqual(f.device.commands,[]);self.assertEqual(f.device.arms,0)
    def test_return_and_real_face_loss_stop_motion_with_responsive_profile(self):
        f=self.scene();f.feed([.9]*30);self.assertTrue(f.device.commands)
        f.feed([.79]*3);pulse=f.device.pulse;f.feed([.7]*8)
        self.assertEqual(f.device.pulse,pulse)
        f.feed([.9]*20);f.s.step(f.packet(state='NO_TARGET',target=None))
        self.assertFalse(f.s.active);self.assertEqual(f.device.status()['flags'],0)
