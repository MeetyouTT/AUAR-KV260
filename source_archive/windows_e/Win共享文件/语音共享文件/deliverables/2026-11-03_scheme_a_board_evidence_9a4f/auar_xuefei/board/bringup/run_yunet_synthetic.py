#!/usr/bin/env python3
"""Run the two packaged synthetic YuNet inputs on an exclusively owned target DPU and save actual tensors."""
import argparse
from contextlib import ExitStack
import fcntl
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]


def load(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--describe', action='store_true', help='inspect fixtures without loading target runtime libraries')
    p.add_argument('--model', type=Path, help='the pinned historical YuNet xmodel on the target board')
    p.add_argument('--out', type=Path, help='fresh external directory for actual target tensors and comparison')
    args = p.parse_args()
    fixture = load(ROOT/'data/board_reference/yunet_synthetic/manifest.json')
    for case in fixture['cases']:
        for f in [case['input']] + case['outputs']:
            if sha(ROOT/f['file']) != f['sha256']:
                raise ValueError('Fixture SHA mismatch: '+f['file'])
    if args.describe:
        print(json.dumps({'scope': 'fixture_inspection_only', 'cases': [v['sample'] for v in fixture['cases']],
                          'model_sha256': fixture['model_sha256'], 'maximum_integer_difference': fixture['maximum_integer_difference'],
                          'hardware_executed': False, 'reference': 'data/board_reference/yunet_synthetic/manifest.json'}))
        return 0
    if args.model is None or args.out is None:
        p.error('--model and --out are required on the target board')
    if platform.machine() not in ('aarch64', 'arm64'):
        p.error('the fixed-input execution requires the target AArch64 board')
    out = args.out.resolve()
    if out.exists() or out == ROOT or ROOT in out.parents:
        p.error('choose a fresh directory outside the package')
    if sha(args.model) != fixture['model_sha256']:
        raise ValueError('Model differs from the fixed reference inputs')
    sys.path[:0] = [str(ROOT/'src'), str(ROOT/'src/models/adapt')]
    import numpy as np
    from dpu_vision_runtime import PinnedRunner, encode
    manifest = ROOT/'data/board_reference/yunet_compiler_manifest.json'
    out.mkdir(parents=True)
    result = {'scope': 'TARGET_BOARD_YUNET_SYNTHETIC_TENSOR_COMPARISON', 'status': 'FAIL',
              'hardware_executed': False, 'board_verified': False, 'model_sha256': fixture['model_sha256'],
              'maximum_integer_difference': fixture['maximum_integer_difference'], 'cases': []}
    try:
        result['target'] = {'architecture': platform.machine(), 'kernel': os.uname().release}
        for key, path in [('device_tree_sha256', Path('/sys/firmware/fdt')),
                          ('boot_id_file_sha256', Path('/proc/sys/kernel/random/boot_id'))]:
            result['target'][key] = sha(path) if path.is_file() else None
        name = Path('/proc/device-tree/fpga-full/firmware-name')
        result['target']['firmware_name'] = name.read_bytes().rstrip(bytes([0])).decode() if name.is_file() else None
        # This is the same exclusive lock used by the original fixed-input runner.
        with ExitStack() as stack:
            lock = stack.enter_context(Path('/run/aura-person-dpu.lock').open('a+'))
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            owner = SimpleNamespace(fingerprint='0x101000056010407', ownership=lock)
            runner = PinnedRunner(args.model, manifest, owner)
            stack.callback(runner.close)
            metas = {t.name: t for t in runner.outputs}
            for case in fixture['cases']:
                image = np.frombuffer((ROOT/case['input']['file']).read_bytes(), dtype=np.uint8).reshape(case['input']['shape'])
                encoded = encode(image.astype(np.float32)[None]/256., runner.input_fix)
                values = runner.execute_encoded(encoded)
                result['hardware_executed'] = True
                row = {'sample': case['sample'], 'input_sha256': case['input']['sha256'],
                       'submit_wait_ms': runner.last_ms, 'heads': []}
                for i, ref in enumerate(case['outputs']):
                    value = values[ref['tensor_name']]
                    expected = np.frombuffer((ROOT/ref['file']).read_bytes(), dtype=np.int8).reshape(ref['shape'])
                    if list(value.shape) != ref['shape'] or not np.isfinite(value).all():
                        raise ValueError('Invalid actual tensor '+ref['tensor_name'])
                    integers = np.rint(value*(2.**metas[ref['tensor_name']].get_attr('fix_point'))).astype(np.int16)
                    difference = np.abs(integers-expected.astype(np.int16))
                    actual = integers.clip(-128,127).astype(np.int8).tobytes()
                    filename = 'sample_%d_head_%d.actual.i8' % (case['sample'],i)
                    (out/filename).write_bytes(actual)
                    row['heads'].append({'name': ref['tensor_name'], 'shape': ref['shape'],
                                         'maximum_integer_difference': int(difference.max()), 'different_elements': int(np.count_nonzero(difference)),
                                         'reference_sha256': ref['sha256'], 'actual_file': filename, 'actual_sha256': hashlib.sha256(actual).hexdigest(),
                                         'passed': int(difference.max())<=fixture['maximum_integer_difference']})
                result['cases'].append(row)
            result['status'] = 'PASS' if len(result['cases'])==2 and all(h['passed'] for c in result['cases'] for h in c['heads']) else 'FAIL'
            result['board_verified'] = result['status']=='PASS'
    except Exception as exc:
        result.update(status='FAIL', board_verified=False, error=type(exc).__name__+': '+str(exc))
    finally:
        (out/'comparison.json').write_text(json.dumps(result, indent=2)+'\n')
    print(result['status'], out/'comparison.json')
    return 0 if result['status']=='PASS' else 1


if __name__=='__main__':
    sys.exit(main())

