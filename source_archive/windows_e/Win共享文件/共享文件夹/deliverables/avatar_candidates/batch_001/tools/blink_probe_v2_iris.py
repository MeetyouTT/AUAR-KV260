#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""眨眼量化探针 v2（只读）：眼区"蓝瞳占比"随帧变化。

坐标依据：2026-10-06 目测 blink_s421001 / rest_s421001 的 f16 帧标定——
  眼区 x in [0.41,0.59]，y in [0.125,0.175]（整幅 864x1536，脸部仅占中央窄带）。
判据：睁眼 -> 眼区含蓝瞳/白巩膜（蓝通道显著高于红）=> blue_frac 高；
      闭眼 -> 眼皮为肤色（红>=蓝）=> blue_frac 骤降。闭眼帧 = blue_frac < 0.5*median。

用法: python zz_blink_probe2.py --batch-root <...\\batch_001> [--out <txt>]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

X0, Y0, X1, Y1 = 0.41, 0.125, 0.59, 0.175


def blue_frac(path: Path) -> float:
    with Image.open(path) as im:
        a = np.asarray(im.convert("RGB"), dtype=np.float32)
    h, w = a.shape[:2]
    box = a[int(Y0 * h):int(Y1 * h), int(X0 * w):int(X1 * w)]
    r, g, b = box[..., 0], box[..., 1], box[..., 2]
    return float(((b > r + 20) & (b > g + 10)).mean())


def probe(d: Path) -> dict:
    pngs = sorted(d.glob("*.png"))
    rec = {"id": d.name, "png": len(pngs)}
    if len(pngs) != 39:
        rec["error"] = "need 39 frames"
        return rec
    f = np.asarray([blue_frac(p) for p in pngs])
    med = float(np.median(f))
    sd = 1.4826 * float(np.median(np.abs(f - med)))      # MAD 稳健噪声底
    i_min = int(np.argmin(f))
    fmin = float(f[i_min])
    dip = (med - fmin) / med if med > 0 else 0.0
    closed = [int(i) for i in np.where(f < 0.72 * med)[0]]
    if dip >= 0.15 and (med - fmin) >= 3.0 * max(sd, 1e-6):
        verdict = "BLINK"
    elif dip >= 0.08:
        verdict = "WEAK"
    else:
        verdict = "NONE"
    rec.update({
        "blue_frac_median": round(med, 4),
        "blue_frac_min": round(fmin, 4),
        "min_frame": i_min,
        "dip_ratio": round(dip, 3),
        "noise_sd": round(sd, 4),
        "closed_frames": closed,
        "verdict": verdict,
        "curve": [round(float(v), 4) for v in f],
    })
    return rec


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="blink probe v2 (read-only)")
    ap.add_argument("--batch-root", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    raw = Path(args.batch_root) / "raw"
    if not raw.is_dir():
        print("FAIL raw dir missing: %s" % raw)
        return 2
    lines = ["NOTE: fixed-region color diagnostic only. NONE does NOT prove no blink; confirm face contact sheets. Known false negative: talking_calm_blink_v3_s421002 frames 15-17.",
             "blink probe v2  eye-box x[%.2f,%.2f] y[%.3f,%.3f]  metric=blue_iris_frac"
             % (X0, X1, Y0, Y1)]
    for d in sorted(raw.iterdir()):
        if not d.is_dir():
            continue
        r = probe(d)
        if "error" in r:
            lines.append("%-34s %s" % (r["id"], r["error"]))
            continue
        lines.append(
            "%-34s med=%.4f sd=%.4f min=%.4f@f%-2d dip=%.1f%% %-5s f0..f3=%s closed=%s"
            % (r["id"], r["blue_frac_median"], r["noise_sd"], r["blue_frac_min"],
               r["min_frame"], r["dip_ratio"] * 100, r["verdict"],
               ",".join("%.3f" % v for v in r["curve"][:4]),
               r["closed_frames"] or "-"))
    txt = "\n".join(lines) + "\n"
    if args.out:
        Path(args.out).write_text(txt, encoding="utf-8")
    print(txt, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
