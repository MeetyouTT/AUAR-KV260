"""Validate saved XIR metadata; optionally hash a local artifact. No inference."""
import argparse
import hashlib
import json
from pathlib import Path

def audit(data, profiles, kind, artifact=None):
    errors, unknown = [], []
    profile = profiles.get("models", {}).get(kind)
    if profile and profile.get("deployment") == "CPU_ORT":
        return {"status": "UNKNOWN", "scope": "saved_xir_metadata_only", "errors": [],
                "unknown": ["speaker uses CPU/ORT; no DPU profile applies"],
                "inference_executed": False}
    if not profile or not profile.get("input_shape"):
        return {"status": "UNKNOWN", "scope": "saved_xir_metadata_only",
                "errors": [], "unknown": ["model target is not validated: " + kind],
                "inference_executed": False}
    if "models" in data:
        matches = [x for x in data["models"] if x.get("sha256") == profile["sha256"]]
        if len(matches) == 1:
            data = matches[0]
        elif len(data["models"]) == 1:
            data = data["models"][0]
        else:
            return {"status": "UNKNOWN", "errors": [], "unknown": ["ambiguous model selection"]}
    if data.get("sha256") != profile["sha256"]:
        errors.append("model SHA differs from selected version")
    parts = data.get("partitions")
    if not isinstance(parts, list):
        parts = []
        unknown.append("missing partitions")
    dpu = [x for x in parts if x.get("device") == "DPU"]
    if len(dpu) != profile["dpu_partitions"]:
        errors.append("unexpected number of DPU compute partitions")
    for part in dpu:
        if str(part.get("fingerprint", "")).lower() != profiles["fingerprint"].lower():
            errors.append("DPU fingerprint mismatch")
        inputs = part.get("inputs", [])
        outputs = part.get("outputs", [])
        if not inputs:
            unknown.append("missing DPU input interface")
        else:
            shape = inputs[0].get("dims", inputs[0].get("shape"))
            if shape != profile["input_shape"]:
                errors.append("input shape mismatch")
            if str(inputs[0].get("dtype", "")).lower() != "xint8":
                errors.append("input interface is not xint8")
            if inputs[0].get("fix_point") != profile["input_fix_point"]:
                errors.append("input fix_point mismatch")
        if not outputs:
            unknown.append("missing DPU output interface")
        for tensor in outputs:
            if str(tensor.get("dtype", "")).lower() != "xint8":
                errors.append("DPU output interface is not xint8")
    artifact_status = "NOT_RUN"
    if artifact is not None:
        path = Path(artifact)
        if not path.is_file():
            unknown.append("artifact does not exist")
            artifact_status = "MISSING"
        else:
            h = hashlib.sha256()
            with path.open("rb") as stream:
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    h.update(block)
            actual = h.hexdigest()
            artifact_status = "PASS" if actual == profile["sha256"] else "FAIL"
            if artifact_status == "FAIL":
                errors.append("artifact byte SHA mismatch")
            if data.get("bytes") is not None and path.stat().st_size != data["bytes"]:
                errors.append("artifact byte length mismatch")
    return {"status": "FAIL" if errors else ("UNKNOWN" if unknown else "PASS"),
            "scope": "saved_xir_metadata_only", "model": kind,
            "errors": errors, "unknown": unknown, "artifact_check": artifact_status,
            "dpu_partitions": len(dpu),
            "cpu_partitions": sum(x.get("device") == "CPU" for x in parts),
            "inference_executed": False, "device_accessed": False,
            "accuracy_verified": False, "runtime_backend_verified": False}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--metadata", type=Path, required=True)
    p.add_argument("--profiles", type=Path, required=True)
    p.add_argument("--model-kind", required=True)
    p.add_argument("--artifact", type=Path)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    try:
        result = audit(json.loads(args.metadata.read_text(encoding="utf-8-sig")),
                       json.loads(args.profiles.read_text(encoding="utf-8-sig")),
                       args.model_kind, args.artifact)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        result = {"status": "UNKNOWN", "errors": [], "unknown": [str(exc)]}
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return {"PASS": 0, "FAIL": 1, "UNKNOWN": 2}[result["status"]]

if __name__ == "__main__":
    raise SystemExit(main())
