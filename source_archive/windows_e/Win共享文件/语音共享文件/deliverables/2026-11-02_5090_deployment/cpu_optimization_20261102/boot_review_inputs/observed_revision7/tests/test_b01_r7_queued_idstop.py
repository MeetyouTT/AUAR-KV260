"""Only R6 B01: queued own platform actions and bound IDSTOP observation.

All systemd, process, source and platform observations are synthetic.
"""
import copy
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'candidate'))
sys.path.insert(0, str(HERE / 'tests'))
import boot_recovery as runtime
import recovery_rules as rules
from test_boot_recovery import (BOOT, PREVIOUS, OWNER, checked_cleanup,
                                job_fixture, local_create, platform_fixture,
                                report_fixture)
from test_review_job_queue import PendingJobTests


def idstop_argv(tx):
    return ['/usr/bin/python3', '-B', (runtime.RELEASE / 'bench_identity_stop.py').as_posix(),
            '--execute', '--confirmation', 'ID_STOP_ONLY',
            '--manifest', (runtime.RELEASE / 'candidate-manifest.json').as_posix(),
            '--manifest-sha256', rules.MANIFEST_SHA,
            '--context', str(tx / 'wide-context.json'),
            '--output', str(tx / 'id-stop.json')]


class QueuedOwnActionTests(unittest.TestCase):
    quiet_with = PendingJobTests.quiet_with

    def test_queued_original_python_idstop_with_no_process_is_refused(self):
        name = 'aura-boot-wide-' + BOOT + '-idstop.service'
        entry = ' '.join(idstop_argv(Path('/public/transaction')))
        # The concrete missed case has neither a loader keyword in its unit
        # name nor a DFX/xmutil executable; it is still a platform action.
        self.assertNotIn('dfx', entry.lower())
        with self.assertRaisesRegex(rules.Hold, 'JOB_PENDING_NO_DFX'):
            self.quiet_with('61 ' + name + ' start waiting\n',
                            {name: dict(MainPID='0', ControlPID='0',
                                        ActiveState='inactive', SubState='dead',
                                        ExecStart=entry)})

    def test_all_own_actions_and_other_boot_jobs_are_refused(self):
        for boot, action in ((BOOT, 'list'), (BOOT, 'remove'), (BOOT, 'load'),
                             (PREVIOUS, 'idstop')):
            name = 'aura-boot-wide-' + boot + '-' + action + '.service'
            with self.subTest(boot=boot, action=action), \
                    self.assertRaisesRegex(rules.Hold, 'JOB_PENDING_NO_DFX'):
                self.quiet_with('62 ' + name + ' start waiting\n',
                                {name: dict(MainPID='0', ExecStart='/usr/bin/true')})

    def test_unrelated_queued_python_job_remains_allowed(self):
        self.quiet_with('63 harmless-python.service start waiting\n',
                        {'harmless-python.service': dict(MainPID='0',
                            ExecStart='/usr/bin/python3 -B /public/clock.py')})

    def test_owned_running_prepare_helper_remains_allowed(self):
        PendingJobTests.test_our_current_platform_helper_job_is_allowed(self)


class BoundIdstopObservationTests(unittest.TestCase):
    def setUp(self):
        (HERE / 'test_work').mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=HERE / 'test_work')
        self.addCleanup(checked_cleanup, self.temporary)
        self.r = object.__new__(runtime.Recovery)
        self.r.tx, self.r.boot, self.r.contract_sha = Path(self.temporary.name), BOOT, '7' * 64
        self.r.contract = dict(startup_path='/public/startup.json')
        self.startup = b'public synthetic startup'
        self.daemon = dict(OWNER, executable_sha256=rules.DAEMON_SHA)
        self.r.daemon_owner = Mock(return_value=self.daemon)
        self.r.source_snapshot = Mock(return_value={})
        # Exercise the actual once and observer methods, not a fake dispatch.
        self.r.once = types.MethodType(runtime.Recovery.once, self.r)
        self.unit_name = 'aura-boot-wide-' + BOOT + '-idstop.service'
        self.intent = dict(boot_id=BOOT, contract_sha256=self.r.contract_sha,
                           unit=self.unit_name, argv=idstop_argv(self.r.tx),
                           daemon=self.daemon, startup_sha256=rules.digest(self.startup))
        local_create(self.r.tx / 'idstop-intent.json', rules.encoded(self.intent))
        local_create(self.r.tx / 'idstop-invocation.json', rules.encoded({'InvocationID': 'a' * 32}))
        local_create(self.r.tx / 'idstop.stdout.raw', rules.encoded(dict(
            identity_stop_passed=True, motion_tested=False, report=str(self.r.tx / 'id-stop.json'))))
        local_create(self.r.tx / 'idstop.stderr.raw', b'')
        local_create(self.r.tx / 'id-stop.json', rules.encoded(report_fixture()))
        self.states = [job_fixture()]
        self.queries = []
        self.dispatch = Mock(side_effect=AssertionError('Observation must never dispatch a command'))
        for item in (patch.object(runtime, 'regular', self.read),
                     patch.object(runtime, 'create', local_create),
                     patch.object(runtime, 'unit', self.current),
                     patch.object(runtime, 'command', self.dispatch),
                     patch.object(runtime, 'platform_metadata', return_value=platform_fixture()),
                     patch.object(runtime.time, 'sleep')):
            item.start()
            self.addCleanup(item.stop)

    def read(self, path, limit=67108864):
        return self.startup if str(path) == self.r.contract['startup_path'] else Path(path).read_bytes()

    def current(self, name):
        self.assertEqual(name, self.unit_name)
        self.queries.append(name)
        return copy.deepcopy(self.states.pop(0) if len(self.states) > 1 else self.states[0])

    def test_bound_queued_idstop_completes_and_reentry_only_observes_same_job(self):
        queued = dict(LoadState='loaded', MainPID='0', ActiveState='inactive',
                      SubState='dead', Job='61', InvocationID='')
        self.states = [queued, job_fixture()]
        before = {p.name: p.read_bytes() for p in self.r.tx.iterdir()}
        for _ in range(2):
            result = self.r.observe_job('idstop')
            self.assertEqual(result['status'], 'EXISTING_ORIGINAL_JOB_OBSERVED_NO_SUBMISSION')
            self.assertEqual(result['InvocationID'], 'a' * 32)
        self.assertEqual(self.queries, [self.unit_name] * 3)
        self.assertEqual({p.name: p.read_bytes() for p in self.r.tx.iterdir()}, before)
        self.dispatch.assert_not_called()

    def test_replaced_invocation_is_refused_without_resubmission(self):
        self.states = [dict(job_fixture(), InvocationID='b' * 32)]
        with self.assertRaisesRegex(rules.Hold, 'OS_JOB_REPLACED'):
            self.r.observe_job('idstop')
        self.assertEqual(json.loads((self.r.tx / 'idstop-invocation.json').read_bytes()),
                         {'InvocationID': 'a' * 32})
        self.dispatch.assert_not_called()

    def test_different_bound_unit_is_refused_before_os_observation(self):
        changed = dict(self.intent, unit='aura-boot-wide-' + PREVIOUS + '-idstop.service')
        (self.r.tx / 'idstop-intent.json').write_bytes(rules.encoded(changed))
        with self.assertRaisesRegex(rules.Hold, 'INTENT_CONTEXT_CHANGED'):
            self.r.observe_job('idstop')
        self.assertEqual(self.queries, [])
        self.dispatch.assert_not_called()

    def test_missing_intent_cannot_create_or_submit_a_job(self):
        (self.r.tx / 'idstop-intent.json').unlink()
        with self.assertRaisesRegex(rules.Hold, 'NO_EXISTING_JOB_TO_OBSERVE'):
            self.r.observe_job('idstop')
        self.assertEqual(self.queries, [])
        self.assertFalse((self.r.tx / 'idstop-intent.json').exists())
        self.dispatch.assert_not_called()


if __name__ == '__main__':
    unittest.main(verbosity=2)
