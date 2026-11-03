"""Compare saved numeric baseline summaries without accessing devices or media."""
import argparse
import hashlib
import json
import math
from pathlib import Path


def number(value):
    return value if type(value) in (int, float) and math.isfinite(value) else None


def get(value, *path):
    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value


def metric(before, after):
    before, after = number(before), number(after)
    return dict(before=before, after=after,
                delta=after - before if before is not None and after is not None else None,
                relative_percent=(after / before - 1) * 100
                    if before is not None and before > 0 and after is not None else None)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--before', required=True, type=Path)
    parser.add_argument('--after', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    inputs = [json.loads(path.read_text(encoding='utf-8')) for path in (args.before, args.after)]
    results = [item['result'] for item in inputs]
    summaries = [result['summary'] for result in results]
    before, after = summaries
    valid = all(result.get('status') == 'COMPLETE' and not result.get('error')
                and not result.get('restore_error') and not result.get('after_error') for result in results)
    same_collector = inputs[0].get('source_sha256') == inputs[1].get('source_sha256')
    scopes_match = all(summary.get('all_main_visible_scheduling_active') is True for summary in summaries)
    rows = {}
    for label, path in {
        'board_cpu_percent': ('board_cpu_busy_percent', 'median'),
        'gtk_callback_cpu_ms': ('ui', 'ui_callback_previous', 'thread_cpu_ms', 'median'),
        'gtk_callback_wall_ms': ('ui', 'ui_callback_previous', 'wall_ms', 'median'),
        'publish_wall_ms': ('ui', 'ui_callback_previous', 'publish_ms', 'median'),
        'presentation_wall_ms': ('ui', 'ui_stage_timings_ms', 'presentation', 'median'),
        'native_age_ms': ('avatar', 'age_ms', 'median'),
        'native_counter_hz': ('counters', 'avatar', 'frames', 'per_second'),
        'camera_capture_hz': ('counters', 'camera', 'capture_frames', 'per_second'),
        'camera_detection_hz': ('counters', 'camera', 'detected_frames', 'per_second'),
        'visual_source_age_ms': ('camera', 'observation_age_ms', 'median'),
        'observer_cpu_per_sample_ms': ('observer_cpu_ms', 'median'),
    }.items():
        rows[label] = metric(get(before, *path), get(after, *path))
    for role in ('gtk', 'camera', 'supervisor'):
        values = []
        for summary in summaries:
            matching = [row for row in summary.get('processes', {}).values() if row.get('role') == role]
            values.append(get(matching[0], 'cpu_one_core_percent', 'median') if len(matching) == 1 else None)
        rows[role + '_cpu_one_core_percent'] = metric(*values)
    report = dict(schema='aura-joint-baseline-comparison-1',
                  status='DESCRIPTIVE_COMPARISON' if valid and scopes_match else 'COMPARISON_SCOPE_INCOMPLETE',
                  original_collector_source_equal=same_collector,
                  complete_main_visible_windows=bool(valid and scopes_match),
                  metrics=rows,
                  evidence=[dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
                            for path in (args.before, args.after)],
                  limits=['Two sequential sparse windows are not randomized whole-system A/B.',
                          'People/pose/background activity can change camera and scheduler load.',
                          'Process CPU uses one core=100%; board CPU uses all cores=100%.',
                          'Observer cost is included; different collector fingerprints require review.',
                          'No real speech-to-acoustic-first-sound measurement is inferred.'])
    with args.output.open('x', encoding='utf-8') as handle:
        handle.write(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(path=str(args.output), status=report['status'],
                          original_collector_source_equal=same_collector, metrics=rows)))


if __name__ == '__main__':
    main()
