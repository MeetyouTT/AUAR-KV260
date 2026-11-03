"""Independent offline adversarial tests of resource release and latching.

No device, native model, real identities, network, or service control is used.
Threaded tests explicitly release all gates in finally, including on failure.
"""
import bootstrap
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from board.identity.face_targets import FaceTargetService
from board.vision.dpu_vision_schedule import DpuVisionSchedule
from board.vision.dpu_yunet import DpuYuNet
from board.vision.pipeline_metrics import OptionalDiagnostics


class AuxiliaryAbort(BaseException):
    """Stand-in for an auxiliary callback interrupt, not a native failure."""


class FakeClock:
    def __init__(self):
        self.now = 1000.

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


class Diagnostics:
    enabled = True

    def __init__(self, *, begin_error=None, finish_error=None, error_error=None,
                 snapshot_error=None, on_begin=None, on_finish=None, on_snapshot=None):
        self.begin_error, self.finish_error = begin_error, finish_error
        self.error_error, self.snapshot_error = error_error, snapshot_error
        self.on_begin, self.on_finish, self.on_snapshot = on_begin, on_finish, on_snapshot
        self.errors = 0

    def begin(self, *args, **kwargs):
        if self.on_begin:
            self.on_begin()
        if self.begin_error:
            raise self.begin_error('synthetic auxiliary begin')
        return {'synthetic_trace': True}

    def finish(self, *args, **kwargs):
        if self.on_finish:
            self.on_finish()
        if self.finish_error:
            raise self.finish_error('synthetic auxiliary finish')

    def error(self):
        self.errors += 1
        if self.error_error:
            raise self.error_error('synthetic auxiliary error reporter')

    def snapshot(self):
        if self.on_snapshot:
            self.on_snapshot()
        if self.snapshot_error:
            raise self.snapshot_error('synthetic auxiliary snapshot')
        return {'enabled': True}


class ReleaseAuditTests(unittest.TestCase):
    def schedule(self, diagnostics=None, *, recovery=False):
        clock = FakeClock()
        schedule = DpuVisionSchedule(clock=clock, diagnostics=diagnostics, yunet_recovery=recovery)
        schedule.next_primary = clock()+1.
        return schedule, clock

    def assert_primary_can_run(self, schedule, clock):
        self.assertIsNone(schedule.active)
        with schedule.primary(clock()+1.):
            self.assertEqual(schedule.active, 'yolo')
        self.assertIsNone(schedule.active)

    def test_auxiliary_begin_exceptions_cannot_leak_execution_right(self):
        for error in (RuntimeError, AuxiliaryAbort):
            with self.subTest(error=error.__name__):
                schedule, clock = self.schedule(Diagnostics(begin_error=error))
                with schedule.optional('sface') as acquired:
                    self.assertTrue(acquired)
                    clock.advance(.002)
                self.assert_primary_can_run(schedule, clock)

    def test_auxiliary_finish_exceptions_cannot_leak_execution_right(self):
        for error in (RuntimeError, AuxiliaryAbort):
            with self.subTest(error=error.__name__):
                schedule, clock = self.schedule(Diagnostics(finish_error=error))
                with schedule.optional('sface') as acquired:
                    self.assertTrue(acquired)
                    clock.advance(.002)
                self.assert_primary_can_run(schedule, clock)

    def test_error_reporter_failure_cannot_turn_auxiliary_failure_into_lease_leak(self):
        for source in ('begin', 'finish'):
            with self.subTest(source=source):
                args = {source+'_error': RuntimeError, 'error_error': AuxiliaryAbort}
                schedule, clock = self.schedule(Diagnostics(**args))
                with schedule.optional('sface') as acquired:
                    self.assertTrue(acquired)
                    clock.advance(.002)
                self.assert_primary_can_run(schedule, clock)

    def test_native_body_base_exception_propagates_but_releases_and_latches(self):
        schedule, clock = self.schedule(Diagnostics(finish_error=AuxiliaryAbort), recovery=True)
        with self.assertRaisesRegex(AuxiliaryAbort, 'synthetic native body'):
            with schedule.optional('yunet') as acquired:
                self.assertTrue(acquired)
                clock.advance(.002)
                raise AuxiliaryAbort('synthetic native body')
        self.assertIsNone(schedule.active)
        self.assertTrue(schedule.disabled('yunet'))
        self.assertEqual(schedule.yunet_recovery.snapshot()['phase'], 'LATCHED')
        clock.advance(12)
        self.assertFalse(schedule.recovery_ready('yunet'))

    def test_primary_body_base_exception_propagates_without_retaining_owner(self):
        schedule, clock = self.schedule()
        with self.assertRaisesRegex(AuxiliaryAbort, 'synthetic primary body'):
            with schedule.primary(clock()+1.):
                raise AuxiliaryAbort('synthetic primary body')
        self.assert_primary_can_run(schedule, clock)

    def test_denied_auxiliary_context_does_not_release_another_owner(self):
        schedule, clock = self.schedule(Diagnostics(begin_error=AuxiliaryAbort))
        with schedule.primary(clock()+1.):
            with schedule.optional('sface') as acquired:
                self.assertFalse(acquired)
            self.assertEqual(schedule.active, 'yolo')
        self.assertIsNone(schedule.active)

    def test_finish_runs_after_release_and_recovery_fault_is_already_committed(self):
        observed = []
        diagnostics = Diagnostics()
        schedule, clock = self.schedule(diagnostics, recovery=True)
        def observe():
            observed.append((schedule.active, schedule.disabled('yunet'),
                             schedule.yunet_recovery.snapshot()['phase']))
        diagnostics.on_finish = observe
        with schedule.optional('yunet') as acquired:
            self.assertTrue(acquired)
            clock.advance(.031)
            schedule.native_completed('yunet')
        self.assertEqual(observed, [(None, True, 'COOLDOWN')])
        self.assertEqual(schedule.jobs['yunet']['overruns'], 1)
        self.assertEqual(schedule.yunet_recovery.snapshot()['faults'], 1)

    def test_diagnostic_time_before_native_remains_inside_original_cap(self):
        diagnostics = Diagnostics()
        schedule, clock = self.schedule(diagnostics, recovery=True)
        diagnostics.on_begin = lambda: clock.advance(.031)
        with schedule.optional('yunet') as acquired:
            self.assertTrue(acquired)
            schedule.native_completed('yunet')
        self.assertEqual(schedule.jobs['yunet']['overruns'], 1)
        self.assertGreater(schedule.jobs['yunet']['maximum_ms'], 30)
        self.assertTrue(schedule.disabled('yunet'))

    def test_guard_breach_is_still_latched_even_when_native_completed(self):
        schedule, clock = self.schedule(Diagnostics(), recovery=True)
        schedule.next_primary = clock()+.026
        with schedule.optional('yunet') as acquired:
            self.assertTrue(acquired)
            clock.advance(.022)
            schedule.native_completed('yunet')
        self.assertEqual(schedule.jobs['yunet']['overruns'], 1)
        self.assertEqual(schedule.yunet_recovery.snapshot()['phase'], 'LATCHED')
        clock.advance(12)
        self.assertFalse(schedule.recovery_ready('yunet'))

    def test_preexecute_withdrawal_is_not_reclassified_as_native_failure(self):
        schedule, clock = self.schedule(Diagnostics(), recovery=True)
        error = RuntimeError('synthetic preexecute withdrawal')
        error.native_not_submitted = True
        with self.assertRaisesRegex(RuntimeError, 'preexecute withdrawal'):
            with schedule.optional('yunet') as acquired:
                self.assertTrue(acquired)
                clock.advance(.002)
                raise error
        self.assertIsNone(schedule.active)
        self.assertFalse(schedule.disabled('yunet'))
        self.assertEqual(schedule.yunet_recovery.snapshot()['faults'], 0)

    def test_waiting_primary_cannot_be_bypassed_by_new_optional_admission(self):
        schedule, clock = self.schedule(Diagnostics())
        schedule.waiting_primary = 1
        with schedule.optional('yunet') as acquired:
            self.assertFalse(acquired)
        self.assertEqual(schedule.waiting_primary, 1)
        self.assertEqual(schedule.jobs['yunet']['calls'], 0)

    def test_blocked_finish_allows_primary_and_old_finalizer_cannot_clear_it(self):
        finish_entered, finish_release = threading.Event(), threading.Event()
        primary_entered, primary_release = threading.Event(), threading.Event()
        failures = []
        def blocking_finish():
            finish_entered.set()
            if not finish_release.wait(2):
                raise RuntimeError('test finish gate expired')
        schedule = DpuVisionSchedule(diagnostics=Diagnostics(on_finish=blocking_finish))
        schedule.next_primary = time.monotonic()+5
        def optional():
            try:
                with schedule.optional('sface') as acquired:
                    self.assertTrue(acquired)
            except BaseException as exc:
                failures.append(exc)
        def primary():
            try:
                with schedule.primary(time.monotonic()+5):
                    primary_entered.set()
                    if not primary_release.wait(2):
                        raise RuntimeError('test primary gate expired')
            except BaseException as exc:
                failures.append(exc)
        optional_thread = threading.Thread(target=optional)
        primary_thread = threading.Thread(target=primary)
        optional_thread.start()
        try:
            self.assertTrue(finish_entered.wait(1))
            primary_thread.start()
            self.assertTrue(primary_entered.wait(1), 'diagnostic finish still blocks the primary')
            finish_release.set()
            optional_thread.join(1)
            self.assertFalse(optional_thread.is_alive())
            self.assertEqual(schedule.active, 'yolo', 'old finalizer cleared the new primary owner')
        finally:
            finish_release.set()
            primary_release.set()
            optional_thread.join(2)
            if primary_thread.ident is not None:
                primary_thread.join(2)
        self.assertFalse(failures, failures)
        self.assertIsNone(schedule.active)

    def test_blocked_snapshot_does_not_own_condition_needed_by_primary(self):
        snapshot_entered, snapshot_release = threading.Event(), threading.Event()
        primary_entered = threading.Event()
        failures = []
        def snapshot():
            snapshot_entered.set()
            if not snapshot_release.wait(2):
                raise RuntimeError('test snapshot gate expired')
        schedule = DpuVisionSchedule(diagnostics=Diagnostics(on_snapshot=snapshot))
        def health():
            try:
                schedule.health()
            except BaseException as exc:
                failures.append(exc)
        def primary():
            try:
                with schedule.primary(time.monotonic()+5):
                    primary_entered.set()
            except BaseException as exc:
                failures.append(exc)
        health_thread = threading.Thread(target=health)
        primary_thread = threading.Thread(target=primary)
        health_thread.start()
        try:
            self.assertTrue(snapshot_entered.wait(1))
            primary_thread.start()
            self.assertTrue(primary_entered.wait(1), 'health snapshot still blocks the primary')
        finally:
            snapshot_release.set()
            health_thread.join(2)
            if primary_thread.ident is not None:
                primary_thread.join(2)
        self.assertFalse(failures, failures)
        self.assertIsNone(schedule.active)

    def test_snapshot_and_its_error_reporter_exceptions_do_not_poison_scheduler(self):
        for error in (RuntimeError, AuxiliaryAbort):
            with self.subTest(error=error.__name__):
                diagnostics = Diagnostics(snapshot_error=error, error_error=AuxiliaryAbort)
                schedule, clock = self.schedule(diagnostics)
                state = schedule.health()
                self.assertIsInstance(state, dict)
                self.assertFalse(state['diagnostic_snapshot_atomic_with_schedule'])
                self.assert_primary_can_run(schedule, clock)


class TraceOwnershipAuditTests(unittest.TestCase):
    def test_partial_begin_is_detached_and_cannot_collect_later_native_marks(self):
        class PartialBegin(OptionalDiagnostics):
            def begin(self, *args, **kwargs):
                super().begin(*args, **kwargs)
                raise AuxiliaryAbort('synthetic failure after publishing trace')
        diagnostics = PartialBegin(enabled=True)
        schedule = DpuVisionSchedule(diagnostics=diagnostics)
        schedule.next_primary = time.monotonic()+5
        with schedule.optional('sface') as acquired:
            self.assertTrue(acquired)
            diagnostics.native_mark('sface', 'execute_start')
        snapshot = diagnostics.snapshot()
        self.assertEqual(snapshot['active_optional'], {})
        self.assertEqual(snapshot['counters']['sface']['native_attempts'], 0)
        self.assertIsNone(getattr(diagnostics.local, 'trace', None))
        self.assertIsNone(schedule.active)

    def test_late_old_trace_finish_does_not_remove_replacement(self):
        diagnostics = OptionalDiagnostics(enabled=True)
        first = diagnostics.begin('yunet', True, 'active', 20, time.monotonic()+5)
        second = diagnostics.begin('yunet', True, 'active', 20, time.monotonic()+5)
        diagnostics.finish('yunet', first, 1., -1000., 0, False, False, False)
        self.assertIs(diagnostics.active['yunet'], second)
        self.assertIs(diagnostics.local.trace[1], second)
        diagnostics.native_mark('yunet', 'execute_start')
        self.assertEqual(second['native_attempts'], 1)
        diagnostics.discard_current('yunet', second)
        self.assertEqual(diagnostics.snapshot()['active_optional'], {})

    def test_discarding_old_trace_cannot_discard_current_identity(self):
        diagnostics = OptionalDiagnostics(enabled=True)
        first = diagnostics.begin('sface', True, 'active', 20, time.monotonic()+5)
        second = diagnostics.begin('sface', True, 'active', 20, time.monotonic()+5)
        diagnostics.discard_current('sface', first)
        self.assertIs(diagnostics.active['sface'], second)
        self.assertIs(diagnostics.local.trace[1], second)
        diagnostics.discard_current('sface', second)
        self.assertEqual(diagnostics.snapshot()['active_optional'], {})

    def test_explicit_lease_boundaries_and_non_atomic_snapshot_scope_are_retained(self):
        class CaptureTrace(OptionalDiagnostics):
            def begin(self, *args, **kwargs):
                self.captured = super().begin(*args, **kwargs)
                return self.captured
        clock = FakeClock()
        diagnostics = CaptureTrace(enabled=True, clock_ns=lambda: int(clock()*1e9), thread_clock_ns=None)
        schedule = DpuVisionSchedule(clock=clock, diagnostics=diagnostics)
        schedule.next_primary = clock()+1
        with schedule.optional('sface') as acquired:
            self.assertTrue(acquired)
            clock.advance(.002)
        trace = diagnostics.captured
        health = schedule.health()
        self.assertEqual(trace['lease_sequence'], health['lease_sequence'])
        self.assertLessEqual(trace['lease_started_mono_ns'], trace['lease_release_decision_mono_ns'])
        self.assertLessEqual(trace['lease_release_decision_mono_ns'], trace['after_release_observed_mono_ns'])
        self.assertLessEqual(trace['after_release_observed_mono_ns'], trace['optional_end_mono_ns'])
        self.assertFalse(health['diagnostic_snapshot_atomic_with_schedule'])
        self.assertIn('pre-release', health['occupancy_scope'])


class FallbackVisibilityAuditTests(unittest.TestCase):
    def adapter(self, clock, *, fail=False):
        adapter = DpuYuNet.__new__(DpuYuNet)
        adapter._health_lock = threading.Lock()
        adapter.fallback_calls = adapter.fallback_failures = 0
        adapter.fallback_last_ms = None
        adapter.fallback_total_ms = 0.
        adapter.fallback_reason = None
        adapter.schedule = SimpleNamespace(disabled=lambda kind: True, recovery_ready=lambda kind: False,
            optional_status=lambda kind: {'recovery': {'reason': 'synthetic-latched-fault'}})
        def fallback(image):
            clock.advance(.007)
            if fail:
                raise RuntimeError('synthetic CPU fallback failure')
            return []
        def native(image):
            self.fail('fallback must not submit another native model job')
        adapter.fallback = SimpleNamespace(detect=fallback)
        adapter.detector = SimpleNamespace(detect=native)
        return adapter

    def test_cpu_fallback_count_time_and_reason_are_directly_observable(self):
        clock = FakeClock()
        adapter = self.adapter(clock)
        with patch('board.vision.dpu_yunet.time.monotonic', clock):
            self.assertEqual(adapter.detect(None), [])
        health = adapter.health()
        self.assertEqual(health['kind'], 'CPU_YUNET_FALLBACK_AFTER_DPU_OVERRUN')
        self.assertEqual(health['fallback_calls'], 1)
        self.assertEqual(health['fallback_failures'], 0)
        self.assertAlmostEqual(health['fallback_last_ms'], 7.)
        self.assertAlmostEqual(health['fallback_total_ms'], 7.)
        self.assertEqual(health['fallback_reason'], 'synthetic-latched-fault')

    def test_failed_cpu_fallback_is_counted_and_preserves_original_failure(self):
        clock = FakeClock()
        adapter = self.adapter(clock, fail=True)
        with patch('board.vision.dpu_yunet.time.monotonic', clock):
            with self.assertRaisesRegex(RuntimeError, 'synthetic CPU fallback failure'):
                adapter.detect(None)
        health = adapter.health()
        self.assertEqual(health['fallback_calls'], 1)
        self.assertEqual(health['fallback_failures'], 1)
        self.assertAlmostEqual(health['fallback_total_ms'], 7.)


class WorkerLatchingAuditTests(unittest.TestCase):
    @staticmethod
    def wait_for(predicate, timeout=1.):
        until = time.monotonic()+timeout
        gate = threading.Event()
        while time.monotonic() < until:
            if predicate():
                return True
            gate.wait(.005)
        return bool(predicate())

    def test_native_fault_stays_observable_and_does_not_retry_new_packets(self):
        class Detector:
            kind = 'synthetic-native'
            def __init__(self):
                self.calls = 0
            def detect(self, image):
                self.calls += 1
                raise RuntimeError('VART execution failed: synthetic status')
            def close(self):
                pass
        detector = Detector()
        service = FaceTargetService(lambda: detector, lambda *args: None, 'synthetic-epoch', clock=lambda: 1000)
        service.start()
        try:
            service.offer(None, 1, 1000)
            self.assertTrue(self.wait_for(lambda: bool(service.health().get('fault_latched'))))
            health = service.health()
            self.assertFalse(health['ready'])
            self.assertTrue(health['error'])
            self.assertTrue(health['worker_alive'])
            self.assertEqual(health['worker_faults'], 1)
            self.assertIsNone(service.current_target())
            self.assertEqual(service.view()['face_count'], 0)
            service.offer(None, 2, 1000)
            with service.lock:
                self.assertIsNone(service.pending, 'new packet was accepted after an unknown native fault')
            self.assertEqual(detector.calls, 1)
        finally:
            service.close()
        self.assertFalse(service.health()['worker_alive'])

    def test_factory_failure_is_latched_without_repeated_rebuild_or_false_ready(self):
        calls = []
        def factory():
            calls.append(True)
            raise RuntimeError('synthetic detector creation failure')
        service = FaceTargetService(factory, lambda *args: None, 'synthetic-epoch', clock=lambda: 1000)
        service.start()
        try:
            self.assertTrue(self.wait_for(lambda: bool(service.health().get('fault_latched'))))
            health = service.health()
            self.assertFalse(health['ready'])
            self.assertTrue(health['worker_alive'])
            self.assertEqual(health['worker_faults'], 1)
            service.offer(None, 1, 1000)
            with service.lock:
                self.assertIsNone(service.pending)
            self.assertEqual(len(calls), 1)
        finally:
            service.close()

    def test_normal_shutdown_cannot_leave_false_ready_after_worker_exit(self):
        detector = SimpleNamespace(detect=lambda image: [], close=lambda: None)
        service = FaceTargetService(lambda: detector, lambda *args: None, 'synthetic-epoch', clock=lambda: 1000)
        service.start()
        try:
            self.assertTrue(self.wait_for(lambda: service.health()['ready']))
        finally:
            service.close()
        health = service.health()
        self.assertFalse(health['worker_alive'])
        self.assertFalse(health['ready'])


if __name__ == '__main__':
    unittest.main()
