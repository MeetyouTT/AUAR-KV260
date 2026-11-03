# -*- coding: utf-8 -*-
"""素材运动量表：**全部素材**的逐帧运动量预计算 + 批量体检 —— 素材动作 SOP 第一步。

背景（用户 2026-10-04 定案）：源素材（i2v 生成，约 5 秒量级）动作又快又大，直接循环会
"顿 + 急促"，故**所有待机族素材统一**走「匀速化 + 放慢 `LOOP_SLOWDOWN` 倍」。

本脚本做三件事：
  ① 逐个素材算**逐帧运动量**（人物区 alpha>100 的平均绝对灰度差）；
  ② 报告"处理前后"的**循环点速度突变比**（≈1 才达标）+ 末尾静止帧数；
  ③ `--write` 时把表落盘 `assets/avatar/<素材名>/motion.json`（运行时**零像素开销**）。

用法：
    "<AURA>\\.venv\\Scripts\\python.exe" -s tools\\build_motion_table.py [--write]
输出：控制台 + %TEMP%\\aura_motion_table.txt（UTF-8）
"""
import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image

AURA = Path(__file__).resolve().parents[1]
if str(AURA) not in sys.path:
    sys.path.insert(0, str(AURA))

from board.interaction import avatar_assets as aa      # noqa: E402
from board.interaction import avatar_timing as at      # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

OUT = Path(os.environ.get("TEMP", ".")) / "aura_motion_table.txt"
ALPHA_MIN = 100          # 人物区掩膜（体检 v3 口径）
STILL_THRESHOLD = 1.0    # 判定"静止帧"的帧间差阈值（灰阶）
LOG = []
NEED_CHECK = []


def log(s):
    LOG.append(str(s))
    print(s, flush=True)


def diffs_of(directory):
    """素材逐帧运动量 + (帧数, fps)；无素材 → ([], 0, 0.0)。"""
    paths = aa.list_frames(directory)
    if not paths:
        return [], 0, 0.0
    grays = []
    masks = []
    for p in paths:
        arr = np.asarray(Image.open(p).convert("RGBA"), dtype=np.float32)
        masks.append(arr[..., 3] > ALPHA_MIN)
        grays.append(arr[..., :3].mean(axis=2))
    out = []
    for a, b, m in zip(grays, grays[1:], masks[1:]):
        out.append(float(np.abs(a - b)[m].mean()) if m.any() else 0.0)
    return out, len(paths), aa.frames_fps(directory)


def main():
    ap = argparse.ArgumentParser(description="素材运动量表：预计算 + 批量体检")
    ap.add_argument("--write", action="store_true", help="把 motion.json 写入素材目录")
    ap.add_argument("--slowdown", type=float, default=at.LOOP_SLOWDOWN)
    args = ap.parse_args()

    log("=== 素材运动量表（SOP：匀速化 + 放慢 %.1f 倍）===" % args.slowdown)
    log("")
    log("%-22s %5s %7s %10s %9s %8s  %s"
        % ("素材", "帧数", "fps", "现状突变比", "处理后", "末静止", "判定"))
    written = 0
    total = 0
    for name in aa.all_asset_names():
        directory = aa.asset_dir(name)
        diffs, n, fps = diffs_of(directory)
        if not diffs:
            log("%-22s %5s %7s %10s %9s %8s  %s" % (name, "-", "-", "-", "-", "-", "无素材"))
            continue
        plain = at.cycle_speed_ratio(diffs, fps, warp=False)
        warped = at.cycle_speed_ratio(diffs, fps, warp=True, slowdown=args.slowdown)
        tail = 0
        for d in reversed(diffs):
            if d < STILL_THRESHOLD:
                tail += 1
            else:
                break
        ok = abs(warped - 1.0) < 0.35
        if not ok:
            NEED_CHECK.append(name)
        log("%-22s %5d %7.1f %10.2f %9.2f %8d  %s"
            % (name, n, fps, plain, warped, tail, "达标" if ok else "★需检查"))
        total += 1
        if args.write:
            meta = aa.read_meta(directory)
            payload = {
                "asset": name, "frames": n, "fps": fps,
                "diffs": [round(d, 4) for d in diffs],
                "slowdown": args.slowdown,
                "spec": "匀速化（avatar_timing.warp_time）+ 放慢；口径见 tools/build_motion_table.py",
                "source": str(meta.get("source", "")),
            }
            (directory / "motion.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
            written += 1
    log("")
    if args.write:
        log("已写入 motion.json：%d 个" % written)
    log("判定口径：处理后速度突变比 |x-1| < 0.35 视为达标（≈1 = 循环点速度连续）")
    log("RESULT: %s（素材 %d 个，需检查 %d 个%s）"
        % ("OK" if not NEED_CHECK else "CHECK", total, len(NEED_CHECK),
           ("：" + "、".join(NEED_CHECK)) if NEED_CHECK else ""))
    OUT.write_text("\n".join(LOG) + "\n", encoding="utf-8")
    print("日志：%s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
