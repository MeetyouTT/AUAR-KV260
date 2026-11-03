"""Validate and replay saved camera health counters. No board or runtime imports."""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

STAGES = {"yolo": "yolo.native_and_decode", "yunet": "yunet.native_lease",
          "sface": "sface.native_lease"}
SCHEMA = "aura.public_camera_counters.v1"


def project(path):
    """Make a shareable numeric projection without copying images, identities or jobs."""
    records = []
    digest = hashlib.sha256()
    finished = False
    boot = None
    with path.open("rb") as stream:
        for line in stream:
            digest.update(line)
            row = json.loads(line)
            event = row["event"]
            if finished or event not in {"start", "sample", "end"}:
                raise ValueError("unexpected input event")
            if event == "end":
                if row["stopped_by_signal"] or row["samples"] != len(records) - 1:
                    raise ValueError("incomplete observed window")
                finished = True
                continue
            if event == "start" and records:
                raise ValueError("unexpected second start")
            if event == "sample" and (not records or row["n"] != len(records)):
                raise ValueError("missing sample")
            camera = row["camera"]
            if not camera["ok"]:
                raise ValueError("camera health unavailable")
            data = camera["data"]
            schedule = data["dpu_schedule"]
            stages = data["pipeline_metrics"]["stages"]
            counters = {}
            for model, stage in STAGES.items():
                calls = (schedule["primary_calls"] if model == "yolo"
                         else schedule["optional"][model]["native_completed"])
                counters[model] = {"calls": calls, "count": stages[stage]["count"],
                                   "total_ms": stages[stage]["total_ms"]}
            boot = row.get("boot_id") or boot
            records.append({"boot": boot, "pid": data["pid"],
                            "finished_mono_s": camera["request_finished_monotonic_s"],
                            "models": counters})
    if not finished:
        raise ValueError("missing final event")
    return {"schema": SCHEMA, "source_sha256": digest.hexdigest(), "records": records}


def finite(value):
    return type(value) in {float, int} and math.isfinite(value) and value >= 0


def audit(data):
    if data.get("schema") != SCHEMA:
        raise ValueError("unknown counter schema")
    rows = data["records"]
    if not isinstance(rows, list) or len(rows) < 2:
        raise ValueError("need baseline and at least one later sample")
    first, last = rows[0], rows[-1]
    prev = None
    for row in rows:
        if not row["boot"] or type(row["pid"]) is not int or row["pid"] <= 0:
            raise ValueError("missing process/boot identity")
        if (row["boot"], row["pid"]) != (first["boot"], first["pid"]):
            raise ValueError("counter owner or boot changed")
        now = row["finished_mono_s"]
        if not finite(now) or (prev and now <= prev["finished_mono_s"]):
            raise ValueError("invalid observation time")
        for model in STAGES:
            entry = row["models"][model]
            for field in ("calls", "count", "total_ms"):
                v = entry[field]
                if not finite(v) or (field != "total_ms" and type(v) is not int):
                    raise ValueError("invalid counter for " + model)
                if prev and v < prev["models"][model][field]:
                    raise ValueError("counter reset for " + model)
        prev = row
    span = last["finished_mono_s"] - first["finished_mono_s"]
    result = {}
    for model, stage in STAGES.items():
        a, b = first["models"][model], last["models"][model]
        calls = b["calls"] - a["calls"]
        count = b["count"] - a["count"]
        ms = b["total_ms"] - a["total_ms"]
        if count == 0 and ms != 0:
            raise ValueError("stage total changed without stage count for " + model)
        result[model] = {"counter_delta": calls, "observed_rate_hz": calls / span,
                         "stage": stage, "stage_count_delta": count,
                         "stage_mean_ms": ms / count if count else None}
    return {"status": "PASS", "sample_count_after_baseline": len(rows) - 1,
            "counter_interval_s": span, "models": result,
            "per_job_source_to_consume_p99_ms": None, "dpu_hardware_utilization": None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--raw", action="store_true", help="read original board_numeric JSONL")
    parser.add_argument("--project", action="store_true", help="print the validated public projection")
    args = parser.parse_args()
    try:
        data = project(args.input) if args.raw else json.loads(args.input.read_text(encoding="utf-8-sig"))
        report = audit(data)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        print(json.dumps({"status": "FAIL", "reason": str(exc)}))
        return 1
    print(json.dumps(data if args.project else report, indent=2, allow_nan=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
