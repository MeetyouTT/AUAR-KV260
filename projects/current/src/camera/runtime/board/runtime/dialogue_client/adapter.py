# -*- coding: utf-8 -*-
"""Dialogue Adapter 合同（Week A1 · 9/5 任务）

人3 任务书 §五：Open-LLM-VTuber 独立运行在 LAN 主机；自研 Adapter 和 Validator。
本文件定义板端 ↔ 对话主机的数据合同与适配器抽象接口。

合同（V1.0 §22.10）：
  板端请求 DialogueRequest：
    {protocol_version, request_id, audio_generation_id, transcript,
     scene_state, allowed_emotions, allowed_avatar_actions}
  主机响应 DialogueResponse：
    {protocol_version, request_id, scene_seq_used, reply_text,
     emotion, avatar_action, visual_claims}

移植说明：无板开发月为 Python 实现；A3 提供真实 WebSocketAdapter，
MockDialogueAdapter 保持接口不变。
"""
import typing
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

PROTOCOL_VERSION = "1.0"


@dataclass
class DialogueRequest:
    protocol_version: str = PROTOCOL_VERSION
    request_id: str = ""
    audio_generation_id: int = 0
    transcript: str = ""
    scene_state: typing.Dict = field(default_factory=dict)
    allowed_emotions: typing.List[str] = field(default_factory=list)
    allowed_avatar_actions: typing.List[str] = field(default_factory=list)

    def to_dict(self) -> typing.Dict:
        return {
            "protocol_version": self.protocol_version,
            "request_id": self.request_id,
            "audio_generation_id": self.audio_generation_id,
            "transcript": self.transcript,
            "scene_state": self.scene_state,
            "allowed_emotions": list(self.allowed_emotions),
            "allowed_avatar_actions": list(self.allowed_avatar_actions),
        }

    @classmethod
    def from_dict(cls, data: typing.Dict) -> "DialogueRequest":
        return cls(
            protocol_version=data.get("protocol_version", PROTOCOL_VERSION),
            request_id=data.get("request_id", ""),
            audio_generation_id=data.get("audio_generation_id", 0),
            transcript=data.get("transcript", ""),
            scene_state=data.get("scene_state") or {},
            allowed_emotions=data.get("allowed_emotions") or [],
            allowed_avatar_actions=data.get("allowed_avatar_actions") or [],
        )


@dataclass
class DialogueResponse:
    protocol_version: str = PROTOCOL_VERSION
    request_id: str = ""
    scene_seq_used: int = 0
    reply_text: str = ""
    emotion: str = ""
    avatar_action: str = ""
    visual_claims: typing.List[typing.Dict] = field(default_factory=list)
    raw: typing.Dict = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: typing.Dict) -> "DialogueResponse":
        return cls(
            protocol_version=data.get("protocol_version", PROTOCOL_VERSION),
            request_id=data.get("request_id", ""),
            scene_seq_used=data.get("scene_seq_used", 0),
            reply_text=data.get("reply_text", ""),
            emotion=data.get("emotion", ""),
            avatar_action=data.get("avatar_action", ""),
            visual_claims=data.get("visual_claims") or [],
            raw=dict(data),
        )

    def to_dict(self) -> typing.Dict:
        return {
            "protocol_version": self.protocol_version,
            "request_id": self.request_id,
            "scene_seq_used": self.scene_seq_used,
            "reply_text": self.reply_text,
            "emotion": self.emotion,
            "avatar_action": self.avatar_action,
            "visual_claims": [dict(c) for c in self.visual_claims],
        }


class AdapterError(Exception):
    """适配器通信错误（连接失败/协议错误等，区别于 LLM 业务错误）。"""


class DialogueAdapter(ABC):
    """板端 ↔ 对话主机适配器抽象合同。

    实现要求：
      - send_request 必须带超时（timeout_ms），超时抛 TimeoutError；
      - 断链/重连状态必须可查询（health_check）；
      - 旧响应不得覆盖新请求（由上层用 request_id/audio_generation_id 把关）。
    """

    @abstractmethod
    def connect(self) -> bool:
        """建立连接；成功返回 True。"""

    @abstractmethod
    def health_check(self) -> typing.Dict:
        """健康检查：返回 {"ok": bool, "latency_ms": int, "detail": ...}。"""

    @abstractmethod
    def send_request(self, request: DialogueRequest,
                     timeout_ms: int = 4000) -> DialogueResponse:
        """发送对话请求并等待响应；超时抛 TimeoutError，通信错误抛 AdapterError。"""

    @abstractmethod
    def close(self) -> None:
        """关闭连接与资源。"""

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """当前是否已连接。"""
