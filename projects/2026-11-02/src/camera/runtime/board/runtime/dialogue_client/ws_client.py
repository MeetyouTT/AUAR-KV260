# -*- coding: utf-8 -*-
"""最小 RFC6455 WebSocket **客户端**（同步、零第三方依赖）—— A3 · 9/19 任务（人3）

为什么自研（而不是 `pip install websocket-client`）
--------------------------------------------------
1. **板端最终是 C++ 实现**，手写协议层（握手 / 帧 / mask / ping-close）与板端一一对应，
   移植时不用"先猜 Python 库做了什么"；
2. 无板开发月**网络受限**（github/huggingface 直连不通），只为跑通合同不值得引入外部依赖；
3. 需求极小：连一次、发文本、收文本、ping、关。

如实标注的**限制**
------------------
- 不支持扩展协商（`permessage-deflate`）、不支持二进制大消息与协商压缩；
- 无 TLS / 代理支持（本项目 LAN 明文，板端同一网段）；
- 分片（continuation）只做**拼接**，不做流式重组上限控制。
生产/联调若需要更全特性，可等价替换为 `websocket-client`（接口一致，见 `ws_adapter.py` 注释）。

环境标签：PC / SIMULATED。
"""
from __future__ import annotations

import base64
import hashlib
import os
import socket
import struct
import time
import typing

WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

OP_CONT = 0x0
OP_TEXT = 0x1
OP_BIN = 0x2
OP_CLOSE = 0x8
OP_PING = 0x9
OP_PONG = 0xA

MAX_FRAME_BYTES = 1 << 20          # 单帧/整条消息上限（1 MiB，LAN 对话文本足够）


class WebSocketError(Exception):
    """WebSocket 协议/网络层错误（上层转成 AdapterError）。"""


class WebSocketHandshakeError(WebSocketError):
    """握手失败（非 101 / Accept 校验不过）。"""


class WebSocketClosed(WebSocketError):
    """对端主动关闭或连接已断开。"""


def _mask_payload(payload: bytes, key: bytes) -> bytes:
    """RFC6455 掩码：客户端发出的帧**必须**加掩码。"""
    return bytes(b ^ key[i % 4] for i, b in enumerate(payload))


class WebSocketClient:
    """同步阻塞式 WebSocket 客户端（文本消息为主）。"""

    def __init__(self, host: str, port: int, path: str = "/",
                 timeout_s: float = 5.0) -> None:
        self.host = host
        self.port = int(port)
        self.path = path if path.startswith("/") else "/" + path
        self.timeout_s = float(timeout_s)
        self._sock: typing.Optional[socket.socket] = None
        self._recv_buf = b""                # 帧内续读缓冲

    # ------------------------------------------------------------ 连接
    @property
    def is_connected(self) -> bool:
        return self._sock is not None

    def connect(self, timeout_s: typing.Optional[float] = None) -> bool:
        """建立 TCP 连接并完成 HTTP Upgrade 握手；失败抛 WebSocketError。"""
        self.close()
        timeout = self.timeout_s if timeout_s is None else float(timeout_s)
        try:
            sock = socket.create_connection((self.host, self.port), timeout=timeout)
        except OSError as exc:
            raise WebSocketError("连接 %s:%d 失败：%s" % (self.host, self.port, exc)) from exc
        sock.settimeout(timeout)
        self._sock = sock
        self._recv_buf = b""

        key = base64.b64encode(os.urandom(16)).decode("ascii")
        request = (
            "GET %s HTTP/1.1\r\n"
            "Host: %s:%d\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            "Sec-WebSocket-Key: %s\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "\r\n" % (self.path, self.host, self.port, key)
        )
        sock.sendall(request.encode("ascii"))
        header = self._read_http_header()
        status_line, _, rest = header.partition("\r\n")
        if " 101" not in status_line:
            self.close()
            raise WebSocketHandshakeError("升级失败：%s" % status_line.strip())

        headers = {}
        for line in rest.split("\r\n"):
            if ":" in line:
                name, _, value = line.partition(":")
                headers[name.strip().lower()] = value.strip()
        expect = base64.b64encode(
            hashlib.sha1((key + WS_GUID).encode("ascii")).digest()).decode("ascii")
        if headers.get("sec-websocket-accept") != expect:
            self.close()
            raise WebSocketHandshakeError("Sec-WebSocket-Accept 校验失败")
        return True

    def _read_http_header(self) -> str:
        """读到 \\r\\n\\r\\n 为止（返回含这两行的字符串）。"""
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = self._sock.recv(4096)
            if not chunk:
                raise WebSocketHandshakeError("握手期间连接被关闭")
            data += chunk
            if len(data) > 65536:
                raise WebSocketHandshakeError("握手响应过大")
        head, _, tail = data.partition(b"\r\n\r\n")
        self._recv_buf = tail                   # 握手后可能已带首帧
        return head.decode("latin-1")

    # ------------------------------------------------------------ 发送
    def _send_frame(self, opcode: int, payload: bytes = b"", fin: bool = True) -> None:
        if self._sock is None:
            raise WebSocketClosed("连接已关闭")
        length = len(payload)
        header = bytearray()
        header.append((0x80 if fin else 0x00) | (opcode & 0x0F))
        if length <= 125:
            header.append(0x80 | length)
        elif length <= 0xFFFF:
            header.append(0x80 | 126)
            header += struct.pack("!H", length)
        else:
            header.append(0x80 | 127)
            header += struct.pack("!Q", length)
        key = os.urandom(4)
        header += key
        try:
            self._sock.sendall(bytes(header) + _mask_payload(payload, key))
        except OSError as exc:
            self.close()
            raise WebSocketClosed("发送失败：%s" % exc) from exc

    def send_text(self, text: str) -> None:
        self._send_frame(OP_TEXT, text.encode("utf-8"))

    def send_ping(self, payload: bytes = b"") -> None:
        self._send_frame(OP_PING, payload)

    # ------------------------------------------------------------ 接收
    def _recv_exact(self, n: int, deadline: float) -> bytes:
        """从缓冲/socket 精确读 n 字节；超时抛 TimeoutError，断开抛 WebSocketClosed。"""
        while len(self._recv_buf) < n:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("接收超时")
            if self._sock is None:
                raise WebSocketClosed("连接已关闭")
            self._sock.settimeout(remaining)
            try:
                chunk = self._sock.recv(65536)
            except socket.timeout as exc:
                raise TimeoutError("接收超时") from exc
            except OSError as exc:
                self.close()
                raise WebSocketClosed("接收失败：%s" % exc) from exc
            if not chunk:
                self.close()
                raise WebSocketClosed("对端关闭连接")
            self._recv_buf += chunk
        out, self._recv_buf = self._recv_buf[:n], self._recv_buf[n:]
        return out

    def _recv_frame(self, deadline: float) -> typing.Tuple[int, bool, bytes]:
        """读一帧 → (opcode, fin, payload)。"""
        head = self._recv_exact(2, deadline)
        fin = bool(head[0] & 0x80)
        opcode = head[0] & 0x0F
        masked = bool(head[1] & 0x80)
        length = head[1] & 0x7F
        if length == 126:
            length = struct.unpack("!H", self._recv_exact(2, deadline))[0]
        elif length == 127:
            length = struct.unpack("!Q", self._recv_exact(8, deadline))[0]
        if length > MAX_FRAME_BYTES:
            raise WebSocketError("帧过大：%d 字节" % length)
        key = self._recv_exact(4, deadline) if masked else b""
        payload = self._recv_exact(length, deadline) if length else b""
        if masked:                                   # 服务端一般不加掩码，容忍即可
            payload = _mask_payload(payload, key)
        return opcode, fin, payload

    def recv_text(self, timeout_s: typing.Optional[float] = None) -> str:
        """收**一条完整文本消息**：自动回 pong、拼接分片；对端 Close 抛 WebSocketClosed。"""
        deadline = time.monotonic() + (self.timeout_s if timeout_s is None else float(timeout_s))
        chunks: typing.List[bytes] = []
        while True:
            opcode, fin, payload = self._recv_frame(deadline)
            if opcode == OP_PING:
                self._send_frame(OP_PONG, payload)
                continue
            if opcode == OP_PONG:
                continue
            if opcode == OP_CLOSE:
                try:
                    self._send_frame(OP_CLOSE, payload[:2])
                finally:
                    self.close()
                raise WebSocketClosed("对端发送 Close 帧")
            if opcode in (OP_TEXT, OP_BIN, OP_CONT):
                chunks.append(payload)
                if fin:
                    break
                continue
            raise WebSocketError("未知 opcode：0x%X" % opcode)
        try:
            return b"".join(chunks).decode("utf-8")
        except UnicodeDecodeError as exc:
            raise WebSocketError("载荷不是合法 UTF-8") from exc

    def recv_pong(self, timeout_s: typing.Optional[float] = None,
                  on_text: typing.Optional[typing.Callable[[bytes], None]] = None) -> bool:
        """等待 PONG（健康检查用）：期间自动回 PING、把文本帧交给 `on_text`、忽略其它控制帧。"""
        deadline = time.monotonic() + (self.timeout_s if timeout_s is None else float(timeout_s))
        while True:
            opcode, _fin, payload = self._recv_frame(deadline)
            if opcode == OP_PONG:
                return True
            if opcode == OP_PING:
                self._send_frame(OP_PONG, payload)
                continue
            if opcode == OP_CLOSE:
                try:
                    self._send_frame(OP_CLOSE, payload[:2])
                finally:
                    self.close()
                return False
            if opcode in (OP_TEXT, OP_BIN, OP_CONT):
                if on_text is not None:
                    on_text(payload)
                continue
            return False

    def close(self) -> None:
        """关闭连接（幂等）。"""
        sock, self._sock = self._sock, None
        self._recv_buf = b""
        if sock is not None:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                sock.close()
            except OSError:
                pass
