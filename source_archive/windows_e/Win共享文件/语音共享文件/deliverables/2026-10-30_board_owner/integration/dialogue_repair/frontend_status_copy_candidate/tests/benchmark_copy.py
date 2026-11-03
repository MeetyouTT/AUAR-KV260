"""Local synthetic fixed-status copy only; no end-to-end/ARM CPU claim."""
import copy
import importlib.util
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


if __name__ == '__main__':
    path = ROOT / 'tests/test_status_copy.py'
    spec = importlib.util.spec_from_file_location('_copy_benchmark_fixtures', path)
    module = importlib.util.module_from_spec(spec); sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    candidate = module.module
    value = module.status()
    value['audio_frontend'].update(frames=12000, processed_samples=3839744, last_roundtrip_ms=15.2,
        max_roundtrip_ms=48.2, worker_pid=12345, worker_generation=7, enabled=True, closed=False,
        capture_lease_closed=False, worker_process_alive=True, worker_capture_process=True,
        endpoint_feed_calls=12000, endpoint_feed_wall_last_ms=18.8, endpoint_feed_wall_max_ms=56.,
        endpoint_feed_wall_total_ms=225600., endpoint_feed_cpu_last_ms=17.4,
        endpoint_feed_cpu_max_ms=39., endpoint_feed_cpu_total_ms=208800., consumer_gap_last_ms=20.,
        consumer_gap_max_ms=61., consumer_gap_total_ms=239980., consumer_gap_count=11999)
    value['input_queue'].update(frame_bytes=640, capacity_ms=160, queued_frames=2,
        frames_read=12003, frames_delivered=12001, source_read_mean_ms=20., source_read_max_ms=830.,
        queue_mean_ms=19., queue_max_ms=80., enabled=True, eof=False, closed=False,
        cancelled=False, reader_alive=True)
    value = candidate.validate_status(value)
    failure = dict(error_code='pcm_input_queue_overflow', from_error_status=True,
        audio_frontend=dict(value['audio_frontend']), input_queue=dict(value['input_queue']))
    records = {}
    iterations = 10000
    for name, data, optimized in (('status', value, candidate._copy_status),
                                  ('failure', failure, candidate._copy_failure)):
        assert optimized(data) == copy.deepcopy(data)
        samples = {'deepcopy': [], 'fixed': []}
        for which in ('deepcopy', 'fixed', 'fixed', 'deepcopy'):
            fn = copy.deepcopy if which == 'deepcopy' else optimized
            begin = time.perf_counter_ns()
            for _ in range(iterations): fn(data)
            samples[which].append((time.perf_counter_ns() - begin) / iterations)
        old, new = statistics.median(samples['deepcopy']), statistics.median(samples['fixed'])
        records[name] = dict(ns_per_copy=samples, median_deepcopy_ns=old, median_fixed_ns=new,
            local_operation_speedup=old / new)
    report = dict(scope='Local Windows Python copy operation on public synthetic status only',
        iterations_per_sample=iterations, order='ABBA', records=records,
        no_board_model_device_or_private_data=True, whole_board_improvement_claimed=False,
        full_snapshot_or_poll_performance_measured=False, gc_policy_changed=False)
    (ROOT / 'tests/benchmark_result.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report))
