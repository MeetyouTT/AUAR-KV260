# -*- coding: utf-8 -*-
"""UiState —— UI 状态聚合（Week A2 · 9/10）

线程安全：UI 线程读 snapshot()，事件线程（EventBus 分发）写 update()。

来源：
  - FSM 状态变更（fsm.state_changed）
  - 场景事件（scene.* / camera.*）
  - 网络/对话事件（dialogue.*）
  - 音频事件（audio.*）
  - 系统事件（system.privacy_changed）
  - MockBoard 外设状态（初始化/轮询时注入）

输出符合 ui/ui_state.schema.json。
"""
import threading
import typing

from board.runtime.event_bus import EventEnvelope
from board.runtime.events import EventType

_DEVICE_KEYS = ("camera", "npu", "pl", "audio", "network")


class UiState:
    def __init__(self, event_bus=None) -> None:
        self._lock = threading.RLock()
        self._event_bus = None
        self._event_subscription = None
        self._avatar_emotion = 'neutral'
        self._s = {
            "schema_version": "1.0",
            "runtime_state": "IDLE",
            "mode": "CORE_LOCAL",
            "camera": {"state": "idle", "detail": ""},
            "npu": {"state": "idle", "detail": ""},
            "pl": {"state": "idle", "detail": ""},
            "audio": {"state": "idle", "detail": ""},
            "network": {"state": "offline", "detail": ""},
            "privacy": False,
            "scene": {
                "scene_seq": 0, "people_count": 0,
                "current_target": None, "recent_events": [],
            },
            "dialogue": {"last_reply": "", "thinking": False},
            "fps": 0.0,
            "avatar_anim": {"name": "", "params": {}, "enabled": False},
        }
        self._recent_text = []  # 事件文本（演示用），容量 8
        if event_bus is not None:
            self.bind_event_bus(event_bus)

    def bind_event_bus(self, bus) -> None:
        """Connect the view model to the same bus as RuntimeFSM, in both directions."""
        if self._event_bus is bus:
            return
        if self._event_subscription is not None:
            self._event_subscription.unsubscribe()
        self._event_bus = bus
        self._event_subscription = bus.subscribe(self.update_from_event)

    def emit_avatar_event(self, event_type: str, payload: dict) -> bool:
        """Publish animation completion to the authoritative FSM, never edit it locally."""
        if self._event_bus is None:
            return False
        import time
        return bool(self._event_bus.publish(EventEnvelope(event_type=event_type, source='avatar',
            created_at_ms=int(time.monotonic() * 1000), payload=payload)))

    def avatar_emotion(self) -> str:
        with self._lock:
            return self._avatar_emotion

    # ------------------------------------------------------------------ #
    # 读取
    # ------------------------------------------------------------------ #
    def snapshot(self) -> typing.Dict:
        with self._lock:
            return dict(self._s)

    def device_snapshot(self) -> typing.Dict:
        with self._lock:
            return {k: dict(v) for k, v in self._s.items() if k in _DEVICE_KEYS}

    def recent_text(self, limit: int = 6) -> typing.List[str]:
        with self._lock:
            return list(self._recent_text[-limit:])

    def set_runtime_state(self, state: str) -> None:
        with self._lock:
            self._s["runtime_state"] = state

    def set_device(self, name: str, state: str, detail: str = "") -> None:
        with self._lock:
            if name in _DEVICE_KEYS:
                self._s[name] = {"state": state, "detail": detail}
                if name == "network" and state == "offline":
                    self._s["mode"] = "CORE_LOCAL"
                elif name == "network" and state == "online":
                    self._s["mode"] = "DIALOGUE_LAN"

    def set_scene(self, scene: typing.Dict) -> None:
        with self._lock:
            self._s["scene"] = scene

    def set_privacy(self, on: bool) -> None:
        with self._lock:
            self._s["privacy"] = bool(on)

    def set_dialogue(self, reply: str = "", thinking: bool = False) -> None:
        with self._lock:
            self._s["dialogue"] = {"last_reply": reply, "thinking": thinking}

    def set_fps(self, fps: float) -> None:
        with self._lock:
            self._s["fps"] = round(float(fps), 1)

    def set_avatar_anim(self, name: str, params: typing.Optional[typing.Dict] = None,
                        enabled: bool = False) -> None:
        """方案 C·数据层：上层下发当前动画名与参数（enabled=False 时渲染端静态）。

        name 对应 avatar_fsm.ANIMATION_FRAMES 帧表；params 含 period_ms/intensity 等。
        """
        with self._lock:
            self._s["avatar_anim"] = {
                "name": name,
                "params": dict(params) if params else {},
                "enabled": bool(enabled),
            }

    def push_text(self, text: str) -> None:
        with self._lock:
            self._recent_text.append(text)
            del self._recent_text[:-8]

    def clear_events(self) -> None:
        """清空事件文本缓冲（仅 `_recent_text`，不动 `_s` 中任何状态）。

        供「剧本化演示」类脚本在开场复位时使用：`build_app()` 初始化即发布
        SCENE_PERSON_ENTER，会留下 PRESENT/IDLE 往返文案，与"开场待机"叙事冲突。
        纯增量接口，不影响既有 `snapshot()/recent_text()` 语义。
        """
        with self._lock:
            self._recent_text = []


    # ------------------------------------------------------------------ #
    # 从 EventBus 事件增量更新
    # ------------------------------------------------------------------ #
    def update_from_event(self, env: EventEnvelope) -> None:
        """增量处理一个事件（线程安全）。与 UI 渲染解耦，只更新状态。"""
        t = env.event_type
        p = env.payload or {}

        if t == EventType.FSM_STATE_CHANGED:
            self.set_runtime_state(p.get("to", "IDLE"))
            self.push_text("状态 -> %s" % p.get("to", ""))
        elif t == EventType.SCENE_STATE:
            self.set_scene(p)
        elif t in (EventType.SCENE_PERSON_ENTER, EventType.SCENE_PERSON_EXIT,
                   EventType.SCENE_TARGET_UPDATE):
            self.push_text("场景事件: %s" % t)
        elif t == EventType.CAMERA_LOST:
            self.set_device("camera", "lost", "camera lost")
            self.set_scene({"scene_seq": self._s["scene"].get("scene_seq", 0),
                            "people_count": 0, "current_target": None,
                            "recent_events": []})
        elif t == EventType.CAMERA_RECOVERED:
            self.set_device("camera", "ready", "online")
        elif t == EventType.DIALOGUE_NETWORK_LOST:
            self.set_device("network", "offline", "LAN down")
        elif t == EventType.DIALOGUE_NETWORK_RESTORED:
            self.set_device("network", "online", "LAN up")
        elif t == EventType.DIALOGUE_RESPONSE_RECEIVED:
            reply = p.get("reply_text", "") if isinstance(p, dict) else ""
            with self._lock:
                self._avatar_emotion = str(p.get('emotion') or 'neutral')
            self.set_dialogue(reply=reply, thinking=False)
            if reply:
                self.push_text("回复: %s" % reply)
        elif t == EventType.DIALOGUE_TIMEOUT:
            self.set_dialogue(reply="（对话超时）", thinking=False)
        elif t == EventType.AUDIO_KWS_DETECTED:
            self.set_device("audio", "busy", "kws hit")
        elif t == EventType.AUDIO_VAD_END:
            self.set_device("audio", "busy", "vad end")
        elif t == EventType.AUDIO_PLAYBACK_STOP:
            self.set_device("audio", "idle", "playback done")
        elif t == EventType.AUDIO_PLAYBACK_START:
            self.set_device("audio", "busy", "playback")
        elif t == EventType.AUDIO_CANCEL_REQUESTED:
            self.set_device("audio", "idle", "cancelled")
            self.push_text("已取消播报")
        elif t == EventType.SYSTEM_PRIVACY_CHANGED:
            self.set_privacy(bool(p.get("on", False)))
        elif t == EventType.SYSTEM_WORKER_CRASH:
            self.push_text("worker 崩溃: %s" % (p.get("worker", "?") if isinstance(p, dict) else "?"))
        elif t == EventType.FPGA_UNDERFLOW:
            self.set_device("pl", "error", "underflow")
        elif t == EventType.FPGA_OVERFLOW:
            self.set_device("pl", "error", "overflow")
        elif t == EventType.FPGA_OVERLAY_COMMITTED:
            self.set_device("pl", "ready", "overlay ok")
        elif t == EventType.BOARD_KEY_PRESSED:
            self.push_text("按键: %s" % (p.get("key", "?") if isinstance(p, dict) else "?"))

    # ------------------------------------------------------------------ #
    # 从 MockBoard / 外部快照整体注入（初始化/轮询）
    # ------------------------------------------------------------------ #
    def ingest(self, ui_state_dict: typing.Dict) -> None:
        """整体注入一份 UiState（JSON 兼容），用于初始化或外部同步。"""
        with self._lock:
            for k, v in ui_state_dict.items():
                if k in self._s and v is not None:
                    self._s[k] = v

    def to_dict(self) -> typing.Dict:
        return self.snapshot()
