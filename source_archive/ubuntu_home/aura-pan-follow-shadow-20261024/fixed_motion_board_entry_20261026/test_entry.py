import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import board_fixed_cli as entry
from reference_receipt import validate_receipt, same_stopped_readback


def receipt():
    return dict(schema='aura-user-observed-fixed-reference-1', boot_id='current', fdt_sha256='current-fdt',
                user_present=True, confirmed_current_position=True, user_observation='fixture observation',
                reference_us=1420, bounds_us=[1402, 1420], polarity=1, camera_moves_with_axis=True,
                authorization_id='fixture-1', observed_mono_s=10., expires_mono_s=610.,
                stopped_readback=dict(flags=0, lease_left_ms=0, width_us=1420, target_us=1420,
                                      reference_us=1420, session=1, epoch=2, ack_seq=3, reason=0))


class ReceiptTests(unittest.TestCase):
    def check(self, value):
        return validate_receipt(value, boot_id='current', fdt_sha256='current-fdt', now=20.)

    def test_current_observed_reference_is_accepted(self):
        self.assertEqual(self.check(receipt())['reference_us'], 1420)

    def test_old_boot_absence_or_missing_observation_are_rejected(self):
        for key, value in [('boot_id', 'old'), ('fdt_sha256', 'old'), ('user_present', False),
                           ('confirmed_current_position', False), ('user_observation', '')]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.check(dict(receipt(), **{key: value}))

    def test_default_register_width_does_not_establish_physical_reference(self):
        r = receipt()
        r['stopped_readback'].update(width_us=1500, target_us=1500)
        with self.assertRaisesRegex(ValueError, 'STOPPED_REFERENCE'):
            self.check(r)

    def test_extended_window_expired_future_or_nonfinite_times_rejected(self):
        for key, value in [('bounds_us', [1400, 1600]), ('reference_us', 1500),
                           ('observed_mono_s', 21.), ('expires_mono_s', 22.),
                           ('expires_mono_s', float('inf')), ('expires_mono_s', 611.)]:
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                self.check(dict(receipt(), **{key: value}))

    def test_path_injection_and_active_state_rejected(self):
        for bad in ('../replace', 'a/b', '', 'a' * 65):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                self.check(dict(receipt(), authorization_id=bad))
        r = receipt()
        r['stopped_readback']['flags'] = 15
        with self.assertRaises(ValueError):
            self.check(r)

    def test_changed_register_epoch_is_not_same_reference_receipt(self):
        r = receipt()
        self.assertTrue(same_stopped_readback(r, dict(r['stopped_readback'])))
        self.assertFalse(same_stopped_readback(r, dict(r['stopped_readback'], epoch=3)))


class EntryTests(unittest.TestCase):
    def test_default_is_host_plan_without_board_preflight(self):
        with patch.object(sys, 'argv', ['entry']), patch.object(entry, 'preflight') as pre, contextlib.redirect_stdout(io.StringIO()) as out:
            entry.main()
        pre.assert_not_called()
        self.assertEqual(json.loads(out.getvalue())['mode'], 'PLAN_ONLY')

    def test_check_with_missing_reference_does_not_open_registers(self):
        with tempfile.TemporaryDirectory() as d, patch.object(entry, 'R', Path(d)), patch.object(entry, 'preflight', return_value=({}, {})), patch.object(sys, 'argv', ['entry', '--check']), contextlib.redirect_stdout(io.StringIO()) as out:
            entry.main()
        self.assertFalse(json.loads(out.getvalue())['MMIO_opened'])

    def test_execute_with_missing_reference_refuses_before_driver_import(self):
        before = set(sys.modules)
        with tempfile.TemporaryDirectory() as d, patch.object(entry, 'R', Path(d)), patch.object(entry, 'preflight', return_value=({}, {})), patch.object(sys, 'argv', ['entry', '--execute']), self.assertRaisesRegex(RuntimeError, 'CURRENT_USER_REFERENCE_MISSING_NO_MMIO'):
            entry.main()
        self.assertFalse({'batch_transport', 'fixed_bench_adapter'} & (set(sys.modules) - before))

    def test_check_and_execute_are_mutually_exclusive(self):
        with patch.object(sys, 'argv', ['entry', '--check', '--execute']), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            entry.main()
        self.assertEqual(error.exception.code, 2)


if __name__ == '__main__':
    unittest.main()
