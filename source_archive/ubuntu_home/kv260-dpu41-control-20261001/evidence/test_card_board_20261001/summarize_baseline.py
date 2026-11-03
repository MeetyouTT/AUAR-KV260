#!/usr/bin/env python3
"""Validate collected baseline evidence and summarize the six 60-second runs."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import statistics

root = Path(__file__).resolve().parent
target = root / 'baseline_inference_summary.json'
if target.exists():
    raise SystemExit('Refusing to overwrite existing summary')

def records(phase):
    result = {}
    for line in (root / (phase + '.results.jsonl')).read_text().splitlines():
        r = json.loads(line)
        if r['type'] == 'command':
            if not r['complete'] or r['exit_code'] != 0:
                raise RuntimeError('Incomplete/failed command: ' + phase + '/' + r['id'])
            p = root / (phase + '.' + r['id'] + '.output')
            if hashlib.sha256(p.read_bytes()).hexdigest() != r['integrity_sha256']:
                raise RuntimeError('Output hash mismatch: ' + str(p))
            result[r['id']] = r
    return result

classification = records('20-resnet18-classification')['classification']
top = re.search(r'r.index 258 Samoyed, Samoyede, r.score ([0-9.]+)', classification['output'])
if top is None:
    raise RuntimeError('Expected Top-1 output not found')
performance = records('22-performance')
if len(performance) != 6:
    raise RuntimeError('Exactly six completed performance runs required')
runs = []
for threads in (1, 2):
    for repeat in (1, 2, 3):
        key = 'perf_t%d_r%d' % (threads, repeat)
        r = performance[key]
        s = r['output']
        fps = re.findall(r'^FPS=([0-9.]+)$', s, re.M)
        if len(fps) != 1 or ('0/60 seconds, %d threads running' % threads) not in s:
            raise RuntimeError('Incorrect benchmark parameters/output: ' + key)
        before, after = s.split('TEMPERATURE_AFTER_MILLIC', 1)
        def temperatures(text):
            return {int(k): int(v) / 1000.0 for k, v in re.findall(r'temp(\d+)_input=(\d+)', text)}
        runs.append({'id': key, 'threads': threads, 'repeat': repeat,
                     'window_seconds': 60, 'fps': float(fps[0]),
                     'temperature_before_c': temperatures(before),
                     'temperature_after_c': temperatures(after),
                     'started_utc': r['started_utc'], 'finished_utc': r['finished_utc'],
                     'output_sha256': r['integrity_sha256'],
                     'evidence': '22-performance.' + key + '.output'})

post = records('23-post-test')
state = post['post_test_state']['output']
expected_hashes = {
    '/lib/firmware/xilinx/kv260-benchmark-b4096/kv260-benchmark-b4096.bit.bin': '7d12c877e0fde40a243d2350b1a2227f565788bf9e2dcae4439d07f213d40a3f',
    '/lib/firmware/xilinx/kv260-benchmark-b4096/kv260-benchmark-b4096.dtbo': '36338937904e5ec988566d7341f6504edba34c01bd7e2e3f2025ab0069337e35',
    '/lib/firmware/xilinx/kv260-benchmark-b4096/kv260-benchmark-b4096.xclbin': 'fc3abb934eec544e49a17c484336cf177258f475522cefc994ec458b726f69ac',
    '/usr/share/vitis_ai_library/models/resnet18/resnet18.xmodel': '4d4d669c84b6d5aa6f731b389ebcf0f51fb1449752cf5fa4a4beddd496c3c0ef',
    '/home/root/kv260-test-20261001/pytorch-resnet-dog.jpg': 'f3f87bb8ab3c26c7ecfd3ac60421d7f32b0503d1d6c5baf8bac42ed93d86351a',
}
actual_hashes = {p: h for h, p in re.findall(r'^([0-9a-f]{64})  (/.+)$', state, re.M)}
if any(actual_hashes.get(p) != h for p, h in expected_hashes.items()):
    raise RuntimeError('Post-test firmware/model/image hash mismatch')
active = False
for line in state.splitlines():
    fields = line.split()
    if len(fields) == 6 and fields[0] == 'kv260-benchmark-b4096' and fields[-1] == '0,':
        active = True
if not active:
    raise RuntimeError('Official app not confirmed active')
query = json.loads(post['post_test_dpu']['output'])
if query['DPU IP Spec']['DPU Core Count'] != 1 or query['DPU IP Spec']['IP version'] != 'v4.1.0':
    raise RuntimeError('Unexpected DPU after testing')
kernel = query['kernels'][0]
if kernel['fingerprint'] != '0x101000056010407' or kernel['cu_addr'] != '0xa0010000':
    raise RuntimeError('Unexpected DPU architecture/address')

stats = {}
for threads in (1, 2):
    values = [r['fps'] for r in runs if r['threads'] == threads]
    stats[str(threads)] = {'median_fps': statistics.median(values),
                           'min_fps': min(values), 'max_fps': max(values),
                           'runs': 3, 'window_seconds': 60}
all_temps = [v for r in runs for section in ('temperature_before_c', 'temperature_after_c')
             for v in r[section].values()]
summary = {'created_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'application': 'kv260-benchmark-b4096', 'candidate_firmware_loaded': False,
           'classification': {'top1_index': 258, 'top1_name': 'Samoyed, Samoyede',
                              'score': float(top[1]), 'exit_code': 0,
                              'output_sha256': classification['integrity_sha256']},
           'runs': runs, 'statistics': stats,
           'sampled_temperature_min_c': min(all_temps),
           'sampled_temperature_max_c': max(all_temps),
           'post_test_hashes_match': True, 'post_test_dpu': kernel,
           'historical_image_identity_confirmed': False,
           'limits': ['Temperature measured only before/after each run; no continuous peak measurement.',
                      'Benchmark preloads/resizes its images; not full camera/storage pipeline FPS.',
                      'Historical image hash and exact benchmark settings remain unconfirmed.']}
with target.open('x') as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)
    f.write('\n')
print(json.dumps({'top1_score': summary['classification']['score'], 'statistics': stats,
                  'sampled_temperature_min_c': summary['sampled_temperature_min_c'],
                  'sampled_temperature_max_c': summary['sampled_temperature_max_c'],
                  'post_test_hashes_match': True}, ensure_ascii=False))
