import importlib.util
from pathlib import Path
import sys
import threading
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'candidate/aura'))
if (ROOT/'tests/bootstrap.py').exists():
    import bootstrap
from board.vision.dpu_vision_schedule import DpuVisionSchedule


class Clock:
    def __init__(self): self.now = 1000.
    def __call__(self): return self.now
    def advance(self, seconds): self.now += seconds


class Harness:
    def setUp(self):
        self.clock = Clock()
        self.schedule = DpuVisionSchedule(clock=self.clock, yunet_recovery=True)
        self.schedule.next_primary = self.clock()+1

    def row(self): return self.schedule.health()['optional']['yunet']
    def policy(self): return self.schedule.health()['yunet_recovery']

    def job(self, seconds=.004, completed=True, kind='yunet'):
        with self.schedule.optional(kind) as acquired:
            self.assertTrue(acquired)
            self.clock.advance(seconds)
            if completed: self.schedule.native_completed(kind)

    def primary(self, overrun=False):
        with self.schedule.primary(self.clock()+.1):
            self.clock.advance(.101 if overrun else .004)

    def fault(self):
        self.job(.031)
        self.assertTrue(self.schedule.disabled('yunet'))
        self.assertEqual(self.row()['overruns'], 1)

    def cooled(self):
        self.clock.advance(10)
        self.primary()


class RecoveryTests(Harness, unittest.TestCase):
    def test_explicit_boolean_required(self):
        for value in (1, None, 'true'):
            with self.assertRaises(ValueError): DpuVisionSchedule(yunet_recovery=value)

    def test_default_preserves_latched_cpu_policy(self):
        s = DpuVisionSchedule(clock=self.clock)
        s.next_primary = self.clock()+1
        with s.optional('yunet') as acquired:
            self.assertTrue(acquired); self.clock.advance(.031); s.native_completed('yunet')
        self.clock.advance(100)
        self.assertTrue(s.disabled('yunet'))
        self.assertFalse(s.recovery_ready('yunet'))
        self.assertNotIn('yunet_recovery', s.health())

    def test_hardcap_records_fault_and_cooldown(self):
        self.fault()
        self.assertEqual(self.policy()['phase'], 'COOLDOWN')
        self.assertFalse(self.schedule.recovery_ready('yunet'))
        self.assertGreater(self.row()['maximum_ms'], 30)

    def test_cooldown_does_not_sleep_or_hold_slot(self):
        self.fault()
        self.assertIsNone(self.schedule.active)
        self.primary()
        self.assertFalse(self.schedule.recovery_ready('yunet'))
        self.assertEqual(self.policy()['attempts'], 0)

    def test_elapsed_time_without_new_primary_cannot_recover(self):
        self.fault(); self.clock.advance(10)
        self.assertFalse(self.schedule.recovery_ready('yunet'))

    def test_stale_primary_cannot_recover(self):
        self.fault(); self.cooled(); self.clock.advance(.501)
        self.assertFalse(self.schedule.recovery_ready('yunet'))

    def test_new_primary_overrun_latches_recovery(self):
        self.fault(); self.clock.advance(10); self.primary(overrun=True)
        self.assertFalse(self.schedule.recovery_ready('yunet'))
        self.assertEqual(self.policy()['phase'], 'LATCHED')

    def test_atomic_admission_retains_disabled_when_primary_waits(self):
        self.fault(); self.cooled()
        self.assertTrue(self.schedule.recovery_ready('yunet'))
        self.schedule.waiting_primary = 1
        with self.schedule.optional('yunet') as acquired: self.assertFalse(acquired)
        self.assertTrue(self.schedule.disabled('yunet'))
        self.assertEqual(self.policy()['attempts'], 0)

    def test_busy_or_inflight_job_prevents_probe(self):
        self.fault(); self.cooled(); self.schedule.active = 'yolo'
        self.assertFalse(self.schedule.recovery_ready('yunet'))
        with self.schedule.optional('yunet') as acquired: self.assertFalse(acquired)
        self.assertEqual(self.policy()['attempts'], 0)

    def test_deadline_denial_does_not_spend_probe_or_clear_disabled(self):
        self.fault(); self.cooled(); self.schedule.next_primary = self.clock()+.010
        with self.schedule.optional('yunet') as acquired: self.assertFalse(acquired)
        self.assertTrue(self.schedule.disabled('yunet'))
        self.assertEqual(self.policy()['attempts'], 0)

    def test_three_native_successes_recover_with_original_counters(self):
        self.fault(); self.cooled()
        self.assertTrue(self.schedule.recovery_ready('yunet'))
        self.job()
        self.assertEqual(self.policy()['phase'], 'PROBATION')
        self.assertFalse(self.schedule.disabled('yunet'))
        self.job(); self.job()
        self.assertEqual(self.policy()['phase'], 'RUNNING')
        self.assertEqual(self.policy()['recoveries'], 1)
        self.assertEqual(self.row()['overruns'], 1)
        self.assertEqual(self.row()['calls'], 4)
        self.assertGreater(self.row()['maximum_ms'], 30)

    def test_unproven_completion_cannot_start_recovery(self):
        self.job(.031, completed=False)
        self.cooled()
        self.assertFalse(self.schedule.recovery_ready('yunet'))
        self.assertEqual(self.policy()['phase'], 'LATCHED')

    def test_primary_overrun_during_probation_stops_probes(self):
        self.fault(); self.cooled(); self.job(); self.primary(overrun=True)
        self.assertTrue(self.schedule.disabled('yunet'))
        self.assertEqual(self.policy()['reason'], 'primary_overrun_during_probation')
        self.assertEqual(self.policy()['recoveries'], 0)

    def test_guard_violation_stays_latched(self):
        self.schedule.next_primary = self.clock()+.026
        self.job(.022)
        self.cooled()
        self.assertFalse(self.schedule.recovery_ready('yunet'))
        self.assertEqual(self.policy()['phase'], 'LATCHED')

    def test_native_exception_stays_latched_and_releases_slot(self):
        with self.assertRaisesRegex(RuntimeError, 'native failure'):
            with self.schedule.optional('yunet') as acquired:
                self.assertTrue(acquired)
                raise RuntimeError('native failure')
        self.assertTrue(self.schedule.disabled('yunet'))
        self.assertEqual(self.policy()['phase'], 'LATCHED')
        self.assertIsNone(self.schedule.active)

    def test_known_preexecute_withdrawal_does_not_latch(self):
        error = RuntimeError('pre-execute deadline'); error.native_not_submitted = True
        with self.assertRaises(RuntimeError):
            with self.schedule.optional('yunet') as acquired:
                self.assertTrue(acquired); raise error
        self.assertFalse(self.schedule.disabled('yunet'))
        self.assertEqual(self.policy()['faults'], 0)

    def test_repeated_faults_stop_at_two_probe_cycles(self):
        self.fault()
        for _ in range(2):
            self.cooled(); self.job(.031)
        self.assertEqual(self.policy()['attempts'], 2)
        self.assertEqual(self.policy()['faults'], 3)
        self.assertEqual(self.row()['overruns'], 3)
        self.assertEqual(self.policy()['phase'], 'LATCHED')
        self.cooled()
        self.assertFalse(self.schedule.recovery_ready('yunet'))

    def test_old_probe_budget_expires_after_window(self):
        self.fault(); self.cooled()
        self.job(); self.job(); self.job()
        self.clock.advance(601); self.primary(); self.job(.031)
        self.cooled(); self.job()
        self.assertEqual(self.policy()['attempts'], 2)
        self.assertEqual(self.policy()['attempts_in_window'], 1)

    def test_other_optional_model_cannot_use_yunet_recovery(self):
        self.job(.031, kind='sface')
        self.assertTrue(self.schedule.disabled('sface'))
        self.assertFalse(self.schedule.recovery_ready('sface'))
        self.assertEqual(self.policy()['faults'], 0)

    def test_completion_outside_slot_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError, 'own'): self.schedule.native_completed('yunet')

    def test_completion_from_another_thread_is_rejected(self):
        failures = []
        def foreign():
            try: self.schedule.native_completed('yunet')
            except RuntimeError as error: failures.append(str(error))
        with self.schedule.optional('yunet') as acquired:
            self.assertTrue(acquired)
            thread = threading.Thread(target=foreign); thread.start(); thread.join(1)
            self.assertFalse(thread.is_alive())
            self.assertEqual(len(failures), 1)
            self.clock.advance(.031)
        self.assertEqual(self.policy()['phase'], 'LATCHED')


class AdapterTests(Harness, unittest.TestCase):
    # Keep this adapter harness independent of numpy/VART and production imports.
    def adapter(self):
        runtime = ModuleType('board.vision.dpu_vision_runtime')
        runtime.PinnedRunner = object
        runtime.encode = lambda value, fix: value
        runtime.make_yunet = lambda *a, **k: None
        runtime.SlotAdmissionDenied = type('SlotAdmissionDenied', (RuntimeError,), {})
        runtime.OptionalJobDisabled = type('OptionalJobDisabled', (RuntimeError,), {})
        path = ROOT/'candidate/aura/board/vision/dpu_yunet.py'
        spec = importlib.util.spec_from_file_location('_adapter_recovery_test', path)
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {'board.vision.dpu_vision_runtime': runtime}):
            spec.loader.exec_module(module)
        adapter = module.DpuYuNet.__new__(module.DpuYuNet)
        adapter.schedule = self.schedule
        adapter.kind = 'DPU_YUNET_INT8'
        self.native_calls = self.cpu_calls = 0
        self.fail_native = False
        def execute(source, *, slot, pre_execute=None):
            with slot as acquired:
                if not acquired: return None
                if pre_execute: pre_execute()
                self.native_calls += 1
                if self.fail_native: raise RuntimeError('nonzero status or native exception')
                self.clock.advance(.004)
            return []
        adapter.runner = SimpleNamespace(input_fix=7, execute_encoded=execute)
        adapter.detector = SimpleNamespace(detect=lambda image: adapter.scheduled(image))
        def fallback(image): self.cpu_calls += 1; return []
        adapter.fallback = SimpleNamespace(detect=fallback)
        return adapter

    def test_cpu_during_cooldown_then_real_probe_updates_backend(self):
        adapter = self.adapter(); self.fault()
        adapter.detect('frame')
        self.assertEqual(self.cpu_calls, 1)
        self.assertEqual(adapter.kind, 'CPU_YUNET_FALLBACK_AFTER_DPU_OVERRUN')
        self.cooled(); adapter.detect('new-frame')
        self.assertEqual(self.native_calls, 1)
        self.assertEqual(adapter.kind, 'DPU_YUNET_INT8')
        self.assertEqual(self.policy()['probe_successes'], 1)

    def test_guarded_adapter_records_native_completion(self):
        adapter = self.adapter(); self.fault(); self.cooled()
        checks = []
        adapter.detect_with_admission_guard('fresh', lambda: checks.append(True))
        self.assertEqual(self.policy()['probe_successes'], 1)
        self.assertGreaterEqual(len(checks), 2)

    def test_failed_native_cannot_produce_completion_proof(self):
        adapter = self.adapter(); self.fail_native = True
        with self.assertRaises(RuntimeError): adapter.detect('frame')
        self.assertEqual(self.policy()['phase'], 'LATCHED')
        self.assertEqual(self.policy()['recoveries'], 0)


if __name__ == '__main__': unittest.main()
