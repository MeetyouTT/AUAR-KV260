from dataclasses import replace
from types import SimpleNamespace
import unittest
from continuous_face_control import EdgeConfig
from hardware_slew_session import HardwareSlewSession
from test_hardware_slew import FrameSlewDevice
from test_recenter import Scene,profile
from board.motion.vsrv_driver import PhysicalReference,MIN_LEASE_MS

def wide_scene(reference=1400):
    f=Scene(reference);solver=f.session.trajectory
    f.device=FrameSlewDevice(lambda:f.now,reference,500,2500)
    config=replace(profile(),minimum_us=500,maximum_us=2500,single_pass_recenter=True,
                   smooth_recenter_stop=True,hardware_slew_recenter=True,
                   maximum_speed_us_s=40.,velocity_gain_us=0.)
    f.session=HardwareSlewSession(f.device,'fixture-boot',config,lambda p:SimpleNamespace(reference_us=p),
                                trajectory=solver,clock=lambda:f.now,allow_fixture=True)
    return f

class WideRangeTests(unittest.TestCase):
    def test_wide_bounds_and_reference(self):
        EdgeConfig(minimum_us=500,maximum_us=2500)
        for p in [500,2048,2500]:PhysicalReference('boot',p,'fixture','software test',1,True,True)
        self.assertEqual(MIN_LEASE_MS,4)
        for p in [499,2501]:
            with self.assertRaises(ValueError):PhysicalReference('boot',p,'fixture','software test',1,True,True)
        for bounds in [(499,2500),(500,2501)]:
            with self.assertRaises(ValueError):EdgeConfig(minimum_us=bounds[0],maximum_us=bounds[1])

    def test_right_endpoint_does_not_jump_output(self):
        f=wide_scene();f.feed([.86]*14)
        self.assertTrue(f.device.commands)
        self.assertEqual({c['target'] for c in f.device.commands},{2500})
        changed=[r for r in f.device.frames if r['width']!=r['before']]
        self.assertEqual(changed[0]['width'],1404)
        self.assertTrue(all(abs(r['width']-r['before'])<=4 for r in changed))
        self.assertLess(f.device.pulse,2500)

    def test_left_endpoint(self):
        f=wide_scene(1600);f.feed([.30]*4+[.16]*10)
        self.assertTrue(f.device.commands)
        self.assertEqual({c['target'] for c in f.device.commands},{500})
        self.assertGreater(f.device.pulse,500)

    def test_stale_source_stops_wide_motion(self):
        f=wide_scene();f.feed([.86]*8);count=len(f.device.commands)
        self.assertTrue(count)
        f.now+=1.0;f.session.tick()
        self.assertEqual(len(f.device.commands),count)
        self.assertFalse(f.device.status()['active'])

    def test_center_stops_before_endpoint(self):
        f=wide_scene();f.feed([.86]*4+[.70]*3+[.60]*3+[.55]*3+[.52]*3)
        self.assertGreater(f.device.finishes,0)
        self.assertLess(f.device.pulse,2500)
        self.assertFalse(f.device.status()['active'])

if __name__=='__main__':unittest.main()
