<!-- aura-architecture-generated -->
# 框架联调 / 媒体交付 / 异常测试

模块：M8 / `software_verify`；负责人：A / B / C；目标位置：PC 软件。

当前证据层级：**软件联调通过**。

输入：合成帧 / 乱序 / 取消 / 身份库。
输出：41 项测试与联调记录。

现有源码/证据来源：

- `tests/framework`
- `metrics/raw/framework-validation-20261009/validation.json`

待补：不能替代设备、真实模型或整机验收。

关联内部验收：T09、T19、T23、T24。

这里是按总框图建立的交付位置和接口说明；本次没有把占位包装为已实现功能。最终工程包必须放入实际使用的源码、输入和实测，而不能仅交本说明。

<!-- aura-structure-details -->
## 复核后的目录职责

主责：B/C；A 审合同；运行/使用位置：PC。

内容：纯软件单元/合同/集成测试与 fixture。

边界：源码中的 SimulationGuard 在 src/ps/motion；这里放验证它的用例。

依据：C2、C13，见 report/structure_detail.md 的依据登记。

现有来源：

- `tests/framework`
- `tests`

目标目录已建立；本轮没有将实际源文件迁移到此处。
