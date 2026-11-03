"""Explicit CPU/Windows/DPU identity on the SAME immutable source frame."""
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
    if (type(config.get('threshold')) not in (int, float) or not math.isfinite(config['threshold'])
            or type(config.get('ambiguity_margin')) not in (int, float)
            or not math.isfinite(config['ambiguity_margin'])):
        raise ValueError('Explicit model-specific identity threshold and ambiguity margin are required')
    if (type(config.get('input_size')) is not int or config['input_size'] not in (128, 192, 256, 320)
            or not 32 <= config['minimum_face_pixels'] <= 256
            or not 0 <= config['minimum_blur_variance'] <= 10000
            or not .5 <= config['minimum_face_score'] <= 1
            or not 0 <= config['threshold'] <= 1 or not 0 <= config['ambiguity_margin'] <= 1):
        raise ValueError('Invalid identity reference parameters')
    for key in ('face_model', 'embedding_model'):
        p = Path(config[key])
        config[key] = str(p if p.is_absolute() else root/p)
    feature = config.get('feature_backend')
    if feature is not None and not isinstance(feature, dict):
        raise ValueError('Invalid feature backend configuration')
    if feature is not None and feature.get('kind') != 'dpu_sface':
        from board.identity.remote_features import RemoteFaceFeatures
        RemoteFaceFeatures(config['feature_backend'])
    if config.get('enrollment_photos') is not None:
        from board.identity.photo_archive import configuration
        configuration(config['enrollment_photos'])
    backend = config.get('face_backend')
    if backend is not None:
        if (not isinstance(backend, dict) or set(backend) != {'kind', 'model', 'manifest', 'model_sha256', 'manifest_sha256'}
                or backend['kind'] != 'dpu_yunet' or config['input_size'] != 320):
            raise ValueError('Invalid DPU face backend configuration')
        for key in ('model', 'manifest'):
            if not Path(backend[key]).is_absolute():
                raise ValueError('DPU face artifacts require explicit absolute paths')
    config['database'] = str(Path(config['database']).expanduser())
    if not Path(config['database']).is_absolute():
        raise ValueError('Identity database must use an absolute device-local path')
    if feature is not None and feature.get('kind') == 'dpu_sface':
        from board.identity.model_store import validate_dpu_configuration
        validate_dpu_configuration(config)
    if config.get('dpu_sface_shadow') is not None:
        from board.identity.sface_shadow import shadow_configuration
        shadow_configuration(config)
    if config.get('dpu_sface_calibration') is not None:
        from board.identity.sface_calibration import calibration_configuration
        calibration_configuration(config)
    if config.get('dpu_sface_producer') is not None:
        from board.identity.sface_producer import producer_configuration
        producer_configuration(config)
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
    def __init__(self, config, *, face_targets=False, schedule=None, owner=None, clock=None,
                 current_target=None, guard_lock=None):
        import cv2
        from board.vision.reference_faces import YuNetCompat, SFaceCompat
        self.cv2, self.config = cv2, config
        self.detector = None if face_targets else YuNetCompat(config['face_model'],
            score_threshold=config['minimum_face_score'],input_size=config['input_size'])
        self.remote = None
        self.local_dpu = None
        feature = config.get('feature_backend')
        if feature and feature.get('kind') == 'dpu_sface':
            from board.vision.dpu_sface import DpuSFace
            self.local_dpu = DpuSFace(config, schedule, owner, clock)
        elif feature:
            from board.identity.remote_features import RemoteFaceFeatures
            self.remote=RemoteFaceFeatures(config['feature_backend'])
        self.embedder = None if self.remote or self.local_dpu else SFaceCompat(config['embedding_model'])
        self.align_crop=SFaceCompat.align_crop
        self.preview_png = None
        self.enrollment_quality = None
        self.shadow = None
        self.shadow_error = ''
        self.shadow_shutdown_timeout = False
        self.calibration = None
        from board.identity.sface_producer import producer_configuration
        self.producer_enabled = producer_configuration(config) is not None
        self.producer = None
        if (config.get('dpu_sface_shadow') or {}).get('enabled'):
            try:
                from board.identity.sface_shadow import SFaceShadow
                from board.identity.sface_calibration import CalibrationSession, calibration_configuration
                calibration = calibration_configuration(config)
                if calibration is not None:
                    self.calibration = CalibrationSession(clock,config['dpu_sface_shadow']['max_source_age_ms'])
                self.shadow = SFaceShadow(config, schedule, owner, current_target,
                    clock=clock, guard_lock=guard_lock, result_observer=self.calibration)
                self.shadow.start()
                if self.producer_enabled:
                    from board.identity.sface_producer import SFaceProducer
                    self.producer = SFaceProducer(config, self.shadow, current_target, clock=clock,
                        guard_lock=guard_lock, align_crop=self.align_crop, cv2=self.cv2)
                    self.producer.start()
            except Exception as exc:
                # Auxiliary startup failures cannot disable Windows identity.
                self.shadow_error = type(exc).__name__[:64]
                if self.calibration is not None:self.calibration.close()

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
        shadow_without_reference = (self.shadow is not None and
            not (self.config.get('dpu_sface_shadow') or {}).get('compare_cosine', True))
        if shadow_without_reference and not self.producer_enabled:
            # Independent compute evidence does not require Windows online.
            # The primary request/error still follows the original path below.
            self._offer_shadow(crop, observation, key, None)
        ok, encoded = self.cv2.imencode('.png', crop)
        if ok and encoded.nbytes <= 65536:
            self.preview_png = encoded.tobytes()
        if self.local_dpu:
            # The store contract accepts ordinary finite Python scalars.
            # The DPU decoder returns numpy.float32 values.
            vector = tuple(float(v) for v in self.local_dpu.feature(
                crop, source_mono_ms=observation['captured_mono_ms']))
        elif self.remote:
            if not self.preview_png:raise ValueError('Could not encode face-only input')
            vector=self.remote.feature(self.preview_png,key,observation['frame_id'],observation['captured_mono_ms'])
        else:vector=tuple(float(v) for v in self.embedder.feature(crop))
        if self.shadow is not None and not shadow_without_reference and not self.producer_enabled:
            self._offer_shadow(crop, observation, key, vector)
        return vector, ''

    def _offer_shadow(self, crop, observation, key, reference):
        try:
            quality = {'quality':self.enrollment_quality} if self.calibration is not None else {}
            self.shadow.offer(crop, observation['frame_id'], observation['captured_mono_ms'], key, reference, **quality)
        except Exception as exc:
            self.shadow_error = type(exc).__name__[:64]

    def close(self):
        producer_stopped = True
        if self.producer is not None:
            try:
                producer_stopped = self.producer.close(timeout=2)
            except Exception as exc:
                producer_stopped = False
                self.shadow_error = type(exc).__name__[:64]
        if self.shadow is not None:
            try:
                self.shadow_shutdown_timeout = not self.shadow.close(timeout=2)
            except Exception as exc:
                self.shadow_error = type(exc).__name__[:64]
                self.shadow_shutdown_timeout = True
        if self.local_dpu:
            self.local_dpu.close()
        self.shadow_shutdown_timeout = self.shadow_shutdown_timeout or not producer_stopped
        return not self.shadow_shutdown_timeout

    def shutdown_ready(self):
        return ((self.producer is None or self.producer.stopped.is_set())
                and (self.shadow is None or self.shadow.stopped.is_set()))

    def feature_status(self):
        if self.local_dpu is not None:
            return self.local_dpu.availability()
        return {'ready': True, 'unavailable_reason': None, 'detail': '', 'recovery_required': False}

    def health(self):
        if self.shadow is not None or self.shadow_error:
            try:
                if self.calibration is not None and self.shadow is not None:
                    self.calibration.observe_target(self.shadow.current_target())
                shadow = self.shadow.health() if self.shadow is not None else {'enabled':True,'ready':False}
                return {'shadow':shadow,'auxiliary_error':self.shadow_error,
                        'producer':self.producer.health() if self.producer is not None else {'enabled':False},
                        'shadow_shutdown_timeout':self.shadow_shutdown_timeout,
                        'calibration':self.calibration.health() if self.calibration is not None else {'enabled':False}}
            except Exception as exc:
                return {'shadow':{'enabled':True,'ready':False},'auxiliary_error':type(exc).__name__[:64],
                        'shadow_shutdown_timeout':self.shadow_shutdown_timeout}
        return self.local_dpu.health() if self.local_dpu else None


def create_service(root, config_path, state, *, schedule=None, owner=None):
    from board.identity.live import IdentityService
    from board.identity.store import IdentityStore
    config = config_for(root, config_path)
    dpu = (config.get('feature_backend') or {}).get('kind') == 'dpu_sface'
    if getattr(schedule,'native_critical',False):
        if not dpu or (config.get('face_backend') or {}).get('kind') != 'dpu_yunet':
            raise ValueError('Native execution requires both reviewed INT8 face backends')
        for name in ('dpu_sface_shadow','dpu_sface_calibration','dpu_sface_producer'):
            if (config.get(name) or {}).get('enabled'):
                raise ValueError('Legacy auxiliary runner cannot bypass the shared native gate: '+name)
    if dpu:
        if schedule is None or owner is None:
            raise ValueError('Select a shared DPU scheduler and owner before opening INT8 identity storage')
        from board.identity.model_store import open_dpu_store
        store = open_dpu_store(config)
    else:
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
    from board.identity.photo_archive import EnrollmentPhotoArchive
    photos=EnrollmentPhotoArchive(config['enrollment_photos']) if config.get('enrollment_photos') else None
    service = IdentityService(store, lambda: CameraFaceExtractor(config, face_targets=True,
        schedule=schedule, owner=owner, clock=state.clock,
        current_target=state.identity_target, guard_lock=state.lock), state.identity_target,
        lock=state.lock, clock=state.clock, result_ttl_ms=config['result_ttl_ms'], interval_ms=config['interval_ms'],
        multi_frame=True, backend='DPU_SFACE_INT8' if dpu else
        'WINDOWS_CPU_SFACE_ORT' if config.get('feature_backend') else 'CPU_SFACE_REFERENCE',
        photo_archive=photos)
    from board.identity.face_targets import FaceTargetService
    from board.vision.reference_faces import YuNetCompat
    if config.get('face_backend'):
        from board.vision.dpu_yunet import DpuYuNet
        factory=lambda:DpuYuNet(config, schedule, owner)
    else:
        factory=lambda:YuNetCompat(config['face_model'],
            score_threshold=config['minimum_face_score'],input_size=config['input_size'])
    service.face_targets=FaceTargetService(factory,
        service.offer_face,state.camera_epoch,lock=state.lock,clock=state.clock,
        minimum_score=config['minimum_face_score'],minimum_pixels=config['minimum_face_pixels'],slot_retry=True,freshness_metrics=True,retry_recovery_ms=50,
        independent_admission=bool(schedule is not None and getattr(schedule,'yunet_slot_wait_ms',0)))
    service.face_targets.start()
    service.start()
    return service
