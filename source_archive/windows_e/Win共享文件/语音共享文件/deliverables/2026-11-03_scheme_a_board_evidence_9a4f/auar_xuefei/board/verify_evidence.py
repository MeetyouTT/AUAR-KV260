#!/usr/bin/env python3
"""Recompute comparisons from preserved public board measurements. This command performs local file reads."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def nested(value, path):
    for key in path.split('/'):
        value = value[key]
    return value


def evaluate(root):
    checks = []
    def compare(name, actual, expected, tolerance=None):
        ok = actual == expected
        if tolerance is not None:
            ok = isinstance(actual, (int, float)) and math.isfinite(actual) and abs(actual - expected) <= tolerance
        checks.append({'check': name, 'observed': actual, 'reference': expected, 'tolerance': tolerance, 'passed': bool(ok)})
    def near(name, actual, expected):
        compare(name, actual, expected, 1e-7)

    manifest = load(root/'board/evidence_sources.json')
    for row in manifest['records']:
        compare('file_sha:' + row['file'], sha(root/row['file']), row['sha256'])
    fixture = load(root/'data/board_reference/yunet_synthetic/manifest.json')
    for case in fixture['cases']:
        for row in [case['input']] + case['outputs']:
            compare('fixture_sha:' + row['file'], sha(root/row['file']), row['sha256'])
    compare('synthetic_case_numbers', [c['sample'] for c in fixture['cases']], [2, 3])

    release = load(root/'board/evidence/runtime_9a4f/release_result.public.json')
    baseline = load(root/'board/release_9a4f.json')
    compare('historical_9a4f_startup', release['startup_sha256'], baseline['baseline_startup_sha256'])
    compare('historical_other_components_preserved', release['other_components_preserved'], 379)
    observed = release['last_readonly_state']
    compare('historical_380_runtime_bytes', observed['all380_actual_bytes_match'], True)
    compare('historical_gui_ready', observed['ready'], True)
    compare('historical_model_host_ready', observed['model_host_ready'], True)
    compare('historical_arm_synthetic_cases', observed['installed_ARM_short_voice_checks']['cases_passed'], 5)
    for field in ['one_embedding_per_eligible_capture', 'unknown_and_too_short_clear_previous_name', 'enrollment_gate_preserved', 'original_worker_closed']:
        compare('historical_arm:' + field, observed['installed_ARM_short_voice_checks'][field], True)
    for row in release['changed_runtime_files']:
        compare('changed_runtime_source:' + row['path'], row['after_sha256'], baseline['runtime_files'][row['path']]['sha256'])

    dpu_dir = root/'board/evidence/dpu_20261021'
    for name in ['yunet_fixed.public.json', 'sface_three_fixed.public.json']:
        report = load(dpu_dir/name)
        compare(name + ':exit', report['core_exit_code'], 0)
        for key in ['passed', 'camera_restored', 'ui_pid_preserved', 'protected_configuration_unchanged', 'boot_preserved']:
            compare(name + ':' + key, report[key], True)
        compare(name + ':protected_config_changed', report['production_config_changed'], False)
        compare(name + ':reported_agreement', report['core']['all_host_quantized_agreement'], True)
    yunet = load(dpu_dir/'yunet_fixed.public.json')['core']
    compare('yunet_sample_count', len(yunet['agreement']), 4)
    ymanifest = load(root/'data/board_reference/yunet_compiler_manifest.json')
    expected_shapes = {tuple(row['dims']) for partition in ymanifest['partitions'] if partition['device'] == 'DPU' for row in partition['outputs']}
    for sample in yunet['agreement']:
        compare('yunet_%d_head_shapes' % sample['sample'], sorted([h['shape'] for h in sample['heads']]), sorted([list(s) for s in expected_shapes]))
        for head in sample['heads']:
            difference = head['max_integer_difference']
            compare('yunet_%d_%s_within_1_lsb' % (sample['sample'], 'x'.join(map(str, head['shape']))), difference <= fixture['maximum_integer_difference'], True)
    sface = load(dpu_dir/'sface_three_fixed.public.json')['core']
    smanifest = load(root/'data/board_reference/sface_compiler_manifest.json')
    compare('sface_model_binding', sface['sface_model_sha256'], smanifest['sha256'])
    compare('sface_sample_count', len(sface['agreement']), 4)
    for sample in sface['agreement']:
        compare('sface_%d_within_1_lsb' % sample['sample'], sample['maximum_integer_difference'] <= 1, True)
    compare('sface_four_reference_cosines', len(sface['fp32_hardware_cosine_four_public_samples']), 4)

    perf_dir = root/'board/evidence/performance_20261102'
    model_report = load(perf_dir/'model_results.public.json')
    resource_report = load(root/'data/board_reference/performance_summary.public.json')
    crosscheck = load(root/'data/board_reference/dpu_crosscheck.public.json')
    resources = [json.loads(line) for line in (perf_dir/'board_numeric.public.jsonl').read_text().splitlines()]
    samples = [row for row in resources if row['event'] == 'sample']
    compare('resource_samples', len(samples), resource_report['resource_samples'])
    near('cpu_mean_percent', statistics.mean(row['cpu']['cpu'] for row in samples), resource_report['cpu_total_percent']['mean'])
    near('cpu_max_percent', max(row['cpu']['cpu'] for row in samples), resource_report['cpu_total_percent']['max'])
    near('minimum_mem_available_mib', min(row['memory_kib']['MemAvailable'] for row in samples) / 1024, resource_report['memory_available_min_mib'])
    cameras = [row['camera'] for row in resources if row.get('camera', {}).get('ok') and row['camera'].get('data')]
    first, last = cameras[0], cameras[-1]
    interval = last['request_finished_monotonic_s'] - first['request_finished_monotonic_s']
    near('dpu_counter_interval_s', interval, crosscheck['counter_interval_s'])
    for item in crosscheck['models']:
        count = nested(last['data'], item['completed_or_admitted_counter_path'].replace('.', '/')) - nested(first['data'], item['completed_or_admitted_counter_path'].replace('.', '/'))
        compare(item['model'] + ':counter_delta', count, item['counter_delta'])
        near(item['model'] + ':observed_rate_hz', count / interval, item['observed_rate_hz'])
        stage = item['timing_stage']
        a = first['data']['pipeline_metrics']['stages'][stage]
        b = last['data']['pipeline_metrics']['stages'][stage]
        n = b['count'] - a['count']
        compare(stage + ':timing_count', n, item['timing_delta_count'])
        near(stage + ':window_mean_ms', (b['total_ms'] - a['total_ms']) / n, item['window_mean_stage_ms'])
    with (perf_dir/'llm_cases.csv').open(encoding='utf-8-sig', newline='') as stream:
        llm = list(csv.DictReader(stream))
    with (perf_dir/'tts_cases.csv').open(encoding='utf-8-sig', newline='') as stream:
        tts = list(csv.DictReader(stream))
    with (perf_dir/'windows_gpu_timeseries.csv').open(encoding='utf-8-sig', newline='') as stream:
        gpu = list(csv.DictReader(stream))
    compare('llm_cases', len(llm), 5)
    compare('tts_cases', len(tts), 5)
    compare('gpu_samples', len(gpu), 180)
    for row in llm:
        near('llm_%s:decode_tokens_per_second' % row['case'], float(row['eval_count']) / (float(row['eval_duration_ms']) / 1000), float(row['decode_tokens_per_second']))
    for row in tts:
        near('tts_%s:rtf' % row['case'], float(row['rpc_ms']) / 1000 / float(row['audio_seconds']), float(row['rpc_real_time_factor']))
        near('tts_%s:pcm_duration' % row['case'], int(row['samples']) / int(row['sample_rate']), float(row['audio_seconds']))
        compare('tts_%s:cache_hit' % row['case'], row['cache_hit'].lower(), 'false')
    for column in ['rpc_ms', 'first_content_ms', 'decode_tokens_per_second']:
        near('llm_median:' + column, statistics.median(float(row[column]) for row in llm), model_report['llm'][column]['median'])
    for column in ['rpc_ms', 'audio_seconds', 'rpc_real_time_factor']:
        near('tts_median:' + column, statistics.median(float(row[column]) for row in tts), model_report['tts_metrics'][column]['median'])
    near('gpu_peak_used_mib', max(float(row['used_mib']) for row in gpu), model_report['windows_gpu']['used_mib']['max'])
    near('gpu_minimum_free_mib', min(float(row['free_mib']) for row in gpu), model_report['windows_gpu']['free_mib']['min'])
    gui = [json.loads(line) for line in (perf_dir/'model_gui.public.jsonl').read_text().splitlines()]
    snapshots = [row for row in gui if row['event'] == 'GUI_SAMPLE']
    compare('gui_samples', len(snapshots), 180)
    compare('gui_fault_max', max(row['gui_fault_count'] for row in snapshots), 0)
    compare('gui_main_paused_mic_closed_axis_stopped', all(row['ui_page'] == 'main' and row['hf_state'] == 'PAUSED' and row['microphone_open'] is False and row['pan']['automatic_following'] is False for row in snapshots), True)
    compare('performance_history_has_distinct_startup', load(perf_dir/'window_contract.public.json')['startup_sha256'] == baseline['baseline_startup_sha256'], False)
    near('window_offset_s', resource_report['resource_start_monotonic_s'] - model_report['board_start_monotonic_s'], resource_report['start_offset_s'])
    near('window_overlap_s', min(resource_report['resource_end_monotonic_s'], model_report['board_end_monotonic_s']) - max(resource_report['resource_start_monotonic_s'], model_report['board_start_monotonic_s']), resource_report['overlap_s'])
    return {'status': 'PASS' if all(row['passed'] for row in checks) else 'FAIL', 'scope': 'OFFLINE_RECOMPUTATION_OF_PRESERVED_HISTORICAL_BOARD_RECORDS',
            'checks': checks, 'hardware_executed_now': False, 'new_build_board_verified': False,
            'historical_groups': ['runtime_9a4f', 'dpu_20261021', 'performance_20261102']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path, help='new directory outside the source tree')
    args = parser.parse_args()
    out = args.out.resolve()
    if out.exists() or out == ROOT or ROOT in out.parents:
        parser.error('choose a fresh external output directory')
    result = evaluate(ROOT)
    out.mkdir(parents=True)
    (out/'comparison.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    with (out/'comparison.csv').open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=['check', 'observed', 'reference', 'tolerance', 'passed'])
        writer.writeheader()
        writer.writerows(result['checks'])
    print(result['status'], len(result['checks']), 'preserved-evidence checks', out)
    return 0 if result['status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())

