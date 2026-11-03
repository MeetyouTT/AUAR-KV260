# -*- coding: utf-8 -*-
"""素材**自动切段**：为每个素材推荐 enter / loop / exit 三段，落盘 `segments.json`。

解决用户实测指出的结构性问题（2026-10-04）：素材是"起→高潮→收"整段，
说话 10 秒会变成"抬手→放下→抬手→放下…"重复 6 次，极不自然。
正确结构 = **[进入：抬手] 一次 → [保持：手在空中 + 小幅自然动] 循环 N 次 → [退出：放下] 一次**。

自动推荐判据（对应用户原话"在手抬起来时取几个幅度小的帧，不让手放下去"）：
  ① 找动作**高潮**（运动量峰值）位置；
  ② 在高潮附近滑窗，挑**运动量小幅但非静止**（≈ 平均 45%）、且**首尾姿态相近**（能自然衔接）的窗口作 `loop`；
  ③ `enter` = 起始 → 窗口首；`exit` = 窗口尾 → 结束。

依赖 `motion.json`（先跑 `tools/build_motion_table.py --write`；没有则本脚本现算）。

用法：
    "<AURA>\\.venv\\Scripts\\python.exe" -s tools\\split_avatar_segments.py [--write]
输出：控制台 + %TEMP%\\aura_segments.txt（UTF-8）
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

OUT = Path(os.environ.get("TEMP", ".")) / "aura_segments.txt"
ALPHA_MIN = 100           # 人物区掩膜
THUMB = (96, 100)         # 姿态比较用缩略尺寸（够判"像不像"，且快）
LOOP_LENGTHS = (8, 10, 12, 14)
TARGET_RATIO = 0.45       # loop 段目标运动量 ≈ 平均的 45%（"小幅但在动"）
LOG = []
NEED_CHECK = []


def log(s):
    LOG.append(str(s))
    print(s, flush=True)


def diffs_of(directory):
    """逐帧运动量（优先读 motion.json；缺失则现算）+ (帧数, fps)。"""
    payload = {}
    path = Path(directory) / "motion.json"
    if path.is_file():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            payload = {}
    if payload.get("diffs"):
        return ([float(d) for d in payload["diffs"]],
                int(payload.get("frames") or 0), float(payload.get("fps") or 0.0))
    paths = aa.list_frames(directory)
    if not paths:
        return [], 0, 0.0
    grays, masks = [], []
    for p in paths:
        arr = np.asarray(Image.open(p).convert("RGBA"), dtype=np.float32)
        masks.append(arr[..., 3] > ALPHA_MIN)
        grays.append(arr[..., :3].mean(axis=2))
    out = [float(np.abs(a - b)[m].mean()) if m.any() else 0.0
           for a, b, m in zip(grays, grays[1:], masks[1:])]
    return out, len(paths), aa.frames_fps(directory)


def thumbs(directory):
    """缩略帧（灰度 + 前景掩膜），用于比较"首尾姿态像不像"。"""
    out = []
    for p in aa.list_frames(directory):
        arr = np.asarray(Image.open(p).convert("RGBA").resize(THUMB, Image.LANCZOS),
                         dtype=np.float32)
        out.append((arr[..., :3].mean(axis=2), arr[..., 3] > ALPHA_MIN))
    return out


def pose_gap(a, b):
    """两帧姿态差（灰阶）：人物区平均绝对差；无前景 → 0.0。"""
    ga, ma = a
    gb, _ = b
    if not ma.any():
        return 0.0
    return float(np.abs(ga - gb)[ma].mean())


def recommend(diffs, ths):
    """推荐三段 (Segments, 诊断 dict)；帧数不足 → (None, {})。"""
    n = len(diffs) + 1
    if n < 20:
        return None, {}
    peak = max(range(len(diffs)), key=lambda i: diffs[i]) + 1
    target = (sum(diffs) / float(len(diffs))) * TARGET_RATIO
    candidates = []
    for wl in LOOP_LENGTHS:
        if wl >= n - 4:
            continue
        # 窗口搜索范围：从"高潮前一点"一直到"素材末（留末帧）"。
        # ⚠ 旧写法上界 `peak + 6` **太紧** —— 峰值靠前的素材只能在开头找窗口，
        #   结果第二个窗口落进 enter 段、且**凑不满 3 个**（实测 `windows=((12,19),(1,8))`）。
        a_lo = max(1, peak - 22)
        a_hi = max(a_lo + 1, n - wl - 2)
        for a in range(a_lo, a_hi):
            b = a + wl - 1
            seg_d = diffs[a:b]
            if not seg_d:
                continue
            mean_d = sum(seg_d) / float(len(seg_d))
            if mean_d < target * 0.5:     # 排除"太静"的窗口（否则会选到近乎静止段 ⇒ 变成"停住"）
                continue
            gap = pose_gap(ths[a], ths[b])
            score = -gap - 0.6 * abs(mean_d - target)
            candidates.append((score, a, b, mean_d, gap))
    if not candidates:
        return None, {}
    candidates.sort(key=lambda c: -c[0])
    best = candidates[0]
    # **多窗口**（用户实测 2026-10-05：单一窗口长时间说话 = 同一个动作反复晃，很单调）：
    # 取打分最高的前 3 个**互不重叠**窗口，运行时每个"来回"轮换一个。
    windows = [(best[1], best[2])]
    for _score, ca, cb, _md, _gap in candidates[1:]:
        if len(windows) >= 3:
            break
        # 排除"起势段"窗口（素材前 20%）。理由：起势段手**还没抬起来**，
        # 在里面往返 = "抬到一半又放回"，观感比单调更差（实测第一个版本选出了 `(1,8)`）。
        if ca < max(2, n // 5):
            continue
        if any(not (cb < wa or ca > wb) for wa, wb in windows):      # 与已选重叠 → 跳过
            continue
        windows.append((ca, cb))
    _s, a, b, mean_d, gap = best
    seg = at.Segments(enter=(0, a), loop=(a, b), exit=(b, n - 1),
                      windows=tuple(windows))
    info = {"peak": peak, "loop": [a, b], "loop_frames": b - a + 1,
            "windows": [list(w) for w in windows],
            "loop_mean_motion": round(mean_d, 3), "loop_pose_gap": round(gap, 3),
            "target_motion": round(target, 3),
            "enter_frames": a + 1, "exit_frames": n - b}
    return seg, info


def main():
    ap = argparse.ArgumentParser(description="素材自动切段（enter/loop/exit）")
    ap.add_argument("--write", action="store_true", help="把 segments.json 写入素材目录")
    args = ap.parse_args()

    log("=== 素材自动切段（enter / loop / exit）===")
    log("目标结构：[抬手] 一次 → [手在空中 + 小幅动] 循环 N 次 → [放下] 一次")
    log("")
    log("%-20s %6s %16s %9s %9s %8s  %s"
        % ("素材", "帧数", "loop 区间", "loop均值", "首尾差", "峰值帧", "判定"))
    written = 0
    total = 0
    for name in aa.all_asset_names():
        directory = aa.asset_dir(name)
        if aa.is_burst_asset(name):
            # ⚠ burst 素材（点头 / 摇头 / 惊讶）必须**整段播一次**，不做三段式：
            # 从中间帧起播或循环都会破坏"一次性完整动作"的语义（用户 2026-10-04 指出）。
            log("%-20s %6s %16s %9s %9s %8s  %s"
                % (name, "-", "-", "-", "-", "-", "burst 素材，跳过三段式"))
            continue
        diffs, n, fps = diffs_of(directory)
        if n < 20:
            log("%-20s %6s %16s %9s %9s %8s  %s"
                % (name, n or "-", "-", "-", "-", "-", "帧数不足/无素材"))
            continue
        seg, info = recommend(diffs, thumbs(directory))
        if seg is None:
            log("%-20s %6d %16s %9s %9s %8s  %s"
                % (name, n, "-", "-", "-", "-", "无法推荐"))
            continue
        total += 1
        ok = info["loop_pose_gap"] < 6.0 and info["loop_frames"] >= 8
        if not ok:
            NEED_CHECK.append(name)
        log("%-20s %6d %16s %9.2f %9.2f %8d  %s"
            % (name, n,
               "%d..%d (%d帧)" % (info["loop"][0], info["loop"][1], info["loop_frames"]),
               info["loop_mean_motion"], info["loop_pose_gap"], info["peak"],
               "达标" if ok else "★需检查"))
        if args.write:
            payload = {
                "asset": name, "frames": n, "fps": fps,
                "enter": list(seg.enter), "loop": list(seg.loop), "exit": list(seg.exit),
                # **多窗口**（运行时按"来回"轮换；缺失时退回单一 loop 段）
                "windows": [list(w) for w in seg.windows],
                "loops_hint": at.loops_for_duration(10.0, seg, fps),
                "spec": "三段式（avatar_timing.segment_time）；由 tools/split_avatar_segments.py 推荐，可人工改",
                "diag": info,
            }
            (Path(directory) / "segments.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
            written += 1
    log("")
    if args.write:
        log("已写入 segments.json：%d 个" % written)
    log("判定口径：loop 段首尾姿态差 < 6 灰阶（能自然衔接）且长度 ≥ 8 帧")
    log("RESULT: %s（素材 %d 个，需检查 %d 个%s）"
        % ("OK" if not NEED_CHECK else "CHECK", total, len(NEED_CHECK),
           ("：" + "、".join(NEED_CHECK)) if NEED_CHECK else ""))
    OUT.write_text("\n".join(LOG) + "\n", encoding="utf-8")
    print("日志：%s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
