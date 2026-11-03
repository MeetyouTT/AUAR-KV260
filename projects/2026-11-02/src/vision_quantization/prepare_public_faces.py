"""Prepare private, identity-disjoint LFW calibration and official pair splits."""
import hashlib
import json
from pathlib import Path
import time
import cv2
import numpy as np
from board.vision.reference_faces import YuNetCompat, SFaceCompat


def read_pairs(path):
    lines = path.read_text().splitlines()
    expected = int(lines[0])
    pairs = []
    for line in lines[1:]:
        p = line.split()
        if len(p) == 3:
            a, i, j = p
            pairs.append(((a, int(i)), (a, int(j)), True))
        elif len(p) == 4:
            a, i, b, j = p
            pairs.append(((a, int(i)), (b, int(j)), False))
        else:
            raise ValueError('Unexpected public pair format')
    assert len(pairs) == 2 * expected
    assert sum(x[2] for x in pairs) == expected
    return pairs


def main():
    cv2.setNumThreads(2)
    root = Path('/data/lfw')
    out = Path('/work/public-faces')
    out.mkdir(parents=True, exist_ok=True)
    splits = {key: read_pairs(root / name) for key, name in (
        ('train', 'pairsDevTrain.txt'), ('test', 'pairsDevTest.txt'))}
    ids = {key: {pair[i][0] for pair in pairs for i in (0, 1)} for key, pairs in splits.items()}
    if ids['train'] & ids['test']:
        raise ValueError('Official train/test identities overlap')
    excluded = ids['train'] | ids['test']
    # Stable hash order avoids alphabetical identity selection. One face per ID.
    candidates = [p for p in (root / 'lfw_funneled').glob('*/*.jpg') if p.parent.name not in excluded]
    candidates.sort(key=lambda p: hashlib.sha256(str(p.relative_to(root)).encode()).digest())
    detector = YuNetCompat('/models/yunet_2022mar.onnx', score_threshold=.6)
    recognizer = SFaceCompat('/models/sface_2021dec.onnx')
    counters = {'multiple_faces': 0, 'missing_faces': 0, 'calibration_attempts': 0}

    def crop(path):
        image = cv2.imread(str(path))
        if image is None:
            raise ValueError('Unreadable public benchmark image')
        faces = detector.detect(image)
        if not len(faces):
            counters['missing_faces'] += 1
            return None
        if len(faces) > 1:
            counters['multiple_faces'] += 1
        # LFW images are centered face crops. Select the closest face center.
        centers = faces[:, :2] + faces[:, 2:4] / 2
        chosen = faces[np.argmin(((centers - np.array(image.shape[1::-1]) / 2) ** 2).sum(axis=1))]
        return SFaceCompat.align_crop(image, chosen)

    calibration = []
    selected_ids = set()
    for path in candidates:
        if path.parent.name in selected_ids:
            continue
        counters['calibration_attempts'] += 1
        value = crop(path)
        if value is not None:
            calibration.append(value)
            selected_ids.add(path.parent.name)
        if len(calibration) == 256:
            break
    if len(calibration) != 256 or selected_ids & excluded:
        raise ValueError('Insufficient independent calibration identities')
    np.save(str(out / 'calibration_bgr.npy'), np.stack(calibration))
    report = {'scope': 'PUBLIC_LFW_DEVELOPMENT_SPLITS_NOT_DEPLOYMENT_ACCEPTANCE',
              'detector_threshold': .6, 'face_selection': 'closest_to_image_center',
              'calibration_images': 256, 'calibration_identities': len(selected_ids),
              'calibration_eval_identity_overlap': 0, 'train_test_identity_overlap': 0,
              'splits': {}, 'images_redistributed': False}
    start = time.monotonic()
    for key, pairs in splits.items():
        images = sorted({x for p in pairs for x in p[:2]})
        crops, features, index = [], [], {}
        missing = 0
        for n, image_key in enumerate(images):
            identity, number = image_key
            path = root / 'lfw_funneled' / identity / ('%s_%04d.jpg' % (identity, number))
            value = crop(path)
            if value is None:
                missing += 1
                continue
            index[image_key] = len(crops)
            crops.append(value)
            features.append(recognizer.feature(value))
            if (n + 1) % 250 == 0:
                print(json.dumps({'split': key, 'processed': n + 1, 'total': len(images),
                                  'seconds': round(time.monotonic() - start, 1)}), flush=True)
        valid = [(index[a], index[b], same) for a, b, same in pairs if a in index and b in index]
        array = np.asarray(valid, dtype=np.int32)
        np.save(str(out / (key + '_bgr.npy')), np.stack(crops))
        np.save(str(out / (key + '_fp32.npy')), np.stack(features))
        np.save(str(out / (key + '_pairs.npy')), array)
        report['splits'][key] = {'pairs_total': len(pairs), 'pairs_evaluable': len(valid),
                                'positive_evaluable': int(array[:, 2].sum()),
                                'negative_evaluable': int((array[:, 2] == 0).sum()),
                                'images_total': len(images), 'images_missing_detection': missing,
                                'images_evaluable': len(crops), 'identities': len(ids[key])}
    report['preparation_counters'] = counters
    (out / 'dataset-report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
