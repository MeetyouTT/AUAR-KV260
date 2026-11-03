"""Small parity fixtures from existing CPU model; not a quantization dataset."""
from pathlib import Path
import sys
import numpy as np
import cv2

ROOT = Path('/home/ghmd/Win共享文件/共享文件夹/aura')
sys.path.insert(0, str(ROOT))
from board.vision.reference_faces import YuNetCompat, SFaceCompat

cv2.setNumThreads(2)
detector = YuNetCompat(ROOT/'models/vision/yunet_2022mar.onnx')
embedder = SFaceCompat(ROOT/'models/vision/sface_2021dec.onnx')
image = cv2.imread('/home/ghmd/kv260-adaptation-check-20261006/identity/reference/lena.jpg')
face = detector.detect(image)[0]
crop = embedder.align_crop(image, face)
rng = np.random.RandomState(20261018)
samples = {'black': np.zeros((112, 112, 3), np.uint8),
           'gray': np.full((112, 112, 3), 127, np.uint8),
           'random': rng.randint(0, 256, (112, 112, 3)).astype(np.uint8), 'public_reference': crop}
output = {'names': np.array(list(samples))}
for name, value in samples.items():
    output['input_'+name] = cv2.dnn.blobFromImage(value, 1., (112, 112), (0, 0, 0), True, False)
    output['output_'+name] = embedder.feature(value)
np.savez(Path(__file__).with_name('reference-parity.npz'), **output)
print('Exported four isolated parity inputs/outputs; not calibration or identity accuracy data')
