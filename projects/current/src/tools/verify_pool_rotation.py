# -*- coding: utf-8 -*-
"""跨素材池轮换验收（P 系列判据；纯逻辑 / 无窗口 / 零像素开销）。

背景（用户 2026-10-05）："说话不够自然" → 同语义素材**交替播放**（`avatar_assets.POOLS`）。
本脚本驱动 `tools/demo_stage.StageCore`（纯逻辑层，与 Tk 演示台**同一份代码**）逐帧推进时间：

  P1 有池状态：素材在池内**轮换**（不是一直播同一个）
  P2 换素材瞬间：**新素材从 enter（帧 0）起播**（index == 0 且 stage == "enter"）★核心
  P3 切换间隔：≈ POOL_SWITCH_SECONDS + 收起耗时（不过频、不卡死）
  P4 无池状态：素材**恒定**（旧行为零回归）
  P5 burst 状态：**永不**参与轮换（一次性动作不可混播）

数值依据：`%TEMP%\\zz_link.py`（2026-10-05）测得跨素材"上素材末帧 → 下素材首帧"灰阶差
1.18~1.56，**低于素材内部 loop 接缝**（自环 1.21~1.31）⇒ 池内混用安全。

用法（本机无系统 Python，用 aura 自带 .venv）：
    "<AURA>\\.venv\\Scripts\\python.exe" -s tools\\verify_pool_rotation.py
输出：控制台 + %TEMP%\\aura_pool_rotation.txt（UTF-8）
"""
import importlib.util
import os
import sys
from pathlib import Path

AURA = Path(__file__).resolve().parents[1]
if str(AURA) not in sys.path:
    sys.path.insert(0, str(AURA))

# 重定向到文件时 stdout 可能是 GBK（本机默认）→ 统一 UTF-8，避免 UnicodeEncodeError
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

from board.interaction import avatar_assets as aa       # noqa: E402

OUT = Path(os.environ.get("TEMP", ".")) / "aura_pool_rotation.txt"
LOG = []
FAILED = []
STEP = 1.0 / 30.0          # 与演示台 TICK_MS = 33 同口径
T0 = 1000.0                # 任意非零起始时刻（验证"不依赖绝对时间"）


def log(s):
    LOG.append(str(s))
    print(s, flush=True)


def check(cond, code, msg):
    log("  [%s] %s %s" % ("OK " if cond else "FAIL", code, msg))
    if not cond:
        FAILED.append(code)
    return cond


def load_stage_core():
    """按路径加载 `tools/demo_stage.py`（不依赖 tools 是否为包）。"""
    path = AURA / "tools" / "demo_stage.py"
    spec = importlib.util.spec_from_file_location("demo_stage_verify", str(path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.StageCore


def simulate(core, state, seconds):
    """逐帧推进 → [(t, 素材名, 帧索引, 阶段), ...]。"""
    out = []
    now = T0
    for _ in range(int(round(seconds / STEP)) + 1):
        info = core.frame_at(state, now)
        if info is None:
            break
        out.append((now - T0, info.get("asset"), int(info.get("index", -1)),
                    info.get("stage")))
        now += STEP
    return out


def switch_points(samples):
    """素材名变化点 → [(t, 旧素材, 新素材, 帧索引, 阶段), ...]。"""
    out = []
    prev = None
    for t, asset, idx, stage in samples:
        if prev is not None and asset != prev:
            out.append((t, prev, asset, idx, stage))
        prev = asset
    return out


def main():
    StageCore = load_stage_core()
    log("=== 跨素材池轮换验收（%s）===" % AURA)
    log("")
    log("池声明：%s" % {k: list(v) for k, v in aa.POOLS.items()})
    for state in sorted(aa.POOLS):
        names = aa.pool_assets(state)
        log("池 %-18s 声明 %d → 可用 %d：%s"
            % (state, len(aa.POOLS[state]), len(names), list(names)))
    log("")

    # ---- P1 / P2 / P3：有池状态 ----
    for state in sorted(aa.POOLS):
        names = aa.pool_assets(state)
        log("--- %s（可用素材 %s）---" % (state, list(names)))
        if len(names) < 2:
            log("  [SKIP] 可用素材 < 2（新素材尚未入库）→ 无从验证轮换")
            log("")
            continue
        core = StageCore()
        samples = simulate(core, state, 20.0)
        if not samples:
            check(False, "P0", "取不到任何帧（素材缺失）")
            log("")
            continue
        used = {a for _, a, _, _ in samples}
        check(used.issubset(set(names)), "P1",
              "实际播放素材 %s ⊆ 池 %s" % (sorted(used), list(names)))
        check(len(used) >= 2, "P1",
              "模拟窗口内用到 %d 个素材（>1 = 确实在轮换）" % len(used))
        sw = switch_points(samples)
        log("     切换点：%s"
            % ["%.2fs %s→%s(idx=%d,%s)" % s for s in sw])
        check(bool(sw) and all(s[3] == 0 and s[4] == "enter" for s in sw), "P2",
              "换素材后**从 enter（帧 0）起播**（%d 次切换）" % len(sw))
        if len(sw) >= 2:
            gaps = [b[0] - a[0] for a, b in zip(sw, sw[1:])]
            low = 0.5 * core.POOL_SWITCH_SECONDS
            high = 2.0 * core.POOL_SWITCH_SECONDS
            log("     切换间隔：%s" % ["%.2fs" % g for g in gaps])
            check(all(low < g < high for g in gaps), "P3",
                  "间隔落在 (%.1f, %.1f) s（POOL_SWITCH_SECONDS=%.1f + 收起耗时）"
                  % (low, high, core.POOL_SWITCH_SECONDS))
        else:
            log("  [WARN] 模拟窗口内切换 < 2 次 → 无法核对间隔（可加长模拟时长）")
        log("")

    # ---- P4：无池状态（旧行为零回归）----
    log("--- P4 无池状态（IDLE / THINKING：素材必须恒定）---")
    for state in ("IDLE", "THINKING"):
        if state in aa.POOLS:
            continue
        core = StageCore()
        samples = simulate(core, state, 10.0)
        used = {a for _, a, _, _ in samples}
        check(len(used) == 1, "P4",
              "%s 素材恒定：%s（旧行为零回归）" % (state, sorted(used)))
    log("")

    # ---- P5：burst 状态永不参与轮换 ----
    log("--- P5 burst 状态（ACK_NOD：一次性动作，不混播）---")
    core = StageCore()
    samples = simulate(core, "ACK_NOD", 6.0)
    used = {a for _, a, _, _ in samples}
    check(len(used) <= 1, "P5", "ACK_NOD 素材恒定：%s" % sorted(used))
    log("")

    log("=== 结果：%s（失败 %d 项：%s）==="
        % ("OK" if not FAILED else "FAIL", len(FAILED), ",".join(FAILED) or "-"))
    try:
        OUT.write_text("\n".join(LOG), encoding="utf-8")
        log("→ 报告：%s" % OUT)
    except OSError as exc:
        log("→ 报告写入失败：%s" % exc)


if __name__ == "__main__":
    main()
    sys.exit(1 if FAILED else 0)
