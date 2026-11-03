"""Inspect pinned ONNX graphs/tool availability; does not quantize or compile."""
import argparse
from collections import Counter
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
import sys


def audit(model):
    import onnx
    graph = onnx.load(str(model))
    onnx.checker.check_model(graph)
    tensors = {x.name: x for x in graph.graph.initializer}
    counts = Counter(x.op_type for x in graph.graph.node)
    def shape(value):
        return [d.dim_value or d.dim_param for d in value.type.tensor_type.shape.dim]
    nodes = []
    for node in graph.graph.node:
        attributes = {}
        for attr in node.attribute:
            value = onnx.helper.get_attribute_value(attr)
            if isinstance(value, bytes):
                value = value.decode(errors='replace')
            if not isinstance(value, (int, float, str, list, tuple)):
                value = str(type(value).__name__)
            attributes[attr.name] = value
        nodes.append({'name': node.name, 'op': node.op_type, 'inputs': list(node.input),
                      'outputs': list(node.output), 'attributes': attributes,
                      'parameter_shapes': {n: list(tensors[n].dims) for n in node.input if n in tensors}})
    return {'file': model.name, 'sha256': hashlib.sha256(model.read_bytes()).hexdigest(),
            'opsets': [{'domain': x.domain, 'version': x.version} for x in graph.opset_import],
            'inputs': {x.name: shape(x) for x in graph.graph.input if x.name not in tensors},
            'outputs': {x.name: shape(x) for x in graph.graph.output},
            'operator_counts': dict(counts), 'nodes': nodes, 'parameters': len(tensors),
            'onnx_checker': 'PASS', 'dpu_compatibility': 'NOT_YET_INSPECTED'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--models', type=Path, required=True)
    args = parser.parse_args()
    result = {'scope': 'OFFLINE_GRAPH_AND_LOCAL_TOOLS_ONLY', 'python': sys.version,
              'modules': {n: bool(importlib.util.find_spec(n)) for n in
                          ['onnx', 'onnxruntime', 'torch', 'pytorch_nndct', 'vai_q_onnx', 'xir']}}
    Path('/work/tool-availability.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2), flush=True)
    from pytorch_nndct.apis import Inspector
    result['inspector_signature'] = str(inspect.signature(Inspector))
    result['inspector_inspect_signature'] = str(inspect.signature(Inspector.inspect))
    result['compiler_binaries'] = [str(p) for p in Path(sys.prefix).glob('bin/vai*')]
    result['target_binaries'] = [str(p) for p in Path(sys.prefix).glob('bin/*target*')]
    result['models'] = [audit(args.models/n) for n in ['sface_2021dec.onnx', 'yunet_2022mar.onnx']]
    Path('/work/graph-and-tools.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: result[k] for k in ['modules', 'inspector_signature', 'inspector_inspect_signature',
                                          'compiler_binaries', 'target_binaries']}, indent=2))
    for model in result['models']:
        print(json.dumps({k: v for k, v in model.items() if k != 'nodes'}, indent=2))


if __name__ == '__main__':
    main()
