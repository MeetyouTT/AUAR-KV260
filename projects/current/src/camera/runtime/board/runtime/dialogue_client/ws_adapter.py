# -*- coding: utf-8 -*-
"""真实 WebSocket 对话适配器（A3 · 9/19 任务）—— 人3

合同（`dialogue_client/adapter.py`，**本文件不改合同**）：
  DialogueRequest  {protocol_version, request_id, audio_generation_id, transcript,
                    scene_state, allowed_emotions, allowed_avatar_actions}
  DialogueResponse {protocol_version, request_id, scene_seq_used, reply_text,
                    emotion, avatar_action, visual_claims}
必须满足：带超时；超时抛 `TimeoutError`；断链可重连；**旧响应不得覆盖新请求**。

实现要点
--------
1. 底层用自研 `ws_client.WebSocketClient`（**零第三方依赖**，与板端 C++ 实现一一对应）；
   若将来要换 `websocket-client`，只需替换 `_client` 的
   `connect / send_text / recv_text / recv_pong / close` 五处调用。
2. **旧响应丢弃**：只接受 `request_id == 当前在途请求` 的帧；其它帧计 `stale_dropped` 并继续等
   —— 保证"取消/超时后迟到的响应"永远不会覆盖新请求（A1 合同 §五）。
3. **业务校验不在这里**：TTL、scene_seq 超前、视觉声明 grounding、白名单由三层 Validator 负责
   （避免两处判据不一致）。
4. 断链：`is_connected=False`；`connect()` 带重试与线性退避；未连接时 `send_request` 抛 `AdapterError`。

环境标签：**PC / SIMULATED**（LAN 明文、同一网段；板端阶段替换为 C++ 等价实现）。
"""
from __future__ import annotations

import json
import time
import typing

from .adapter import (PROTOCOL_VERSION, AdapterError, DialogueAdapter,
                      DialogueRequest, DialogueResponse)
from .ws_client import WebSocketClient, WebSocketClosed, WebSocketError


class WebSocketAdapter(DialogueAdapter):
    """板端 ↔ LAN 对话主机（Open-LLM-VTuber 侧服务）的 WebSocket 适配器。"""

    MAX_STALE_FRAMES = 16          # 单次等待中允许丢弃的迟到帧上限（防御性）

    def __init__(self, host: str = "127.0.0.1", port: int = 8765,
                 path: str = "/dialogue", timeout_s: float = 5.0,
                 max_retries: int = 2, backoff_ms: int = 200,
                 protocol_version: str = PROTOCOL_VERSION,
                 client: typing.Optional[WebSocketClient] = None) -> None:
        self.host = host
        self.port = int(port)
        self.path = path
        self.timeout_s = float(timeout_s)
        self.max_retries = max(0, int(max_retries))
        self.backoff_ms = max(0, int(backoff_ms))
        self.protocol_version = protocol_version
        self._client = client or WebSocketClient(host, self.port, path, self.timeout_s)
        self._active_request_id = ""
        self._last_latency_ms = 0.0
        self._counters = {"requests": 0, "responses_ok": 0, "stale_dropped": 0,
                          "timeouts": 0, "reconnects": 0, "errors": 0}

    # ------------------------------------------------------- 合同实现
    def connect(self) -> bool:
        """连接（失败按 `max_retries` 重试，线性退避）；仍失败抛 AdapterError。"""
        last: typing.Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                if self._client.connect():
                    if attempt:
                        self._counters["reconnects"] += 1
                    return True
            except WebSocketError as exc:
                last = exc
            if attempt < self.max_retries and self.backoff_ms:
                time.sleep(self.backoff_ms / 1000.0 * (attempt + 1))
        self._counters["errors"] += 1
        raise AdapterError("连接对话主机失败（%s:%d%s）：%s"
                           % (self.host, self.port, self.path, last))

    def health_check(self) -> typing.Dict:
        """PING/PONG 往返延迟；未连接或异常时 `ok=False`（不抛异常）。"""
        if not self._client.is_connected:
            return {"ok": False, "latency_ms": -1, "detail": {"reason": "not_connected"}}
        t0 = time.perf_counter()
        try:
            self._client.send_ping(b"hc")
            ok = self._client.recv_pong(self.timeout_s, on_text=self._on_text)
        except (WebSocketError, TimeoutError) as exc:
            self._counters["errors"] += 1
            return {"ok": False, "latency_ms": -1, "detail": {"reason": str(exc)}}
        latency = (time.perf_counter() - t0) * 1000.0
        self._last_latency_ms = latency
        return {"ok": bool(ok), "latency_ms": int(round(latency)), "detail": self.stats()}

    def send_request(self, request: DialogueRequest,
                     timeout_ms: int = 4000) -> DialogueResponse:
        """发送请求并等待**匹配 request_id** 的响应；超时抛 TimeoutError。"""
        if not self._client.is_connected:
            raise AdapterError("adapter 未连接：请先 connect()")
        payload = request.to_dict()
        request_id = str(payload.get("request_id") or "")
        if not request_id:
            raise AdapterError("request_id 不能为空（合同要求）")

        self._active_request_id = request_id
        self._counters["requests"] += 1
        t0 = time.perf_counter()
        try:
            self._client.send_text(json.dumps(payload, ensure_ascii=False))
        except WebSocketError as exc:
            self._counters["errors"] += 1
            self._active_request_id = ""
            raise AdapterError("发送失败：%s" % exc) from exc
        return self._wait_response(request_id, timeout_ms, t0)

    def close(self) -> None:
        self._client.close()
        self._active_request_id = ""

    @property
    def is_connected(self) -> bool:
        return self._client.is_connected

    # ------------------------------------------------------- 内部
    def _wait_response(self, request_id: str, timeout_ms: int,
                       t0: float) -> DialogueResponse:
        """等响应：丢弃迟到帧；超时/断链分别转成 TimeoutError / AdapterError。"""
        deadline = t0 + max(1, int(timeout_ms)) / 1000.0
        stale = 0
        while True:
            remain = deadline - time.perf_counter()
            if remain <= 0:
                self._counters["timeouts"] += 1
                self._active_request_id = ""
                raise TimeoutError("对话请求超时（%dms，request_id=%s）"
                                   % (timeout_ms, request_id))
            try:
                raw = self._client.recv_text(remain)
            except TimeoutError:
                self._counters["timeouts"] += 1
                self._active_request_id = ""
                raise TimeoutError("对话请求超时（%dms，request_id=%s）"
                                   % (timeout_ms, request_id))
            except WebSocketClosed as exc:
                self._counters["errors"] += 1
                self._active_request_id = ""
                raise AdapterError("连接中断：%s" % exc) from exc

            try:
                data = json.loads(raw)
            except ValueError as exc:
                self._counters["errors"] += 1
                raise AdapterError("响应不是合法 JSON：%s" % exc) from exc
            if not isinstance(data, dict):
                self._counters["errors"] += 1
                raise AdapterError("响应必须是 JSON 对象，收到 %s" % type(data).__name__)

            rid = str(data.get("request_id") or "")
            if rid != request_id:            # ★ 旧响应/他人响应：丢弃，绝不覆盖新请求
                stale += 1
                self._counters["stale_dropped"] += 1
                if stale >= self.MAX_STALE_FRAMES:
                    self._active_request_id = ""
                    raise AdapterError("迟到响应过多（≥%d 条）" % self.MAX_STALE_FRAMES)
                continue

            version = str(data.get("protocol_version") or "")
            if version != self.protocol_version:
                self._active_request_id = ""
                raise AdapterError("协议版本不匹配：%s ≠ %s" % (version, self.protocol_version))

            self._counters["responses_ok"] += 1
            self._last_latency_ms = (time.perf_counter() - t0) * 1000.0
            self._active_request_id = ""
            return DialogueResponse.from_dict(data)

    def _on_text(self, payload: bytes) -> None:
        """健康检查期间收到的文本帧：仍按 stale 判定计数（不返回给调用方）。"""
        try:
            data = json.loads(payload.decode("utf-8"))
        except Exception:
            return
        if not isinstance(data, dict):
            return
        if str(data.get("request_id") or "") != self._active_request_id:
            self._counters["stale_dropped"] += 1

    # ------------------------------------------------------- 证据/测试
    def stats(self) -> typing.Dict:
        """计数器（写进证据 JSON）；`stale_dropped>0` 即"旧响应被丢弃"的直接证明。"""
        data = dict(self._counters)
        data.update({"host": self.host, "port": self.port, "path": self.path,
                     "connected": self._client.is_connected,
                     "last_latency_ms": round(self._last_latency_ms, 2),
                     "active_request_id": self._active_request_id})
        return data
