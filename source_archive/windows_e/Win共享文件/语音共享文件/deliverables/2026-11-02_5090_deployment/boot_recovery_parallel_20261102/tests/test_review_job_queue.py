"""Targeted independent-review queue gaps. No real systemd or /proc inspection."""
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'candidate'))
import boot_recovery as runtime
import recovery_rules as rules


class EmptyProc:
    def iterdir(self):
        return []


class PendingJobTests(unittest.TestCase):
    def quiet_with(self, rows, extra):
        idle = dict(MainPID='0', ControlPID='0', ActiveState='inactive', SubState='dead', Job='')
        def current(name):
            return idle if name in {rules.CAMERA, rules.GUI} else extra.get(name, dict(ExecStart='/usr/bin/date'))
        reply = subprocess.CompletedProcess([], 0, rows.encode(), b'')
        with patch.object(runtime, 'unit', side_effect=current), patch.object(runtime, 'command', return_value=reply), \
                patch.object(runtime, 'Path', return_value=EmptyProc()), \
                patch.object(runtime, 'owner_scan', return_value=dict(complete=True, owners=[], unreadable=[])):
            object.__new__(runtime.Recovery).quiet()

    def test_queued_arbitrarily_named_dfx_load_with_no_process_is_refused(self):
        with self.assertRaisesRegex(rules.Hold, 'JOB_PENDING_NO_DFX'):
            self.quiet_with('55 delayed-worker.service start waiting\n',
                            {'delayed-worker.service': dict(ExecStart='/usr/bin/dfx-mgr-client -load ' + rules.APP, MainPID='0')})

    def test_queued_remove_in_start_pre_is_refused(self):
        with self.assertRaisesRegex(rules.Hold, 'JOB_PENDING_NO_DFX'):
            self.quiet_with('56 maintenance-worker.service start waiting\n',
                            {'maintenance-worker.service': dict(ExecStart='/usr/bin/true', ExecStartPre='/usr/bin/dfx-mgr-client -remove 0', MainPID='0')})

    def test_daemon_stop_or_restart_job_is_refused(self):
        for action in ('stop', 'restart'):
            with self.subTest(action=action), self.assertRaisesRegex(rules.Hold, 'JOB_PENDING_NO_DFX'):
                self.quiet_with('57 dfx-mgr.service ' + action + ' waiting\n',
                                {'dfx-mgr.service': dict(MainPID='900', ActiveState='active', ExecStart='/original/dfx-mgrd')})

    def test_direct_daemon_owner_check_refuses_job_before_reading_process(self):
        props = dict(ActiveState='active', SubState='running', MainPID='900', Job='57')
        with patch.object(runtime, 'unit', return_value=props), patch.object(runtime, 'process') as process:
            with self.assertRaisesRegex(rules.Hold, 'DAEMON_JOB_PENDING'):
                object.__new__(runtime.Recovery).daemon_owner()
            process.assert_not_called()

    def test_unrelated_job_does_not_force_a_blanket_boot_hold(self):
        self.quiet_with('58 harmless-monitor.service start waiting\n', {})

    def test_our_current_platform_helper_job_is_allowed(self):
        self.quiet_with('59 aura-original-wide-prepare.service start running\n',
                        {'aura-original-wide-prepare.service': dict(MainPID=str(os.getpid()))})

    def test_a_different_platform_helper_cannot_be_treated_as_ours(self):
        with self.assertRaisesRegex(rules.Hold, 'ANOTHER_PLATFORM_PREPARE'):
            self.quiet_with('59 aura-original-wide-prepare.service start waiting\n',
                            {'aura-original-wide-prepare.service': dict(MainPID='0')})

    def test_unknown_job_queue_format_stops_before_any_proc_scan(self):
        with self.assertRaisesRegex(rules.Hold, 'QUEUE_SHAPE_UNKNOWN'):
            self.quiet_with('unparsed queue output\n', {})

    def test_new_camera_job_appearing_after_unit_snapshot_is_not_silently_skipped(self):
        with self.assertRaisesRegex(rules.Hold, 'SERVICE_JOB_CHANGED'):
            self.quiet_with('60 ' + rules.CAMERA + ' start waiting\n', {})


if __name__ == '__main__':
    unittest.main(verbosity=2)
