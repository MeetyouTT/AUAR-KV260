# -*- coding: utf-8 -*-
"""WebSocket 适配器合同测试（A3 · 9/19）—— 人3

验证「板端 ↔ LAN 主机」合同：连接 / 请求-响应 / `request_id` 匹配 / 超时 / 断链 /
**迟到响应不覆盖新请求** / 脏 JSON / 协议版本 / 健康检查 / 未连接保护。

被测：`board/runtime/dialogue_client/ws_adapter.py` + `ws_client.py`
替身：`scripts/mock_dialogue_server.py`（标准库实现，可注入 9 种模式）
环境标签：PC / SIMULATED（本机回环，非板端实测）。
"""
from __future__ import annotations

import os
import sys
import time

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from board.runtime.dialogue_client.adapter import (AdapterError, DialogueRequest,   # noqa: E402
                                                   DialogueResponse)
from board.runtime.dialogue_client.ws_adapter import WebSocketAdapter               # noqa: E402
from scripts.mock_dialogue_server import MockDialogueServer                           # noqa: E402

SCENE = {"scene_seq": 12, "people_count": 1, "camera_state": "online",
         "current_target": {"track_id": 7, "position": "left"}}


def _server(mode: str = "normal", **kw) -> MockDialogueServer:
    return MockDialogueServer(port=0, mode=mode, **kw).start()


def _adapter(server: MockDialogueServer, **kw) -> WebSocketAdapter:
    kw.setdefault("max_retries", 1)
    kw.setdefault("backoff_ms", 20)
    kw.setdefault("timeout_s", 2.0)
    return WebSocketAdapter(host="127.0.0.1", port=server.port, path="/dialogue", **kw)


def _request(rid: str = "req-1", scene=None) -> DialogueRequest:
    return DialogueRequest(request_id=rid, audio_generation_id=1, transcript="你好",
                           scene_state=dict(scene or SCENE),
                           allowed_emotions=["friendly"],
                           allowed_avatar_actions=["wave"])


class TestHappyPath:
    """正向链路：连接 → 请求 → 响应 → 关闭。"""

    def test_roundtrip_returns_matching_response(self):
        with _server() as srv:
            ad = _adapter(srv)
            assert ad.connect() is True
            assert ad.is_connected is True
            resp = ad.send_request(_request("req-ok"), timeout_ms=2000)
            assert isinstance(resp, DialogueResponse)
            assert resp.request_id == "req-ok"
            assert resp.reply_text and resp.protocol_version == "1.0"
            stats = ad.stats()
            assert stats["requests"] == 1 and stats["responses_ok"] == 1
            assert stats["stale_dropped"] == 0 and stats["timeouts"] == 0
            ad.close()
            assert ad.is_connected is False

    def test_request_payload_reaches_server(self):
        with _server() as srv:
            ad = _adapter(srv)
            ad.connect()
            ad.send_request(_request("req-a"), timeout_ms=2000)
            assert srv.requests_seen == 1
            assert srv.last_request["request_id"] == "req-a"
            assert srv.last_request["audio_generation_id"] == 1
            assert srv.last_request["scene_state"]["scene_seq"] == 12
            ad.close()

    def test_health_check_ok_with_latency(self):
        with _server() as srv:
            ad = _adapter(srv)
            ad.connect()
            hc = ad.health_check()
            assert hc["ok"] is True and hc["latency_ms"] >= 0
            ad.close()

    def test_health_check_when_not_connected_returns_not_ok(self):
        ad = WebSocketAdapter(port=1, timeout_s=0.3)
        assert ad.health_check()["ok"] is False          # 不抛异常

    def test_slow_server_within_timeout(self):
        with _server(mode="slow", latency_ms=150) as srv:
            ad = _adapter(srv)
            ad.connect()
            resp = ad.send_request(_request("req-slow"), timeout_ms=3000)
            assert resp.request_id == "req-slow"
            assert ad.stats()["last_latency_ms"] >= 100
            ad.close()


class TestFaults:
    """故障注入：超时 / 断链 / 脏数据 / 协议版本 / 迟到响应。"""

    def test_timeout_raises_timeout_error(self):
        with _server(mode="hang", hang_s=3.0) as srv:
            ad = _adapter(srv, timeout_s=0.3)
            ad.connect()
            with pytest.raises(TimeoutError):
                ad.send_request(_request("req-hang"), timeout_ms=300)
            assert ad.stats()["timeouts"] == 1
            ad.close()

    def test_close_after_recv_raises_adapter_error(self):
        with _server(mode="close_after_recv") as srv:
            ad = _adapter(srv)
            ad.connect()
            with pytest.raises(AdapterError):
                ad.send_request(_request("req-close"), timeout_ms=1500)
            assert ad.stats()["errors"] >= 1
            ad.close()

    def test_bad_json_raises_adapter_error(self):
        with _server(mode="bad_json") as srv:
            ad = _adapter(srv)
            ad.connect()
            with pytest.raises(AdapterError):
                ad.send_request(_request("req-badjson"), timeout_ms=1500)
            ad.close()

    def test_bad_protocol_version_raises_adapter_error(self):
        with _server(mode="bad_version") as srv:
            ad = _adapter(srv)
            ad.connect()
            with pytest.raises(AdapterError):
                ad.send_request(_request("req-ver"), timeout_ms=1500)
            ad.close()

    def test_wrong_id_is_dropped_then_timeout(self):
        """服务端只回错误 request_id → 客户端丢弃并超时（绝不返回错内容）。"""
        with _server(mode="wrong_id") as srv:
            ad = _adapter(srv)
            ad.connect()
            with pytest.raises(TimeoutError):
                ad.send_request(_request("req-x"), timeout_ms=400)
            assert ad.stats()["stale_dropped"] >= 1
            assert ad.stats()["responses_ok"] == 0
            ad.close()

    def test_duplicate_stale_then_correct(self):
        """服务端先发迟到响应、再发正确响应 → 只取正确那条，且 stale≥1。"""
        with _server(mode="duplicate") as srv:
            ad = _adapter(srv)
            ad.connect()
            resp = ad.send_request(_request("req-dup"), timeout_ms=2000)
            assert resp.request_id == "req-dup"
            stats = ad.stats()
            assert stats["stale_dropped"] >= 1 and stats["responses_ok"] == 1
            ad.close()


class TestConnect:
    """连接管理：未连保护 / 连不上 / 断链后重连。"""

    def test_connect_fails_when_nothing_listening(self):
        ad = WebSocketAdapter(host="127.0.0.1", port=9, timeout_s=0.3, max_retries=0)
        with pytest.raises(AdapterError):
            ad.connect()

    def test_send_without_connect_raises(self):
        with _server() as srv:
            ad = _adapter(srv)
            with pytest.raises(AdapterError):
                ad.send_request(_request("req-noconn"), timeout_ms=200)
            ad.close()

    def test_empty_request_id_rejected(self):
        with _server() as srv:
            ad = _adapter(srv)
            ad.connect()
            with pytest.raises(AdapterError):
                ad.send_request(_request(""), timeout_ms=500)
            ad.close()

    def test_disconnect_then_reconnect_to_new_endpoint(self):
        """链路中断 → 报 AdapterError；换新服务端后可重新 connect 并成功请求。"""
        srv = _server()
        ad = _adapter(srv)
        ad.connect()
        # ⚠️ connect() 收到 101 早于服务端登记连接 → 等登记完成再停服，否则"没有连接可断"
        deadline = time.time() + 2.0
        while srv.connections < 1 and time.time() < deadline:
            time.sleep(0.02)
        srv.stop()
        time.sleep(0.2)
        with pytest.raises(AdapterError):
            ad.send_request(_request("req-after-stop"), timeout_ms=500)
        ad.close()

        with _server() as srv2:
            ad2 = _adapter(srv2)
            assert ad2.connect() is True
            assert ad2.send_request(_request("req-2"), timeout_ms=2000).request_id == "req-2"
            ad2.close()
