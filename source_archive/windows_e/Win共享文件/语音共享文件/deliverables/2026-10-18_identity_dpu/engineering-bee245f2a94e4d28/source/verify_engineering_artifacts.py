"""Check actual partition boundaries and integer fixture layout before execution."""
import ast
import hashlib
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).parent
result = json.loads((ROOT/'compiled-engineering-result.json').read_text())
model = ROOT/'compiled-engineering/sface_engineering.xmodel'
assert hashlib.sha256(model.read_bytes()).hexdigest() == result['sha256']
dpu = [p for p in result['partitions'] if p['device'] == 'DPU']
assert len(dpu) == 1 and dpu[0]['fingerprint'] == '0x101000056010407'
assert dpu[0]['inputs'][0]['dims'] == [1, 112, 112, 3] and dpu[0]['inputs'][0]['fix_point'] == 7
assert dpu[0]['outputs'][0]['dims'] == [1, 128] and dpu[0]['outputs'][0]['fix_point'] == 5
assert all(set(p['operator_counts']) <= {'data-fix', 'fix2float'} for p in result['partitions'] if p['device'] != 'DPU')
with np.load(str(ROOT/'hardware-reference.npz'), allow_pickle=False) as data:
    assert list(data['names']) == ['black', 'gray', 'random', 'public_reference']
    for name in data['names']:
        source, expected, cpu = (data[prefix+str(name)] for prefix in ('input_', 'quantized_', 'fp32_'))
        assert source.shape == (1, 112, 112, 3) and source.dtype == np.int8
        assert expected.shape == (128,) and expected.dtype == np.int8 and np.linalg.norm(expected) > 0
        assert cpu.shape == (128,) and np.isfinite(cpu).all()
for name in ('quantize_sface.py', 'export_compile.py', 'board_engineering_smoke.py', 'board_stage_smoke.py', 'build_engineering_bundle.py', 'run_uart.py'):
    ast.parse((ROOT/name).read_bytes())
print(json.dumps({'status': 'PASS_ARTIFACT_AND_INTEGER_FIXTURE_CHECKS', 'dpu_core_partitions': 1,
                  'non_dpu_computation': 'only fix2float output conversion', 'fixture_cases': 4,
                  'source_syntax_checks': 6, 'real_identity_accuracy_tested': False}))
