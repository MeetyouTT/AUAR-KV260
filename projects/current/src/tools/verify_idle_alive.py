# -*- coding: utf-8 -*-
"""潜动层（L0）验收：呼吸 / 重心 / 微摆"活着但不做作"（纯逻辑，无 Qt / PIL / numpy）。

取口径与播放层**共用** `board/interaction/avatar_timing.idle_offsets` —— 这是
"验收测的就是播放层"的前提（本机无 PySide6，qt_widgets 拿不到，见 .cline-handover.md 第 28 条）。

检查项：
  A1 中性位：t<=0 / gain=0 → 位移 0、缩放 1.0（进场不跳、可一键关闭）
  A2 幅度上限：全采样不超过设计值（呼吸 ≤0.6% / 重心 ≤1.2px / 微摆 ≤0.35°）
  A3 平滑度：24fps 下最大帧间变化（折算显示像素）远低于"抖"（<0.25 px）
  A4 可感知度：呼吸在 423×436 显示框上的纵向起伏 ≈2.6px（2~4px 才好看）
  A5 不重复：任意 t 与 t+200s 的姿态距离显著 > 0（200 秒内不回到同一姿态）
  A6 复合周期：各通道互质 → 复合周期 > 200s
  A7 周期正确性：60s 内呼吸起伏峰数 ≈ 60/3.7 ≈ 16 个

用法（本机无系统 Python，aura 自带 .venv 即可）：
    "<AURA>\\.venv\\Scripts\\python.exe" -s tools\\verify_idle_alive.py
输出：控制台 + %TEMP%\\aura_idle_alive.txt（UTF-8）
"""
import math
import os
import sys
from pathlib import Path

AURA = Path(__file__).resolve().parents[1]
if str(AURA) not in sys.path:
    sys.path.insert(0, str(AURA))

from board.interaction import avatar_timing as at        # noqa: E402

OUT = Path(os.environ.get("TEMP", ".")) / "aura_idle_alive.txt"
LOG = []
FAILED = []

#: 合同显示框（板端与 PC 一致）：waist-up 素材按宽铺满 423、高 436
DISPLAY_W = 423.0
DISPLAY_H = 436.0
#: 24fps 下一帧的时间步（潜动层必须在此粒度下平滑）
FRAME_STEP = 1.0 / 24.0


def log(s):
    LOG.append(str(s))
    print(s, flush=True)


def check(cond, code, msg):
    log("  [%s] %s" % ("OK " if cond else "FAIL", "%s %s" % (code, msg)))
    if not cond:
        FAILED.append(code)
    return cond


def samples(seconds, step):
    n = int(round(seconds / step))
    return [at.idle_offsets(i * step) for i in range(n + 1)]


def dist(a, b):
    """两个姿态的显示距离（像素）：位移直接算，缩放/旋转折算成像素。"""
    return (abs(a.dx - b.dx) + abs(a.dy - b.dy)
            + abs(a.scale_y - b.scale_y) * DISPLAY_H
            + abs(a.tilt_deg - b.tilt_deg) * math.pi / 180.0 * DISPLAY_H * 0.5)


def a1_neutral():
    log("A1 中性位（进场不跳 / 可一键关闭）")
    for t in (0.0, -1e-9, -5.0):
        off = at.idle_offsets(t)
        check(off == at.IdleOffsets(0.0, 0.0, 1.0, 0.0), "A1",
              "t=%g → dx=%.3f dy=%.3f scale=%.5f tilt=%.3f" % ((t,) + tuple(off)))
    off = at.idle_offsets(3.3, gain=0.0)
    check(off == at.IdleOffsets(0.0, 0.0, 1.0, 0.0), "A1",
          "gain=0 → dx=%.3f dy=%.3f scale=%.5f tilt=%.3f" % tuple(off))


def a2_amplitude():
    log("A2 幅度上限（设计值）")
    offs = samples(300.0, 0.01)
    max_dx = max(abs(o.dx) for o in offs)
    max_dy = max(o.dy for o in offs)
    lo_scale = min(o.scale_y for o in offs)
    hi_scale = max(o.scale_y for o in offs)
    max_tilt = max(o.tilt_deg for o in offs)
    check(max_dx <= at.IDLE_SWAY_AMP_X + 1e-9, "A2",
          "|dx|max=%.3f ≤ %.1f px" % (max_dx, at.IDLE_SWAY_AMP_X))
    check(max_dy <= at.IDLE_SWAY_AMP_Y + 1e-9, "A2",
          "dy max=%.3f ≤ %.1f px" % (max_dy, at.IDLE_SWAY_AMP_Y))
    check(lo_scale >= 1.0 and hi_scale <= 1.0 + at.IDLE_BREATH_AMP + 1e-9, "A2",
          "scale_y ∈ [%.5f, %.5f]（设计 1.0 ~ %.4f，且不缩小）"
          % (lo_scale, hi_scale, 1.0 + at.IDLE_BREATH_AMP))
    check(max_tilt <= at.IDLE_TILT_AMP_DEG + 1e-9, "A2",
          "|tilt|max=%.3f° ≤ %.2f°" % (max_tilt, at.IDLE_TILT_AMP_DEG))


def a3_smoothness():
    log("A3 平滑度（%.0f fps 下最大帧间变化，折算显示像素）" % (1.0 / FRAME_STEP))
    offs = samples(60.0, FRAME_STEP)
    worst = max(dist(a, b) for a, b in zip(offs, offs[1:]))
    check(worst < 0.25, "A3", "最大帧间变化 %.4f px（阈值 0.25）" % worst)


def a4_perceivable():
    log("A4 可感知度（显示框 %.0f×%.0f）" % (DISPLAY_W, DISPLAY_H))
    breath_px = DISPLAY_H * at.IDLE_BREATH_AMP
    check(2.0 <= breath_px <= 4.0, "A4",
          "呼吸纵向起伏 %.2f px（<2 看不见、>4 像抖）" % breath_px)
    check(0.8 <= at.IDLE_SWAY_AMP_X <= 2.0, "A4",
          "重心水平摆动 ±%.1f px" % at.IDLE_SWAY_AMP_X)
    tip = at.IDLE_TILT_AMP_DEG * math.pi / 180.0 * (DISPLAY_H * 0.5)
    check(0.8 <= tip <= 2.5, "A4",
          "微摆端点位移 %.2f px（%.2f°）" % (tip, at.IDLE_TILT_AMP_DEG))


def a5_not_repeating(gap=200.0):
    log("A5 不重复（t 与 t+%.0fs 的姿态距离）" % gap)
    dists = [dist(at.idle_offsets(i * 0.25), at.idle_offsets(i * 0.25 + gap))
             for i in range(240)]
    check(min(dists) > 0.02, "A5", "最小距离 %.4f > 0.02（无重合）" % min(dists))
    check(sum(dists) / len(dists) > 0.2, "A5",
          "平均距离 %.3f > 0.2" % (sum(dists) / len(dists)))


def a6_composite():
    log("A6 复合周期")
    period = at.idle_composite_period()
    check(200.0 < period < 1e9, "A6",
          "复合周期 %.0f s（%.1f 分钟）> 200 s" % (period, period / 60.0))
    log("     通道：呼吸 %.1fs / 重心 %.1f + %.1fs / 微摆 %.1fs"
        % (at.IDLE_BREATH_PERIOD, at.IDLE_SWAY_PERIODS[0],
           at.IDLE_SWAY_PERIODS[1], at.IDLE_TILT_PERIOD))


def a7_period_count():
    log("A7 周期正确性（60s 内呼吸峰数）")
    vals = [o.scale_y for o in samples(60.0, 0.02)]
    peaks = sum(1 for i in range(1, len(vals) - 1)
                if vals[i] > vals[i - 1] and vals[i] >= vals[i + 1])
    expect = 60.0 / at.IDLE_BREATH_PERIOD
    check(abs(peaks - expect) <= 1.0, "A7",
          "峰数 %d ≈ 期望 %.1f（周期 %.1fs）" % (peaks, expect, at.IDLE_BREATH_PERIOD))


def main():
    log("=== 潜动层（L0）验收：呼吸 / 重心 / 微摆 ===")
    log("口径来源：board/interaction/avatar_timing.idle_offsets（播放层共用同一份）")
    log("")
    a1_neutral()
    log("")
    a2_amplitude()
    log("")
    a3_smoothness()
    log("")
    a4_perceivable()
    log("")
    a5_not_repeating()
    log("")
    a6_composite()
    log("")
    a7_period_count()
    log("")
    log("RESULT: %s (%d 项失败)" % ("OK" if not FAILED else "FAIL", len(FAILED)))
    if FAILED:
        log("失败项：%s" % ", ".join(sorted(set(FAILED))))
    OUT.write_text("\n".join(LOG) + "\n", encoding="utf-8")
    print("日志：%s" % OUT)
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
