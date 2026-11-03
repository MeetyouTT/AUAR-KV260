"""Validate a normalized saved trace. No MMIO, simulator, device or network IO."""
import argparse
import json
import math
from pathlib import Path

def number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)

def audit(data, profile):
    errors, unknown = [], []
    events = data.get("events")
    if not isinstance(events, list) or not events:
        return {"status": "UNKNOWN", "scope": "normalized_saved_trace_only",
                "errors": [], "unknown": ["missing events"], "device_accessed": False}
    if data.get("schema") != "aura.guard_trace.v1":
        unknown.append("unsupported or missing trace schema")
    if data.get("build_id") != profile.get("build_id"):
        errors.append("build_id does not match selected contract")
    boot = data.get("boot_id")
    if not boot:
        unknown.append("missing boot_id")
    sequences = {}
    last_time = None
    positive = stops = rejects = 0
    permitted = False
    for index, event in enumerate(events):
        prefix = "event[%d]" % index
        if not isinstance(event, dict):
            errors.append(prefix + " is not an object")
            continue
        now = event.get("time_ms")
        if not number(now) or now < 0:
            errors.append(prefix + " invalid time_ms")
        else:
            if last_time is not None and now < last_time:
                errors.append(prefix + " clock moved backwards")
            last_time = now
        if event.get("boot_id") != boot:
            errors.append(prefix + " boot context mismatch")
        kind = event.get("kind")
        if kind == "commit":
            accepted = event.get("accepted")
            if type(accepted) is not bool:
                unknown.append(prefix + " missing accepted decision")
                continue
            if not accepted:
                rejects += 1
                if not event.get("reason"):
                    unknown.append(prefix + " rejection has no reason")
                continue
            positive += 1
            target, lease, seq = event.get("target_us"), event.get("lease_ms"), event.get("sequence")
            if not number(target) or not profile["min_us"] <= target <= profile["max_us"]:
                errors.append(prefix + " accepted target out of range")
            if not number(lease) or not profile["min_lease_ms"] <= lease <= profile["max_lease_ms"]:
                errors.append(prefix + " accepted lease out of range")
            epoch, session = event.get("epoch"), event.get("session")
            if epoch is None or session is None:
                unknown.append(prefix + " missing epoch/session")
            key = (boot, str(epoch), str(session))
            if type(seq) is not int or seq < 1:
                errors.append(prefix + " invalid accepted sequence")
            else:
                if seq <= sequences.get(key, 0):
                    errors.append(prefix + " accepted replay or out-of-order sequence")
                sequences[key] = max(seq, sequences.get(key, 0))
            permitted = True
        elif kind in ("stop_ack", "expiry_observation"):
            required = ["active", "lease_left_ms"]
            if kind == "stop_ack":
                required += ["armed", "flags"]
            missing = [k for k in required if k not in event]
            if missing:
                unknown.append(prefix + " missing fields: " + ",".join(missing))
            if "active" in event and event["active"] is not False:
                errors.append(prefix + " output still active")
            if "lease_left_ms" in event and event["lease_left_ms"] != 0:
                errors.append(prefix + " remaining lease after stop/expiry")
            if kind == "stop_ack":
                stops += 1
                if "armed" in event and event["armed"] is not False:
                    errors.append(prefix + " still armed after STOP acknowledgement")
                if "flags" in event and event["flags"] != 0:
                    errors.append(prefix + " flags not clear after STOP acknowledgement")
            permitted = False
        elif kind == "output_sample":
            width = event.get("width_us")
            if not number(width) or not profile["min_us"] <= width <= profile["max_us"]:
                errors.append(prefix + " invalid output width")
            if event.get("active") is True and not permitted:
                errors.append(prefix + " active output without a recorded new permit")
        else:
            unknown.append(prefix + " unsupported event kind")
    if positive == 0:
        unknown.append("no accepted positive commit; cannot validate by rejecting everything")
    if stops == 0:
        unknown.append("no complete STOP acknowledgement")
    return {
        "status": "FAIL" if errors else ("UNKNOWN" if unknown else "PASS"),
        "scope": "normalized_saved_trace_only", "evidence_kind": data.get("evidence_kind", "UNKNOWN"),
        "events": len(events), "accepted_commits": positive, "rejected_commits": rejects,
        "errors": errors, "unknown": unknown, "device_accessed": False,
        "rtl_simulated": False, "physical_waveform_verified": False,
        "absolute_source_deadline_verified": False,
    }

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--trace", type=Path, required=True)
    p.add_argument("--profile", type=Path, required=True)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    try:
        result = audit(json.loads(args.trace.read_text(encoding="utf-8-sig")),
                       json.loads(args.profile.read_text(encoding="utf-8-sig")))
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
