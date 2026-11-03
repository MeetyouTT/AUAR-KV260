# -*- coding: utf-8 -*-
"""AURA 主机模型服务包（C 线，ASR/VLM/TTS）。

目录来源：《03_C负责人手册》§16.1 目标结构 `aura_fpga/host/model_service/`。
当前状态：协议与 fixture 骨架（可跑单测），真实后端尚未接通。
"""

from .protocol import DOCUMENT_CONTRACT_VERSION, PROTOCOL_VERSION

__all__ = ["PROTOCOL_VERSION", "DOCUMENT_CONTRACT_VERSION"]
