"""Measure batch amortization without changing saved PTQ scales."""
from pathlib import Path
import json
import time
import numpy as np
import torch
from pytorch_nndct.apis import torch_quantizer
from reconstruct_sface import reconstruct
from rewrite_sface_v2 import rewrite
from quantize_sface_public import inputs

torch.set_num_threads(2)
core, _ = reconstruct(Path('/models/sface_2021dec.onnx'), core_only=True)
model, _ = rewrite(core)
raw = np.load('/work/public-faces/train_bgr.npy', mmap_mode='r')
quantizer = torch_quantizer('test', model, (torch.zeros(1, 3, 112, 112),),
    output_dir='/work/sface-public-int8', device=torch.device('cpu'), bitwidth=8)
actual = quantizer.quant_model.eval()
first = None
with torch.no_grad():
    for batch in (8, 32, 64):
        before = time.monotonic()
        value = actual(torch.from_numpy(inputs(raw[:batch]).copy())).numpy().reshape(-1, 128)
        seconds = time.monotonic() - before
        if first is None:
            first = value.copy()
        print(json.dumps({'batch': batch, 'seconds': seconds, 'seconds_per_image': seconds / batch,
                          'first_eight_max_abs_difference': float(np.max(np.abs(value[:8] - first)))}), flush=True)
