"""Candidate failure boundaries; no real model, gallery or audio device."""
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "aura"))
from board.runtime.audio.board_speaker_onnx import (BoardEcapaOnnxEncoder, SpeechBrainFbank,
                                                   normalize_embedding)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Session:
    def __init__(self):
        self.output = np.arange(1, 193, dtype=np.float32)[None]
        self.input_name = "features"
        self.seen = []
    def get_inputs(self):
        return [SimpleNamespace(name=self.input_name)]
    def get_outputs(self):
        return [SimpleNamespace(name="embedding")]
    def run(self, names, feeds):
        self.seen.append(feeds["features"])
        return [self.output]


@pytest.fixture
def candidate(tmp_path):
    np.savez(tmp_path / "frontend.npz", window=np.ones(400, dtype=np.float32),
             filterbank=np.ones((201, 80), dtype=np.float32) / 201.)
    (tmp_path / "embedding.onnx").write_bytes(b"synthetic-model-placeholder")
    manifest = {"schema_version": 1, "sample_rate": 16000, "dimension": 192, "precision": "float32",
                "source_model_id": "synthetic-fixture-model",
                "sha256": {f: sha(tmp_path / f) for f in ("embedding.onnx", "frontend.npz")}}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    session = Session()
    return tmp_path, session, lambda model, threads: session


@pytest.mark.parametrize("samples,frames", [(1600, 11), (16000, 101), (320000, 2001)])
def test_dynamic_frontend_lengths_and_sentence_mean(candidate, samples, frames):
    path, session, factory = candidate
    encoder = BoardEcapaOnnxEncoder(path, session_factory=factory)
    vector = encoder.encode(np.zeros(samples, dtype="<i2").tobytes())
    assert len(vector) == 192 and abs(sum(v*v for v in vector) - 1) < 1e-12
    assert session.seen[0].shape == (1, frames, 80)
    assert session.seen[0].dtype == np.float32 and np.max(np.abs(session.seen[0])) < 1e-5


@pytest.mark.parametrize("raw", [b"", b"x" * 3198, b"x" * 3201, b"x" * 640002, "not bytes"],
                         ids=["empty", "too-short", "odd-length", "too-long", "wrong-type"])
def test_bounded_pcm_rejected_before_inference(candidate, raw):
    path, session, factory = candidate
    encoder = BoardEcapaOnnxEncoder(path, session_factory=factory)
    with pytest.raises(ValueError):
        encoder.encode(raw)
    assert session.seen == []


@pytest.mark.parametrize("output", [np.zeros((1, 192)), np.full((1, 192), np.nan), np.full((1, 192), np.inf), np.ones((1, 193))])
def test_invalid_embedding_output_fails_closed(candidate, output):
    path, session, factory = candidate
    encoder = BoardEcapaOnnxEncoder(path, session_factory=factory)
    session.output = output
    with pytest.raises(ValueError):
        encoder.encode(b"\0" * 3200)


def test_candidate_bytes_and_expected_manifest_are_pinned(candidate):
    path, session, factory = candidate
    with pytest.raises(ValueError, match="manifest fingerprint"):
        BoardEcapaOnnxEncoder(path, session_factory=factory, expected_manifest_sha256="0" * 64)
    (path / "embedding.onnx").write_bytes(b"changed")
    with pytest.raises(ValueError, match="file fingerprint"):
        BoardEcapaOnnxEncoder(path, session_factory=factory)


def test_graph_interface_and_cpu_thread_bounds(candidate):
    path, session, factory = candidate
    for threads in (0, 3, True):
        with pytest.raises(ValueError):
            BoardEcapaOnnxEncoder(path, session_factory=factory, threads=threads)
    session.input_name = "different-input"
    with pytest.raises(ValueError, match="ONNX interface"):
        BoardEcapaOnnxEncoder(path, session_factory=factory)


def test_bad_frontend_shapes_and_nonfinite_constants_are_rejected(tmp_path):
    for window, bank in ((np.ones(399), np.ones((201, 80))), (np.ones(400), np.full((201, 80), np.nan))):
        path = tmp_path / "bad-frontend.npz"
        np.savez(path, window=window, filterbank=bank)
        with pytest.raises(ValueError):
            SpeechBrainFbank(path)


def test_health_does_not_grant_identity_or_open_media(candidate):
    path, session, factory = candidate
    health = BoardEcapaOnnxEncoder(path, session_factory=factory).health()
    assert health["identity_access_granted"] is False
    assert health["production_deployed"] is False
    assert health["global_embedding_normalization"] is False
