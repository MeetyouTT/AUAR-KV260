"""No automatic CPU/DPU fallback: a backend must satisfy its own contract."""
import hashlib
import importlib
from common.config import project_path
from common.contracts import Detection


class SyntheticDetector:
    kind = "SYNTHETIC_INPUT"

    def detect(self, frame):
        if frame.ref.timestamp_semantics != "synthetic" or not isinstance(frame.image, dict):
            raise ValueError("Synthetic detector accepts explicit fixture input only")
        return [Detection(tuple(row["box"]), row["score"], row.get("label", "person"))
                for row in frame.image.get("detections", [])]


class CpuFaceDetector:
    kind = "CPU_YUNET_REFERENCE"

    def __init__(self, config):
        from .reference_faces import YuNetCompat
        self.model = YuNetCompat(project_path(config["model"]),
                                 score_threshold=config["score_threshold"],
                                 input_size=config["input_size"])
        self.last_faces = None

    def detect(self, frame):
        self.last_faces = self.model.detect(frame.image)
        return [Detection(tuple(float(v) for v in row[:4]), float(row[14]), "face")
                for row in self.last_faces]


class DpuPluginDetector:
    """A verified model-specific VART adapter is provided via module:factory.

    Adapter API: backend_kind='DPU', verify_runtime()->arch fingerprint,
    detect(CapturedFrame)->sequence[Detection]. Pre/postprocessing is explicit
    in that adapter; a generic ONNX file is not enough to satisfy this port.
    """
    kind = "DPU_PLUGIN"

    def __init__(self, config):
        entry = config.get("entrypoint", "")
        if ":" not in entry or not config.get("model_sha256") or not config.get("arch_fingerprint"):
            raise RuntimeError("DPU model, SHA256, architecture fingerprint and module:factory required")
        model = project_path(config["model"])
        digest = hashlib.sha256()
        with model.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        if digest.hexdigest() != config["model_sha256"]:
            raise RuntimeError("DPU model hash mismatch")
        module, factory = entry.split(":", 1)
        self.adapter = getattr(importlib.import_module(module), factory)(config)
        if (getattr(self.adapter, "backend_kind", None) != "DPU"
                or self.adapter.verify_runtime() != config["arch_fingerprint"]):
            raise RuntimeError("DPU runtime architecture mismatch")

    def detect(self, frame):
        output = list(self.adapter.detect(frame))
        if not all(isinstance(item, Detection) for item in output):
            raise TypeError("DPU adapter must return original-image Detection objects")
        return output


def create_detector(config):
    return {"synthetic": lambda: SyntheticDetector(),
            "cpu_yunet": lambda: CpuFaceDetector(config),
            "dpu_plugin": lambda: DpuPluginDetector(config)}[config["backend"]]()
