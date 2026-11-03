"""The GUI must not display a historical register value as current feedback."""
import threading
import unittest
from unittest.mock import patch
from tools.face_pan_controls import FacePanProcess


class Manual:
    def read(self):
        return dict(state='READY', pulse_us=1500, target_us=1500,
            readback=dict(width_us=1500, flags=0, lease_left_ms=0),
            automatic_following=False, message='', error='')


def proxy(result):
    value = FacePanProcess.__new__(FacePanProcess)
    value.manual = Manual()
    value.lock = threading.RLock()
    value.running = True
    value.cleanup_pending = False
    value.output = None
    value.last_report_read = 0
    value.result = result
    return value


class FollowReportFreshnessTests(unittest.TestCase):
    def read_at(self, result, *, cleanup=False):
        p = proxy(result)
        p.cleanup_pending = cleanup
        with patch('tools.face_pan_controls.time.monotonic', return_value=10.):
            return p.read()

    def test_starting_follow_has_no_current_pulse_receipt(self):
        value = self.read_at(dict(state='STARTING'))
        self.assertIsNone(value['pulse_us'])
        self.assertIsNone(value['readback'])
        self.assertFalse(value['face_follow']['report_fresh'])

    def test_fresh_report_uses_follow_register_feedback(self):
        value = self.read_at(dict(state='CONTINUOUS_FACE_ZONE_RUNNING', phase='FOLLOWING',
            heartbeat_mono_ms=9900, pulse_us=1640,
            readback=dict(width_us=1640, target_us=2500, flags=15, lease_left_ms=100)))
        self.assertEqual(value['pulse_us'], 1640)
        self.assertTrue(value['face_follow']['report_fresh'])
        self.assertEqual(value['face_follow']['report_age_ms'], 100)

    def test_stale_report_cannot_claim_current_pulse_or_motion(self):
        value = self.read_at(dict(state='CONTINUOUS_FACE_ZONE_RUNNING', phase='FOLLOWING',
            heartbeat_mono_ms=8000, pulse_us=1640, readback=dict(width_us=1640)))
        self.assertIsNone(value['pulse_us'])
        self.assertIsNone(value['readback'])
        self.assertEqual(value['state'], 'UNAVAILABLE')
        self.assertTrue(value['automatic_following'])  # STOP control remains available.

    def test_future_or_invalid_heartbeat_cannot_claim_current_pulse(self):
        for heartbeat in (11000, True, float('nan'), None):
            with self.subTest(heartbeat=heartbeat):
                value = self.read_at(dict(state='CONTINUOUS_FACE_ZONE_RUNNING',
                    heartbeat_mono_ms=heartbeat, pulse_us=1640, readback=dict(width_us=1640)))
                self.assertIsNone(value['pulse_us'])
                self.assertFalse(value['face_follow']['report_fresh'])

    def test_terminal_report_is_not_presented_as_current_follow_motion(self):
        value = self.read_at(dict(state='CONTINUOUS_FACE_ZONE_STOPPED',
            phase='FOLLOWING', heartbeat_mono_ms=10000, pulse_us=1640))
        self.assertEqual(value['state'], 'UNAVAILABLE')
        self.assertIsNone(value['pulse_us'])

    def test_cleanup_keeps_stop_retry_and_does_not_show_old_manual_pulse(self):
        value = self.read_at(dict(state='FAILED'), cleanup=True)
        self.assertEqual(value['state'], 'STOPPING')
        self.assertTrue(value['automatic_following'])
        self.assertIsNone(value['pulse_us'])


if __name__ == '__main__':
    unittest.main()
