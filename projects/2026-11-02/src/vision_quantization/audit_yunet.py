"""Export a compact, numeric audit of the pinned YuNet graph for reconstruction."""
import hashlib
import json
from collections import Counter
from pathlib import Path
import onnx
from onnx import numpy_helper

p = Path('/models/yunet_2022mar.onnx')
assert hashlib.sha256(p.read_bytes()).hexdigest() == '50ef07f702a31741ca46a4c0d947773b64143b9362780237bf0d427d6c79bab7'
m = onnx.load(str(p))
out = {'nodes': [], 'initializers': {}, 'operators': dict(Counter(n.op_type for n in m.graph.node)),
       'inputs': {v.name: [d.dim_value for d in v.type.tensor_type.shape.dim] for v in m.graph.input},
       'outputs': [v.name for v in m.graph.output]}
for t in m.graph.initializer:
    out['initializers'][t.name] = list(t.dims)
for n in m.graph.node:
    attrs = {}
    for a in n.attribute:
        v = onnx.helper.get_attribute_value(a)
        if isinstance(v, onnx.TensorProto):
            v = numpy_helper.to_array(v).tolist()
        if isinstance(v, bytes):
            v = v.decode()
        attrs[a.name] = v
    out['nodes'].append({'name': n.name, 'op': n.op_type, 'inputs': list(n.input),
                         'outputs': list(n.output), 'attrs': attrs})
Path('/work/yunet-graph-audit.json').write_text(json.dumps(out, indent=2) + '\n')
print(json.dumps(out, indent=2), flush=True)
