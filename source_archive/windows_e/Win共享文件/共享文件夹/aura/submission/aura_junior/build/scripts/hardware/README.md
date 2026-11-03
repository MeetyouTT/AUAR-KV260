<!-- aura-architecture-generated -->
# Vivado / Vitis / PetaLinux 构建

模块：M8 / `hardware_build`；负责人：A；目标位置：Ubuntu 构建机。

当前证据层级：**已有有限板测**。

输入：平台 / RTL / XDC / 固定工具。
输出：配套硬件包 / 报告 / SHA。

现有源码/证据来源：

- `/home/ghmd/kv260-visual-servo-20261007/scripts/implement_source_platform.py`
- `/home/ghmd/kv260-visual-servo-20261007/SOURCE_PLATFORM_REPORT.md`

待补：旧源共存工程有构建与板测；最终新监督整体构建和外部约束待补。

关联内部验收：T01、T02。

这里是按总框图建立的交付位置和接口说明；本次没有把占位包装为已实现功能。最终工程包必须放入实际使用的源码、输入和实测，而不能仅交本说明。

<!-- aura-structure-details -->
## 复核后的目录职责

主责：A；运行/使用位置：Ubuntu。

内容：平台/RTL/系统构建流程。

边界：外部旧脚本使用主机绝对路径与缓存，发布前需要参数化及实跑。

依据：C10，见 report/structure_detail.md 的依据登记。

现有来源：

- `/home/ghmd/kv260-visual-servo-20261007/scripts/implement_source_platform.py`

目标目录已建立；本轮没有将实际源文件迁移到此处。
