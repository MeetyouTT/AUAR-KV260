<!-- aura-architecture-generated -->
# 单一 EventBus / 交互状态机

模块：M7 / `fsm`；负责人：C / B；目标位置：KV260 PS。

当前证据层级：**软件联调通过**。

输入：真实事件 / 取消 / 故障。
输出：角色与会话状态 / 诊断。

现有源码/证据来源：

- `board/runtime/event_bus.py`
- `board/runtime/fsm.py`
- `board/runtime/application.py`

待补：软件已测；真实异步媒体、失联恢复和整机长测待验。

关联内部验收：T19、T26、T27。

这里是按总框图建立的交付位置和接口说明；本次没有把占位包装为已实现功能。最终工程包必须放入实际使用的源码、输入和实测，而不能仅交本说明。
