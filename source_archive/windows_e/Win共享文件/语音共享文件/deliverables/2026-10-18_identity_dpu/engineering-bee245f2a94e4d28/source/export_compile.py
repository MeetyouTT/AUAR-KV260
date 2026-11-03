"""Export and compile the engineering model, then audit actual XIR partitions."""
from collections import Counter
from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import xir

WORK = Path('/work')


def run(args, log):
    with log.open('w') as stream:
        process = subprocess.run(args, stdout=stream, stderr=subprocess.STDOUT)
    if process.returncode:
        lines = [re.sub(r'\x1b\[[0-9;]*m', '', s) for s in log.read_text(errors='replace').splitlines()
                 if len(s) < 600 and 'OpInfo:' not in s and '|' not in s]
        print('\n'.join(lines[-28:]), flush=True)
        raise RuntimeError('Command failed (%d): %s; log=%s' % (process.returncode, args[0], log))


def tensor(t):
    return {'name': t.name, 'dims': list(t.dims), 'dtype': str(t.dtype),
            'fix_point': t.get_attr('fix_point') if t.has_attr('fix_point') else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exported', type=Path)
    parser.add_argument('--compiled', type=Path)
    args = parser.parse_args()
    if args.compiled is None:
        if args.exported is None:
            run([sys.executable, '-B', '/work/quantize_sface.py', '--mode', 'test'], WORK/'quantize-test.log')
        raw = [args.exported] if args.exported else sorted((WORK/'quantized-engineering').glob('*.xmodel'))
        if len(raw) != 1:
            raise RuntimeError('Expected exactly one exported quantized xmodel')
        out = WORK/'compiled-engineering'
        out.mkdir(exist_ok=True)
        run(['vai_c_xir', '-x', str(raw[0]), '-a', '/target-arch.json', '-o', str(out), '-n', 'sface_engineering'], WORK/'compile-engineering.log')
        model = out/'sface_engineering.xmodel'
    else:
        model = args.compiled
    graph = xir.Graph.deserialize(str(model))
    root = graph.get_root_subgraph()
    partitions = []
    for sub in root.toposort_child_subgraph():
        fingerprint = next((sub.get_attr(k) for k in ('dpu_fingerprint', 'fingerprint') if sub.has_attr(k)), None)
        partitions.append({'name': sub.get_name(), 'device': sub.get_attr('device') if sub.has_attr('device') else None,
                           'fingerprint': hex(fingerprint) if isinstance(fingerprint, int) else fingerprint,
                           'operator_counts': dict(Counter(op.get_type() for op in sub.get_ops())),
                           'inputs': [tensor(t) for t in sub.get_input_tensors()],
                           'outputs': [tensor(t) for t in sub.get_output_tensors()]})
    dpu = [p for p in partitions if p['device'] == 'DPU']
    expected = json.loads(Path('/target-arch.json').read_text())['fingerprint']
    if not dpu or any(p['fingerprint'] != expected for p in dpu):
        raise RuntimeError('Compiled DPU fingerprint mismatch or missing DPU partition')
    report = {'status': 'COMPILED_ENGINEERING_MODEL_NOT_IDENTITY_ACCURACY_ACCEPTED',
              'finished_utc': datetime.now(timezone.utc).isoformat(),
              'model': str(model), 'bytes': model.stat().st_size,
              'sha256': hashlib.sha256(model.read_bytes()).hexdigest(), 'target_fingerprint': expected,
              'partitions': partitions, 'representative_calibration': False,
              'independent_identity_evaluation': False, 'board_tested': False,
              'limited_metrics': json.loads((WORK/'quantized-engineering/report-test.json').read_text())}
    (WORK/'compiled-engineering-result.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
