"""Portable JSON configuration; paths resolve relative to the project root."""
import copy
import json
from pathlib import Path
from .contracts import finite, integer

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def project_path(value):
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


def load_config(path=None):
    path = project_path(path or "config/runtime.sim.json")
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    validate_config(data)
    return data


def validate_config(data):
    required = {"schema_version", "release_id", "environment", "vision", "freshness",
                "scheduler", "motion", "identity", "dialogue", "logging"}
    if not isinstance(data, dict) or set(data) != required or data["schema_version"] != "aura-project-1":
        raise ValueError("Unsupported/incomplete project configuration")
    if data["environment"] not in ("simulation", "reference", "kv260") or not data["release_id"]:
        raise ValueError("Invalid environment/release")
    v, f, s, m, identity, d = (data[k] for k in
                              ("vision", "freshness", "scheduler", "motion", "identity", "dialogue"))
    if v["backend"] not in ("synthetic", "cpu_yunet", "dpu_plugin"):
        raise ValueError("Unknown detection backend")
    if v["tracker"] not in ("iou_reference", "bytetrack") or v["target_policy"] not in ("single_or_manual", "largest"):
        raise ValueError("Unknown tracking/target policy")
    if data["environment"] != "simulation" and v["backend"] == "synthetic":
        raise ValueError("Synthetic detector requires simulation environment")
    if f["policy"] not in ("fixed", "variable") or not integer(f["fixed_ms"], 1):
        raise ValueError("Invalid freshness policy")
    if f["policy"] == "variable":
        p = f["calibration"]
        names = ("u0_px", "delta_v_px_s", "acceleration_px_s2", "allowed_error_px", "cap_ms")
        if not all(finite(p[k]) and p[k] >= 0 for k in names) or p["allowed_error_px"] <= 0 or not integer(p["cap_ms"], 1):
            raise ValueError("Invalid uncertainty parameters")
        if data["environment"] != "simulation" and p.get("verified") is not True:
            raise ValueError("Variable deadlines require measured calibration outside simulation")
    if s["policy"] not in ("detection_priority", "deadline_admission"):
        raise ValueError("Unknown scheduler policy")
    if not all(finite(s[k]) and s[k] >= 0 for k in ("detection_ms", "identity_ms", "other_ms", "margin_ms")):
        raise ValueError("Invalid task cost estimates")
    if not integer(s["identity_every_n_detections"], 1):
        raise ValueError("Identity period must be positive")
    if m["backend"] not in ("simulation_guard", "disabled"):
        raise ValueError("Physical motion is not enabled by this bootstrap runtime")
    if m["physical_actuation"] is not False:
        raise ValueError("Physical actuation is outside the bootstrap runtime")
    if data["environment"] != "simulation" and m["backend"] != "disabled":
        raise ValueError("Simulation guard cannot authorize physical operation")
    if identity["backend"] not in ("disabled", "synthetic", "cpu_sface"):
        raise ValueError("Unknown identity backend")
    if identity["backend"] == "synthetic" and data["environment"] != "simulation":
        raise ValueError("Synthetic identity requires simulation environment")
    if identity["backend"] == "cpu_sface" and v["backend"] != "cpu_yunet":
        raise ValueError("CPU SFace requires the same-frame YuNet landmark adapter")
    if not integer(identity["dimension"], 1) or not -1 <= identity["threshold"] <= 1 or not 0 <= identity["ambiguity_margin"] <= 2:
        raise ValueError("Invalid identity configuration")
    if d["backend"] not in ("mock", "websocket", "disabled") or not integer(d["timeout_ms"], 1):
        raise ValueError("Invalid dialogue configuration")
    if not integer(identity["cache_ttl_ms"], 1):
        raise ValueError("Identity cache expiry must be positive")
    if not integer(v["confirm_observations"], 1) or not integer(v["lost_ms"], 1):
        raise ValueError("Invalid track lifetime")
    if not all(finite(d[k]) and 0 <= d[k] <= 1 for k in ("speaker_threshold", "speaker_margin")):
        raise ValueError("Invalid speaker threshold")
    return copy.deepcopy(data)
