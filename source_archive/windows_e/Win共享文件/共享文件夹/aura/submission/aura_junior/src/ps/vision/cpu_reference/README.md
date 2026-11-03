<!-- aura-architecture-generated -->
# CPU YuNet / IoU 参考链

模块：M2 / `cpu_vision`；负责人：B；目标位置：KV260 PS CPU。

当前证据层级：**已有有限板测**。

输入：人脸图像。
输出：参考框 / 轨迹。

现有源码/证据来源：

- `board/vision/reference_core.py`
- `board/vision/reference_faces.py`
- `/home/ghmd/kv260-realtime-vision-20261007/REALTIME_REPORT.md`

待补：它是人脸与 IoU 参考，不能当作人体 DPU 或 ByteTrack 完成。

关联内部验收：T04、T05、T08。

这里是按总框图建立的交付位置和接口说明；本次没有把占位包装为已实现功能。最终工程包必须放入实际使用的源码、输入和实测，而不能仅交本说明。
