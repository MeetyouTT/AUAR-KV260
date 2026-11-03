"""Candidate-only fault injection. No MMIO, real camera, or physical motion."""
import math
import multiprocessing
import time
import unittest
from unittest.mock import patch

from board.motion.input_freshness import InputFreshness
from board.motion.manual import ManualPan
from board.motion.manual_process import ManualPanProcess, backend
from board.motion.manual_vsrv import load_release
from board.motion.vsrv_driver import VSRVDriver, ID, ABI, BUILD_ID, QUIESCE, STOP
from board.motion.vsrv_transport import NativeRegisters
from test_manual_pan import Hardware, wait_for
from test_manual_pan_process import fake_backend, wait_process


class Clock:
    def __init__(self): self.now = 10.
    def __call__(self): return self.now
    def advance(self, seconds): self.now += seconds


class Registers:
    def __init__(self, mode='normal'):
        self.values = {0: ID, 4: ABI, 8: BUILD_ID, 0x0c: 15, 0x28: 3, 0x2c: 1420,
                       0x30: 100, 0x34: 11, 0x38: 2, 0x40: 1420, 0x44: 1440}
        self.writes, self.pending, self.mode = [], 0, mode

    def read(self, offset):
        if offset == 0x0c and self.pending:
            if self.mode == 'normal':
                self.pending -= 1
                if not self.pending: self.values.update({0x0c: 0, 0x30: 0})
            elif self.mode == 'context': self.values[0x38] += 1
            elif self.mode == 'expiry': self.values.update({0x0c: 64, 0x30: 0})
        return self.values.get(offset, 0)

    def write(self, offset, value):
        self.writes.append((offset, value))
        if offset == 0x24 and value == QUIESCE: self.pending = 2
        if offset == 0x24 and value == STOP:
            self.pending = 0
            self.values.update({0x0c: 0, 0x30: 0})


class DriverCompletionTests(unittest.TestCase):
    def test_finish_waits_for_off_without_immediate_stop(self):
        registers = Registers(); driver = VSRVDriver(registers, BUILD_ID, 'boot')
        result = driver.finish()
        self.assertEqual(result['flags'], 0)
        self.assertEqual(result['lease_left_ms'], 0)
        self.assertEqual(registers.writes, [(0x24, QUIESCE)])

    def test_finish_of_already_off_hardware_sends_no_command(self):
        registers = Registers(); registers.values.update({0x0c: 0, 0x30: 0})
        VSRVDriver(registers, BUILD_ID, 'boot').finish()
        self.assertEqual(registers.writes, [])

    def test_stuck_completion_falls_back_to_stop_and_raises(self):
        clock = Clock(); registers = Registers('stuck')
        driver = VSRVDriver(registers, BUILD_ID, 'boot', clock=clock)
        with patch('board.motion.vsrv_driver.time.sleep', side_effect=lambda _:clock.advance(.01)):
            with self.assertRaisesRegex(RuntimeError, 'timed out'): driver.finish()
        self.assertEqual(registers.writes, [(0x24, QUIESCE), (0x24, STOP)])

    def test_context_change_is_not_accepted_as_success(self):
        registers = Registers('context'); driver = VSRVDriver(registers, BUILD_ID, 'boot')
        with self.assertRaisesRegex(RuntimeError, 'Context changed'): driver.finish()
        self.assertEqual(registers.writes[-1], (0x24, STOP))

    def test_expiry_during_completion_is_a_fault(self):
        registers = Registers('expiry'); driver = VSRVDriver(registers, BUILD_ID, 'boot')
        with self.assertRaisesRegex(RuntimeError, 'Hardware fault'): driver.finish()
        self.assertEqual(registers.writes[-1], (0x24, STOP))

    def test_already_expired_permission_is_not_cleared_into_ready(self):
        registers = Registers(); registers.values.update({0x0c: 64, 0x30: 0})
        driver = VSRVDriver(registers, BUILD_ID, 'boot')
        with self.assertRaisesRegex(RuntimeError, 'expired'): driver.finish()
        self.assertNotIn((0x24, QUIESCE), registers.writes)

    def test_old_abi_or_build_cannot_send_a_command(self):
        for offset, value in [(4, 1), (8, 0x14da0e60)]:
            registers = Registers(); registers.values[offset] = value
            with self.assertRaises(RuntimeError): VSRVDriver(registers, BUILD_ID, 'boot')
            self.assertEqual(registers.writes, [])
        with self.assertRaises(ValueError): VSRVDriver(Registers(), 0, 'boot')

    def test_unbounded_or_invalid_wait_is_rejected_without_write(self):
        for timeout in [0, -.1, .1, math.nan, math.inf, True]:
            registers = Registers(); driver = VSRVDriver(registers, BUILD_ID, 'boot')
            with self.assertRaises(ValueError): driver.finish(timeout_s=timeout)
            self.assertEqual(registers.writes, [])

    def test_immediate_stop_is_still_available(self):
        registers = Registers(); VSRVDriver(registers, BUILD_ID, 'boot').stop()
        self.assertEqual(registers.writes, [(0x24, STOP)])


class StepCompletionTests(unittest.TestCase):
    def start(self, hardware=None, **options):
        hardware = hardware or Hardware()
        pan = ManualPan(lambda:hardware, duration_s=.06, **options)
        self.addCleanup(pan.close); wait_for(lambda:pan.read()['state']=='READY')
        return pan, hardware

    def test_normal_end_uses_full_pulse_finish(self):
        pan, hardware = self.start(); pan.jog('right')
        wait_for(lambda:len(pan.read()['history'])==1)
        self.assertEqual(pan.read()['state'], 'READY')
        self.assertEqual(hardware.calls.count('finish'), 1)
        self.assertNotIn('stop', hardware.calls)
        self.assertEqual(pan.read()['history'][-1]['completion'], 'FULL_PULSE_FINISH')

    def test_failed_finish_latches_fault_even_if_fallback_stop_succeeds(self):
        class Stuck(Hardware):
            def finish(self): raise RuntimeError('Completion did not settle')
        pan, hardware = self.start(Stuck()); pan.jog('right')
        wait_for(lambda:pan.read()['state']=='FAULT')
        self.assertEqual(hardware.flags, 0)
        self.assertIn('Completion did not settle', pan.read()['history'][-1]['failure']['error'])
        with self.assertRaises(ValueError): pan.jog('left')

    def test_explicit_stop_keeps_immediate_path(self):
        pan, hardware = self.start(); pan.jog('right')
        wait_for(lambda:any(isinstance(call, tuple) for call in hardware.calls))
        pan.stop(); wait_for(lambda:len(pan.read()['history'])==1)
        self.assertEqual(pan.read()['history'][-1]['completion'], 'IMMEDIATE_STOP')
        self.assertNotIn('finish', hardware.calls)

    def test_original_time_is_preserved_through_manual_preflight(self):
        clock = Clock(); pan, hardware = self.start(clock=clock)
        hardware.before_move = lambda:clock.advance(.2)
        pan.jog('right', source_time=clock()-.1)
        wait_for(lambda:len(pan.read()['history'])==1)
        self.assertNotIn('begin', hardware.calls)
        self.assertEqual(pan.read()['history'][-1]['commands_accepted'], 0)
        self.assertEqual(pan.read()['history'][-1]['source_time'], 9.9)

    def test_stale_future_and_nan_direct_intents_never_arm(self):
        pan, hardware = self.start()
        for source in [time.monotonic()-1, time.monotonic()+5, math.nan, math.inf, True]:
            with self.assertRaises(ValueError): pan.jog('right', source_time=source)
        self.assertEqual(hardware.calls, [])


class FreshnessTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock(); self.gate = InputFreshness(self.clock)
        for _ in range(6): self.clock.advance(.05); self.gate.heartbeat()

    def check(self, event=1000, server=1020, round_trip=.002):
        before = self.clock(); self.clock.advance(round_trip)
        return self.gate.source_time(event, server, before, self.clock())

    def test_fresh_event_is_converted_conservatively(self):
        before = self.clock(); source = self.check()
        self.assertAlmostEqual(source, before-.02)

    def test_old_event_rejected_even_after_heartbeat_is_current(self):
        with self.assertRaises(ValueError): self.check(event=500)

    def test_future_event_rejected(self):
        with self.assertRaises(ValueError): self.check(event=1030)

    def test_x_timestamp_wrap_is_handled(self):
        source = self.check(event=0xfffffff0, server=20)
        self.assertAlmostEqual(self.clock()-source, .038)

    def test_missing_time_or_boolean_rejected(self):
        for stamp in [0, None, True, -1, 0x100000000]:
            with self.assertRaises(ValueError): self.check(event=stamp)

    def test_long_server_round_trip_rejected(self):
        with self.assertRaises(ValueError): self.check(round_trip=.11)

    def test_stalled_gui_rejects_even_a_recent_event(self):
        self.clock.advance(.3)
        with self.assertRaises(ValueError): self.check()

    def test_recovered_gui_requires_quiet_window(self):
        self.clock.advance(.3); self.gate.heartbeat()
        with self.assertRaises(ValueError): self.check()
        for _ in range(6): self.clock.advance(.05); self.gate.heartbeat()
        self.check()

    def test_monotonic_clock_reversal_rejects(self):
        self.clock.advance(-1)
        with self.assertRaises(ValueError): self.check()


def delayed_backend(connection, config):
    class Delayed(Hardware):
        def before_move(self): time.sleep(.12)
    backend(connection, config, transport_factory=Delayed)


class IPCFreshnessTests(unittest.TestCase):
    def test_proxy_does_not_accept_old_or_future_source(self):
        pan = ManualPanProcess({}, target=fake_backend); self.addCleanup(pan.close)
        wait_process(lambda:pan.read()['state']=='READY')
        for stamp in [time.monotonic()-1, time.monotonic()+2, math.nan, True]:
            with self.assertRaises(ValueError): pan.jog('right', source_time=stamp)
        self.assertEqual(pan.read()['history'], [])

    def test_backend_does_not_freshen_original_timestamp_before_arm(self):
        context = multiprocessing.get_context('spawn'); parent, child = context.Pipe()
        process = context.Process(target=delayed_backend, args=(child, {})); process.start(); child.close()
        try:
            while True:
                self.assertTrue(parent.poll(3)); response = parent.recv()
                if response['kind']=='state' and response['value']['state']=='READY': break
            issued = time.monotonic()-.2
            parent.send(dict(kind='jog', id='original', issued=issued, direction='right', step_us=5))
            deadline = time.monotonic()+3
            while time.monotonic()<deadline:
                if parent.poll(.2):
                    response = parent.recv()
                    if response['kind']=='state' and response['value']['history']:
                        row = response['value']['history'][-1]
                        self.assertEqual(row['source_time'], issued)
                        self.assertEqual(row['commands_accepted'], 0)
                        self.assertEqual(row['final_us'], 1430)
                        break
            else: self.fail('Missing cancelled-before-ARM history')
        finally:
            parent.send(dict(kind='close')); process.join(3); parent.close()
            if process.is_alive(): process.kill(); process.join()


class ReleaseGateTests(unittest.TestCase):
    def test_default_and_template_are_disabled_before_read_or_mmio(self):
        with patch('board.motion.manual_vsrv.Path') as paths:
            for config in [{}, {'enabled': False}, {'enabled': 'true'}]:
                with self.assertRaisesRegex(RuntimeError, '保持锁定'): load_release(config)
            paths.assert_not_called()

    def test_unqualified_manifest_rejected_before_payload_or_mmio(self):
        import hashlib, json, tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as temporary:
            p = Path(temporary)/'release.json'
            p.write_text(json.dumps(dict(schema_version=1, status='OFFLINE_ONLY')))
            config = dict(enabled=True, release_manifest=str(p),
                          release_manifest_sha256=hashlib.sha256(p.read_bytes()).hexdigest())
            with self.assertRaisesRegex(RuntimeError, 'not qualified'): load_release(config)

    def test_native_transport_on_host_does_not_load_library(self):
        from types import SimpleNamespace
        with patch('board.motion.vsrv_transport.os.uname', return_value=SimpleNamespace(machine='x86_64')):
            with patch('board.motion.vsrv_transport.ctypes.CDLL') as library:
                with self.assertRaises(RuntimeError): NativeRegisters('/unused', '0'*64, 'boot', {})
                library.assert_not_called()


if __name__ == '__main__': unittest.main()
