"""Fault-state and rollback ownership checks without hardware access."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import edid_trial as trial


class TrialGuards(unittest.TestCase):
    def setUp(self):
        self.expected = {'boot': 'measured-boot', 'gui': 10, 'x': 11}
        self.state = {'boot': 'measured-boot',
                      'owners': {'gui': {'pid': 10, 'birth': 100, 'state': 'active'},
                                 'x': {'pid': 11, 'birth': 101, 'state': 'active'}},
                      'override_hex': '', 'edid_bytes': 0, 'force': 'unspecified',
                      'display_on': True, 'mode_ok': True, 'ui_idle': True,
                      'saver': [600, 600], 'dpms': [600, 600, 600], 'dpms_enabled': True}

    def test_measured_reference(self):
        blob = Path(__file__).with_name('screen_verified_727d3e18.edid').read_bytes()
        self.assertEqual(blob, trial.REFERENCE)
        trial.validate_reference(blob)

    def test_corrupted_or_different_reference_rejected(self):
        for raw in (trial.REFERENCE[:-1], bytes(128), trial.REFERENCE[:-1] + b'\0'):
            with self.subTest(length=len(raw)), self.assertRaises(ValueError):
                trial.validate_reference(raw)

    def test_expected_fault_state_is_accepted(self):
        trial.validate_before(self.state, self.expected)

    def test_stale_boot_or_owner_rejected(self):
        for key, value in (('boot', 'old-boot'), ('gui', 99), ('x', 99)):
            expected = dict(self.expected, **{key: value})
            with self.subTest(key=key), self.assertRaises(ValueError):
                trial.validate_before(self.state, expected)

    def test_normal_sleeping_busy_or_overridden_display_rejected(self):
        for key, value in (('edid_bytes', 128), ('override_hex', trial.REFERENCE.hex()),
                           ('display_on', False), ('mode_ok', False), ('ui_idle', False),
                           ('force', 'on'), ('saver', None), ('dpms', None)):
            state = copy.deepcopy(self.state)
            state[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                trial.validate_before(state, self.expected)

    def test_rollback_only_owns_its_reference(self):
        self.assertEqual(trial.restoration_decision('a', 'a', trial.REFERENCE), 'clear_own_override')
        self.assertEqual(trial.restoration_decision('a', 'a', b''), 'already_clear')
        with self.assertRaises(ValueError):
            trial.restoration_decision('a', 'a', bytes(128))

    def test_rollback_does_not_write_new_boot(self):
        self.assertEqual(trial.restoration_decision('b', 'a', bytes(128)), 'new_boot_no_writes')

    def test_normal_display_has_no_transaction_or_commands(self):
        state = copy.deepcopy(self.state)
        state['edid_bytes'] = 128
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.object(trial, 'ROOT', root), patch.object(trial, 'snapshot', return_value=state), patch.object(trial, 'run') as command:
                with self.assertRaises(ValueError):
                    trial.apply_trial(self.expected)
                command.assert_not_called()
                self.assertEqual(list(root.iterdir()), [])

    def exercise_transaction(self, fail_off):
        class Override:
            value = b''
            def read_bytes(self):
                return self.value
            def open(self, *args, **kwargs):
                return self
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def write(self, data):
                self.value = b'' if data == b'reset' else data
                return len(data)

        override = Override()
        calls = []
        before = copy.deepcopy(self.state)
        before['boot'] = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
        expected = dict(self.expected, boot=before['boot'])
        after = copy.deepcopy(before)
        after['override_hex'] = trial.REFERENCE.hex()
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / 'transactions'
            root.mkdir()
            connector = base / 'connector'
            connector.mkdir()
            (connector / 'edid').write_bytes(b'')
            state = base / 'state'
            on = trial.TIMING + '\n\tactive=1\n'
            state.write_text(on)

            def command(args, timeout=15):
                calls.append(list(args))
                if args[0] == 'xrandr':
                    if '--off' in args:
                        state.write_text('\n\tactive=0\n')
                        if fail_off:
                            raise RuntimeError('simulated lost modeset acknowledgement')
                    else:
                        state.write_text(on)
                return ''

            with patch.object(trial, 'ROOT', root), patch.object(trial, 'OVERRIDE', override), patch.object(trial, 'CONNECTOR', connector), patch.object(trial, 'STATE', state), patch.object(trial, 'snapshot', side_effect=[before, after]), patch.object(trial, 'identity', return_value=before['owners']['x']), patch.object(trial, 'run', side_effect=command), patch.object(trial.time, 'sleep'):
                if fail_off:
                    with self.assertRaisesRegex(RuntimeError, 'lost modeset'):
                        trial.apply_trial(expected)
                    transaction = next(root.iterdir())
                    report = json.loads((transaction / 'failed.json').read_text())
                    self.assertTrue(report['rollback']['restored'])
                else:
                    report = trial.apply_trial(expected)
                    self.assertTrue(report['software_verified'])
                    self.assertFalse(report['physical_panel_verified'])
                    self.assertEqual(override.value, trial.REFERENCE)
                    transaction = Path(report['transaction'])
                    restored = trial.restore(transaction)
                    self.assertTrue(restored['restored'])
                    self.assertTrue(restored['idle_policy_restored'])
                self.assertEqual(override.value, b'')
                self.assertEqual(state.read_text(), on)
                self.assertEqual(calls[0][0], 'systemd-run')
                self.assertIn('--on-active=180s', calls[0])
                self.assertIn(['xset', 's', '600', '600'], calls)
                self.assertIn(['xset', 'dpms', '600', '600', '600'], calls)
                self.assertIn(['xset', '+dpms'], calls)

    def test_mid_modeset_failure_restores_reference_mode_and_policy(self):
        self.exercise_transaction(True)

    def test_success_is_not_visual_verification_and_can_rollback(self):
        self.exercise_transaction(False)


if __name__ == '__main__':
    unittest.main()
