# KV260 运行时源码与复现附件

这是 AURA / KV260 参赛工程的运行时附件，覆盖 DFX manager 与 ZOCL 两项最小修复。已导出固定源码、原许可、补丁、真实失败/成功证据、独立主机复现入口和可复用技能。完整 AURA 应用、PWM、自研硬件工程导出和最终比赛材料仍需补齐。

## 当前已完成

- DFX 原始/修复源码各 139 个文件；XRT 运行时源码快照导出 840 个文件。完整上游 2,278 文件快照另保存在主机证据区；导出不改变源码内容，覆盖旧编译记录的全部 69 份 XRT 源码依赖。
- DFX manager 新入口在独立目录构建成功，ELF 与原镜像 ABI/加载器检查通过。新构建输出没有上板；全 ELF 哈希随路径变化，不能称逐字节可复现。
- 已板测的两项二进制保留在 `tested_inputs/`，仅作为复用输入；与这次主机构建的 `host_rebuild/` 区分。
- 技能工具完成本机隔离验证；沙箱最初禁止创建测试 socket 的失败记录保留。接板预检脚本已准备，但没有取得新的板端状态。

此前联合有限板测通过 1,000 次 list 循环、50 轮目录增删、3 轮官方应用重载和官方/M3 同图推理；随后恢复了原 manager、原 ZOCL 和官方应用。它不是长期验收，也不是永久启用。

## 查阅入口

| 文件或目录 | 内容 |
|---|---|
| [docs/reproducibility.md](docs/reproducibility.md) | 源码准备、DFX / ZOCL 构建入口、外部依赖和本次验证边界 |
| [docs/version_rationale.md](docs/version_rationale.md) | 保留 2022.2 的理由、DPU 4.0/4.1 与模型差异 |
| [docs/contributions_and_licenses.md](docs/contributions_and_licenses.md) | 上游、自研/修复范围和许可清单 |
| [docs/collaboration_log.md](docs/collaboration_log.md) | 真实可见提示、纠错案例和记录范围 |
| [docs/board_next_steps.md](docs/board_next_steps.md) | 新预检、启用、长期复验和恢复顺序 |
| [skill/README.md](skill/README.md) | 技能的用途、运行方法、失效条件和效果证据 |
| [config/source_lock.json](config/source_lock.json) | commit、补丁、内核配置及板测输入哈希 |
| [evidence/verification_summary.json](evidence/verification_summary.json) | 本附件本次主机验证摘要 |

`evidence/historical/` 和 `evidence/board_outputs/` 来自封存证据，原样复制。历史报告中的绝对链接指向原工作区；新入口使用相对链接。`config/runtime_requirements.json` 原样保存了旧单独 DFX 包的描述，其中 “not included in this package” 指其来源包；本附件的 `tested_inputs/zocl.ko` 是明确列出的复用输入。

## 尚未完成

本次完整内核/ZOCL 新入口已在独立目录执行通过，见 [docs/kernel_zocl_validation.md](docs/kernel_zocl_validation.md)。尚未在陌生环境从零安装 SDK 复现；原构建与新构建日志均保留。UART 未连接，所以本次没有板端切换、30 轮重载、30 分钟采样、永久启用或 PWM 验收。

尚未公开 GitHub/Gitee；完整可见对话导出、完整自研硬件/应用源码、报名资格和最新比赛评分细则仍待补齐。本附件不能单独当作最终参赛作品提交。

原工程、安装、ZIP 和封存证据不作覆盖。各路径采用英文；上游必需的 `CMakeLists.txt`、`Makefile`、`LICENSE` 和标准 `SKILL.md` 保持原名。没有将所有第三方组件重新标为 MIT。
