# -*- coding: utf-8 -*-
"""mock_dialogue_server.py —— 本地对话主机（标准库 WebSocket 服务端，A3 合同测试用）

用途：在没有 LAN 主机（Open-LLM-VTuber）的环境下，**完整验证板端侧合同**：
      WebSocket 握手 / 请求-响应 / request_id 匹配 / 超时 / 断链 / 迟到响应 / 非法载荷。
零第三方依赖（`socketserver` + 自研帧编解码），可与 `board/runtime/dialogue_client/ws_adapter.py` 对跑。

用法（两种）
------------
    # ① 命令行起服务（PC 演示 / 人工联调）
    python scripts\\mock_dialogue_server.py --port 8765 --mode normal --latency-ms 120

    # ② 测试内嵌（子线程起停，见 tests/test_ws_adapter.py）
    from scripts.mock_dialogue_server import MockDialogueServer
    srv = MockDialogueServer(port=0, mode="duplicate").start()

故障/场景注入（`--mode`）
-------------------------
| mode | 行为 | 验证点 |
|---|---|---|
| `normal` | 正常回复（基于 SceneState 的 grounded 模板） | 正向链路 |
| `slow` | 延迟 `--latency-ms` 后回复 | 延迟统计 |
| `hang` | 收到请求后**不回复**（保持连接） | 客户端 `TimeoutError` |
| `close_after_recv` | 收到请求后立刻断开 | 断链 → `AdapterError` |
| `bad_json` | 回复非 JSON 文本 | 客户端拒绝脏数据 |
| `wrong_id` | 回复的 `request_id` 不匹配 | 迟到/他人响应被丢弃 |
| `duplicate` | 先回一条 `wrong_id` 再回正确响应 | `stale_dropped ≥ 1` 且结果正确 |
| `bad_version` | `protocol_version="9.9"` | 协议版本防护 |
| `ungrounded` | 无人却声明"看到人" | 交给三层 Validator 拒绝（policy） |

环境标签：**PC / SIMULATED**（本服务是开发期替身，不是真实 LLM 主机）。
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import socket
import socketserver
import struct
import sys
import threading
import time
import typing

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from board.runtime.dialogue_client.adapter import DialogueRequest          # noqa: E402
from board.runtime.dialogue_client.mock_adapter import default_response_factory  # noqa: E402

WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
OP_TEXT, OP_CLOSE, OP_PING, OP_PONG = 0x1, 0x8, 0x9, 0xA


def _accept_key(client_key: str) -> str:
    digest = hashlib.sha1((client_key + WS_GUID).encode("ascii")).digest()
    return base64.b64encode(digest).decode("ascii")


def _apply_mask(payload: bytes, key: bytes) -> bytes:
    return bytes(b ^ key[i % 4] for i, b in enumerate(payload))


class _ServerConn:
    """服务端单连接：握手 + 帧读写（服务端→客户端**不加掩码**，客户端→服务端必有掩码）。"""

    def __init__(self, conn: socket.socket, timeout_s: float = 10.0) -> None:
        self.conn = conn
        self.timeout_s = timeout_s
        self.buf = b""

    # ---- 握手 ----
    def handshake(self) -> bool:
        self.conn.settimeout(self.timeout_s)
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = self.conn.recv(4096)
            if not chunk:
                return False
            data += chunk
            if len(data) > 65536:
                return False
        head, _, tail = data.partition(b"\r\n\r\n")
        self.buf = tail
        key = ""
        for line in head.decode("latin-1").split("\r\n"):
            name, _, value = line.partition(":")
            if name.strip().lower() == "sec-websocket-key":
                key = value.strip()
        if not key:
            return False
        resp = ("HTTP/1.1 101 Switching Protocols\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                "Sec-WebSocket-Accept: %s\r\n\r\n" % _accept_key(key))
        self.conn.sendall(resp.encode("ascii"))
        return True

    # ---- 读写 ----
    def _read_exact(self, n: int) -> bytes:
        while len(self.buf) < n:
            chunk = self.conn.recv(65536)
            if not chunk:
                raise ConnectionError("client closed")
            self.buf += chunk
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def read_message(self) -> typing.Tuple[int, bytes]:
        """读一条消息 → (opcode, payload)；只做基础分片拼接。"""
        chunks: typing.List[bytes] = []
        first_opcode = None
        while True:
            head = self._read_exact(2)
            fin = bool(head[0] & 0x80)
            opcode = head[0] & 0x0F
            masked = bool(head[1] & 0x80)
            length = head[1] & 0x7F
            if length == 126:
                length = struct.unpack("!H", self._read_exact(2))[0]
            elif length == 127:
                length = struct.unpack("!Q", self._read_exact(8))[0]
            key = self._read_exact(4) if masked else b""
            payload = self._read_exact(length) if length else b""
            if masked:
                payload = _apply_mask(payload, key)
            if first_opcode is None:
                first_opcode = opcode
            chunks.append(payload)
            if fin:
                return first_opcode, b"".join(chunks)

    def send_frame(self, opcode: int, payload: bytes = b"") -> None:
        length = len(payload)
        header = bytearray([0x80 | (opcode & 0x0F)])
        if length <= 125:
            header.append(length)
        elif length <= 0xFFFF:
            header.append(126)
            header += struct.pack("!H", length)
        else:
            header.append(127)
            header += struct.pack("!Q", length)
        self.conn.sendall(bytes(header) + payload)

    def send_text(self, text: str) -> None:
        self.send_frame(OP_TEXT, text.encode("utf-8"))

    def send_close(self, code: int = 1000) -> None:
        self.send_frame(OP_CLOSE, struct.pack("!H", code))

    def close(self) -> None:
        try:
            self.conn.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            self.conn.close()
        except OSError:
            pass


def _handle_conn(app: "MockDialogueServer", sock: socket.socket) -> None:
    """单连接主循环：握手 → 收请求 → 按 mode 生成/伪造回复。"""
    conn = _ServerConn(sock)
    if not conn.handshake():
        conn.close()
        return
    app.connections += 1
    app._register(conn)
    if app._stopping:                       # 停服中：握手刚完成的连接也别再服务
        app._unregister(conn)
        conn.close()
        return
    try:
        while True:
            try:
                opcode, payload = conn.read_message()
            except (ConnectionError, socket.timeout, OSError):
                break
            if opcode == OP_CLOSE:
                conn.send_close()
                break
            if opcode == OP_PING:
                conn.send_frame(OP_PONG, payload)
                continue
            if opcode != OP_TEXT:
                continue

            app.requests_seen += 1
            try:
                request = json.loads(payload.decode("utf-8"))
            except Exception:
                app.bad_requests += 1
                continue
            if not isinstance(request, dict):
                app.bad_requests += 1
                continue
            app.last_request = request
            mode = app.mode

            if mode == "close_after_recv":              # 断链场景
                conn.close()
                break
            if mode == "hang":                          # 不回复（客户端应超时）
                time.sleep(min(app.hang_s, 5.0))
                continue
            if mode == "slow":
                time.sleep(max(0, app.latency_ms) / 1000.0)

            reply = app.build_reply(request)
            if mode == "bad_json":                      # 脏数据场景
                conn.send_text("not-a-json")
                app.replies_sent += 1
                continue
            if mode == "bad_version":
                reply["protocol_version"] = "9.9"
            if mode == "wrong_id":
                reply["request_id"] = "stale-0001"
            if mode == "ungrounded":                    # 无人却声明看到人（交给 Validator 拒）
                reply["visual_claims"] = [{"fact": "person_on_left", "source_track_id": 7}]
            if mode == "duplicate":                     # 先发一条**迟到响应**，再发正确的
                stale = dict(reply)
                stale["request_id"] = "stale-0001"
                conn.send_text(json.dumps(stale, ensure_ascii=False))
                app.stale_sent += 1

            conn.send_text(json.dumps(reply, ensure_ascii=False))
            app.replies_sent += 1
    finally:
        app._unregister(conn)
        conn.close()


class MockDialogueServer:
    """可编程的对话主机替身（标准库实现），支持故障/脏数据注入与统计。"""

    def __init__(self, host: str = "127.0.0.1", port: int = 0, mode: str = "normal",
                 latency_ms: int = 0, hang_s: float = 30.0,
                 reply_factory: typing.Optional[typing.Callable[[typing.Dict], typing.Dict]] = None
                 ) -> None:
        self.host = host
        self.port = int(port)
        self.mode = mode
        self.latency_ms = int(latency_ms)
        self.hang_s = float(hang_s)
        self.reply_factory = reply_factory or self._default_reply
        self.connections = 0
        self.requests_seen = 0
        self.replies_sent = 0
        self.stale_sent = 0
        self.bad_requests = 0
        self.last_request: typing.Optional[typing.Dict] = None
        self._server: typing.Optional[socketserver.ThreadingTCPServer] = None
        self._thread: typing.Optional[threading.Thread] = None
        self._conns: typing.List[_ServerConn] = []      # 在处理的连接（stop 时强制断开）
        self._lock = threading.Lock()
        self._stopping = False                          # 已进入停止流程 → 新连接立即关闭

    # ---- 活动连接登记（供 stop() 真断链）----
    def _register(self, conn: "_ServerConn") -> None:
        with self._lock:
            self._conns.append(conn)

    def _unregister(self, conn: "_ServerConn") -> None:
        with self._lock:
            if conn in self._conns:
                self._conns.remove(conn)

    # ---- 回复生成（默认复用 Mock 的 grounded 模板，与既有演示保持一致）----
    def _default_reply(self, request: typing.Dict) -> typing.Dict:
        dto = DialogueRequest.from_dict(request)
        return default_response_factory(dto).to_dict()

    def build_reply(self, request: typing.Dict) -> typing.Dict:
        try:
            reply = dict(self.reply_factory(request))
        except Exception as exc:                        # pragma: no cover - 自定义工厂异常
            reply = {"reply_text": "（mock 主机内部错误：%s）" % exc}
        reply.setdefault("protocol_version", "1.0")
        reply.setdefault("request_id", str(request.get("request_id") or ""))
        reply.setdefault("reply_text", "（mock 回复）")
        return reply

    # ---- 生命周期 ----
    def start(self) -> "MockDialogueServer":
        app = self

        class _Server(socketserver.ThreadingTCPServer):
            allow_reuse_address = True
            daemon_threads = True

        class _Handler(socketserver.BaseRequestHandler):
            def handle(self) -> None:
                _handle_conn(app, self.request)

        self._server = _Server((self.host, self.port), _Handler)
        self.port = int(self._server.server_address[1])   # port=0 时取实际端口
        self._stopping = False
        self._thread = threading.Thread(target=self._server.serve_forever,
                                        daemon=True, name="mock-dialogue")
        self._thread.start()
        return self

    def stop(self) -> None:
        """停止服务：标记 stopping → **强制断开在处理的连接** → 停 accept 循环。

        注意两点（都是真实踩过的坑）：
        ① 必须强制断开在处理的连接，否则 daemon 线程会继续服务，"停服"形同虚设；
        ② 客户端 `connect()` 返回（收到 101）**早于**服务端登记连接，因此还要用
           `stopping` 标志兜住"握手刚完成但尚未登记"的新连接。
        """
        self._stopping = True
        with self._lock:
            conns, self._conns = list(self._conns), []
        for conn in conns:
            conn.close()
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None

    def __enter__(self) -> "MockDialogueServer":
        return self.start()

    def __exit__(self, *_exc) -> None:
        self.stop()

    def stats(self) -> typing.Dict:
        return {"mode": self.mode, "connections": self.connections,
                "requests_seen": self.requests_seen, "replies_sent": self.replies_sent,
                "stale_sent": self.stale_sent, "bad_requests": self.bad_requests,
                "address": "%s:%d" % (self.host, self.port)}


def main() -> int:
    ap = argparse.ArgumentParser(description="mock 对话主机（PC / SIMULATED）")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765, help="监听端口（0 = 随机）")
    ap.add_argument("--mode", default="normal",
                    choices=("normal", "slow", "hang", "close_after_recv", "bad_json",
                             "wrong_id", "duplicate", "bad_version", "ungrounded"))
    ap.add_argument("--latency-ms", type=int, default=0, help="slow 模式延迟")
    args = ap.parse_args()

    server = MockDialogueServer(host=args.host, port=args.port, mode=args.mode,
                                latency_ms=args.latency_ms).start()
    print("Mock 对话主机已启动：ws://%s:%d/dialogue ｜ mode=%s ｜ 环境标签 PC / SIMULATED"
          % (server.host, server.port, server.mode))
    print("等待板端 Adapter 连接……（Ctrl+C 结束）")
    try:
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\n已中断，统计：%s" % server.stats())
    finally:
        server.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
