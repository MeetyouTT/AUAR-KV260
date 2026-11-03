<!-- aura-architecture-generated -->
# 软件监督合同模型

模块：M5 / `guard_model`；负责人：A / B；目标位置：PC / PS 模拟。

当前证据层级：**软件联调通过**。

输入：命令 / 源证据 / 时钟。
输出：接受、拒绝、到期状态。

现有源码/证据来源：

- `board/motion/guard.py`

待补：需 tick/poll；不能证明 PS 暂停时 FPGA 独立停止。

关联内部验收：T12。

这里是按总框图建立的交付位置和接口说明；本次没有把占位包装为已实现功能。最终工程包必须放入实际使用的源码、输入和实测，而不能仅交本说明。

<!-- aura-structure-details -->
## 复核后的目录职责

主责：B/A；运行/使用位置：PC 联调 / PS 软件参考。

内容：软件合同模型及模拟运动后端。

边界：当前运行时直接依赖；不把它当作 PL 独立到期的证据。

依据：C2、C8，见 report/structure_detail.md 的依据登记。

现有来源：

- `board/motion/guard.py`

目标目录已建立；本轮没有将实际源文件迁移到此处。
