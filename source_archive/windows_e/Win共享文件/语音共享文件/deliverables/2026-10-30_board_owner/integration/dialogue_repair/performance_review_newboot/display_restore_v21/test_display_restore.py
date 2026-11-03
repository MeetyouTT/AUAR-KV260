"""Public deterministic tests, with no X server, microphone, SSH, or production reads."""
import copy
import json
from pathlib import Path
import types
import unittest
from unittest.mock import patch

import display_restore as subject
import run_display_restore as runner


class Clock:
    def __init__(self):
        self.now = 1000.

    def read(self):
        return self.now

    def sleep(self, delay):
        self.now += delay


class FakeX:
    def __init__(self, clock, tick=True):
        self.clock = clock
        self.tick = tick
        self.values = dict(subject.TEMPORARY)
        self.enabled = False
        self.writes = []
        self.wakes = 0
        self.fail_write = False

    def query(self):
        elapsed = self.clock.read() - 1000
        idle = int((elapsed % 5 if self.tick else elapsed) * 1000)
        return dict(screen_saver=dict(self.values), dpms_enabled=self.enabled,
            dpms_level=0, dpms_timeouts=[600, 600, 600], xss_idle_ms=idle, xss_state=0, xss_kind=0)

    def set_policy(self, values, enabled):
        self.writes.append((dict(values), enabled))
        self.values, self.enabled = dict(values), enabled
        if self.fail_write and enabled:
            raise subject.Refused('DPMS_POLICY_WRITE_FAILED')

    def wake_for_failure(self):
        self.wakes += 1


def live():
    return dict(enabled=False, state='PAUSED', microphone_open=False, playing=False, native_frames=123)


class ObservationTests(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.x = FakeX(self.clock)
        self.snapshots = []

    def run_probe(self, guard=live, finish=None):
        return subject.observe(self.x, guard, lambda value: self.snapshots.append(copy.deepcopy(value)),
            {}, finish, self.clock.read, self.clock.sleep)

    def test_original_policy_restored_without_observer_reset(self):
        result = self.run_probe()
        self.assertEqual(result['status'], 'ORIGINAL_POLICY_RESTORED_PAUSED_IDLE_OBSERVED')
        self.assertEqual(len(result['samples']), 31)
        self.assertEqual(result['idle_drop_times_seconds'], [5., 10., 15., 20., 25., 30.])
        self.assertEqual(self.x.writes, [(subject.ORIGINAL, True)])
        self.assertEqual(self.x.wakes, 0)
        self.assertTrue(result['external_input_not_excluded'])

    def test_intent_is_saved_before_any_policy_write(self):
        called = []
        def save(value):
            called.append(value['status'])
            if value['status'] == 'RESTORE_INTENT_SAVED':
                self.assertFalse(self.x.writes)
        subject.observe(self.x, live, save, {}, clock=self.clock.read, sleep=self.clock.sleep)
        self.assertEqual(called[0], 'RESTORE_INTENT_SAVED')

    def test_missing_tick_falls_back_at_eight_seconds(self):
        self.x.tick = False
        result = self.run_probe()
        self.assertEqual(result['failure']['code'], 'PAUSED_IDLE_EXCEEDED_7500_MS')
        self.assertEqual(result['fallback'], 'TEMPORARY_RESTORED_SAME_PAUSED_OWNER')
        self.assertEqual(self.clock.read(), 1008.)
        self.assertEqual(self.x.writes[-1], (subject.TEMPORARY, False))
        self.assertEqual(self.x.wakes, 1)

    def test_partial_restore_error_falls_back(self):
        self.x.fail_write = True
        result = self.run_probe()
        self.assertEqual(result['policy_left'], 'TEMPORARY')
        self.assertEqual(len(result['samples']), 0)
        self.assertEqual(len(self.x.writes), 2)

    def test_owner_change_prevents_fallback_write(self):
        def guard():
            if self.clock.read() >= 1002.:
                raise subject.Refused('LIVE_OWNER_CHANGED')
            return live()
        result = self.run_probe(guard)
        self.assertEqual(result['fallback'], 'REFUSED_OR_FAILED')
        self.assertEqual(result['fallback_failure']['code'], 'LIVE_OWNER_CHANGED')
        self.assertEqual(self.x.writes, [(subject.ORIGINAL, True)])
        self.assertEqual(self.x.wakes, 0)

    def test_pause_change_prevents_fallback_write(self):
        def guard():
            if self.clock.read() >= 1001.:
                raise subject.Refused('LIVE_PAUSE_CHANGED')
            return live()
        result = self.run_probe(guard)
        self.assertEqual(result['fallback_failure']['code'], 'LIVE_PAUSE_CHANGED')
        self.assertEqual(len(self.x.writes), 1)

    def test_deadline_falls_back(self):
        def guard():
            if self.x.enabled:
                self.clock.now += 41.
            return live()
        result = self.run_probe(guard)
        self.assertEqual(result['status'], 'RESTORE_OR_OBSERVATION_FAILED')
        self.assertEqual(result['policy_left'], 'TEMPORARY')

    def test_original_policy_failure_never_exports_exception_text(self):
        def finish():
            raise ValueError('private payload must stay private')
        result = self.run_probe(finish=finish)
        self.assertEqual(result['failure'], dict(code='TOOL_OR_GUARD_FAILURE', exception_class='ValueError'))
        self.assertNotIn('private payload', json.dumps(result))
        self.assertEqual(result['policy_left'], 'TEMPORARY')

    def test_save_intent_failure_does_not_restore(self):
        def fail(value):
            raise OSError('synthetic full filesystem')
        with self.assertRaises(OSError):
            subject.observe(self.x, live, fail, {}, clock=self.clock.read, sleep=self.clock.sleep)
        self.assertEqual(self.x.writes, [])

    def test_write_receipt_failure_after_restore_attempts_safe_fallback(self):
        count = 0
        def fail_second(value):
            nonlocal count
            count += 1
            if count == 2:
                raise OSError('synthetic full filesystem')
        result = subject.observe(self.x, live, fail_second, {}, clock=self.clock.read, sleep=self.clock.sleep)
        self.assertEqual(result['policy_left'], 'TEMPORARY')

    def test_constant_low_idle_does_not_claim_observed_resets(self):
        original = self.x.query
        def constant():
            return dict(original(), xss_idle_ms=0)
        self.x.query = constant
        result = self.run_probe()
        self.assertEqual(result['failure']['code'], 'INSUFFICIENT_PASSIVE_IDLE_RESETS')

    def test_all_samples_are_numeric_enum_metadata(self):
        result = self.run_probe()
        self.assertEqual(set(result['samples'][0]), {'elapsed_seconds', 'screen_saver', 'dpms_enabled',
            'dpms_level', 'dpms_timeouts', 'xss_idle_ms', 'xss_state', 'xss_kind', 'enabled', 'state',
            'microphone_open', 'playing', 'native_frames'})


class FakeFunction:
    def __init__(self, result=1):
        self.result = result
        self.calls = []

    def __call__(self, *arguments):
        self.calls.append(arguments)
        return self.result


class SymbolPreflightTests(unittest.TestCase):
    def libraries(self):
        x = types.SimpleNamespace(**{name: FakeFunction() for name in ('XGetScreenSaver', 'XSetScreenSaver',
            'XDefaultRootWindow', 'XSync', 'XOpenDisplay', 'XCloseDisplay')})
        ext = types.SimpleNamespace(**{name: FakeFunction() for name in ('DPMSCapable', 'DPMSInfo',
            'DPMSGetTimeouts', 'DPMSEnable', 'DPMSDisable', 'DPMSForceLevel')})
        xss = types.SimpleNamespace(XScreenSaverQueryExtension=FakeFunction(), XScreenSaverQueryInfo=FakeFunction())
        return x, ext, xss

    def test_missing_required_symbol_refuses_before_connection(self):
        x, ext, xss = self.libraries()
        del ext.DPMSEnable
        with self.assertRaises(AttributeError):
            subject.XSession(types.SimpleNamespace(_display_libraries=lambda: (x, ext)), lambda: xss)
        self.assertEqual(x.XOpenDisplay.calls, [])
        self.assertEqual(x.XSetScreenSaver.calls, [])

    def test_missing_xss_refuses_without_mutation(self):
        x, ext, xss = self.libraries()
        def missing():
            raise OSError('synthetic unavailable lib')
        with self.assertRaises(OSError):
            subject.XSession(types.SimpleNamespace(_display_libraries=lambda: (x, ext)), missing)
        self.assertFalse(x.XOpenDisplay.calls)
        self.assertFalse(x.XSetScreenSaver.calls)

    def test_unavailable_x_connection_does_not_change_policy(self):
        x, ext, xss = self.libraries()
        x.XOpenDisplay.result = None
        with self.assertRaisesRegex(subject.Refused, '^X11_CONNECTION_UNAVAILABLE$'):
            subject.XSession(types.SimpleNamespace(_display_libraries=lambda: (x, ext)), lambda: xss)
        self.assertFalse(x.XSetScreenSaver.calls)

    def test_missing_extension_closes_without_mutation(self):
        x, ext, xss = self.libraries()
        xss.XScreenSaverQueryExtension.result = 0
        with self.assertRaisesRegex(subject.Refused, '^XSS_EXTENSION_UNAVAILABLE$'):
            subject.XSession(types.SimpleNamespace(_display_libraries=lambda: (x, ext)), lambda: xss)
        self.assertEqual(len(x.XCloseDisplay.calls), 1)
        self.assertFalse(x.XSetScreenSaver.calls)


class PolicyTests(unittest.TestCase):
    def original(self):
        return dict(boot_id=subject.BOOT, owner='root-v21-display-publication', phase='ORIGINAL_POLICY_SAVED',
            original_screen_saver=subject.ORIGINAL, dpms_capable=True, dpms_originally_enabled=True, saved_mono=1.)

    def test_exact_original_record(self):
        value = self.original()
        self.assertEqual(subject.policy(json.dumps(value).encode()), value)

    def test_original_dpms_state_must_be_true(self):
        value = dict(self.original(), dpms_originally_enabled=False)
        with self.assertRaises(subject.Refused):
            subject.policy(json.dumps(value).encode())

    def test_unknown_saved_field_rejected(self):
        with self.assertRaises(subject.Refused):
            subject.policy(json.dumps(dict(self.original(), arbitrary='private')).encode())

    def test_bool_policy_integer_is_rejected(self):
        value = dict(self.original(), original_screen_saver=dict(subject.ORIGINAL, prefer_blank=True))
        with self.assertRaises(subject.Refused):
            subject.policy(json.dumps(value).encode())

    def test_remote_has_finite_alarm_and_no_model_or_microphone_commands(self):
        source = runner.build_remote()
        self.assertIn('signal.alarm(90)', source)
        self.assertNotIn('subprocess.Popen', source)
        self.assertNotIn("request('POST'", source)
        self.assertNotIn('DPMSSetTimeouts', source)

    def test_actual_sealed_inputs_validate_locally(self):
        common, arguments = runner.local_inputs(runner.EVIDENCE / 'spec.json', runner.SPEC_SHA,
                                                runner.EVIDENCE / 'ready.json', runner.READY_SHA)
        self.assertEqual(arguments['spec']['component_pins'], 380)
        self.assertEqual(arguments['baseline_owners']['gtk']['pid'], 171274)
        self.assertEqual(arguments['baseline_owners']['supervisor']['pid'], 171266)

    def test_other_spec_sha_rejected_before_loading_any_source(self):
        with self.assertRaisesRegex(subject.Refused, '^ACTUAL_SEALED_V21_INPUTS_REQUIRED$'):
            runner.local_inputs(Path('absent'), '0' * 64, Path('absent'), runner.READY_SHA)

    def test_current_idle_is_not_compared_with_stale_preflight_idle(self):
        # Reading Xss does not freeze its timer. Only the four stable policy fields match.
        source = Path(subject.__file__).read_text('utf-8')
        self.assertNotIn("previous.get('x') == current", source)
        self.assertIn("('screen_saver', 'dpms_enabled', 'dpms_level', 'dpms_timeouts')", source)


if __name__ == '__main__':
    unittest.main(verbosity=2)
