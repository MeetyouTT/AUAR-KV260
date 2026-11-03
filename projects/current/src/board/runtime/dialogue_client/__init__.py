# -*- coding: utf-8 -*-
"""dialogue_client —— 板端 ↔ LAN 对话主机通信层（人3）。

A1：Adapter 抽象合同 + Mock 实现；
A3：真实 WebSocketAdapter + ASR/TTS 编排。
"""
from .adapter import (PROTOCOL_VERSION, AdapterError, DialogueAdapter,
                      DialogueRequest, DialogueResponse)
from .mock_adapter import MockDialogueAdapter, default_response_factory

__all__ = [
    "PROTOCOL_VERSION", "AdapterError", "DialogueAdapter",
    "DialogueRequest", "DialogueResponse",
    "MockDialogueAdapter", "default_response_factory",
]
