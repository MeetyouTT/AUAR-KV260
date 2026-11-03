"""Isolated native DPU tests using a pinned image; never open the camera."""
import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import statistics
import subprocess
import sys
import time
import urllib.request

root = Path(__file__).resolve().parent
sys.path.insert(0, '/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009/aura')
import cv2
import numpy as np
cv2.setNumThreads(2)

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def health():
    with urllib.request.urlopen('http://127.0.0.1:8790/health', timeout=3) as response:
        return json.load(response)

before = health()
library = root / 'libaura_yolox.so'
build = subprocess.run(['python3', '-B', str(root / 'build_yolox.py'), '--output', str(library)],
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=70)
assert build.returncode == 0, build.stdout
build_result = json.loads(build.stdout)
config = {'model': '/usr/share/vitis_ai_library/models/yolox_nano_pt/yolox_nano_pt.xmodel',
    'model_sha256': 'def64abdeeccbd020cb651913ba907464c1a1786e30ba7d4aa077b601388950a',
    'model_config_sha256': '371c5979ac0ec1558455e86459b498cbeaa50852c90b722c31712a84904db7bf',
    'native_library': str(library), 'native_sha256': sha(library),
    'arch_fingerprint': '0x101000056010407', 'classes': ['person'], 'score_threshold': .3}
spec = importlib.util.spec_from_file_location('isolated_yolo', str(root / 'yolo_dpu.py'))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
detector = module.DpuYoloX(config)
image = cv2.imread(str(root / 'bus-reference.jpg'))
assert image is not None
try:
    timings = []
    for index in range(24):
        start = time.monotonic()
        people = detector.detect_bgr(image)
        timings.append((time.monotonic() - start) * 1000)
        assert len(people) >= 2, ('Expected at least two people in the pinned bus image', people)
    blank = detector.detect_bgr(np.zeros((480, 640, 3), np.uint8))
    assert not blank, blank
    mirrored = detector.detect_bgr(cv2.flip(image, 1))
    assert len(mirrored) >= 2, mirrored
finally:
    detector.close()
after = health()
assert before['pid'] == after['pid'] and before['camera_epoch'] == after['camera_epoch']
assert after['capture_frames'] > before['capture_frames'] and after['preview_frames'] > before['preview_frames']

def encode(p):
    data = p.read_bytes()
    return {'bytes': len(data), 'sha256': sha(p), 'base64': base64.b64encode(data).decode()}

painted = image.copy()
for person in people:
    x, y, w, h = [round(v) for v in person.box]
    cv2.rectangle(painted, (x, y), (x + w, y + h), (40, 220, 60), 2)
    cv2.putText(painted, 'person %.2f' % person.score, (x, max(18, y - 5)), cv2.FONT_HERSHEY_SIMPLEX, .5, (40, 220, 60), 1)
cv2.imwrite(str(root / 'bus-detected.jpg'), painted)
result = {'status': 'PASS', 'input_kind': 'pinned_static_reference', 'camera_opened': False,
    'config': config, 'build': build_result, 'people': [{'box': d.box, 'score': d.score} for d in people],
    'blank_people': len(blank), 'mirrored_people': len(mirrored), 'inference_ms':
        {'samples': len(timings), 'median': statistics.median(timings[1:]), 'p95': sorted(timings[1:])[int(.95 * (len(timings)-2))], 'first': timings[0]},
    'camera_before': before, 'camera_after': after,
    'artifacts': {'libaura_yolox.so': encode(library), 'bus-detected.jpg': encode(root / 'bus-detected.jpg')}}
(root / 'probe-result.json').write_text(json.dumps({k: v for k, v in result.items() if k != 'artifacts'}, indent=2) + '\n')
print(json.dumps(result))
