"""Check FP32 parity before running the real target-specific Vitis inspector."""
import json
from pathlib import Path
import cv2
import numpy as np
import torch
from pytorch_nndct.apis import Inspector
from reconstruct_yunet import reconstruct, cpu_outputs

torch.set_num_threads(2)
cv2.setNumThreads(2)
model = reconstruct('/models/yunet_2022mar.onnx')
net = cv2.dnn.readNetFromONNX('/models/yunet_2022mar.onnx')
checks = []
for size in (128, 192, 256, 320):
    for kind in ('black', 'random'):
        rng = np.random.RandomState(173)
        raw = np.zeros((1, 3, size, size), np.float32) if kind == 'black' else rng.randint(0, 256, (1, 3, size, size)).astype(np.float32)
        net.setInput(raw)
        reference = net.forward(['loc', 'conf', 'iou'])
        with torch.no_grad():
            heads = [x.numpy() for x in model(torch.from_numpy(raw / 256.))]
        actual = cpu_outputs(heads)
        errors = [float(np.max(np.abs(a.reshape(b.shape) - b))) for a, b in zip(actual, reference)]
        if not all(np.isfinite(a).all() for a in actual) or max(errors) > .0005:
            raise ValueError('YuNet reconstruction parity failed: ' + str(errors))
        checks.append({'size': size, 'input': kind, 'max_abs_errors_loc_conf_iou': errors,
                       'head_shapes': [list(x.shape) for x in heads]})
out = Path('/work/yunet-inspector')
out.mkdir(parents=True, exist_ok=True)
(out / 'fp32-parity.json').write_text(json.dumps({'passed': True, 'checks': checks}, indent=2) + '\n')
print(json.dumps({'fp32_parity_passed': True, 'checks': checks}), flush=True)
Inspector('0x101000056010407').inspect(model, (torch.zeros(1, 3, 320, 320),),
    device=torch.device('cpu'), output_dir=str(out), image_format=None)
