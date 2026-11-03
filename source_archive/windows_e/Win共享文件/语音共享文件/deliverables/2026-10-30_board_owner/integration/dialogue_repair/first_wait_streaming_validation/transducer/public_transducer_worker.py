"""Isolated 1-thread small bilingual transducer public quality/realtime probe.

Root alone supplies an externally supervised deadline and hardware window.
Reuse the frozen quality helper's exact 8-case/public WAV validation unchanged.
No downloads, microphone, network, database, production writes or subprocesses.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
import sys
import time
import types

sys.dont_write_bytecode = True
HELPER_SHA = "293b23f5dd350e5f4d1cce1489120a44b2c4d743c1534080da496f3f58407176"
SOURCE_REVISION = "e2382758de9a0219b4efe682b95af30b399db3b8"
FILES = {
    "encoder": ("encoder-epoch-99-avg-1.int8.onnx", 42980793,
                "db6f51551762e40e549166fe041ea3e45464370b595e9ad23f06478ec3794fbb"),
    "decoder": ("decoder-epoch-99-avg-1.onnx", 13877276,
                "89be509a83175261695bdef5fd1c7b9ab1129a663d1284e7ba9f8507b21e0906"),
    "joiner": ("joiner-epoch-99-avg-1.int8.onnx", 3228485,
               "bdda356d6f9b8c2d7cee9ee0e26075fa537490f7fd06520be408d287073667b9"),
    "tokens": ("tokens.txt", 56317,
               "a8e0e4ec53810e433789b54a5c0134a7eaa2ffca595a6334d54c00da858841d3"),
}


class Refused(Exception):
    pass


def require(ok, code):
    if not ok:
        raise Refused(code)


def load_quality_helper(path):
    path = Path(path)
    require(path.is_absolute() and path.is_file() and not path.is_symlink()
            and path.stat().st_size < 65536, "QUALITY_HELPER_PATH_INVALID")
    source = path.read_bytes()
    require(hashlib.sha256(source).hexdigest() == HELPER_SHA, "QUALITY_HELPER_PIN_MISMATCH")
    module = types.ModuleType("frozen_public_quality_helper")
    exec(compile(source, "<frozen_public_quality_helper>", "exec"), module.__dict__)
    return module


def percentile(values, fraction):
    return sorted(values)[max(0, math.ceil(len(values) * fraction) - 1)] if values else 0


def decode_round(engine, samples, tail, *, realtime, feed_ms, deadline,
                 clock=time.perf_counter, sleep=time.sleep, cpu=time.process_time,
                 monotonic=time.monotonic):
    """Same finalization in both modes; realtime preserves source arrival times."""
    stream = engine.create_stream()
    started, cpu_started = clock(), cpu()
    duration = len(samples) / 16000
    accepted, backlog_peak = 0, 0.0
    lag, calls = [], []
    decode_cpu = 0.0
    source_end = started + duration

    def backlog():
        nonlocal backlog_peak
        if realtime:
            backlog_peak = max(backlog_peak,
                min(duration, max(0.0, clock() - started)) - accepted / 16000)

    def drain():
        nonlocal decode_cpu
        while engine.is_ready(stream):
            require(monotonic() < deadline and len(calls) < 2000,
                    "SOFT_DEADLINE_EXCEEDED")
            before, cpu_before = clock(), cpu()
            engine.decode_stream(stream)
            calls.append(clock() - before)
            decode_cpu += cpu() - cpu_before
            backlog()

    if realtime:
        require(feed_ms in (20, 160), "FEED_MS_INVALID")
        stride = 16000 * feed_ms // 1000
        for offset in range(0, len(samples), stride):
            stop = min(offset + stride, len(samples))
            due = started + stop / 16000
            while clock() < due:
                require(monotonic() < deadline, "SOFT_DEADLINE_EXCEEDED")
                sleep(max(0.0, due - clock()))
            backlog()
            lag.append(max(0.0, clock() - due))
            stream.accept_waveform(16000, samples[offset:stop])
            accepted = stop
            input_accepted = clock()
            drain()
    else:
        stream.accept_waveform(16000, samples)
        accepted = len(samples)
        input_accepted = clock()

    flush_started = clock()
    stream.accept_waveform(16000, tail)
    stream.input_finished()
    drain()
    hypothesis = engine.get_result(stream)
    ended, cpu_ended = clock(), cpu()
    require(monotonic() < deadline, "SOFT_DEADLINE_EXCEEDED")
    require(isinstance(hypothesis, str) and len(hypothesis) <= 1000,
            "HYPOTHESIS_INVALID")
    stats = {
        "samples": accepted, "wave_duration_ms": duration * 1000,
        "round_wall_ms": (ended - started) * 1000,
        "round_cpu_ms": (cpu_ended - cpu_started) * 1000,
        "decode_calls": len(calls), "decode_wall_ms": sum(calls) * 1000,
        "decode_cpu_ms": decode_cpu * 1000,
        "decode_call_p95_ms": percentile(calls, 0.95) * 1000,
        "decode_call_max_ms": max(calls, default=0) * 1000,
        "tail_zero_samples": len(tail), "tail_wait_ms": 0,
        "feed_ms": feed_ms if realtime else None,
        "feed_lateness_p95_ms": percentile(lag, 0.95) * 1000 if realtime else None,
        "feed_lateness_max_ms": max(lag, default=0) * 1000 if realtime else None,
        "unfed_elapsed_audio_peak_ms": max(0.0, backlog_peak) * 1000 if realtime else None,
        "final_after_scheduled_input_end_ms": (ended - source_end) * 1000 if realtime else None,
        "final_after_last_real_accept_ms": (ended - input_accepted) * 1000 if realtime else None,
        "flush_wall_ms": (ended - flush_started) * 1000 if realtime else None,
    }
    return hypothesis, {k: round(v, 3) if isinstance(v, float) else v for k, v in stats.items()}


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise Refused("ARGUMENTS_INVALID")


def main(argv=None):
    parser = Parser(description=__doc__)
    parser.add_argument("--mode", required=True, choices=("quality", "realtime"))
    parser.add_argument("--quality-helper", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--feed-ms", type=int, choices=(20, 160), default=160)
    parser.add_argument("--max-seconds", type=int, default=180)
    parser.add_argument("--external-deadline-managed", action="store_true", required=True)
    args = parser.parse_args(argv)
    require(platform.system() == "Linux" and platform.machine() == "aarch64",
            "NOT_LINUX_AARCH64")
    require(args.external_deadline_managed and 30 <= args.max_seconds <= 300,
            "DEADLINE_REQUIRED")
    deadline = time.monotonic() + args.max_seconds
    helper = load_quality_helper(args.quality_helper)
    try:
        manifest = json.loads(helper.pinned_bytes(helper.public_path(args.manifest),
                                                 args.manifest_sha256, 65536))
        audio = helper.validate_manifest(manifest)
        directory = Path(args.model_dir)
        require(directory.is_absolute() and directory.is_dir()
                and not any(p.is_symlink() for p in (directory, *directory.parents))
                and "win共享文件" not in str(directory.resolve()).casefold(),
                "MODEL_PATH_INVALID")
        paths = {}
        for role, (name, size, sha) in FILES.items():
            path = directory / name
            require(path.is_file() and path.stat().st_size == size, "MODEL_SIZE_MISMATCH")
            helper.verify_model_resource(path, sha, size)
            paths[role] = str(path)
        results = []
        with helper.quiet_native():
            import numpy as np
            import sherpa_onnx
            require(sherpa_onnx.__version__ == "1.13.8", "SHERPA_VERSION_MISMATCH")
            load_start, load_cpu = time.perf_counter(), time.process_time()
            engine = sherpa_onnx.OnlineRecognizer.from_transducer(
                **paths, num_threads=1, sample_rate=16000, feature_dim=80,
                decoding_method="greedy_search", enable_endpoint_detection=False,
                provider="cpu", debug=False)
            load_ms = (time.perf_counter() - load_start) * 1000
            load_cpu_ms = (time.process_time() - load_cpu) * 1000
            for ordinal, (row, spans, pcm) in enumerate(audio, 1):
                require(time.monotonic() < deadline, "SOFT_DEADLINE_EXCEEDED")
                samples = np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768.0
                text, stats = decode_round(
                    engine, samples, np.zeros(10560, dtype=np.float32),
                    realtime=args.mode == "realtime", feed_ms=args.feed_ms,
                    deadline=deadline)
                results.append({"id": row["id"], "ordinal": ordinal,
                    "first_model_decode": ordinal == 1,
                    "reference": row["reference_text"], "hypothesis": text,
                    "wav_sha256": row["sha256"], "rate": 16000,
                    "intended_text_character_error": helper.character_error(row["reference_text"], text),
                    "critical_spans_literal_match": [{"span": span, "present": span in text} for span in spans],
                    "semantic_acceptance_passed": None, "timing": stats})
        edits = sum(r["intended_text_character_error"]["edit_distance"] for r in results)
        chars = sum(r["intended_text_character_error"]["reference_chars"] for r in results)
        return {
            "schema_version": 1, "status": "MEASURED_NOT_ACCEPTED",
            "engine": "small_bilingual_zipformer_transducer_2023_02_16",
            "mode": "realtime_public_wave_pacing" if args.mode == "realtime" else "offline_quality_not_realtime_latency",
            "decode_chunk_len_from_pinned_export": 32, "sherpa_version": "1.13.8",
            "source_revision": SOURCE_REVISION, "quality_helper_sha256": HELPER_SHA,
            "source_texts_sha256": helper.TEXT_SET_SHA, "manifest_sha256": args.manifest_sha256,
            "model_file_sha256": {role: info[2] for role, info in FILES.items()},
            "asr_threads": 1, "recognizer_constructions": 1,
            "load_wall_ms": round(load_ms, 3), "load_cpu_ms": round(load_cpu_ms, 3),
            "public_synthetic": True, "intended_not_human_verified": True,
            "gold_human_reference": False, "semantic_acceptance_passed": None,
            "endpoint_source": "PUBLIC_WAV_END", "vad_executed": False,
            "microphone_opened": False, "production_written": False,
            "aggregate_intended_text_cer": round(edits / chars, 6),
            "aggregate_edit_distance": edits, "aggregate_reference_chars": chars,
            "results": results,
        }
    except helper.Refused as error:
        raise Refused(str(error))


if __name__ == "__main__":
    try:
        print(json.dumps(main(), ensure_ascii=False, allow_nan=False))
    except KeyboardInterrupt:
        print('{"status":"INTERRUPTED"}')
        sys.stderr.write("INTERRUPTED\n")
        sys.exit(130)
    except Exception as error:
        code = str(error) if isinstance(error, Refused) else "TRANSDUCER_WORKER_FAILED"
        print(json.dumps({"status": "REFUSED_OR_FAILED", "code": code}))
        sys.stderr.write(code + "\n")
        sys.exit(2)
