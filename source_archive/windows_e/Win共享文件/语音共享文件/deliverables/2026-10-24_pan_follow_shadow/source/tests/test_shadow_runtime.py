import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
APP = Path('/home/ghmd/Win共享文件/共享文件夹/aura')
sys.path.insert(0, str(ROOT / 'shadow_runtime'))
sys.path.insert(0, str(APP))
sys.path.insert(0, str(ROOT))
from common.motion_observation import MAX_AGE_MS, PROTOCOL
from shadow_follow import FollowConfig, PanFollowController, ShadowDriver


class ShadowRuntimeTests(unittest.TestCase):
    def test_live_shadow_controller_has_no_physical_driver_and_observed_bounds(self):
        config = json.loads((ROOT / 'config/pan_follow.shadow.json').read_text())['controller']
        control = FollowConfig(**config)
        driver = ShadowDriver()
        controller = PanFollowController(driver, 'boot', reference_us=1425,
                                         polarity=-1, camera_moves_with_axis=True,
                                         config=control, physical=False)
        for index in range(30):
            stamp = 1000 + index*100
            packet = {
                'protocol_version': PROTOCOL, 'source_kind': 'actual',
                'board_boot_id': 'boot', 'service_epoch': 'service',
                'camera_epoch': 'camera', 'state': 'READY',
                'source_frame_id': index+1, 'source_mono_ms': stamp,
                'deadline_mono_ms': stamp+MAX_AGE_MS,
                'frame_width': 640, 'frame_height': 480,
                'mirror_horizontal': True,
                'target': {'track_id': 1, 'track_generation': 1,
                           'box': [40., 0., 80., 480.], 'score': .9},
            }
            controller.observe(packet, stamp+50)
        self.assertTrue(driver.submissions)
        self.assertTrue(all(1425 <= pulse <= 1445 for pulse, _ in driver.submissions))
        self.assertEqual(controller.status()['scope'], 'SOFTWARE_SHADOW')
        with self.assertRaises(ValueError):
            PanFollowController(driver, 'boot', reference_us=1425,
                                config=control, physical=True)


if __name__ == '__main__':
    unittest.main()
