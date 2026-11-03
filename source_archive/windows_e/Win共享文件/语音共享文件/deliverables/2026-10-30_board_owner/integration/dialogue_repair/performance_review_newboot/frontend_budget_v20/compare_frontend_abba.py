"""Offline fixed-gate ABBA screening. A passed screen authorizes no deployment."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics

import frontend_v20_common as current


THRESHOLDS = dict(candidate_mean_gate_wall_ms_max=16.,
    minimum_mean_wall_improvement_percent=15.,
    candidate_to_baseline_process_cpu_ratio_max=1.25,
    candidate_complete_50_frame_window_mean_ms_max=18.,
    candidate_paced_queue_peak_max=6, candidate_paced_queue_max_ms=120.)


def compare(rows):
    expected = ['A1', 'B1', 'B2', 'A2']
    result = dict(status='INCOMPLETE_DO_NOT_DEPLOY', thresholds=dict(THRESHOLDS),
                  expected_slots=expected, observed_slots=[row.get('slot') for row in rows],
                  physical_dialogue_accepted=False, production_change_authorized=False)
    if [row.get('slot') for row in rows] != expected:
        return result
    if any(row.get('status') != 'PASS_PUBLIC_SLOT' for row in rows):
        result.update(status='FAILED_SLOT_DO_NOT_DEPLOY')
        return result
    if any(row.get('startup_sha256') != current.STARTUP_SHA
           or row.get('source_mapping_sha256') != current.MAPPING_SHA
           or row.get('source_components_verified') != 380
           or not isinstance(row.get('live_guard_before'), dict)
           or not isinstance(row.get('live_guard_after'), dict) for row in rows):
        result.update(status='CURRENT_SOURCE_PROOF_REQUIRED')
        return result
    if [row.get('mode') for row in rows] != ['baseline_1','dual_nospin','dual_nospin','baseline_1']:
        raise ValueError('ABBA modes mismatch')
    direct = [trial for row in rows for trial in row['throughput']]
    if len(direct) != 8:
        raise ValueError('Require the two fixed repetitions in all four slots')
    same_direct = all(len({trial[key] for trial in direct}) == 1 for key in
        ('frames','model_hops','output_samples','output_float32_sha256','output_pcm16_sha256','decision_sha256','decision_bytes_hex'))
    endpoint_fields = ('start_sample','captured_samples','original_pcm_sha256','decision_sha256','end_total_samples')
    same_endpoint = all(len({row['paced']['endpoint'][key] for row in rows}) == 1 for key in endpoint_fields)
    same_paced_float = len({row['paced']['denoised']['float32_sha256'] for row in rows}) == 1
    owners = all(row['before'] == row['after'] and row['priority']['restoration_confirmed'] for row in rows)
    identities = len({(row['startup_sha256'], row['source_wav_sha256'],
        row['before']['boot_id'], row['before']['ui_pid'], row['before']['camera_pid']) for row in rows}) == 1
    versions = len({json.dumps(row['runtime']['versions'], sort_keys=True) for row in rows}) == 1
    guards = [row[key] for row in rows for key in ('live_guard_before', 'live_guard_after')]
    expected_owners = {role: current.baseline()[role] for role in ('supervisor', 'gtk', 'camera')}
    pinned_owners = all(guard.get('owners') == expected_owners for guard in guards)
    capture_stable = len({json.dumps(guard.get('capture_stats'), sort_keys=True) for guard in guards}) == 1
    memory_stable = all(len({guard.get(key) for guard in guards}) == 1
                        for key in ('memory_completed', 'memory_discarded'))
    baseline = [trial for row in rows if row['mode']=='baseline_1' for trial in row['throughput']]
    candidate = [trial for row in rows if row['mode']=='dual_nospin' for trial in row['throughput']]
    a_wall = statistics.mean(trial['gate_wall_ms']['mean'] for trial in baseline)
    b_wall = statistics.mean(trial['gate_wall_ms']['mean'] for trial in candidate)
    a_cpu = statistics.mean(trial['gate_process_cpu_ms']['mean'] for trial in baseline)
    b_cpu = statistics.mean(trial['gate_process_cpu_ms']['mean'] for trial in candidate)
    improvement = (a_wall-b_wall)/a_wall*100 if a_wall else 0.
    windows = [window['mean'] for trial in candidate for window in trial['frame_windows']['windows_50_frames']
               if window['count'] == 50]
    queue = [row['paced']['input_queue'] for row in rows if row['mode']=='dual_nospin']
    checks = dict(full_direct_numeric_parity=same_direct, paced_endpoint_parity=same_endpoint,
        paced_denoised_parity=same_paced_float, owners_and_priority=owners, same_source_and_processes=identities,
        same_runtime_versions=versions,
        current_v20_owners=pinned_owners, capture_activity_unchanged=capture_stable,
        background_memory_counters_unchanged=memory_stable,
        mean_wall_headroom=b_wall <= THRESHOLDS['candidate_mean_gate_wall_ms_max'],
        relative_wall_gain=improvement >= THRESHOLDS['minimum_mean_wall_improvement_percent'],
        total_process_cpu_budget=a_cpu > 0 and b_cpu/a_cpu <= THRESHOLDS['candidate_to_baseline_process_cpu_ratio_max'],
        complete_window_budget=bool(windows) and max(windows) <= THRESHOLDS['candidate_complete_50_frame_window_mean_ms_max'],
        paced_raw8_headroom=all(row['capacity_frames']==8 and not row['error']
            and row['peak_frames'] <= THRESHOLDS['candidate_paced_queue_peak_max']
            and row['queue_max_ms'] <= THRESHOLDS['candidate_paced_queue_max_ms'] for row in queue))
    result.update(status='ELIGIBLE_FOR_CONTROLLED_LIVE_VALIDATION' if all(checks.values()) else 'DO_NOT_DEPLOY',
        checks=checks, baseline_mean_gate_wall_ms=a_wall, candidate_mean_gate_wall_ms=b_wall,
        wall_improvement_percent=improvement, baseline_mean_gate_process_cpu_ms=a_cpu,
        candidate_mean_gate_process_cpu_ms=b_cpu,
        statistical_significance_claimed=False,
        remaining='A public screening pass still needs the normal IPC/capture entry, sustained listening, live ASR admission, visual queries and complete audio playback validation.')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('evidence', type=Path, nargs='+')
    args = parser.parse_args()
    rows = []
    sources = []
    for path in args.evidence:
        raw = path.read_bytes()
        item = json.loads(raw)
        if isinstance(item.get('slots'), list):
            rows.extend(item['slots'])
        else:
            rows.append(item.get('result', item))
        sources.append(dict(path=str(path.resolve()), sha256=hashlib.sha256(raw).hexdigest()))
    print(json.dumps(dict(compare(rows), sources=sources), indent=2))
