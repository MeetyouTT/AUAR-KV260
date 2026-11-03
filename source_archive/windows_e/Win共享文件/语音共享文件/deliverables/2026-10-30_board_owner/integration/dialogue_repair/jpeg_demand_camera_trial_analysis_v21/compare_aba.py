"""Compare three saved camera sampler receipts locally, without device access."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import statistics


MANIFEST = '6a7c6a56a5ceda2259ddf0ee7e00fbc932d1a34d56a396202e2f4cd045fce6e1'
BOOT = 'bebd3e7d-e984-4517-8cbb-211df7f1c6dc'
BASE = '/home/root/aura-native-live-20261024/ops/be72669aa53de735/pan-face-edge-v5/face-source-v17/entry.py'
CANDIDATE = '/home/root/aura-board-owner-candidate-20261030/jpeg-trial-' + MANIFEST[:16] + '/candidate/entry.py'
TOP_KEYS = {'status', 'label', 'owner', 'manifest_sha256', 'journal_sha256', 'summary', 'samples',
            'GUI_normally_closed_all_samples', 'sampler_JPEG_GET_requests',
            'camera_frames_or_private_database_read', 'production_mutated', 'limits'}
PROCESS_KEYS = {'mono', 'ticks', 'birth', 'rss_bytes', 'system_busy_ticks'}
HEALTH_KEYS = {'pid', 'board_boot_id', 'service_epoch', 'camera_epoch', 'capture_frames',
               'detected_frames', 'preview_frames', 'preview_buffers', 'capture_age_ms',
               'observation_age_ms', 'people_count', 'face_source_age_ms', 'face_processed',
               'native_primary_calls', 'native_primary_overruns', 'native_optional_overruns',
               'camera_error_present', 'detector_error_present', 'preview_error_present'}
RATE_KEYS = ('capture_frames', 'detected_frames', 'preview_frames')
SUMMARY_KEYS = {'seconds', 'camera_cpu_cores', 'whole_system_busy_cores', 'camera_rss_min_bytes',
                'camera_rss_max_bytes', 'people_counts', 'face_source_age_ms',
                'capture_frames_per_second', 'detected_frames_per_second', 'preview_frames_per_second'}
THRESHOLDS = {'throughput_relative_change': .10, 'people_distribution_total_variation': .20,
              'people_unknown_fraction': .05, 'baseline_CPU_relative_change': .15,
              'duration_relative_change': .10, 'face_age_p95_relative_change': .20,
              'face_age_p95_absolute_change_ms': 25}


def require(value, message):
    if not value:
        raise ValueError(message)


def number(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def sha256(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, 'Duplicate JSON field')
        result[key] = value
    return result


def same_number(first, second):
    return number(first) and number(second) and math.isclose(first, second, rel_tol=1e-9, abs_tol=1e-9)


def age_summary(values):
    valid = sorted(value for value in values if value is not None)
    result = {'valid': len(valid), 'missing': len(values) - len(valid)}
    if valid:
        result.update(median_ms=statistics.median(valid), p95_ms=valid[math.ceil(.95 * len(valid)) - 1],
                      max_ms=valid[-1], fraction_below250ms=sum(x < 250 for x in valid) / len(valid),
                      fraction_below1000ms=sum(x < 1000 for x in valid) / len(valid))
    return result


def describe(value, label):
    require(isinstance(value, dict) and set(value) == TOP_KEYS, 'Exact sampler receipt schema required')
    require(value['status'] == 'METADATA_SAMPLE_COMPLETE' and value['label'] == label
            and value['manifest_sha256'] == MANIFEST, 'Wrong result, arm or candidate manifest')
    require(sha256(value['journal_sha256']), 'Missing exact journal digest')
    require(value['GUI_normally_closed_all_samples'] is True and value['sampler_JPEG_GET_requests'] == 0
            and type(value['sampler_JPEG_GET_requests']) is int
            and value['camera_frames_or_private_database_read'] is False
            and value['production_mutated'] is False, 'Expected read-only closed-GUI scope required')
    owner = value['owner']
    require(isinstance(owner, dict) and set(owner) == {'pid', 'birth', 'cmd_sha256', 'argv'} and type(owner['pid']) is int
            and owner['pid'] > 1 and isinstance(owner['birth'], str) and owner['birth'].isdigit(), 'Invalid owner')
    expected_argv = ['/usr/bin/python3', '-B', CANDIDATE, '--manifest-sha256', MANIFEST] if label == 'B' else ['/usr/bin/python3', '-B', BASE]
    require(owner['argv'] == expected_argv, 'Arm does not use its expected camera entry')
    require(owner['cmd_sha256'] == hashlib.sha256(('\0'.join(expected_argv) + '\0').encode()).hexdigest(),
            'Owner command digest differs from its argv')
    if label == 'A1':
        require(owner['pid'] == 1335 and owner['birth'] == '2344', 'Original A1 owner changed')
    rows = value['samples']
    require(isinstance(rows, list) and len(rows) in (21, 31, 61), 'Unsupported bounded sampler row count')
    for index, row in enumerate(rows):
        require(isinstance(row, dict) and set(row) == {'process', 'health'}
                and isinstance(row['process'], dict) and set(row['process']) == PROCESS_KEYS
                and isinstance(row['health'], dict) and set(row['health']) == HEALTH_KEYS, 'Unexpected sampler row fields')
        process, health = row['process'], row['health']
        require(process['birth'] == owner['birth'] and health['pid'] == owner['pid']
                and health['board_boot_id'] == BOOT, 'Sample owner or boot differs')
        require(all(number(process[key]) for key in PROCESS_KEYS - {'birth'}), 'Invalid process counter')
        require(all(health[key] is False for key in ('camera_error_present', 'detector_error_present', 'preview_error_present')),
                'Sample reports camera pipeline errors')
        require(all(health[key] is None or number(health[key]) for key in
                    ('capture_age_ms', 'observation_age_ms', 'face_source_age_ms')), 'Invalid source age')
        require(health['people_count'] is None or type(health['people_count']) is int and health['people_count'] >= 0,
                'Invalid person count')
        require(all(type(health[key]) is int and health[key] >= 0 for key in RATE_KEYS), 'Invalid pipeline counters')
        require(all(isinstance(health[key], str) and health[key] for key in ('camera_epoch', 'service_epoch')),
                'Missing camera epoch')
        require(type(health['preview_buffers']) is int and 0 <= health['preview_buffers'] <= 8, 'Preview ring bound changed')
        require(all(health[key] == rows[0]['health'][key] for key in ('camera_epoch', 'service_epoch')), 'Epoch changed within arm')
        if index:
            previous = rows[index - 1]
            require(process['mono'] > previous['process']['mono'], 'Nonincreasing sample clock')
            require(all(process[key] >= previous['process'][key] for key in ('ticks', 'system_busy_ticks')),
                    'CPU counter decreased')
            require(all(health[key] >= previous['health'][key] for key in RATE_KEYS), 'Pipeline counter decreased')
    first, last = rows[0], rows[-1]
    seconds = last['process']['mono'] - first['process']['mono']
    summary = value['summary']
    require(isinstance(summary, dict) and set(summary) == SUMMARY_KEYS, 'Unexpected sampler summary fields')
    require(same_number(summary['seconds'], seconds) and seconds > 0, 'Reported duration differs from samples')
    rates = {key + '_per_second': (last['health'][key] - first['health'][key]) / seconds for key in RATE_KEYS}
    require(all(rates[key] > 0 and same_number(summary[key], rates[key]) for key in rates), 'Reported throughput differs')
    people = [row['health']['people_count'] for row in rows]
    ages = [row['health']['face_source_age_ms'] for row in rows]
    require(summary['people_counts'] == people and summary['face_source_age_ms'] == ages, 'Reported workload differs')
    rss = [row['process']['rss_bytes'] for row in rows]
    require(summary['camera_rss_min_bytes'] == min(rss) and summary['camera_rss_max_bytes'] == max(rss), 'RSS summary differs')
    cpu, system_cpu = summary['camera_cpu_cores'], summary['whole_system_busy_cores']
    require(number(cpu) and cpu > 0 and number(system_cpu), 'Invalid CPU summary')
    tick_delta = last['process']['ticks'] - first['process']['ticks']
    inferred_hz = tick_delta / seconds / cpu
    require(inferred_hz > 0 and same_number(system_cpu,
            (last['process']['system_busy_ticks'] - first['process']['system_busy_ticks']) / seconds / inferred_hz),
            'Camera and system CPU summaries imply different clock ticks')
    counts = Counter('unknown' if count is None else str(count) for count in people)
    histogram = {key: count / len(people) for key, count in sorted(counts.items())}
    return {'label': label, 'owner': owner, 'journal_sha256': value['journal_sha256'],
            'first_mono': first['process']['mono'], 'last_mono': last['process']['mono'],
            'service_epoch': first['health']['service_epoch'], 'camera_epoch': first['health']['camera_epoch'],
            'samples': len(rows), 'seconds': seconds, 'camera_cpu_cores': cpu, 'system_busy_cores': system_cpu,
            'sampler_implied_clock_ticks_per_second': inferred_hz, 'rss_min_bytes': min(rss), 'rss_max_bytes': max(rss),
            'person_count_histogram_fraction': histogram, 'face_source_age': age_summary(ages),
            'capture_age': age_summary([row['health']['capture_age_ms'] for row in rows]),
            'observation_age': age_summary([row['health']['observation_age_ms'] for row in rows]),
            'CPU_ms_per_capture_completion': cpu * 1000 / rates['capture_frames_per_second'],
            'CPU_ms_per_preview_completion': cpu * 1000 / rates['preview_frames_per_second'],
            'JPEG_requests_generated_by_sampler': 0, 'pipeline_errors_present': False, **rates}


def comparison(a1, b, a2):
    arms = [describe(value, label) for value, label in ((a1, 'A1'), (b, 'B'), (a2, 'A2'))]
    require(arms[0]['last_mono'] < arms[1]['first_mono'] < arms[1]['last_mono'] < arms[2]['first_mono'],
            'A1/B/A2 chronology does not match')
    require(len({arm['owner']['pid'] for arm in arms}) == 3 and
            int(arms[0]['owner']['birth']) < int(arms[1]['owner']['birth']) < int(arms[2]['owner']['birth']),
            'Three sequential owners required')
    require(len({arm['journal_sha256'] for arm in arms}) == 3, 'Three distinct phase journals required')
    require(all(math.isclose(arm['sampler_implied_clock_ticks_per_second'], arms[0]['sampler_implied_clock_ticks_per_second'],
                            rel_tol=1e-9) for arm in arms), 'CPU clock units differ across arms')
    b = arms[1]
    pairs, flags = [], []
    for baseline in (arms[0], arms[2]):
        name = baseline['label']
        changes = {key: b[key] / baseline[key] - 1 for key in ('camera_cpu_cores', 'seconds',
                   'capture_frames_per_second', 'detected_frames_per_second', 'preview_frames_per_second')}
        counts, base_counts = b['person_count_histogram_fraction'], baseline['person_count_histogram_fraction']
        variation = .5 * sum(abs(counts.get(key, 0) - base_counts.get(key, 0)) for key in counts.keys() | base_counts.keys())
        if variation >= THRESHOLDS['people_distribution_total_variation']:
            flags.append('B_vs_' + name + '_person_count_distribution_changed')
        for key in ('capture_frames_per_second', 'detected_frames_per_second', 'preview_frames_per_second'):
            if abs(changes[key]) >= THRESHOLDS['throughput_relative_change']:
                flags.append('B_vs_' + name + '_' + key + '_changed')
        if abs(changes['seconds']) >= THRESHOLDS['duration_relative_change'] or b['samples'] != baseline['samples']:
            flags.append('B_vs_' + name + '_measurement_duration_changed')
        current_age, base_age = b['face_source_age'], baseline['face_source_age']
        if 'p95_ms' in current_age and 'p95_ms' in base_age:
            difference = current_age['p95_ms'] - base_age['p95_ms']
            if abs(difference) >= max(THRESHOLDS['face_age_p95_absolute_change_ms'],
                                      base_age['p95_ms'] * THRESHOLDS['face_age_p95_relative_change']):
                flags.append('B_vs_' + name + '_face_source_age_changed')
        pairs.append({'baseline': name, 'B_relative_changes_percent': {key: 100 * value for key, value in changes.items()},
                      'person_distribution_total_variation': variation,
                      'B_peak_RSS_minus_baseline_bytes': b['rss_max_bytes'] - baseline['rss_max_bytes'],
                      'B_CPU_ms_per_capture_minus_baseline': b['CPU_ms_per_capture_completion'] - baseline['CPU_ms_per_capture_completion']})
    for arm in arms:
        if arm['person_count_histogram_fraction'].get('unknown', 0) > THRESHOLDS['people_unknown_fraction']:
            flags.append(arm['label'] + '_person_count_coverage_incomplete')
        if arm['face_source_age']['missing']:
            flags.append(arm['label'] + '_face_age_coverage_incomplete')
    baseline_drift = arms[2]['camera_cpu_cores'] / arms[0]['camera_cpu_cores'] - 1
    if abs(baseline_drift) >= THRESHOLDS['baseline_CPU_relative_change']:
        flags.append('A1_to_A2_baseline_CPU_changed')
    return {'status': 'DESCRIPTIVE_ABA_WITH_THRESHOLD_FLAGS' if flags else 'DESCRIPTIVE_ABA_WITHOUT_THRESHOLD_FLAGS',
            'arms': arms, 'B_against_each_baseline': pairs, 'threshold_flags': flags,
            'A2_vs_A1_CPU_change_percent': 100 * baseline_drift, 'thresholds': THRESHOLDS,
            'B_CPU_lower_than_both_baselines': all(b['camera_cpu_cores'] < arm['camera_cpu_cores'] for arm in (arms[0], arms[2])),
            'comparison_changes_production': False, 'B_adoption_authorized_by_comparison': False,
            'limits': ['Thresholds are declared descriptive screening choices, not calibrated performance acceptance criteria.',
                       'Person counts cannot establish identical motion, texture or illumination. Scene-load differences remain possible.',
                       'Clock tick frequency is inferred from the sampler summaries because receipts omit the original sysconf value.',
                       'The GUI is closed in every arm. The sampler generates zero JPEG GET requests, while other clients are not measured.',
                       'Conversational latency and physical display FPS are unmeasured.',
                       'This report makes no service changes and does not authorize permanent candidate adoption.']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--a1', required=True, type=Path)
    parser.add_argument('--b', required=True, type=Path)
    parser.add_argument('--a2', required=True, type=Path)
    parser.add_argument('--result-member', help='Explicit envelope member containing the unchanged sampler JSON')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    values, references = [], []
    for path in (args.a1, args.b, args.a2):
        raw = path.read_bytes()
        require(len(raw) <= 2 * 1024 * 1024, 'Receipt exceeds bounded metadata size')
        value = json.loads(raw, object_pairs_hook=unique,
                           parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite JSON value')))
        if args.result_member:
            require(isinstance(value, dict) and isinstance(value.get(args.result_member), dict), 'Explicit result member missing')
            for key in ('returncode', 'process_exit_code'):
                require(key not in value or type(value[key]) is int and value[key] == 0, 'Envelope reports failed execution')
            value = value[args.result_member]
        values.append(value)
        references.append({'path': str(path.resolve()), 'sha256': hashlib.sha256(raw).hexdigest(),
                           'result_member': args.result_member})
    result = comparison(*values)
    result['inputs'] = references
    encoded = (json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
    if args.output:
        with args.output.open('xb') as stream:
            stream.write(encoded)
        print(json.dumps({'status': result['status'], 'output': str(args.output.resolve()),
                          'sha256': hashlib.sha256(encoded).hexdigest(), 'threshold_flags': result['threshold_flags']}))
    else:
        print(encoded.decode())


if __name__ == '__main__':
    main()
