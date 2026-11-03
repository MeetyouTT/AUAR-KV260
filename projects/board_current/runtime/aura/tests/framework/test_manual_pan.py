"""Manual calibration policy tests; fake hardware produces no physical output."""
import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from board.motion.manual import ManualPan
from board.motion.manual_vsrv import ManualVSRV, ManualCommandError


class Hardware:
    def __init__(self, pulse=1430):
        self.pulse = pulse
        self.calls = []
        self.preflight_gate = None
        self.fail_commit = False
        self.reject_preflight = False
        self.flags = 0
        self.epoch = 8
        self.seq = 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.calls.append('close')

    def status(self):
        return dict(flags=self.flags, lease_left_ms=100 if self.flags else 0,
                    width_us=self.pulse, epoch=self.epoch, ack_seq=self.seq)

    def before_move(self):
        if self.reject_preflight:
            raise ValueError('正在登记身份')
        if self.preflight_gate:
            self.preflight_gate.wait(1)

    def begin(self, before):
        self.calls.append('begin')
        self.epoch += 1
        self.seq = 0

    def commit(self, target):
        self.calls.append(('commit', target))
        if self.fail_commit:
            raise RuntimeError('ACK mismatch')
        self.seq += 1
        self.pulse = target
        self.flags = 15
        return self.status()

    def stop(self):
        self.calls.append('stop')
        self.flags = 0
        return self.status()


def wait_for(predicate):
    deadline = time.monotonic()+2
    while not predicate():
        if time.monotonic() > deadline:
            raise AssertionError('Timed out')
        time.sleep(.002)


class ManualPanTests(unittest.TestCase):
    def start(self, hardware=None, duration=.06):
        hardware = hardware or Hardware()
        pan = ManualPan(lambda:hardware, duration_s=duration)
        self.addCleanup(pan.close)
        wait_for(lambda:pan.read()['state'] != 'CONNECTING')
        return pan, hardware

    def complete(self, pan, direction='left', step=20):
        before = len(pan.read()['history'])
        pan.jog(direction, step)
        wait_for(lambda:pan.read()['state'] in ('READY','FAULT'))
        self.assertEqual(len(pan.read()['history']), before+1)

    def test_startup_reads_actual_pulse_without_arm_or_motion(self):
        pan, hardware = self.start()
        self.assertEqual(pan.read()['pulse_us'],1430)
        self.assertEqual(hardware.calls,[])
        self.assertFalse(pan.read()['mechanical_reference_calibrated'])
        self.assertFalse(pan.read()['automatic_following'])

    def test_left_decreases_and_right_increases_pulse(self):
        pan, hardware = self.start()
        self.complete(pan)
        self.assertEqual(pan.read()['pulse_us'],1410)
        self.complete(pan,'right')
        self.assertEqual(pan.read()['pulse_us'],1430)
        self.assertEqual(hardware.flags,0)

    def test_fine_step_and_direction_swap(self):
        pan, hardware = self.start()
        pan.reverse()
        self.complete(pan,'left',5)
        self.assertEqual(hardware.pulse,1435)

    def test_no_movement_is_queued_while_busy(self):
        pan, hardware = self.start(duration=.5)
        pan.jog('right')
        with self.assertRaises(ValueError):pan.jog('left')
        with self.assertRaises(ValueError):pan.reverse()
        pan.stop()
        wait_for(lambda:pan.read()['state']=='READY')

    def test_stop_interrupts_before_duration_and_confirms_output_off(self):
        pan, hardware = self.start(duration=2)
        pan.jog('right')
        wait_for(lambda:any(isinstance(x,tuple) for x in hardware.calls))
        start=time.monotonic()
        pan.stop()
        wait_for(lambda:pan.read()['state']=='READY')
        self.assertLess(time.monotonic()-start,.2)
        self.assertTrue(pan.read()['history'][-1]['stopped_early'])
        self.assertEqual(pan.read()['readback']['flags'],0)

    def test_stop_during_preflight_prevents_arm(self):
        h=Hardware();h.preflight_gate=threading.Event()
        pan,h=self.start(h)
        pan.jog('left');pan.stop();h.preflight_gate.set()
        wait_for(lambda:pan.read()['state']=='READY')
        self.assertNotIn('begin',h.calls)

    def test_limits_reject_instead_of_clamping_or_extending_range(self):
        pan,h=self.start(Hardware(1400))
        with self.assertRaises(ValueError):pan.jog('left',5)
        self.assertEqual(h.calls,[])
        pan,h=self.start(Hardware(1600))
        with self.assertRaises(ValueError):pan.jog('right',20)

    def test_bad_direction_step_bool_and_large_step_rejected(self):
        pan,h=self.start()
        for direction,step in [('up',5),('left',True),('left',100),('left',0)]:
            with self.assertRaises(ValueError):pan.jog(direction,step)
        self.assertEqual(h.calls,[])

    def test_ack_failure_stops_and_latches_fault(self):
        pan,h=self.start();h.fail_commit=True
        pan.jog('right')
        wait_for(lambda:pan.read()['state']=='FAULT')
        self.assertEqual(h.flags,0)
        self.assertIn('ACK mismatch',pan.read()['error'])
        with self.assertRaises(ValueError):pan.jog('right')

    def test_stale_intent_cannot_arm(self):
        pan,h=self.start();pan.clock=lambda:time.monotonic()+1
        h.preflight_gate=threading.Event()
        pan.jog('left');pan.clock=lambda:time.monotonic()+3
        h.preflight_gate.set()
        wait_for(lambda:pan.read()['state']=='READY')
        self.assertNotIn('begin',h.calls)

    def test_identity_sampling_rejects_without_arm_and_allows_later_manual_retry(self):
        pan,h=self.start();h.reject_preflight=True
        pan.jog('right');wait_for(lambda:pan.read()['state']=='READY')
        self.assertNotIn('begin',h.calls)
        self.assertIn('登记身份',pan.read()['message'])
        h.reject_preflight=False
        self.complete(pan,'right')
        self.assertEqual(pan.read()['pulse_us'],1450)

    def test_close_stops_and_releases_owner(self):
        pan,h=self.start(duration=2)
        pan.jog('right');wait_for(lambda:'begin' in h.calls)
        pan.close()
        self.assertEqual(h.flags,0)
        self.assertIn('close',h.calls)
        self.assertFalse(pan.thread.is_alive())

    def test_active_startup_is_refused_without_arm(self):
        h=Hardware();h.flags=15
        pan,h=self.start(h)
        self.assertEqual(pan.read()['state'],'FAULT')
        self.assertNotIn('begin',h.calls)

    def test_duration_is_finite(self):
        for duration in (0,3):
            with self.assertRaises(ValueError):ManualPan(lambda:None,duration_s=duration)

    def test_host_adapter_rejects_without_board_mmio(self):
        adapter=ManualVSRV({})
        with patch('board.motion.manual_vsrv.os.uname',return_value=SimpleNamespace(machine='x86_64')):
            with self.assertRaises(RuntimeError):adapter.verify_platform()
        self.assertIsNone(adapter.io)

    def test_expired_permission_is_recorded_before_any_new_commit(self):
        adapter=ManualVSRV({});adapter.session=123;adapter.epoch=9;adapter.seq=3
        state=dict(flags=0,lease_left_ms=0,session=123,epoch=9,ack_seq=3,width_us=1450)
        adapter.status=lambda:dict(state)
        with self.assertRaises(ManualCommandError) as caught:adapter.commit(1455)
        self.assertEqual(caught.exception.detail['before'],state)
        self.assertEqual(caught.exception.detail['attempted_seq'],4)
        self.assertIsNone(adapter.io)

    def test_failed_step_retains_diagnostic_after_stop_clears_flags(self):
        pan,h=self.start();h.fail_commit=True
        pan.jog('right');wait_for(lambda:pan.read()['state']=='FAULT')
        row=pan.read()['history'][-1]
        self.assertIn('ACK mismatch',row['failure']['error'])
        self.assertEqual(row['final']['flags'],0)


if __name__=='__main__':
    unittest.main()
