<!-- aura-architecture-generated -->
# PL 官方 DPU：单 CU B4096

模块：M1 / `dpu`；负责人：A / B；目标位置：KV260 PL。

当前证据层级：**已有有限板测**。

输入：模型张量 / DDR。
输出：神经网络输出。

现有源码/证据来源：

- `/home/ghmd/kv260-visual-servo-20261007/BOARD_TEST_REPORT.md`

待补：历史分类与共存板测已有；项目检测/身份共享负载待验。

关联内部验收：T02、T04、T05。

这里是按总框图建立的交付位置和接口说明；本次没有把占位包装为已实现功能。最终工程包必须放入实际使用的源码、输入和实测，而不能仅交本说明。

<!-- aura-structure-details -->
## 复核后的目录职责

主责：A；运行/使用位置：KV260 PL 集成。

内容：官方 DPU 配置、版本、来源、架构指纹及集成输入。

边界：不声称拥有/交付 AMD DPU 的自研 RTL；以实际授权工具/IP 获取流程复建。

依据：P2、C8、C10，见 report/structure_detail.md 的依据登记。

现有来源：

- `hardware/platform/platform_manifest.json`

目标目录已建立；本轮没有将实际源文件迁移到此处。
