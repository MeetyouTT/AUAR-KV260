# -*- coding: utf-8 -*-
"""UiState 聚合单测：事件 → UI 状态更新，输出符合 ui_state.schema.json。"""
import json
import os

from board.runtime.event_bus import EventEnvelope
from board.runtime.events import EventType
from board.interaction.ui_state import UiState


def ev(t, payload=None):
    return EventEnvelope(event_type=t, source="test", created_at_ms=0,
                         payload=payload or {})


def test_initial_snapshot_schema():
    ui = UiState()
    snap = ui.snapshot()
    assert snap["runtime_state"] == "IDLE"
    assert snap["mode"] == "CORE_LOCAL"
    assert snap["privacy"] is False
    assert "scene" in snap and "dialogue" in snap


def test_snapshot_matches_json_schema():
    import jsonschema
    spec_path = os.path.join(os.path.dirname(__file__), "..", "ui",
                             "ui_state.schema.json")
    with open(spec_path, encoding="utf-8") as f:
        schema = json.load(f)
    ui = UiState()
    ui.set_device("camera", "ready")
    ui.set_device("network", "online")
    ui.set_scene({"scene_seq": 1, "people_count": 1, "current_target": {},
                  "recent_events": []})
    jsonschema.Draft7Validator(schema).validate(ui.snapshot())  # 无异常即通过


def test_fsm_state_changed_updates_runtime_state():
    ui = UiState()
    ui.update_from_event(ev(EventType.FSM_STATE_CHANGED, {"to": "SPEAKING"}))
    assert ui.snapshot()["runtime_state"] == "SPEAKING"


def test_speaking_low_in_schema_enum():
    """新增的 SPEAKING_LOW（低落播报）必须落在 ui_state.schema.json 枚举内。"""
    import jsonschema
    spec_path = os.path.join(os.path.dirname(__file__), "..", "ui",
                             "ui_state.schema.json")
    with open(spec_path, encoding="utf-8") as f:
        schema = json.load(f)
    assert "SPEAKING_LOW" in schema["properties"]["runtime_state"]["enum"]
    ui = UiState()
    ui.set_runtime_state("SPEAKING_LOW")
    jsonschema.Draft7Validator(schema).validate(ui.snapshot())  # 无异常即通过


def test_camera_lost_clears_scene():
    ui = UiState()
    ui.set_scene({"scene_seq": 5, "people_count": 1, "current_target": {},
                  "recent_events": []})
    ui.update_from_event(ev(EventType.CAMERA_LOST))
    snap = ui.snapshot()
    assert snap["camera"]["state"] == "lost"
    assert snap["scene"]["people_count"] == 0


def test_network_lost_sets_core_local():
    ui = UiState()
    ui.set_device("network", "online")
    assert ui.snapshot()["mode"] == "DIALOGUE_LAN"
    ui.update_from_event(ev(EventType.DIALOGUE_NETWORK_LOST))
    assert ui.snapshot()["network"]["state"] == "offline"
    assert ui.snapshot()["mode"] == "CORE_LOCAL"


def test_dialogue_response_updates_reply():
    ui = UiState()
    ui.update_from_event(ev(EventType.DIALOGUE_RESPONSE_RECEIVED,
                            {"reply_text": "我看到画面左侧有一位来访者。"}))
    assert ui.snapshot()["dialogue"]["last_reply"] == "我看到画面左侧有一位来访者。"


def test_privacy_event():
    ui = UiState()
    ui.update_from_event(ev(EventType.SYSTEM_PRIVACY_CHANGED, {"on": True}))
    assert ui.snapshot()["privacy"] is True


def test_recent_text_bounded():
    ui = UiState()
    for i in range(20):
        ui.push_text("evt-%d" % i)
    assert len(ui.recent_text()) <= 8


def test_avatar_anim_interface():
    """方案 C·数据层：UiState.avatar_anim 下发动画名/参数/enabled。"""
    ui = UiState()
    # 默认静态（enabled=False）
    assert ui.snapshot()["avatar_anim"]["enabled"] is False
    # 上层下发动画
    ui.set_avatar_anim("blink", {"period_ms": 3500}, enabled=True)
    anim = ui.snapshot()["avatar_anim"]
    assert anim["name"] == "blink"
    assert anim["params"] == {"period_ms": 3500}
    assert anim["enabled"] is True


def test_ingest_external_snapshot():
    ui = UiState()
    ui.ingest({"runtime_state": "ERROR", "fps": 12.5})
    snap = ui.snapshot()
    assert snap["runtime_state"] == "ERROR"
    assert snap["fps"] == 12.5


def test_concurrent_update_no_crash():
    """并发读写不抛异常（线程安全基本验证）。"""
    import threading
    ui = UiState()
    errors = []

    def writer():
        try:
            for i in range(200):
                ui.update_from_event(ev(EventType.FSM_STATE_CHANGED, {"to": "PRESENT"}))
                ui.set_fps(float(i))
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    def reader():
        try:
            for _ in range(200):
                ui.snapshot()
                ui.recent_text()
        except Exception as e:  # noqa: BLE001
            errors.append(e)

    ts = [threading.Thread(target=writer), threading.Thread(target=reader)]
    for t in ts:
        t.start()
    for t in ts:
        t.join(timeout=5)
    assert not errors
