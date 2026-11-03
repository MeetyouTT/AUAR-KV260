<!-- aura-architecture-generated -->
# SFace 128 维 CPU 图片参考

模块：M3 / `id_cpu`；负责人：B；目标位置：KV260 PS CPU。

当前证据层级：**已有有限板测**。

输入：对齐人脸。
输出：归一化特征。

现有源码/证据来源：

- `models/vision/sface_2021dec.onnx`
- `/home/ghmd/kv260-adaptation-check-20261006/ADAPTATION_REPORT.md`

待补：既有板端静态图片参考；实时身份应用未验收。

关联内部验收：T21、T22。

这里是按总框图建立的交付位置和接口说明；本次没有把占位包装为已实现功能。最终工程包必须放入实际使用的源码、输入和实测，而不能仅交本说明。
