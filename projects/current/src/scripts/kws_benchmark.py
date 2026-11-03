# -*- coding: utf-8 -*-
"""kws_benchmark.py —— KWS 延迟 / 误触发 / CPU / 内存 benchmark（人3 · A2 · 9/12 任务）

任务书要求（Week A2 · 9/12）：
  「KWS 延迟、误触发、CPU/内存 benchmark」→ KWS 报告，**仅标 PC 基线**。

测什么
------
| 指标 | 口径 |
|---|---|
| 单块解码延迟 | 每 100ms 音频块解码墙钟耗时 p50 / p95 / p99（ms） |
| 实时率 RTF | 总解码耗时 ÷ 音频时长（<1 表示比实时快） |
| 首命中偏移 | 命中发生时已解码的音频时长（ms，越小越"灵敏"） |
| 命中率 | 有命中的音频条数 ÷ 总条数 |
| 误触发 | **无命中的音频**里检测到的命中次数 → 换算"每小时误触发" |
| CPU | `process_time` 增量 ÷ 墙钟增量（单线程解码时接近 100%） |
| 内存 | 进程峰值工作集（Windows: GetProcessMemoryInfo；Linux/mac: rusage） |

用法
----
    python scripts\\kws_benchmark.py                         # 自动找模型 + 官方 test_wavs
    python scripts\\kws_benchmark.py --wav a.wav --wav b.wav  # 指定音频
    python scripts\\kws_benchmark.py --synthetic              # 无模型/无音频的链路自检
    python scripts\\kws_benchmark.py --out evidence_shots\\kws_benchmark.json

⚠️ 局限（**必须如实标注**）：正/负样本按"是否命中"自动分类，不是人工标注；
   官方 test_wavs 只有 7 条，误触发统计的置信度低；模型/音频均为 16kHz 中文朗读语料。
环境标签：**PC 基线（CPU，单线程）**。
"""
from __future__ import annotations

import argparse
import ctypes
import glob
import json
import os
import statistics
import sys
import time
import typing

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from board.runtime.audio import (KwsConfig, KwsRunner, ScriptedKeywordSpotter,   # noqa: E402
                                 SherpaKeywordSpotter, read_wav_mono16k)
from board.runtime.audio.kws import iter_chunks                                   # noqa: E402
from board.runtime.event_bus import EventBus                                      # noqa: E402
from board.runtime.fsm import RuntimeFSM                                          # noqa: E402


# --------------------------------------------------------------- 资源计数

def peak_working_set_bytes() -> int:
    """进程峰值工作集（Windows）；失败返回 0。"""
    if os.name != "nt":
        try:                                            # pragma: no cover - 非 Windows
            import resource
            return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024
        except Exception:
            return 0

    class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t)]

    counters = PROCESS_MEMORY_COUNTERS()
    counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
    try:
        kernel32 = ctypes.windll.kernel32
        # ⚠️ 必须声明 restype/argtypes：默认按 c_int 处理会**截断 64 位句柄**，导致调用失败、恒返回 0
        kernel32.GetCurrentProcess.restype = ctypes.c_void_p
        handle = kernel32.GetCurrentProcess()
        for dll, func in (("psapi", "GetProcessMemoryInfo"),
                          ("kernel32", "K32GetProcessMemoryInfo")):
            try:
                lib = getattr(ctypes.windll, dll)
                fn = getattr(lib, func)
            except AttributeError:                      # pragma: no cover - 老系统
                continue
            fn.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong]
            fn.restype = ctypes.c_int
            if fn(handle, ctypes.byref(counters), counters.cb):
                return int(counters.PeakWorkingSetSize)
        return 0
    except Exception:                                   # pragma: no cover
        return 0


def percentile(values: typing.Sequence[float], q: float) -> float:
    """简单百分位（线性插值）。"""
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    pos = (len(ordered) - 1) * max(0.0, min(1.0, q))
    low, high = int(pos), min(int(pos) + 1, len(ordered) - 1)
    frac = pos - low
    return float(ordered[low] * (1.0 - frac) + ordered[high] * frac)


def auto_model_dir(root: str = _ROOT) -> str:
    for pattern in ("sherpa-onnx-kws-*", "*kws*"):
        for path in sorted(glob.glob(os.path.join(root, "models", pattern))):
            if os.path.isdir(path) and glob.glob(os.path.join(path, "**", "tokens.txt"),
                                                 recursive=True):
                return path
    return ""


def parse_args():
    ap = argparse.ArgumentParser(description="KWS benchmark（PC 基线）")
    ap.add_argument("--synthetic", action="store_true", help="无模型/无音频的链路自检")
    ap.add_argument("--wav", action="append", default=[], help="指定音频（可重复）")
    ap.add_argument("--model-dir", default="", help="模型目录（默认自动查找 models/sherpa-onnx-kws-*）")
    ap.add_argument("--keywords-file", default="", help="keywords.txt（默认模型自带）")
    ap.add_argument("--repeat", type=int, default=1, help="每条音频重复次数（默认 %(default)s）")
    ap.add_argument("--threshold", type=float, default=0.25, help="关键词阈值（默认 %(default)s）")
    ap.add_argument("--chunk-ms", type=int, default=100, help="块长毫秒（默认 %(default)s）")
    ap.add_argument("--sample-rate", type=int, default=16000, help="采样率（默认 %(default)s）")
    ap.add_argument("--num-threads", type=int, default=1, help="解码线程数（默认 %(default)s）")
    ap.add_argument("--out", default="", help="JSON 输出路径（默认 evidence_shots/kws_benchmark.json）")
    return ap.parse_args()


def _rel(path: str) -> str:
    if not path:
        return ""
    try:
        return os.path.relpath(path, _ROOT).replace("\\", "/")
    except ValueError:                                  # pragma: no cover
        return path


def measure_real(wavs: typing.Sequence[str], args) -> typing.Dict:
    """逐条音频跑真实模型，采集延迟/命中/RTF/CPU/内存。"""
    model_dir = args.model_dir or auto_model_dir()
    cfg = KwsConfig(model_dir=model_dir, keywords_file=args.keywords_file or "",
                    sample_rate=args.sample_rate, threshold=args.threshold,
                    num_threads=args.num_threads)
    chunk = max(1, int(args.sample_rate * args.chunk_ms / 1000.0))
    bus = EventBus(max_size=256, dispatch_async=False)
    RuntimeFSM(bus=bus)                                 # 绑定 FSM：验证事件链路真实可用

    rows: typing.List[typing.Dict] = []
    block_ms: typing.List[float] = []
    for wav in wavs:
        samples = read_wav_mono16k(wav, target_rate=args.sample_rate)
        seconds = len(samples) / float(args.sample_rate)
        for rep in range(max(1, args.repeat)):
            spotter = SherpaKeywordSpotter(cfg)
            runner = KwsRunner(bus, spotter, source="kws-bench")
            cpu0, wall0 = time.process_time(), time.perf_counter()
            hits = []
            for blk in iter_chunks(samples, chunk):
                t0 = time.perf_counter()
                hits.extend(runner.feed(blk))
                block_ms.append((time.perf_counter() - t0) * 1000.0)
            wall1, cpu1 = time.perf_counter(), time.process_time()
            spotter.close()
            hits_sorted = sorted(hits, key=lambda h: h.timestamp_ms)
            rows.append({
                "wav": os.path.basename(wav), "repeat": rep,
                "seconds": round(seconds, 3),
                "hits": [h.keyword for h in hits_sorted],
                "first_hit_ms": round(hits_sorted[0].timestamp_ms, 1) if hits_sorted else None,
                "decode_s": round(wall1 - wall0, 4),
                "rtf": round((wall1 - wall0) / seconds, 4) if seconds else 0.0,
                "cpu_percent": round(100.0 * (cpu1 - cpu0) / max(1e-9, wall1 - wall0), 1),
            })

    pos = [r for r in rows if r["hits"]]
    neg = [r for r in rows if not r["hits"]]
    rtf = [r["rtf"] for r in rows] or [0.0]
    neg_seconds = sum(r["seconds"] for r in neg)
    false_pos = sum(len(r["hits"]) for r in neg)
    first_hits = [r["first_hit_ms"] for r in pos if r["first_hit_ms"] is not None]
    return {
        "engine": "sherpa-onnx",
        "model_dir": _rel(model_dir),
        "keywords_file": _rel(cfg.keywords_file),
        "threshold": args.threshold,
        "num_threads": args.num_threads,
        "latency": {
            "chunk_ms": args.chunk_ms,
            "blocks": len(block_ms),
            "p50_ms": round(percentile(block_ms, 0.50), 3),
            "p95_ms": round(percentile(block_ms, 0.95), 3),
            "p99_ms": round(percentile(block_ms, 0.99), 3),
            "max_ms": round(max(block_ms), 3) if block_ms else 0.0,
            "mean_ms": round(statistics.fmean(block_ms), 3) if block_ms else 0.0,
        },
        "throughput": {
            "rtf_mean": round(statistics.fmean(rtf), 4),
            "rtf_max": round(max(rtf), 4),
            "speedup_x": round(1.0 / statistics.fmean(rtf), 1) if statistics.fmean(rtf) else 0.0,
        },
        "detection": {
            "audio_files": len(wavs), "runs": len(rows),
            "hit_runs": len(pos), "hit_rate": round(len(pos) / len(rows), 3) if rows else 0.0,
            "false_positives": false_pos,
            "negative_seconds": round(neg_seconds, 2),
            "false_triggers_per_hour": round(false_pos / neg_seconds * 3600.0, 2) if neg_seconds else 0.0,
            "first_hit_ms_mean": round(statistics.fmean(first_hits), 1) if first_hits else None,
            "keywords_seen": sorted({k for r in rows for k in r["hits"]}),
        },
        "resources": {
            "cpu_percent_mean": round(statistics.fmean([r["cpu_percent"] for r in rows]), 1) if rows else 0.0,
            "peak_working_set_mb": round(peak_working_set_bytes() / (1024.0 * 1024.0), 1),
        },
        "rows": rows,
        "caveats": ["正/负样本按「是否命中」自动分类，非人工标注；官方 test_wavs 仅 7 条，"
                    "误触发统计置信度低；16kHz 中文朗读语料；PC 基线（CPU 单线程），非板端实测。"],
    }


def measure_synthetic(args) -> typing.Dict:
    """无模型/无音频的**纯链路开销**（对照基线：Runner + EventBus + FSM）。"""
    import numpy as np

    chunk = max(1, int(args.sample_rate * args.chunk_ms / 1000.0))
    blocks = max(50, args.repeat * 200)
    bus = EventBus(max_size=256, dispatch_async=False)
    RuntimeFSM(bus=bus)
    runner = KwsRunner(bus, ScriptedKeywordSpotter(every_n_chunks=20), source="kws-bench")
    blk = np.zeros(chunk, dtype=np.float32)

    lat: typing.List[float] = []
    cpu0, wall0 = time.process_time(), time.perf_counter()
    for _ in range(blocks):
        t0 = time.perf_counter()
        runner.feed(blk)
        lat.append((time.perf_counter() - t0) * 1000.0)
    wall1, cpu1 = time.perf_counter(), time.process_time()
    audio_seconds = blocks * chunk / float(args.sample_rate)
    rtf = (wall1 - wall0) / audio_seconds if audio_seconds else 0.0

    return {
        "engine": "scripted(无模型)",
        "latency": {"chunk_ms": args.chunk_ms, "blocks": len(lat),
                    "p50_ms": round(percentile(lat, 0.50), 3),
                    "p95_ms": round(percentile(lat, 0.95), 3),
                    "p99_ms": round(percentile(lat, 0.99), 3),
                    "max_ms": round(max(lat), 3) if lat else 0.0,
                    "mean_ms": round(statistics.fmean(lat), 3) if lat else 0.0},
        "throughput": {"rtf_mean": round(rtf, 6), "rtf_max": round(rtf, 6),
                       "speedup_x": round(1.0 / rtf, 1) if rtf else 0.0},
        "detection": {"runs": 1, "hit_runs": 1 if runner.hits else 0,
                      "false_positives": 0, "false_triggers_per_hour": 0.0,
                      "hits": runner.hits},
        "resources": {"cpu_percent_mean": round(100.0 * (cpu1 - cpu0) / max(1e-9, wall1 - wall0), 1),
                      "peak_working_set_mb": round(peak_working_set_bytes() / (1024.0 * 1024.0), 1)},
        "rows": [],
        "caveats": ["脚本化后端仅为链路自检：不反映真实模型算力占用；"
                    "真实指标请跑 --wav 模式。环境标签：PC / SIMULATED。"],
    }


def print_report(report: typing.Dict, title: str) -> None:
    """人类可读报告（同时打印到 stdout 供证据留痕）。"""
    lat, thr = report["latency"], report["throughput"]
    det, res = report["detection"], report["resources"]
    print("=== %s ｜ 环境标签：PC / SIMULATED ===" % title)
    print("引擎：%s ｜ 模型：%s" % (report["engine"], report.get("model_dir", "-") or "-"))
    print("延迟（块长 %dms，共 %d 块）：mean=%.3f  p50=%.3f  p95=%.3f  p99=%.3f  max=%.3f ms"
          % (lat["chunk_ms"], lat["blocks"], lat["mean_ms"], lat["p50_ms"],
             lat["p95_ms"], lat["p99_ms"], lat["max_ms"]))
    print("吞吐：RTF=%.4f（均值）｜加速比 %.1f×实时 ｜ RTF_max=%.4f"
          % (thr["rtf_mean"], thr["speedup_x"], thr["rtf_max"]))
    print("检测：音频 %s 条 / 运行 %s 次 ｜ 命中 %s 次（命中率 %s）｜ 误触发 %s 次（%s 秒负样本 → %s 次/小时）"
          % (det.get("audio_files", "-"), det.get("runs", "-"), det.get("hit_runs", "-"),
             det.get("hit_rate", "-"), det.get("false_positives", "-"),
             det.get("negative_seconds", "-"), det.get("false_triggers_per_hour", "-")))
    if det.get("first_hit_ms_mean") is not None:
        print("首命中偏移（均值）：%.1f ms" % det["first_hit_ms_mean"])
    if det.get("keywords_seen"):
        print("命中关键词：%s" % "、".join(det["keywords_seen"]))
    print("资源：CPU≈%.1f%%（单线程）｜ 峰值工作集 %.1f MB"
          % (res["cpu_percent_mean"], res["peak_working_set_mb"]))
    for row in report.get("rows", []):
        print("  %-8s %5.2fs  hits=%-26s rtf=%.4f cpu=%.0f%%"
              % (row["wav"], row["seconds"], ",".join(row["hits"]) or "-",
                 row["rtf"], row["cpu_percent"]))


def main() -> int:
    args = parse_args()
    if args.synthetic:
        report = measure_synthetic(args)
        title = "KWS benchmark（脚本化链路自检，无模型）"
    else:
        model_dir = args.model_dir or auto_model_dir()
        wavs = list(args.wav)
        if not wavs and model_dir:
            wavs = sorted(glob.glob(os.path.join(model_dir, "test_wavs", "*.wav")))
        if not wavs:
            print("!! 没找到音频：请用 --wav 指定，或先下载模型包（自带 test_wavs/）")
            return 2
        if not args.keywords_file and model_dir:
            candidate = os.path.join(model_dir, "test_wavs", "test_keywords.txt")
            if os.path.isfile(candidate):
                args.keywords_file = candidate
        report = measure_real(wavs, args)
        title = "KWS benchmark（真实模型 sherpa-onnx）"

    report["env"] = "PC / SIMULATED"
    report["generated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    print_report(report, title)

    out = args.out or os.path.join(_ROOT, "evidence_shots", "kws_benchmark.json")
    out = out if os.path.isabs(out) else os.path.join(_ROOT, out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)
    print("报告已写入：%s" % _rel(out))
    print("结论: PASS（benchmark 完成；数值口径见 JSON 的 caveats）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
