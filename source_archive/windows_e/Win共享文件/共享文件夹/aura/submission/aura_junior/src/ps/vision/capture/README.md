<!-- aura-architecture-generated -->
# USB 相机：唯一来源与最新帧槽

模块：M2 / `camera`；负责人：B；目标位置：KV260 PS。

当前证据层级：**已有有限板测**。

输入：实际帧与采集元数据。
输出：FrameRef + 最新图像。

现有源码/证据来源：

- `board/vision/capture.py`
- `board/vision/frames.py`
- `/home/ghmd/kv260-realtime-vision-20261007/realtime_vision.py`

待补：原 CPU 相机链已有板测；新框架采集适配未开设备，曝光时间语义待校准。

关联内部验收：T05、T06、T24。

这里是按总框图建立的交付位置和接口说明；本次没有把占位包装为已实现功能。最终工程包必须放入实际使用的源码、输入和实测，而不能仅交本说明。
