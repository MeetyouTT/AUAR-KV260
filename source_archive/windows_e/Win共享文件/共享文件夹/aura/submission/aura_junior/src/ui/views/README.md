<!-- aura-architecture-generated -->
# 正式 UI / 字幕 / 对象 / 错误反馈

模块：M7 / `ui`；负责人：C；目标位置：KV260 PS / HDMI。

当前证据层级：**接口或部分实现**。

输入：会话 / 目标 / 身份 / 硬件状态。
输出：正常页 / 调试页 / 字幕。

现有源码/证据来源：

- `board/interaction/qt_app.py`
- `board/interaction/ui_state.py`
- `ui/ui_state.schema.json`

待补：Qt/UI 状态接入已有；实屏完整交互及登记界面待验。

关联内部验收：T23、T25。

这里是按总框图建立的交付位置和接口说明；本次没有把占位包装为已实现功能。最终工程包必须放入实际使用的源码、输入和实测，而不能仅交本说明。
