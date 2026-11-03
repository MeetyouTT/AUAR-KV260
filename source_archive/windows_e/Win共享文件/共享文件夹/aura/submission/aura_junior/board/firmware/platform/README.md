<!-- aura-architecture-generated -->
# Linux / 驱动 / SDK / 平台指纹

模块：M1 / `platform`；负责人：A；目标位置：KV260 PS。

当前证据层级：**已有有限板测**。

输入：硬件包与系统版本。
输出：可核验运行环境。

现有源码/证据来源：

- `config/toolchain_lock.json`
- `hardware/platform/platform_manifest.json`
- `/home/ghmd/kv260-reference-2022.2-20260930/DEPLOYMENT_REVIEW.md`

待补：最终镜像、精确器件型号、DPU 指纹与统一发布待冻结。

关联内部验收：T01、T02、T28。

这里是按总框图建立的交付位置和接口说明；本次没有把占位包装为已实现功能。最终工程包必须放入实际使用的源码、输入和实测，而不能仅交本说明。
