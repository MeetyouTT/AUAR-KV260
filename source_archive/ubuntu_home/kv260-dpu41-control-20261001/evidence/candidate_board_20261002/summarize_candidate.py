#!/usr/bin/env python3
"""Verify candidate inference/restore evidence and compare against the fixed official baseline."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import statistics

root = Path(__file__).resolve().parent
baseline = root.parent / 'test_card_board_20261001'
target = root / 'candidate_board_summary.json'
if target.exists():
    raise SystemExit('Refusing to overwrite existing summary')

def records(phase):
    result = {}
    for line in (root / (phase + '.results.jsonl')).read_text().splitlines():
        r = json.loads(line)
        if r['type'] == 'command':
            if not r['complete'] or r['exit_code'] != 0:
                raise RuntimeError('Failed/incomplete command: ' + phase + '/' + r['id'])
            p = root / (phase + '.' + r['id'] + '.output')
            if hashlib.sha256(p.read_bytes()).hexdigest() != r['integrity_sha256']:
                raise RuntimeError('Evidence output hash mismatch: ' + str(p))
            result[r['id']] = r
    return result

def top5(text):
    return [(int(i), float(s)) for i, s in re.findall(r'r.index (\d+) [^\n]*?r.score ([0-9.]+)', text)]

official_scores = top5((baseline / '20-resnet18-classification.classification.output').read_text())
candidate_class = records('08-candidate-classification')['candidate_classification']
restore = records('14-restored-verification')
restored_class = restore['restored_classification']
if len(official_scores) != 5 or top5(candidate_class['output']) != official_scores or top5(restored_class['output']) != official_scores:
    raise RuntimeError('Top-5 comparison failed')
for phase in ('04-install', '05-unload-official', '06-load-candidate', '07-candidate-runtime',
              '09-candidate-warmup', '12-unload-candidate', '13-restore-official'):
    records(phase)
perf = records('10-candidate-performance')
if len(perf) != 6:
    raise RuntimeError('Exactly six performance runs required')
runs = []
for threads in (1, 2):
    for repeat in (1, 2, 3):
        key = 'candidate_perf_t%d_r%d' % (threads, repeat)
        r = perf[key]
        output = r['output']
        fps = re.findall(r'^FPS=([0-9.]+)$', output, re.M)
        if len(fps) != 1 or ('0/60 seconds, %d threads running' % threads) not in output:
            raise RuntimeError('Unexpected benchmark parameters: ' + key)
        before, after = output.split('TEMPERATURE_AFTER_MILLIC', 1)
        def temps(s):
            return {int(k): int(v) / 1000 for k, v in re.findall(r'temp(\d+)_input=(\d+)', s)}
        runs.append({'id': key, 'threads': threads, 'repeat': repeat, 'window_seconds': 60,
                     'fps': float(fps[0]), 'temperature_before_c': temps(before),
                     'temperature_after_c': temps(after), 'started_utc': r['started_utc'],
                     'finished_utc': r['finished_utc'], 'output_sha256': r['integrity_sha256']})

post = records('11-candidate-post-test')
before_query = json.loads((baseline / '23-post-test.post_test_dpu.output').read_text())
candidate_query = json.loads(post['candidate_after_perf_dpu']['output'])
restore_query = json.loads(restore['restored_dpu_query']['output'])
for query in (candidate_query, restore_query):
    k = query['kernels'][0]
    if query['DPU IP Spec']['DPU Core Count'] != 1 or k['fingerprint'] != '0x101000056010407' or k['cu_addr'] != '0xa0010000':
        raise RuntimeError('Unexpected actual DPU architecture')
    if k['DPU Frequency (MHz)'] != 300:
        raise RuntimeError('Unexpected actual DPU frequency')
if restore_query['DPU IP Spec'] != before_query['DPU IP Spec']:
    raise RuntimeError('Original hardware revision not restored')

def active_apps(text):
    result = []
    for line in text.splitlines():
        fields = line.split()
        if len(fields) == 6 and fields[1] == 'XRT_FLAT' and fields[-1].rstrip(',') == '0':
            result.append(fields[0])
    return result

candidate_state = post['candidate_after_perf_state']['output']
restored_state = restore['restored_metadata']['output']
if active_apps(candidate_state) != ['kv260-benchmark-b4096-dpu41'] or active_apps(restored_state) != ['kv260-benchmark-b4096']:
    raise RuntimeError('Final slot/application state mismatch')
for text, name in [(candidate_state, 'kv260-benchmark-b4096-dpu41'), (restored_state, 'kv260-benchmark-b4096')]:
    if name + '.bit.bin' not in text.splitlines() or 'operating' not in text.splitlines():
        raise RuntimeError('Live firmware-name/manager state mismatch')
    if 'firmware: /lib/firmware/xilinx/' + name + '/' + name + '.xclbin' not in text:
        raise RuntimeError('Default VART configuration mismatch')
expected_hashes = {
    '/lib/firmware/xilinx/kv260-benchmark-b4096/kv260-benchmark-b4096.bit.bin': '7d12c877e0fde40a243d2350b1a2227f565788bf9e2dcae4439d07f213d40a3f',
    '/lib/firmware/xilinx/kv260-benchmark-b4096/kv260-benchmark-b4096.dtbo': '36338937904e5ec988566d7341f6504edba34c01bd7e2e3f2025ab0069337e35',
    '/lib/firmware/xilinx/kv260-benchmark-b4096/kv260-benchmark-b4096.xclbin': 'fc3abb934eec544e49a17c484336cf177258f475522cefc994ec458b726f69ac',
    '/lib/firmware/xilinx/kv260-benchmark-b4096/shell.json': '2967ccbc1f75c8d4accd1b6fecc11b16a32a5d7992e56c6eebceb99a3410f777',
    '/lib/firmware/xilinx/kv260-benchmark-b4096-dpu41/kv260-benchmark-b4096-dpu41.bit.bin': '4d2fd04adc41cafc46ac6edcc7050f2edc9283d28aacfffc85e380a7ff1aebbf',
    '/lib/firmware/xilinx/kv260-benchmark-b4096-dpu41/kv260-benchmark-b4096-dpu41.dtbo': 'd19426602f7b4873eb8151099066e280313999cd58b5fbdc7fe89301f68ed39d',
    '/lib/firmware/xilinx/kv260-benchmark-b4096-dpu41/kv260-benchmark-b4096-dpu41.xclbin': '4d9fae142e0a952ea1d1fd1f75395afbb2d485c1b66f507aa9d4cb317532894b',
    '/lib/firmware/xilinx/kv260-benchmark-b4096-dpu41/shell.json': 'a13dbd0a508de4656c3ba22aa9f8a41494a5082bcd585589fc366a56cc5ba1c1',
    '/usr/share/vitis_ai_library/models/resnet18/resnet18.xmodel': '4d4d669c84b6d5aa6f731b389ebcf0f51fb1449752cf5fa4a4beddd496c3c0ef',
    '/usr/share/vitis_ai_library/models/resnet18/resnet18.prototxt': '691c393b15ae87976060a125067534334bd034c3a5193a96f6f5db3f4da3729c',
    '/home/root/kv260-test-20261001/pytorch-resnet-dog.jpg': 'f3f87bb8ab3c26c7ecfd3ac60421d7f32b0503d1d6c5baf8bac42ed93d86351a',
    '/home/root/kv260-test-20261001/samoyed.list': 'bf02d74370fbfdd8d008c7916109a14be3a5b33bd6057522fbb14e95ac2e9caa',
}
for text in (candidate_state, restored_state):
    hashes = {p: h for h, p in re.findall(r'^([0-9a-f]{64})  (/.+)$', text, re.M)}
    if any(hashes.get(p) != h for p, h in expected_hashes.items()):
        raise RuntimeError('Official baseline or input file changed')
baseline_stats = json.loads((baseline / 'baseline_inference_summary.json').read_text())['statistics']
stats = {}
for threads in (1, 2):
    values = [r['fps'] for r in runs if r['threads'] == threads]
    official_median = baseline_stats[str(threads)]['median_fps']
    median = statistics.median(values)
    stats[str(threads)] = {'median_fps': median, 'min_fps': min(values), 'max_fps': max(values),
                           'official_median_fps': official_median,
                           'difference_percent': (median / official_median - 1) * 100}
kernel_stages = {'before_switch': post['kernel_before_switch']['output'],
                 'after_candidate_tests': post['kernel_after_candidate_tests']['output'],
                 'after_restore': restore['kernel_after_restore']['output']}
kernel_counts = {stage: {'unbalanced_overlay_refcount_errors': text.count('of_node_get()/of_node_put() unbalanced'),
                         'overlay_property_leak_warnings': text.count('memory leak will occur if overlay removed')}
                 for stage, text in kernel_stages.items()}
observed_errors = sorted({line for text in kernel_stages.values() for line in text.splitlines()
                          if 'of_node_get()/of_node_put() unbalanced' in line})
restored_kernel = kernel_stages['after_restore']
if not re.search(r'zocl_xclbin_read_axlf eedb44e9-3f77-0244-9ea9-23b953894638 ret: 0', restored_kernel):
    raise RuntimeError('Original runtime UUID not confirmed restored')
if post['kernel_before_switch']['integrity_sha256'] != '75a7d593488306b7ad41b41aa98d9dca736597de0990004f986986bffaeb9597':
    raise RuntimeError('Saved pre-switch kernel log changed')
all_temps = [v for r in runs for section in ('temperature_before_c', 'temperature_after_c') for v in r[section].values()]
summary = {'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'candidate_application': 'kv260-benchmark-b4096-dpu41',
           'candidate_load_and_runtime_pass': True, 'candidate_top5_matches_official': True,
           'restored_top5_matches_official': True, 'top1_score': official_scores[0][1],
           'runs': runs, 'statistics': stats, 'sampled_temperature_min_c': min(all_temps),
           'sampled_temperature_max_c': max(all_temps), 'kernel_log_counts': kernel_counts,
           'observed_refcount_error_events': observed_errors,
           'kernel_count_scope': 'Current ring-buffer snapshots; overwritten history is not covered and counts are not cumulative totals.',
           'overlay_refcount_issue_resolved': False, 'final_active_application': 'kv260-benchmark-b4096',
           'restore_verified': True, 'default_vart_configuration_restored': True,
           'original_hardware_revision_restored': True, 'original_file_hashes_match': True,
           'candidate_ip_spec': candidate_query['DPU IP Spec'], 'restored_ip_spec': restore_query['DPU IP Spec'],
           'limits': ['One model and one fixed image; no other interface, actuator or long stress validation.',
                      'Kernel overlay reference-count and property-lifetime issues remain unresolved.',
                      'Host DRC warnings and incomplete I/O timing constraints remain unchanged.',
                      'Temperature sampled only before/after each run.']}
with target.open('x') as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)
    f.write('\n')
print(json.dumps({k: v for k, v in summary.items() if k in ('statistics', 'top1_score', 'kernel_log_counts',
                  'restore_verified', 'final_active_application', 'sampled_temperature_min_c', 'sampled_temperature_max_c')}, ensure_ascii=False))
