# -*- coding: utf-8 -*-
"""Mock 对话适配器：本地回环实现（无板开发月联调用，A3 替换为真实 WebSocketAdapter）。"""
import time
import typing

from .. import avatar_actions
from .adapter import AdapterError, DialogueAdapter, DialogueRequest, DialogueResponse

POS_TEXT = {"left": "左侧", "center": "中间", "right": "右侧"}


def default_response_factory(request: DialogueRequest) -> DialogueResponse:
    """基于 SceneState 生成带 grounding 的默认回复（演示/冒烟用）。

    注意：这是模拟 LLM 行为的确定性模板，真实回复来自 LAN 主机 LLM。
    """
    ss = request.scene_state or {}
    target = ss.get("current_target") or {}
    pos = target.get("position")
    if pos in POS_TEXT:
        text = "我看到画面%s有一位来访者。" % POS_TEXT[pos]
        claims = [{"fact": "person_on_%s" % pos,
                   "source_track_id": target.get("track_id")}]
    elif ss.get("people_count", 0) > 0:
        text = "我看到有人在场。"
        claims = [{"fact": "person_present"}]
    elif ss.get("camera_state") == "online":
        text = "不确定，当前画面没有看到人。"
        claims = [{"fact": "no_person"}]
    else:
        text = "不确定，摄像头当前不可用。"
        claims = [{"fact": "no_visual_evidence"}]
    return DialogueResponse(
        protocol_version=request.protocol_version,
        request_id=request.request_id,
        scene_seq_used=ss.get("scene_seq", 0),
        reply_text=text,
        emotion="friendly",
        avatar_action=avatar_actions.DEFAULT_MOCK_ACTION,  # 白名单内动作（原 "wave" 名单外 → 被静默忽略，P0-4）
        visual_claims=claims,
    )


class MockDialogueAdapter(DialogueAdapter):
    """可配置的 Mock 适配器：
      latency_ms      模拟端到端延迟
      response_factory 自定义响应生成（默认基于 SceneState 的模板）
      fail_mode       "error" / "timeout" / None（故障注入用）
    """

    def __init__(self, latency_ms: int = 0,
                 response_factory: typing.Optional[typing.Callable[[DialogueRequest], DialogueResponse]] = None,
                 fail_mode: typing.Optional[str] = None) -> None:
        self._latency_ms = max(0, int(latency_ms))
        self._factory = response_factory or default_response_factory
        self._fail_mode = fail_mode
        self._connected = False
        self._call_count = 0
        self._connect_count = 0
        self._requests = []        # type: typing.List[DialogueRequest]
        self._responses = []       # type: typing.List[DialogueResponse]
        self._last_request = None  # type: typing.Optional[DialogueRequest]

    # ---- DialogueAdapter 接口 ----
    def connect(self) -> bool:
        self._connect_count += 1
        self._connected = True
        return True

    def health_check(self) -> typing.Dict:
        return {
            "ok": self._connected,
            "latency_ms": self._latency_ms,
            "detail": {"calls": self._call_count, "connect_count": self._connect_count},
        }

    def send_request(self, request: DialogueRequest, timeout_ms: int = 4000) -> DialogueResponse:
        if not self._connected:
            raise AdapterError("adapter 未连接")
        self._call_count += 1
        self._last_request = request
        self._requests.append(request)

        if self._fail_mode == "error":
            raise AdapterError("mock: 主机返回错误")
        if self._fail_mode == "timeout" or self._latency_ms > timeout_ms:
            raise TimeoutError("mock: 请求超时 (%dms > %dms)" % (self._latency_ms, timeout_ms))

        if self._latency_ms > 0:
            time.sleep(self._latency_ms / 1000.0)
        response = self._factory(request)
        self._responses.append(response)
        return response

    def close(self) -> None:
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    # ---- 测试辅助 ----
    @property
    def call_count(self) -> int:
        return self._call_count

    def set_fail_mode(self, mode: typing.Optional[str]) -> None:
        """故障注入：None | "error" | "timeout"。"""
        if mode not in (None, "error", "timeout"):
            raise ValueError("fail_mode 必须为 None/error/timeout")
        self._fail_mode = mode
