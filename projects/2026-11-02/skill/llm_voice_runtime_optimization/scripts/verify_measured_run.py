"""Compare public per-call measurements against the saved run receipt (offline)."""
import argparse
import csv
import json
import math
import statistics
import sys
from pathlib import Path


def positive(value, name, allow_zero=False):
    number = float(value)
    if not math.isfinite(number) or number < 0 or (number == 0 and not allow_zero):
        raise ValueError("invalid numeric value in " + name)
    return number


def cases(rows):
    result = {}
    for row in rows:
        ident = int(row["case"])
        if ident <= 0 or ident in result:
            raise ValueError("invalid or duplicate case " + str(ident))
        result[ident] = row
    return result


def compare(rows, fields, expected, allow_zero=False):
    result = {}
    for field in fields:
        values = sorted(positive(row[field], field, allow_zero) for row in rows)
        actual = dict(n=len(values), min=min(values), median=statistics.median(values),
                      max=max(values), mean=statistics.mean(values),
                      p95_nearest_rank=values[math.ceil(.95 * len(values)) - 1])
        for name, value in actual.items():
            if not math.isclose(value, expected[field][name], rel_tol=1e-8, abs_tol=1e-7):
                raise ValueError("receipt mismatch in " + field + "." + name)
        result[field] = actual
    return result


def audit(llm, tts, gpu, receipt):
    if receipt["schema"] != "aura-current-model-performance-results-1":
        raise ValueError("unsupported receipt schema")
    if not llm or not tts or not gpu:
        raise ValueError("missing measurement rows")
    lcases, tcases = cases(llm), cases(tts)
    skipped = [int(x["case"]) for x in receipt["skipped_cases"]]
    planned = set(range(1, receipt["planned_each"] + 1))
    if (lcases.keys() != tcases.keys() or set(skipped) & lcases.keys()
            or len(skipped) != len(set(skipped)) or set(skipped) | lcases.keys() != planned):
        raise ValueError("requested, admitted and skipped cases do not reconcile")
    for name, table in (("llm", llm), ("tts", tts)):
        if receipt[name + "_success"] != len(table) or receipt[name + "_attempted"] != len(table):
            raise ValueError("unrepresented attempt or success for " + name)
    for row in llm:
        tps = int(row["eval_count"]) / (positive(row["eval_duration_ms"], "decode duration") / 1000)
        if not math.isclose(tps, float(row["decode_tokens_per_second"]), rel_tol=1e-5):
            raise ValueError("inconsistent decoded tokens/duration")
    for row in tts:
        samples, rate = int(row["samples"]), int(row["sample_rate"])
        if samples <= 0 or rate != receipt["sample_rate_hz"] or rate <= 0:
            raise ValueError("incorrect PCM samples or sample rate")
        duration = samples / rate
        rtf = positive(row["rpc_ms"], "TTS RPC") / 1000 / duration
        if (not math.isclose(duration, float(row["audio_seconds"]))
                or not math.isclose(rtf, float(row["rpc_real_time_factor"]), rel_tol=1e-5)):
            raise ValueError("inconsistent PCM duration or RPC RTF")
        if row["cache_hit"].lower() != "false" or receipt["all_tts_cache_hit_false"] is not True:
            raise ValueError("separate cached and uncached TTS trials")
    if len(gpu) != receipt["host_sample_count"]:
        raise ValueError("GPU sample count does not match")
    times = [positive(row["host_mono"], "host monotonic", True) for row in gpu]
    if any(a >= b for a, b in zip(times, times[1:])):
        raise ValueError("GPU timestamps are repeated or reordered")
    return {"status": "PASS", "run_id": receipt["run_id"], "admitted_cases": sorted(lcases),
            "skipped": receipt["skipped_cases"], "llm": compare(llm, ("rpc_ms", "first_content_ms",
                "decode_tokens_per_second"), receipt["llm"]), "tts": compare(tts, ("rpc_ms",
                "audio_seconds", "rpc_real_time_factor"), receipt["tts_metrics"]),
            "device_gpu": compare(gpu, ("used_mib", "free_mib"), receipt["windows_gpu"], True),
            "scope": "offline reproduction of one saved warm run; no live inference or acoustic timing"}


def read_table(folder, name):
    with (folder / name).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path, help="directory containing the three CSVs and reference.json")
    folder = parser.parse_args().directory
    try:
        result = audit(read_table(folder, "llm_cases.csv"), read_table(folder, "tts_cases.csv"),
                       read_table(folder, "windows_gpu_timeseries.csv"),
                       json.loads((folder / "reference.json").read_text(encoding="utf-8-sig")))
    except (ValueError, KeyError, TypeError, OverflowError, OSError) as exc:
        print("Cannot verify measurements: " + str(exc), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
