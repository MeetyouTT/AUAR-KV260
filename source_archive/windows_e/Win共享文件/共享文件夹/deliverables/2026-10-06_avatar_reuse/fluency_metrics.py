"""Measure Qt frame submissions, not physical display refresh or audio lip sync."""
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def percentile(values, fraction):
    ordered = sorted(values)
    if not ordered:
        return None
    position = (len(ordered) - 1) * fraction
    lo = int(position)
    hi = min(lo + 1, len(ordered) - 1)
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (position - lo)


def describe(values):
    return {
        'count': len(values),
        'mean_ms': sum(values) / len(values) if values else None,
        'p50_ms': percentile(values, .5),
        'p95_ms': percentile(values, .95),
        'p99_ms': percentile(values, .99),
        'max_ms': max(values) if values else None,
        'over_83_333_ms': sum(value > 1000 / 12 for value in values),
        'over_100_ms': sum(value > 100 for value in values),
    }


def write_review(frames, cue_delivery, end, using_reuse):
    pairs = list(zip(frames, frames[1:]))
    intervals = [(right['submitted_at_seconds'] - left['submitted_at_seconds']) * 1000
                 for left, right in pairs]
    span = frames[-1]['submitted_at_seconds'] - frames[0]['submitted_at_seconds'] if len(frames) > 1 else 0
    by_state = {}
    for state in sorted({frame['display_state'] for frame in frames}):
        stable = [(right['submitted_at_seconds'] - left['submitted_at_seconds']) * 1000
                  for left, right in pairs
                  if left['display_state'] == right['display_state'] == state
                  and left['asset'] == right['asset']]
        by_state[state] = describe(stable)
    worst = sorted(pairs, key=lambda pair: pair[1]['submitted_at_seconds'] - pair[0]['submitted_at_seconds'], reverse=True)[:15]
    result = {
        'generated_utc': datetime.now(timezone.utc).isoformat(),
        'environment': 'PC / SIMULATED',
        'measurement': 'perf_counter (monotonic) timestamp immediately after QLabel.setPixmap; submissions, not physical scanout',
        'assets_mode': 'reuse' if using_reuse else 'original',
        'script_seconds': end,
        'timer_interval_ms': 33,
        'source_fps': 24,
        'submitted_frames': len(frames),
        'first_submission_seconds': frames[0]['submitted_at_seconds'] if frames else None,
        'submission_span_seconds': span,
        'mean_submission_fps': (len(frames) - 1) / span if span else None,
        'frame_intervals': describe(intervals),
        'sampling_and_image_upload_cost': describe([frame['work_ms'] for frame in frames]),
        'stable_asset_intervals_by_state': by_state,
        'worst_intervals': [dict(
            interval_ms=(right['submitted_at_seconds'] - left['submitted_at_seconds']) * 1000,
            from_seconds=left['submitted_at_seconds'],
            to_seconds=right['submitted_at_seconds'],
            from_state=left['display_state'], to_state=right['display_state'],
            from_asset=left['asset'], to_asset=right['asset'],
        ) for left, right in worst],
        'cue_delivery': cue_delivery,
        'runtime': {'python': sys.version, 'platform': platform.platform(),
                    'clock': vars(time.get_clock_info('perf_counter'))},
        'limits': 'One desktop run. Frame submission does not measure compositor scanout, perceived naturalness, phoneme alignment or board performance. First loads are included.',
    }
    directory = Path(__file__).with_name('fluency_review')
    directory.mkdir(exist_ok=True)
    suffix = '' if using_reuse else '_original'
    (directory / ('real_time_frames' + suffix + '.json')).write_text(json.dumps(frames, ensure_ascii=False, indent=2), encoding='utf-8')
    (directory / ('real_time_fluency' + suffix + '.json')).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result
