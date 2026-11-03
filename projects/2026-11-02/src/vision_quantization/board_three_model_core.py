"""Fixed public inputs for calibrated SFace and same-owner three-model switching."""
import ctypes
import faulthandler
import fcntl
import hashlib
import json
from pathlib import Path
import sys
import time
from types import SimpleNamespace
import cv2
import numpy as np

faulthandler.enable()
root, config_path, runtime = map(Path, sys.argv[1:4])
sys.path[:0] = [str(root), str(runtime)]
from dpu_vision_runtime import PinnedRunner, encode, sface_feature
from board.vision.reference_faces import SFaceCompat

cv2.setNumThreads(2)
config = json.loads(config_path.read_text())
identity = json.loads(Path(config['identity']['config']).read_text())
lock = Path('/run/aura-person-dpu.lock').open('a+')
fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
owner = SimpleNamespace(fingerprint='0x101000056010407', ownership=lock)
sface = PinnedRunner(root / 'sface_public_int8.xmodel', root / 'sface-manifest.json', owner)
yunet_root = Path('/home/root/aura-dpu-vision-20261021/staging/3f10273827d88501/kit-974f2fb1a5641f10')
yunet = PinnedRunner(yunet_root / 'yunet_public_int8.xmodel', yunet_root / 'manifest.json', owner)
vectors = np.load(str(root / 'sface-vectors.npz'), allow_pickle=False)
agreement, similarities, dpu_times = [], [], []
reference = SFaceCompat(identity['embedding_model'])
for i, image in enumerate(vectors['images_bgr']):
    actual = sface_feature(image, sface)
    expected = vectors['sample_%d_%s' % (i, sface.outputs[0].name)].reshape(128)
    integers = np.rint(actual * (2. ** sface.outputs[0].get_attr('fix_point'))).astype(np.int16)
    diff = np.abs(integers - expected.astype(np.int16))
    original = reference.feature(image).astype(np.float64)
    similarities.append(float(np.dot(actual, original) / (np.linalg.norm(actual) * np.linalg.norm(original))))
    agreement.append({'sample': i, 'maximum_integer_difference': int(diff.max()),
                      'different_elements': int(np.count_nonzero(diff)), 'submit_wait_ms': sface.last_ms})


def summary(values):
    a = np.asarray(values)
    return {'samples': len(a), 'median_ms': float(np.median(a)),
            'p95_ms': float(np.percentile(a, 95)), 'maximum_ms': float(a.max())}


latencies = {}
for label in ('arm_cpu_fp32', 'dpu_int8_with_input_output_conversion'):
    elapsed = []
    for i in range(8):
        image = vectors['images_bgr'][i % 4]
        before = time.monotonic()
        if label == 'arm_cpu_fp32':
            reference.feature(image)
        else:
            sface_feature(image, sface)
            dpu_times.append(sface.last_ms)
        elapsed.append((time.monotonic() - before) * 1000.)
    latencies[label] = summary(elapsed)

yolo = config['yolo']
for key, sha_key in [('model', 'model_sha256'), ('native_library', 'native_sha256'), ('reference_image', 'reference_sha256')]:
    assert hashlib.sha256(Path(yolo[key]).read_bytes()).hexdigest() == yolo[sha_key]
native = ctypes.CDLL(yolo['native_library'])
native.aura_yolox_create.argtypes = [ctypes.c_char_p]
native.aura_yolox_create.restype = ctypes.c_void_p
native.aura_yolox_error.restype = ctypes.c_char_p
native.aura_yolox_detect.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int,
    ctypes.c_int, ctypes.c_int, ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
native.aura_yolox_detect.restype = ctypes.c_int
native.aura_yolox_destroy.argtypes = [ctypes.c_void_p]
handle = native.aura_yolox_create(yolo['model'].encode())
assert handle, native.aura_yolox_error()
person = np.ascontiguousarray(cv2.imread(yolo['reference_image']))
h, w = person.shape[:2]
boxes = np.zeros((32, 6), np.float32)
yunet_vectors = np.load(str(yunet_root / 'vectors.npz'), allow_pickle=False)
face_input = encode(yunet_vectors['images_bgr'][0].astype(np.float32)[None] / 256., yunet.input_fix)
identity_input = encode((vectors['images_bgr'][0][:, :, ::-1].astype(np.float32)[None] - 127.5) / 128., sface.input_fix)
mixed = []
try:
    for label, slots, faces_enabled, identity_enabled in (
        ('yolo_only', 20, False, False), ('yolo_yunet', 40, True, False), ('yolo_yunet_sface', 40, True, True)):
        start = time.monotonic()
        primary, faces, features, overruns = [], [], [], 0
        for i in range(slots):
            deadline = start + i * .1
            time.sleep(max(0, deadline - time.monotonic()))
            count = ctypes.c_int()
            before = time.monotonic()
            status = native.aura_yolox_detect(handle, person.ctypes.data, w, h, person.strides[0],
                boxes.ctypes.data, 32, 0, ctypes.byref(count))
            assert status == 0 and count.value > 0, native.aura_yolox_error()
            primary.append((time.monotonic() - before) * 1000.)
            if faces_enabled and i % 2 == 0:
                yunet.execute_encoded(face_input)
                faces.append(yunet.last_ms)
            if identity_enabled and i % 5 == 0:
                result = sface.execute_encoded(identity_input)
                expected = vectors['sample_0_' + sface.outputs[0].name]
                value = next(iter(result.values()))
                assert np.max(np.abs(np.rint(value * 32.) - expected)) <= 1
                features.append(sface.last_ms)
            overruns += int(time.monotonic() > deadline + .1)
        mixed.append({'mode': label, 'yolo': summary(primary),
            'yunet': summary(faces) if faces else None, 'sface': summary(features) if features else None,
            'yolo_calls': len(primary), 'yunet_calls': len(faces), 'sface_calls': len(features),
            'scheduled_hz': {'yolo': 10, 'yunet': 5 if faces_enabled else 0, 'sface': 2 if identity_enabled else 0},
            'period_overruns': overruns})
finally:
    native.aura_yolox_destroy(handle)
    sface.close()
    yunet.close()
    lock.close()

print(json.dumps({'scope': 'PUBLIC_FIXED_INPUT_BOARD_CHECK_AND_PREENCODED_THREE_MODEL_SWITCHING_NOT_LIVE_BUSINESS',
    'sface_model_sha256': hashlib.sha256((root / 'sface_public_int8.xmodel').read_bytes()).hexdigest(),
    'agreement': agreement, 'all_host_quantized_agreement': all(x['maximum_integer_difference'] <= 1 for x in agreement),
    'fp32_hardware_cosine_four_public_samples': similarities, 'latencies': latencies,
    'sface_submit_wait': summary(dpu_times), 'mixed': mixed,
    'identity_database_or_enrollment_changed': False}), flush=True)
