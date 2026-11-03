"""Actual target inspection of an exact rewrite; no production calibration."""
from pathlib import Path
import json
import numpy as np
import torch
from torch import nn
from pytorch_nndct.apis import Inspector
from reconstruct_sface import reconstruct, verify, SubtractScalar, MultiplyScalar
from rewrite_sface_v2 import rewrite

torch.set_num_threads(2)
core, _ = reconstruct(Path('/models/sface_2021dec.onnx'), core_only=True)
rewritten, counts = rewrite(core)
full = nn.Sequential(SubtractScalar(127.5), MultiplyScalar(.0078125), rewritten).eval()
fixture = np.load('/work/reference-parity.npz', allow_pickle=False)
parity = verify(full, fixture)
target = json.loads(Path('/work/arch.json').read_text())['fingerprint']
result = {'scope': 'EXACT_FP32_REWRITE_V2_AND_ACTUAL_VAI_INSPECTOR_NOT_QUANTIZED',
          'target': target, 'source_model_mutated': False, 'trained': False, 'quantized': False,
          'board_verified': False, 'rewrites': counts, 'parity': parity}
Path('/work/rewrite-v2-equivalence.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result, indent=2), flush=True)
Inspector(target).inspect(rewritten, (torch.zeros(1, 3, 112, 112),), device=torch.device('cpu'),
                          output_dir='/work/inspector-rewrite-v2', verbose_level=2, image_format=None)
result['inspector_finished'] = True
Path('/work/rewrite-v2-inspector-result.json').write_text(json.dumps(result, indent=2)+'\n')
print('V2 rewritten graph inspection completed', flush=True)
