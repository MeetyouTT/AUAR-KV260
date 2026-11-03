# -*- coding: utf-8 -*-
"""Ollama 对话主机（**零第三方依赖** WebSocket 服务端）—— 本地实机演示用。

角色：LAN 主机侧服务。板端 `WebSocketAdapter` 连它（默认 `127.0.0.1:8765`，路径 `/dialogue`）。

合同（**不改**，见 `board/runtime/dialogue_client/adapter.py`）：

    收到 DialogueRequest  {protocol_version, request_id, audio_generation_id, transcript,
                           scene_state, allowed_emotions, allowed_avatar_actions}
    返回 DialogueResponse {protocol_version, request_id, scene_seq_used, reply_text,
                           emotion, avatar_action, visual_claims}

关键设计
--------
1. **零第三方依赖**：自写 RFC6455 服务端（握手 + 文本帧 + ping/pong + close），帧口径与
   项目自研客户端 `ws_client.py` 严格对应：服务端→客户端**不加掩码**（客户端 `_recv_frame`
   已容忍带/不带掩码，见其 :199 注释）。
2. **LLM 输出必须被约束成合同 JSON**：用 Ollama `format="json"`，提示词里直接给出**白名单**
   （取自 `board/runtime/avatar_actions.ALLOWED_AVATAR_ACTIONS` —— P0-4 的单一来源），返回后
   再做**归一化 + 兜底**（未知 emotion → neutral；白名单外动作 → 空串），保证板端
   `policy_validator` 不会把整条响应判为非法。
3. **后端可切换**：`--backend ollama`（默认）或 `--backend mock`（不依赖 LLM 的确定性回复，
   用来先验证 WS 链路本身）。
4. **串行**：单连接逐请求同步处理（演示用途，不做并发）；客户端断开后回到 accept 等待重连。

用法（本机无系统 Python，用 ComfyUI 便携解释器）：
    "<PY>" -s tools\\dialogue_host_ollama.py --backend ollama --model huihui_ai/qwen3-abliterated:14b
    "<PY>" -s tools\\dialogue_host_ollama.py --backend mock          # 不依赖 LLM
自检（不接客户端）：
    "<PY>" -s tools\\dialogue_host_ollama.py --selftest --backend mock
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import socket
import struct
import sys
import time
import typing
import urllib.error
import urllib.request
from pathlib import Path

AURA = Path(__file__).resolve().parents[1]
if str(AURA) not in sys.path:
    sys.path.insert(0, str(AURA))

from board.runtime import avatar_actions                        # noqa: E402
from board.runtime.character import CHARACTER_DESCRIPTION, CHARACTER_NAME, persona_prompt  # noqa: E402
from board.runtime.dialogue_client.adapter import PROTOCOL_VERSION  # noqa: E402

# 控制台可能是 GBK（重定向到文件时尤甚）→ 统一 UTF-8 + 替换，日志/回显不易混淆
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
OP_CONT, OP_TEXT, OP_BIN, OP_CLOSE, OP_PING, OP_PONG = 0x0, 0x1, 0x2, 0x8, 0x9, 0xA
MAX_FRAME_BYTES = 1 << 20
OLLAMA_HOST = "http://127.0.0.1:11434"
DEFAULT_MODEL = "huihui_ai/qwen3-abliterated:14b"
HISTORY_MESSAGES = 8          # 主机侧保留最近 8 条消息（约 4 轮），让回复能接住上文
LAST_TIMINGS = {}


# --------------------------------------------------------------------------- #
# WebSocket 服务端（最小 RFC6455 子集）
# --------------------------------------------------------------------------- #
class WsError(Exception):
    """握手 / 帧层错误。"""


def handshake(conn: socket.socket, expect_path: str) -> str:
    """读 HTTP 升级请求 → 回 101；返回请求路径（不匹配则拒绝）。"""
    data = b""
    while b"\r\n\r\n" not in data:
        chunk = conn.recv(4096)
        if not chunk:
            raise WsError("握手期间连接被关闭")
        data += chunk
        if len(data) > 65536:
            raise WsError("握手请求过大")
    head, _, _tail = data.partition(b"\r\n\r\n")
    lines = head.decode("latin-1").split("\r\n")
    request_line = lines[0] if lines else ""
    parts = request_line.split()
    path = parts[1] if len(parts) > 1 else "/"
    headers = {}
    for line in lines[1:]:
        if ":" in line:
            name, _, value = line.partition(":")
            headers[name.strip().lower()] = value.strip()
    if "websocket" not in headers.get("upgrade", "").lower():
        raise WsError("不是 WebSocket 升级请求：%s" % request_line)
    key = headers.get("sec-websocket-key")
    if not key:
        raise WsError("缺少 Sec-WebSocket-Key")
    if expect_path and path.split("?")[0] != expect_path:
        raise WsError("路径不匹配：%s ≠ %s" % (path, expect_path))
    accept = base64.b64encode(
        hashlib.sha1((key + WS_GUID).encode("ascii")).digest()).decode("ascii")
    conn.sendall((
        "HTTP/1.1 101 Switching Protocols\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        "Sec-WebSocket-Accept: %s\r\n\r\n" % accept).encode("ascii"))
    return path


def _recv_exact(conn: socket.socket, n: int) -> bytes:
    buf = b""
    while len(buf) < n:
        chunk = conn.recv(n - len(buf))
        if not chunk:
            raise WsError("连接已关闭")
        buf += chunk
    return buf


def read_frame(conn: socket.socket) -> typing.Tuple[int, bool, bytes]:
    """读一帧 → (opcode, fin, payload)；**容忍**客户端掩码（RFC 要求客户端必须加）。"""
    head = _recv_exact(conn, 2)
    fin = bool(head[0] & 0x80)
    opcode = head[0] & 0x0F
    masked = bool(head[1] & 0x80)
    length = head[1] & 0x7F
    if length == 126:
        length = struct.unpack("!H", _recv_exact(conn, 2))[0]
    elif length == 127:
        length = struct.unpack("!Q", _recv_exact(conn, 8))[0]
    if length > MAX_FRAME_BYTES:
        raise WsError("帧过大：%d" % length)
    key = _recv_exact(conn, 4) if masked else b""
    payload = _recv_exact(conn, length) if length else b""
    if masked:
        payload = bytes(b ^ key[i % 4] for i, b in enumerate(payload))
    return opcode, fin, payload


def send_frame(conn: socket.socket, opcode: int, payload: bytes = b"") -> None:
    """发一帧（服务端→客户端**不加掩码**）。"""
    header = bytearray([0x80 | (opcode & 0x0F)])
    n = len(payload)
    if n <= 125:
        header.append(n)
    elif n <= 0xFFFF:
        header.append(126)
        header += struct.pack("!H", n)
    else:
        header.append(127)
        header += struct.pack("!Q", n)
    conn.sendall(bytes(header) + payload)


def read_message(conn: socket.socket) -> typing.Optional[str]:
    """收一条完整文本消息；自动回 PONG；Close 返回 None。"""
    chunks: typing.List[bytes] = []
    while True:
        opcode, fin, payload = read_frame(conn)
        if opcode == OP_PING:
            send_frame(conn, OP_PONG, payload)
            continue
        if opcode == OP_PONG:
            continue
        if opcode == OP_CLOSE:
            try:
                send_frame(conn, OP_CLOSE, payload[:2])
            except OSError:
                pass
            return None
        if opcode in (OP_TEXT, OP_BIN, OP_CONT):
            chunks.append(payload)
            if fin:
                break
            continue
        raise WsError("未知 opcode：0x%X" % opcode)
    return b"".join(chunks).decode("utf-8")


# --------------------------------------------------------------------------- #
# LLM 侧：提示词 + 输出解析 + 两种后端
# --------------------------------------------------------------------------- #
SYSTEM_PROMPT = (
    "你在扮演桌面玩偶「{name}」（{description}），和面前的人面对面闲聊。\n"
    "说话要像真人朋友随口聊天：语气自然、有点温度，不用客服腔，也不念旁白。\n"
    "**只输出一个 JSON 对象**，不要解释、不要代码围栏。字段：\n"
    "  \"emotion\": 从这些里选一个 → {emotions}\n"
    "  \"avatar_action\": 从这些里选一个，或空串 → {actions}\n"
    "     含义：ack_nod=确认/答应, deny_shake=否定/拒绝, emo_surprised=惊讶, emo_puzzled=困惑\n"
    "  \"reply_text\": 你要说出口的中文，不超过 {max_chars} 字。硬性要求：\n"
    "     - 标点一律用全角（，。？！、……），禁止半角 , . ? !\n"
    "     - 以短句为主，每句尽量不超过十五个字，像说话换气那样自然断开\n"
    "     - 可以带自然的语气词（呀、啦、吧、呢、嘛、嗯、诶、哦），但别堆叠\n"
    "     - 想拖长或犹豫时用「……」，想强调时可用「！」\n"
    "     - 不要复述对方原话，不要书面语，不要罗列条目或编号\n"
    "     - 通常一两句就好，别长篇大论\n"
    "没有把握时 emotion 用列表第一个、avatar_action 用空串。"
)


def build_system_prompt(allowed_emotions: typing.Sequence, allowed_avatar_actions: typing.Sequence,
                        max_chars: int = 80) -> str:
    """把**请求侧白名单**注入提示词（动作白名单即 P0-4 的单一来源）。"""
    emotions = [str(e) for e in (allowed_emotions or []) if e] or \
               ["neutral", "friendly", "happy", "sad", "low"]
    actions = [str(a) for a in (allowed_avatar_actions or []) if a] or \
              list(avatar_actions.ALLOWED_AVATAR_ACTIONS)
    return persona_prompt() + SYSTEM_PROMPT.format(name=CHARACTER_NAME, description=CHARACTER_DESCRIPTION,
                                emotions=" / ".join(emotions),
                                actions=" / ".join(actions), max_chars=int(max_chars))


def build_user_prompt(request: typing.Dict) -> str:
    ss = request.get("scene_state") or {}
    target = ss.get("current_target") or {}
    return "\n".join([
        "user_text: %s" % (request.get("transcript") or ""),
        "people_count: %s" % ss.get("people_count", 0),
        "camera_state: %s" % ss.get("camera_state", "unknown"),
        "target_position: %s" % (target.get("position") or "none"),
    ])


def extract_json(content: typing.Any) -> typing.Dict:
    """从 LLM 输出里取出 JSON 对象（容忍代码围栏 / 前后废话 / thinking 混杂）。"""
    if not isinstance(content, str):
        return {}
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.lower().startswith("json"):
            text = text[4:].strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return {}
    try:
        data = json.loads(text[start:end + 1])
    except ValueError:
        return {}
    return data if isinstance(data, dict) else {}


_HALF_TO_FULL = str.maketrans({",": "，", "!": "！", "?": "？", ";": "；", ":": "：",
                               "(": "（", ")": "）", "~": "～"})


def to_fullwidth_punctuation(text: str) -> str:
    """把中文回复里的半角标点换成全角：Qwen TTS 的停顿与语气跟着标点走，全角更自然。"""
    return text.translate(_HALF_TO_FULL)


def normalize_reply(data: typing.Dict, request: typing.Dict) -> typing.Dict:
    """LLM 原始字段 → 合同字段（**白名单归一 + 兜底**，保证板端 policy 校验不拒）。"""
    allowed_emotions = [str(e) for e in (request.get("allowed_emotions") or []) if e]
    allowed_actions = [str(a) for a in (request.get("allowed_avatar_actions") or []) if a]
    emotion = str(data.get("emotion") or "").strip().lower()
    if allowed_emotions and emotion not in allowed_emotions:
        emotion = allowed_emotions[0]
    elif not emotion:
        emotion = "neutral"
    action = avatar_actions.normalize(data.get("avatar_action"))
    if not avatar_actions.is_allowed(action) or (allowed_actions and action not in allowed_actions):
        action = ""
    text = data.get("reply_text")
    text = to_fullwidth_punctuation(text.strip()) if isinstance(text, str) else ""
    if not text:
        text = "我在听，请再说一次。"
    return {"emotion": emotion, "avatar_action": action, "reply_text": text}


def fast_system_prompt():
    from common.spoken_input import SPEECH_INPUT_HINT
    return (persona_prompt()+'和面前的人连续闲聊。'
            '自然、亲近、像朋友接话，不复述用户，不用客服语气。通常一两句，最多48个中文字。'
            '用中文全角标点，自然停顿和语气词。记住上文，不虚构视觉。'
            +SPEECH_INPUT_HINT+
            '输出JSON：reply_text为说出口的话，emotion为neutral/friendly/happy/sad之一，avatar_action为空字符串。')


def chat_body(model, system, user, history=None, *, fast=False, num_predict=200):
    messages = [{"role": "system", "content": system}]
    messages.extend(history or [])
    messages.append({"role": "user", "content": user})
    body = {"model": model, "stream": False, "format": "json", "think": False,
            "options": {"temperature": 0.6, "num_predict": int(num_predict)}, "messages": messages}
    if fast:
        body.update(keep_alive='30m', format={'type':'object','properties':{
            'reply_text':{'type':'string'},'emotion':{'type':'string','enum':['neutral','friendly','happy','sad']},
            'avatar_action':{'type':'string','enum':['']}},
            'required':['reply_text','emotion','avatar_action'],'additionalProperties':False})
        body['options'].update(num_ctx=2048,num_predict=120)
    return body


def ollama_chat(model: str, system: str, user: str, host: str = OLLAMA_HOST,
                timeout_s: float = 180.0, num_predict: int = 200,
                history: typing.Optional[typing.Sequence] = None, fast: bool = False) -> str:
    """调 Ollama `/api/chat`（`format=json` + 关 thinking），返回原始 content。

    `history`：前置的 user/assistant 轮次（主机侧维护，协议本身不含历史字段），
    用来让回复接住上文，更像真人连续对话。
    """
    body = chat_body(model, system, user, history, fast=fast, num_predict=num_predict)
    req = urllib.request.Request(host + "/api/chat",
                                 data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    LAST_TIMINGS.clear()
    LAST_TIMINGS.update({key:data.get(key) for key in ('model','load_duration','prompt_eval_duration','eval_duration','eval_count','prompt_eval_count','done_reason')})
    return str((data.get("message") or {}).get("content") or "")


def mock_reply(request: typing.Dict) -> typing.Dict:
    """不依赖 LLM 的确定性回复（先联调 WS 链路本身）。"""
    ss = request.get("scene_state") or {}
    pos = (ss.get("current_target") or {}).get("position")
    user = str(request.get("transcript") or "")
    if ("不用" in user) or ("关灯" in user and "不" in user) or ("别" in user):
        return {"emotion": "neutral", "avatar_action": "deny_shake",
                "reply_text": "好，那我不动它。"}
    if pos in ("left", "center", "right"):
        where = {"left": "左侧", "center": "中间", "right": "右侧"}[pos]
        return {"emotion": "friendly", "avatar_action": "ack_nod",
                "reply_text": "我看到画面%s有一位来访者，需要我做什么？" % where}
    return {"emotion": "neutral", "avatar_action": "",
            "reply_text": "我在听，请再说一次。"}


# --------------------------------------------------------------------------- #
# 请求 → 响应（合同组装）
# --------------------------------------------------------------------------- #
def build_response(request: typing.Dict, backend: str, model: str,
                   max_chars: int = 80,
                   history: typing.Optional[typing.Sequence] = None, strict: bool = False, fast: bool = False,
                   host: str = OLLAMA_HOST) -> typing.Dict:
    """一个请求 → 一条合同响应（**永不让板端校验失败**）。"""
    scene_state = request.get("scene_state") or {}
    if backend == "ollama":
        try:
            if fast:
                system=fast_system_prompt()
                content=ollama_chat(model,system,str(request.get('transcript') or ''),history=history,fast=True,host=host)
            else:content = ollama_chat(model,
                                  build_system_prompt(request.get("allowed_emotions"),
                                                      request.get("allowed_avatar_actions"),
                                                      max_chars),
                                  build_user_prompt(request),
                                  history=history,host=host)
            parsed = extract_json(content)
            if strict and (not parsed or not str(parsed.get('reply_text') or '').strip()):
                raise RuntimeError('对话模型没有返回有效台词')
            parsed = parsed or mock_reply(request)
        except Exception as exc:                      # LLM 不可用 → 兜底，别让演示中断
            if strict:raise RuntimeError('真实对话模型失败：%s' % exc) from exc
            print("[host] ollama 不可用，回落 mock：%s" % exc, flush=True)
            parsed = mock_reply(request)
    else:
        parsed = mock_reply(request)

    norm = normalize_reply(parsed, request)
    return {
        "protocol_version": str(request.get("protocol_version") or PROTOCOL_VERSION),
        "request_id": str(request.get("request_id") or ""),
        "scene_seq_used": int(scene_state.get("scene_seq", 0) or 0),
        "reply_text": norm["reply_text"],
        "emotion": norm["emotion"],
        "avatar_action": norm["avatar_action"],
        "visual_claims": [],          # 默认空：grounding 校验最安全（要演示声明可另扩展）
    }


def serve(host: str, port: int, path: str, backend: str, model: str,
          max_chars: int = 80, once: bool = False, strict: bool = False, fast: bool = False) -> int:
    """监听并逐请求处理（单连接串行；断开后回到 accept 等重连）。"""
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, int(port)))
    srv.listen(4)
    print("[host] listening ws://%s:%d%s  backend=%s model=%s"
          % (host, port, path, backend, model if backend == "ollama" else "-"), flush=True)
    while True:
        conn, addr = srv.accept()
        conn.settimeout(300.0)
        print("[host] client %s:%d connected" % addr, flush=True)
        try:
            handshake(conn, path)
            history: typing.List[typing.Dict[str,str]] = []
            while True:
                raw = read_message(conn)
                if raw is None:
                    break
                t0 = time.time()
                try:
                    request = json.loads(raw)
                except ValueError:
                    print("[host] 非法 JSON，已忽略", flush=True)
                    continue
                if not isinstance(request, dict):
                    continue
                response = build_response(request, backend, model, max_chars, history, strict, fast)
                if fast:print('TIMING '+json.dumps(LAST_TIMINGS),flush=True)
                history.append({"role": "user",
                                "content": str(request.get("transcript") or "")})
                history.append({"role": "assistant", "content": response["reply_text"]})
                del history[:-HISTORY_MESSAGES]          # 只保留最近若干条，控制上下文长度
                send_frame(conn, OP_TEXT,
                           json.dumps(response, ensure_ascii=False).encode("utf-8"))
                print("[host] req=%s emotion=%s action=%s %.0fms | %s"
                      % (response["request_id"], response["emotion"],
                         response["avatar_action"] or "-", (time.time() - t0) * 1000.0,
                         response["reply_text"][:40]), flush=True)
                if once:
                    return 0
        except (WsError, OSError, socket.timeout, RuntimeError) as exc:
            print("[host] 连接结束：%s" % exc, flush=True)
        finally:
            try:
                conn.close()
            except OSError:
                pass
        if once:
            return 0


def selftest(backend: str, model: str) -> int:
    """自检：直接跑一条请求 → 打印合同响应（不开端口、不需要客户端）。"""
    request = {
        "protocol_version": PROTOCOL_VERSION, "request_id": "selftest-1",
        "audio_generation_id": 1, "transcript": "你看到我了吗？",
        "scene_state": {"scene_seq": 7, "camera_state": "online", "people_count": 1,
                        "current_target": {"track_id": 3, "position": "left"}},
        "allowed_emotions": ["neutral", "friendly", "happy", "sad"],
        "allowed_avatar_actions": list(avatar_actions.ALLOWED_AVATAR_ACTIONS),
    }
    resp = build_response(request, backend, model)
    print(json.dumps(resp, ensure_ascii=False, indent=2), flush=True)
    ok = (resp["request_id"] == "selftest-1"
          and resp["protocol_version"] == PROTOCOL_VERSION
          and bool(resp["reply_text"])
          and (not resp["avatar_action"] or avatar_actions.is_allowed(resp["avatar_action"]))
          and resp["emotion"] in request["allowed_emotions"])
    print("SELFTEST %s" % ("OK" if ok else "FAIL"), flush=True)
    return 0 if ok else 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Ollama 对话主机（零依赖 WS 服务端）")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--path", default="/dialogue")
    parser.add_argument("--backend", choices=("ollama", "mock"), default="ollama")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-chars", type=int, default=80)
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--strict", action="store_true", help="真实模型失败时断开并报错，不回落固定回复")
    parser.add_argument("--fast", action="store_true", help="短口语提示、结构化输出、2048上下文、30分钟驻留")
    parser.add_argument("--once", action="store_true", help="处理一条请求后退出")
    args = parser.parse_args(argv)
    if args.selftest:
        return selftest(args.backend, args.model)
    if args.fast and args.backend=='ollama':
        started=time.perf_counter()
        build_response({'transcript':'你好','allowed_emotions':['neutral','friendly','happy','sad']},
                       'ollama',args.model,strict=True,fast=True)
        print('PREWARM_DONE '+json.dumps({'seconds':time.perf_counter()-started,**LAST_TIMINGS}),flush=True)
    return serve(args.host, args.port, args.path, args.backend, args.model,
                 args.max_chars, args.once, args.strict, args.fast)


if __name__ == "__main__":
    sys.exit(main())
