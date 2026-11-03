# -*- coding: utf-8 -*-
"""P0-2 播放时序验收：相位随机化 + 轻度变速（方案 §4.1 P0-2 / §6.1）。

纯逻辑（不依赖 Qt / PIL / numpy），取帧口径与播放层**共用**
`board/interaction/avatar_timing.py` —— 这是"验收测的就是播放层"的前提
（见 .cline-handover.md 第 28 条：本机无 PySide6，验收脚本拿不到 qt_widgets）。

检查项：
  T1 限幅：speed 恒在 [0.85, 1.15]；非法输入回落 1.0
  T2 单调：字越多 → speed 越小
  T3 只对播报三档生效：其余状态恒 1.0
  T4 burst 不加相位、不变速（一次性动作必须从第 0 帧起播）
  T5 相位 ∈ [0, duration) 且随机（多次抽样离散）
  T6 基线（改前）：speed=1.0 / phase=0 → 采样序列精确周期 = 素材帧数（39 = 1.625s）
  T7 改后：按三档句长各自 speed 采样 → 精确周期不再等于素材帧数（循环节被打散）
  T8 入场一致被消除：改前多次入场首帧恒同帧；改后分散

用法（本机无系统 Python，用 ComfyUI 便携解释器）：
    "<PY>" -s tools\\verify_v2_timing.py
输出：控制台 + %TEMP%\\aura_v2_timing.txt（UTF-8）
"""
import os
import sys
from pathlib import Path

AURA = Path(__file__).resolve().parents[1]
if str(AURA) not in sys.path:
    sys.path.insert(0, str(AURA))

from board.interaction import avatar_assets
from board.interaction import avatar_timing as at

OUT = Path(os.environ.get("TEMP", ".")) / "aura_v2_timing.txt"
LOG = []
FAILED = []

DEMO_STATE = "SPEAKING_NEUTRAL"     # 演示素材：中性播报（loop，命中率最高的档）
TEXTS = {
    "短句 10 字": "好的，我帮你把灯打开。",
    "中句 30 字": "我看到画面左侧有一位来访者，他正站在门口，手里拿着一封信。",
    "长句 80 字": ("我看到画面左侧有一位来访者，他先在门口停了一会儿，然后向房间里走了两步，"
                   "又把手里那封信举起来晃了晃，像是在确认我有没有注意到他；如果你愿意，"
                   "我也可以先替你打个招呼，再问问他今天来找谁。"),
}


def log(s):
    LOG.append(str(s))
    print(s, flush=True)


def check(cond, code, msg):
    log("  [%s] %s" % ("OK " if cond else "FAIL", "%s %s" % (code, msg)))
    if not cond:
        FAILED.append(code)
    return cond


def demo_spec():
    """真实素材规格（frames/fps/seconds/burst）；素材缺失则回落 v2 规格。"""
    directory = avatar_assets.frames_dir(DEMO_STATE)
    if directory is not None:
        frames = avatar_assets.list_frames(directory)
        fps = avatar_assets.frames_fps(directory)
        if frames:
            return {"asset": directory.name, "frames": len(frames), "fps": fps,
                    "seconds": len(frames) / fps,
                    "burst": DEMO_STATE in avatar_assets.BURST_STATES}
    return {"asset": "(回落 v2 规格)", "frames": 39, "fps": 24.0,
            "seconds": 39 / 24.0, "burst": False}


def main():
    spec = demo_spec()
    log("=== P0-2 播放时序验收（相位随机化 + 轻度变速）===")
    log("口径：board/interaction/avatar_timing.py（与 qt_widgets 播放层同一份）")
    log("素材：%s · %d 帧 @%.2f fps · %.3f s · %s"
        % (spec["asset"], spec["frames"], spec["fps"], spec["seconds"],
           "burst" if spec["burst"] else "loop"))

    # ---- T1 限幅 ----
    log("T1 速度限幅")
    check(at.speed_for_text("") == 1.0, "T1a", "无文本 → 中性 1.0")
    check(at.clamp_speed(9.9) == at.MAX_SPEED, "T1b", "越界上夹紧 → %.2f" % at.MAX_SPEED)
    check(at.clamp_speed(0.01) == at.MIN_SPEED, "T1c", "越界下夹紧 → %.2f" % at.MIN_SPEED)
    check(at.clamp_speed("bad") == 1.0, "T1d", "非法输入 → 1.0")
    speeds = [at.speed_for_text(t) for t in TEXTS.values()]
    check(all(at.MIN_SPEED <= s <= at.MAX_SPEED for s in speeds), "T1e",
          "所有档位速度 ∈ [%.2f, %.2f]：%s"
          % (at.MIN_SPEED, at.MAX_SPEED, ["%.3f" % s for s in speeds]))

    # ---- T2 单调 ----
    log("T2 句长单调（字越多 → 越慢）")
    seq = [at.speed_for_text("字" * n) for n in (5, 15, 30, 45, 80)]
    log("  n=5/15/30/45/80 → %s" % (["%.3f" % s for s in seq],))
    check(all(seq[i] >= seq[i + 1] for i in range(len(seq) - 1)), "T2a",
          "速度随句长单调不增")

    # ---- T3 仅播报档 ----
    log("T3 仅播报三档变速")
    for st in ("IDLE", "PRESENT", "LISTENING", "THINKING", "AWAKE", "ACK_NOD"):
        check(at.speed_for_state(st, TEXTS["长句 80 字"]) == 1.0,
              "T3[%s]" % st, "%s 恒 1.0" % st)
    for st in at.SPEAKING_STATES:
        check(at.speed_for_state(st, TEXTS["长句 80 字"]) == at.MIN_SPEED,
              "T3[%s]" % st, "%s 按句长变速" % st)

    # ---- T4 burst 不受影响 ----
    log("T4 burst 一次性动作不加相位/不变速")
    check(at.frame_time(1.5, burst=True, phase=5.0, speed=0.5) == 1.5, "T4a",
          "burst 原样返回（从第 0 帧起播、不被拉长）")
    check(at.frame_time(1.5, burst=False, phase=5.0, speed=0.9, drift=False) == 6.35, "T4b",
          "loop（关 drift）→ t*speed+phase = 1.5*0.9+5.0 = 6.35")
    check(at.frame_time(1.5, burst=False, phase=0.0, speed=0.5, drift=False) == 1.275, "T4c",
          "速度越界仍夹紧：1.5*0.85(夹紧后)+0.0 = 1.275")
    check(at.frame_time(0.0, burst=False, drift=True) == 0.0, "T4d",
          "drift 在 t=0 不偏移（入场仍从第 0 帧起，与相位随机化兼容）")
    check(abs(at.frame_time(1.5, burst=False, drift=True) - 1.5) > 1e-6, "T4e",
          "drift 生效：t=1.5s 时等效时间已偏离原值（去机械化）")

    # ---- T5 相位 ----
    log("T5 相位随机化")
    phases = [at.random_phase(spec["seconds"]) for _ in range(64)]
    check(all(0.0 <= p < spec["seconds"] for p in phases), "T5a",
          "phase ∈ [0, duration=%.3f)" % spec["seconds"])
    check(len(set(round(p, 6) for p in phases)) >= 60, "T5b",
          "64 次抽样得到 %d 个不同值（随机，非常量）"
          % len(set(round(p, 6) for p in phases)))
    check(at.random_phase(0.0) == 0.0, "T5c", "duration=0 → phase 0.0")

    return _finish(spec)


def _finish(spec):
    """T6~T8（改前基线 / 改后对比 / 入场一致性）+ 收尾。"""
    # ---- T6 基线：改前的循环节 = 素材时长 ----
    log("T6 基线（改前：phase=0 / speed=1.0）")
    before = at.sample_frame_indices(spec["frames"], spec["fps"], spec["burst"],
                                     4.0, phase=0.0, speed=1.0, out_fps=24.0, drift=False)
    per_before = at.exact_period(before)
    log("  采样 %d 点；精确周期 = %s 点 = %s s"
        % (len(before), per_before,
           ("%.3f" % (per_before / 24.0)) if per_before else "-"))
    check(per_before == spec["frames"], "T6a",
          "改前精确周期 = 素材帧数 %d（= 素材时长 %.3fs，肉眼可辨的循环节）"
          % (spec["frames"], spec["seconds"]))

    # ---- T7 改后：周期不再固定 ----
    log("T7 改后（随机相位 + 按句长变速）")
    for label, text in TEXTS.items():
        speed = at.speed_for_text(text)
        phase = at.random_phase(spec["seconds"])
        after = at.sample_frame_indices(spec["frames"], spec["fps"], spec["burst"],
                                        4.0, phase=phase, speed=speed, out_fps=24.0,
                                        drift=False)
        per_after = at.exact_period(after)
        log("  %s：%d 字 → 预计 %.1fs → speed %.3f → 精确周期 %s"
            % (label, len(text), at.estimate_seconds(text), speed,
               ("%s 点 (%.3fs)" % (per_after, per_after / 24.0)) if per_after else "无（已打散）"))
        check(per_after != spec["frames"], "T7[%s]" % label,
              "精确周期不再等于素材帧数（不再固定 %.3fs 循环）" % spec["seconds"])

    # ---- T8 入场一致被消除 ----
    log("T8 入场一致性（多次重新入场，取 t=0.3s 的帧）")
    fixed, spread = set(), set()
    for _ in range(32):
        fixed.add(at.frame_index(0.3, spec["frames"], spec["fps"], spec["burst"]))
        ph = at.random_phase(spec["seconds"])
        spread.add(at.frame_index(at.frame_time(0.3, burst=False, phase=ph, drift=False),
                                  spec["frames"], spec["fps"], spec["burst"]))
    log("  改前首帧 %d 种 %s；改后 %d 种（前 8 个 %s）"
        % (len(fixed), sorted(fixed), len(spread), sorted(spread)[:8]))
    check(len(fixed) == 1, "T8a", "改前 32 次入场首帧恒为同一帧（G1 入场一致）")
    check(len(spread) >= 8, "T8b",
          "改后 32 次入场得到 %d 种首帧（入场一致已消除）" % len(spread))

    # ---- T9 去机械化（用户反馈的"长时间机械循环"）：周期被打散 ----
    log("T9 长时间循环（30s）周期对比")
    seq_off = at.sample_frame_indices(spec["frames"], spec["fps"], spec["burst"], 30.0,
                                      phase=0.0, speed=1.0, out_fps=24.0, drift=False)
    seq_on = at.sample_frame_indices(spec["frames"], spec["fps"], spec["burst"], 30.0,
                                     phase=0.0, speed=1.0, out_fps=24.0, drift=True)
    per_off = at.exact_period(seq_off)
    per_on = at.exact_period(seq_on)
    log("  关 drift：精确周期 = %s 点（= 素材时长 %.3fs 的精确重复）"
        % (per_off, spec["seconds"]))
    log("  开 drift：精确周期 = %s" % (per_on,))
    check(per_off == spec["frames"], "T9a",
          "关 drift 时精确周期 = 素材帧数 %d（机械循环的量化基线）" % spec["frames"])
    check(per_on != spec["frames"], "T9b",
          "开 drift 后周期不再等于素材帧数（长时间循环被打散）：%s" % (per_on,))

    log("=== RESULT: %s (%d 项失败) ===" % ("FAIL" if FAILED else "OK", len(FAILED)))
    if FAILED:
        log("失败项：%s" % (", ".join(FAILED),))
    OUT.write_text("\n".join(LOG), encoding="utf-8")
    print("log -> %s" % OUT, flush=True)
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
