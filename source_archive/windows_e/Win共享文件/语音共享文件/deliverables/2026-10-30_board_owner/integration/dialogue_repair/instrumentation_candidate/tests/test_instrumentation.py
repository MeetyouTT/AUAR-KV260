"""Actual candidate queues/controllers; synthetic inference, PCM and sinks only."""
import ast
from collections import deque
import importlib.util
import json
from pathlib import Path
import sys
import threading
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
INTEGRATION = ROOT.parent.parent
PROJECT = ROOT.parents[4]
sys.path.insert(0, str(PROJECT / 'aura'))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


# Reuse the already frozen public fixtures, then explicitly load both new sources.
support = load('_instrumentation_public_fixtures', INTEGRATION /
    'response_latency/streaming_candidate/tests/test_streaming.py')
jobs_module = load('board.runtime.audio.board_dialogue_jobs', ROOT /
    'after/board/runtime/audio/board_dialogue_jobs.py')
recording_module = load('tools.board_recording', ROOT / 'after/tools/board_recording.py')


class CounterClock:
    def __init__(self): self.now = 10.
    def __call__(self):
        value = self.now
        self.now += .001
        return value


class InstrumentationJobs(unittest.TestCase):
    def make(self):
        controller, store, models, clock = support.setup()
        jobs = jobs_module.BoardDialogueJobs(controller,
            dict(enabled=True, host='192.168.50.1', port=8797, timeout_ms=10000),
            'public-boot', asr=support.Asr(clock),
            scope_provider=lambda meta: dict(kind='conversation', id='a' * 32),
            clock=clock, start_worker=False)
        self.addCleanup(jobs.close)
        return jobs, controller, store, models

    def test_stream_receipt_and_ack_unchanged_with_numeric_diagnostics(self):
        jobs, controller, store, models = self.make()
        jobs.submit(support.clip())
        self.assertTrue(jobs.run_next())
        values = []
        while (item := jobs.poll()) is not None: values.append(item)
        pcm = b''.join(v['pcm'] for v in values if v.get('channel_event', {}).get('kind') == 'audio')
        complete = next(v for v in values if 'network_complete' in v)
        self.assertEqual(len(pcm) // 2, complete['network_complete']['sample_count'])
        self.assertEqual(sum(v.get('channel_event', {}).get('kind') == 'end' for v in values), 1)
        diagnostics = jobs.public()['diagnostics']
        self.assertEqual(diagnostics['guard_calls'], store.events.count('durable') - 4)
        self.assertGreater(diagnostics['guard_calls'], 0)
        self.assertTrue(all(type(v) in (int, float) and v >= 0 for v in diagnostics.values()))
        self.assertLessEqual(diagnostics['progress_queue_peak'], 128)
        self.assertEqual(jobs.public()['latency']['error_class'], 'none')
        diagnostics['guard_calls'] = -9
        self.assertGreater(jobs.public()['diagnostics']['guard_calls'], 0)
        jobs.acknowledge(complete['context'], complete['network_complete'])
        jobs.drain_actions()
        self.assertTrue(jobs.public()['last_playback_ack']['committed'])

    def test_bounded_wait_rechecks_guard_outside_condition_before_append(self):
        jobs, _, _, _ = self.make()
        jobs.submit(support.clip()); job = jobs.waiting
        jobs.progress.extend(dict(sentinel=i) for i in range(128))
        calls = []
        def guard():
            self.assertFalse(jobs.condition._is_owned())
            calls.append(True)
        def wake(_): jobs.progress.popleft()
        with mock.patch.object(jobs.condition, 'wait', side_effect=wake), \
                mock.patch.object(jobs_module.time, 'perf_counter', side_effect=CounterClock()):
            jobs._put(job, dict(public_packet=True), admission_guard=guard)
        self.assertEqual(len(calls), 2)
        self.assertEqual(job.diagnostics['guard_calls'], 2)
        self.assertAlmostEqual(job.diagnostics['guard_total_ms'], 2.)
        self.assertAlmostEqual(job.diagnostics['progress_wait_ms'], 1.)
        self.assertAlmostEqual(job.diagnostics['progress_wait_peak_ms'], 1.)
        self.assertEqual(job.diagnostics['progress_queue_peak'], 128)
        self.assertEqual(len(jobs.progress), 128)
        self.assertEqual(jobs.progress[0], dict(sentinel=1))
        self.assertTrue(jobs.progress[-1]['public_packet'])

    def test_revocation_during_backpressure_never_publishes_next_packet(self):
        jobs, _, _, _ = self.make()
        jobs.submit(support.clip()); job = jobs.waiting
        jobs.progress.extend(dict(sentinel=i) for i in range(128))
        valid = [True]
        def guard():
            if not valid[0]: raise PermissionError('private fixture must not be copied')
        def wake(_):
            valid[0] = False
            jobs.progress.popleft()
        with mock.patch.object(jobs.condition, 'wait', side_effect=wake):
            with self.assertRaises(PermissionError): jobs._put(job, dict(audio=True), admission_guard=guard)
        self.assertEqual(job.diagnostics['guard_calls'], 2)
        self.assertEqual(len(jobs.progress), 127)
        self.assertFalse(any('audio' in item for item in jobs.progress))

    def test_unguarded_wait_and_cancel_preserve_original_queue_semantics(self):
        jobs, _, _, _ = self.make()
        jobs.submit(support.clip()); job = jobs.waiting
        jobs.progress.extend(dict(sentinel=i) for i in range(128))
        def wake(_): job.cancelled.set()
        with mock.patch.object(jobs.condition, 'wait', side_effect=wake):
            with self.assertRaises(support.dialogue.StaleGeneration): jobs._put(job, dict(audio=True))
        self.assertEqual(job.diagnostics['guard_calls'], 0)
        self.assertGreater(job.diagnostics['progress_wait_ms'], 0)
        self.assertEqual(len(jobs.progress), 128)

    def test_failure_keeps_only_current_prepare_metadata_and_fixed_class(self):
        jobs, controller, _, _ = self.make()
        controller.last_prepare_metrics = dict(llm_rpc_ms=99999., text='previous private fixture')
        def fail(*args, **kwargs):
            self.assertEqual(controller.last_prepare_metrics, {})
            controller.last_prepare_metrics = dict(llm_rpc_ms=12., tts_calls=1,
                prepare_total_ms=13., complete=False, text='private fixture', request_id='private-id',
                tts_rpc_ms=float('nan'), context_ms=-1)
            raise ValueError('private failure message')
        controller.prepare_text = fail
        jobs.submit(support.clip()); jobs.run_next()
        phase = jobs.public()['latency']
        self.assertEqual(phase['error_class'], 'ValueError')
        self.assertFalse(phase['complete'])
        self.assertEqual(phase['prepare'], dict(llm_rpc_ms=12., tts_calls=1,
            prepare_total_ms=13., complete=False))
        self.assertNotIn('private', json.dumps(phase))

    def test_failure_before_metrics_cannot_copy_previous_turn_and_unknown_name_is_fixed(self):
        jobs, controller, _, _ = self.make()
        controller.last_prepare_metrics = dict(llm_rpc_ms=99999.)
        failure = type('PrivateArbitraryExceptionName', (Exception,), {})
        def fail(*args, **kwargs): raise failure('private message')
        controller.prepare_text = fail
        jobs.submit(support.clip()); jobs.run_next()
        phase = jobs.public()['latency']
        self.assertEqual(phase['prepare'], {})
        self.assertEqual(phase['error_class'], 'other')
        self.assertNotIn('llm_rpc_ms', phase['prepare'])

    def test_job_original_eighth_positional_cancel_argument_is_preserved(self):
        event = threading.Event()
        job = jobs_module._Job({}, b'', {}, 1., None, None, None, event)
        self.assertIs(job.cancelled, event)
        other = jobs_module._Job({}, b'', {}, 1., None)
        self.assertIsNot(job.diagnostics, other.diagnostics)


class Sink:
    def __init__(self): self.received = []; self.last_error = ''; self.fail = False
    def channel_event(self, header, pcm, *args):
        if self.fail: raise RuntimeError('synthetic sink failure')
        self.received.append((dict(header), pcm))
    def public(self):
        return dict(phase='IDLE', playing=False, paused=False, pending_job=None,
            audio_output_state='IDLE_READY')


class Producer:
    feedback_assets = {}
    def __init__(self): self.items = deque()
    def poll(self): return self.items.popleft() if self.items else None
    def public(self): return dict(enabled=True, pending=False, streaming=True, feedback_ready=True)
    def enabled(self): return True


class InstrumentationRecording(unittest.TestCase):
    def make(self):
        sink, producer = Sink(), Producer()
        owner = recording_module.RecordingController(sink, transcriber=producer)
        owner.transcription.update(state='GENERATING', request_id='public-request', capture_id='public-capture')
        owner.requested_at = 10.
        return owner, sink, producer

    def packet(self, *, foreign=False):
        return dict(context=dict(request_id='other' if foreign else 'public-request', capture_id='public-capture'),
            channel_event=dict(kind='audio'), pcm=b'\x01\x00' * 480)

    def test_eight_packet_limit_original_pcm_and_drain_gap_are_observed(self):
        owner, sink, producer = self.make()
        producer.items.extend(self.packet() for _ in range(10))
        perf = CounterClock()
        with mock.patch.object(recording_module.time, 'perf_counter', side_effect=perf):
            owner._poll_transcription()
            self.assertEqual(len(sink.received), 8)
            self.assertEqual(len(producer.items), 2)
            perf.now += .5
            owner._poll_transcription()
        metrics = owner.public()['stream_diagnostics']
        self.assertEqual(metrics['drain_calls'], 2)
        self.assertEqual(metrics['audio_packets'], 10)
        self.assertEqual(metrics['channel_event_calls'], 10)
        self.assertAlmostEqual(metrics['channel_event_total_ms'], 10.)
        self.assertGreaterEqual(metrics['max_drain_gap_ms'], 500.)
        self.assertTrue(all(pcm == b'\x01\x00' * 480 for _, pcm in sink.received))
        self.assertTrue(all(type(value) in (int, float) and value >= 0 for value in metrics.values()))
        metrics['audio_packets'] = -1
        self.assertEqual(owner.public()['stream_diagnostics']['audio_packets'], 10)

    def test_six_ms_budget_and_foreign_owner_packets_remain_enforced(self):
        owner, sink, producer = self.make()
        producer.items.extend([self.packet(foreign=True), self.packet()])
        with mock.patch.object(recording_module.time, 'monotonic', side_effect=[10., 10.007]):
            owner._poll_transcription()
        self.assertEqual(len(producer.items), 1)
        self.assertFalse(sink.received)
        self.assertEqual(owner.public()['stream_diagnostics']['channel_event_calls'], 0)

    def test_failed_channel_event_time_is_measured_without_claiming_audio_delivered(self):
        owner, sink, producer = self.make(); sink.fail = True
        producer.items.append(self.packet())
        with mock.patch.object(recording_module.time, 'perf_counter', side_effect=CounterClock()):
            with self.assertRaises(RuntimeError): owner._poll_transcription()
        metrics = owner.public()['stream_diagnostics']
        self.assertEqual(metrics['channel_event_calls'], 1)
        self.assertEqual(metrics['audio_packets'], 0)
        self.assertAlmostEqual(metrics['channel_event_total_ms'], 1.)

    def test_new_transcription_resets_numeric_counters_and_idle_does_not_count(self):
        owner, sink, producer = self.make()
        producer.items.append(self.packet()); owner._poll_transcription()
        owner._queue_transcription()  # No utterance; no model, capture or file operations.
        metrics = owner.public()['stream_diagnostics']
        self.assertTrue(all(value == 0 for value in metrics.values()))
        owner._poll_transcription()
        self.assertEqual(owner.public()['stream_diagnostics']['drain_calls'], 0)


if __name__ == '__main__': unittest.main()
