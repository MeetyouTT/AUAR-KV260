"""Analyze normalized one-row-per-job logs in one clock domain; no inference."""
import argparse
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

def finite(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)

def stats(values):
    values = sorted(values)
    if not values:
        return {"count": 0, "median": None, "p95": None, "p99": None}
    return {"count": len(values), "median": statistics.median(values),
            "p95": values[max(0, math.ceil(.95 * len(values)) - 1)],
            "p99": values[max(0, math.ceil(.99 * len(values)) - 1)]}

def audit(data):
    errors, unknown = [], []
    rows = data.get("jobs", [])
    if data.get("schema") != "aura.schedule_jobs.v1" or not rows:
        unknown.append("missing schema/jobs")
    if data.get("time_unit") != "ms" or not data.get("clock_domain"):
        unknown.append("explicit ms clock domain required")
    if not data.get("boot_id"):
        unknown.append("explicit boot identity required")
    seen, groups = set(), defaultdict(list)
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append("job[%d] is not an object" % i)
            continue
        task = row.get("task")
        if not isinstance(task, str) or not task:
            unknown.append("job[%d] missing task" % i)
            continue
        if row.get("outcome") not in {"ok", "denied", "cancelled", "expired", "pending", "unknown"}:
            unknown.append("job[%d] unrecognized or missing outcome" % i)
        if row.get("boot_id") != data.get("boot_id"):
            errors.append("job[%d] mixes boot contexts" % i)
        if row.get("clock_domain", data.get("clock_domain")) != data.get("clock_domain"):
            errors.append("job[%d] mixes unmapped clocks" % i)
        identifier = (row.get("boot_id"), row.get("job_id"))
        if not identifier[1]:
            unknown.append("job[%d] missing job_id" % i)
        elif identifier in seen:
            errors.append("duplicate job identity")
        seen.add(identifier)
        for key in ("source_ms", "queued_ms", "start_ms", "end_ms", "consumed_ms", "deadline_ms"):
            if row.get(key) is not None and (not finite(row[key]) or row[key] < 0):
                errors.append("job[%d] invalid %s" % (i, key))
        for a, b in (("source_ms", "queued_ms"), ("queued_ms", "start_ms"),
                     ("start_ms", "end_ms"), ("end_ms", "consumed_ms")):
            if finite(row.get(a)) and finite(row.get(b)) and row[b] < row[a]:
                errors.append("job[%d] time order %s/%s" % (i, a, b))
        groups[task].append(row)
    if errors or unknown:
        return {"status": "FAIL" if errors else "UNKNOWN", "errors": errors, "unknown": unknown,
                "scope": "normalized_job_log_only", "tasks": {}, "device_accessed": False}
    output = {}
    for task, jobs in sorted(groups.items()):
        waits, durations, ages = [], [], []
        timely, missing_validity = 0, 0
        completed = 0
        outcomes = defaultdict(int)
        for row in jobs:
            outcomes[row["outcome"]] += 1
            if row["outcome"] in {"pending", "unknown"}:
                missing_validity += 1
            if finite(row.get("start_ms")) and finite(row.get("queued_ms")):
                waits.append(row["start_ms"] - row["queued_ms"])
            if finite(row.get("end_ms")) and finite(row.get("start_ms")):
                durations.append(row["end_ms"] - row["start_ms"])
            if finite(row.get("consumed_ms")) and finite(row.get("source_ms")):
                ages.append(row["consumed_ms"] - row["source_ms"])
            if row.get("outcome") == "ok":
                completed += 1
                if finite(row.get("consumed_ms")) and finite(row.get("deadline_ms")):
                    timely += row["consumed_ms"] <= row["deadline_ms"]
                else:
                    missing_validity += 1
        output[task] = {
            "arrivals": len(jobs), "completed": completed, "outcomes": dict(outcomes),
            "timely_consumed": timely, "validity_unknown": missing_validity,
            "timely_rate_all_arrivals": None if missing_validity else timely / len(jobs),
            "waiting_ms": stats(waits), "execution_ms": stats(durations),
            "consumed_source_age_ms": stats(ages),
        }
    return {"status": "FAIL" if errors else ("UNKNOWN" if unknown else "PASS"),
            "scope": "normalized_job_log_only", "evidence_kind": data.get("evidence_kind", "UNKNOWN"),
            "errors": errors, "unknown": unknown, "tasks": output,
            "percentile_method": "nearest_rank; median uses statistics.median",
            "device_accessed": False, "causal_speedup_claimed": False}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, required=True)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    try:
        result = audit(json.loads(args.input.read_text(encoding="utf-8-sig")))
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
