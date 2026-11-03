"""Reviewed ECAPA-only stage/launch/poll operation, executed through UART.

CONFIG is supplied by the local reviewed runner. Every file is a pinned public
model, pinned public fixture or candidate code. No business state is changed.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request


def digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(data)
    return h.hexdigest()


def safe():
    with urllib.request.urlopen("http://127.0.0.1:8783/api/state", timeout=3) as stream:
        state = json.load(stream)
    assert state["phase"] == "IDLE" and state["playing"] is False
    hf = state.get("handsfree_dialogue", {}); pan = state.get("manual_pan", {})
    assert hf.get("enabled") is False and hf.get("microphone_open") is False
    assert pan.get("automatic_following") is False
    return {"idle": True, "microphone": False, "playing": False, "following": False}


def main():
    config = CONFIG
    assert config["base"].startswith("http://192.168.50.1:")
    pin = config["pin"]
    assert len(pin) == 64 and all(v in "0123456789abcdef" for v in pin)
    root = Path("/home/root/aura-board-owner-candidate-20261030/speaker-" + pin[:16])
    assert not root.is_symlink()
    mode = config["mode"]
    if mode == "stage":
        safe()
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(config["base"] + "/manifest.json", timeout=5) as stream:
            encoded = stream.read(65537)
        assert len(encoded) <= 65536 and hashlib.sha256(encoded).hexdigest() == pin
        manifest = json.loads(encoded)
        assert manifest["purpose"] == "public_same_ecapa_candidate_only" and manifest["private_identity_data"] is False
        names = {"embedding.onnx", "frontend.npz", "manifest.json", "public_validation_fixtures.npz",
                 "board_speaker_onnx.py", "arm_verify_public.py", "onnxruntime-1.17.3-aarch64.whl"}
        assert {item["name"] for item in manifest["entries"]} == names
        root.mkdir(parents=True, exist_ok=True)
        for item in manifest["entries"]:
            # Reuse the separately validated ORT17 candidate read-only. Do not
            # re-install a package into the board's base environment.
            if item["name"].endswith(".whl"):
                continue
            target = root / item["name"]
            assert target.parent.resolve() == root.resolve() and not target.is_symlink()
            if target.exists():
                assert target.stat().st_size == item["bytes"] and digest(target) == item["sha256"]
                continue
            partial = target.with_suffix(target.suffix + ".partial")
            assert not partial.exists() and not partial.is_symlink()
            h = hashlib.sha256(); size = 0
            with opener.open(config["base"] + "/assets/" + item["sha256"], timeout=10) as stream, partial.open("xb") as out:
                while True:
                    data = stream.read(min(1024 * 1024, item["bytes"] + 1 - size))
                    if not data:
                        break
                    size += len(data); assert size <= item["bytes"]
                    h.update(data); out.write(data)
                out.flush(); os.fsync(out.fileno())
            assert size == item["bytes"] and h.hexdigest() == item["sha256"]
            os.link(str(partial), str(target)); partial.unlink()
        pinned = root / "assets_manifest.json"
        if pinned.exists():
            assert pinned.read_bytes() == encoded
        else:
            with pinned.open("xb") as stream:
                stream.write(encoded)
        print(json.dumps({"stage_complete": True, "candidate_root": str(root), "safety": safe(), "copied_public_files": 6}))
        return
    assert (root / "assets_manifest.json").is_file() and digest(root / "assets_manifest.json") == pin
    status_file = root / "probe_status.json"
    report_file = root / "arm_report.json"
    if mode == "launch":
        safety = safe()
        assert not status_file.exists() and not report_file.exists()
        manifest = json.loads((root / "assets_manifest.json").read_text())
        for item in manifest["entries"]:
            if not item["name"].endswith(".whl"):
                assert digest(root / item["name"]) == item["sha256"]
        deps = Path("/home/root/aura-board-owner-candidate-20261030/fft-ee19b936d17aa451/deps")
        asr = Path("/home/root/aura-board-owner-candidate-20261030/asr-1.13.8/deps")
        assert (deps / "onnxruntime").is_dir() and asr.is_dir()
        env = dict(os.environ, PYTHONPATH=str(deps) + ":" + str(asr), PYTHONNOUSERSITE="1",
                   OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
        command = ["timeout", "90s", "nice", "-n", "10", sys.executable, "-B", str(root / "arm_verify_public.py"),
            "--candidate-dir", str(root), "--encoder-module", str(root / "board_speaker_onnx.py"),
            "--expected-manifest-sha256", "d59b61bd1dfffacabf4927ec55e9469550882ff213c1b5ac5d3b6fa2dd6f77fe",
            "--expected-fixtures-sha256", "a3d536b79a713ba726a0be4a1c341d188be8a988465c4d858c232084e1463ccb",
            "--indices", "0,1,2,3", "--threads", "1", "--budget-seconds", "75", "--report", str(report_file)]
        with (root / "probe.stdout").open("xb") as out, (root / "probe.stderr").open("xb") as err:
            child = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                     env=env, close_fds=True, start_new_session=True)
        status = {"candidate_root": str(root), "pid": child.pid, "started_utc": time.time(),
                  "timeout_seconds": 90, "safety_before": safety, "production_changed": False}
        with status_file.open("x") as stream:
            json.dump(status, stream)
        print(json.dumps(dict(status, launched=True)))
        return
    assert mode == "poll"
    status = json.loads(status_file.read_text())
    if report_file.exists():
        print(json.dumps({"complete": True, "report": json.loads(report_file.read_text()), "safety_after": safe(),
                          "candidate_root": str(root), "stderr_bytes": (root / "probe.stderr").stat().st_size,
                          "probe_process_alive": Path("/proc/" + str(status["pid"])).exists()}))
    else:
        running = Path("/proc/" + str(status["pid"])).exists()
        result = {"complete": False, "running": running, "age_seconds": time.time() - status["started_utc"], "candidate_root": str(root)}
        if not running:
            result["stderr"] = (root / "probe.stderr").read_text(errors="replace")[-4000:]
        print(json.dumps(result))


if __name__ == "__main__":
    main()
