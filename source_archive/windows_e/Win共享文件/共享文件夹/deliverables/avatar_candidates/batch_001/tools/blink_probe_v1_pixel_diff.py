#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""眨眼专项数值探针：眼区暗像素数随时间曲线（只读，不写素材目录）。

原理：闭眼时眼球暗区被眼皮（肤色）覆盖 -> 眼区暗像素数出现 1~2 帧的骤降。
      该信号与"整幅重绘/头部微小位移"无关，因此可区分 rest（无眨眼）与 blink（有眨眼）。

用法:
  python zz_blink_probe.py --batch-root <...\\batch_001> [--out <报告.txt>]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

# 按 864x1536 竖构图实测标定的脸部窗口（归一化）
ROWS = (0.05, 0.28)
COLS = (0.28, 0.72)


def gray(path: Path) -> np.ndarray:
    with Image.open(path) as im:
        return np.asarray(im.convert("L"), dtype=np.float32)


def eye_boxes(a: np.ndarray, h: int, w: int):
    r0, r1 = int(ROWS[0] * h), int(ROWS[1] * h)
    c0, c1 = int(COLS[0] * w), int(COLS[1] * w)
    face = a[r0:r1, c0:c1]
    thr = float(face.mean() - 0.8 * face.std())
    dark = face < thr
    colh = dark.sum(axis=0)
    mid = colh.shape[0] // 2
    half = max(int(0.05 * w), 8)

    def box(half_hist, offset):
        k = int(np.argmax(half_hist)) + offset
        return max(k - half, 0), min(k + half, w)

    l0, l1 = box(colh[:mid], c0)
    r0b, r1b = box(colh[mid:], c0 + mid)
    return (r0, r1), (l0, l1), (r0b, r1b), float(colh[:mid].max()), float(colh[mid:].max()), thr


def probe(d: Path) -> dict:
    pngs = sorted(d.glob("*.png"))
    rec = {"id": d.name, "png": len(pngs)}
    if len(pngs) != 39:
        rec["error"] = "need 39 frames"
        return rec
    ref = gray(pngs[19])
    h, w = ref.shape
    (r0, r1), (l0, l1), (r0b, r1b), lpk, rpk, thr = eye_boxes(ref, h, w)
    rec["eye_rows"] = [r0, r1]
    rec["eye_cols_left"] = [l0, l1]
    rec["eye_cols_right"] = [r0b, r1b]
    rec["sym_left_right"] = round(min(lpk, rpk) / max(lpk, rpk, 1e-9), 3)
    rec["dark_thr"] = round(thr, 1)

    frac = []
    for p in pngs:
        a = gray(p)
        band = a[r0:r1]
        both = np.concatenate([band[:, l0:l1].ravel(), band[:, r0b:r1b].ravel()])
        frac.append(float((both < thr).mean()))
    f = np.asarray(frac)
    med = float(np.median(f))
    i_min = int(np.argmin(f))
    dip = (med - float(f[i_min])) / med if med > 0 else 0.0
    i_max = int(np.argmax(f))
    rec.update({
        "dark_frac_median": round(med, 4),
        "dark_frac_min": round(float(f[i_min]), 4),
        "min_frame": i_min,
        "dip_ratio": round(dip, 3),
        "dark_frac_max": round(float(f[i_max]), 4),
        "max_frame": i_max,
        "curve": [round(float(v), 4) for v in f],
    })
    return rec


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="blink probe (read-only)")
    ap.add_argument("--batch-root", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    raw = Path(args.batch_root) / "raw"
    if not raw.is_dir():
        print("FAIL raw dir missing: %s" % raw)
        return 2
    recs = [probe(d) for d in sorted(raw.iterdir()) if d.is_dir()]
    lines = ["blink probe  (dark-fraction of eye boxes; dip = closed-eye signature)"]
    for r in recs:
        if "error" in r:
            lines.append("%-34s %s" % (r["id"], r["error"]))
            continue
        lines.append(
            "%-34s eye_rows=%s sym=%.2f med=%.4f dip=%.1f%%@f%-2d max=%.4f@f%-2d"
            % (r["id"], r["eye_rows"], r["sym_left_right"], r["dark_frac_median"],
               r["dip_ratio"] * 100, r["min_frame"], r["dark_frac_max"], r["max_frame"]))
    txt = "\n".join(lines) + "\n"
    if args.out:
        Path(args.out).write_text(txt, encoding="utf-8")
    print(txt, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
