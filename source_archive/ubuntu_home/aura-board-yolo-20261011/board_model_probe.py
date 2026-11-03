import hashlib
import json
from pathlib import Path
import subprocess
import xir

p = Path('/usr/share/vitis_ai_library/models/yolox_nano_pt/yolox_nano_pt.xmodel')
g = xir.Graph.deserialize(str(p))
dpu = [s for s in g.get_root_subgraph().toposort_child_subgraph() if s.has_attr('device') and s.get_attr('device') == 'DPU']
attrs = [{k: str(v) for k, v in s.get_attrs().items() if k in ['device', 'dpu_name', 'dpu_fingerprint', 'fingerprint', 'runner']} for s in dpu]
result = {'model_sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'dpu_attrs': attrs,
    'attr_keys': [list(s.get_attrs()) for s in dpu],
    'jpeg_source': Path('/home/root/Vitis-AI/examples/vai_library/samples/yolovx/test_jpeg_yolovx.cpp').read_text()[:12000],
    'header': Path('/usr/include/vitis/ai/yolovx.hpp').read_text()[:16000],
    'images': [str(p) for p in Path('/home/root/Vitis-AI/examples').glob('**/*.jpg')][:70]}
print(json.dumps(result))
