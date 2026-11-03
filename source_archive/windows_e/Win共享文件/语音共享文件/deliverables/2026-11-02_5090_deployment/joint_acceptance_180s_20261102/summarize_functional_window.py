"""Summarize actual public numeric events without inventing physical acceptance."""
import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def rows(name):
    path = ROOT / name
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def leaves(value, prefix=""):
    result = {}
    if not isinstance(value, dict):
        return result
    for key, item in value.items():
        path = prefix + "/" + key
        if type(item) in (int, float):
            result[path] = item
        elif isinstance(item, dict):
            result.update(leaves(item, path))
    return result


def main():
    events = rows("functional_events.jsonl")
    models = rows("windows_models.jsonl")
    samples = [row for row in events if row.get("event") == "SAMPLE"]
    baseline = next((row for row in events if row.get("event") == "BASELINE"), None)
    finished = next((row for row in reversed(events) if row.get("event") == "FINISHED"), None)
    completed = {row["turn_hash"] for row in events if row.get("event") == "TURN_COMPLETED"}
    human_path = ROOT / "USER_FUNCTIONAL_FEEDBACK.json"
    human = json.loads(human_path.read_text(encoding="utf-8")) if human_path.is_file() else None
    model_deltas = {}
    if len(models) >= 2:
        before = leaves({k: models[0].get(k, {}) for k in ("counts", "gpu_schedule")})
        after = leaves({k: models[-1].get(k, {}) for k in ("counts", "gpu_schedule")})
        for key in before.keys() & after.keys():
            if "/counts/" in key and after[key] >= before[key]:
                model_deltas[key] = after[key] - before[key]
    faults = [row["gui_fault_count"] for row in samples if type(row.get("gui_fault_count")) is int]
    memory_errors = sum(row.get("memory", {}).get("error_present") is True for row in samples)
    result = {
        "schema": "aura-joint-functional-window-result-1",
        "summarized_host_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": "OBSERVATION_COMPLETE_HUMAN_ACCEPTANCE_PENDING" if finished else "OBSERVATION_INCOMPLETE",
        "baseline_seen": baseline is not None,
        "finished_seen": finished is not None,
        "elapsed_board_seconds": finished.get("elapsed_seconds") if finished else None,
        "first_host_receipt_utc": baseline.get("host_observed_utc") if baseline else None,
        "last_host_receipt_utc": finished.get("host_observed_utc") if finished else None,
        "gui_samples": len(samples),
        "windows_model_samples": len(models),
        "new_full_playback_ack_count": len(completed),
        "at_least_two_new_full_playbacks": len(completed) >= 2,
        "observed_speaking_samples": sum(row.get("phase") == "SPEAKING" for row in samples),
        "observed_microphone_open_samples": sum(row.get("microphone_open") is True for row in samples),
        "observed_following_samples": sum(row.get("pan", {}).get("automatic_following") is True for row in samples),
        "gui_fault_count_first": faults[0] if faults else None,
        "gui_fault_count_last": faults[-1] if faults else None,
        "memory_error_samples": memory_errors,
        "model_counter_deltas": model_deltas,
        "human_feedback": human,
        "board_controls_sent_by_functional_observer": 0,
        "measurement_scope": [
            "Actual full playback commits, not a physical loudspeaker waveform measurement",
            "GUI activity and model admission counters, not full hardware kernel traces",
            "Only new ACK hashes after this window baseline count",
            "Human physical voice/name/memory/avatar/axis observations are separate evidence",
            "No cold-boot or general multi-person calibration acceptance is implied",
        ],
    }
    (ROOT / "FUNCTIONAL_RESULT.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("status", "gui_samples", "windows_model_samples", "new_full_playback_ack_count", "elapsed_board_seconds")}))


if __name__ == "__main__":
    main()
