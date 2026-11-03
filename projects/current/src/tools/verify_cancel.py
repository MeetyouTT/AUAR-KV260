# -*- coding: utf-8 -*-
"""取消完整性探针（#4）：取消后**在途的旧回复必须作废**（不显示、不进状态机、不播放）。

背景（2026-10-04 外部审查 #4）：取消**只改状态**，没有停 TTS；取消后迟到的旧回复仍会被显示并念出。
修复方式（`demo_stage.StageCore`）：给每轮对话一个**代次** `talk_gen`，取消 / 重发令其递增，
回程用 `accept_response(gen, data)` 校验 —— 旧代次直接判废。本脚本用**纯逻辑**验证该机制。

用法：
    "<AURA>\\.venv\\Scripts\\python.exe" -s tools\\verify_cancel.py
输出：控制台 + %TEMP%\\aura_cancel.txt（UTF-8）
"""
import os
import sys
from pathlib import Path

AURA = Path(__file__).resolve().parents[1]
if str(AURA) not in sys.path:
    sys.path.insert(0, str(AURA))

from board.runtime.events import EventType             # noqa: E402

sys.path.insert(0, str(AURA / "tools"))                # tools 不是包 → 按目录直接导入
from demo_stage import StageCore                       # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

OUT = Path(os.environ.get("TEMP", ".")) / "aura_cancel.txt"
LOG = []
FAILED = []
REPLY = {"emotion": "neutral", "avatar_action": "", "reply_text": "这是一条迟到的旧回复。"}


def log(s):
    LOG.append(str(s))
    print(s, flush=True)


def check(cond, code, msg):
    log("  [%s] %s %s" % ("OK " if cond else "FAIL", code, msg))
    if not cond:
        FAILED.append(code)
    return cond


def main():
    log("=== 取消完整性探针（#4）===")
    log("")

    # C1 正常一轮：发起 → 响应回程应被接受
    log("C1 正常一轮（响应应被接受）")
    core = StageCore()
    gen = core.new_turn()
    accepted = core.accept_response(gen, REPLY)
    check(accepted and core.reply_text == REPLY["reply_text"], "C1",
          "gen=%s 被接受，reply_text=%r" % (gen, core.reply_text[:12]))
    log("")

    # C2 取消后旧响应作废（核心场景）
    log("C2 取消后旧响应必须作废")
    core = StageCore()
    gen = core.new_turn()                    # 发起（在途）
    core.cancel()                            # 用户取消
    before = core.reply_text
    accepted = core.accept_response(gen, REPLY)   # 旧回复迟到
    check(not accepted, "C2", "旧代次 gen=%s 被拒绝（accepted=%s）" % (gen, accepted))
    check(core.reply_text == before, "C2",
          "回复文本未被旧响应覆盖（仍为 %r）" % (core.reply_text[:12],))
    log("")

    # C3 取消后重新发起 → 新响应接受、更旧的仍然作废
    log("C3 取消后重发（新代次接受 / 更旧代次作废）")
    core = StageCore()
    gen1 = core.new_turn()
    core.cancel()
    gen2 = core.new_turn()
    check(core.accept_response(gen1, REPLY) is False, "C3", "gen1=%s 作废" % gen1)
    check(core.accept_response(gen2, REPLY) is True, "C3", "gen2=%s 接受" % gen2)
    log("")

    # C4 取消 / 重发 对 cancelled 标志的影响
    log("C4 cancelled 标志")
    core = StageCore()
    core.new_turn()
    check(core.cancelled is False, "C4", "发起后 cancelled=False")
    core.cancel()
    check(core.cancelled is True, "C4", "取消后 cancelled=True")
    core.new_turn()
    check(core.cancelled is False, "C4", "重发后 cancelled=False")
    log("")

    # C5 非法代次（None / 非数字）→ 一律拒绝（安全默认）
    log("C5 非法代次一律拒绝")
    core = StageCore()
    core.new_turn()
    check(core.accept_response(None, REPLY) is False, "C5", "gen=None → 拒绝")
    check(core.accept_response("abc", REPLY) is False, "C5", "gen='abc' → 拒绝")
    log("")

    # C6 取消同时送 FSM 事件 → 状态回迁（有人在 → PRESENT）
    log("C6 取消送事件 → FSM 回迁")
    core = StageCore()
    core.send(EventType.SCENE_PERSON_ENTER)
    core.send(EventType.BOARD_KEY_PRESSED)          # → LISTENING
    core.cancel()
    core.send(EventType.AUDIO_CANCEL_REQUESTED)
    check(core.fsm.state.value == "PRESENT", "C6",
          "取消后状态 = %s（有人在 → PRESENT）" % core.fsm.state.value)
    log("")

    log("RESULT: %s（%d 项失败）" % ("OK" if not FAILED else "FAIL", len(FAILED)))
    if FAILED:
        log("失败项：%s" % ", ".join(sorted(set(FAILED))))
    log("")
    log("⚠ 本脚本只覆盖**代次作废（显示/状态机侧）**；『停 TTS』由 demo_stage.cancel_talk() 调 tts.stop()，"
        "需在真实窗口 / 有音频环境复核。")
    OUT.write_text("\n".join(LOG) + "\n", encoding="utf-8")
    print("日志：%s" % OUT)
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
