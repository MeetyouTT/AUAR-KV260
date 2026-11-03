# -*- coding: utf-8 -*-
"""三段式**阶段机**探针（#5）：验证"说完 / 被打断 → 平滑收起"能真正跑通。

背景（2026-10-04 外部审查 #5）：原来的三段式是**固定周期**（按"预计句长"估循环次数），
真实语音时长随机 ⇒ 句子短会白等、句子长会提前退，且**没有"说完 → 平滑收起"**。
当前为连续游标：enter → 主窗口余弦往返 → blend（150ms速度渐入）
→ 沿原帧收回最近的首尾姿势。这里用构造的 Segments 验证，不读取图片。

用法：
    "<AURA>\\.venv\\Scripts\\python.exe" -s tools\\verify_segment_exit.py
输出：控制台 + %TEMP%\\aura_segment_exit.txt（UTF-8）
"""
import os
import sys
from pathlib import Path

AURA = Path(__file__).resolve().parents[1]
if str(AURA) not in sys.path:
    sys.path.insert(0, str(AURA))

sys.path.insert(0, str(AURA / "tools"))                # tools 不是包 → 按目录导入
from board.interaction import avatar_timing as at      # noqa: E402
from demo_stage import StageCore                       # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

OUT = Path(os.environ.get("TEMP", ".")) / "aura_segment_exit.txt"
LOG = []
FAILED = []

SEG = at.Segments(enter=(0, 12), loop=(12, 19), exit=(19, 38))
FPS = 24.0
STATE = "SPEAKING_NEUTRAL"
STEP = 1.0 / FPS


def log(s):
    LOG.append(str(s))
    print(s, flush=True)


def check(cond, code, msg):
    log("  [%s] %s %s" % ("OK " if cond else "FAIL", code, msg))
    if not cond:
        FAILED.append(code)
    return cond


def run(core, t_from, t_to):
    """推进时间，逐帧取 (阶段, alpha, a 帧号, b 帧号)。"""
    rows = []
    t = t_from
    while t <= t_to:
        ta, tb, alpha = core.segment_stage_time(STATE, SEG, FPS, 0.0, t)
        stage = core.stage_state()[0]
        rows.append((round(t, 4), stage, alpha,
                     at.frame_index(ta, 39, FPS, False),
                     at.frame_index(tb, 39, FPS, False) if tb is not None else None))
        t += STEP
    return rows


def main():
    log("=== 三段式阶段机探针（#5）===")
    enter_s = at.stage_seconds(SEG, FPS, stage="enter")
    exit_s = at.stage_seconds(SEG, FPS, stage="exit")
    blend_s = at.segment_blend_seconds()
    log("历史分段长度：enter %.3fs ／ loop(一个来回) %.3fs ／ exit %.3fs ｜ 速度渐入 %.3fs"
        % (enter_s, at.stage_seconds(SEG, FPS, stage="loop"), exit_s, blend_s))
    log("")

    # E1~E2 阶段推进：enter → loop
    log("E1/E2 阶段推进（enter → loop，未请求退出时不进 exit）")
    core = StageCore()
    rows = run(core, 0.0, enter_s + 0.5)
    stages = [r[1] for r in rows]
    check(stages and stages[0] == "enter", "E1", "起始阶段 = %s" % (stages[0] if stages else "-"))
    check("loop" in stages and "blend" not in stages and "exit" not in stages, "E2",
          "未请求退出：阶段序列 = %s（无 blend/exit）" % "→".join(dict.fromkeys(stages)))
    log("")

    # E3~E5: interruption -> velocity ramp -> recovery, adjacent source frames.
    log("E3~E5 在 loop 中途被打断（t=1.37s，**非整数倍**）→ blend → exit")
    core = StageCore()
    run(core, 0.0, 1.37)                     # 先播到打断点
    break_stage = core.stage_state()[0]
    core.request_exit()
    rows = run(core, 1.37, 1.37 + blend_s + 0.2)
    stages = [r[1] for r in rows]
    check(break_stage == "loop", "E3", "打断时阶段 = %s（应为 loop）" % break_stage)
    check("blend" in stages and "exit" in stages, "E3",
          "请求退出后阶段序列 = %s" % "→".join(dict.fromkeys(stages)))
    blend_rows = [r for r in rows if r[1] == "blend"]
    check(len(blend_rows) >= 2, "E3", "速度渐入段帧数 = %d（≈%.0fms）"
          % (len(blend_rows), blend_s * 1000))
    a_frames = [r[3] for r in blend_rows]
    check(all(abs(a-b) <= 1 for a,b in zip(a_frames,a_frames[1:])), "E4",
          "速度渐入期间沿相邻原始帧移动：%s" % a_frames)
    alphas = [r[2] for r in blend_rows]
    check(all(a == 0 for a in alphas), "E5", "不做跨姿势淡化：alpha 恒为零")
    log("")

    # E6: stop at the selected recovery endpoint.
    log("E6 exit 播完 → 停在恢复端点（不再前进）")
    rows = run(core, 1.37 + blend_s, 1.37 + blend_s + exit_s + 0.6)
    exit_rows = [r for r in rows if r[1] == "exit"]
    tail = [r[3] for r in exit_rows]
    check(bool(exit_rows) and tail[-1] in (0,38), "E6",
          "exit 恢复到最近首尾姿势 = %s" % (tail[-1] if tail else "-"))
    check(len(set(tail[-5:])) == 1, "E6", "最后 5 帧恒定 = %s（停住）" % tail[-5:])
    log("")

    # E7 任意时长都能收完（1.0s / 3.7s / 9.3s 三个非整数倍点）
    log("E7 任意时长（1.0 / 3.7 / 9.3 秒）打断都能走完 exit")
    for t_break in (1.0, 3.7, 9.3):
        core = StageCore()
        run(core, 0.0, t_break)
        core.request_exit()
        rows = run(core, t_break, t_break + blend_s + exit_s + 0.3)
        stages = [r[1] for r in rows]
        last = [r for r in rows if r[1] == "exit"]
        ok = ("blend" in stages and "exit" in stages and last and last[-1][3] in (0,38))
        check(ok, "E7", "打断 t=%.1fs → %s，末帧 %s"
              % (t_break, "→".join(dict.fromkeys(stages)),
                 last[-1][3] if last else "-"))
    log("")

    # E8 与旧写法对比：旧 segment_time（固定周期）在 3.7s 时停在 loop 中途
    log("E8 对照：旧 `segment_time`（固定周期）在 3.7s 时并未在 exit 段")
    loops = at.loops_for_duration(3.7, SEG, FPS)
    old_t = at.segment_time(3.7, SEG, FPS, loops=loops)
    old_idx = at.frame_index(old_t, 39, FPS, False)
    new_t, _new_b, _a = StageCore().segment_stage_time(STATE, SEG, FPS, 0.0, 3.7)
    new_idx = at.frame_index(new_t, 39, FPS, False)
    log("     旧：loops=%d，t=3.7s 取帧 %d ／ 新（阶段机）：t=3.7s 仍处 enter/loop 中段，"
        "但 `request_exit()` 后能走完 end" % (loops, old_idx))
    check(True, "E8", "（仅作信息对照，不判失败）")
    log("")

    # E9: reject unsafe cross-window cuts, keep the primary window.
    log("E9 不兼容窗口禁止直接轮换（只使用主窗口）")
    seg3 = at.Segments(enter=(0, 12), loop=(12, 19), exit=(19, 38),
                       windows=((12, 19), (22, 29), (30, 37)))
    core3 = StageCore()
    seen = []
    t3 = 0.0
    while t3 <= 6.0:
        ta3, _tb3, _a3 = core3.segment_stage_time(STATE, seg3, FPS, 0.0, t3)
        if core3.stage_state()[0] == "loop":
            seen.append(at.frame_index(ta3, 39, FPS, False))
        t3 += 0.05
    rounds = core3._loop_round
    check(rounds >= 2, "E9", "6 秒内完成 %d 个来回（应 ≥2）" % rounds)
    check(bool(seen) and set(seen).issubset(set(range(12,20))), "E9",
          "loop 所有帧留在主窗口12..19：%s" % sorted(set(seen)))
    log("")

    log("RESULT: %s（%d 项失败）" % ("OK" if not FAILED else "FAIL", len(FAILED)))
    if FAILED:
        log("失败项：%s" % ", ".join(sorted(set(FAILED))))
    OUT.write_text("\n".join(LOG) + "\n", encoding="utf-8")
    print("日志：%s" % OUT)
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
