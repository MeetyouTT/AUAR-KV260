"""Failure injection for reset reporting; no real X server or board access."""
import json
from pathlib import Path
import subprocess
import unittest

import launcher
import test_display_startup as cold
from unittest.mock import patch


class RetrainResultTests(cold.ColdStartupTests):
    def setUp(self):
        super().setUp()
        self.fail_off = None
        self.fail_readback_once = False
        self.fail_marker = False

    def run_command(self, args, env):
        result = super().run_command(args, env)
        if '--off' in args and self.fail_off:
            raise self.fail_off
        if '--current' in args and self.fail_readback_once:
            self.fail_readback_once = False
            return 'DP-1 connected primary 1024x768+0+0\n'
        return result

    def marker(self):
        return json.loads(Path(self.config['display_recovery_marker']).read_text())

    def test_off_failure_never_becomes_a_successful_retrain(self):
        self.fail_off = RuntimeError('fixture output-off failure')
        setup = launcher.configure_display(self.config, {})
        self.assertFalse(setup['startup_output_retrained'])
        self.assertTrue(setup['startup_retrain_attempted'])
        self.assertFalse(self.marker()['retrain']['completed'])
        self.assertFalse(self.marker()['retrain']['off_succeeded'])
        self.assertTrue(self.marker()['retrain']['restore_succeeded'])
        self.assertTrue(self.marker()['software_modeset_verified'])
        self.assertIn('output-off', self.marker()['retrain']['error'])
        self.assertEqual(self.off_count(), 1)
        self.calls.clear()
        retry = launcher.configure_display(self.config, {})
        self.assertFalse(retry['startup_retrain_attempted'])
        self.assertFalse(retry['retrain']['completed'])
        self.assertEqual(self.off_count(), 0)

    def test_timeout_off_always_attempts_restore_and_reports_incomplete(self):
        self.fail_off = subprocess.TimeoutExpired('xrandr', 8)
        setup = launcher.configure_display(self.config, {})
        self.assertFalse(setup['startup_output_retrained'])
        self.assertTrue(any('--mode' in c for c in self.calls))
        self.assertEqual(self.off_count(), 1)

    def test_cancelled_wait_cannot_mark_full_reset_completed(self):
        self.stop_during_off = True
        try:
            with self.assertRaises(RuntimeError):
                launcher.configure_display(self.config, {})
            state = self.marker()['retrain']
            self.assertTrue(state['off_succeeded'])
            self.assertFalse(state['off_wait_completed'])
            self.assertTrue(state['restore_succeeded'])
            self.assertFalse(state['completed'])
        finally:
            launcher.STOP.clear()

    def test_transient_restore_failure_keeps_phase_evidence(self):
        self.fail_enable_once = True
        setup = launcher.configure_display(self.config, {})
        self.assertTrue(setup['startup_output_retrained'])
        self.assertTrue(self.marker()['retrain']['off_wait_completed'])
        self.assertIn('output-restore', self.marker()['retrain']['error'])
        self.assertEqual(self.off_count(), 1)

    def test_readback_retry_never_sends_a_second_off(self):
        self.fail_readback_once = True
        setup = launcher.configure_display(self.config, {})
        self.assertTrue(setup['startup_output_retrained'])
        self.assertEqual(self.off_count(), 1)

    def test_legacy_marker_is_not_proof_of_complete_reset(self):
        path = Path(self.config['display_recovery_marker'])
        path.write_text(json.dumps({'boot_id':self.boot, 'output':'DP-1',
            'mode':'1024x600', 'edid_sha256':self.config['edid_sha256'],
            'software_modeset_verified':True}))
        setup = launcher.configure_display(self.config, {})
        self.assertFalse(setup['startup_output_retrained'])
        self.assertTrue(setup['retrain']['legacy_result_unknown'])
        self.assertFalse(setup['retrain']['completed'])
        self.assertEqual(self.off_count(), 0)

    def test_success_marker_keeps_all_three_phases_and_no_physical_claim(self):
        setup = launcher.configure_display(self.config, {})
        self.assertTrue(setup['startup_output_retrained'])
        for key in ('attempted','off_succeeded','off_wait_completed','restore_succeeded','completed'):
            self.assertTrue(self.marker()['retrain'][key], key)
        self.assertFalse(self.marker()['physical_panel_verified'])

    def test_marker_write_failure_prevents_output_off(self):
        with patch.object(launcher, 'atomic_json', side_effect=OSError('fixture read-only')):
            with self.assertRaises(RuntimeError):
                launcher.configure_display(self.config, {})
        self.assertEqual(self.off_count(), 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
