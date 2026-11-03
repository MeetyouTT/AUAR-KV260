"""CPU-only export and public-fixture equivalence; never opens a speaker DB."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import wave

TASK = Path(__file__).resolve().parent
ROOT = TASK.parents[2]
sys.path.insert(0, str(TASK / "export_dependencies"))
sys.path.insert(0, str(ROOT / "aura"))
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["OMP_NUM_THREADS"] = "2"
os.environ["MKL_NUM_THREADS"] = "2"


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def cosine(a, b):
    return sum(x * y for x, y in zip(a, b))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output).resolve()
    allowed = Path("D:/AIModels/speaker-identity/board-onnx-20261030").resolve()
    if output != allowed:
        raise ValueError("Use the isolated ECAPA candidate model directory")
    import numpy as np
    import onnx
    import onnxruntime as ort
    import torch
    from common.speaker_identity import EcapaEncoder, verify_model
    from board.runtime.audio.board_speaker_onnx import BoardEcapaOnnxEncoder, normalize_embedding
    torch.set_num_threads(2)
    directory = Path("D:/AIModels/speaker-identity/ecapa")
    original_id = verify_model(directory)
    start = time.perf_counter()
    encoder = EcapaEncoder(directory, original_id)
    encoder.model.eval()
    load_ms = (time.perf_counter() - start) * 1000
    feature = encoder.model.mods.compute_features
    stft = feature.compute_STFT
    bank = feature.compute_fbanks
    norm = encoder.model.mods.mean_var_norm
    expected = (stft.sample_rate, stft.n_fft, stft.win_length, stft.hop_length, stft.center, stft.pad_mode,
                stft.normalized_stft, stft.onesided, bank.n_mels, bank.amin, bank.top_db, bank.multiplier,
                bank.db_multiplier, bank.freeze, bank.param_rand_factor, norm.norm_type, norm.std_norm)
    assert expected == (16000, 400, 400, 160, True, "constant", False, True, 80, 1e-10, 80., 10, 0., True, 0., "sentence", False), expected
    assert not feature.deltas and not feature.context and bank.filter_shape == "triangular"
    output.mkdir(parents=True, exist_ok=True)
    if (output / "manifest.json").exists():
        raise ValueError("A completed candidate already exists; verify it rather than overwrite")
    with torch.inference_mode():
        central = bank.f_central.repeat(bank.all_freqs_mat.shape[1], 1).transpose(0, 1)
        bands = bank.band.repeat(bank.all_freqs_mat.shape[1], 1).transpose(0, 1)
        matrix = bank._create_fbank_matrix(central, bands).cpu().numpy()
    np.savez(output / "frontend.npz", window=stft.window.cpu().numpy(), filterbank=matrix)
    class Embedding(torch.nn.Module):
        def __init__(self, model):
            super().__init__(); self.model = model
        def forward(self, features):
            lengths = torch.ones(features.shape[0], dtype=features.dtype, device=features.device)
            return self.model(features, lengths).reshape(1, 192)
    wrapper = Embedding(encoder.model.mods.embedding_model).eval()
    torch.onnx.export(wrapper, (torch.zeros(1, 301, 80),), str(output / "embedding.onnx"),
        input_names=["features"], output_names=["embedding"], dynamic_axes={"features": {1: "frames"}},
        opset_version=17, do_constant_folding=True, dynamo=False)
    graph = onnx.load(str(output / "embedding.onnx"))
    onnx.checker.check_model(graph)
    manifest = {"schema_version": 1, "source_model_id": original_id, "source_embedding_sha256": sha(directory / "embedding_model.ckpt"),
        "source_revision": "0f99f2d0ebe89ac095bcc5903c4dd8f72b367286", "sample_rate": 16000, "dimension": 192,
        "precision": "float32", "onnx_opset": 17, "onnx_ir_version": graph.ir_version,
        "sha256": {name: sha(output / name) for name in ("embedding.onnx", "frontend.npz")},
        "frontend": {"n_fft": 400, "hop_length": 160, "window": "original_periodic_hamming_400",
                     "center": True, "pad_mode": "constant", "n_mels": 80, "db_floor": 80., "sentence_mean": True,
                     "std_normalization": False, "global_embedding_normalization": False},
        "candidate_only": True, "private_identity_data": False}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    candidate = BoardEcapaOnnxEncoder(output, threads=2)
    fixture_manifest = json.loads((ROOT / "deliverables/2026-10-19_speaker_identity/public_sample_sources.json").read_text(encoding="utf-8"))
    clips = []
    for fixture in fixture_manifest:
        path = Path("D:/AIModels/speaker-identity/public-samples") / fixture["file"]
        assert sha(path) == fixture["sha256"]
        with wave.open(str(path), "rb") as stream:
            assert (stream.getframerate(), stream.getnchannels(), stream.getsampwidth()) == (16000, 1, 2)
            raw = stream.readframes(stream.getnframes())
        clips.append((fixture["file"], raw, fixture["sha256"]))
    # Public-derived boundary cases exercise the dynamic frame axis, without
    # opening a microphone or using a person's stored voice templates.
    first = clips[0][1]
    clips.extend([("public_crop_100ms", first[:3200], sha_bytes(first[:3200])),
                  ("public_repeat_20s", (first * 8)[:640000], sha_bytes((first * 8)[:640000]))])
    rows = []; vectors = {}; references = {}; public_data = {}
    for index, (name, raw, source_hash) in enumerate(clips):
        waveform = torch.from_numpy(np.frombuffer(raw, dtype="<i2").astype(np.float32)[None] / np.float32(32768.))
        with torch.inference_mode():
            torch_features = norm(feature(waveform), torch.ones(1)).cpu().numpy()
        numpy_features = candidate.frontend(raw)
        start = time.perf_counter(); baseline = encoder.encode(raw); torch_ms = (time.perf_counter() - start) * 1000
        start = time.perf_counter(); converted = candidate.encode(raw); onnx_ms = (time.perf_counter() - start) * 1000
        isolated = normalize_embedding(candidate.session.run(["embedding"], {"features": torch_features})[0].reshape(-1))
        rows.append({"fixture": name, "sha256": source_hash, "samples": len(raw) // 2,
            "frontend_max_abs_error": float(np.max(np.abs(torch_features - numpy_features))),
            "embedding_max_abs_error": max(abs(a-b) for a,b in zip(baseline, converted)),
            "embedding_cosine": cosine(baseline, converted), "onnx_only_cosine": cosine(baseline, isolated),
            "torch_cpu_ms": round(torch_ms, 3), "onnx_cpu_ms": round(onnx_ms, 3)})
        vectors[name] = converted; references[name] = baseline
        public_data["pcm_" + str(index)] = np.frombuffer(raw, dtype="<i2")
        public_data["embedding_" + str(index)] = np.asarray(baseline, dtype=np.float64)
    pair_errors = [abs(cosine(references[a], references[b]) - cosine(vectors[a], vectors[b]))
                   for i, a in enumerate(vectors) for b in list(vectors)[i+1:]]
    passed = all(r["embedding_max_abs_error"] < 5e-5 and 1-r["embedding_cosine"] < 1e-6 for r in rows) and max(pair_errors) < 5e-5
    np.savez(output / "public_validation_fixtures.npz", **public_data)
    report = {"status": "PASS_PUBLIC_EQUIVALENCE" if passed else "FAIL_PUBLIC_EQUIVALENCE", "production_deployed": False,
        "private_gallery_read": False, "microphone_opened": False, "source_model_id": original_id,
        "candidate_directory": str(output), "manifest_sha256": sha(output / "manifest.json"),
        "candidate_files": {p.name: {"bytes": p.stat().st_size, "sha256": sha(p)} for p in output.iterdir() if p.is_file()},
        "torch": torch.__version__, "onnx": onnx.__version__, "onnxruntime": ort.__version__, "cpu_threads": 2,
        "load_ms": round(load_ms, 2), "fixtures": rows, "pairwise_cosine_max_abs_error": max(pair_errors),
        "source_weights_unchanged": verify_model(directory) == original_id, "field_calibrated": False,
        "sources": ["https://huggingface.co/speechbrain/spkrec-ecapa-voxceleb",
                    "https://speechbrain.readthedocs.io/en/v1.0.3/_modules/speechbrain/processing/features.html",
                    "https://docs.pytorch.org/docs/2.5/onnx.html"]}
    (TASK / "cpu_equivalence.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"status": report["status"], "fixtures": len(rows), "max_embedding_error": max(r["embedding_max_abs_error"] for r in rows),
                      "max_pair_error": max(pair_errors), "model_bytes": (output / "embedding.onnx").stat().st_size}))
    if not passed:
        raise SystemExit(2)


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


if __name__ == "__main__":
    main()
