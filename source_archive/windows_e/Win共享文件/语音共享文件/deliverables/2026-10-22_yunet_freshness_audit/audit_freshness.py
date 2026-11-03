"""Read frozen numeric evidence and source hashes; never contacts a board/service."""
import ast
import hashlib
import json
import math
from pathlib import Path


HERE = Path(__file__).resolve().parent
DELIVERABLES = Path('/home/ghmd/Win共享文件/语音共享文件/deliverables')
GIL = DELIVERABLES / '2026-10-22_gil_interval_trial'
OVERLAY = Path('/home/ghmd/aura-thread-sched-20261022/candidate/aura')
YUNET = DELIVERABLES / '2026-10-21_dpu_vision_start/candidate/aura'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def literal_assignment(path, name):
    for node in ast.parse(path.read_text()).body:
        if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == name for target in node.targets):
            return ast.literal_eval(node.value)
    raise ValueError('Missing assignment: ' + name)


def stage_deltas(first, last):
    result = {}
    a, b = first['pipeline_metrics']['stages'], last['pipeline_metrics']['stages']
    for name, row in b.items():
        before = a.get(name, {'count': 0, 'total_ms': 0})
        count = row['count'] - before['count']
        total = row['total_ms'] - before['total_ms']
        result[name] = {
            'first_count': before['count'], 'last_count': row['count'],
            'count_delta': count, 'total_ms_delta': total,
            'window_mean_ms': total / count if count else None,
            'cumulative_max_ms': row['max_ms'],
            'last_recent_count': row['recent_count'],
            'last_recent_p95_ms': row['recent_p95_ms'],
        }
    return result


def summarize(path):
    envelope = json.loads(path.read_text())
    report = envelope['report']
    samples = report['samples']
    first, last = samples[0], samples[-1]
    assert len({s['pid'] for s in samples}) == 1
    start_diag = first['pipeline_metrics']['optional_diagnostics']['started_mono_ns']
    snapshot_ns = [s['pipeline_metrics']['optional_diagnostics']['snapshot_mono_ns'] for s in samples]
    assert all(a < b for a, b in zip(snapshot_ns, snapshot_ns[1:]))
    faces = [s['face_targets'] for s in samples]
    ages = [face['source_age_ms'] for face in faces]
    assert all(type(a) is int and a >= 0 for a in ages)
    final_diag = last['pipeline_metrics']['optional_diagnostics']
    final_counter = final_diag['counters']['yunet']
    initial_counter = first['pipeline_metrics']['optional_diagnostics']['counters']['yunet']
    assert final_counter['requests'] == final_counter['admitted'] + final_counter['rejected']
    assert final_counter['rejected'] == sum(final_counter['rejected_' + k]
                                          for k in ('disabled', 'active', 'primary_waiting', 'deadline'))
    assert final_counter['native_completed'] == last['dpu_schedule']['optional']['yunet']['calls']
    assert final_counter['native_failed'] == 0
    counter_delta = {k: value - initial_counter[k] for k, value in final_counter.items()}
    numeric_samples = []
    for index, sample in enumerate(samples):
        diag = sample['pipeline_metrics']['optional_diagnostics']
        face = sample['face_targets']
        counter = diag['counters']['yunet']
        row = {
            'sample_index': index,
            'harness_elapsed_s': sample['elapsed_s'],
            'diagnostic_snapshot_relative_s': (diag['snapshot_mono_ns'] - start_diag) / 1e9,
            'face_source_age_ms': face['source_age_ms'],
            'face_ttl_expired': face['source_age_ms'] >= 1000,
            'face_processed': face['processed'], 'face_discarded': face['discarded'],
            'face_last_inference_ms': face['last_inference_ms'],
            'yolo_observation_age_ms': sample['observation_age_ms'],
            'capture_frames': sample['capture_frames'], 'detected_frames': sample['detected_frames'],
            'estimated_budget_ms': sample['dpu_schedule']['optional']['yunet']['estimated_budget_ms'],
            'optional_maximum_ms': sample['dpu_schedule']['optional']['yunet']['maximum_ms'],
            **{key: counter[key] for key in ('requests', 'admitted', 'rejected', 'rejected_active',
                                           'rejected_deadline', 'native_completed', 'faults')},
        }
        if index:
            old = numeric_samples[-1]
            row['previous_snapshot_interval_s'] = (snapshot_ns[index] - snapshot_ns[index - 1]) / 1e9
            row['previous_interval_delta'] = {k: row[k] - old[k] for k in (
                'face_processed', 'face_discarded', 'capture_frames', 'detected_frames',
                'requests', 'admitted', 'rejected', 'rejected_active', 'rejected_deadline')}
        numeric_samples.append(row)
    stale_indices = [i for i, age in enumerate(ages) if age >= 1000]
    around_stale = [{
        'expired_sample_index': index,
        'neighbor_samples': numeric_samples[max(index-1, 0):min(index+2, len(samples))],
    } for index in stale_indices]
    trace = final_diag['maximum_normal_trace']
    gaps = {}
    for key, a, b in (
            ('optional_start_to_execute_start', 'optional_start', 'execute_start'),
            ('execute_return_to_wait_start', 'execute_return', 'wait_start'),
            ('wait_end_to_optional_end', 'wait_end', 'optional_end')):
        gaps[key] = {
            'wall_ms': (trace[b + '_mono_ns'] - trace[a + '_mono_ns']) / 1e6,
            'calling_thread_cpu_ms': (trace[b + '_thread_cpu_ns'] - trace[a + '_thread_cpu_ns']) / 1e6,
        }
    duration = report['observed_seconds']
    snapshot_span = (snapshot_ns[-1] - snapshot_ns[0]) / 1e9
    return {
        'evidence': {'path': str(path), 'sha256': sha(path)},
        'scope': report['scope'], 'original_harness_passed': report['passed'],
        'rollback_verified_in_frozen_evidence': report['rollback_verified'],
        'sample_count': len(samples), 'face_ttl_ms': 1000,
        'sparse_age_summary': {
            'minimum_ms': min(ages), 'median_ms': sorted(ages)[len(ages)//2],
            'p95_ms': sorted(ages)[math.ceil(.95 * len(ages))-1], 'maximum_ms': max(ages),
            'at_or_over_ttl_samples': len(stale_indices), 'expired_sample_indices': stale_indices,
            'scope': 'Sparse health snapshots only; neither per-frame distribution nor expired-time fraction',
        },
        'harness_counting_window_s': duration, 'diagnostic_snapshot_span_s': snapshot_span,
        'cpu_window': report['cpu_window'],
        'harness_reported_rates_hz': {k: report[k] for k in (
            'observed_yolo_hz', 'observed_yunet_hz', 'observed_capture_hz')},
        'same_pid_count_deltas': {
            'capture_frames': last['capture_frames'] - first['capture_frames'],
            'detected_frames': last['detected_frames'] - first['detected_frames'],
            'published_face_results': last['face_targets']['processed'] - first['face_targets']['processed'],
            'face_discarded': last['face_targets']['discarded'] - first['face_targets']['discarded'],
            'native_completed': counter_delta['native_completed'],
        },
        'published_face_result_rate_using_harness_window_hz':
            (last['face_targets']['processed'] - first['face_targets']['processed']) / duration,
        'first_counters': initial_counter, 'last_counters': final_counter,
        'window_counter_deltas': counter_delta,
        'cumulative_rejected_fraction': final_counter['rejected'] / final_counter['requests'],
        'cumulative_deadline_fraction_of_rejections':
            final_counter['rejected_deadline'] / final_counter['rejected'],
        'first_face_processed': first['face_targets']['processed'],
        'last_face_processed': last['face_targets']['processed'],
        'last_dequantize_count': last['pipeline_metrics']['stages']['yunet.dequantize']['count'],
        'last_face_discarded_minus_slot_rejected':
            last['face_targets']['discarded'] - final_counter['rejected'],
        'primary_period_overruns_first': first['dpu_schedule']['primary_period_overruns'],
        'primary_period_overruns_last': last['dpu_schedule']['primary_period_overruns'],
        'last_optional_schedule': last['dpu_schedule']['optional']['yunet'],
        'normal_success_timing_means_ms': {key: row['sum_ms'] / row['count']
                                         for key, row in final_diag['normal_success_timings']['yunet'].items()},
        'stages': stage_deltas(first, last),
        'maximum_normal_trace': {key: value for key, value in trace.items()
                                 if type(value) in (int, float, bool)},
        'maximum_trace_relative_diagnostic_start_s':
            (trace['optional_start_mono_ns'] - start_diag) / 1e9,
        'maximum_trace_boundary_gaps': gaps,
        'observer': final_diag['thread_sched_observer'],
        'expired_sample_neighbors': around_stale,
        'numeric_samples': numeric_samples,
        'limits': {
            'person_present_required_by_this_trial': False,
            'face_counts_or_target_validity_collected_in_this_evidence': False,
            'per_attempt_timestamps_collected': False,
            'exact_ttl_cause_proven': False,
            'dpu_busy_fraction_measured': False,
            'same_input_speedup_proven': False,
            'whole_board_cpu_percent_is_a_speedup_metric': False,
        },
    }


def main():
    HERE.mkdir(exist_ok=True)
    bundle = json.loads((GIL / 'pinned-native-bundle.json').read_text())
    helper = GIL / 'source/board_gil_switch_1ms_20261022.py'
    baseline = literal_assignment(helper, 'BASELINE')
    evidence = GIL / 'evidence/long-600s.json'
    report = json.loads(evidence.read_text())['report']
    records = []
    for relative, expected in report['source_hashes'].items():
        path = OVERLAY / relative
        actual = sha(path)
        assert actual == expected == bundle['manifest']['files'][relative]['sha256']
        ast.parse(path.read_text())
        records.append({'path': str(path), 'sha256': actual, 'bytes': path.stat().st_size})
    assert len(records) == 14
    assert sha(Path(bundle['path'])) == bundle['sha256']
    for relative in ('board/identity/face_targets.py', 'board/vision/dpu_yunet.py'):
        path = YUNET / relative
        actual = sha(path)
        assert actual == baseline[relative]
        ast.parse(path.read_text())
        records.append({'path': str(path), 'sha256': actual, 'bytes': path.stat().st_size})
    before = Path('/home/ghmd/aura-dpu-vision-20261021/live-source/board/identity/face_targets.py')
    manifest = {
        'scope': 'Read-only local audit; no board connection or deployment',
        'frozen_sources': records,
        'native_bundle': {key: bundle[key] for key in ('path', 'sha256', 'bytes')},
        'baseline_hash_authority': {'path': str(helper), 'sha256': sha(helper)},
        'excluded_migration_before_source': {'path': str(before), 'sha256': sha(before)},
    }
    (HERE / 'source-manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    values = {'long': summarize(evidence), 'short': summarize(GIL / 'evidence/short-120s.json')}
    (HERE / 'numeric-audit.json').write_text(json.dumps(values, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({key: {
        'samples': value['sample_count'], 'expired': value['sparse_age_summary'],
        'published_hz': value['published_face_result_rate_using_harness_window_hz'],
        'maximum_trace_gaps': value['maximum_trace_boundary_gaps'],
    } for key, value in values.items()}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
