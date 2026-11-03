"""Compile a quantized candidate and record actual XIR hardware interfaces."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import xir


def tensor(value):
    return {'name': value.name, 'dims': list(value.dims), 'dtype': str(value.dtype),
            'fix_point': value.get_attr('fix_point') if value.has_attr('fix_point') else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kind', choices=['sface', 'yunet'])
    parser.add_argument('--exported', type=Path)
    args = parser.parse_args()
    source = Path('/work') / (args.kind + '-public-int8')
    export_directory = Path('/work/sface-public-export') if args.kind == 'sface' else source
    raw = [args.exported] if args.exported else sorted(export_directory.glob('*.xmodel'))
    if len(raw) != 1:
        raise ValueError('Expected exactly one quantizer-exported model')
    destination = Path('/work') / (args.kind + '-compiled')
    destination.mkdir(parents=True, exist_ok=True)
    name = args.kind + '_public_int8'
    with (destination / 'compiler.log').open('w') as log:
        result = subprocess.run(['vai_c_xir', '-x', str(raw[0]), '-a', '/work/arch.json',
                                 '-o', str(destination), '-n', name], stdout=log, stderr=subprocess.STDOUT)
    if result.returncode:
        raise RuntimeError('Compiler failed; inspect the private compiler.log')
    path = destination / (name + '.xmodel')
    graph = xir.Graph.deserialize(str(path))
    partitions = []
    for sub in graph.get_root_subgraph().toposort_child_subgraph():
        partitions.append({'name': sub.get_name(),
            'device': sub.get_attr('device') if sub.has_attr('device') else None,
            'fingerprint': hex(sub.get_attr('dpu_fingerprint')) if sub.has_attr('dpu_fingerprint') else None,
            'ops': dict(Counter(op.get_type() for op in sub.get_ops())),
            'inputs': [tensor(t) for t in sub.get_input_tensors()],
            'outputs': [tensor(t) for t in sub.get_output_tensors()]})
    dpu = [s for s in partitions if s['device'] == 'DPU']
    if len(dpu) != 1 or dpu[0]['fingerprint'] != '0x101000056010407':
        raise ValueError('A single matching KV260 DPU partition is required')
    if any(t['dims'][0] != 1 for t in dpu[0]['inputs'] + dpu[0]['outputs']):
        raise ValueError('Board deployment requires batch one at every DPU port')
    report = {'scope': 'COMPILED_CANDIDATE_NOT_PRODUCTION_ACCEPTED', 'kind': args.kind,
              'file': path.name, 'bytes': path.stat().st_size,
              'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'partitions': partitions,
              'public_simulation': json.loads((source / 'evaluation-report.json').read_text()),
              'board_tested': False, 'field_accepted': False}
    (destination / 'manifest.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
