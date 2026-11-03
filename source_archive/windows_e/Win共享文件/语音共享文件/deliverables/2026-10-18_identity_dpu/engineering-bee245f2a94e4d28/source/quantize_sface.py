"""PTQ engineering probe for the pinned SFace rewrite; no accuracy acceptance."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import torch
from pytorch_nndct.apis import torch_quantizer
from reconstruct_sface import reconstruct
from rewrite_sface_v2 import rewrite


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['calib', 'test'], required=True)
    parser.add_argument('--data', default='/work/reference-parity.npz')
    parser.add_argument('--output', default='/work/quantized-engineering')
    parser.add_argument('--hardware-reference', type=Path)
    args = parser.parse_args()
    torch.set_num_threads(2)
    core, _ = reconstruct(Path('/models/sface_2021dec.onnx'), core_only=True)
    model, counts = rewrite(core)
    fixtures = np.load(args.data, allow_pickle=False)
    public = fixtures['input_public_reference'].astype(np.float32)
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    quantizer = torch_quantizer(args.mode, model, (torch.from_numpy((public-127.5)/128.),),
                               output_dir=str(output), device=torch.device('cpu'), bitwidth=8)
    quantized = quantizer.quant_model.eval()
    report = {'scope': 'ENGINEERING_QUANTIZATION_ONLY_SINGLE_PUBLIC_REFERENCE_NOT_IDENTITY_ACCURACY',
              'mode': args.mode, 'representative_calibration': False,
              'independent_identity_evaluation': False, 'rewrites': counts,
              'data_sha256': hashlib.sha256(Path(args.data).read_bytes()).hexdigest()}
    with torch.no_grad():
        if args.mode == 'calib':
            # Deterministic photometric variation checks exportability only.
            # One public face cannot represent identities or deployment conditions.
            samples = 0
            for gain in (.65, .8, 1., 1.15):
                for offset in (-20., -8., 8., 20.):
                    for flip in (False, True):
                        raw = np.clip(public*gain+offset, 0, 255)
                        if flip:
                            raw = raw[:, :, :, ::-1].copy()
                        quantized(torch.from_numpy(((raw-127.5)/128.).copy()))
                        samples += 1
            quantizer.export_quant_config()
            report['photometric_samples'] = samples
        else:
            metrics = []
            hardware = {'names': fixtures['names']}
            for name in fixtures['names']:
                source = fixtures['input_'+str(name)].astype(np.float32)
                reference = fixtures['output_'+str(name)].reshape(-1).astype(np.float64)
                normalized = (source-127.5)/128.
                if args.hardware_reference:
                    integers = np.clip(np.floor(normalized*128.+.5), -128, 127).astype(np.int8)
                    normalized = integers.astype(np.float32)/128.
                    hardware['input_'+str(name)] = np.transpose(integers, (0, 2, 3, 1)).copy()
                value = quantized(torch.from_numpy(normalized)).numpy().reshape(-1).astype(np.float64)
                if value.shape != (128,) or not np.isfinite(value).all() or np.linalg.norm(value) <= 1e-8:
                    raise ValueError('Invalid quantized feature')
                metrics.append({'sample': str(name), 'cosine': float(np.dot(value, reference)/(np.linalg.norm(value)*np.linalg.norm(reference))), 'maximum_absolute_error': float(np.max(np.abs(value-reference)))})
                if args.hardware_reference:
                    hardware['quantized_'+str(name)] = np.clip(np.rint(value*32.), -128, 127).astype(np.int8)
                    hardware['fp32_'+str(name)] = reference.astype(np.float32)
            # Export a single batch with the face as the final forward input.
            if args.hardware_reference:
                np.savez_compressed(str(args.hardware_reference), **hardware)
                report['hardware_reference_input'] = 'NHWC INT8 fix_point=7; floor(normalized*128+.5) clipped'
                report['hardware_reference_output'] = 'INT8 fix_point=5'
            else:
                quantized(torch.from_numpy((public-127.5)/128.))
                quantizer.export_xmodel(output_dir=str(output), deploy_check=False)
            report['limited_fp32_quantized_metrics'] = metrics
    name = 'report-hardware-reference.json' if args.hardware_reference else 'report-'+args.mode+'.json'
    (output/name).write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
