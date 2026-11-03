# -*- coding: utf-8 -*-
"""avatar_fsm 逻辑层单测：10 态 → 表现映射完整性（LVGL 版复用同一逻辑）。"""
from board.interaction.avatar_fsm import AVATAR_MAP, all_states, avatar_spec, expression_spec


def test_all_states_defined():
    required = {"IDLE", "PRESENT", "LISTENING", "THINKING", "SPEAKING", "SPEAKING_LOW",
                "CAMERA_LOST", "NETWORK_LOST", "CANCELLED", "ERROR"}
    assert required.issubset(set(AVATAR_MAP.keys()))


def test_speaking_two_emotion_tiers():
    """播报两档：SPEAKING 情绪高涨（happy）/ SPEAKING_LOW 情绪低落（sad）。"""
    assert avatar_spec("SPEAKING").expression == "happy"
    low = avatar_spec("SPEAKING_LOW")
    assert low.animation == "speak"
    assert low.expression == "sad"
    assert low.label and low.token_key


def test_avatar_spec_fields():
    spec = avatar_spec("PRESENT")
    assert spec.animation == "attention"
    assert spec.expression == "curious"
    assert spec.label
    assert spec.token_key


def test_unknown_state_falls_back_idle():
    assert avatar_spec("NOT_A_STATE") == AVATAR_MAP["IDLE"]


def test_expression_spec_complete():
    expressions = {s.expression for s in AVATAR_MAP.values()}
    for e in expressions:
        spec = expression_spec(e)
        assert "eye_dx" in spec and "mouth" in spec, e


def test_animations_positive():
    for s in all_states():
        spec = avatar_spec(s)
        assert spec.animation in ("breath", "attention", "listen", "think", "speak", "static")


def test_animation_frames_interface():
    """方案 C·映射层：ANIMATION_FRAMES 帧表可查询。"""
    from board.interaction.avatar_fsm import ANIMATION_FRAMES, animation_frames
    assert "blink" in ANIMATION_FRAMES
    assert "look" in ANIMATION_FRAMES
    assert animation_frames("blink") == [("eye", 0.0), ("eye", 1.0), ("eye", 0.0)]
    assert animation_frames("look") == [("look_dx", -1.0), ("look_dx", 1.0)]
    assert animation_frames("not_exist") == []
