# Input-size extension: https://github.com/opencv/opencv/blob/4.6.0/modules/objdetect/src/face_detect.cpp
"""Pinned YuNet 2022mar / SFace 2021dec CPU backend for OpenCV 4.5.2.

Postprocessing follows OpenCV 4.6.0 objdetect (Apache-2.0), including its
legacy asymmetric box variance. This is a software reference, not a DPU model.
Instances own mutable DNN state and must be used by one inference worker.
"""
from pathlib import Path
import hashlib
import cv2
import numpy as np

YUNET_SHA256 = '50ef07f702a31741ca46a4c0d947773b64143b9362780237bf0d427d6c79bab7'
SFACE_SHA256 = '0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79'

def checked_net(path, expected):
    path = Path(path)
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    if h.hexdigest() != expected:
        raise ValueError('Model hash mismatch: ' + str(path))
    net = cv2.dnn.readNetFromONNX(str(path))
    net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
    net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
    return net

def bgr_image(image):
    if not isinstance(image, np.ndarray) or image.dtype != np.uint8 or image.ndim != 3 or image.shape[2] != 3 or not image.size:
        raise ValueError('Expected a nonempty uint8 BGR image')

class YuNetCompat:
    def __init__(self, model, score_threshold=0.9, nms_threshold=0.3, top_k=5000, input_size=320):
        if not 0 <= score_threshold <= 1 or not 0 < nms_threshold <= 1 or top_k < 1:
            raise ValueError('Invalid detector thresholds')
        if type(input_size) is not int or input_size not in (128,192,256,320):
            raise ValueError("Expected validated input size divisible by 64")
        self.net = checked_net(model, YUNET_SHA256)
        self.score_threshold, self.nms_threshold, self.top_k = score_threshold, nms_threshold, top_k
        self.size = input_size
        priors = []
        # OpenCV 4.6.0 generatePriors; supported sizes have exact /8,/16,/32,/64 grids.
        for step, sizes in [(8,[10,16,24]), (16,[32,48]), (32,[64,96]), (64,[128,192,256])]:
            cells = self.size // step
            for y in range(cells):
                for x in range(cells):
                    for s in sizes:
                        priors.append([(x + .5) * step / self.size, (y + .5) * step / self.size, s / self.size, s / self.size])
        self.priors = np.asarray(priors, dtype=np.float32)

    def detect(self, image):
        bgr_image(image)
        h, w = image.shape[:2]
        resized = cv2.resize(image, (self.size, self.size), interpolation=cv2.INTER_LINEAR)
        self.net.setInput(cv2.dnn.blobFromImage(resized))
        loc, conf, iou = self.net.forward(['loc', 'conf', 'iou'])
        loc, conf, iou = loc.reshape(-1,14), conf.reshape(-1,2), iou.reshape(-1)
        if not (len(loc) == len(conf) == len(iou) == len(self.priors)):
            raise RuntimeError('Unexpected legacy YuNet output layout')
        score = np.sqrt(conf[:,1] * np.clip(iou,0,1))
        good = np.isfinite(score) & (score > self.score_threshold) & np.isfinite(loc).all(axis=1)
        p, l, s = self.priors[good], loc[good], score[good]
        if not len(p):
            return np.empty((0,15), dtype=np.float32)
        center = (p[:,:2] + l[:,:2] * np.float32(.1) * p[:,2:]) * self.size
        size = p[:,2:] * np.exp(l[:,2:4] * np.array([.1,.2],np.float32)) * self.size
        xy = center - size / 2
        landmarks = (p[:,None,:2] + l[:,4:].reshape(-1,5,2) * np.float32(.1) * p[:,None,2:]) * self.size
        faces = np.concatenate((xy,size,landmarks.reshape(-1,10),s[:,None]),axis=1).astype(np.float32)
        boxes = faces[:,:4].astype(np.int32).tolist()
        keep = cv2.dnn.NMSBoxes(boxes,s.tolist(),self.score_threshold,self.nms_threshold,eta=1.,top_k=self.top_k)
        keep = np.asarray(keep,dtype=np.int32).reshape(-1)
        faces = faces[keep].copy()
        faces[:,[0,2,4,6,8,10,12]] *= w / self.size
        faces[:,[1,3,5,7,9,11,13]] *= h / self.size
        return faces

class SFaceCompat:
    def __init__(self, model):
        self.net = checked_net(model, SFACE_SHA256)

    @staticmethod
    def align_crop(image, face):
        bgr_image(image)
        face = np.asarray(face,dtype=np.float32).reshape(-1)
        if len(face) != 15 or not np.isfinite(face).all():
            raise ValueError('Expected one finite YuNet face row with five landmarks')
        src = face[4:14].reshape(5,2)
        dst = np.array([[38.2946,51.6963],[73.5318,51.5014],[56.0252,71.7366],[41.5493,92.3655],[70.7299,92.2041]],np.float32)
        src_mean = src.mean(axis=0)
        dst_mean = np.array([56.0262,71.9008],np.float32)
        src_d, dst_d = src - src_mean, dst - dst_mean
        # Use float32 products as the C++ implementation does, then double SVD.
        a = (dst_d[:,:,None] * src_d[:,None,:]).sum(axis=0,dtype=np.float64) / 5
        u,s,vt = np.linalg.svd(a)
        d = np.array([1., -1. if np.linalg.det(a) < 0 else 1.])
        if s[1] <= s[0] * 2 * np.finfo(np.float32).tiny:
            d[1] = 1. if np.linalg.det(u) * np.linalg.det(vt) > 0 else -1.
        variance = (src_d * src_d).sum(dtype=np.float64) / 5
        if variance <= 1e-10:
            raise ValueError('Degenerate face landmarks')
        scale = np.dot(s,d) / variance
        rotation = u @ np.diag(d) @ vt
        matrix = np.column_stack((scale * rotation, dst_mean - scale * (rotation @ src_mean)))
        return cv2.warpAffine(image,matrix,(112,112),flags=cv2.INTER_LINEAR)

    def feature(self, crop):
        bgr_image(crop)
        if crop.shape[:2] != (112,112):
            raise ValueError('Expected an aligned 112x112 crop')
        self.net.setInput(cv2.dnn.blobFromImage(crop,1.,(112,112),(0,0,0),True,False))
        feature = self.net.forward().reshape(-1).astype(np.float32)
        if feature.shape != (128,) or not np.isfinite(feature).all() or np.linalg.norm(feature) <= 1e-8:
            raise RuntimeError('Invalid SFace embedding')
        return feature

    @staticmethod
    def match(feature1, feature2):
        a,b = np.asarray(feature1,dtype=np.float64).reshape(-1),np.asarray(feature2,dtype=np.float64).reshape(-1)
        if a.shape != (128,) or b.shape != (128,) or not np.isfinite(a).all() or not np.isfinite(b).all():
            raise ValueError('Expected two finite 128-dimensional embeddings')
        den = np.linalg.norm(a) * np.linalg.norm(b)
        if den <= 1e-12:
            raise ValueError('Zero embedding')
        return float(np.dot(a,b) / den)
