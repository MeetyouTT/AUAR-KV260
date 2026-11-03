"""Check equivalent SFace rewrites against the original CPU outputs and DPU."""
from pathlib import Path
import json
import numpy as np
import torch
from torch import nn
from pytorch_nndct.apis import Inspector
from reconstruct_sface import reconstruct, verify, SubtractScalar, MultiplyScalar
from rewrite_sface import rewrite

torch.set_num_threads(2)
source = Path('/models/sface_2021dec.onnx')
core, normalization = reconstruct(source, core_only=True)
rewritten, counts = rewrite(core)
full = nn.Sequential(SubtractScalar(127.5), MultiplyScalar(.0078125), rewritten).eval()
fixture = np.load('/work/reference-parity.npz', allow_pickle=False)
parity = verify(full, fixture)
target = json.loads(Path('/work/arch.json').read_text())['fingerprint']
result = {'scope': 'EXACT_FP32_REWRITE_AND_ACTUAL_VAI_INSPECTOR_NOT_QUANTIZED',
          'target': target, 'source_model_sha256': '0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79',
          'graph_rewritten': True, 'source_model_mutated': False, 'trained': False,
          'learned_parameters_retrained': False, 'quantized': False, 'board_verified': False,
          'rewrites': counts, 'parity': parity}
Path('/work/rewrite-equivalence.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result, indent=2), flush=True)
Inspector(target).inspect(rewritten, (torch.zeros(1, 3, 112, 112),), device=torch.device('cpu'),
                          output_dir='/work/inspector-rewrite', verbose_level=2, image_format=None)
result['inspector_finished'] = True
Path('/work/rewrite-inspector-result.json').write_text(json.dumps(result, indent=2)+'\n')
print('Rewritten graph inspection completed', flush=True)
