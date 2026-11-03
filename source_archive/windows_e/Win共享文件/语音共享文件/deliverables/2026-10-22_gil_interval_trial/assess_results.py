"""Recompute explicit, bounded health-snapshot limits from numeric trial evidence."""
import json
import math
from pathlib import Path


def assess(value):
    report = value['report']
    samples = report['samples']
    ages = [row['face_targets']['source_age_ms'] for row in samples
            if row.get('face_targets', {}).get('source_age_ms') is not None]
    first = samples[0]
    last = report['camera_after']
    schedule = last['dpu_schedule']
    counters = schedule['optional_diagnostics']['counters']['yunet']
    assert counters['native_completed'] == schedule['optional']['yunet']['calls']
    assert counters['requests'] == counters['admitted'] + counters['rejected']
    assert counters['native_failed'] == 0
    return {
        'scope': report['scope'],
        'original_harness_passed': report['passed'],
        'health_sample_count': len(samples),
        'face_age_sample_count': len(ages),
        'face_ttl_ms': 1000,
        'face_age_samples_at_or_over_ttl': sum(age >= 1000 for age in ages),
        'maximum_sampled_face_age_ms': max(ages),
        'p95_sampled_face_age_ms': sorted(ages)[math.ceil(len(ages) * .95) - 1],
        'sample_age_scope': 'sparse health snapshots, not per-frame latency or fraction of time expired',
        'all_sampled_face_results_fresh': all(age < 1000 for age in ages),
        'primary_period_overruns_first': first['dpu_schedule']['primary_period_overruns'],
        'primary_period_overruns_last': schedule['primary_period_overruns'],
        'native_completions_cumulative': counters['native_completed'],
        'published_face_results_cumulative': last['face_targets']['processed'],
        'counts_include_startup_before_window': True,
        'yunet_scheduler_counters': counters,
        'same_input_speedup_proven': False,
        'dpu_busy_fraction_measured_in_this_trial': False,
    }


if __name__ == '__main__':
    root = Path(__file__).resolve().parent
    values = {}
    for name in ('short', 'long'):
        path = root / ('result-' + name + '.json')
        if not path.exists():
            path = root / 'evidence' / ('short-120s.json' if name == 'short' else 'long-600s.json')
        values[name] = assess(json.loads(path.read_text()))
    print(json.dumps(values, ensure_ascii=False, indent=2))
