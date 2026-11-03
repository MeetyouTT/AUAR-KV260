"""Fresh batch-one export after batched public evaluation, reusing fixed scales."""
import json
from pathlib import Path
import numpy as np
import torch
from pytorch_nndct.apis import torch_quantizer
from reconstruct_sface import reconstruct
from rewrite_sface_v2 import rewrite
from quantize_sface_public import inputs

torch.set_num_threads(2)
core, _ = reconstruct(Path('/models/sface_2021dec.onnx'), core_only=True)
model, _ = rewrite(core)
source = torch.from_numpy(inputs(np.load('/work/public-faces/calibration_bgr.npy')[:1]).copy())
quantizer = torch_quantizer('test', model, (source,), output_dir='/work/sface-public-int8',
                            device=torch.device('cpu'), bitwidth=8)
with torch.no_grad():
    actual = quantizer.quant_model.eval()(source)
    assert tuple(actual.shape) == (1, 128)
    quantizer.export_xmodel(output_dir='/work/sface-public-export', deploy_check=False)
print(json.dumps({'fresh_export_batch': 1, 'output_shape': list(actual.shape)}), flush=True)
