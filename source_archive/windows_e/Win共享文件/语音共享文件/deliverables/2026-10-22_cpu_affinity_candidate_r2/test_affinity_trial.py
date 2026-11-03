"""No devices: simulated OS failures and affinity in an owned short child only."""
import ast
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from affinity_camera_launcher import CAMERA_SHA, ROLE_SOURCES, launch, target_matches
from thread_affinity_trial import AffinityTrial, checked_policy, current_identity

ROLES = ('camera-detection', 'camera-face-targets', 'camera-live-preview', 'camera-identity')
MASKS = {role: frozenset((2, 3) if index < 2 else (0, 1)) for index, role in enumerate(ROLES)}


def policy():
    return {'expected_process_cpus': [0, 1, 2, 3],
            'roles': {role: sorted(mask) for role, mask in MASKS.items()}}


class FatalExit(BaseException):
    pass


class FakeOS:
    def __init__(self):
        self.lock = threading.Lock()
        self.masks = {}
        self.calls = []
        self.fail_role = self.clip_role = self.restore_failure = None
        self.pid = 42

    def identity(self):
        tid = threading.get_native_id()
        return dict(pid=self.pid, process_starttime=99, tid=tid, thread_starttime=tid + 100)

    def get(self, who):
        assert who == 0
        with self.lock:
            return set(self.masks.get(threading.get_native_id(), range(4)))

    def set(self, who, mask):
        assert who == 0
        with self.lock:
            mask = frozenset(mask)
            name = threading.current_thread().name
            self.calls.append((threading.get_native_id(), who, mask))
            if self.restore_failure == name and mask == frozenset(range(4)):
                raise OSError('synthetic restoration failure')
            self.masks[threading.get_native_id()] = mask
            if mask != frozenset(range(4)) and self.clip_role == name:
                self.masks[threading.get_native_id()] = frozenset((min(mask),))
            if mask != frozenset(range(4)) and self.fail_role == name:
                raise OSError('synthetic partial set failure')


class TrialFixture:
    def __init__(self, masks=MASKS, timeout=.15, journal=None):
        self.os = FakeOS()
        self.events = []
        self.fatals = []
        self.errors = []
        self.executed = []

        def fatal(code):
            self.fatals.append(code)
            raise FatalExit()

        self.trial = AffinityTrial(masks, journal or self.events.append,
            startup_timeout=timeout, shutdown_timeout=.1,
            get_affinity=self.os.get, set_affinity=self.os.set,
            identity=self.os.identity, fatal=fatal)
        self.threads = []

    def start(self, role, callback=None):
        def run():
            try:
                with self.trial.role(role):
                    self.executed.append(role)
                    if callback:
                        callback()
            except BaseException as exc:
                self.errors.append(exc)
        thread = threading.Thread(target=run, name=role)
        self.threads.append(thread)
        thread.start()
        return thread

    def all(self, callback=None):
        for role in self.trial.masks:
            self.start(role, callback)
        self.join()

    def join(self):
        for thread in self.threads:
            thread.join(1.)
            assert not thread.is_alive(), 'test worker leaked'


class PolicyTests(unittest.TestCase):
    def test_accepts_explicit_disjoint_masks(self):
        self.assertEqual(checked_policy(policy(), range(4)), MASKS)

    def test_rejects_invalid_masks_before_any_os_change(self):
        for invalid in ([], [True], [0, 0], [-1], [4096], [[0]], '0,1'):
            with self.subTest(invalid=invalid):
                value = policy()
                value['roles']['camera-detection'] = invalid
                with self.assertRaises(ValueError):
                    checked_policy(value, range(4))

    def test_rejects_actual_cpu_set_change(self):
        with self.assertRaises(ValueError):
            checked_policy(policy(), (0, 1, 2))

    def test_rejects_outside_mask(self):
        value = policy()
        value['roles']['camera-detection'] = [4]
        with self.assertRaises(ValueError):
            checked_policy(value, range(4))

    def test_rejects_overlapping_inference_preparation(self):
        value = policy()
        value['roles']['camera-identity'] = [2]
        with self.assertRaises(ValueError):
            checked_policy(value, range(4))

    def test_rejects_unknown_or_partial_optional_roles(self):
        for extra in ('unknown-native', 'sface-dpu-shadow'):
            value = policy()
            value['roles'][extra] = [2]
            with self.assertRaises(ValueError):
                checked_policy(value, range(4))

    def test_rejects_three_model_dependency_cycle_configuration(self):
        value = policy()
        value['roles'].update({'sface-dpu-shadow': [2, 3], 'sface-crop-prepare': [0, 1]})
        with self.assertRaises(ValueError):
            checked_policy(value, range(4))


class TransactionTests(unittest.TestCase):
    def test_all_roles_commit_before_work_and_restore_current_threads(self):
        f = TrialFixture()
        f.all(lambda: self.assertTrue(f.trial.committed))
        f.trial.close()
        self.assertCountEqual(f.executed, ROLES)
        self.assertFalse(f.fatals)
        self.assertFalse(f.errors)
        self.assertEqual(len([e for e in f.events if e['event'] == 'RESTORED']), 4)
        self.assertTrue(all(mask == frozenset(range(4)) for mask in f.os.masks.values()))
        self.assertTrue(all(who == 0 for _, who, _ in f.os.calls))

    def test_startup_barrier_blocks_an_early_thread(self):
        f = TrialFixture(timeout=.5)
        f.start(ROLES[0])
        time.sleep(.015)
        self.assertEqual(f.executed, [])
        for role in ROLES[1:]:
            f.start(role)
        f.join()
        self.assertFalse(f.fatals)

    def test_partial_os_failure_restores_every_attempt_and_runs_no_target(self):
        f = TrialFixture()
        f.os.fail_role = 'camera-live-preview'
        f.all()
        self.assertFalse(f.executed)
        self.assertEqual(f.fatals, [70])
        self.assertTrue(all(mask == frozenset(range(4)) for mask in f.os.masks.values()))

    def test_kernel_clipped_mask_is_not_reported_as_success(self):
        f = TrialFixture()
        f.os.clip_role = 'camera-face-targets'
        f.all()
        self.assertFalse(f.executed)
        self.assertEqual(f.fatals, [70])
        self.assertTrue(all(mask == frozenset(range(4)) for mask in f.os.masks.values()))

    def test_missing_role_times_out_and_restores(self):
        f = TrialFixture(timeout=.03)
        f.start(ROLES[0])
        f.join()
        self.assertFalse(f.executed)
        self.assertEqual(f.fatals, [70])
        self.assertTrue(all(mask == frozenset(range(4)) for mask in f.os.masks.values()))

    def test_restoration_failure_forces_owned_process_exit(self):
        f = TrialFixture()
        f.os.restore_failure = 'camera-detection'
        f.all()
        self.assertEqual(f.fatals, [70])
        self.assertIn('restoration', f.trial.failure)

    def test_process_identity_change_refuses_before_any_mutation(self):
        f = TrialFixture()
        f.os.pid = 43
        f.start(ROLES[0])
        f.join()
        self.assertFalse(f.os.calls)
        self.assertFalse(f.executed)
        self.assertEqual(f.fatals, [70])

    def test_logging_failure_before_set_never_changes_affinity(self):
        def broken(_):
            raise OSError('synthetic journal failure')
        f = TrialFixture(journal=broken)
        f.start(ROLES[0])
        f.join()
        self.assertFalse(f.os.calls)
        self.assertFalse(f.executed)
        self.assertEqual(f.fatals, [70])

    def test_logging_failure_after_set_restores_before_abort(self):
        def broken(event):
            if event['event'] == 'APPLIED':
                raise OSError('synthetic journal failure after set')
        f = TrialFixture(journal=broken)
        f.start(ROLES[0])
        f.join()
        self.assertFalse(f.executed)
        self.assertEqual(f.fatals, [70])
        self.assertTrue(all(mask == frozenset(range(4)) for mask in f.os.masks.values()))

    def test_original_target_exception_restores_without_masking_it(self):
        f = TrialFixture()

        def original():
            raise ValueError('original target error')
        f.all(original)
        self.assertEqual(len(f.errors), 4)
        self.assertTrue(all(isinstance(e, ValueError) for e in f.errors))
        self.assertFalse(f.fatals)
        self.assertTrue(all(mask == frozenset(range(4)) for mask in f.os.masks.values()))

    def test_duplicate_or_late_role_never_reapplies(self):
        f = TrialFixture()
        f.all()
        count = len(f.os.calls)
        f.start(ROLES[0])
        f.join()
        self.assertEqual(len(f.os.calls), count)
        self.assertEqual(f.fatals, [70])

    def test_close_with_live_scopes_is_bounded_and_exits_owned_process(self):
        f = TrialFixture()
        entered = threading.Event()
        release = threading.Event()

        def body():
            entered.set()
            release.wait(1.)
        for role in ROLES:
            f.start(role, body)
        self.assertTrue(entered.wait(.5))
        try:
            with self.assertRaises(FatalExit):
                f.trial.close()
        finally:
            release.set()
            f.join()
        self.assertEqual(f.fatals, [70])
        self.assertIn('live affinity scopes', f.trial.failure)


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'tools').mkdir()
        self.target = self.root / 'tools' / 'board_camera_motion.py'
        self.target.write_text('print("fixture only")\n')
        self.digest = hashlib.sha256(self.target.read_bytes()).hexdigest()
        self.options = dict(allowed_root=self.root, expected_sha=self.digest)
        self.env = patch.dict(os.environ, {}, clear=True)
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def test_disabled_launcher_does_not_install_hook_or_journal(self):
        original = threading.Thread.run
        original_interval = sys.getswitchinterval()
        old_argv = sys.argv

        def runner(target, run_name):
            self.assertIs(threading.Thread.run, original)
            self.assertEqual(sys.argv, [str(self.target), '--fixture'])
            self.assertEqual(sys.getswitchinterval(), original_interval)
            return 17
        self.assertEqual(launch([str(self.target), '--fixture'], runner=runner, **self.options), 17)
        self.assertIs(sys.argv, old_argv)
        self.assertFalse(list(self.root.glob('affinity-*.jsonl')))

    def test_wrong_entrypoint_hash_refuses(self):
        self.target.write_text('changed\n')
        with self.assertRaises(ValueError):
            launch([str(self.target)], **self.options)

    def test_symlink_entrypoint_refuses(self):
        link = self.root / 'board_camera_motion.py'
        link.symlink_to(self.target)
        with self.assertRaises(ValueError):
            launch([str(link)], **self.options)

    def test_explicit_gil_combination_refuses_without_changing_it(self):
        os.environ.update(AURA_EXPERIMENT_AFFINITY='1', AURA_EXPERIMENT_GIL_MS='1')
        before = sys.getswitchinterval()
        with self.assertRaises(ValueError):
            launch([str(self.target)], **self.options)
        self.assertEqual(sys.getswitchinterval(), before)

    def test_role_binding_requires_path_and_qualname(self):
        namespace = {}
        source = 'def worker():\n    return None\n'
        exec(compile(source, str(self.target), 'exec'), namespace)
        thread = threading.Thread(target=namespace['worker'])
        self.assertTrue(target_matches(thread, (self.target, 'worker')))
        self.assertFalse(target_matches(thread, (self.target, 'wrong')))
        self.assertFalse(target_matches(thread, (self.root / 'other.py', 'worker')))


class SourceAuditTests(unittest.TestCase):
    def test_pins_match_independent_board_audit_native_bundle_and_migrated_source(self):
        # Read independent, already-frozen upstream release/board evidence.
        # Comparing only this package's reference copy to its own pin would not
        # detect an accidentally selected pre-migration face_targets source.
        deliverables = Path(os.environ.get('AURA_AFFINITY_UPSTREAM_DELIVERABLES',
            '/home/ghmd/Win共享文件/语音共享文件/deliverables'))
        gil_release = deliverables/'2026-10-22_gil_interval_trial'
        audit = json.loads((gil_release/'evidence/final-active-audit.json').read_text())
        native = json.loads((gil_release/'pinned-native-bundle.json').read_text())['manifest']['files']
        long_test = json.loads((gil_release/'evidence/long-600s.json').read_text())['report']
        actual_source = (deliverables/'2026-10-21_dpu_vision_start/candidate/aura'
                         /'board/identity/face_targets.py')
        actual_sha = hashlib.sha256(actual_source.read_bytes()).hexdigest()
        self.assertEqual(actual_sha, audit['source_hashes']['board/identity/face_targets.py'])
        self.assertNotEqual(actual_sha,
            '8d0270f2367140262815959c435b0e5ea2795c075fcbf07c4dcb8def24c40828')
        reference = Path(__file__).parent/'source-reference/aura'
        for role, (relative, _, digest) in ROLE_SOURCES.items():
            with self.subTest(role=role):
                independent_sha = (actual_sha if relative=='board/identity/face_targets.py'
                                   else native[relative]['sha256'])
                self.assertEqual(digest, independent_sha)
                self.assertEqual(hashlib.sha256((reference/relative).read_bytes()).hexdigest(),
                                 independent_sha)
        self.assertEqual(CAMERA_SHA,
            long_test['experimental_process_setting']['target_sha256'])

    def test_frozen_source_sha_and_qualnames_match_recovered_runtime(self):
        root = Path(__file__).parent/'source-reference/aura'
        self.assertEqual(hashlib.sha256((root/'tools/board_camera_motion.py').read_bytes()).hexdigest(), CAMERA_SHA)
        for role, (relative, expected_qualname, digest) in ROLE_SOURCES.items():
            path = root/relative
            with self.subTest(role=role):
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)
                found = set()

                def visit(node, prefix=''):
                    for child in ast.iter_child_nodes(node):
                        if isinstance(child, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                            name = prefix + child.name
                            found.add(name)
                            visit(child, name + ('.' if isinstance(child, ast.ClassDef) else '.<locals>.'))
                        else:
                            visit(child, prefix)
                visit(ast.parse(path.read_text()))
                self.assertIn(expected_qualname, found)

    def test_current_identity_is_this_process_and_calling_thread(self):
        identity = current_identity()
        self.assertEqual(identity['pid'], os.getpid())
        self.assertEqual(identity['tid'], threading.get_native_id())
        self.assertGreater(identity['process_starttime'], 0)
        self.assertGreaterEqual(identity['thread_starttime'], identity['process_starttime'])


class OwnedChildTests(unittest.TestCase):
    def test_owned_child_affinity_restoration_and_native_inheritance_boundary(self):
        available = sorted(os.sched_getaffinity(0))
        if len(available) < 2:
            self.skipTest('Need two allowed CPUs for a disjoint owned-child test')
        before = os.sched_getaffinity(0)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root/'tools').mkdir()
            roles_path = root/'roles.py'
            roles_path.write_text('''def targets():
    def detection(): observe('camera-detection')
    def faces(): observe('camera-face-targets')
    def preview(): observe('camera-live-preview')
    def identity(): observe('camera-identity')
    return {'camera-detection':detection,'camera-face-targets':faces,
            'camera-live-preview':preview,'camera-identity':identity}
''')
            digest = hashlib.sha256(roles_path.read_bytes()).hexdigest()
            names = ('detection','faces','preview','identity')
            sources = {role: ('roles.py', 'targets.<locals>.'+name, digest)
                       for role, name in zip(ROLES, names)}
            entry = root/'tools/board_camera_motion.py'
            entry.write_text('''import json, os, runpy, threading
from pathlib import Path
namespace=runpy.run_path(str(Path(__file__).parents[1]/'roles.py'))
results=[]
def observe(role):
    results.append({'role':role,'cpus':sorted(os.sched_getaffinity(0)),
                    'pid':os.getpid(),'tid':threading.get_native_id()})
    if role=='camera-detection':
        child=threading.Thread(target=lambda:observe('unknown-descendant'),name='unknown-descendant')
        child.start();child.join()
namespace['targets'].__globals__['observe']=observe
threads=[threading.Thread(target=target,name=role)
         for role,target in namespace['targets']().items()
         if role!=os.environ.get('AURA_AFFINITY_FIXTURE_OMIT_ROLE')]
threads.append(threading.Thread(target=lambda:observe('unknown'),name='unknown-native-like-role'))
for thread in threads:thread.start()
for thread in threads:thread.join()
print(json.dumps({'results':results,'main_cpus':sorted(os.sched_getaffinity(0))}))
''')
            p = {'expected_process_cpus': available, 'roles': {
                role: [available[0 if index<2 else 1]] for index,role in enumerate(ROLES)}}
            policy_path = root/'policy.json'
            policy_path.write_text(json.dumps(p))
            script = root/'run_owned_fixture.py'
            script.write_text('''from pathlib import Path
import json, sys, threading
from affinity_camera_launcher import launch
from thread_affinity_trial import AffinityTrial
old_argv=sys.argv
old_run=threading.Thread.run
old_interval=sys.getswitchinterval()
launch(%r, allowed_root=Path(%r), expected_sha=%r, role_sources=%r,
       record_directory=Path(%r),
       trial_factory=lambda masks,journal:AffinityTrial(masks,journal,startup_timeout=1.))
print(json.dumps({'post_launch':{'argv_restored':sys.argv is old_argv,
    'thread_hook_restored':threading.Thread.run is old_run,
    'gil_unchanged':sys.getswitchinterval()==old_interval}}))
''' % ([str(entry)], str(root), hashlib.sha256(entry.read_bytes()).hexdigest(), sources, str(root)))
            env = dict(os.environ, AURA_EXPERIMENT_AFFINITY='1',
                       AURA_EXPERIMENT_AFFINITY_POLICY=str(policy_path),
                       PYTHONPATH=str(Path(__file__).parent))
            env.pop('AURA_EXPERIMENT_GIL_MS', None)
            result = subprocess.run([sys.executable, str(script)], capture_output=True, text=True,
                                    timeout=8, env=env)
            self.assertEqual(result.returncode, 0, result.stderr)
            report, post = [json.loads(line) for line in result.stdout.splitlines()]
            self.assertEqual(post['post_launch'],dict(argv_restored=True,
                             thread_hook_restored=True,gil_unchanged=True))
            self.assertEqual(report['main_cpus'], available)
            self.assertEqual(len(report['results']), 6)
            for value in report['results']:
                self.assertNotEqual(value['pid'], os.getpid())
                expected = (available if value['role']=='unknown' else
                            p['roles']['camera-detection'] if value['role']=='unknown-descendant'
                            else p['roles'][value['role']])
                self.assertEqual(value['cpus'], expected)
            records = [json.loads(line) for line in next(root.glob('affinity-*.jsonl')).read_text().splitlines()]
            self.assertEqual(len([r for r in records if r['event']=='RESTORED']),4)
            self.assertEqual(records[-1]['event'], 'CLOSED')
            failed_env = dict(env, AURA_AFFINITY_FIXTURE_OMIT_ROLE='camera-identity')
            failed = subprocess.run([sys.executable, str(script)], capture_output=True, text=True,
                                    timeout=8, env=failed_env)
            self.assertEqual(failed.returncode, 70, failed.stderr)
            failed_records = []
            for file in root.glob('affinity-*.jsonl'):
                candidate = [json.loads(line) for line in file.read_text().splitlines()]
                if candidate[-1]['event']=='ABORT_OWNED_PROCESS':
                    failed_records = candidate
                    break
            self.assertTrue(failed_records)
            self.assertEqual(len([r for r in failed_records if r['event']=='RESTORED']), 3)
            self.assertEqual(failed_records[-1]['scopes_still_active'], [])
            self.assertFalse(failed.stdout)
            evidence_path = os.environ.get('AURA_AFFINITY_TEST_EVIDENCE')
            if evidence_path:
                with Path(evidence_path).open('x') as output:
                    json.dump({'scope':'localhost owned subprocess fixtures; not KV260',
                               'parent_cpus_before':sorted(before),
                               'parent_cpus_after':sorted(os.sched_getaffinity(0)),
                               'success_exit':result.returncode,'failure_exit':failed.returncode,
                               'success_report':report,'post_launch':post['post_launch'],
                               'success_records':records,
                               'failure_records':failed_records}, output, indent=2)
        self.assertEqual(os.sched_getaffinity(0), before)


if __name__ == '__main__':
    unittest.main(verbosity=2)
