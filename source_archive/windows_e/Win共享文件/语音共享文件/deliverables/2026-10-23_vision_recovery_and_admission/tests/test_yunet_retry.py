"""Synthetic frames, virtual clocks and fake native runner: no DPU needed."""
import bootstrap
from contextlib import contextmanager
import importlib.util
from pathlib import Path
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from board.identity.face_targets import FaceTargetService
import board.identity.face_targets as faces_module
from board.vision.dpu_yunet import DpuYuNet
import board.vision.dpu_yunet as yunet_module
from board.vision.dpu_vision_runtime import (AdmissionCancelled, OptionalJobDisabled,
    PinnedRunner, SlotAdmissionDenied, SlotUnavailable, YuNetNetwork, sface_feature)
import board.vision.dpu_vision_runtime as runtime_module
from board.vision.dpu_vision_schedule import DpuVisionSchedule
from board.vision.pipeline_metrics import OptionalDiagnostics, PipelineMetrics


class Clock:
    def __init__(self): self.now = 1000.
    def monotonic(self): return self.now
    def monotonic_ns(self): return round(self.now*1e9)
    def millis(self): return round(self.now*1000)
    def advance(self, seconds): self.now += seconds


class Native:
    def __init__(self, harness):
        self.h = harness
        self.submitted = self.completed = 0
        self.cost = .004
        self.status = 0
        self.failure = None
        self.before_execute = self.before_wait = None

    def execute_async(self, inputs, outputs):
        self.submitted += 1
        self.h.native_fids.append(self.h.preparer.fids[-1])
        if self.before_execute: self.before_execute()
        if self.failure: raise self.failure
        for output in outputs: output.fill(1)
        return 7

    def wait(self, job):
        assert job == 7
        if self.before_wait: self.before_wait()
        self.h.clock.advance(self.cost)
        if self.status == 0: self.completed += 1
        return self.status


class Preparer:
    def __init__(self, harness):
        self.h = harness
        self.fids = []
        self.before = self.after = None
        self.cost = 0.

    def detect(self, frame):
        self.fids.append(frame)
        if self.before: self.before(frame)
        self.h.clock.advance(self.cost)
        result = self.h.adapter.scheduled(np.zeros((1, 1, 1, 3), dtype=np.float32))
        if result is None: raise SlotUnavailable('ordinary default denial')
        if self.after: self.after(frame)
        return []


class Harness:
    def __init__(self, retry=True):
        self.clock = Clock()
        self.schedule = DpuVisionSchedule(clock=self.clock.monotonic)
        self.schedule.next_primary = self.clock.now+10
        self.publications = []
        self.service = FaceTargetService(lambda: None, lambda *args: self.publications.append(args),
            'synthetic', clock=self.clock.millis, slot_retry=retry, retry_clock=self.clock.monotonic)
        self.service.ready = True
        self.native_fids = []
        self.adapter = DpuYuNet.__new__(DpuYuNet)
        # This fixture bypasses the model-loading constructor; initialize only
        # its new observable fallback state as the real constructor does.
        self.adapter._health_lock = threading.Lock()
        self.adapter.fallback_calls = self.adapter.fallback_failures = 0
        self.adapter.fallback_last_ms = None
        self.adapter.fallback_total_ms = 0.
        self.adapter.fallback_reason = None
        self.adapter.schedule = self.schedule
        self.adapter.kind = 'DPU_YUNET_INT8'
        self.runner = PinnedRunner.__new__(PinnedRunner)
        self.runner.owner = SimpleNamespace(ownership=SimpleNamespace(fileno=lambda: 1))
        self.runner.input_fix = 7
        self.runner.inputs = [SimpleNamespace(dims=[1, 1, 1, 3])]
        self.runner.outputs = [SimpleNamespace(name='synthetic-output', dims=[1, 1], get_attr=lambda _: 0)]
        self.runner.metrics = PipelineMetrics()
        self.runner.stage_kind = 'yunet'
        self.runner.last_ms = None
        self.native = Native(self)
        self.runner.runner = self.native
        self.adapter.runner = self.runner
        self.preparer = Preparer(self)
        self.adapter.detector = self.preparer
        self.fallback_fids = []
        self.adapter.fallback = SimpleNamespace(detect=lambda frame: self.fallback_fids.append(frame) or [])
        self.waits = []
        self.events = []
        self.service.condition.wait = self.wait

    def packet(self, fid, stamp=None):
        return (fid, fid, self.clock.millis() if stamp is None else stamp)

    def offer(self, fid, stamp=None): self.service.offer(*self.packet(fid, stamp))

    def event(self, delay, action):
        self.events.append((self.clock.now+delay, action))
        self.events.sort(key=lambda pair: pair[0])

    def wait(self, timeout=None):
        assert timeout is not None and 0 < timeout <= .201
        assert self.schedule.active != 'yunet', 'waiting while owning DPU slot'
        condition = self.service.condition
        saved = condition._release_save()
        try:
            self.waits.append((self.clock.now, timeout, self.schedule.active))
            end = self.clock.now+timeout
            if self.events and self.events[0][0] <= end+1e-10:
                at, action = self.events.pop(0)
                self.clock.now = max(self.clock.now, at)
                action()
            else:
                self.clock.now = end
        finally:
            condition._acquire_restore(saved)

    @contextmanager
    def clocks(self):
        # Replace each module's time reference, never global time functions.
        fake = SimpleNamespace(monotonic=self.clock.monotonic, monotonic_ns=self.clock.monotonic_ns)
        with patch.object(yunet_module, 'time', fake), patch.object(runtime_module, 'time', fake), \
                patch.object(faces_module, 'time', fake):
            yield

    def run(self, fid=1, packet=None):
        with self.clocks():
            packet = packet or self.packet(fid)
            if self.service.slot_retry:
                return self.service._process_with_retry(packet, self.adapter)
            return self.service.process(packet, self.adapter)

    def deny(self): self.schedule.active = 'yolo'

    def allow(self):
        self.schedule.active = None
        self.schedule.next_primary = self.clock.now+10


class RetryTests(unittest.TestCase):
    def test_default_is_disabled_and_requires_explicit_bool(self):
        service = FaceTargetService(lambda: None, lambda *args: None, 'epoch')
        self.assertFalse(service.slot_retry)
        for value in (1, 'true', None):
            with self.assertRaises(ValueError):
                FaceTargetService(lambda: None, lambda *args: None, 'epoch', slot_retry=value)

    def test_default_denial_still_one_attempt_no_wait_no_publish(self):
        h = Harness(False); h.deny(); h.offer(2)
        h.run()
        self.assertEqual(h.preparer.fids, [1])
        self.assertEqual(h.native.submitted, 0)
        self.assertEqual(h.waits, [])
        self.assertEqual(h.service.pending[1], 2)
        self.assertEqual(h.service.discarded, 1)
        self.assertEqual(h.publications, [])

    def test_default_success_matches_frozen_face_service(self):
        path = bootstrap.ROOT/'baseline/aura/board/identity/face_targets.py'
        spec = importlib.util.spec_from_file_location('frozen_face_targets', path)
        baseline = importlib.util.module_from_spec(spec); spec.loader.exec_module(baseline)
        outputs = []
        for cls in (baseline.FaceTargetService, FaceTargetService):
            publications = []
            service = cls(lambda: None, lambda *args: publications.append(args), 'epoch', clock=lambda: 1000)
            service.ready = True
            service.process(('synthetic', 1, 999), SimpleNamespace(detect=lambda _: [], kind='synthetic'))
            outputs.append((service.processed, service.discarded, service.stamp, service.view(), publications))
        self.assertEqual(outputs[0], outputs[1])

    def test_retry_uses_latest_pending_after_25ms(self):
        h = Harness(); h.deny(); began = h.clock.now
        h.event(.005, lambda: h.offer(2))
        h.event(.015, lambda: h.offer(3))
        h.event(.025, h.allow)
        h.run()
        self.assertEqual(h.preparer.fids, [1, 3])
        self.assertEqual(h.native_fids, [3])
        self.assertEqual(h.native.completed, 1)
        self.assertGreaterEqual(h.clock.now-began, .025)
        self.assertEqual(h.service.retry_health()['retries'], 1)
        self.assertEqual(h.publications[0][2], 3)

    def test_repeated_denial_max_three_cpu_preparations(self):
        h = Harness(); h.deny()
        h.event(.010, lambda: h.offer(2))
        h.event(.040, lambda: h.offer(3))
        h.event(.080, lambda: h.offer(4))
        h.run()
        self.assertEqual(h.preparer.fids, [1, 2, 3])
        self.assertEqual(h.native.submitted, 0)
        self.assertEqual(h.service.retry_health()['denied'], 3)
        self.assertEqual(h.service.retry_health()['exhausted'], 1)
        self.assertLess(h.clock.now, 1000.080)

    def test_without_new_frame_waits_to_deadline_without_repreparing(self):
        h = Harness(); h.deny(); began = h.clock.now
        h.run()
        self.assertEqual(h.preparer.fids, [1])
        self.assertAlmostEqual(h.clock.now-began, .200)
        self.assertEqual(h.service.retry_health()['deadline'], 1)
        self.assertEqual(h.native.submitted, 0)

    def test_old_or_expired_pending_cannot_spend_retry(self):
        h = Harness(); h.deny()
        h.event(.005, lambda: h.offer(1))
        h.event(.040, lambda: h.offer(2, h.clock.millis()-1001))
        h.event(.080, lambda: h.offer(3, h.clock.millis()+1))
        h.run()
        self.assertEqual(h.preparer.fids, [1])
        self.assertEqual(h.service.retry_health()['retries'], 0)
        self.assertEqual(h.native.submitted, 0)

    def test_close_during_backoff_stops_without_preparation(self):
        h = Harness(); h.deny()
        h.event(.010, h.service.close)
        h.run()
        self.assertEqual(h.preparer.fids, [1])
        self.assertEqual(h.service.retry_health()['closed'], 1)
        self.assertIsNone(h.service.pending)

    def test_wait_releases_state_lock_and_holds_no_dpu_slot(self):
        h = Harness(); h.deny(); completed = []
        def producer():
            thread = threading.Thread(target=lambda: (h.offer(2), completed.append(True)))
            thread.start(); thread.join(.5)
            self.assertFalse(thread.is_alive(), 'Condition.wait did not release producer lock')
            h.allow()
        h.event(.030, producer)
        h.run()
        self.assertEqual(completed, [True])
        self.assertEqual(h.native_fids, [2])

    def test_retry_cpu_preparation_crossing_deadline_prevents_admission(self):
        h = Harness(); h.deny()
        def allow_slow():
            h.offer(2); h.allow(); h.preparer.cost = .190
        h.event(.025, allow_slow)
        h.run()
        self.assertEqual(h.preparer.fids, [1, 2])
        self.assertEqual(h.native.submitted, 0)
        self.assertEqual(h.service.retry_health()['deadline'], 1)
        self.assertGreater(h.service.retry_health()['maximum_deadline_overrun_ms'], 0)
        self.assertEqual(h.schedule.health()['optional']['yunet']['calls'], 0)

    def test_initial_cpu_preparation_has_ttl_recheck_before_admission(self):
        h = Harness(); h.preparer.cost = 1.001
        h.run()
        self.assertEqual(h.native.submitted, 0)
        self.assertEqual(h.service.retry_health()['expired'], 1)
        self.assertNotIn('yunet', h.schedule.jobs)

    def test_closed_during_cpu_preparation_prevents_admission(self):
        h = Harness(); h.preparer.before = lambda _: h.service.close()
        h.run()
        self.assertEqual(h.native.submitted, 0)
        self.assertEqual(h.service.retry_health()['closed'], 1)

    def test_initial_stale_packet_does_not_start_preparation(self):
        h = Harness()
        h.run(packet=h.packet(1, h.clock.millis()-1000))
        self.assertEqual(h.preparer.fids, [])
        self.assertEqual(h.native.submitted, 0)

    def test_round_deadline_does_not_carry_into_new_round(self):
        h = Harness(); h.deny(); h.run()
        h.clock.advance(.201); h.allow(); h.run(2)
        self.assertEqual(h.native_fids, [2])
        self.assertEqual(h.service.retry_health()['rounds'], 2)

    def test_success_and_no_face_do_not_retry(self):
        h = Harness(); h.offer(2); h.run()
        self.assertEqual(h.native.completed, 1)
        self.assertEqual(h.preparer.fids, [1])
        self.assertEqual(h.service.pending[1], 2)
        self.assertEqual(h.service.retry_health()['retries'], 0)

    def test_ordinary_slotunavailable_is_not_retry_signal(self):
        h = Harness()
        detector = SimpleNamespace(detect=lambda _: (_ for _ in ()).throw(SlotUnavailable('other')))
        h.service._process_with_retry(h.packet(1), detector)
        self.assertEqual(h.waits, [])
        self.assertEqual(h.service.retry_health()['denied'], 0)

    def test_cancelled_and_disabled_are_not_retry_signals(self):
        for exception in (AdmissionCancelled('closed'), OptionalJobDisabled('protected')):
            h = Harness()
            detector = SimpleNamespace(detect=lambda _, exception=exception: (_ for _ in ()).throw(exception))
            h.service._process_with_retry(h.packet(1), detector)
            self.assertEqual(h.waits, [])
            self.assertEqual(h.service.retry_health()['retries'], 0)

    def test_native_exception_is_not_retried(self):
        h = Harness(); h.native.failure = RuntimeError('synthetic native failure'); h.offer(2)
        with self.assertRaisesRegex(RuntimeError, 'native completion was not confirmed'): h.run()
        self.assertTrue(h.schedule.owner_fenced)
        self.assertEqual(h.native.submitted, 1)
        self.assertEqual(h.native.completed, 0)
        self.assertEqual(h.waits, [])
        self.assertIsNone(h.schedule.active)

    def test_nonzero_vart_status_is_not_retried(self):
        h = Harness(); h.native.status = -1
        with self.assertRaisesRegex(RuntimeError, 'VART execution failed'): h.run()
        self.assertEqual(h.native.submitted, 1)
        self.assertEqual(h.native.completed, 0)
        self.assertEqual(h.waits, [])

    def test_disabled_job_preserves_original_cpu_fallback_no_retry(self):
        for retry in (False, True):
            h = Harness(retry)
            h.schedule.jobs['yunet'] = {'disabled': True}
            h.run()
            self.assertEqual(h.fallback_fids, [1])
            self.assertEqual(h.native.submitted, 0)
            self.assertEqual(h.waits, [])
            self.assertEqual(h.service.backend, 'CPU_YUNET_FALLBACK_AFTER_DPU_OVERRUN')

    def test_schedule_disables_between_detect_and_admission_no_retry(self):
        h = Harness()
        h.preparer.before = lambda _: h.schedule.jobs.update(yunet={'disabled': True, 'skipped': 0, 'estimated_budget_ms': 20.})
        h.run()
        self.assertEqual(h.preparer.fids, [1])
        self.assertEqual(h.native.submitted, 0)
        self.assertEqual(h.service.retry_health()['disabled'], 1)
        self.assertEqual(h.waits, [])

    def test_hard_30ms_protection_unchanged_after_success(self):
        h = Harness(); h.native.cost = .031
        h.run()
        self.assertEqual(h.native.completed, 1)
        stats = h.schedule.health()['optional']['yunet']
        self.assertEqual(stats['overruns'], 1)
        self.assertTrue(stats['disabled'])
        self.assertEqual(h.service.retry_health()['retries'], 0)
        h.clock.advance(.2); h.run(2)
        self.assertEqual(h.fallback_fids, [2])
        self.assertEqual(h.native.submitted, 1)

    def test_guard_5ms_protection_unchanged(self):
        h = Harness(); h.schedule.next_primary = h.clock.now+.026; h.native.cost = .022
        h.run()
        stats = h.schedule.health()['optional']['yunet']
        self.assertEqual(stats['overruns'], 1)
        self.assertTrue(stats['disabled'])
        self.assertLess(stats['maximum_ms'], 30)

    def test_waiting_primary_keeps_priority(self):
        h = Harness(); h.schedule.waiting_primary = 1
        h.event(.010, lambda: h.offer(2))
        h.run()
        self.assertEqual(h.native.submitted, 0)
        self.assertEqual(h.service.retry_health()['denied'], 2)

    def test_execute_start_diagnostic_delay_rechecks_absolute_deadline(self):
        h = Harness(); h.deny()
        h.event(.025, lambda: (h.allow(), h.offer(2)))
        original = h.runner._diagnostic_mark
        def delayed(phase, status=None):
            original(phase, status)
            if phase == 'execute_start': h.clock.advance(.180)
        h.runner._diagnostic_mark = delayed
        h.run()
        self.assertEqual(h.native.submitted, 0)
        self.assertEqual(h.service.retry_health()['deadline'], 1)
        self.assertIsNone(h.schedule.active)
        # It acquired a slot but withdrew; scheduler calls is NOT native count.
        self.assertEqual(h.schedule.health()['optional']['yunet']['calls'], 1)

    def test_denial_diagnostic_delay_cannot_move_round_deadline_later(self):
        h = Harness(); h.deny(); began = h.clock.now
        class Diagnostics:
            enabled = True
            def begin(self, *args): h.clock.advance(.210)
            def error(self): raise AssertionError('diagnostic failed')
        h.schedule.diagnostics = Diagnostics()
        h.run()
        self.assertEqual(h.preparer.fids, [1])
        self.assertEqual(h.waits, [])
        self.assertEqual(h.service.retry_health()['deadline'], 1)
        self.assertGreater(h.clock.now-began, .200)

    def test_slow_denial_still_waits_25ms_after_bookkeeping(self):
        h=Harness();h.deny();began=h.clock.now
        class Diagnostics:
            enabled=True
            def begin(self,*args):h.clock.advance(.030)
            def error(self):raise AssertionError('diagnostic failed')
        h.schedule.diagnostics=Diagnostics()
        h.offer(2);h.run()
        self.assertGreater(len(h.waits),0)
        self.assertAlmostEqual(h.waits[0][0]-began,.030)
        self.assertGreaterEqual(h.waits[0][1],.025-1e-10)

    def test_retry_health_is_visible_only_when_enabled(self):
        self.assertNotIn('slot_retry',Harness(False).service.health())
        h=Harness(True);self.assertEqual(h.service.health()['slot_retry']['withdrawn_after_slot'],0)

    def test_preexecute_state_lock_contention_withdraws_without_waiting_in_slot(self):
        h = Harness(); locked = threading.Event(); release = threading.Event()
        def holder():
            with h.service.lock:
                locked.set(); release.wait(1.)
        thread = threading.Thread(target=holder)
        original = h.runner._diagnostic_mark
        def mark(phase, status=None):
            original(phase, status)
            if phase == 'execute_start':
                thread.start(); self.assertTrue(locked.wait(.5))
        h.runner._diagnostic_mark = mark
        # Observe release *before* process's ordinary accounting needs the lock.
        original_optional = h.schedule.optional
        @contextmanager
        def optional(kind):
            try:
                with original_optional(kind) as acquired: yield acquired
            finally:
                self.assertIsNone(h.schedule.active)
                release.set()
        h.schedule.optional = optional
        try:
            h.run()
        finally:
            release.set()
            if thread.ident is not None: thread.join(.5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(h.native.submitted, 0)
        self.assertEqual(h.service.retry_health()['busy'], 1)
        self.assertEqual(h.waits, [])

    def test_ttl_crossed_during_execute_start_diagnostics_prevents_native(self):
        h = Harness()
        h.runner._diagnostic_mark = lambda phase, status=None: h.clock.advance(1.001) if phase == 'execute_start' else None
        h.run()
        self.assertEqual(h.native.submitted, 0)
        self.assertEqual(h.service.retry_health()['expired'], 1)

    def test_native_started_before_deadline_may_finish_after_deadline(self):
        h = Harness(); h.deny()
        h.event(.180, lambda: (h.allow(), h.offer(2)))
        h.native.cost = .025
        h.run()
        self.assertEqual(h.native.submitted, 1)
        self.assertEqual(h.native.completed, 1)
        self.assertGreater(h.service.retry_health()['maximum_deadline_overrun_ms'], 0)

    def test_retry_denials_preserve_original_stamp_and_ttl(self):
        h = Harness(); h.service.stamp = h.clock.millis()-900
        h.deny(); old = h.service.stamp
        h.run()
        self.assertEqual(h.service.stamp, old)
        self.assertEqual(h.service.processed, 0)
        self.assertIsNone(h.service.current_target())

    def test_worker_keeps_200ms_interval_after_no_face_success(self):
        for retry in (False, True):
            h = Harness(retry)
            h.service.factory = lambda: h.adapter
            h.service.pending = h.packet(1)
            h.preparer.after = lambda _: h.offer(2)
            h.event(.010, h.service.close)
            with h.clocks(): h.service.work()
            self.assertEqual(h.preparer.fids, [1])
            self.assertEqual(h.service.processed, 1)
            self.assertAlmostEqual(h.waits[0][1], .200)
            self.assertIsNone(h.runner.runner)

    def test_successful_native_finishing_after_source_ttl_is_not_published(self):
        h = Harness(); h.native.cost = 1.001
        h.run()
        self.assertEqual(h.native.completed, 1)
        self.assertEqual(h.service.processed, 0)
        self.assertEqual(h.publications, [])
        self.assertEqual(h.service.discarded, 1)

    def test_encode_delay_is_part_of_retry_admission_deadline(self):
        h = Harness(); h.deny()
        original = yunet_module.encode
        def delayed(values, fix):
            if h.preparer.fids[-1] == 2: h.clock.advance(.180)
            return original(values, fix)
        h.event(.025, lambda: (h.allow(), h.offer(2)))
        with patch.object(yunet_module, 'encode', delayed): h.run()
        self.assertEqual(h.preparer.fids, [1, 2])
        self.assertEqual(h.native.submitted, 0)
        self.assertEqual(h.service.retry_health()['deadline'], 1)

    def test_retry_exactly_at_absolute_deadline_cannot_start_cpu_preparation(self):
        h = Harness(); h.deny()
        h.event(.200, lambda: (h.allow(), h.offer(2)))
        h.run()
        self.assertEqual(h.preparer.fids, [1])
        self.assertEqual(h.native.submitted, 0)
        self.assertEqual(h.service.retry_health()['deadline'], 1)

    def test_native_guard_is_cleared_after_failure_for_next_round(self):
        h = Harness(); h.native.failure = RuntimeError('synthetic failure')
        with self.assertRaises(RuntimeError): h.run()
        self.assertIsNone(h.adapter._admission_check)
        h.native.failure = None; h.clock.advance(.2); h.allow(); h.run(2)
        # Cleanup does not authorize reuse after an unconfirmed native failure.
        self.assertTrue(h.schedule.disabled('yunet'))
        self.assertEqual(h.native_fids, [1])
        self.assertEqual(h.fallback_fids, [2])
        self.assertEqual(h.native.completed, 0)

    def test_diagnostic_completion_stays_zero_on_withdrawal(self):
        h = Harness(); h.deny()
        diagnostics = OptionalDiagnostics(enabled=True, clock_ns=h.clock.monotonic_ns,
            thread_clock_ns=lambda: 1)
        h.schedule.diagnostics = diagnostics
        h.runner.metrics.optional_diagnostics = diagnostics
        original = h.runner._diagnostic_mark
        def delayed(phase, status=None):
            original(phase, status)
            if phase == 'execute_start': h.clock.advance(.180)
        h.runner._diagnostic_mark = delayed
        h.event(.025, lambda: (h.allow(), h.offer(2)))
        h.run()
        row = diagnostics.snapshot()['counters']['yunet']
        self.assertEqual(row['native_completed'], 0)
        self.assertEqual(row['native_execute_returned'], 0)
        self.assertEqual(h.native.submitted, 0)
        self.assertEqual(h.schedule.health()['optional']['yunet']['calls'], 1)
        # Existing execute_start/exception diagnostics include guarded withdrawal.
        self.assertEqual(row['native_attempts'], 1)
        self.assertEqual(row['native_failed'], 1)
        self.assertEqual(h.service.retry_health()['withdrawn_after_slot'],1)

    def test_sface_runtime_default_api_unchanged(self):
        h = Harness()
        h.runner.stage_kind = 'sface'
        h.runner.inputs = [SimpleNamespace(dims=[1, 112, 112, 3])]
        h.runner.outputs = [SimpleNamespace(name='features', dims=[1, 128], get_attr=lambda _: 5)]
        # This runtime path does not touch DpuYuNet or a FaceTargetService guard.
        h.preparer.fids.append(99)
        with h.clocks(): feature = sface_feature(np.zeros((112, 112, 3), np.uint8), h.runner)
        np.testing.assert_array_equal(feature, np.full(128, 1/32, np.float32))
        self.assertEqual(h.native.completed, 1)
        self.assertEqual(h.service.retry_health()['rounds'], 0)


if __name__ == '__main__': unittest.main()
