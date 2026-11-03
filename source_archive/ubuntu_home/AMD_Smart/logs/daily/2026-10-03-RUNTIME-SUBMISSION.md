# 2026-10-03：运行时复现与参赛附件

在独立目录 /home/ghmd/kv260-runtime-submission-20261002 整理运行时源码与证据。未覆盖用户项目.zip、原工具/源码、板卡基线或旧封存报告。原五份索引共 1,779 条记录核对通过。

DFX 固定源码 139 文件及两项补丁还原通过；最初完整 XRT 2,278 文件快照保留。其 6 个路径含 ++ / %，实际命名审阅失败留存；按 ARM ZOCL 范围导出 840 个内容不变的 runtime core 文件，旧编译依赖中的 69 份 XRT 源码/头文件均覆盖。

三个独立目录 DFX 新构建通过，原镜像 ABI/loader 检查通过；daemon 84 个强依赖无未解析项。最终独立目录再完整执行内核 prepare、vmlinux/modules 和 ZOCL 编译三阶段：准备/模块并行 4、内核并行 8，内核编译 477.246 秒。配置仅 GCC 名称 .real 文本差异；新 Module.symvers 与旧表逐字节相同。

新 ZOCL srcversion 9BDC942A6014BCCBD1DCB78、vermagic 5.15.36-xilinx-v2022.2 SMP mod_unload aarch64 与旧修复版匹配；.text 相同，字符串区规范化源码前缀后相同，完整模块哈希不同。四类模块 warning 与原 baseline / patched 相同，原样保存。新输出没有上板或替代已板测输入。

skill-creator 用于提炼真实排错案例；工具 9 项本机隔离验证及技能结构检查通过。初次创建 Unix socket 被沙箱 EPERM 拒绝的记录保留；批准沙箱外验证后通过。目标只读预检拒绝开发电脑通过，没有执行真实板端预检。

verified v2 源码包已完成 525 文件索引和 526 压缩包成员回读哈希检查；SHA-256 5cf9f945f9269c8df844e41c49f50d738fa2e7d9fd4d79bf25c97a743033ffab。初版包与完整快照另存。

末尾仍没有 /dev/serial/by-id，没有新板端实时状态、应用/驱动切换、长期复验、永久启用、SD/QSPI 烧录或 PWM。接回备用卡 USB 串口后继续实时预检、备份、受控启用和 30 轮/至少 30 分钟复验。全文可见交互导出、完整 AURA/自研硬件材料、最新细则及公开仓库仍待补齐。

报告：[CONTINUATION_REPORT.md](/home/ghmd/kv260-runtime-submission-20261002/CONTINUATION_REPORT.md)。
最新包：[kv260_runtime_annex_verified_20261003.tar.gz](/home/ghmd/kv260-runtime-submission-20261002/release/kv260_runtime_annex_verified_20261003.tar.gz)。
