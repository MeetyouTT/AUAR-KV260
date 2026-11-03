"""Run the actual VAI 3.0 inspector only after CPU math parity passes."""
from pathlib import Path
import json
import numpy as np
import torch
from pytorch_nndct.apis import Inspector
from reconstruct_sface import reconstruct, verify

torch.set_num_threads(2)
source = Path('/models/sface_2021dec.onnx')
full, normalization = reconstruct(source)
fixture = np.load('/work/reference-parity.npz', allow_pickle=False)
parity = verify(full, fixture)
core, _ = reconstruct(source, core_only=True)
with torch.no_grad():
    for name in fixture['names']:
        value = torch.from_numpy(fixture['input_'+str(name)])
        if not torch.allclose(core((value-127.5)*.0078125), full(value), atol=1e-5, rtol=1e-5):
            raise ValueError('CPU normalization boundary is not equivalent')
target = json.loads(Path('/work/arch.json').read_text())['fingerprint']
result = {'scope': 'OFFLINE_FP32_EQUIVALENCE_AND_ACTUAL_VAI_INSPECTOR', 'target': target,
          'weights_changed': False, 'trained': False, 'quantized': False, 'board_verified': False,
          'torch_version': torch.__version__, 'parity': parity, 'normalization': normalization,
          'cpu_normalization_boundary_verified': True}
Path('/work/sface-equivalence.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result, indent=2), flush=True)
inspector = Inspector(target)
inspector.inspect(core, (torch.zeros(1, 3, 112, 112),), device=torch.device('cpu'),
                  output_dir='/work/inspector', verbose_level=2, image_format=None)
result['inspector_finished'] = True
Path('/work/sface-inspector-result.json').write_text(json.dumps(result, indent=2)+'\n')
print('Actual VAI inspector completed', flush=True)
