"""Pinned Vitis AI 3.0 YOLOX-Nano person detector for the current KV260 DPU.

The native call releases Python's GIL. The service supplies its latest BGR
frame; this module never opens a camera or changes the FPGA configuration.
"""
import ctypes
import fcntl
import hashlib
import json
import math
from pathlib import Path
import subprocess
import threading

from common.contracts import Detection


def checked_file(path, expected):
    path = Path(path)
    if not isinstance(expected, str) or len(expected) != 64:
        raise ValueError('A SHA256 is required for every model component')
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise RuntimeError('YOLO component hash mismatch: ' + str(path))
    return path.resolve()


def verify_architecture(model, expected):
    import xir
    graph = xir.Graph.deserialize(str(model))
    subgraphs = [s for s in graph.get_root_subgraph().toposort_child_subgraph()
                 if s.has_attr('device') and s.get_attr('device') == 'DPU']
    if len(subgraphs) != 1:
        raise RuntimeError('Expected exactly one YOLO DPU subgraph')
    subgraph = subgraphs[0]
    fingerprint = hex(int(subgraph.get_attr('dpu_fingerprint')))
    if fingerprint != expected or subgraph.get_attr('dpu_name') != 'DPUCZDX8G_ISA1_B4096':
        raise RuntimeError('YOLO model architecture mismatch')
    inputs, outputs = list(subgraph.get_input_tensors()), list(subgraph.get_output_tensors())
    if (len(inputs) != 1 or list(inputs[0].dims) != [1, 416, 416, 3]
            or inputs[0].get_attr('fix_point') != -2
            or sorted(tuple(t.dims) for t in outputs) != [(1, 13, 13, 85), (1, 26, 26, 85), (1, 52, 52, 85)]
            or any(str(t.dtype) != 'xint8' for t in inputs + outputs)):
        raise RuntimeError('Unexpected YOLOX-Nano tensor layout')
    response = subprocess.run(['xdputil', 'query'], stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, text=True, timeout=15, check=True)
    kernels = json.loads(response.stdout).get('kernels', [])
    if len(kernels) != 1 or kernels[0].get('fingerprint') != expected:
        raise RuntimeError('Live DPU fingerprint does not match the YOLO model')
    return fingerprint


def original_person_boxes(rows, width, height, threshold=.3, nms_iou=.45):
    """Validate, clip and bound the native original-image xyxy results."""
    detections = []
    for row in rows:
        if len(row) != 6 or not all(math.isfinite(float(v)) for v in row):
            raise RuntimeError('Non-finite or malformed native YOLO result')
        x1, y1, x2, y2, score, label = map(float, row)
        if label != 0 or not 0 <= score <= 1:
            raise RuntimeError('Unexpected native YOLO class or score')
        if score < threshold:
            continue
        x1, y1 = max(0., min(width, x1)), max(0., min(height, y1))
        x2, y2 = max(0., min(width, x2)), max(0., min(height, y2))
        if x2 > x1 and y2 > y1:
            detections.append(Detection((x1, y1, x2 - x1, y2 - y1), score, 'person'))
    # The supplied 0.65 NMS can retain nested boxes on a single person. Use an
    # explicit, stricter person-only NMS for the UI count and association.
    retained = []
    for candidate in sorted(detections, key=lambda d: d.score, reverse=True):
        x, y, w, h = candidate.box
        duplicate = False
        for previous in retained:
            px, py, pw, ph = previous.box
            overlap = max(0., min(x+w, px+pw)-max(x, px)) * max(0., min(y+h, py+ph)-max(y, py))
            if overlap / max(w*h+pw*ph-overlap, 1e-9) > nms_iou:
                duplicate = True
                break
        if not duplicate:
            retained.append(candidate)
            if len(retained) == 16:break
    return retained


class DpuYoloX:
    backend_kind = 'DPU'
    kind = 'DPU_YOLOX_NANO_PERSON'

    def __init__(self, config):
        self.config = dict(config)
        self.handle = None
        self.ownership = None
        self.lock = threading.Lock()
        model = checked_file(config['model'], config['model_sha256'])
        checked_file(model.with_suffix('.prototxt'), config['model_config_sha256'])
        library = checked_file(config['native_library'], config['native_sha256'])
        if (config.get('classes') != ['person'] or config.get('score_threshold') not in (.1, .3)
                or config.get('person_nms_iou', .45) != .45):
            raise ValueError('Only reviewed person detection/tracking thresholds are supported')
        self.fingerprint = verify_architecture(model, config['arch_fingerprint'])
        # Also coordinate the project's generic DPU adapter and UI adapter.
        self.ownership = Path('/run/aura-person-dpu.lock').open('a+')
        try:
            fcntl.flock(self.ownership, fcntl.LOCK_EX | fcntl.LOCK_NB)
            native = ctypes.CDLL(str(library))
            native.aura_yolox_abi.restype = ctypes.c_int
            if native.aura_yolox_abi() != 1:
                raise RuntimeError('YOLO native ABI mismatch')
            native.aura_yolox_error.restype = ctypes.c_char_p
            native.aura_yolox_create.argtypes = [ctypes.c_char_p]
            native.aura_yolox_create.restype = ctypes.c_void_p
            native.aura_yolox_destroy.argtypes = [ctypes.c_void_p]
            native.aura_yolox_destroy.restype = None
            native.aura_yolox_detect.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_float),
                ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
            native.aura_yolox_detect.restype = ctypes.c_int
            self.native = native
            self.handle = native.aura_yolox_create(str(model).encode())
            if not self.handle:
                raise RuntimeError(self._error())
        except BaseException:
            self.close()
            raise

    def _error(self):
        return (self.native.aura_yolox_error() or b'Native YOLO failure').decode(errors='replace')

    def verify_runtime(self):
        return self.fingerprint

    def detect_bgr(self, image):
        import numpy as np
        if image.dtype != np.uint8 or image.ndim != 3 or image.shape[2] != 3:
            raise ValueError('YOLO expects uint8 BGR image data')
        height, width = image.shape[:2]
        if not 0 < width <= 4096 or not 0 < height <= 4096:
            raise ValueError('YOLO image size out of range')
        image = np.ascontiguousarray(image)
        output = (ctypes.c_float * (16 * 6))()
        count = ctypes.c_int()
        with self.lock:
            if not self.handle:
                raise RuntimeError('YOLO detector is closed')
            status = self.native.aura_yolox_detect(self.handle, image.ctypes.data,
                width, height, image.strides[0], output, 16, 0, ctypes.byref(count))
            if status != 0:
                raise RuntimeError(self._error())
            if not 0 <= count.value <= 16:
                raise RuntimeError('Native YOLO output exceeds capacity')
        rows = [list(output[i * 6:i * 6 + 6]) for i in range(count.value)]
        return original_person_boxes(rows, width, height, self.config['score_threshold'], self.config.get('person_nms_iou', .45))

    def detect(self, frame):
        if frame.ref.timestamp_semantics == 'synthetic':
            raise ValueError('DPU adapter requires a real captured frame')
        return self.detect_bgr(frame.image)

    def close(self):
        with self.lock:
            if self.handle:
                self.native.aura_yolox_destroy(self.handle)
                self.handle = None
            if self.ownership:
                self.ownership.close()
                self.ownership = None


def create(config):
    return DpuYoloX(config)
