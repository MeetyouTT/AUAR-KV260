<!-- aura-architecture-generated -->
# ByteTrack / 轨迹代次 / 人员事件

模块：M2 / `tracking`；负责人：B；目标位置：KV260 PS。

当前证据层级：**接口或部分实现**。

输入：高低分检测 / 空帧 / 源时间。
输出：TrackKey / 生命周期 / 人员事件。

现有源码/证据来源：

- `board/vision/tracking.py`
- `common/contracts.py`

待补：IoU 运行接入已验证；ByteTrack 依赖、实际视频与交叉遮挡待验。

关联内部验收：T08、T09。

这里是按总框图建立的交付位置和接口说明；本次没有把占位包装为已实现功能。最终工程包必须放入实际使用的源码、输入和实测，而不能仅交本说明。
