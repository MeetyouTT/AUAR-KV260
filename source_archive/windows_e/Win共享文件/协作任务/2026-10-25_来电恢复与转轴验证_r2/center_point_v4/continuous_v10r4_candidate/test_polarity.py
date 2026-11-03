"""Both directions survive observation expiry and use pulse-space limit signs."""
import sys,unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).parent))
import test_continuous_session as fixtures
from continuous_session import ContinuousSession
from continuous_face_control import EdgeConfig


class PolarityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):fixtures.SessionTests.setUpClass()
    def scene(self,polarity):
        f=fixtures.SessionTests();f.setUp()
        f.s=ContinuousSession(f.device,'boot',EdgeConfig(left_ratio=.1),lambda p:SimpleNamespace(reference_us=p),
            trajectory=f.trajectory,clock=lambda:f.now,allow_fixture=True,polarity=polarity)
        return f
    def test_actual_image_side_changes_pulse_sign_for_both_polarities(self):
        for polarity in (-1,1):
            for center,edge in ((.04,-1),(.9,1)):
                with self.subTest(polarity=polarity,edge=edge):
                    f=self.scene(polarity);f.feed([center]*30)
                    delta=f.device.pulse-1469
                    self.assertGreater(delta*edge*polarity,0)
                    self.assertLessEqual(abs(delta),3)
                    self.assertFalse(f.s.fatal)
    def test_observation_expiry_and_stream_disconnect_preserve_mapping(self):
        for polarity in (-1,1):
            f=self.scene(polarity);f.feed([.9]*20)
            f.s.disconnected();self.assertEqual(f.s.controller.polarity,polarity)
            f.now+=.4;f.s.step(f.packet(.9,state='NO_TARGET',target=None))
            self.assertEqual(f.s.controller.polarity,polarity)
            f.feed([.5]*12);origin=f.device.pulse;f.feed([.9]*25)
            self.assertGreater((f.device.pulse-origin)*polarity,0)
    def test_inside_zone_remains_motionless_for_both_mappings(self):
        for polarity in (-1,1):
            f=self.scene(polarity);f.feed([.5]*30)
            self.assertEqual(f.device.commands,[]);self.assertEqual(f.device.arms,0)
    def test_opposite_polarity_keeps_same_pulse_direction_limit_latched(self):
        f=self.scene(-1);f.feed([.9]*20);f.s.limit_side=-1
        f.s.step(f.packet(.9))
        self.assertEqual(f.s.limit_side,-1)
        f.tick();self.assertEqual(f.s.reason,'SOFT_LIMIT_HOLD')
    def test_invalid_polarity_is_rejected_before_hardware_setup(self):
        f=self.scene(1)
        for polarity in (True,False,0,2,-2,'-1',None):
            with self.assertRaises(ValueError):
                ContinuousSession(f.device,'boot',f.s.config,f.s.factory,trajectory=f.trajectory,polarity=polarity)
        self.assertEqual(f.device.arms,0);self.assertEqual(f.device.commands,[])


if __name__=='__main__':unittest.main()
