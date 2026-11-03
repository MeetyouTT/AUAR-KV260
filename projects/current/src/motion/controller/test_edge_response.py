import unittest
from types import SimpleNamespace
import test_continuous_session as fixtures
from continuous_face_control import EdgeConfig
from continuous_session import ContinuousSession


class EdgeResponseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):fixtures.SessionTests.setUpClass()
    def scene(self,floor):
        f=fixtures.SessionTests();f.setUp()
        c=EdgeConfig(left_ratio=.1,confirm_frames=2,maximum_correction_us=None,prearm_confirmed_face=True,
                     maximum_speed_us_s=20.,minimum_edge_speed_us_s=floor,velocity_gain_us=12.)
        f.s=ContinuousSession(f.device,'boot',c,lambda p:SimpleNamespace(reference_us=p),
            trajectory=f.trajectory,clock=lambda:f.now,allow_fixture=True,polarity=1)
        return f
    def test_near_boundary_minimum_speed_reduces_quantized_start_delay(self):
        delays=[]
        for floor in (2.,6.):
            f=self.scene(floor);f.feed([.8]*20);start=f.now;f.feed([.808]*20)
            moved=[x for x in f.device.commands if x['target']!=1469]
            self.assertTrue(moved);delays.append(moved[0]['now']-start)
            self.assertTrue(all(abs(x['delta_us'])<=4 for x in f.s.command_trace))
            f.feed([.8]*10);pulse=f.device.pulse;f.feed([.5]*10)
            self.assertEqual(f.device.pulse,pulse)
        self.assertLess(delays[1],delays[0])
    def test_lk_refresh_expiry_preserves_only_original_finite_authority(self):
        f=self.scene(6.);f.feed([.9]*15);old=f.s.authority
        p=f.expired_refresh();p['face_tracking']['reason']='FACE_FIXED_ANCHOR_LK_AFFINE'
        f.now+=.02;f.s.step(p);self.assertEqual(f.s.authority,old)
        f.tick(20);self.assertFalse(f.s.active);self.assertEqual(f.device.status()['flags'],0)
    def test_detector_timing_is_collected_even_when_face_is_unconfirmed(self):
        from input_timing import InputTiming
        t=InputTiming();p=dict(state='UNCONFIRMED',detector_timing={'frame_id':7,'process_begin_mono_ns':1000})
        for _ in range(20):t.observe(p,{},10)
        snapshot=t.snapshot();self.assertEqual(snapshot['counts']['distinct_detector_rounds'],1)
        self.assertEqual(len(snapshot['detector_round_timing']),1)
