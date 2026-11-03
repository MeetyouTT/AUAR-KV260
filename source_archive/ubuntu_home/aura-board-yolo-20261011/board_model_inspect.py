import hashlib
import json
from pathlib import Path
import subprocess
import vitis_ai_library
import xir

models = []
for folder in sorted(Path('/usr/share/vitis_ai_library/models').glob('*yolo*nano*')):
    row = {'path': str(folder), 'files': []}
    for p in sorted(folder.iterdir()):
        f = {'name': p.name, 'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
        if p.suffix in ['.json', '.prototxt', '.txt']:
            f['text'] = p.read_text()[:5000]
        if p.suffix == '.xmodel':
            graph = xir.Graph.deserialize(str(p))
            f['subgraphs'] = []
            for sub in graph.get_root_subgraph().toposort_child_subgraph():
                f['subgraphs'].append({'name': sub.get_name(), 'attrs': {k: str(sub.get_attr(k)) for k in ['device', 'fingerprint', 'dpu_name'] if sub.has_attr(k)},
                    'inputs': [{'name': t.name, 'dims': t.dims, 'type': str(t.dtype), 'fix': t.get_attr('fix_point') if t.has_attr('fix_point') else None} for t in sub.get_input_tensors()],
                    'outputs': [{'name': t.name, 'dims': t.dims, 'type': str(t.dtype), 'fix': t.get_attr('fix_point') if t.has_attr('fix_point') else None} for t in sub.get_output_tensors()]})
        row['files'].append(f)
    models.append(row)

result = {'models': models, 'vitis_ai_library': {'path': vitis_ai_library.__file__, 'members': dir(vitis_ai_library)},
    'headers': [str(p) for p in Path('/usr/include/vitis/ai').glob('*yolo*')],
    'examples': [str(p) for p in Path('/home/root/Vitis-AI').glob('**/*yolovx*')][:15],
    'compiler': subprocess.run(['sh', '-c', 'command -v g++'], stdout=subprocess.PIPE, text=True).stdout.strip(),
    'images': [str(p) for p in Path('/usr/share/vitis_ai_library').glob('**/*.jpg')][:30]}
print(json.dumps(result))
