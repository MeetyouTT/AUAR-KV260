"""Multi-identity SFace PTQ with held-out public pair evaluation, no live data."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import numpy as np
import torch
from pytorch_nndct.apis import torch_quantizer
from reconstruct_sface import reconstruct
from rewrite_sface_v2 import rewrite


def inputs(crops):
    # Match the board's existing quantization rounding exactly before PTQ test.
    rgb = crops[:, :, :, ::-1].transpose(0, 3, 1, 2).astype(np.float32)
    normalized = (rgb - 127.5) / 128.
    return np.clip(np.floor(normalized * 128. + .5), -128, 127) / 128.


def scores(features, pairs):
    norms = np.linalg.norm(features, axis=1, keepdims=True)
    if not np.isfinite(features).all() or (norms <= 1e-8).any():
        raise ValueError('Invalid embedding in benchmark')
    values = features.astype(np.float64) / norms
    return (values[pairs[:, 0]] * values[pairs[:, 1]]).sum(axis=1)


def statistics(values, labels, threshold):
    positive, negative = labels == 1, labels == 0
    accepted = values >= threshold
    return {'threshold': float(threshold), 'accuracy': float((accepted == labels).mean()),
            'balanced_accuracy': float((accepted[positive].mean() + (~accepted[negative]).mean()) / 2),
            'true_accept_rate': float(accepted[positive].mean()),
            'false_accept_rate': float(accepted[negative].mean()),
            'false_accepts': int(accepted[negative].sum()), 'negative_pairs': int(negative.sum()),
            'false_rejects': int((~accepted[positive]).sum()), 'positive_pairs': int(positive.sum())}


def learn_threshold(values, labels, far=None):
    candidates = np.r_[np.nextafter(values.min(), -np.inf), np.unique(values),
                       np.nextafter(values.max(), np.inf)]
    best, chosen = -1., None
    for threshold in candidates:
        result = statistics(values, labels, threshold)
        value = result['balanced_accuracy'] if far is None else result['true_accept_rate']
        if (far is None or result['false_accept_rate'] <= far) and value >= best:
            best, chosen = value, float(threshold)
    if chosen is None:
        raise ValueError('Threshold estimation failed')
    return chosen


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode', choices=['calib', 'test'], required=True)
    p.add_argument('--output', default='/work/sface-public-int8')
    args = p.parse_args()
    torch.set_num_threads(2)
    data = Path('/work/public-faces')
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    core, _ = reconstruct(Path('/models/sface_2021dec.onnx'), core_only=True)
    model, counts = rewrite(core)
    calibration = np.load(str(data / 'calibration_bgr.npy'), allow_pickle=False)
    seed = inputs(calibration[:1]).copy()
    # Reconstruction parity must be checked on real independent aligned faces.
    parity = []
    if args.mode == 'calib':
        raw = np.load(str(data / 'test_bgr.npy'), mmap_mode='r')
        reference = np.load(str(data / 'test_fp32.npy'), allow_pickle=False)
        with torch.no_grad():
            for index in np.linspace(0, len(raw) - 1, 16, dtype=int):
                source = raw[index:index+1, :, :, ::-1].transpose(0, 3, 1, 2).astype(np.float32)
                actual = model(torch.from_numpy((source - 127.5) / 128.)).numpy().reshape(128)
                cosine = float(np.dot(actual, reference[index]) / (np.linalg.norm(actual) * np.linalg.norm(reference[index])))
                error = float(np.max(np.abs(actual - reference[index])))
                if cosine < .99999 or error > .01:
                    raise ValueError('SFace real-face FP32 parity failed')
                parity.append({'cosine': cosine, 'max_absolute_error': error})
    quantizer = torch_quantizer(args.mode, model, (torch.from_numpy(seed),),
        output_dir=str(out), device=torch.device('cpu'), bitwidth=8)
    quantized = quantizer.quant_model.eval()
    started = time.monotonic()
    with torch.no_grad():
        if args.mode == 'calib':
            for i in range(len(calibration)):
                quantized(torch.from_numpy(inputs(calibration[i:i+1]).copy()))
                if (i + 1) % 32 == 0:
                    print(json.dumps({'calibration_completed': i + 1, 'seconds': round(time.monotonic() - started, 1)}), flush=True)
            quantizer.export_quant_config()
            report = {'calibration_samples': len(calibration), 'identities': len(calibration),
                      'fp32_real_face_parity': parity, 'rewrites': counts,
                      'calibration_sha256': hashlib.sha256((data / 'calibration_bgr.npy').read_bytes()).hexdigest()}
            (out / 'calibration-report.json').write_text(json.dumps(report, indent=2) + '\n')
        else:
            all_features = {}
            for key in ('train', 'test'):
                raw = np.load(str(data / (key + '_bgr.npy')), mmap_mode='r')
                values = []
                for i in range(0, len(raw), 8):
                    result = quantized(torch.from_numpy(inputs(raw[i:i+8]).copy())).numpy().reshape(-1, 128)
                    values.append(result.copy())
                    if i % 256 == 0:
                        print(json.dumps({'split': key, 'quantized_images': min(i + 8, len(raw)),
                                          'seconds': round(time.monotonic() - started, 1)}), flush=True)
                features = np.concatenate(values)
                np.save(str(data / (key + '_int8_simulation.npy')), features)
                all_features[key] = features
            report = {'scope': 'PUBLIC_LFW_HELD_OUT_PTQ_SIMULATION_NOT_BOARD_OR_FIELD_ACCEPTANCE',
                      'dataset': json.loads((data / 'dataset-report.json').read_text()), 'models': {}}
            for label, suffix in (('fp32', 'fp32'), ('int8_simulation', 'int8_simulation')):
                train_pairs = np.load(str(data / 'train_pairs.npy'))
                test_pairs = np.load(str(data / 'test_pairs.npy'))
                train = scores(np.load(str(data / ('train_' + suffix + '.npy'))), train_pairs)
                test = scores(np.load(str(data / ('test_' + suffix + '.npy'))), test_pairs)
                optimal = learn_threshold(train, train_pairs[:, 2])
                strict = learn_threshold(train, train_pairs[:, 2], far=.01)
                report['models'][label] = {
                    'train_selected_balanced_accuracy': statistics(train, train_pairs[:, 2], optimal),
                    'held_out_at_train_selected_threshold': statistics(test, test_pairs[:, 2], optimal),
                    'held_out_at_train_far_1pct_threshold': statistics(test, test_pairs[:, 2], strict)}
            a = all_features['test'].astype(np.float64)
            b = np.load(str(data / 'test_fp32.npy')).astype(np.float64)
            cosine = (a * b).sum(axis=1) / (np.linalg.norm(a, axis=1) * np.linalg.norm(b, axis=1))
            report['same_image_fp32_int8_cosine'] = {key: float(np.percentile(cosine, q))
                for key, q in (('minimum', 0), ('p05', 5), ('median', 50), ('p95', 95))}
            fp = report['models']['fp32']['held_out_at_train_selected_threshold']['balanced_accuracy']
            iq = report['models']['int8_simulation']['held_out_at_train_selected_threshold']['balanced_accuracy']
            report['engineering_quality_gate'] = {
                'criteria': 'balanced accuracy loss <= 0.02; median feature cosine >= 0.95; p05 >= 0.85',
                'passed': bool(fp - iq <= .02 and np.median(cosine) >= .95 and np.percentile(cosine, 5) >= .85),
                'balanced_accuracy_loss': float(fp - iq), 'field_identity_acceptance': False}
            # NNDCT keeps batch-shape history from simulation. Export in the
            # fresh batch-one process that is also checked by the compiler.
            report['deployment_export'] = 'export_sface_batch_one.py in a fresh process'
            (out / 'evaluation-report.json').write_text(json.dumps(report, indent=2) + '\n')
            print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
