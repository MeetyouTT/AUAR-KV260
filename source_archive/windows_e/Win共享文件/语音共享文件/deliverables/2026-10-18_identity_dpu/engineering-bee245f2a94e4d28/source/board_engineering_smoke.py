"""Bounded DPU execution of public/synthetic vectors, without identity enrollment."""
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.request
import numpy as np
import vart
import xir

ROOT = Path(__file__).resolve().parent
assert os.uname().machine == 'aarch64'
assert Path('/sys/block/mmcblk1/device/cid').read_text().strip() == '0353445345333247805558c00401a100'
boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert boot == '94bbc908-4eb8-4111-9435-db2eb1e5a511', 'Recheck after boot change'
manifest = json.loads((ROOT/'manifest.json').read_text())
for name, meta in manifest['files'].items():
    data = (ROOT/name).read_bytes()
    assert len(data) == meta['bytes'] and hashlib.sha256(data).hexdigest() == meta['sha256']


def camera():
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open('http://127.0.0.1:8790/health', timeout=3) as response:
        s = json.load(response)
    return {k: s.get(k) for k in ('pid', 'service_epoch', 'detected_frames', 'observation_age_ms',
                                 'camera_error', 'detector_error', 'identity_recognition')}


def cosine(a, b):
    a, b = a.reshape(-1).astype(np.float64), b.reshape(-1).astype(np.float64)
    return float(np.dot(a, b)/(np.linalg.norm(a)*np.linalg.norm(b)))


before = camera()
graph = xir.Graph.deserialize(str(ROOT/'sface_engineering.xmodel'))
subgraphs = [s for s in graph.get_root_subgraph().toposort_child_subgraph()
             if s.has_attr('device') and s.get_attr('device') == 'DPU']
assert len(subgraphs) == 1
assert subgraphs[0].get_attr('dpu_fingerprint') == int('0x101000056010407', 16)
runner = vart.Runner.create_runner(subgraphs[0], 'run')
inputs, outputs = runner.get_input_tensors(), runner.get_output_tensors()
assert len(inputs) == len(outputs) == 1
assert list(inputs[0].dims) == [1, 112, 112, 3] and inputs[0].get_attr('fix_point') == 7
assert list(outputs[0].dims) == [1, 128] and outputs[0].get_attr('fix_point') == 5
fixtures = np.load(str(ROOT/'hardware-reference.npz'), allow_pickle=False)
results = []
for name in fixtures['names']:
    source = np.ascontiguousarray(fixtures['input_'+str(name)], dtype=np.int8)
    output = np.zeros(tuple(outputs[0].dims), dtype=np.int8)
    started = time.monotonic()
    job = runner.execute_async([source], [output])
    status = runner.wait(job, 5000)
    elapsed = (time.monotonic()-started)*1000
    assert status == 0, 'VART execution failed/timed out: '+str(status)
    expected = fixtures['quantized_'+str(name)]
    difference = np.abs(output.reshape(-1).astype(np.int16)-expected.astype(np.int16))
    score = cosine(output, expected)
    results.append({'sample': str(name), 'submit_wait_ms': round(elapsed, 3),
                    'cosine_to_host_quantized': score, 'maximum_integer_difference': int(difference.max()),
                    'cosine_to_original_cpu': cosine(output.astype(np.float32)/32., fixtures['fp32_'+str(name)]),
                    'output_sha256': hashlib.sha256(output.tobytes()).hexdigest(),
                    'host_quantized_agreement': bool(difference.max() <= 1 or score >= .995)})
    time.sleep(.1)
after = camera()
report = {'scope': 'ONESHOT_ENGINEERING_DPU_EXECUTION_NOT_REAL_IDENTITY_OR_SCHEDULER_ACCEPTANCE',
          'model_sha256': manifest['files']['sface_engineering.xmodel']['sha256'],
          'boot_id': boot, 'results': results, 'camera_before': before, 'camera_after': after,
          'camera_owner_preserved': before['pid'] == after['pid'] and before['service_epoch'] == after['service_epoch'],
          'camera_detection_advanced': after['detected_frames'] > before['detected_frames'],
          'identity_enrollment_or_production_deployment': False, 'representative_calibration': False,
          'independent_identity_evaluation': False, 'unified_dpu_scheduler_tested': False}
report['status'] = 'PASS_ENGINEERING_SMOKE' if all(r['host_quantized_agreement'] for r in results) and report['camera_owner_preserved'] and report['camera_detection_advanced'] and not after['camera_error'] and not after['detector_error'] else 'FAILED_ENGINEERING_SMOKE'
(ROOT/'smoke-result.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report), flush=True)
raise SystemExit(0 if report['status'] == 'PASS_ENGINEERING_SMOKE' else 1)
