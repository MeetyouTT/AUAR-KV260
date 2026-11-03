# -*- coding: utf-8 -*-
"""Dialogue Adapter 单测：往返、超时、错误注入、重连、数据合同。"""
import time

import pytest

from board.runtime.dialogue_client import (AdapterError, DialogueRequest,
                                           MockDialogueAdapter)


def scene():
    return {
        "schema_version": "1.0", "scene_seq": 125, "captured_at_ms": 1000,
        "valid_until_ms": 200000, "camera_state": "online", "people_count": 1,
        "current_target": {"track_id": 7, "position": "left", "confidence": 0.91,
                           "source_frame_id": 888},
        "recent_events": [{"type": "person_enter", "track_id": 7, "age_ms": 500}],
        "uncertainty": [],
    }


def req():
    return DialogueRequest(request_id="req-1", audio_generation_id=1,
                           transcript="你看到我了吗", scene_state=scene(),
                           allowed_emotions=["neutral", "friendly"],
                           allowed_avatar_actions=["idle", "wave"])


def test_connect_and_health():
    a = MockDialogueAdapter()
    assert a.connect() is True
    assert a.health_check()["ok"] is True
    assert a.is_connected is True
    a.close()
    assert a.is_connected is False


def test_roundtrip_grounded_reply():
    a = MockDialogueAdapter()
    a.connect()
    r = a.send_request(req())
    assert r.request_id == "req-1"
    assert "左侧" in r.reply_text
    assert r.visual_claims[0]["fact"] == "person_on_left"
    assert r.visual_claims[0]["source_track_id"] == 7
    assert a.call_count == 1


def test_latency_simulated():
    a = MockDialogueAdapter(latency_ms=100)
    a.connect()
    t0 = time.time()
    a.send_request(req(), timeout_ms=2000)
    assert time.time() - t0 >= 0.08


def test_timeout_raises():
    a = MockDialogueAdapter(latency_ms=500)
    a.connect()
    with pytest.raises(TimeoutError):
        a.send_request(req(), timeout_ms=100)


def test_error_mode_raises_adapter_error():
    a = MockDialogueAdapter(fail_mode="error")
    a.connect()
    with pytest.raises(AdapterError):
        a.send_request(req())


def test_not_connected_raises():
    a = MockDialogueAdapter()
    with pytest.raises(AdapterError):
        a.send_request(req())


def test_fault_injection_toggle():
    a = MockDialogueAdapter()
    a.connect()
    a.set_fail_mode("timeout")
    with pytest.raises(TimeoutError):
        a.send_request(req())
    a.set_fail_mode(None)
    r = a.send_request(req())
    assert r.request_id == "req-1"


def test_request_records_for_audit():
    a = MockDialogueAdapter()
    a.connect()
    a.send_request(req())
    a.send_request(req())
    assert len(a._requests) == 2
    assert a._requests[0].transcript == "你看到我了吗"


def test_dialogue_request_to_from_dict():
    r = req()
    d = r.to_dict()
    r2 = DialogueRequest.from_dict(d)
    assert r2.request_id == r.request_id
    assert r2.scene_state["scene_seq"] == 125
    assert r2.allowed_emotions == ["neutral", "friendly"]


def test_reconnect_after_close():
    a = MockDialogueAdapter()
    a.connect()
    a.close()
    with pytest.raises(AdapterError):
        a.send_request(req())
    assert a.connect() is True  # 断链后可重连
    assert a.send_request(req()).request_id == "req-1"
