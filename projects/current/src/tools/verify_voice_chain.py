# -*- coding: utf-8 -*-
"""语音事件链探针：把典型事件序列跑一遍真 `RuntimeFSM`，打印"事件 → 状态 → 是否被拒"表。

背景（2026-10-04 外部审查实测，本脚本用于**复现 + 回归**）：
  · **#1 KWS 唤醒链**：`PRESENT→AWAKE→LISTENING` 后收到回复**被拒**（要连发两次"说完"才进思考）；
  · **#1 附**：`AWAKE` 期间收到 `AUDIO_PLAYBACK_STOP` **被拒**（缺"唤醒动画结束"编排）；
  · **#2 麦克风链**：识别文本送模型时**没有**推进到思考（等价于"聆听中收不到 VAD_END 的效果"）。

判据：用 `fsm.rejected_count` 的**差值**判断单步是否被拒（同状态迁移也返回 None，不能只看返回值）。

用法：
    "<AURA>\\.venv\\Scripts\\python.exe" -s tools\\verify_voice_chain.py
输出：控制台 + %TEMP%\\aura_voice_chain.txt（UTF-8）
"""
import os
import sys
from pathlib import Path

AURA = Path(__file__).resolve().parents[1]
if str(AURA) not in sys.path:
    sys.path.insert(0, str(AURA))

from board.runtime.event_bus import EventEnvelope      # noqa: E402
from board.runtime.events import EventType             # noqa: E402
from board.runtime.fsm import RuntimeFSM               # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

OUT = Path(os.environ.get("TEMP", ".")) / "aura_voice_chain.txt"
LOG = []
FAILED = []


def log(s):
    LOG.append(str(s))
    print(s, flush=True)


def check(cond, code, msg):
    log("  [%s] %s %s" % ("OK " if cond else "FAIL", code, msg))
    if not cond:
        FAILED.append(code)
    return cond


# (链名, [(事件名, payload)], 期望状态序列（含初始态）)
CHAINS = (
    ("① 按键链（现状应通过）", (
        ("SCENE_PERSON_ENTER", {}),
        ("BOARD_KEY_PRESSED", {}),
        ("AUDIO_VAD_END", {}),
        ("DIALOGUE_RESPONSE_RECEIVED", {"emotion": "neutral"}),
        ("AUDIO_PLAYBACK_STOP", {}),
    ), ("IDLE", "PRESENT", "LISTENING", "THINKING", "SPEAKING_NEUTRAL", "IDLE")),

    ("② KWS 唤醒完整链（#1 现状应失败）", (
        ("SCENE_PERSON_ENTER", {}),
        ("AUDIO_KWS_DETECTED", {}),
        ("AUDIO_VAD_END", {}),
        ("DIALOGUE_RESPONSE_RECEIVED", {"emotion": "neutral"}),
        ("AUDIO_PLAYBACK_STOP", {}),
    ), ("IDLE", "PRESENT", "AWAKE", "THINKING", "SPEAKING_NEUTRAL", "IDLE")),

    ("③ 唤醒动画播完 → 进聆听（#1 附，现状应失败）", (
        ("AUDIO_KWS_DETECTED", {}),
        ("AUDIO_PLAYBACK_STOP", {}),
    ), ("IDLE", "AWAKE", "LISTENING")),

    ("④ 麦克风链：聆听中一句说完即进思考（#2）", (
        ("BOARD_KEY_PRESSED", {}),
        ("AUDIO_VAD_END", {}),
        ("DIALOGUE_RESPONSE_RECEIVED", {"emotion": "happy"}),
        ("AUDIO_PLAYBACK_STOP", {}),
    ), ("IDLE", "LISTENING", "THINKING", "SPEAKING", "IDLE")),

    ("⑤ 唤醒后直接收到回复（快路径兜底）", (
        ("AUDIO_KWS_DETECTED", {}),
        ("DIALOGUE_RESPONSE_RECEIVED", {"emotion": "neutral"}),
    ), ("IDLE", "AWAKE", "SPEAKING_NEUTRAL")),

    # 取消：CANCELLED 是**瞬时态**，按"是否有人在"立刻回迁（有人在 → PRESENT）
    ("⑥ 取消回迁（有人在时；#4 的停播 / 丢旧响应不在此覆盖）", (
        ("SCENE_PERSON_ENTER", {}),
        ("BOARD_KEY_PRESSED", {}),
        ("AUDIO_CANCEL_REQUESTED", {}),
    ), ("IDLE", "PRESENT", "LISTENING", "PRESENT")),
)


def run_chain(name, steps, expect):
    fsm = RuntimeFSM(publish_state_changes=False)
    log("【%s】" % name)
    log("     期望：%s" % " → ".join(expect))
    actual = [fsm.state.value]
    rejected_steps = []
    for evt_name, payload in steps:
        evt = getattr(EventType, evt_name, None)
        if evt is None:
            log("     事件不存在：%s（跳过整条链）" % evt_name)
            return
        before = fsm.rejected_count
        fsm.handle_event(EventEnvelope(event_type=evt, source="probe",
                                       created_at_ms=0, payload=payload))
        rejected = fsm.rejected_count > before
        if rejected:
            rejected_steps.append(evt_name)
        actual.append(fsm.state.value)
        log("     %-30s → %-16s %s"
            % (evt_name, fsm.state.value, "★被拒" if rejected else ""))
    log("     实际：%s" % " → ".join(actual))
    if rejected_steps:
        log("     被拒事件：%s" % ", ".join(rejected_steps))
    check(actual == list(expect), "V%s" % name[0], "链结果与期望一致")
    log("")


def main():
    log("=== 语音事件链探针（真 RuntimeFSM）===")
    log("")
    for name, steps, expect in CHAINS:
        run_chain(name, steps, expect)
    log("RESULT: %s（%d 条链不符合期望）" % ("OK" if not FAILED else "FAIL", len(FAILED)))
    if FAILED:
        log("失败链：%s" % ", ".join(sorted(set(FAILED))))
    OUT.write_text("\n".join(LOG) + "\n", encoding="utf-8")
    print("日志：%s" % OUT)
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
