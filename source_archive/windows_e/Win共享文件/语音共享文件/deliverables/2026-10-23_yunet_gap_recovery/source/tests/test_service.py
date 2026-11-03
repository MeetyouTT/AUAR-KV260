"""20 service behavior cases adapted from frozen full23, not the full23 suite.
Independent per-attempt wall/CPU and cross-clock comparisons are omitted.
"""
import copy
import hashlib
import importlib.util
import json
import sys
import threading
import types
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / 'candidate/aura/board/identity'
BASELINE = ROOT / 'baseline/aura/board/identity/face_targets.py'
BASELINE_SHA = 'd03e2aee39a43f31705494dd679ad4ce7d9b49ddf7bd1185f5e021cdb8990aa0'
FACE = (10, 20, 60, 70, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, .99)


class SlotUnavailable(RuntimeError):
    pass


class SlotAdmissionDenied(SlotUnavailable):
    pass


class AdmissionCancelled(RuntimeError):
    pass


class OptionalJobDisabled(RuntimeError):
    pass


class Clock:
    def __init__(self, ms=100):
        self.ms = ms
        self.source_calls = self.mono_calls = self.cpu_calls = 0
        self.source_hook = None

    def source(self):
        self.source_calls += 1
        if self.source_hook:
            self.source_hook(self)
        return self.ms

    def mono(self):
        self.mono_calls += 1
        return self.ms / 1000

    def wall_ns(self):
        return round(self.ms * 1000000)

    def cpu_ns(self):
        self.cpu_calls += 1
        return self.cpu_calls * 1000


class Tracks:
    def __init__(self, *args, **kwargs):
        self.tracks = {}
        self.hook = None

    def update(self, *args):
        if self.hook:
            self.hook()
        return {'tracks': []}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self.assertEqual(hashlib.sha256(BASELINE.read_bytes()).hexdigest(), BASELINE_SHA)
        self.recorder_module = load('audit_metrics', CANDIDATE / 'face_freshness_metrics.py')
        dependencies = {
            'board.interaction.ui_contract': types.SimpleNamespace(millis=lambda: 0),
            'board.vision.reference_core': types.SimpleNamespace(FaceTracks=Tracks, valid_box=lambda *a: None),
            'board.vision.dpu_vision_runtime': types.SimpleNamespace(SlotUnavailable=SlotUnavailable,
                SlotAdmissionDenied=SlotAdmissionDenied, AdmissionCancelled=AdmissionCancelled,
                OptionalJobDisabled=OptionalJobDisabled),
            'board.identity.face_freshness_metrics': self.recorder_module,
        }
        self.modules = patch.dict(sys.modules, dependencies)
        self.modules.start()
        self.addCleanup(self.modules.stop)
        self.old = load('audit_old_service', BASELINE)
        self.new = load('audit_candidate_service', CANDIDATE / 'face_targets.py')

    def make(self, enabled=None, old=False, callback=None):
        clock = Clock()
        module = self.old if old else self.new
        module.time = types.SimpleNamespace(monotonic=clock.mono)
        calls = []
        callback = callback if callback is not None else lambda *args: calls.append(args[2:])
        kwargs = {'clock': clock.source}
        if enabled is not None:
            kwargs['freshness_metrics'] = enabled
        service = module.FaceTargetService(lambda: None, callback, 'SYNTHETIC', **kwargs)
        service.ready = True
        return service, clock, calls

    def detector(self, rows=(), hook=None):
        class Detector:
            kind = 'SYNTHETIC_DETECTOR'
            calls = 0

            def detect(self, image):
                self.calls += 1
                if hook:
                    hook()
                return rows
        return Detector()

    def metrics(self, service):
        return service.health()['freshness_metrics']

    def test_default_off_matches_baseline_normal_without_extra_clocks(self):
        states = []
        for old in (True, False):
            service, clock, calls = self.make(old=old)
            detector = self.detector(hook=lambda: setattr(clock, 'ms', clock.ms + 40))
            service.process((object(), 1, 80), detector)
            states.append((service.health(), clock.source_calls, clock.mono_calls,
                           clock.cpu_calls, detector.calls, len(calls)))
            service.close()
        self.assertEqual(states[0], states[1])
        self.assertNotIn('freshness_metrics', states[1][0])
        self.assertEqual(states[1][3], 0)

    def test_default_off_does_not_construct_recorder(self):
        with patch.object(self.recorder_module, 'FaceFreshnessMetrics', side_effect=AssertionError('must not import/construct')):
            service, _, _ = self.make()
        self.assertIsNone(service._freshness)

    def test_default_slot_unavailable_same_state_and_clock_calls(self):
        states = []
        def denied():
            raise SlotUnavailable('synthetic')
        for old in (True, False):
            service, clock, calls = self.make(old=old)
            service.stamp = 10
            service.processed = 7
            service.process((object(), 1, 80), self.detector(hook=denied))
            states.append((service.health(), clock.source_calls, clock.mono_calls, len(calls)))
        self.assertEqual(states[0], states[1])

    def test_default_worker_200ms_after_denial_is_unchanged(self):
        values = []
        for old in (True, False):
            service, clock, _ = self.make(old=old)
            clock.ms = 0
            starts = []
            class Condition:
                waits = 0
                def __enter__(self):
                    return self
                def __exit__(self, *args):
                    return False
                def wait_for(self, predicate):
                    if not service.closed and service.pending is None:
                        service.pending = (object(), len(starts)+1, clock.ms)
                    assert predicate()
                def wait(self, duration):
                    self.waits += 1
                    assert self.waits <= 4, 'virtual wait failed to advance'
                    # Step past the floating-point deadline by 1 ns instead of
                    # rounding a sub-millisecond remainder to zero forever.
                    clock.ms += duration*1000 + .000001
                    service.pending = (object(), len(starts)+1, clock.ms)
            def denied():
                starts.append(clock.ms)
                clock.ms += 40
                if len(starts) == 2:
                    service.closed = True
                raise SlotUnavailable('synthetic')
            service.condition = Condition()
            service.factory = lambda: self.detector(hook=denied)
            service.work()
            values.append((starts, service.discarded, service.error))
        self.assertEqual(values[0], values[1])
        self.assertEqual(values[1][0][0], 0)
        self.assertAlmostEqual(values[1][0][1], 240, delta=.00001)
        self.assertEqual(values[1][1:], (2, ''))

    def test_enabled_offer_latest_replacements_no_frame_retention(self):
        service, _, _ = self.make(enabled=True)
        image = object()
        for fid in range(1, 4):
            service.offer(image, fid, 80)
        health = self.metrics(service)
        self.assertEqual(health['counters']['offers'], 3)
        self.assertEqual(health['counters']['latest_replaced'], 2)
        self.assertIs(service.pending[0], image)
        self.assertEqual(service.pending[1], 3)
        self.assertEqual(set(health['counters']), set(self.recorder_module.COUNTERS))
        json.dumps(health, allow_nan=False)

    def test_enabled_negative_and_positive_are_distinct_from_drops(self):
        service, clock, _ = self.make(enabled=True)
        for rows in ((), (FACE,), (FACE, FACE)):
            service.process((object(), 1, clock.ms-20), self.detector(rows))
            clock.ms += 200
        counters = self.metrics(service)['counters']
        self.assertEqual((counters['published'], counters['published_negative'],
                          counters['published_positive'], counters['published_multiface']), (3, 1, 2, 1))
        self.assertEqual(counters['input_ttl_discarded'], 0)
        self.assertEqual(counters['publish_ttl_discarded'], 0)

    def test_slot_rejections_preserve_stamp_and_track_streak(self):
        service, clock, calls = self.make(enabled=True)
        service.stamp = 0
        def denied():
            raise SlotUnavailable('synthetic')
        for _ in range(3):
            service.process((object(), 1, clock.ms), self.detector(hook=denied))
        self.assertEqual(service.stamp, 0)
        self.assertEqual(len(calls), 0)
        first = self.metrics(service)['counters']
        self.assertEqual(first['maximum_consecutive_slot_rejections'], 3)
        self.assertEqual(first['consecutive_slot_rejections'], 3)
        service.process((object(), 2, clock.ms), self.detector())
        last = self.metrics(service)['counters']
        self.assertEqual(last['maximum_consecutive_slot_rejections'], 3)
        self.assertEqual(last['consecutive_slot_rejections'], 0)

    def test_input_ttl_drop_does_not_prepare_or_fake_zero_age(self):
        service, clock, _ = self.make(enabled=True)
        clock.ms = 1000
        detector = self.detector()
        service.process((object(), 1, 0), detector)
        service.process((object(), 2, 1100), detector)
        health = self.metrics(service)
        self.assertEqual(detector.calls, 0)
        self.assertEqual(health['counters']['input_ttl_discarded'], 2)
        self.assertEqual(health['counters']['invalid_source_ages'], 1)
        self.assertEqual(health['summaries']['input_source_age_ms']['count'], 1)
        self.assertEqual(health['summaries']['input_source_age_ms']['min_ms'], 1000)

    def test_post_detect_ttl_and_close_drops_are_separate(self):
        service, clock, _ = self.make(enabled=True)
        detector = self.detector(hook=lambda: setattr(clock, 'ms', 1200))
        service.process((object(), 1, 80), detector)
        clock.ms = 1300
        service.process((object(), 2, 1300), self.detector(hook=lambda: setattr(service, 'closed', True)))
        counters = self.metrics(service)['counters']
        self.assertEqual((counters['publish_ttl_discarded'], counters['closed_after_detect_discarded']), (1, 1))
        self.assertEqual(counters['published'], 0)

    def test_gap_uses_previous_source_stamp_plus_ttl(self):
        service, clock, _ = self.make(enabled=True)
        service.process((object(), 1, 0), self.detector())
        clock.ms = 1500
        service.process((object(), 2, 1450), self.detector())
        health = self.metrics(service)
        for name in ('clipped_gap_lower_bound_ms', 'clipped_gap_upper_bound_ms'):
            self.assertEqual(health['summaries'][name]['last_ms'], 500)
        self.assertEqual(health['summaries']['post_commit_interval_ms']['last_ms'], 1400)
        self.assertEqual(health['counters']['definite_clipped_gap_intervals'], 1)

    def test_precheck_and_post_commit_observation_bound_gap(self):
        service, clock, _ = self.make(enabled=True)
        service.process((object(), 1, 0), self.detector())
        clock.ms = 1450
        service.tracker.hook = lambda: setattr(clock, 'ms', 1550)
        service.process((object(), 2, 1400), self.detector())
        health = self.metrics(service)
        self.assertEqual(health['summaries']['clipped_gap_lower_bound_ms']['last_ms'], 450)
        self.assertEqual(health['summaries']['clipped_gap_upper_bound_ms']['last_ms'], 550)

    def test_delayed_observation_at_ttl_is_not_a_ttl_gate_failure(self):
        service, clock, _ = self.make(enabled=True)
        clock.ms = 1400
        def delayed(c):
            if c.source_calls == 3:
                c.ms += 200
        clock.source_hook = delayed
        service.process((object(), 1, 500), self.detector())
        health = self.metrics(service)
        self.assertEqual(service.processed, 1)
        self.assertEqual(health['summaries']['pre_commit_source_age_ms']['last_ms'], 900)
        self.assertEqual(health['summaries']['post_commit_source_age_ms']['last_ms'], 1100)
        self.assertEqual(health['counters']['post_commit_at_or_over_ttl'], 1)
        self.assertEqual(health['counters']['publish_ttl_discarded'], 0)

    def test_callback_exception_preserves_business_exception(self):
        def failed(*args):
            raise RuntimeError('original callback error')
        service, clock, _ = self.make(enabled=True, callback=failed)
        with self.assertRaisesRegex(RuntimeError, 'original callback error'):
            service.process((object(), 1, 80), self.detector())
        counters = self.metrics(service)['counters']
        self.assertEqual((counters['published'], counters['callback_errors']), (1, 1))
        self.assertEqual(counters['active_attempts'], 0)

    def test_detect_exception_preserves_business_exception(self):
        def failed():
            raise ValueError('original detector error')
        service, _, _ = self.make(enabled=True)
        with self.assertRaisesRegex(ValueError, 'original detector error'):
            service.process((object(), 1, 80), self.detector(hook=failed))
        health = self.metrics(service)
        self.assertEqual(health['counters']['process_errors'], 1)
        self.assertEqual(health['counters']['active_attempts'], 0)

    def test_observer_raising_cannot_break_process_or_health(self):
        service, _, calls = self.make(enabled=True)
        class Broken:
            def __getattr__(self, name):
                raise RuntimeError('observer only')
        service._freshness = Broken()
        service.offer(object(), 1, 80)
        service.process((object(), 1, 80), self.detector())
        health = self.metrics(service)
        self.assertEqual(service.processed, 1)
        self.assertEqual(len(calls), 1)
        self.assertTrue(health['observer_unavailable'])
        self.assertGreaterEqual(health['observer_failures'], 3)
        service.close()

    def test_bad_begin_token_and_malformed_packet_do_not_replace_business_error(self):
        service, _, _ = self.make(enabled=True)
        service._freshness.begin = lambda stamp: object()
        with self.assertRaises(ValueError):
            service.process((object(), 1), self.detector())
        self.assertEqual(service._freshness_failures, 1)




    def test_snapshot_detached_and_concurrent_updates_consistent(self):
        service, _, _ = self.make(enabled=True)
        worker = threading.Thread(target=lambda: [service.offer(object(), i, 80) for i in range(8)])
        worker.start()
        samples = [self.metrics(service) for _ in range(8)]
        worker.join(2)
        self.assertFalse(worker.is_alive())
        for sample in samples:
            counters = sample['counters']
            self.assertEqual(counters['offers'], counters['offers_accepted']+counters['offers_closed'])
            self.assertLessEqual(len(sample['events']), sample['event_capacity'])
        sample = self.metrics(service)
        sample['counters']['offers'] = -1
        self.assertEqual(self.metrics(service)['counters']['offers'], 8)

    def test_events_bounded_and_counters_saturate(self):
        service, clock, _ = self.make(enabled=True)
        def denied():
            raise SlotUnavailable('synthetic')
        for _ in range(24):
            service.process((object(), 1, clock.ms), self.detector(hook=denied))
        health = self.metrics(service)
        self.assertEqual(len(health['events']), 16)
        self.assertEqual(health['counters']['events_evicted'], 8)
        service._freshness_failures = (1 << 63)-1
        service._freshness_failed()
        self.assertEqual(service._freshness_failures, (1 << 63)-1)
        with service._freshness.lock:
            service._freshness.counters['offers'] = (1 << 63)-1
            service._freshness.inc('offers')
        self.assertEqual(self.metrics(service)['counters']['counter_saturation'], 1)

    def test_close_idempotent_and_frozen_collection(self):
        service, _, _ = self.make(enabled=True)
        service.process((object(), 1, 80), self.detector())
        service.close()
        first = copy.deepcopy(self.metrics(service))
        service.close()
        service.offer(object(), 2, 80)
        last = self.metrics(service)
        self.assertEqual(first, last)
        self.assertFalse(last['collecting'])
        self.assertTrue(last['closed'])

    def test_constructor_failure_is_visible_and_business_still_runs(self):
        with patch.object(self.recorder_module, 'FaceFreshnessMetrics', side_effect=RuntimeError('observer init')):
            service, _, _ = self.make(enabled=True)
        service.process((object(), 1, 80), self.detector())
        health = self.metrics(service)
        self.assertTrue(health['observer_unavailable'])
        self.assertEqual(health['observer_failures'], 1)
        self.assertEqual(service.processed, 1)


if __name__ == '__main__':
    unittest.main()
