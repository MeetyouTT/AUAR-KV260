"""Export a few private public/synthetic hardware agreement vectors."""
import argparse
import json
from pathlib import Path
import cv2
import numpy as np
import torch
from pytorch_nndct.apis import torch_quantizer
from dpu_vision_runtime import encode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('kind', choices=['yunet', 'sface'])
    args = parser.parse_args()
    torch.set_num_threads(2)
    cv2.setNumThreads(2)
    work = Path('/work')
    manifest = json.loads((work / (args.kind + '-compiled/manifest.json')).read_text())
    partition = next(s for s in manifest['partitions'] if s['device'] == 'DPU')
    if args.kind == 'yunet':
        from reconstruct_yunet import reconstruct
        from quantize_yunet import image_paths
        model = reconstruct('/models/yunet_2022mar.onnx')
        _, paths = image_paths()
        images = [cv2.resize(cv2.imread(str(p)), (320, 320)) for p in paths[:2]]
        images.extend([np.zeros((320, 320, 3), np.uint8),
                       np.random.RandomState(142).randint(0, 256, (320, 320, 3)).astype(np.uint8)])
        source = lambda image: image.astype(np.float32)[None] / 256.
    else:
        from reconstruct_sface import reconstruct
        from rewrite_sface_v2 import rewrite
        core, _ = reconstruct(Path('/models/sface_2021dec.onnx'), core_only=True)
        model, _ = rewrite(core)
        images = list(np.load('/work/public-faces/test_bgr.npy', mmap_mode='r')[:4])
        source = lambda image: (image[:, :, ::-1].astype(np.float32)[None] - 127.5) / 128.
    quantizer = torch_quantizer('test', model, (torch.zeros(tuple([1, 3] + list(images[0].shape[:2]))),),
        output_dir=str(work / (args.kind + '-public-int8')), device=torch.device('cpu'), bitwidth=8)
    quantized = quantizer.quant_model.eval()
    values = {'images_bgr': np.stack(images)}
    with torch.no_grad():
        for i, image in enumerate(images):
            integers = encode(source(image), partition['inputs'][0]['fix_point'])
            normalized = integers.astype(np.float32) / (2. ** partition['inputs'][0]['fix_point'])
            result = quantized(torch.from_numpy(normalized.transpose(0, 3, 1, 2).copy()))
            if args.kind == 'sface':
                result = (result,)
            for output in result:
                array = output.numpy()
                if args.kind == 'yunet':
                    array = array.transpose(0, 2, 3, 1)
                tensor = next(t for t in partition['outputs'] if tuple(t['dims']) == array.shape)
                values['sample_%d_%s' % (i, tensor['name'])] = np.clip(np.rint(array * 2. ** tensor['fix_point']), -128, 127).astype(np.int8)
    destination = work / (args.kind + '-hardware-vectors.npz')
    np.savez_compressed(str(destination), **values)
    print(json.dumps({'kind': args.kind, 'samples': len(images), 'bytes': destination.stat().st_size,
                      'source': 'public_benchmark_or_synthetic', 'not_for_shared_distribution': True}), flush=True)


if __name__ == '__main__':
    main()
