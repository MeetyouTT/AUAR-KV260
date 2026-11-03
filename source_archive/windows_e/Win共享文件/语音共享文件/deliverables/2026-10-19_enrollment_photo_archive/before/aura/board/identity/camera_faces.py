"""YuNet/SFace CPU reference on the detector's SAME immutable source frame."""
import json
import math
import os
from pathlib import Path


def config_for(root, config_path):
    root = Path(root)
    path = Path(config_path)
    config = json.loads((path if path.is_absolute() else root/path).read_text(encoding='utf-8'))
    if config.get('schema_version') != 'aura-camera-identity-1':
        raise ValueError('Unknown camera identity configuration')
    if (type(config.get('input_size')) is not int or config['input_size'] not in (128, 192, 256, 320)
            or not 32 <= config['minimum_face_pixels'] <= 256
            or not 0 <= config['minimum_blur_variance'] <= 10000
            or not .5 <= config['minimum_face_score'] <= 1
            or not 0 <= config['threshold'] <= 1 or not 0 <= config['ambiguity_margin'] <= 1):
        raise ValueError('Invalid identity reference parameters')
    for key in ('face_model', 'embedding_model'):
        p = Path(config[key])
        config[key] = str(p if p.is_absolute() else root/p)
    if config.get('feature_backend') is not None:
        from board.identity.remote_features import RemoteFaceFeatures
        RemoteFaceFeatures(config['feature_backend'])
    config['database'] = str(Path(config['database']).expanduser())
    if not Path(config['database']).is_absolute():
        raise ValueError('Identity database must use an absolute device-local path')
    return config


def face_for_target(faces, tracks, key, *, minimum_score=.9, minimum_pixels=48):
    """Reject overlapping ownership/multiple faces instead of choosing nearest."""
    candidates = []
    selected = key['track_id'], key['track_generation']
    for face in faces:
        if len(face) != 15 or not all(math.isfinite(float(v)) for v in face):
            continue
        x, y, w, h = map(float, face[:4])
        if min(w, h) < minimum_pixels or face[14] < minimum_score:
            continue
        owners = []
        for t in tracks:
            if not t['visible']:
                continue
            tx, ty, tw, th = map(float, t['box'])
            intersection = max(0, min(x+w, tx+tw)-max(x, tx))*max(0, min(y+h, ty+th)-max(y, ty))
            if tw > 0 and th > 0 and tx <= x+w/2 <= tx+tw and ty <= y+h/2 <= ty+.65*th and intersection/(w*h) >= .9:
                owners.append((t['track_id'], t['generation']))
        if selected in owners:
            if len(owners) != 1:
                return None, '人脸对应多个人体，请分开站立后重试'
            candidates.append(face)
    if len(candidates) != 1:
        return None, '当前目标有多张人脸，请重新选择' if candidates else '未检测到合格人脸，请靠近并正对摄像头'
    return candidates[0], ''


class CameraFaceExtractor:
    def __init__(self, config, *, face_targets=False):
        import cv2
        from board.vision.reference_faces import YuNetCompat, SFaceCompat
        self.cv2, self.config = cv2, config
        self.detector = None if face_targets else YuNetCompat(config['face_model'],
            score_threshold=config['minimum_face_score'],input_size=config['input_size'])
        self.remote = None
        if config.get('feature_backend'):
            from board.identity.remote_features import RemoteFaceFeatures
            self.remote=RemoteFaceFeatures(config['feature_backend'])
        self.embedder = None if self.remote else SFaceCompat(config['embedding_model'])
        self.align_crop=SFaceCompat.align_crop
        self.preview_png = None
        self.enrollment_quality = None

    def extract(self, image, observation, key):
        self.preview_png = None
        self.enrollment_quality = None
        if observation.get('target_kind')=='face':
            face=observation.get('face');reason='等待当前目标的清晰正面人脸'
            if (observation.get('face_target')!=key or face is None or len(face)!=15
                    or not all(math.isfinite(float(v)) for v in face)
                    or min(face[2:4])<self.config['minimum_face_pixels'] or face[14]<self.config['minimum_face_score']):face=None
        else:
            if self.detector is None:return None,'人脸目标来源不正确'
            face, reason = face_for_target(self.detector.detect(image), observation['tracks'], key,
                minimum_score=self.config['minimum_face_score'], minimum_pixels=self.config['minimum_face_pixels'])
        if face is None:
            return None, reason
        crop = self.align_crop(image, face)
        variance = float(self.cv2.Laplacian(self.cv2.cvtColor(crop, self.cv2.COLOR_BGR2GRAY), self.cv2.CV_64F).var())
        if not math.isfinite(variance) or variance < self.config['minimum_blur_variance']:
            return None, '人脸较模糊，请保持正对摄像头'
        from board.identity.sampling import pose_quality
        self.enrollment_quality = pose_quality(face, variance)
        ok, encoded = self.cv2.imencode('.png', crop)
        if ok and encoded.nbytes <= 65536:
            self.preview_png = encoded.tobytes()
        if self.remote:
            if not self.preview_png:raise ValueError('Could not encode face-only input')
            vector=self.remote.feature(self.preview_png,key,observation['frame_id'],observation['captured_mono_ms'])
        else:vector=tuple(float(v) for v in self.embedder.feature(crop))
        return vector, ''


def create_service(root, config_path, state):
    from board.identity.live import IdentityService
    from board.identity.store import IdentityStore
    config = config_for(root, config_path)
    path = Path(config['database'])
    path.parent.mkdir(parents=True, exist_ok=True)
    # New local biometric databases are private and are never part of a bundle.
    try:
        fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        pass
    else:
        os.close(fd)
    store = IdentityStore(path, config['model_id'], 128, config['threshold'], config['ambiguity_margin'],
                          allow_cross_thread=True)
    service = IdentityService(store, lambda: CameraFaceExtractor(config,face_targets=True), state.identity_target,
        lock=state.lock, clock=state.clock, result_ttl_ms=config['result_ttl_ms'], interval_ms=config['interval_ms'],
        multi_frame=True,backend='WINDOWS_CPU_SFACE_ORT' if config.get('feature_backend') else 'CPU_SFACE_REFERENCE')
    from board.identity.face_targets import FaceTargetService
    from board.vision.reference_faces import YuNetCompat
    service.face_targets=FaceTargetService(lambda:YuNetCompat(config['face_model'],
        score_threshold=config['minimum_face_score'],input_size=config['input_size']),
        service.offer_face,state.camera_epoch,lock=state.lock,clock=state.clock,
        minimum_score=config['minimum_face_score'],minimum_pixels=config['minimum_face_pixels'])
    service.face_targets.start()
    service.start()
    return service
