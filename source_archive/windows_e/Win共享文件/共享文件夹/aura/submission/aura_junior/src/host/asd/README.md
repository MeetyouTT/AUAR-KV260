<!-- aura-architecture-generated -->
# Windows Light-ASD / 有限上下文

模块：M7 / `asd`；负责人：C；目标位置：Windows 模型主机。

当前证据层级：**待实现或待实验**。

输入：同期录音 / 每人连续脸片段。
输出：每人分数 / 模型与窗口归属。

现有源码/证据来源：

- `config/model_manifest.json`

待补：模型与作者样例、真实同窗输入和两人测试未接。

关联内部验收：T15。

这里是按总框图建立的交付位置和接口说明；本次没有把占位包装为已实现功能。最终工程包必须放入实际使用的源码、输入和实测，而不能仅交本说明。

<!-- aura-structure-details -->
## 复核后的目录职责

主责：C，B 复核对象；运行/使用位置：Windows 模型主机。

内容：Light-ASD 同窗视听推理与质量/分数。

边界：真实模型和同步未完成；只给建议，不生成舵机坐标。

依据：P1、P2，见 report/structure_detail.md 的依据登记。

现有来源：

- `config/model_manifest.json`

目标目录已建立；本轮没有将实际源文件迁移到此处。
