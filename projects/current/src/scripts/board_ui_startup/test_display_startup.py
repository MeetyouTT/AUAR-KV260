"""Cold-start ordering and bounded recovery; all display commands are fixtures."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import launcher
import test_display_fallback as fallback


class ColdStartupTests(fallback.DisplayFallbackTests):
    # Reuse the five protection regressions with recovery enabled as well.
    def setUp(self):
        super().setUp()
        self.clock = [0.0]
        self.patch_clock = patch.object(launcher.time, 'monotonic', lambda: self.clock[0])
        self.patch_clock.start(); self.addCleanup(self.patch_clock.stop)
        self.wait.stop()
        self.patch_wait = patch.object(launcher.STOP, 'wait', self.advance)
        self.patch_wait.start(); self.addCleanup(self.patch_wait.stop)
        self.config.update(display_wait_seconds=30, edid_grace_seconds=5,
                           display_stable_seconds=2, startup_display_retrain=True,
                           display_retrain_off_seconds=1,
                           display_recovery_marker=str(self.edid.with_name('marker.json')))
        self.boot = 'first-boot'
        self.patch_boot = patch.object(launcher, 'display_boot_id', lambda: self.boot)
        self.patch_boot.start(); self.addCleanup(self.patch_boot.stop)
        self.on_wait = None
        self.fail_enable_once = False
        self.fail_enable_always = False
        self.stop_during_off = False

    def advance(self, seconds):
        self.clock[0] += seconds
        if self.on_wait:
            self.on_wait()
        if self.stop_during_off and self.calls[-1] == ['xrandr', '--output', 'DP-1', '--off']:
            launcher.STOP.set()

    def run_command(self, args, env):
        result = super().run_command(args, env)
        if '--mode' in args and (self.fail_enable_once or self.fail_enable_always):
            self.fail_enable_once = False
            raise RuntimeError('fixture transient enable failure')
        return result

    def off_count(self):
        return self.calls.count(['xrandr', '--output', 'DP-1', '--off'])

    def test_late_edid_wins_before_fallback_and_waits_until_stable(self):
        def appear():
            if self.clock[0] >= 3:
                self.edid.write_bytes(b'original-edid')
                self.modes = 'DP-1 connected primary 1024x768+0+0\n' + fallback.MODE
        self.on_wait = appear
        setup = launcher.configure_display(self.config, {})
        self.assertEqual(setup['mode_source'], 'live_edid')
        self.assertGreaterEqual(self.clock[0], 6)  # live at 3, stable 2, output-off 1
        self.assertFalse(any('--newmode' in c for c in self.calls))
        self.assertEqual(self.off_count(), 1)

    def test_missing_edid_waits_grace_then_cycles_only_verified_output(self):
        setup = launcher.configure_display(self.config, {})
        self.assertGreaterEqual(self.clock[0], 8)
        self.assertTrue(setup['startup_output_retrained'])
        self.assertFalse(setup['physical_panel_verified'])
        self.assertEqual(self.off_count(), 1)
        self.assertTrue(all(c[c.index('--output')+1] == 'DP-1' for c in self.calls if '--output' in c))

    def test_same_boot_service_restart_does_not_cycle_again(self):
        launcher.configure_display(self.config, {})
        self.calls.clear()
        setup = launcher.configure_display(self.config, {})
        self.assertFalse(setup['startup_output_retrained'])
        self.assertEqual(self.off_count(), 0)

    def test_new_boot_invalidates_old_marker(self):
        launcher.configure_display(self.config, {})
        self.boot = 'second-boot'; self.calls.clear()
        launcher.configure_display(self.config, {})
        self.assertEqual(self.off_count(), 1)
        self.assertEqual(json.loads(Path(self.config['display_recovery_marker']).read_text())['boot_id'], self.boot)

    def test_transient_restore_failure_cannot_repeat_output_off(self):
        self.fail_enable_once = True
        launcher.configure_display(self.config, {})
        self.assertEqual(self.off_count(), 1)
        self.assertGreaterEqual(sum('--mode' in c for c in self.calls), 2)

    def test_cancel_during_off_still_restores_without_success_marker(self):
        self.stop_during_off = True
        try:
            with self.assertRaises(RuntimeError):
                launcher.configure_display(self.config, {})
            self.assertEqual(self.off_count(), 1)
            self.assertTrue(any('--mode' in c for c in self.calls))
            marker=json.loads(Path(self.config['display_recovery_marker']).read_text())
            self.assertFalse(marker['software_modeset_verified'])
        finally:
            launcher.STOP.clear()

    def test_failed_startup_cannot_cycle_again_on_service_retry(self):
        self.fail_enable_always = True
        with self.assertRaises(RuntimeError):
            launcher.configure_display(self.config, {})
        self.assertEqual(self.off_count(), 1)
        self.fail_enable_always = False; self.calls.clear()
        launcher.configure_display(self.config, {})
        self.assertEqual(self.off_count(), 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
