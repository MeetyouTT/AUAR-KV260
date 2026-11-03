"""Calibrate the exact YuNet CNN; measure held-out FP32 detection agreement."""
import argparse
import hashlib
import json
from pathlib import Path
import cv2
import numpy as np
import torch
from pytorch_nndct.apis import torch_quantizer
from board.vision.reference_faces import YuNetCompat
from prepare_public_faces import read_pairs
from reconstruct_yunet import reconstruct, cpu_outputs


def image_paths():
    root = Path('/data/lfw')
    train = read_pairs(root / 'pairsDevTrain.txt')
    test = read_pairs(root / 'pairsDevTest.txt')
    excluded = {p[i][0] for p in train + test for i in (0, 1)}
    calibration = [p for p in (root / 'lfw_funneled').glob('*/*.jpg') if p.parent.name not in excluded]
    calibration.sort(key=lambda p: hashlib.sha256(str(p.relative_to(root)).encode()).digest())
    selected, identities = [], set()
    for path in calibration:
        if path.parent.name in identities:
            continue
        selected.append(path)
        identities.add(path.parent.name)
        if len(selected) == 256:
            break
    eval_images = sorted({p[i] for p in test for i in (0, 1)})
    rng = np.random.RandomState(260)
    indices = rng.choice(len(eval_images), 256, replace=False)
    evaluation = [root / 'lfw_funneled' / eval_images[i][0] /
                  ('%s_%04d.jpg' % eval_images[i]) for i in indices]
    assert not identities & {p.parent.name for p in evaluation}
    return selected, evaluation


def blob(image):
    raw = cv2.dnn.blobFromImage(cv2.resize(image, (320, 320)))
    return torch.from_numpy(raw / 256.)


class QuantizedNet:
    def __init__(self, model):
        self.model = model

    def setInput(self, raw):
        self.raw = raw

    def forward(self, names):
        assert names == ['loc', 'conf', 'iou']
        with torch.no_grad():
            heads = [h.numpy() for h in self.model(torch.from_numpy(self.raw / 256.))]
        return cpu_outputs(heads)


def box_iou(a, b):
    lower = np.maximum(a[:2], b[:2])
    upper = np.minimum(a[:2] + a[2:4], b[:2] + b[2:4])
    area = np.maximum(upper - lower, 0).prod()
    return float(area / max(a[2:4].prod() + b[2:4].prod() - area, 1e-8))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['calib', 'test'], required=True)
    args = parser.parse_args()
    torch.set_num_threads(2)
    cv2.setNumThreads(2)
    calibration, evaluation = image_paths()
    out = Path('/work/yunet-public-int8')
    out.mkdir(parents=True, exist_ok=True)
    model = reconstruct('/models/yunet_2022mar.onnx')
    seed = blob(cv2.imread(str(calibration[0])))
    quantizer = torch_quantizer(args.mode, model, (seed,), output_dir=str(out),
                                device=torch.device('cpu'), bitwidth=8)
    quantized = quantizer.quant_model.eval()
    with torch.no_grad():
        if args.mode == 'calib':
            for i, path in enumerate(calibration):
                quantized(blob(cv2.imread(str(path))))
                if (i + 1) % 32 == 0:
                    print(json.dumps({'yunet_calibration_images': i + 1}), flush=True)
            quantizer.export_quant_config()
            report = {'scope': 'PUBLIC_FACE_CROP_ENGINEERING_CALIBRATION', 'images': len(calibration),
                      'identities': len(calibration), 'eval_identity_overlap': 0,
                      'limitations': 'LFW lacks full-scene camera backgrounds; deployment recalibration remains required'}
            (out / 'calibration-report.json').write_text(json.dumps(report, indent=2) + '\n')
        else:
            records = {}
            for threshold in (.6, .9):
                reference = YuNetCompat('/models/yunet_2022mar.onnx', score_threshold=threshold)
                actual = YuNetCompat('/models/yunet_2022mar.onnx', score_threshold=threshold)
                actual.net = QuantizedNet(quantized)
                counts = {'reference_faces': 0, 'int8_faces': 0, 'matched_iou_ge_05': 0,
                          'same_face_count_images': 0, 'images': len(evaluation)}
                ious, landmark_errors, score_errors = [], [], []
                for path in evaluation:
                    image = cv2.imread(str(path))
                    a, b = reference.detect(image), actual.detect(image)
                    counts['reference_faces'] += len(a)
                    counts['int8_faces'] += len(b)
                    counts['same_face_count_images'] += int(len(a) == len(b))
                    available = set(range(len(b)))
                    for face in a:
                        if not available:
                            continue
                        index = max(available, key=lambda j: box_iou(face, b[j]))
                        iou = box_iou(face, b[index])
                        if iou < .5:
                            continue
                        available.remove(index)
                        counts['matched_iou_ge_05'] += 1
                        ious.append(iou)
                        landmark_errors.append(float(np.linalg.norm(face[4:14].reshape(5, 2) - b[index, 4:14].reshape(5, 2), axis=1).mean()))
                        score_errors.append(float(abs(face[14] - b[index, 14])))
                records[str(threshold)] = {'counts': counts,
                    'reference_face_recovery': counts['matched_iou_ge_05'] / max(counts['reference_faces'], 1),
                    'matched_box_iou_median': float(np.median(ious)) if ious else None,
                    'landmark_error_pixels_median': float(np.median(landmark_errors)) if ious else None,
                    'score_absolute_error_median': float(np.median(score_errors)) if ious else None}
            quantized(seed)
            quantizer.export_xmodel(output_dir=str(out), deploy_check=False)
            report = {'scope': 'HELD_OUT_PUBLIC_FP32_INT8_AGREEMENT_NOT_GROUND_TRUTH_AP',
                      'identity_disjoint_calibration_evaluation': True, 'thresholds': records,
                      'field_acceptance': False}
            (out / 'evaluation-report.json').write_text(json.dumps(report, indent=2) + '\n')
            print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
