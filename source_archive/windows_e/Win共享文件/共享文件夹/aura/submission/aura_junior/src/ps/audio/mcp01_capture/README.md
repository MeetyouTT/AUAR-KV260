<!-- aura-architecture-generated -->
# MCP01 USB 采集 / 实际样本时钟

模块：M6 / `mcp_capture`；负责人：C；目标位置：KV260 PS。

当前证据层级：**待实现或待实验**。

输入：实际 USB 音频 / 按键。
输出：PCM + AudioRef / 样本时间。

现有源码/证据来源：

- `host/model_service/protocol.py`

待补：设备身份、实际格式、录音转换、xrun 与并发未实测。

关联内部验收：T16、T18、T26。

这里是按总框图建立的交付位置和接口说明；本次没有把占位包装为已实现功能。最终工程包必须放入实际使用的源码、输入和实测，而不能仅交本说明。
