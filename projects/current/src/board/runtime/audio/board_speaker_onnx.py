"""Candidate ECAPA inference on the board: NumPy frontend + CPU ONNX Runtime.

No microphone, network, identity gallery, enrolment, permission grant or service
is opened here. The FP32 graph is exported from the existing verified SpeechBrain
ECAPA weights. Public-sample equivalence is evidence, not field calibration.
"""
import hashlib
import json
import math
from pathlib import Path


def _sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_embedding(value):
    values = [float(v) for v in value]
    if len(values) != 192 or any(not math.isfinite(v) for v in values):
        raise ValueError("Invalid ECAPA output")
    length = math.sqrt(sum(v * v for v in values))
    if length < 1e-12:
        raise ValueError("Zero ECAPA output")
    return [v / length for v in values]


class SpeechBrainFbank:
    """Exact exported window/filter constants; no substituted mel convention.

    SpeechBrain 1.0.3 defaults to CONSTANT centering padding here, despite older
    descriptive docstrings mentioning reflect padding. Constants and attributes
    are checked by the exporter against the loaded original modules.
    """
    def __init__(self, constants):
        import numpy as np
        self.np = np
        with np.load(str(constants), allow_pickle=False) as data:
            if set(data.files) != {"window", "filterbank"}:
                raise ValueError("Invalid ECAPA feature constants")
            self.window = np.array(data["window"], dtype=np.float32, copy=True)
            self.filterbank = np.array(data["filterbank"], dtype=np.float32, copy=True)
        if self.window.shape != (400,) or self.filterbank.shape != (201, 80):
            raise ValueError("Invalid ECAPA feature dimensions")
        if not np.isfinite(self.window).all() or not np.isfinite(self.filterbank).all():
            raise ValueError("Non-finite ECAPA feature constants")
        self.window.flags.writeable = False
        self.filterbank.flags.writeable = False

    def __call__(self, raw):
        if not isinstance(raw, bytes) or len(raw) % 2 or not 3200 <= len(raw) <= 640000:
            raise ValueError("Require bounded 16kHz mono PCM16 bytes")
        np = self.np
        wave = np.frombuffer(raw, dtype="<i2").astype(np.float32) / np.float32(32768.)
        wave = np.pad(wave, (200, 200), mode="constant")
        count = 1 + (wave.size - 400) // 160
        frames = np.lib.stride_tricks.as_strided(wave, shape=(count, 400),
                    strides=(wave.strides[0] * 160, wave.strides[0]), writeable=False)
        spectrum = np.fft.rfft(frames * self.window, n=400, axis=1).astype(np.complex64)
        power = spectrum.real * spectrum.real + spectrum.imag * spectrum.imag
        mel = np.matmul(power, self.filterbank)
        logs = np.float32(10.) * np.log10(np.maximum(mel, np.float32(1e-10)))
        logs = np.maximum(logs, np.max(logs) - np.float32(80.))
        # Single utterance, full length, sentence mean; std_norm=False.
        return np.ascontiguousarray((logs - np.mean(logs, axis=0, keepdims=True))[None], dtype=np.float32)


class BoardEcapaOnnxEncoder:
    dimension = 192

    def __init__(self, directory, *, expected_manifest_sha256=None, threads=1, session_factory=None):
        import numpy as np
        if type(threads) is not int or not 1 <= threads <= 2:
            raise ValueError("ECAPA candidate permits one or two CPU threads")
        directory = Path(directory).resolve()
        manifest_path = directory / "manifest.json"
        if expected_manifest_sha256 is not None and _sha(manifest_path) != expected_manifest_sha256:
            raise ValueError("ECAPA candidate manifest fingerprint mismatch")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if (manifest.get("schema_version") != 1 or manifest.get("sample_rate") != 16000
                or manifest.get("dimension") != 192 or manifest.get("precision") != "float32"
                or set(manifest.get("sha256", {})) != {"embedding.onnx", "frontend.npz"}):
            raise ValueError("Unsupported ECAPA candidate manifest")
        for filename, fingerprint in manifest["sha256"].items():
            if _sha(directory / filename) != fingerprint:
                raise ValueError("ECAPA candidate file fingerprint mismatch")
        self.model_id = manifest["source_model_id"]
        self.candidate_id = "ecapa-onnx-f32:" + manifest["sha256"]["embedding.onnx"]
        self.frontend = SpeechBrainFbank(directory / "frontend.npz")
        if session_factory is None:
            import onnxruntime as ort
            options = ort.SessionOptions()
            options.intra_op_num_threads = threads
            options.inter_op_num_threads = 1
            options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
            options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_EXTENDED
            options.log_severity_level = 3
            self.session = ort.InferenceSession(str(directory / "embedding.onnx"), options, providers=["CPUExecutionProvider"])
        else:
            self.session = session_factory(str(directory / "embedding.onnx"), threads)
        inputs = self.session.get_inputs()
        outputs = self.session.get_outputs()
        if len(inputs) != 1 or inputs[0].name != "features" or len(outputs) != 1 or outputs[0].name != "embedding":
            raise ValueError("Invalid ECAPA ONNX interface")
        self.np = np

    def encode(self, raw):
        features = self.frontend(raw)
        output = self.session.run(["embedding"], {"features": features})[0]
        return normalize_embedding(self.np.asarray(output).reshape(-1))

    def health(self):
        return {"candidate": True, "production_deployed": False, "backend": "onnxruntime_cpu",
                "dimension": 192, "sample_rate": 16000, "waveform_scale": "pcm16_divide_32768",
                "feature_normalization": "sentence_mean_no_std", "embedding_normalization": "l2",
                "global_embedding_normalization": False, "identity_access_granted": False}
