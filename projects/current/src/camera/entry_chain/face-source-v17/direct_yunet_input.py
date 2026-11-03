"""Same native YuNet tensors and decode, without a float32 NCHW round trip.

Only the reviewed native fix7 detector instance is adapted. Its original
admission guard, runner, model, output transform and CPU fallback remain owned
by DpuYuNet. The decode below retains reference_faces.YuNetCompat operations
and their order (OpenCV 4.6 legacy YuNet postprocessing, Apache-2.0).
"""
import types
import cv2
import numpy as np
from fast_yunet_input import FastYuNetNetwork, eligible

_LUT = np.minimum((np.arange(256, dtype=np.uint16) + 1) >> 1, 127).astype(np.uint8)
_LUT.flags.writeable = False


def encode_bgr(image):
    if (not isinstance(image, np.ndarray) or image.dtype != np.uint8
            or image.shape != (320, 320, 3)):
        raise ValueError('Direct YuNet needs uint8 [320,320,3] BGR')
    # uint8 itself proves the finite integer 0..255 domain. The lookup is
    # exactly original /256 then round-half-up fix7, including saturated 255.
    return np.ascontiguousarray(cv2.LUT(image, _LUT).view(np.int8)[None])


class DirectBGRNetwork(FastYuNetNetwork):
    def setBGR(self, image):
        self.source = None
        self.source = self.measure('direct_bgr_encode', encode_bgr, image)


def _detect(detector, image, bgr_check, measure):
    bgr_check(image)
    h, w = image.shape[:2]
    resized = measure('compat_resize', cv2.resize, image, (detector.size, detector.size),
                      interpolation=cv2.INTER_LINEAR)
    detector.net.setBGR(resized)
    loc, conf, iou = detector.net.forward(['loc', 'conf', 'iou'])
    loc, conf, iou = loc.reshape(-1, 14), conf.reshape(-1, 2), iou.reshape(-1)
    if not (len(loc) == len(conf) == len(iou) == len(detector.priors)):
        raise RuntimeError('Unexpected legacy YuNet output layout')
    score = np.sqrt(conf[:, 1] * np.clip(iou, 0, 1))
    good = np.isfinite(score) & (score > detector.score_threshold) & np.isfinite(loc).all(axis=1)
    p, l, s = detector.priors[good], loc[good], score[good]
    if not len(p):
        return np.empty((0, 15), dtype=np.float32)
    center = (p[:, :2] + l[:, :2] * np.float32(.1) * p[:, 2:]) * detector.size
    size = p[:, 2:] * np.exp(l[:, 2:4] * np.array([.1, .2], np.float32)) * detector.size
    xy = center - size / 2
    landmarks = (p[:, None, :2] + l[:, 4:].reshape(-1, 5, 2)
                 * np.float32(.1) * p[:, None, 2:]) * detector.size
    faces = np.concatenate((xy, size, landmarks.reshape(-1, 10), s[:, None]), axis=1).astype(np.float32)
    boxes = faces[:, :4].astype(np.int32).tolist()
    keep = measure('compat_nms', cv2.dnn.NMSBoxes, boxes, s.tolist(), detector.score_threshold,
                   detector.nms_threshold, eta=1., top_k=detector.top_k)
    keep = np.asarray(keep, dtype=np.int32).reshape(-1)
    faces = faces[keep].copy()
    faces[:, [0, 2, 4, 6, 8, 10, 12]] *= w / detector.size
    faces[:, [1, 3, 5, 7, 9, 11, 13]] *= h / detector.size
    return faces


def install(adapter_type, output_transform, measure, detector_type, bgr_check):
    if not all(callable(x) for x in (output_transform, measure, detector_type, bgr_check)):
        raise ValueError('Original detector contract and stage measurement required')
    if getattr(adapter_type, '_aura_direct_yunet_input_v17', False):
        return
    original = adapter_type.__init__

    def initialize(self, *args, **kwargs):
        original(self, *args, **kwargs)
        detector = getattr(self, 'detector', None)
        if not eligible(self) or type(detector) is not detector_type or detector.size != 320:
            return
        detector.net = DirectBGRNetwork(self, output_transform, measure)

        def detect(instance, image):
            return measure('compat_detect', _detect, instance, image, bgr_check, measure)

        detector.detect = types.MethodType(detect, detector)

    adapter_type.__init__ = initialize
    adapter_type._aura_direct_yunet_input_v17 = True
