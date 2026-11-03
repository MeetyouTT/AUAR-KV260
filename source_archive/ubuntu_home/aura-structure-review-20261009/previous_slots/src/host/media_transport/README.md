<!-- aura-architecture-generated -->
# 板端 ↔ Windows 媒体传输 / 重连

模块：M6 / `transport`；负责人：C；目标位置：LAN / 两端。

当前证据层级：**接口或部分实现**。

输入：音频、图像、请求、段流。
输出：带归属回复 / 失败 / 重连。

现有源码/证据来源：

- `host/model_service/client.py`
- `board/runtime/dialogue_client/ws_client.py`

待补：文字 1.0 客户端与同进程媒体接口已有；跨机媒体通道未接。

关联内部验收：T18、T19、T26。

这里是按总框图建立的交付位置和接口说明；本次没有把占位包装为已实现功能。最终工程包必须放入实际使用的源码、输入和实测，而不能仅交本说明。
