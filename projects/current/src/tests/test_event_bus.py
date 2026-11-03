# -*- coding: utf-8 -*-
"""Event Bus 单测：有界队列、丢旧保新、critical 不丢、订阅分发。"""
import threading
import time

from board.runtime.event_bus import EventBus, EventEnvelope
from board.runtime.events import EventType


def mk(event_type, payload=None, source="test", t=0):
    return EventEnvelope(event_type=event_type, source=source,
                         created_at_ms=t, payload=payload or {})


def test_envelope_validation():
    import pytest
    with pytest.raises(ValueError):
        EventEnvelope(event_type="", source="t", created_at_ms=0)


def test_subscribe_receives_event():
    bus = EventBus(max_size=8)
    got = []
    bus.subscribe(lambda e: got.append(e.event_type))
    bus.publish(mk(EventType.AUDIO_KWS_DETECTED))
    assert got == [EventType.AUDIO_KWS_DETECTED]


def test_subscribe_filter_by_type():
    bus = EventBus(max_size=8)
    got = []
    bus.subscribe(lambda e: got.append(e.event_type), {EventType.SCENE_PERSON_ENTER})
    bus.publish(mk(EventType.SCENE_PERSON_ENTER))
    bus.publish(mk(EventType.SYSTEM_HEARTBEAT))
    assert got == [EventType.SCENE_PERSON_ENTER]


def test_bounded_drop_when_full():
    bus = EventBus(max_size=3)
    for i in range(10):
        bus.publish(mk(EventType.SYSTEM_HEARTBEAT, {"i": i}))
    assert bus.current_size == 3
    m = bus.metrics()
    assert m["published"] == 3
    assert m["dropped_by_type"].get(EventType.SYSTEM_HEARTBEAT, 0) == 7


def test_latest_evict_oldest_frame():
    bus = EventBus(max_size=2)
    bus.publish(mk(EventType.DETECTOR_FRAME, {"frame_id": 1}))
    bus.publish(mk(EventType.DETECTOR_FRAME, {"frame_id": 2}))
    bus.publish(mk(EventType.DETECTOR_FRAME, {"frame_id": 3}))  # 挤掉 frame 1
    frames = [e.payload["frame_id"] for e in bus._queue.snapshot()]
    assert frames == [2, 3]
    assert bus.metrics()["evicted_total"] == 1


def test_latest_final_scene_state_keeps_newest():
    bus = EventBus(max_size=2)
    bus.publish(mk(EventType.SCENE_STATE, {"seq": 1}))
    bus.publish(mk(EventType.SCENE_STATE, {"seq": 2}))
    bus.publish(mk(EventType.SCENE_STATE, {"seq": 3}))  # 新状态覆盖旧状态
    seqs = [e.payload["seq"] for e in bus._queue.snapshot()]
    assert seqs == [2, 3]


def test_critical_evicts_noncritical():
    bus = EventBus(max_size=2)
    bus.publish(mk(EventType.SYSTEM_HEARTBEAT))
    bus.publish(mk(EventType.SYSTEM_HEARTBEAT))
    ok = bus.publish(mk(EventType.AUDIO_CANCEL_REQUESTED))  # critical
    assert ok
    snap = [e.event_type for e in bus._queue.snapshot()]
    assert EventType.AUDIO_CANCEL_REQUESTED in snap
    assert bus.metrics()["evicted_total"] == 1


def test_critical_blocking_when_all_critical():
    bus = EventBus(max_size=2)
    bus.publish(mk(EventType.AUDIO_CANCEL_REQUESTED))
    bus.publish(mk(EventType.SYSTEM_WORKER_CRASH))
    result = {}

    def pub():
        result["ok"] = bus.publish(mk(EventType.SYSTEM_SHUTDOWN))

    t = threading.Thread(target=pub)
    t.start()
    time.sleep(0.05)
    assert t.is_alive()  # 全 critical 满：发布线程应阻塞等待
    bus._queue.get_nowait()  # 消费一条腾出空间
    t.join(timeout=1.0)
    assert result.get("ok") is True
    assert bus.published_count == 3  # 全部入队，无静默丢失


def test_wait_event():
    bus = EventBus(max_size=8)
    bus.publish(mk(EventType.SCENE_PERSON_ENTER))
    ev = bus.wait_event(EventType.SCENE_PERSON_ENTER, timeout=1.0)
    assert ev is not None and ev.event_type == EventType.SCENE_PERSON_ENTER


def test_wait_event_timeout():
    bus = EventBus(max_size=8)
    assert bus.wait_event(EventType.SCENE_PERSON_ENTER, timeout=0.1) is None


def test_async_dispatch():
    bus = EventBus(max_size=8, dispatch_async=True)
    got = []
    bus.subscribe(lambda e: got.append(e.event_type))
    bus.publish(mk(EventType.SYSTEM_HEARTBEAT))
    time.sleep(0.15)
    assert EventType.SYSTEM_HEARTBEAT in got
    bus.stop()


def test_handler_error_does_not_break_bus():
    bus = EventBus(max_size=8)
    ok = []

    def bad(_e):
        raise RuntimeError("boom")

    def good(_e):
        ok.append(1)

    bus.subscribe(bad)
    bus.subscribe(good)
    bus.publish(mk(EventType.SYSTEM_HEARTBEAT))
    assert ok == [1]


def test_metrics_visibility():
    bus = EventBus(max_size=4)
    bus.publish(mk(EventType.SYSTEM_HEARTBEAT))
    bus.publish(mk(EventType.SYSTEM_HEARTBEAT))
    m = bus.metrics()
    assert m["max_size"] == 4
    assert m["published"] == 2
    assert m["dispatch_async"] is False
