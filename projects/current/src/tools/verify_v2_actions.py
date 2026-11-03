# -*- coding: utf-8 -*-
"""P0-4 一致性收口验收：`avatar_action` 取值三处收敛（方案 §6.3 / G3）。

背景：见 docs/玩偶素材丰富填充_方案设计.md §3.3 / §4.1 P0-4。
历史上 `avatar_action` 的取值散在三处且不一致（fsm 认 ack_nod 等三值、mock 送
`wave` 被静默忽略、请求侧白名单无权威来源）。收口后**单一来源**是
`board/runtime/avatar_actions.py`，本脚本断言各处确实跟着它走。

检查项（纯静态一致性，不读像素、不依赖 numpy/PIL）：
  C1 单点自洽：ALLOWED_AVATAR_ACTIONS == ACTION_TO_STATE 键集合；
     别名取值 ⊆ 白名单；DEFAULT_MOCK_ACTION ∈ 白名单。
  C2 fsm 路由：名单内动作经 DIALOGUE_RESPONSE_RECEIVED 上报后落到
     ACTION_TO_STATE 指定状态；状态未落地者（如 P1-1 前的 deny_shake）
     必须被忽略并回落到情绪分档，**不得**落错态。
  C3 mock 产出：default_response_factory 的 avatar_action 归一化后 ∈ 白名单
     （即不再出现"送了但被静默忽略"的取值）。
  C4 素材映射：目标状态已落地的动作，avatar_assets.STATE_ASSET 必须有映射
     （否则播放层会掉回 IDLE，等于动作没演出来）。
  C5 burst 语义：报告目标状态是否在 avatar_assets.BURST_STATES —— 仅报告，
     不判失败（burst/loop 取舍的单点仍是 avatar_assets，P1-1 会改）。

用法（本机无系统 Python，用 ComfyUI 便携解释器）：
    "<PY>" -s tools\\verify_v2_actions.py
输出：控制台 + %TEMP%\\aura_v2_actions.txt（UTF-8）
"""
import sys
from pathlib import Path

AURA = Path(__file__).resolve().parents[1]
if str(AURA) not in sys.path:
    sys.path.insert(0, str(AURA))

import os

from board.interaction import avatar_assets
from board.runtime import avatar_actions as av
from board.runtime.dialogue_client import DialogueRequest, default_response_factory
from board.runtime.dialogue_client.adapter import PROTOCOL_VERSION
from board.runtime.event_bus import EventEnvelope
from board.runtime.events import EventType
from board.runtime.fsm import RuntimeFSM, RuntimeState, speaking_state_name

OUT = Path(os.environ.get("TEMP", ".")) / "aura_v2_actions.txt"
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


def _ev(t, payload=None):
    return EventEnvelope(event_type=t, source="verify", created_at_ms=0,
                         payload=payload or {})


def _to_thinking():
    """按真实链路推进到 THINKING：IDLE→PRESENT→AWAKE→LISTENING→THINKING。

    注意 v2 里 `AUDIO_KWS_DETECTED` 的目标是 AWAKE（先播一次性反应），
    `AUDIO_VAD_END` 要发两次才到 THINKING（AWAKE→LISTENING→THINKING）。
    """
    fsm = RuntimeFSM()
    fsm.handle_event(_ev(EventType.SCENE_PERSON_ENTER))
    fsm.handle_event(_ev(EventType.AUDIO_KWS_DETECTED))
    fsm.handle_event(_ev(EventType.AUDIO_VAD_END))
    fsm.handle_event(_ev(EventType.AUDIO_VAD_END))
    assert fsm.state is RuntimeState.THINKING, "前置链路异常：%s" % fsm.state
    return fsm


def main():
    log("=== P0-4 avatar_action 一致性收口验收 ===")
    log("单一来源：board/runtime/avatar_actions.py")
    log("白名单  ：%s" % (list(av.ALLOWED_AVATAR_ACTIONS),))

    # ---- C1 单点自洽 ----
    log("C1 单点自洽")
    check(set(av.ALLOWED_AVATAR_ACTIONS) == set(av.ACTION_TO_STATE),
          "C1a", "白名单与 ACTION_TO_STATE 键集合一致")
    check(all(v in av.ALLOWED_AVATAR_ACTIONS for v in av.ACTION_ALIASES.values()),
          "C1b", "别名取值均在白名单内：%s" % (av.ACTION_ALIASES,))
    check(av.is_allowed(av.DEFAULT_MOCK_ACTION),
          "C1c", "DEFAULT_MOCK_ACTION=%r 在白名单内" % (av.DEFAULT_MOCK_ACTION,))
    check(not av.is_allowed("wave"),
          "C1d", "旧值 wave 已不在白名单（原本被静默忽略）")

    # ---- C2 fsm 路由 ----
    log("C2 fsm 路由（名单内动作 → 目标状态）")
    for action in av.ALLOWED_AVATAR_ACTIONS:
        want = av.state_for(action)
        landed = want in RuntimeState.__members__
        fsm = _to_thinking()
        fsm.handle_event(_ev(EventType.DIALOGUE_RESPONSE_RECEIVED,
                             {"avatar_action": action, "emotion": "friendly"}))
        got = fsm.state.name
        if landed:
            check(got == want, "C2[%s]" % action,
                  "%s → %s（期望 %s）" % (action, got, want))
        else:
            fallback = speaking_state_name("friendly")
            check(got == fallback, "C2[%s]" % action,
                  "%s 未落地状态 → 回落 %s（期望 %s）" % (action, got, fallback))
    # 别名与未知动作
    fsm = _to_thinking()
    fsm.handle_event(_ev(EventType.DIALOGUE_RESPONSE_RECEIVED,
                         {"avatar_action": " Surprised ", "emotion": "friendly"}))
    check(fsm.state.name == av.state_for("emo_surprised"),
          "C2[alias]", "别名 ' Surprised ' 归一化后与 emo_surprised 同效")
    fsm = _to_thinking()
    fsm.handle_event(_ev(EventType.DIALOGUE_RESPONSE_RECEIVED,
                         {"avatar_action": "wave", "emotion": "friendly"}))
    check(fsm.state.name == speaking_state_name("friendly"),
          "C2[unknown]", "未知动作 wave → 情绪分档兜底（行为与 v2 等价）")

    # ---- C3 mock 产出 ----
    log("C3 mock 适配器产出")
    resp = default_response_factory(DialogueRequest(
        protocol_version=PROTOCOL_VERSION, request_id="verify-1",
        scene_state={"scene_seq": 1, "camera_state": "online", "people_count": 1,
                     "current_target": {"track_id": 7, "position": "left"}}))
    log("  mock avatar_action = %r" % (resp.avatar_action,))
    check(av.is_allowed(resp.avatar_action), "C3a",
          "mock 默认动作在白名单内（修复 §3.3 的静默忽略）")

    # ---- C4 素材映射 ----
    log("C4 素材映射（STATE_ASSET）")
    for action in av.ALLOWED_AVATAR_ACTIONS:
        name = av.state_for(action)
        if name in RuntimeState.__members__:
            check(name in avatar_assets.STATE_ASSET, "C4[%s]" % action,
                  "%s → 素材 %s" % (name, avatar_assets.STATE_ASSET.get(name)))
        else:
            log("  [skip] C4[%s] 状态 %s 尚未落地（P1-1 启用）" % (action, name))

    # ---- C5 burst 语义（仅报告） ----
    log("C5 burst 语义（单点仍是 avatar_assets.BURST_STATES，仅报告）")
    for action in av.ALLOWED_AVATAR_ACTIONS:
        name = av.state_for(action)
        log("  %-14s → %-14s burst=%s" % (
            action, name, name in avatar_assets.BURST_STATES))

    log("=== RESULT: %s (%d 项失败) ===" % ("FAIL" if FAILED else "OK", len(FAILED)))
    if FAILED:
        log("失败项：%s" % (", ".join(FAILED),))
    OUT.write_text("\n".join(LOG), encoding="utf-8")
    print("log -> %s" % OUT, flush=True)
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
