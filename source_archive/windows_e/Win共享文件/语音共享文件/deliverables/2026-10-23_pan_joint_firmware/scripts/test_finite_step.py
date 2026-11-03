import json
from pathlib import Path
import subprocess
import sys
import unittest

from bench_finite_step import run_finite


class FakeClock:
    def __init__(self):
        self.now = 100.

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class FakeHardware:
    """Model an expiring permit; output cannot resume after a lost lease."""
    def __init__(self, clock):
        self.clock = clock
        self.shadow = {}
        self.flags = self.seq = self.session = self.epoch = self.reason = 0
        self.width = self.target = self.reference = 1500
        self.expires = None
        self.stops = self.finishes = self.commits = 0
        self.delay_shadow = False

    def write(self, offset, value):
        if offset != 0x24:
            self.shadow[offset] = value
            if self.delay_shadow and offset == 0x20:
                self.clock.sleep(.03)
            return
        if value == 0x42494e44:
            self.flags = 8
            self.session, self.epoch, self.seq = self.shadow[0x10], self.shadow[0x14], 0
        elif value == 0x52454621:
            self.flags = 12
            self.width = self.target = self.reference = self.shadow[0x3c]
        elif value == 0x41524d21:
            self.flags = 14
        elif value == 0x434d5421:
            if self.flags & 14 != 14:
                raise RuntimeError('Fake hardware rejected expired permit')
            self.flags = 15
            self.seq = self.shadow[0x18]
            self.width = self.target = self.shadow[0x1c]
            self.expires = self.clock() + .1
            self.commits += 1
        else:
            raise RuntimeError('Unexpected command in finite bench')

    def status(self):
        if self.expires is not None and self.clock() >= self.expires and self.flags & 1:
            self.flags = 0
            self.reason = 4
        return {'flags': self.flags, 'active': bool(self.flags & 1),
            'session': self.session, 'epoch': self.epoch, 'ack_seq': self.seq,
            'width_us': self.width, 'target_us': self.target, 'reference_us': self.reference,
            'lease_left_ms': 100 if self.flags & 1 else 0, 'reason': self.reason}

    def stop(self):
        self.stops += 1
        self.flags = self.reason = 0
        return self.status()

    def finish(self):
        self.finishes += 1
        self.flags = self.reason = 0
        return self.status()


class FiniteStepTests(unittest.TestCase):
    def setUp(self):
        self.clock = FakeClock()
        self.hardware = FakeHardware(self.clock)
        self.events = []

    def run_bench(self, sleep=None):
        return run_finite(self.hardware, self.hardware, 1420, 1425, self.events,
                          clock=self.clock, sleep=sleep or self.clock.sleep)

    def test_two_seconds_and_full_finish(self):
        result = self.run_bench()
        self.assertAlmostEqual(self.clock.now, 102.)
        self.assertEqual(self.hardware.finishes, 1)
        self.assertEqual(self.hardware.stops, 2)
        self.assertEqual({row['target_us'] for row in self.events}, {1420, 1425})
        self.assertEqual(result['stopped']['flags'], 0)
        self.assertFalse(result['mechanical_reference_calibrated'])

    def test_slow_shadow_writes_do_not_commit(self):
        self.hardware.delay_shadow = True
        with self.assertRaisesRegex(RuntimeError, 'Late submission refused'):
            self.run_bench()
        self.assertEqual(self.hardware.commits, 0)
        self.assertEqual(self.hardware.flags, 0)
        self.assertEqual(self.hardware.stops, 2)

    def test_stall_expiry_stops_without_rearm_or_retry(self):
        with self.assertRaisesRegex(RuntimeError, 'Lease or command context lost'):
            self.run_bench(sleep=lambda _: self.clock.sleep(.11))
        self.assertEqual(self.hardware.commits, 1)
        self.assertEqual(self.hardware.flags, 0)
        self.assertEqual(self.hardware.finishes, 0)

    def test_already_active_rejected_without_setup(self):
        self.hardware.flags = 15
        with self.assertRaisesRegex(RuntimeError, 'already be stopped'):
            self.run_bench()
        self.assertEqual(self.hardware.shadow, {})
        self.assertEqual(self.hardware.commits, 0)

    def test_more_than_five_microseconds_refused(self):
        with self.assertRaisesRegex(RuntimeError, 'Invalid finite step'):
            run_finite(self.hardware, self.hardware, 1420, 1440, [], clock=self.clock, sleep=self.clock.sleep)
        self.assertEqual(self.hardware.shadow, {})

    def test_default_cli_is_plan_only(self):
        script = Path(__file__).with_name('bench_finite_step.py')
        process = subprocess.run([sys.executable, '-B', str(script)], capture_output=True, text=True)
        self.assertEqual(process.returncode, 0)
        result = json.loads(process.stdout)
        self.assertFalse(result['board_accessed'])
        self.assertTrue(result['initial_pulse_requires_operator_selection'])


if __name__ == '__main__':
    unittest.main()
