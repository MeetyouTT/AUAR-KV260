"""Recheck camera owner/checkpoint/GUI before any camera-only maintenance."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.request


def props(unit):
    fields = "MainPID,ActiveState,SubState,Result,ExecMainStatus,ExecMainCode,Restart,KillMode,SendSIGKILL,TimeoutStopUSec,ExecStart,DropInPaths"
    raw = subprocess.check_output(["systemctl", "show", unit, "--property=" + fields], text=True)
    return dict(line.split("=", 1) for line in raw.splitlines() if "=" in line)


def get(url):
    op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with op.open(url, timeout=3) as stream:
        return json.load(stream)


camera = props("aura-camera-ui.service")
gui = props("aura-avatar-ui.service")
health = get("http://127.0.0.1:8790/health")
ui = get("http://127.0.0.1:8783/api/state")
manual = ui.get("manual_pan", {})
exec_paths = re.findall(r"/[^\s;{}]+\.py", camera.get("ExecStart", ""))
source_path = Path(exec_paths[-1]) if exec_paths else None

maintenance_root = None
pins_valid = None
checkpoint_summary = None
if source_path is not None:
    for path in map(Path, camera.get("DropInPaths", "").split()):
        try:
            raw = path.read_text()
        except OSError:
            continue
        match = re.search(r"--root\s+(\S+)", raw)
        if match and "native-maintenance" in str(path):
            maintenance_root = Path(match.group(1))
            break
if maintenance_root is not None:
    meta = json.loads((maintenance_root / "meta.json").read_text())
    state = json.loads((maintenance_root / "state.json").read_text())
    pins = meta.get("source_pins", {})
    pins_valid = all(hashlib.sha256((maintenance_root / name).read_bytes()).hexdigest() == digest
                     for name, digest in pins.items())
    candidate_config = json.loads(Path(meta["candidate_config"]).read_text())
    checkpoint_path = Path(candidate_config["native_execution"]["checkpoint_output"])
    if checkpoint_path.exists() and not checkpoint_path.is_symlink():
        checkpoint = json.loads(checkpoint_path.read_text())
        seed, aux = checkpoint.get("seed", {}), checkpoint.get("auxiliary", {})
        checkpoint_summary = {
            "exists": True,
            "schema_ok": checkpoint.get("schema") == "aura-native-protection-checkpoint-2",
            "scope_ok": checkpoint.get("scope") == "final_quiescent_before_native_owner_close",
            "source_pid": seed.get("source_pid"),
            "boot_matches": seed.get("boot_id") == Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
            "fenced": bool(seed.get("fenced") or aux.get("fenced")),
            "active": bool(aux.get("active")),
            "primary_waiting": bool(aux.get("primary_waiting")),
            "pending_results": sum(bool(x) for x in aux.get("pending_result_tokens", [])),
        }
else:
    state = {}

summary = {
    "boot_id": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
    "camera": {k: camera.get(k) for k in ("MainPID", "ActiveState", "SubState", "Result", "ExecMainStatus", "Restart", "KillMode", "SendSIGKILL", "TimeoutStopUSec")},
    "camera_source_basename": source_path.name if source_path else None,
    "camera_source_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest() if source_path and source_path.is_file() else None,
    "maintenance_phase": state.get("phase"),
    "maintenance_source_pins_valid": pins_valid,
    "checkpoint": checkpoint_summary,
    "gui": {k: gui.get(k) for k in ("MainPID", "ActiveState", "SubState", "Result")},
    "gui_phase": ui.get("phase"),
    "gui_playing": ui.get("playing"),
    "audio_output_state": ui.get("audio_output_state"),
    "manual_pan": {k: manual.get(k) for k in ("state", "pulse_us", "minimum_us", "maximum_us", "automatic_following", "mechanical_reference_calibrated")},
    "camera_health": {
        "reported_pid": health.get("pid"),
        "native_critical": health.get("dpu_schedule", {}).get("native_critical"),
        "owner_fenced": health.get("dpu_schedule", {}).get("owner_fenced"),
        "identity_ready": health.get("identity", {}).get("ready"),
        "worker_alive": health.get("identity", {}).get("face_targets", {}).get("worker_alive"),
        "freshness_gaps": health.get("identity", {}).get("face_targets", {}).get("freshness_metrics", {}).get("counters", {}).get("observed_gap_intervals"),
    },
    "motion_feed_status": None,
}
try:
    feed = get("http://127.0.0.1:8790/v1/motion/observation")
    summary["motion_feed_status"] = {"http": 200, "state": feed.get("state"), "source_kind": feed.get("source_kind")}
except Exception as exc:
    code = getattr(exc, "code", None)
    summary["motion_feed_status"] = {"http": code, "error_type": type(exc).__name__}
print(json.dumps(summary, sort_keys=True))
