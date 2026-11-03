"""Summarize declared-valid benchmark rows without mixing machines, cache or warm states."""
import argparse
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

METRICS = ("asr_ms", "first_text_ms", "speech_ready_ms", "first_pcm_ms", "complete_ack_ms")
def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
def stats(values):
    values = sorted(values)
    return {"count": len(values), "median_ms": statistics.median(values) if values else None,
            "p95_ms": values[max(0, math.ceil(.95 * len(values)) - 1)] if values else None}

def audit(data):
    errors, unknown = [], []
    if data.get("schema") != "aura.voice_bench.v1":
        unknown.append("unsupported or missing schema")
    rows = data.get("records", [])
    if not isinstance(rows, list) or not rows:
        return {"status": "UNKNOWN", "errors": [], "unknown": ["no benchmark rows"], "groups": []}
    groups, seen = defaultdict(list), set()
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append("row[%d] is not an object" % i)
            continue
        required = ("trial_id", "platform_id", "variant", "case_group", "model_sha256",
                    "backend", "warm_state", "tts_cache_hit", "answer_valid")
        missing = [key for key in required if key not in row or row[key] is None]
        if missing:
            unknown.append("row[%d] missing %s" % (i, ",".join(missing)))
            continue
        if type(row["tts_cache_hit"]) is not bool or type(row["answer_valid"]) is not bool:
            errors.append("row[%d] cache/quality flags must be explicit booleans" % i)
            continue
        identity = (row["platform_id"], row["trial_id"])
        if identity in seen:
            errors.append("duplicate trial_id within platform")
        seen.add(identity)
        invalid = False
        for key in METRICS:
            if row.get(key) is not None and (not finite(row[key]) or row[key] < 0):
                errors.append("row[%d] invalid %s" % (i, key))
                invalid = True
        if invalid:
            continue
        key = tuple(str(row[k]) for k in ("platform_id", "variant", "case_group",
                                          "model_sha256", "backend", "warm_state"))
        key += (row["tts_cache_hit"],)
        groups[key].append(row)
    output = []
    for key, samples in sorted(groups.items()):
        valid = [row for row in samples if row["answer_valid"]]
        output.append({
            "platform_id": key[0], "variant": key[1], "case_group": key[2],
            "model_sha256": key[3], "backend": key[4], "warm_state": key[5],
            "tts_cache_hit": key[6], "observed_samples": len(samples),
            "declared_valid_answers": len(valid),
            "declared_invalid_answers": len(samples) - len(valid),
            "metrics": {m: stats([r[m] for r in valid if finite(r.get(m))]) for m in METRICS},
        })
    return {"status": "FAIL" if errors else ("UNKNOWN" if unknown else "PASS"),
            "scope": "saved_metadata_descriptive_statistics",
            "errors": errors, "unknown": unknown, "groups": output,
            "percentile_method": "nearest_rank",
            "quality_labels_independently_verified": False,
            "causal_speedup_claimed": False, "acoustic_first_sound_measured": False,
            "model_invoked": False}

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
