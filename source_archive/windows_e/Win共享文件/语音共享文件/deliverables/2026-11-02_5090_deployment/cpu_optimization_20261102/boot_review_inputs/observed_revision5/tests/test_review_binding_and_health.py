"""Small CPU-review counterexamples for healthy owner and captured-ledger CAS."""
import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / 'candidate'))
import boot_recovery as runtime
import recovery_rules as rules
spec = importlib.util.spec_from_file_location('binding_review_public_helpers', HERE / 'tests/test_boot_recovery.py')
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)


class CameraAdmissionTests(unittest.TestCase):
    def sample(self, **schedule_changes):
        schedule = dict(native_critical=True, native_abi=2, owner_fenced=False, quiesced=False)
        schedule.update(schedule_changes)
        return dict(pid=helpers.OWNER['pid'], board_boot_id=helpers.BOOT, motion_command_emitted=False,
                    identity=dict(ready=True), dpu_schedule=schedule, capture_frames=10, detected_frames=5)

    def test_deactivating_camera_is_rejected_without_reading_health(self):
        recovery = object.__new__(runtime.Recovery)
        recovery.boot = helpers.BOOT
        state = dict(MainPID=str(helpers.OWNER['pid']), ActiveState='deactivating', SubState='stop-sigterm', Job='')
        with patch.object(runtime, 'unit', return_value=state), patch.object(runtime, 'get_metadata') as get:
            with self.assertRaisesRegex(rules.Hold, 'EXIT_OR_JOB_PENDING'):
                recovery.camera_samples()
            get.assert_not_called()

    def test_pending_camera_stop_is_rejected_even_with_active_mainpid(self):
        recovery = object.__new__(runtime.Recovery)
        state = dict(MainPID=str(helpers.OWNER['pid']), ActiveState='active', SubState='running', Job='99')
        with patch.object(runtime, 'unit', return_value=state), patch.object(runtime, 'get_metadata') as get:
            with self.assertRaisesRegex(rules.Hold, 'EXIT_OR_JOB_PENDING'):
                recovery.camera_samples()
            get.assert_not_called()

    def test_quiesced_or_unknown_native_state_cannot_admit_binding(self):
        for quiesced in (True, None):
            recovery = object.__new__(runtime.Recovery)
            recovery.boot = helpers.BOOT
            state = dict(MainPID=str(helpers.OWNER['pid']), ControlPID='0', ActiveState='active', SubState='running', Job='')
            with self.subTest(quiesced=quiesced), patch.object(runtime, 'unit', return_value=state), \
                    patch.object(runtime, 'get_metadata', return_value=self.sample(quiesced=quiesced)), \
                    patch.object(runtime, 'process', return_value=helpers.OWNER), \
                    patch.object(runtime.time, 'monotonic', side_effect=[0, 76]):
                with self.assertRaisesRegex(rules.Hold, 'CAMERA_NOT_READY_NO_RESTART'):
                    recovery.camera_samples()

    def test_genuine_running_nonquiesced_owner_advances(self):
        recovery = object.__new__(runtime.Recovery)
        recovery.boot = helpers.BOOT
        state = dict(MainPID=str(helpers.OWNER['pid']), ControlPID='0', ActiveState='active', SubState='running', Job='')
        one, two = self.sample(), self.sample()
        two.update(capture_frames=11, detected_frames=6)
        with patch.object(runtime, 'unit', return_value=state), patch.object(runtime, 'get_metadata', side_effect=[one, two]), \
                patch.object(runtime, 'process', return_value=helpers.OWNER), patch.object(runtime.time, 'sleep'):
            admitted, _ = recovery.camera_samples()
        self.assertEqual(admitted, helpers.OWNER)


class CapturedLedgerTests(helpers.SourceDriftTests):
    # Reuse only the public three-file fixture, not the baseline test cases.
    def setUp(self):
        super().setUp()
        self.r.boot = helpers.BOOT
        self.r.tx = self.base / 'transaction'
        self.r.tx.mkdir()
        self.ops = self.base / 'ops'
        run = self.ops / ('native-run-' + helpers.BOOT + '-' + str(helpers.OWNER['pid'])) / 'config.json'
        run.parent.mkdir(parents=True)
        manifest = dict(path='/public/manifest.json', sha256='3' * 64)
        run.write_bytes(rules.encoded(dict(native_execution=dict(source_manifest=manifest['path'], source_manifest_sha256=manifest['sha256'], checkpoint_output=str(runtime.CHECKPOINT)))))
        self.r.contract.update(native_ops_root=str(self.ops), native_manifest=manifest)
        self.r.prepared = lambda: None
        health = dict(dpu_schedule=dict(protection_handoff=dict(mode='native_new_kernel_boot', seed_sha256='8' * 64,
                        source_pid=helpers.OWNER['pid'], source_birth_ticks=int(helpers.OWNER['birth_ticks']),
                        current_boot=helpers.BOOT, source_boot=helpers.PREVIOUS)))
        self.r.camera_samples = lambda: (helpers.OWNER, health)
        self.r.check_camera_live = lambda expected: health
        self.r.accepted_live_history = lambda gate, handoff: (dict(head={}, archive_count=1, archives=[], legacy_pin={}), {})
        gate = dict(boot_id=helpers.BOOT, contract_sha256=self.r.contract_sha, checkpoint_sha256='8' * 64,
                    predecessor=dict(boot_id=helpers.PREVIOUS, camera_owner=helpers.OWNER))
        (self.r.tx / 'current-camera-gate.json').write_bytes(rules.encoded(gate))
        self.active = self.state / 'active-source.json'
        active = dict(self.r.contract['initial_source_state'], contract_sha256=self.r.contract_sha)
        self.active.write_bytes(rules.encoded(active))
        self.original_active = self.active.read_bytes()
        self.original_ui = self.ui.read_bytes()
        self.original_startup = self.startup.read_bytes()
        self.inject_after_startup = False
        self.newer = rules.encoded(dict(active, newer_revision='preserve_this_public_metadata'))

        def cas(path, before, after):
            path = Path(path)
            rules.require(path.read_bytes() == before, 'CAS_SOURCE_CHANGED')
            path.write_bytes(after)
            if path == self.startup and self.inject_after_startup:
                self.active.write_bytes(self.newer)

        gui = dict(MainPID='0', ActiveState='activating', SubState='start-pre', ControlPID=str(os.getpid()))
        self.extra = [patch.object(runtime, 'create', helpers.local_create), patch.object(runtime, 'replace_known', cas),
                      patch.object(runtime, 'original_verify'), patch.object(runtime, 'process', return_value=helpers.OWNER),
                      patch.object(runtime, 'unit', return_value=gui)]
        for value in self.extra:
            value.start()

    def tearDown(self):
        for value in reversed(self.extra):
            value.stop()
        super().tearDown()

    def test_normal_binding_publishes_captured_ledger(self):
        result = self.r.bind_camera()
        self.assertEqual(result['status'], 'ORIGINAL_VERIFIER_CURRENT_BINDING_COMMITTED')
        self.assertNotEqual(self.active.read_bytes(), self.original_active)

    def test_ledger_change_after_source_capture_aborts_before_ui_write(self):
        original_snapshot = self.r.source_snapshot
        calls = 0
        def snapshot():
            nonlocal calls
            calls += 1
            if calls == 2:
                self.active.write_bytes(self.newer)
            return original_snapshot()
        self.r.source_snapshot = snapshot
        with self.assertRaisesRegex(rules.Hold, 'SOURCE_CHANGED_BEFORE_BINDING_CAS'):
            self.r.bind_camera()
        self.assertEqual(self.active.read_bytes(), self.newer)
        self.assertEqual(self.ui.read_bytes(), self.original_ui)
        self.assertEqual(self.startup.read_bytes(), self.original_startup)

    def test_ledger_change_after_ui_startup_writes_is_never_reblessed(self):
        self.inject_after_startup = True
        with self.assertRaisesRegex(rules.Hold, 'CAS_SOURCE_CHANGED'):
            self.r.bind_camera()
        self.assertEqual(self.active.read_bytes(), self.newer)

    def test_camera_lifecycle_change_immediately_before_cas_keeps_sources_original(self):
        def stopped(expected):
            raise rules.Hold('CAMERA_LIFECYCLE_CHANGED_NO_BINDING_OR_READY')
        self.r.check_camera_live = stopped
        with self.assertRaisesRegex(rules.Hold, 'LIFECYCLE_CHANGED'):
            self.r.bind_camera()
        self.assertEqual(self.ui.read_bytes(), self.original_ui)
        self.assertEqual(self.startup.read_bytes(), self.original_startup)


if __name__ == '__main__':
    (HERE / 'test_work').mkdir(exist_ok=True)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(CameraAdmissionTests)
    for name in ('test_normal_binding_publishes_captured_ledger',
                 'test_ledger_change_after_source_capture_aborts_before_ui_write',
                 'test_ledger_change_after_ui_startup_writes_is_never_reblessed',
                 'test_camera_lifecycle_change_immediately_before_cas_keeps_sources_original'):
        suite.addTest(CapturedLedgerTests(name))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
