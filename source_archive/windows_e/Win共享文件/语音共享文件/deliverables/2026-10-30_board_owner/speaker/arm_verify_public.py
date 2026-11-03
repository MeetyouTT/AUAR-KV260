"""Short-lived ARM CPU verification using ONLY pinned public test fixtures.

Run through an external timeout/nice wrapper, never a production service. This
script imports no torch/SpeechBrain and does not open any capture/playback or
identity database. Output contains numerical errors, timings and resource counts.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import platform
import sys
import time


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rss():
    result = {}
    path = Path("/proc/self/status")
    if path.exists():
        for line in path.read_text().splitlines():
            if line.startswith(("VmRSS:", "VmHWM:")):
                result[line.split(":")[0] + "_kib"] = int(line.split()[1])
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-dir", required=True)
    parser.add_argument("--encoder-module", required=True)
    parser.add_argument("--expected-manifest-sha256", required=True)
    parser.add_argument("--expected-fixtures-sha256", required=True)
    parser.add_argument("--indices", default="0,1,2,3")
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--budget-seconds", type=float, default=75.)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    started = time.perf_counter()
    indices = [int(v) for v in args.indices.split(",")]
    if not indices or len(set(indices)) != len(indices) or any(v not in range(6) for v in indices):
        raise ValueError("Invalid public fixture selection")
    directory = Path(args.candidate_dir).resolve()
    fixture_path = directory / "public_validation_fixtures.npz"
    if sha(fixture_path) != args.expected_fixtures_sha256:
        raise ValueError("Public fixture fingerprint mismatch")
    spec = importlib.util.spec_from_file_location("candidate_board_speaker_onnx", args.encoder_module)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    import numpy as np
    import onnxruntime as ort
    before = rss(); load_start = time.perf_counter()
    encoder = module.BoardEcapaOnnxEncoder(directory, threads=args.threads,
        expected_manifest_sha256=args.expected_manifest_sha256)
    load_ms = (time.perf_counter() - load_start) * 1000
    rows = []; references = {}; outputs = {}
    with np.load(str(fixture_path), allow_pickle=False) as fixtures:
        for i in indices:
            if time.perf_counter() - started > args.budget_seconds:
                raise TimeoutError("Public ECAPA probe exceeded its budget")
            pcm = np.asarray(fixtures["pcm_" + str(i)], dtype="<i2")
            reference = np.asarray(fixtures["embedding_" + str(i)], dtype=np.float64)
            begin = time.perf_counter()
            embedding = np.asarray(encoder.encode(pcm.tobytes()), dtype=np.float64)
            elapsed = time.perf_counter() - begin
            rows.append({"fixture_index": i, "samples": pcm.size,
                "embedding_max_abs_error": float(np.max(np.abs(reference - embedding))),
                "cosine_to_original_cpu": float(np.dot(reference, embedding)),
                "encode_ms": round(elapsed * 1000, 3), "real_time_factor": elapsed / (pcm.size / 16000.),
                "resources": rss()})
            references[i] = reference; outputs[i] = embedding
    errors = [abs(float(np.dot(references[a], references[b])) - float(np.dot(outputs[a], outputs[b])))
              for j, a in enumerate(indices) for b in indices[j+1:]]
    passed = all(r["embedding_max_abs_error"] < 5e-5 and 1-r["cosine_to_original_cpu"] < 1e-6 for r in rows) and max(errors, default=0.) < 5e-5
    arm = platform.machine().lower() in {"aarch64", "arm64", "armv8l"}
    status = ("PASS_ARM_PUBLIC_EQUIVALENCE" if arm else "PASS_HOST_PUBLIC_RUNNER_SMOKE") if passed else "FAIL_PUBLIC_EQUIVALENCE"
    report = {"status": status, "arm_executed": arm,
        "production_deployed": False, "field_calibrated": False, "identity_gallery_opened": False,
        "microphone_opened": False, "speaker_identity_ids_transmitted": False,
        "platform": platform.machine(), "python": platform.python_version(), "numpy": np.__version__,
        "onnxruntime": ort.__version__, "providers": encoder.session.get_providers(), "threads": args.threads,
        "load_ms": round(load_ms, 3), "elapsed_seconds": time.perf_counter() - started,
        "resources_before": before, "resources_after": rss(), "fixtures": rows,
        "pairwise_cosine_max_abs_error": max(errors, default=0.), "torch_imported": "torch" in sys.modules,
        "speechbrain_imported": "speechbrain" in sys.modules,
        "manifest_sha256": args.expected_manifest_sha256, "public_fixtures_sha256": args.expected_fixtures_sha256,
        "omitted_fixture_indices": sorted(set(range(6)) - set(indices))}
    Path(args.report).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report))
    if not passed:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
