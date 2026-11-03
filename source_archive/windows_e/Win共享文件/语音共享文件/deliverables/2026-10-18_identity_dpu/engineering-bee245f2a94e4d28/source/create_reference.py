"""Create four private numeric fixtures from one supplied reference image."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import cv2
import numpy as np

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--aura', required=True, type=Path)
parser.add_argument('--image', required=True, type=Path)
parser.add_argument('--output', required=True, type=Path)
args = parser.parse_args()
output = args.output.resolve()
assert output.suffix == '.npz' and not output.exists(), 'Use a new private .npz output'
assert Path('/home/ghmd/Win共享文件') not in output.parents, 'Do not publish input/embedding fixtures in the shared tree'
sys.path.insert(0, str(args.aura.resolve()))
from board.vision.reference_faces import YuNetCompat, SFaceCompat

cv2.setNumThreads(2)
detector = YuNetCompat(args.aura/'models/vision/yunet_2022mar.onnx')
embedder = SFaceCompat(args.aura/'models/vision/sface_2021dec.onnx')
image = cv2.imread(str(args.image))
if image is None:
    raise ValueError('Cannot read reference image')
faces = detector.detect(image)
if len(faces) != 1:
    raise ValueError('Expected exactly one reference face')
crop = embedder.align_crop(image, faces[0])
rng = np.random.RandomState(20261018)
samples = {'black': np.zeros((112, 112, 3), np.uint8),
           'gray': np.full((112, 112, 3), 127, np.uint8),
           'random': rng.randint(0, 256, (112, 112, 3)).astype(np.uint8),
           'public_reference': crop}
values = {'names': np.array(list(samples))}
for name, value in samples.items():
    values['input_'+name] = cv2.dnn.blobFromImage(value, 1., (112, 112), (0, 0, 0), True, False)
    values['output_'+name] = embedder.feature(value)
output.parent.mkdir(parents=True, exist_ok=True)
with output.open('xb') as stream:
    np.savez(stream, **values)
output.chmod(0o600)
print(json.dumps({'scope': 'FOUR_NUMERIC_FIXTURES_NOT_REPRESENTATIVE_CALIBRATION_OR_IDENTITY_ACCURACY',
                  'cases': len(samples), 'sha256': hashlib.sha256(output.read_bytes()).hexdigest()}))
