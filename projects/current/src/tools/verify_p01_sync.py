# -*- coding: utf-8 -*-
"""P0-1 验收：一次性动作与说话的**同步**（方案 §4.1 P0-1）。

问题（实机观测到）：LLM 返回 `avatar_action=ack_nod` 时，玩偶只点头 0.92s（burst 素材播完
**夹末帧静止**），而 TTS 还在念 3~5 秒 → 观感"玩偶没跟上语音"。

修法：动作段播完 → 若**语音还在**，发**既有**事件 `AUDIO_PLAYBACK_START` 接进按 emotion 分档的
播报档；语音播完（`AUDIO_PLAYBACK_STOP`）才回 IDLE；**纯应答**（没有语音）则保持不动。

检查项
------
  S1 动作段内状态 = ACK_NOD（burst，从第 0 帧起播）
  S2 播完 + 语音还在 → 接进 SPEAKING_*，且**帧号继续变化**（不再静止）
  S3 播完 + 语音已停 → 状态不变（纯应答不被续播）
  S4 语音播完（AUDIO_PLAYBACK_STOP）→ 回 IDLE
  S5 对照"旧行为"：不接续播时，动作段结束→语音结束期间玩偶**静止**；修复后静止时长为 0

用法：`"<PY>" -s tools\\verify_p01_sync.py`；日志 `%TEMP%\\aura_p01_sync.txt`
"""
import os
import sys
from pathlib import Path

AURA = Path(__file__).resolve().parents[1]
if str(AURA) not in sys.path:
    sys.path.insert(0, str(AURA))
sys.path.insert(0, str(AURA / "tools"))

from board.runtime.events import EventType        # noqa: E402
from demo_stage import StageCore                   # noqa: E402

OUT = Path(os.environ.get("TEMP", ".")) / "aura_p01_sync.txt"
REPLY = "你好呀，我是你的桌面玩偶，可以陪你聊天、玩游戏，想和我做朋友吗？"
LOG = []
FAILED = []


def log(s):
    LOG.append(str(s))
    print(s, flush=True)


def check(cond, code, msg):
    log("  [%s] %s" % ("OK " if cond else "FAIL", "%s %s" % (code, msg)))
    if not cond:
        FAILED.append(code)
    return cond


def run_case(tts_busy: bool, auto_continue: bool, action: str = "ack_nod"):
    """跑一次「一次性动作 + 长回复」：返回采样时间线 [(t, state, frame, note), ...]。"""
    core = StageCore()
    core.reply_text = REPLY
    # fsm 合同：DIALOGUE_RESPONSE_RECEIVED 只在 THINKING 被接受 →
    # 先按"按键唤醒 → 说完 VAD"推进（与演示台 _send_llm 的代为推进一致）
    core.send(EventType.BOARD_KEY_PRESSED)     # IDLE → LISTENING
    core.send(EventType.AUDIO_VAD_END)         # LISTENING → THINKING
    core.apply_response({"emotion": "friendly", "avatar_action": action,
                         "reply_text": REPLY})
    timeline = []

    def sample(t, note=""):
        meta = core.frame_at(core.fsm.state.label, 1000.0 + t)
        timeline.append((round(t, 2), core.fsm.state.label,
                         (meta["index"] + 1) if meta else None, note))

    for t in (0.0, 0.3, 0.6, 0.9):          # 动作段（burst 0.917s）
        sample(t)
    sample(0.95, "动作段播完")
    if auto_continue and core.take_burst_finished() and tts_busy:
        core.send(EventType.AUDIO_PLAYBACK_START, {"emotion": core.emotion})
        sample(0.96, "接进播报段")
    for t in (1.2, 2.0, 3.0, 4.0, 5.0):     # 播报段（TTS 仍在念）
        sample(t)
    core.send(EventType.AUDIO_PLAYBACK_STOP)
    sample(5.1, "语音播完")
    return timeline


def frames_of(timeline, lo, hi):
    return [f for (t, _s, f, _n) in timeline if lo <= t <= hi and f is not None]


def main():
    log("=== P0-1 验收：动作与说话同步（ack_nod + 长回复）===")
    log("回复文本：%s（%d 字）" % (REPLY[:24] + "…", len(REPLY)))

    # ---- 修复后：语音还在 → 续播 ----
    fixed = run_case(tts_busy=True, auto_continue=True)
    log("修复后时间线（语音仍在播）：")
    for row in fixed:
        log("    t=%-5s %-16s frame=%-4s %s" % (row[0], row[1], row[2], row[3]))
    check(all(s == "ACK_NOD" for (_t, s, _f, _n) in fixed if _t <= 0.9), "S1",
          "动作段内状态 = ACK_NOD")
    after = [s for (t, s, _f, _n) in fixed if t >= 1.2 and t <= 5.0]
    check(bool(after) and all(s.startswith("SPEAKING") for s in after), "S2a",
          "动作段播完 → 接进播报档：%s" % sorted(set(after)))
    frames = frames_of(fixed, 1.2, 5.0)
    check(len(set(frames)) >= 3, "S2b",
          "播报段帧号在变化（不再静止）：%s" % frames)
    check(fixed[-1][1] == "IDLE", "S4", "语音播完 → %s" % fixed[-1][1])

    # ---- 纯应答：语音已停 → 不续播 ----
    idle_case = run_case(tts_busy=False, auto_continue=True)
    after2 = [s for (t, s, _f, _n) in idle_case if 1.2 <= t <= 5.0]
    check(after2 and all(s == "ACK_NOD" for s in after2), "S3",
          "语音已停 → 不续播，保持 %s（纯应答语义）" % sorted(set(after2)))

    # ---- 对照旧行为：静止时长 ----
    old = run_case(tts_busy=True, auto_continue=False)
    old_static = 5.0 - 0.95
    new_frames = frames_of(fixed, 0.95, 5.0)
    new_static = 0.0 if len(set(new_frames)) >= 3 else 5.0 - 0.95
    log("对照：旧行为（不接续播）动作段结束后静止 ≈%.2fs；修复后静止 %.2fs"
        % (old_static, new_static))
    check(new_static < 0.5, "S5",
          "修复后'语音仍在播但玩偶静止'的时长 = %.2fs（旧行为 ≈%.2fs）"
          % (new_static, old_static))
    check(all(s == "ACK_NOD" for (t, s, _f, _n) in old if 1.2 <= t <= 5.0), "S5b",
          "旧行为确实停在 ACK_NOD 末帧（问题复现）")

    # ---- P1-1：摇头（deny_shake）走同一条"动作段 → 播报段"链路 ----
    deny_case = run_case(tts_busy=True, auto_continue=True, action="deny_shake")
    deny_during = [s for (t, s, _f, _n) in deny_case if t <= 0.9]
    deny_after = [s for (t, s, _f, _n) in deny_case if 1.2 <= t <= 5.0]
    log("deny_shake 时间线：动作段 %s → 播报段 %s"
        % (sorted(set(deny_during)), sorted(set(deny_after))))
    check(all(s == "DENY_SHAKE" for s in deny_during), "S6a",
          "动作段内状态 = DENY_SHAKE（新素材与点头同规格）")
    check(bool(deny_after) and all(s.startswith("SPEAKING") for s in deny_after), "S6b",
          "deny_shake 动作段播完 → 同样接进播报档：%s" % sorted(set(deny_after)))

    log("=== RESULT: %s (%d 项失败) ===" % ("FAIL" if FAILED else "OK", len(FAILED)))
    if FAILED:
        log("失败项：%s" % (", ".join(FAILED),))
    OUT.write_text("\n".join(LOG), encoding="utf-8")
    print("log -> %s" % OUT, flush=True)
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
