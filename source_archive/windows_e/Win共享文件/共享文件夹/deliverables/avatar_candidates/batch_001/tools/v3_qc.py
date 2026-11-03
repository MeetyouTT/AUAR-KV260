#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""v3 说话素材候选：数值体检（结构 + 运动分布），不消耗看图次数。

范围与护栏：
  - 只读  <batch-root>\\raw\\<asset>_s<seed>\\ 下的 *.png 与 meta.json；
  - 只写  <batch-root>\\qc\\ 下的报告；
  - 绝不修改/删除任何帧，绝不写 aura\\assets 或正式素材目录。

判定口径与 aura\\tools\\check_naturalness_candidate.py 一致：
  status = FAIL 或 STRUCTURE_VALID_REQUIRES_VISUAL_REVIEW
  后者只表示"结构 + 运动数值合格"，**不等于视觉通过**，仍需抽帧目测。

用法:
  python zz_v3_qc.py --batch-root <...\\deliverables\\avatar_candidates\\batch_001>
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

FRAME_COUNT_EXPECTED = 39
PIXEL_EPS = 8.0          # 灰度差超过 8 才算"变了"的像素
NO_MOTION_PEAK = 0.5     # 峰值均值差低于此值视为"完全没动"
TAIL_RATIO_MAX = 0.50    # 末帧/峰值 比值上限，超出说明没回到静息姿势
LOWER_SHARE_MAX = 0.55   # 下半幅差异占比上限，超出说明身体/手在动
BLINK_PEAK_MIN = 1.0     # blink 类相邻帧峰值下限


def _gray(path: Path) -> np.ndarray:
    with Image.open(path) as im:
        return np.asarray(im.convert("L"), dtype=np.float32)


def _band_bounds(profile: np.ndarray, lo: float = 0.05, hi: float = 0.95):
    """按累计分布返回 [lo, hi] 分位与重心，坐标归一化到 0~1。"""
    total = float(profile.sum())
    n = profile.shape[0]
    if total <= 0:
        return 0.0, 0.0, 0.0
    cum = np.cumsum(profile) / total
    a = float(np.searchsorted(cum, lo)) / n
    b = float(np.searchsorted(cum, hi)) / n
    c = float((profile * np.arange(n)).sum() / total) / n
    return a, b, c


def inspect_dir(d: Path) -> dict:
    pngs = sorted(d.glob("*.png"))
    meta_path = d / "meta.json"
    meta = {}
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            meta = {"_meta_error": "%s: %s" % (type(exc).__name__, exc)}

    rec: dict = {
        "id": d.name,
        "asset": d.name.rsplit("_s", 1)[0],
        "seed": d.name.rsplit("_s", 1)[1] if "_s" in d.name else "",
        "frame_count": len(pngs),
        "meta_state": meta.get("state"),
        "flags": [],
    }
    if len(pngs) != FRAME_COUNT_EXPECTED:
        rec["flags"].append("FRAME_COUNT_MISMATCH")
        rec["status"] = "FAIL"
        return rec

    ref = _gray(pngs[0])
    h, w = ref.shape
    rec["size"] = [w, h]

    n = len(pngs)
    mean0 = np.zeros(n); meanp = np.zeros(n); frac0 = np.zeros(n)
    rowp = np.zeros((n, h)); colp = np.zeros((n, w))
    y0 = int(0.08 * h); y1 = int(0.18 * h)          # 眼部带（按 864x1536 竖构图实测标定）
    eyep = np.zeros(n)                              # 眼部带帧间差分均值
    eyer = np.zeros(n); eyel = np.zeros(n)          # 眼部带左右两半之差分质量（眨眼应对称）
    eyef = np.zeros(n); eyeconc = np.zeros(n)       # 眼部带变化像素占比 / 强变化像素质量占比

    prev = ref
    size_bad = False
    for i, p in enumerate(pngs):
        cur = _gray(p)
        if cur.shape != ref.shape:
            size_bad = True
            continue
        d0 = np.abs(cur - ref)
        mean0[i] = float(d0.mean())
        frac0[i] = float((d0 > PIXEL_EPS).mean())
        rowp[i] = d0.mean(axis=1)
        colp[i] = d0.mean(axis=0)
        if i > 0:
            dp = np.abs(cur - prev)
            meanp[i] = float(dp.mean())
            band = dp[y0:y1]
            eyep[i] = float(band.mean())
            eyer[i] = float(band[:, : w // 2].sum())
            eyel[i] = float(band[:, w // 2:].sum())
            eyef[i] = float((band > PIXEL_EPS).mean())
            strong = float(band[band > 4 * PIXEL_EPS].sum())
            eyef_sum = float(band.sum())
            eyeconc[i] = (strong / eyef_sum) if eyef_sum > 0 else 0.0
        prev = cur

    if size_bad:
        rec["flags"].append("FRAME_SIZE_MISMATCH")
        rec["status"] = "FAIL"
        return rec

    peak_frame = int(np.argmax(mean0[1:])) + 1
    peak = float(mean0[peak_frame])
    last = float(mean0[-1])
    ratio = (last / peak) if peak > 0 else 0.0

    y_lo, y_hi, y_c = _band_bounds(rowp[peak_frame])
    x_lo, x_hi, x_c = _band_bounds(colp[peak_frame])
    tot = max(float(rowp[peak_frame].sum()), 1e-9)
    upper = float(rowp[peak_frame, : int(h * 0.45)].sum() / tot)
    lower = float(rowp[peak_frame, int(h * 0.55):].sum() / tot)

    blink_frame = int(np.argmax(meanp))
    eb_frame = int(np.argmax(eyep))
    eb_peak = float(eyep[eb_frame])
    lr_total = float(eyer[eb_frame] + eyel[eb_frame])
    eb_lr = (float(eyer[eb_frame]) / lr_total) if lr_total > 0 else 0.0
    rec.update({
        "peak_frame": peak_frame,
        "peak_mean_diff": round(peak, 3),
        "last_mean_diff": round(last, 3),
        "tail_ratio": round(ratio, 3),
        "peak_frac_changed": round(float(frac0[peak_frame]), 4),
        "motion_y_band": [round(y_lo, 3), round(y_hi, 3)],
        "motion_y_centroid": round(y_c, 3),
        "motion_x_band": [round(x_lo, 3), round(x_hi, 3)],
        "upper_share": round(upper, 3),
        "lower_share": round(lower, 3),
        "prev_peak_frame": blink_frame,
        "prev_peak_mean_diff": round(float(meanp[blink_frame]), 3),
        "eye_band_prev_peak": round(eb_peak, 3),
        "eye_band_prev_peak_frame": eb_frame,
        "eye_band_lr_ratio": round(eb_lr, 3),
        "eye_band_frac_changed_at_peak": round(float(eyef[eb_frame]), 4),
        "eye_band_concentration_at_peak": round(float(eyeconc[eb_frame]), 3),
        "eye_band_curve": [round(float(v), 3) for v in eyep],
        "curve_mean0": [round(float(v), 3) for v in mean0],
        "curve_meanp": [round(float(v), 3) for v in meanp],
    })

    flags = rec["flags"]
    if peak < NO_MOTION_PEAK:
        flags.append("NO_MOTION")
    if ratio > TAIL_RATIO_MAX:
        flags.append("TAIL_NOT_RETURNED")
    if lower > LOWER_SHARE_MAX:
        flags.append("LOWER_BODY_MOTION_DOMINANT")
    if "blink" in rec["asset"] and float(meanp[blink_frame]) < BLINK_PEAK_MIN:
        flags.append("BLINK_PEAK_MISSING")

    rec["status"] = "FAIL" if any(f in ("FRAME_COUNT_MISMATCH", "FRAME_SIZE_MISMATCH") for f in flags) \
        else "STRUCTURE_VALID_REQUIRES_VISUAL_REVIEW"
    return rec


def one_line(rec: dict) -> str:
    if "peak_mean_diff" not in rec:
        return "%-34s png=%-3d state=%-8s %s" % (
            rec["id"], rec["frame_count"], str(rec.get("meta_state")), ",".join(rec["flags"]))
    return ("%-34s png=%-3d peak=%-7.3f@f%-2d last=%-7.3f tail=%-6.3f y=%.2f-%.2f "
            "up=%.2f low=%.2f dprev=%.3f@f%-2d eye=%.3f@f%-2d lr=%.2f ef=%.3f ec=%.2f %s") % (
        rec["id"], rec["frame_count"], rec["peak_mean_diff"], rec["peak_frame"],
        rec["last_mean_diff"], rec["tail_ratio"], rec["motion_y_band"][0], rec["motion_y_band"][1],
        rec["upper_share"], rec["lower_share"], rec["prev_peak_mean_diff"], rec["prev_peak_frame"],
        rec["eye_band_prev_peak"], rec["eye_band_prev_peak_frame"], rec["eye_band_lr_ratio"],
        rec["eye_band_frac_changed_at_peak"], rec["eye_band_concentration_at_peak"],
        ",".join(rec["flags"]) or "-")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="numeric QC for v3 avatar candidates (read-only)")
    ap.add_argument("--batch-root", required=True)
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--report", default=None)
    args = ap.parse_args(argv)

    root = Path(args.batch_root)
    raw = root / "raw"
    qc_dir = root / "qc"
    qc_dir.mkdir(parents=True, exist_ok=True)
    if not raw.is_dir():
        print("FAIL raw dir missing: %s" % raw)
        return 2

    dirs = [d for d in sorted(raw.iterdir()) if d.is_dir()]
    if args.only:
        dirs = [d for d in dirs if d.name in set(args.only)]
    if not dirs:
        print("FAIL no candidate dirs under %s" % raw)
        return 2

    recs = [inspect_dir(d) for d in dirs]
    stamp = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    fails = [r["id"] for r in recs if r["status"] == "FAIL"]
    report = {
        "candidate_root": str(raw),
        "generated_at": stamp,
        "frame_count_expected": FRAME_COUNT_EXPECTED,
        "status": "FAIL" if fails else "STRUCTURE_VALID_REQUIRES_VISUAL_REVIEW",
        "note": "STRUCTURE_VALID_REQUIRES_VISUAL_REVIEW = numeric checks only; visual review still required.",
        "thresholds": {"PIXEL_EPS": PIXEL_EPS, "NO_MOTION_PEAK": NO_MOTION_PEAK,
                       "TAIL_RATIO_MAX": TAIL_RATIO_MAX, "LOWER_SHARE_MAX": LOWER_SHARE_MAX,
                       "BLINK_PEAK_MIN": BLINK_PEAK_MIN},
        "candidates": recs,
    }
    out = Path(args.report) if args.report else (qc_dir / ("qc_%s.json" % stamp))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    txt = ["count=%d status=%s" % (len(recs), report["status"])]
    txt += [one_line(r) for r in recs]
    txt.append("FAIL_IDS=%s" % (",".join(fails) or "-"))
    txt.append("FLAGGED_IDS=%s" % (",".join(r["id"] for r in recs if r["flags"] and r["status"] != "FAIL") or "-"))
    (qc_dir / ("qc_%s.txt" % stamp)).write_text("\n".join(txt) + "\n", encoding="utf-8")
    print("\n".join(txt))
    print("report=%s" % out)
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
