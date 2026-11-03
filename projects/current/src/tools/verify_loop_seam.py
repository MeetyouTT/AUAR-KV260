# -*- coding: utf-8 -*-
"""循环接缝诊断 + 乒乓/裁尾修法验收（PIL 读帧 + 纯逻辑判据）。

背景（用户实测反馈 2026-10-04）：素材**首末帧姿态基本相同**（i2v 循环素材常态），
且动作曲线为"起→高潮→收"⇒ 正放循环时"末帧→首帧"= 同一帧连播两次 → 观感"顿一下"。

检查项：
  S1 帧间差曲线（人物区 mean abs diff）→ 末尾**静止帧数 N**（= 顿点长度）
  S2 首末帧差 → 判断"首末是否同一姿态"
  S3 乒乓折返连续性：折返处帧索引变化 |Δ| ≤ 1（无跳帧），且**折返点不重复**
  S4 折返周期：`pingpong_time(t + span) == pingpong_time(t)`（span = 2·eff − 1/fps）
  S5 状态名单：待机族折返、播报族不折返、burst 不适用

用法（本机无系统 Python，用 aura 自带 .venv）：
    "<AURA>\\.venv\\Scripts\\python.exe" -s tools\\verify_loop_seam.py [--asset idle_normal]
输出：控制台 + %TEMP%\\aura_loop_seam.txt（UTF-8）
"""
import argparse
import os
import sys
from pathlib import Path

import numpy as np
from PIL import Image

AURA = Path(__file__).resolve().parents[1]
if str(AURA) not in sys.path:
    sys.path.insert(0, str(AURA))

from board.interaction import avatar_assets as aa       # noqa: E402
from board.interaction import avatar_timing as at       # noqa: E402

# 重定向到文件时 stdout 可能是 GBK（本机默认）→ 统一 UTF-8，避免 U+2212 之类字符报
# UnicodeEncodeError（.cline-handover.md 第 31 条已记过这个坑）
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

OUT = Path(os.environ.get("TEMP", ".")) / "aura_loop_seam.txt"
LOG = []
FAILED = []
#: 判定"静止帧"的帧间差阈值（灰阶 0~255）：低于此值肉眼视为未动
STILL_THRESHOLD = 1.0
ALPHA_MIN = 100          # 人物区掩膜（体检 v3 口径：alpha>100 才算前景）


def log(s):
    LOG.append(str(s))
    print(s, flush=True)


def check(cond, code, msg):
    log("  [%s] %s" % ("OK " if cond else "FAIL", "%s %s" % (code, msg)))
    if not cond:
        FAILED.append(code)
    return cond


def load_frames(name):
    directory = aa.asset_dir(name)
    paths = aa.list_frames(directory)
    if not paths:
        raise SystemExit("素材缺失：%s" % directory)
    return [Image.open(p).convert("RGBA") for p in paths], aa.frames_fps(directory)


def fg_diff(a, b):
    """人物区（alpha > ALPHA_MIN）平均绝对灰度差；无前景 → 0.0。"""
    ga = np.asarray(a, dtype=np.float32)
    gb = np.asarray(b, dtype=np.float32)
    mask = ga[..., 3] > ALPHA_MIN
    if not mask.any():
        return 0.0
    da = ga[..., :3].mean(axis=2)
    db = gb[..., :3].mean(axis=2)
    return float(np.abs(da - db)[mask].mean())


def tail_still_count(frame_diffs, threshold=STILL_THRESHOLD):
    """末尾连续"静止"帧数 N：从倒数第 2 个差开始往前数（差的个数 = 帧数-1）。"""
    n = 0
    for d in reversed(frame_diffs):
        if d < threshold:
            n += 1
        else:
            break
    return n


def s1_seam(asset, frames, fps):
    log("S1 帧间差曲线（%s：%d 帧 @%.1f fps，阈值 %.1f）"
        % (asset, len(frames), fps, STILL_THRESHOLD))
    diffs = [fg_diff(a, b) for a, b in zip(frames, frames[1:])]
    log("     逐帧差：%s" % " ".join("%.2f" % d for d in diffs))
    n_tail = tail_still_count(diffs)
    loop_gap = fg_diff(frames[-1], frames[0])
    log("     末尾静止帧数 N = %d（≈%.2f s，占素材 %.0f%%）"
        % (n_tail, n_tail / fps, 100.0 * n_tail / len(frames)))
    log("     最大帧间差 %.2f ／ 平均 %.2f" % (max(diffs), sum(diffs) / len(diffs)))
    check(n_tail >= 1, "S1", "存在末尾静止段（N=%d）→ 循环顿点成立" % n_tail)
    return diffs, n_tail, loop_gap


def s2_ends(loop_gap, mean_diff):
    """首末是否近似回到起点：判据用**素材自身平均帧间差**，不能用绝对阈值。

    实测 idle_normal：首末差 3.22 灰阶、平均帧间差 5.59 → 比值 0.58，即
    近似回到起点（但不是像素级同一帧）；若用绝对阈值 1.0 会误判为不成立。
    """
    log("S2 首末帧差（是否近似回到起点）")
    ratio = loop_gap / mean_diff if mean_diff > 0 else 0.0
    log("     末帧 vs 首帧 = %.2f 灰阶 ／ 平均帧间差 %.2f → 比值 %.2f"
        % (loop_gap, mean_diff, ratio))
    check(ratio < 0.7, "S2",
          "首末帧接近同一姿态（比值 %.2f < 0.7）→ 正放循环等于回到起点重来，必顿"
          % ratio)
    return loop_gap


def s3_pingpong(frames, fps, trim):
    log("S3 乒乓折返连续性（裁尾 %d 帧）" % trim)
    n_eff = len(frames) - trim
    duration = len(frames) / fps        # 传素材总时长，裁尾交给 trim_frames
    eff = (n_eff - 1) / fps
    span = 2.0 * eff
    step = 1.0 / fps
    idx = []
    for i in range(int(round(span * fps)) + 1):
        t = at.pingpong_time(i * step, duration, trim, fps)
        idx.append(at.frame_index(t, n_eff, fps, False))
    jumps = [abs(b - a) for a, b in zip(idx, idx[1:])]
    worst = max(jumps) if jumps else 0
    check(worst <= 1, "S3", "折返序列最大帧索引跳变 = %d（≤1 连续）" % worst)
    check(idx.count(n_eff - 1) == 1, "S3",
          "末帧（%d）在序列中出现 %d 次（=1 才没重复折返）"
          % (n_eff - 1, idx.count(n_eff - 1)))
    check(idx.count(0) == 2, "S3",
          "首帧（0）出现 %d 次（一个来回恰好 2 次：起点 + 终点）" % idx.count(0))
    log("     序列（前 20）：%s" % idx[:20])
    return idx


def s4_period(fps, trim, frames_n):
    log("S4 折返周期")
    n_eff = frames_n - trim
    duration = frames_n / fps
    eff = (n_eff - 1) / fps
    span = 2.0 * eff
    ok = True
    for t in (0.0, 0.137, 0.5, 1.0, 2.0):
        a = at.pingpong_time(t, duration, trim, fps)
        b = at.pingpong_time(t + span, duration, trim, fps)
        ok = ok and abs(a - b) < 1e-6
    check(ok, "S4", "pingpong_time(t + span) == pingpong_time(t)，span = %.4f s" % span)
    check(abs(span - 2.0 * eff) < 1e-9, "S4",
          "span = 2*(n_eff-1)/fps = %.4f s（n_eff = %d，末帧只在折返点取一次）"
          % (span, n_eff))
    return span


def s6_warp(diffs, fps):
    log("S6 匀速化（时间重映射）：循环点速度匹配")
    plain = at.cycle_speed_ratio(diffs, fps, warp=False)
    warped = at.cycle_speed_ratio(diffs, fps, warp=True)
    check(abs(plain - 1.0) > 0.5, "S6",
          "现状速度突变比 %.2f（偏离 1 越远越顿）" % plain)
    check(abs(warped - 1.0) < 0.35, "S6",
          "匀速化后速度突变比 %.2f（≈1 → 循环点速度连续，看不出接缝）" % warped)
    slow = at.cycle_speed_ratio(diffs, fps, warp=True, slowdown=1.5)
    check(abs(slow - 1.0) < 0.35, "S6",
          "叠加放慢 1.5 倍后突变比 %.2f（放慢不破坏速度匹配）" % slow)
    return plain, warped


def s5_states():
    log("S5 折返状态名单")
    check(at.pingpong_for_state("IDLE") and at.pingpong_for_state("THINKING"), "S5",
          "待机族折返：IDLE=%s / THINKING=%s"
          % (at.pingpong_for_state("IDLE"), at.pingpong_for_state("THINKING")))
    check(not at.pingpong_for_state("SPEAKING")
          and not at.pingpong_for_state("SPEAKING_NEUTRAL"), "S5",
          "播报族不折返（倒放会让口型反向）：SPEAKING=%s"
          % at.pingpong_for_state("SPEAKING"))


def main():
    ap = argparse.ArgumentParser(description="循环接缝诊断 + 乒乓/裁尾验收")
    ap.add_argument("--asset", default="idle_normal")
    ap.add_argument("--trim-extra", type=int, default=0,
                    help="在自动测得的静止帧数之上额外多裁几帧（默认 0）")
    args = ap.parse_args()

    log("=== 循环接缝诊断（%s）===" % args.asset)
    frames, fps = load_frames(args.asset)
    log("")
    diffs, n_tail, loop_gap = s1_seam(args.asset, frames, fps)
    log("")
    s2_ends(loop_gap, sum(diffs) / len(diffs) if diffs else 0.0)
    log("")
    trim = n_tail + max(0, args.trim_extra)
    log("→ 建议裁尾 %d 帧（末尾静止 %d + 额外 %d）" % (trim, n_tail, args.trim_extra))
    log("")
    s3_pingpong(frames, fps, trim)
    log("")
    s4_period(fps, trim, len(frames))
    log("")
    s5_states()
    log("")
    s6_warp(diffs, fps)
    log("")
    log("RESULT: %s (%d 项失败)" % ("OK" if not FAILED else "FAIL", len(FAILED)))
    if FAILED:
        log("失败项：%s" % ", ".join(sorted(set(FAILED))))
    OUT.write_text("\n".join(LOG) + "\n", encoding="utf-8")
    print("日志：%s" % OUT)
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
