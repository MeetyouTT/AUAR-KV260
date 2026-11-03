"""Source-only public-WAV probe. No microphone, network, Store, or file writes.

Root supplies all input paths and SHA256 pins. Run on isolated Linux AArch64.
The whole WAV is an externally supplied endpoint; this does not run or tune VAD.
Official v1.13.8 ending: 0.66 s zero padding -> input_finished -> drain is_ready.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import re
import sys
import time
import unicodedata
import wave
from pathlib import Path

VERSION = "1.13.8"
SAMPLE_RATE = 16000
PUBLIC_WAV_SAMPLES = 89834  # 5.614625 seconds; hash still supplied by root.
TAIL_SAMPLES = 10560  # 0.66 seconds, model context only, never real audio.


class ProbeRefusal(Exception):
    pass


def require(condition, code):
    if not condition:
        raise ProbeRefusal(code)


def pinned_file(raw_path, expected_hash, size_limit):
    path = Path(raw_path)
    require(path.is_absolute(), "PATH_NOT_ABSOLUTE")
    require(re.fullmatch(r"[0-9a-fA-F]{64}", expected_hash) is not None,
            "HASH_FORMAT_INVALID")
    require(path.is_file() and not path.is_symlink(), "INPUT_NOT_REGULAR_FILE")
    require(0 < path.stat().st_size <= size_limit, "INPUT_SIZE_INVALID")
    resolved = str(path.resolve()).replace("\\", "/").casefold()
    require("win共享文件" not in resolved and not resolved.startswith("e:/"),
            "INPUT_IN_SHARED_TREE")
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    require(digest.hexdigest() == expected_hash.lower(), "INPUT_HASH_MISMATCH")
    return path


def normalized(text):
    # Keep all letters/numerals: no Chinese-number equivalence or fuzzy matching.
    return "".join(c for c in unicodedata.normalize("NFKC", text).casefold()
                   if c.isalnum())


def accuracy(reference, hypothesis):
    ref, hyp = normalized(reference), normalized(hypothesis)
    require(0 < len(ref) <= 500 and len(hyp) <= 1000, "TEXT_LENGTH_INVALID")
    row = list(range(len(hyp) + 1))
    for i, left in enumerate(ref, 1):
        next_row = [i]
        for j, right in enumerate(hyp, 1):
            next_row.append(min(next_row[-1] + 1, row[j] + 1,
                                row[j - 1] + (left != right)))
        row = next_row
    return {"normalized_exact": ref == hyp, "reference_chars": len(ref),
            "hypothesis_chars": len(hyp), "edit_distance": row[-1],
            "cer": round(row[-1] / len(ref), 6)}


def quantile(values, fraction):
    ordered = sorted(values)
    return ordered[max(0, math.ceil(len(ordered) * fraction) - 1)] if ordered else 0


def run_round(recognizer, samples, tail, feed_ms, reference=None, *,
              clock=time.perf_counter, sleep=time.sleep, cpu=time.process_time):
    """Synchronous consumer of a virtual real-time source; never drop late data.

    Each block becomes available at its end-time. If decoding falls behind,
    subsequent blocks are offered immediately, and the lag is measured.
    This is an input pacing probe, not an actual audio capture/queue test.
    """
    require(feed_ms in (20, 160), "FEED_SIZE_INVALID")
    require(len(samples) == PUBLIC_WAV_SAMPLES and len(tail) == TAIL_SAMPLES,
            "SAMPLE_COUNT_INVALID")
    stream = recognizer.create_stream()
    frame_samples = SAMPLE_RATE * feed_ms // 1000
    duration = len(samples) / SAMPLE_RATE
    calls, decode_wall, decode_cpu, lag = [], 0.0, 0.0, []
    backlog_peak, accepted = 0.0, 0
    started, cpu_started = clock(), cpu()
    real_end = started + duration

    def observe_backlog():
        nonlocal backlog_peak
        elapsed_audio = min(duration, max(0.0, clock() - started))
        backlog_peak = max(backlog_peak, elapsed_audio - accepted / SAMPLE_RATE)

    def drain():
        nonlocal decode_wall, decode_cpu
        while recognizer.is_ready(stream):
            require(len(calls) < 2000 and clock() - started < 120,
                    "PROBE_BUDGET_EXCEEDED")
            wall_before, cpu_before = clock(), cpu()
            recognizer.decode_stream(stream)
            wall_delta, cpu_delta = clock() - wall_before, cpu() - cpu_before
            decode_wall += wall_delta
            decode_cpu += cpu_delta
            calls.append(wall_delta)
            observe_backlog()

    for offset in range(0, len(samples), frame_samples):
        stop = min(offset + frame_samples, len(samples))
        deadline = started + stop / SAMPLE_RATE
        while clock() < deadline:
            sleep(max(0.0, deadline - clock()))
        observe_backlog()
        lag.append(max(0.0, clock() - deadline))
        stream.accept_waveform(SAMPLE_RATE, samples[offset:stop])
        accepted = stop
        if stop == len(samples):
            input_accepted_at = clock()
        drain()

    # Do not wait another 0.66 seconds: these zeros are context, not recording.
    flush_started = clock()
    stream.accept_waveform(SAMPLE_RATE, tail)
    stream.input_finished()
    drain()
    result = recognizer.get_result(stream)
    ended, cpu_ended = clock(), cpu()
    require(isinstance(result, str) and len(result) <= 1000, "RESULT_TYPE_INVALID")
    summary = {
        "feed_ms": feed_ms, "real_samples": accepted,
        "tail_zero_samples": len(tail), "tail_wait_ms": 0,
        "real_chunk_count": len(lag),
        "last_real_chunk_samples": len(samples) % frame_samples or frame_samples,
        "wave_duration_ms": duration * 1000,
        "round_wall_ms": (ended - started) * 1000,
        "round_cpu_ms": (cpu_ended - cpu_started) * 1000,
        "input_accept_after_scheduled_end_ms": (input_accepted_at - real_end) * 1000,
        "final_after_scheduled_input_end_ms": (ended - real_end) * 1000,
        "final_after_last_real_accept_ms": (ended - input_accepted_at) * 1000,
        "flush_wall_ms": (ended - flush_started) * 1000,
        "decode_calls": len(calls), "decode_wall_ms": decode_wall * 1000,
        "decode_cpu_ms": decode_cpu * 1000,
        "decode_call_p95_ms": quantile(calls, 0.95) * 1000,
        "decode_call_max_ms": max(calls, default=0) * 1000,
        "feed_lateness_p95_ms": quantile(lag, 0.95) * 1000,
        "feed_lateness_max_ms": max(lag, default=0) * 1000,
        "unfed_elapsed_audio_peak_ms": max(0, backlog_peak) * 1000,
        "gold_reference_supplied": reference is not None,
        "accuracy": accuracy(reference, result) if reference is not None else None,
        "public_result_sha256": hashlib.sha256(result.encode()).hexdigest(),
        "public_result_chars": len(result),
    }
    return {k: round(v, 3) if isinstance(v, float) else v
            for k, v in summary.items()}, normalized(result)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("model", "tokens", "wav"):
        parser.add_argument("--" + name, required=True)
        parser.add_argument("--" + name + "-sha256", required=True)
    reference_group = parser.add_mutually_exclusive_group(required=True)
    reference_group.add_argument("--public-reference")
    reference_group.add_argument("--baseline-output-sha256")
    parser.add_argument("--public-input-confirmed", action="store_true", required=True)
    parser.add_argument("--schedule-ms", type=int, nargs="+", choices=(20, 160),
                        default=[20, 160, 160, 20])
    args = parser.parse_args(argv)
    require(platform.system() == "Linux" and platform.machine() == "aarch64",
            "NOT_LINUX_AARCH64")
    require(args.public_input_confirmed and 0 < len(args.schedule_ms) <= 4,
            "INPUT_DECLARATION_INVALID")
    if args.public_reference is not None:
        require(0 < len(normalized(args.public_reference)) <= 500,
                "REFERENCE_INVALID")
    else:
        require(re.fullmatch(r"[0-9a-fA-F]{64}", args.baseline_output_sha256)
                is not None, "BASELINE_HASH_INVALID")
    model = pinned_file(args.model, args.model_sha256, 64 * 1024 * 1024)
    tokens = pinned_file(args.tokens, args.tokens_sha256, 1024 * 1024)
    wav_path = pinned_file(args.wav, args.wav_sha256, 1024 * 1024)
    with wave.open(str(wav_path), "rb") as wav:
        require((wav.getnchannels(), wav.getsampwidth(), wav.getframerate(),
                 wav.getnframes(), wav.getcomptype()) ==
                (1, 2, SAMPLE_RATE, PUBLIC_WAV_SAMPLES, "NONE"),
                "PUBLIC_WAV_FORMAT_MISMATCH")
        pcm = wav.readframes(wav.getnframes())
    require(len(pcm) == PUBLIC_WAV_SAMPLES * 2, "WAV_TRUNCATED")

    import numpy as np
    import sherpa_onnx
    import resource
    require(sherpa_onnx.__version__ == VERSION, "SHERPA_VERSION_MISMATCH")
    samples = np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768.0
    tail = np.zeros(TAIL_SAMPLES, dtype=np.float32)
    load_start, load_cpu = time.perf_counter(), time.process_time()
    recognizer = sherpa_onnx.OnlineRecognizer.from_zipformer2_ctc(
        tokens=str(tokens), model=str(model), num_threads=1,
        sample_rate=SAMPLE_RATE, feature_dim=80,
        enable_endpoint_detection=False, decoding_method="greedy_search",
        provider="cpu", debug=False)
    load_wall_ms = (time.perf_counter() - load_start) * 1000
    load_cpu_ms = (time.process_time() - load_cpu) * 1000
    rounds, results = [], []
    for ordinal, feed_ms in enumerate(args.schedule_ms, 1):
        metrics, result = run_round(recognizer, samples, tail, feed_ms,
                                    args.public_reference)
        metrics.update({"ordinal": ordinal, "first_model_decode_round": ordinal == 1})
        if args.baseline_output_sha256 is not None:
            metrics["baseline_exact_text_sha256_match"] = (
                metrics["public_result_sha256"] == args.baseline_output_sha256.lower())
        rounds.append(metrics)
        results.append(result)
    return {
        "schema_version": 1, "status": "MEASURED", "sherpa_version": VERSION,
        "model_sha256": args.model_sha256.lower(),
        "tokens_sha256": args.tokens_sha256.lower(),
        "wav_sha256": args.wav_sha256.lower(),
        "reference_sha256": (hashlib.sha256(args.public_reference.encode()).hexdigest()
                             if args.public_reference is not None else None),
        "baseline_output_sha256": args.baseline_output_sha256,
        "baseline_is_gold": False,
        "asr_threads": 1, "recognizer_constructions": 1,
        "vad_executed": False, "endpoint_source": "PUBLIC_WAV_END",
        "microphone_opened": False, "production_accessed": False,
        "load_wall_ms": round(load_wall_ms, 3), "load_cpu_ms": round(load_cpu_ms, 3),
        "process_peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "all_normalized_results_equal": len(set(results)) == 1,
        "rounds": rounds,
    }


if __name__ == "__main__":
    try:
        print(json.dumps(main(), ensure_ascii=True, allow_nan=False))
    except ProbeRefusal as exc:
        print(json.dumps({"status": "REFUSED", "code": str(exc)}))
        sys.exit(2)
    except KeyboardInterrupt:
        print('{"status":"INTERRUPTED"}')
        sys.exit(130)
    except Exception:
        # Never emit arbitrary native/path/text exception messages.
        print('{"status":"ERROR","code":"PROBE_FAILED"}')
        sys.exit(3)
