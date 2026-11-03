---
name: llm-voice-runtime-optimization
description: 分析本地 LLM 与 TTS 请求时延、缓存和有效样本，或核对语音播放回执与可撤销记忆的提交顺序。
---

在本技能目录运行 python3 -B scripts/check.py。用 scripts/verify_measured_run.py examples/measured 复算模型主机的逐次记录与汇总。比较方案时固定模型、量化、输出上限和 TTS 步数，将冷热状态、TTS 缓存、跳过的请求和语义审核分开记录。分别报告 LLM 首个内容、完整响应、TTS 返回，以及有实物采样时的扬声器首声。

核对播放与记忆时，用 scripts/validate_delivery_trace.py --input 读入归一化轨迹，匹配请求、代次、段号、PCM 指纹和有效时限。完整播放回执才允许提交已播记忆。缺失的时点和无法判定的样本保留 UNKNOWN。示例字段与五对实测数据见[复算说明](readme.md)。
