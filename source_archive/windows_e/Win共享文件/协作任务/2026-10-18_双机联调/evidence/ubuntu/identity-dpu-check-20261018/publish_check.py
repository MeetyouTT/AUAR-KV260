"""Publish check scripts/metrics only; exclude images, tensors, weights and deps."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil

JOB = Path(__file__).parent
SHARE = Path('/home/ghmd/Win共享文件')
OUT = SHARE/'协作任务/2026-10-18_双机联调/evidence/ubuntu/identity-dpu-check-20261018'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mapping(path):
    rows = []
    current = None
    for line in path.read_text().splitlines():
        if line.startswith('node name: '):
            if current:
                rows.append(current)
            current = {'name': line[11:]}
        elif current:
            for prefix, key in [('op type: ', 'op'), ('assigned device: ', 'device'), ('hardware constraints: ', 'reason')]:
                if line.startswith(prefix):
                    current[key] = line[len(prefix):]
    if current:
        rows.append(current)
    return {'devices': dict(Counter(row.get('device') for row in rows)),
            'cpu_operators': dict(Counter(row['op'] for row in rows if row.get('device') == 'cpu')),
            'cpu_details': [row for row in rows if row.get('device') == 'cpu']}


def main():
    original = mapping(JOB/'inspector/inspect_0x101000056010407.txt')
    first = mapping(JOB/'inspector-rewrite/inspect_0x101000056010407.txt')
    second = mapping(JOB/'inspector-rewrite-v2/inspect_0x101000056010407.txt')
    assert original['cpu_operators'] == {'nndct_prelu': 27, 'nndct_dense': 1}
    assert second['devices'].get('cpu', 0) == 0 and second['devices']['dpu'] == 139
    parity = json.loads((JOB/'rewrite-v2-equivalence.json').read_text())['parity']
    assert len(parity) == 4 and all(r['cosine'] > .99999 and r['maximum_absolute_error'] < .01 for r in parity)
    tests = (JOB/'rewrite-tests.log').read_text()
    assert 'Ran 3 tests' in tests and tests.rstrip().endswith('OK')
    source = SHARE/'共享文件夹/aura/models/vision/sface_2021dec.onnx'
    assert digest(source) == '0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79'
    files = ['audit_graph.py', 'reconstruct_sface.py', 'export_reference.py', 'inspect_sface.py',
             'rewrite_sface.py', 'inspect_rewrite.py', 'rewrite_sface_v2.py', 'inspect_rewrite_v2.py',
             'test_rewrite.py', 'publish_check.py', 'graph-and-tools.json', 'tool-availability.json',
             'onnx-dependency.json', 'sface-equivalence.json', 'sface-inspector-result.json',
             'rewrite-equivalence.json', 'rewrite-inspector-result.json',
             'rewrite-v2-equivalence.json', 'rewrite-v2-inspector-result.json', 'rewrite-tests.log',
             'inspector/inspect_0x101000056010407.txt', 'inspector-rewrite/inspect_0x101000056010407.txt',
             'inspector-rewrite-v2/inspect_0x101000056010407.txt']
    OUT.mkdir(parents=True, exist_ok=True)
    entries = []
    for rel in files:
        src = JOB/rel;dst = OUT/rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists():
            assert digest(dst) == digest(src), 'Do not overwrite changed shared evidence'
        else:
            shutil.copyfile(src, dst)
        assert digest(src) == digest(dst)
        entries.append({'path': rel, 'bytes': dst.stat().st_size, 'sha256': digest(dst)})
    arch = Path('/home/ghmd/kv260-dpu41-control-20261001/test_bundle/provenance/hardware/arch.json')
    shutil.copyfile(arch, OUT/'target_arch.json')
    assert digest(arch) == digest(OUT/'target_arch.json')
    entries.append({'path': 'target_arch.json', 'bytes': arch.stat().st_size, 'sha256': digest(arch)})
    summary = {'status': 'FP32_REWRITE_PARITY_AND_VAI_INSPECTOR_PASS_NOT_DEPLOYABLE_MODEL',
        'checked_utc': datetime.now(timezone.utc).isoformat(), 'target_fingerprint': '0x101000056010407',
        'container_image': 'xilinx/vitis-ai-pytorch-cpu:ubuntu2004-3.0.0.106', 'image_id_prefix': '8b2d3517c0a9',
        'original': original, 'first_rewrite': first, 'second_rewrite': second,
        'fp32_parity': parity, 'rewrite_boundary_tests_passed': 3, 'source_model_sha256': digest(source),
        'source_model_modified': False, 'trained': False, 'int8_quantized': False,
        'complete_xmodel_compiled': False, 'board_tested': False, 'yolo_mixed_workload_tested': False,
        'frozen_identity_calibration_and_independent_test_data_found': False,
        'production_code_modified': False, 'private_or_reference_input_tensors_published': False,
        'files': entries}
    (OUT/'verification.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({'status': summary['status'], 'original_cpu_operators': original['cpu_operators'],
        'rewritten_devices': second['devices'], 'fp32_samples': len(parity),
        'boundary_tests_passed': 3, 'shared_artifacts': len(entries),
        'shared_bytes': sum(x['bytes'] for x in entries)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
