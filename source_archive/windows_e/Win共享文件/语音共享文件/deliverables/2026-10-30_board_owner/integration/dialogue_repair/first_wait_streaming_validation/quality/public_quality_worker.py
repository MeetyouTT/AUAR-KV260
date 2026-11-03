"""Root-run public synthetic ASR comparison, never a live-dialogue benchmark.

Require an external root-owned process deadline. Only the pinned synthetic
manifest/WAVs, reviewed model files, and optionally pinned adapter are read.
No microphone, network, Store, subprocess, production write, or model download.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import re
import sys
import time
import types
import unicodedata
import wave

sys.dont_write_bytecode = True
WAV_ROOT = Path("/home/root/aura-public-streaming-validation-20261031")
TEXT_SET_SHA = "e41dc194e00e3b76c40bdf4ee96cadf364e088a9c2c1f180ff872d6e77f72ede"
ADAPTER_SHA = "4edb865881c887d6a290a02e078e14386bd95d017b79820b143b5a1e329997c3"
PINS = {
    "paraformer": (
        "f36a0433bcf096bd6d6f11b80a3ac8bed110bdca632fe0d731df8d1a84475945",
        "59aba8873a2ed1e122c25fee421e25f283b63290efbde85c1f01a853d83cb6e6"),
    "ctc": (
        "68c9c943840f7d9cf3e8a4970ba50f404feb5277f611fa82b7e72267786fa84a",
        "6fed8c6c248516f38e7faa19404b57413e8ce259f1cbc1fa4aebc86eac32fdfd"),
}
CASES = (
    ("S01", "你好，请用两句话介绍你自己。", ("两句", "介绍", "自己")),
    ("S02", "我叫林悦，树林的林，喜悦的悦。", ("林悦", "树林", "喜悦")),
    ("S03", "桌上有三本书，杯子里有二百五十毫升水。", ("三本书", "二百五十", "毫升")),
    ("S04", "我没有关灯，也没有锁门。", ("没有关灯", "没有锁门")),
    ("S05", "更正一下，会议改到下午四点，不是三点。", ("更正", "下午四点", "不是三点")),
    ("S06", "请记住，我把蓝色钥匙放在书架第二层。", ("记住", "蓝色钥匙", "书架第二层")),
    ("S07", "我刚才把蓝色钥匙放在哪里？", ("刚才", "蓝色钥匙", "哪里")),
    ("S08", "请忘记我刚才说的钥匙位置。", ("忘记", "刚才", "钥匙位置")),
)


class Refused(Exception):
    pass


def require(ok, code):
    if not ok:
        raise Refused(code)


def public_path(raw):
    require(isinstance(raw, str), "PUBLIC_PATH_INVALID")
    path = Path(raw)
    require(path.is_absolute(), "PUBLIC_PATH_INVALID")
    # Reject lexical traversal and every symlink, including parent directories.
    require(".." not in path.parts and not any(p.is_symlink() for p in (path, *path.parents)),
            "PUBLIC_PATH_INVALID")
    try:
        path.resolve().relative_to(WAV_ROOT.resolve())
    except ValueError:
        raise Refused("PUBLIC_PATH_OUTSIDE_ROOT")
    require(path.is_file(), "PUBLIC_FILE_MISSING")
    return path


def pinned_bytes(path, expected, maximum):
    require(isinstance(expected, str) and re.fullmatch(r"[0-9a-f]{64}", expected),
            "HASH_INVALID")
    require(path.is_file() and not path.is_symlink(), "PINNED_FILE_INVALID")
    require(0 < path.stat().st_size <= maximum, "PINNED_FILE_SIZE_INVALID")
    data = path.read_bytes()
    require(len(data) <= maximum and hashlib.sha256(data).hexdigest() == expected,
            "PIN_MISMATCH")
    return data


def verify_model_resource(path, expected, maximum):
    require(path.is_file() and not path.is_symlink()
            and 0 < path.stat().st_size <= maximum, "MODEL_RESOURCE_INVALID")
    digest, size = hashlib.sha256(), 0
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            size += len(block)
            require(size <= maximum, "MODEL_RESOURCE_INVALID")
            digest.update(block)
    require(digest.hexdigest() == expected, "MODEL_PIN_MISMATCH")


def normalized(text):
    return "".join(c for c in unicodedata.normalize("NFKC", text).casefold()
                   if c.isalnum())


def character_error(reference, hypothesis):
    left, right = normalized(reference), normalized(hypothesis)
    require(bool(left) and len(right) <= 1000, "TEXT_SIZE_INVALID")
    row = list(range(len(right) + 1))
    for i, a in enumerate(left, 1):
        nxt = [i]
        for j, b in enumerate(right, 1):
            nxt.append(min(nxt[-1] + 1, row[j] + 1, row[j - 1] + (a != b)))
        row = nxt
    return {"reference_chars": len(left), "hypothesis_chars": len(right),
            "edit_distance": row[-1], "cer": round(row[-1] / len(left), 6),
            "normalized_exact": left == right}


def validate_manifest(manifest):
    require(isinstance(manifest, dict)
            and manifest.get("source_texts_sha256") == TEXT_SET_SHA
            and manifest.get("public_synthetic") is True
            and manifest.get("intended_not_human_verified") is True,
            "MANIFEST_PROVENANCE_INVALID")
    rows = manifest.get("cases")
    require(isinstance(rows, list) and len(rows) == len(CASES), "CASE_SET_INVALID")
    audio, seen_paths = [], set()
    for row, (case_id, text, spans) in zip(rows, CASES):
        require(isinstance(row, dict) and row.get("id") == case_id
                and row.get("reference_text") == text, "CASE_TEXT_INVALID")
        require(type(row.get("samples")) is int and 0 < row["samples"] <= 320000
                and type(row.get("rate")) is int and row["rate"] == 16000,
                "WAV_DECLARATION_INVALID")
        path = public_path(row.get("wav_path"))
        require(str(path.resolve()) not in seen_paths, "WAV_PATH_REUSED")
        seen_paths.add(str(path.resolve()))
        data = pinned_bytes(path, row.get("sha256"), 1024 * 1024)
        try:
            with wave.open(io.BytesIO(data), "rb") as wav:
                require((wav.getnchannels(), wav.getsampwidth(), wav.getframerate(),
                         wav.getnframes(), wav.getcomptype()) ==
                        (1, 2, 16000, row["samples"], "NONE"), "WAV_FORMAT_INVALID")
                pcm = wav.readframes(row["samples"])
        except (wave.Error, EOFError):
            raise Refused("WAV_FORMAT_INVALID")
        require(len(pcm) == row["samples"] * 2 and any(pcm), "WAV_PCM_INVALID")
        audio.append((row, spans, pcm))
    return audio


@contextmanager
def quiet_native():
    """Discard native/Python runtime logs; verified public results go to JSON."""
    sys.stdout.flush()
    sys.stderr.flush()
    saved_out, saved_err = os.dup(1), os.dup(2)
    sink = os.open(os.devnull, os.O_WRONLY)
    try:
        os.dup2(sink, 1)
        os.dup2(sink, 2)
        yield
    finally:
        sys.stdout.flush()
        sys.stderr.flush()
        os.dup2(saved_out, 1)
        os.dup2(saved_err, 2)
        os.close(saved_out)
        os.close(saved_err)
        os.close(sink)


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise Refused("ARGUMENTS_INVALID")


def main(argv=None):
    parser = Parser(description=__doc__)
    parser.add_argument("--engine", required=True, choices=("paraformer", "ctc"))
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--model-dir", required=True)
    parser.add_argument("--paraformer-source")
    parser.add_argument("--external-deadline-managed", action="store_true", required=True)
    parser.add_argument("--max-seconds", type=int, default=180)
    args = parser.parse_args(argv)
    require(platform.system() == "Linux" and platform.machine() == "aarch64",
            "NOT_LINUX_AARCH64")
    require(args.external_deadline_managed and 30 <= args.max_seconds <= 300,
            "DEADLINE_REQUIRED")
    require((args.engine == "paraformer") == bool(args.paraformer_source),
            "ADAPTER_ARGUMENT_INVALID")
    deadline = time.monotonic() + args.max_seconds
    manifest = json.loads(pinned_bytes(public_path(args.manifest),
                                     args.manifest_sha256, 65536))
    audio = validate_manifest(manifest)
    directory = Path(args.model_dir)
    require(directory.is_absolute() and directory.is_dir()
            and not any(p.is_symlink() for p in (directory, *directory.parents))
            and "win共享文件" not in str(directory.resolve()).casefold(),
            "MODEL_PATH_INVALID")
    model_sha, tokens_sha = PINS[args.engine]
    verify_model_resource(directory / "model.int8.onnx", model_sha, 300 * 1024 * 1024)
    verify_model_resource(directory / "tokens.txt", tokens_sha, 1024 * 1024)
    adapter = None
    if args.engine == "paraformer":
        path = Path(args.paraformer_source)
        require(path.is_absolute(), "ADAPTER_PATH_INVALID")
        source = pinned_bytes(path, ADAPTER_SHA, 32768)
        module = types.ModuleType("public_pinned_paraformer_adapter")
        exec(compile(source, "<pinned_public_paraformer_adapter>", "exec"), module.__dict__)
        adapter = module.BoardParaformer
    results = []
    with quiet_native():
        import numpy as np
        import sherpa_onnx
        require(sherpa_onnx.__version__ == "1.13.8", "SHERPA_VERSION_MISMATCH")
        load_start, load_cpu = time.perf_counter(), time.process_time()
        if args.engine == "paraformer":
            engine = adapter(str(directory), model_sha256=model_sha,
                             tokens_sha256=tokens_sha, num_threads=3)
        else:
            engine = sherpa_onnx.OnlineRecognizer.from_zipformer2_ctc(
                tokens=str(directory / "tokens.txt"),
                model=str(directory / "model.int8.onnx"), num_threads=1,
                sample_rate=16000, feature_dim=80, decoding_method="greedy_search",
                enable_endpoint_detection=False, provider="cpu", debug=False)
        load_ms = (time.perf_counter() - load_start) * 1000
        load_cpu_ms = (time.process_time() - load_cpu) * 1000
        for ordinal, (row, spans, pcm) in enumerate(audio, 1):
            require(time.monotonic() < deadline, "SOFT_DEADLINE_EXCEEDED")
            start, cpu_start = time.perf_counter(), time.process_time()
            if args.engine == "paraformer":
                hypothesis = engine.transcribe(pcm, sample_rate=16000, deadline=deadline)
            else:
                samples = np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768.0
                stream = engine.create_stream()
                stream.accept_waveform(16000, samples)
                stream.accept_waveform(16000, np.zeros(10560, dtype=np.float32))
                stream.input_finished()
                calls = 0
                while engine.is_ready(stream):
                    require(time.monotonic() < deadline and calls < 2000,
                            "SOFT_DEADLINE_EXCEEDED")
                    engine.decode_stream(stream)
                    calls += 1
                hypothesis = engine.get_result(stream)
            wall_ms = (time.perf_counter() - start) * 1000
            cpu_ms = (time.process_time() - cpu_start) * 1000
            require(time.monotonic() < deadline, "SOFT_DEADLINE_EXCEEDED")
            require(isinstance(hypothesis, str) and len(hypothesis) <= 1000,
                    "HYPOTHESIS_INVALID")
            results.append({
                "id": row["id"], "ordinal": ordinal,
                "first_model_decode": ordinal == 1,
                "reference": row["reference_text"], "hypothesis": hypothesis,
                "wav_sha256": row["sha256"], "samples": row["samples"], "rate": 16000,
                "offline_decode_wall_ms": round(wall_ms, 3),
                "offline_decode_cpu_ms": round(cpu_ms, 3),
                "intended_text_character_error": character_error(row["reference_text"], hypothesis),
                "critical_spans_literal_match": [
                    {"span": span, "present": span in hypothesis} for span in spans],
                "semantic_acceptance_passed": None,
            })
    edits = sum(r["intended_text_character_error"]["edit_distance"] for r in results)
    chars = sum(r["intended_text_character_error"]["reference_chars"] for r in results)
    return {
        "schema_version": 1, "status": "MEASURED_NOT_ACCEPTED", "engine": args.engine,
        "mode": "offline_quality_not_realtime_latency", "sherpa_version": "1.13.8",
        "asr_threads": 3 if args.engine == "paraformer" else 1,
        "recognizer_constructions": 1, "manifest_sha256": args.manifest_sha256,
        "source_texts_sha256": TEXT_SET_SHA, "model_sha256": model_sha,
        "tokens_sha256": tokens_sha,
        "adapter_sha256": ADAPTER_SHA if args.engine == "paraformer" else None,
        "public_synthetic": True, "intended_not_human_verified": True,
        "gold_human_reference": False, "semantic_acceptance_passed": None,
        "ctc_tail_zero_samples": 10560 if args.engine == "ctc" else 0,
        "load_wall_ms": round(load_ms, 3), "load_cpu_ms": round(load_cpu_ms, 3),
        "aggregate_intended_text_cer": round(edits / chars, 6),
        "aggregate_edit_distance": edits, "aggregate_reference_chars": chars,
        "production_written": False, "microphone_opened": False,
        "results": results,
    }


if __name__ == "__main__":
    try:
        print(json.dumps(main(), ensure_ascii=False, allow_nan=False))
    except KeyboardInterrupt:
        print('{"status":"INTERRUPTED"}')
        sys.stderr.write("INTERRUPTED\n")
        sys.exit(130)
    except Exception as error:
        code = str(error) if isinstance(error, Refused) else "QUALITY_WORKER_FAILED"
        print(json.dumps({"status": "REFUSED_OR_FAILED", "code": code}))
        sys.stderr.write(code + "\n")
        sys.exit(2)
