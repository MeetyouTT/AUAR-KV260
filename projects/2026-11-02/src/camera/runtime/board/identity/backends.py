from common.config import project_path
from board.vision.reference_core import iou


class CpuSFaceEmbedder:
    kind = "CPU_SFACE_REFERENCE"

    def __init__(self, config, face_detector):
        from board.vision.reference_faces import SFaceCompat
        self.model = SFaceCompat(project_path(config["model"]))
        self.face_detector = face_detector

    def extract(self, frame, target):
        faces = getattr(self.face_detector, "last_faces", None)
        if faces is None or not len(faces):
            raise RuntimeError("SFace requires same-frame YuNet five-point landmarks")
        face = max(faces, key=lambda row: iou(target.box, row[:4]))
        if iou(target.box, face[:4]) < 0.5:
            raise RuntimeError("Face landmarks cannot be attributed to this target")
        crop = self.model.align_crop(frame.image, face)
        return tuple(float(v) for v in self.model.feature(crop))
