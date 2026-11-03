<!-- aura-architecture-generated -->
# 会话 / 图像绑定 / 取消 / 回复校验

模块：M6 / `media_session`；负责人：C / B；目标位置：KV260 PS。

当前证据层级：**软件联调通过**。

输入：录音与本轮图 / 当前目标。
输出：有效请求 token / 交付结果。

现有源码/证据来源：

- `board/runtime/session.py`
- `board/runtime/media_session.py`

待补：逻辑与 fixture 通过；真实数据传输和播放消费待接。

关联内部验收：T19、T24。

这里是按总框图建立的交付位置和接口说明；本次没有把占位包装为已实现功能。最终工程包必须放入实际使用的源码、输入和实测，而不能仅交本说明。
