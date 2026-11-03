"""A duplicate image cannot bypass the original invalid-clock STOP path."""
import unittest
from test_wide_range import wide_scene


class DuplicateClockSafetyTests(unittest.TestCase):
    def test_duplicate_source_preserves_clock_rollback_stop(self):
        scene = wide_scene()
        scene.feed([.86] * 4)
        self.assertTrue(scene.session.active)
        before = len(scene.device.commands)
        last_observation_ms = scene.session.controller.last_now
        scene.now = (last_observation_ms - 1) / 1000.
        scene.session.step(scene.last)
        self.assertTrue(scene.session.fatal)
        self.assertEqual(scene.session.reason, 'INVALID_CLOCK')
        self.assertEqual(len(scene.device.commands), before)
        self.assertEqual(scene.device.status()['flags'], 0)


if __name__ == '__main__':
    unittest.main()
