# -*- coding: utf-8 -*-
"""FSM 单测：10 态转换、CANCELLED 瞬时回迁、异常态覆盖、播报情绪分档。"""
from board.runtime import avatar_actions as av
from board.runtime.event_bus import EventBus, EventEnvelope
from board.runtime.events import EventType
from board.runtime.fsm import LOW_EMOTIONS, RuntimeFSM, RuntimeState, is_low_emotion


def ev(t, p=None, src="test"):
    return EventEnvelope(event_type=t, source=src, created_at_ms=0, payload=p or {})


def test_initial_idle():
    assert RuntimeFSM().state == RuntimeState.IDLE


def test_person_enter_present_exit_idle():
    fsm = RuntimeFSM()
    fsm.handle_event(ev(EventType.SCENE_PERSON_ENTER))
    assert fsm.state == RuntimeState.PRESENT
    assert fsm.has_presence is True
    fsm.handle_event(ev(EventType.SCENE_PERSON_EXIT))
    assert fsm.state == RuntimeState.IDLE
    assert fsm.has_presence is False


def test_full_dialogue_flow():
    fsm = RuntimeFSM()
    fsm.handle_event(ev(EventType.SCENE_PERSON_ENTER))     # IDLE → PRESENT
    fsm.handle_event(ev(EventType.AUDIO_KWS_DETECTED))      # → LISTENING
    fsm.handle_event(ev(EventType.AUDIO_VAD_END))           # → THINKING
    fsm.handle_event(ev(EventType.DIALOGUE_RESPONSE_RECEIVED))  # → SPEAKING
    fsm.handle_event(ev(EventType.AUDIO_PLAYBACK_STOP))     # → IDLE
    assert fsm.state == RuntimeState.IDLE


def test_cancel_with_presence_resumes_present():
    fsm = RuntimeFSM()
    fsm.handle_event(ev(EventType.SCENE_PERSON_ENTER))
    fsm.handle_event(ev(EventType.AUDIO_KWS_DETECTED))
    fsm.handle_event(ev(EventType.AUDIO_CANCEL_REQUESTED))
    assert fsm.state == RuntimeState.PRESENT  # CANCELLED 瞬时 → PRESENT


def test_cancel_without_presence_resumes_idle():
    fsm = RuntimeFSM()
    fsm.handle_event(ev(EventType.AUDIO_KWS_DETECTED))  # IDLE 唤醒
    fsm.handle_event(ev(EventType.AUDIO_CANCEL_REQUESTED))
    assert fsm.state == RuntimeState.IDLE


def test_camera_lost_from_any_state():
    for target in (RuntimeState.IDLE, RuntimeState.PRESENT, RuntimeState.SPEAKING,
                   RuntimeState.SPEAKING_LOW):
        fsm = RuntimeFSM()
        fsm.reset(target)
        fsm.handle_event(ev(EventType.CAMERA_LOST))
        assert fsm.state == RuntimeState.CAMERA_LOST
        fsm.handle_event(ev(EventType.CAMERA_RECOVERED))
        assert fsm.state == RuntimeState.IDLE


def test_network_lost_and_restored():
    fsm = RuntimeFSM()
    fsm.handle_event(ev(EventType.SCENE_PERSON_ENTER))
    fsm.handle_event(ev(EventType.DIALOGUE_NETWORK_LOST))
    assert fsm.state == RuntimeState.NETWORK_LOST
    # 断网后本地 KWS 仍可进入聆听（本地模式）
    fsm.handle_event(ev(EventType.AUDIO_KWS_DETECTED))
    assert fsm.state == RuntimeState.LISTENING
    fsm.handle_event(ev(EventType.DIALOGUE_NETWORK_RESTORED))
    assert fsm.state == RuntimeState.IDLE


def test_worker_crash_to_error_and_recover():
    fsm = RuntimeFSM()
    fsm.handle_event(ev(EventType.SYSTEM_WORKER_CRASH))
    assert fsm.state == RuntimeState.ERROR
    fsm.handle_event(ev(EventType.SYSTEM_HEALTH_OK))
    assert fsm.state == RuntimeState.IDLE


def test_invalid_transition_rejected():
    fsm = RuntimeFSM()
    # IDLE 下 AUDIO_VAD_END 未定义转换 → 拒绝不崩溃
    ch = fsm.handle_event(ev(EventType.AUDIO_VAD_END))
    assert ch is None
    assert fsm.rejected_count == 1


def test_state_changed_published():
    bus = EventBus(max_size=16)
    fsm = RuntimeFSM(bus=bus)
    changes = []
    bus.subscribe(lambda e: changes.append(e.payload), {EventType.FSM_STATE_CHANGED})
    fsm.handle_event(ev(EventType.SCENE_PERSON_ENTER))
    assert changes
    assert changes[-1]["to"] == "PRESENT"
    assert changes[-1]["trigger"] == EventType.SCENE_PERSON_ENTER


def test_deterministic_sequence():
    """相同事件序列 → 相同状态序列（确定性）。"""
    events = [
        EventType.SCENE_PERSON_ENTER,
        EventType.AUDIO_KWS_DETECTED,
        EventType.AUDIO_VAD_END,
        EventType.DIALOGUE_RESPONSE_RECEIVED,
        EventType.AUDIO_PLAYBACK_STOP,
    ]

    def run():
        fsm = RuntimeFSM()
        states = [fsm.state.label]
        for t in events:
            fsm.handle_event(ev(t))
            states.append(fsm.state.label)
        return states

    assert run() == run()


# --------------------------------------------------------------------------- #
# 播报情绪分档（SPEAKING / SPEAKING_LOW，2026-09-12）
# --------------------------------------------------------------------------- #
def _to_thinking(fsm):
    """IDLE → PRESENT → LISTENING → THINKING（对话链路前四步）。"""
    fsm.handle_event(ev(EventType.SCENE_PERSON_ENTER))
    fsm.handle_event(ev(EventType.AUDIO_KWS_DETECTED))
    fsm.handle_event(ev(EventType.AUDIO_VAD_END))


def test_is_low_emotion_normalization():
    assert is_low_emotion(" Sad ") is True      # 大小写/空白归一
    assert is_low_emotion("低落") is True        # 中文标签
    assert is_low_emotion("happy") is False
    assert is_low_emotion(None) is False
    assert is_low_emotion(3) is False
    assert "sad" in LOW_EMOTIONS


def test_low_emotion_routes_to_speaking_low():
    """回复 emotion 命中低落白名单 → SPEAKING_LOW；播报结束仍回 IDLE。"""
    for emotion in ("sad", "沮丧"):
        fsm = RuntimeFSM()
        _to_thinking(fsm)
        fsm.handle_event(ev(EventType.DIALOGUE_RESPONSE_RECEIVED,
                            {"reply_text": "抱歉。", "emotion": emotion}))
        assert fsm.state == RuntimeState.SPEAKING_LOW
        fsm.handle_event(ev(EventType.AUDIO_PLAYBACK_STOP))
        assert fsm.state == RuntimeState.IDLE


def test_missing_or_high_emotion_stays_speaking():
    """无 emotion 字段 / 非低落标签 → 维持原有 SPEAKING（默认不分档，向后兼容）。"""
    for payload in ({"reply_text": "好呀！"}, {"reply_text": "好呀！", "emotion": "happy"}):
        fsm = RuntimeFSM()
        _to_thinking(fsm)
        fsm.handle_event(ev(EventType.DIALOGUE_RESPONSE_RECEIVED, payload))
        assert fsm.state == RuntimeState.SPEAKING


def test_low_speaking_cancel_resumes_idle():
    fsm = RuntimeFSM()
    fsm.reset(RuntimeState.SPEAKING_LOW)
    fsm.handle_event(ev(EventType.AUDIO_CANCEL_REQUESTED))
    assert fsm.state == RuntimeState.IDLE   # CANCELLED 瞬时 → 无人在场 → IDLE


def test_low_speaking_state_change_published():
    bus = EventBus(max_size=16)
    fsm = RuntimeFSM(bus=bus)
    changes = []
    bus.subscribe(lambda e: changes.append(e.payload), {EventType.FSM_STATE_CHANGED})
    _to_thinking(fsm)
    fsm.handle_event(ev(EventType.DIALOGUE_RESPONSE_RECEIVED,
                        {"reply_text": "抱歉。", "emotion": "sad"}))

# --------------------------------------------------------------------------- #
# P0-4 · avatar_action 取值收敛（单一来源 board/runtime/avatar_actions.py）
# 依据：docs/玩偶素材丰富填充_方案设计.md §3.3 / §4.1 P0-4
# --------------------------------------------------------------------------- #
def _to_thinking():
    """按真实链路推进到 THINKING：IDLE→PRESENT→AWAKE→LISTENING→THINKING。"""
    fsm = RuntimeFSM()
    fsm.handle_event(ev(EventType.SCENE_PERSON_ENTER))
    fsm.handle_event(ev(EventType.AUDIO_KWS_DETECTED))
    fsm.handle_event(ev(EventType.AUDIO_VAD_END))   # AWAKE → LISTENING
    fsm.handle_event(ev(EventType.AUDIO_VAD_END))   # LISTENING → THINKING
    assert fsm.state == RuntimeState.THINKING
    return fsm


def test_avatar_action_whitelist_single_source():
    """白名单 / 映射表 / 别名 / mock 默认值四处取值自洽。"""
    assert set(av.ALLOWED_AVATAR_ACTIONS) == set(av.ACTION_TO_STATE)
    assert all(v in av.ALLOWED_AVATAR_ACTIONS for v in av.ACTION_ALIASES.values())
    assert av.is_allowed(av.DEFAULT_MOCK_ACTION)
    assert not av.is_allowed("wave")      # P0-4：旧值已移出白名单


def test_avatar_action_routes_to_landed_state():
    """名单内动作上报后落到指定状态；状态未落地（P1-1 前的 deny_shake）→ 回落分档。"""
    for action in av.ALLOWED_AVATAR_ACTIONS:
        want = av.state_for(action)
        fsm = _to_thinking()
        fsm.handle_event(ev(EventType.DIALOGUE_RESPONSE_RECEIVED,
                            {"avatar_action": action, "emotion": "friendly"}))
        if want in RuntimeState.__members__:
            assert fsm.state.name == want
        else:
            assert fsm.state == RuntimeState.SPEAKING_NEUTRAL


def test_avatar_action_alias_and_unknown():
    """短别名与 v2 等价；未知动作仍走情绪分档兜底（不被静默改写状态）。"""
    fsm = _to_thinking()
    fsm.handle_event(ev(EventType.DIALOGUE_RESPONSE_RECEIVED,
                        {"avatar_action": " Surprised ", "emotion": "friendly"}))
    assert fsm.state == RuntimeState.AWAKE
    fsm = _to_thinking()
    fsm.handle_event(ev(EventType.DIALOGUE_RESPONSE_RECEIVED,
                        {"avatar_action": "wave", "emotion": "friendly"}))
    assert fsm.state == RuntimeState.SPEAKING_NEUTRAL

    assert changes[-1]["to"] == "SPEAKING_LOW"
