<!-- aura-architecture-generated -->
# MCP01 播放 / 真实停声 / 半双工

模块：M6 / `mcp_play`；负责人：C；目标位置：KV260 PS。

当前证据层级：**待实现或待实验**。

输入：有效 PCM 段 / cancel。
输出：真实样本进度 / 静音与结束事件。

现有源码/证据来源：

- `board/runtime/audio/tts.py`
- `board/runtime/media_session.py`

待补：逻辑 token 有效；声卡取消、缓冲清理、首声与半双工待验。

关联内部验收：T18、T19。

这里是按总框图建立的交付位置和接口说明；本次没有把占位包装为已实现功能。最终工程包必须放入实际使用的源码、输入和实测，而不能仅交本说明。
