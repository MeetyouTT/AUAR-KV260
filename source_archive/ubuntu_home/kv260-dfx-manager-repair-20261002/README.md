# KV260 DFX manager 监视项修复

本目录保存固定版本的独立修复、主机构建、有限板端复验及恢复证据。

- dfx-mgr：`bc06691eb35d7f0acb7c2508b6d050d77b0264a0`。
- libdfx：`f2b7bbca9d6936141024becfb92266600eeefc2b`。
- 输入：已封存的 M3 板测日志、官方配方和原镜像。
- 范围：修复 watch 表重复登记，保留容量和原加载流程。
- 候选已通过主机回归和有限板端复验；原驱动、管理器、官方活动应用已恢复，26 份运行文件哈希与测试前一致。
- 候选没有永久安装；原程序中原有的管理器和 ZOCL 缺陷仍然存在。

结果见 [DFX_MANAGER_REPAIR_REPORT.md](DFX_MANAGER_REPAIR_REPORT.md) 和 [CURRENT_STATUS.md](CURRENT_STATUS.md)。本轮没有烧录、重启、PWM 或执行器操作。

可交付候选位于 `release/kv260-dfx-watch-reviewed.tar.gz`。二进制与已板测候选一致；新包只做整理和哈希回读，没有再次部署。`bundle-v2` 保留为历史测试输入，其原就绪探针使用 SOCK_STREAM 的失败及独立续跑修正均已记录，不能盲目重放。
