# KV260 修复当前状态

更新日期：2026-10-02（America/Los_Angeles）。

**ZOCL 修复候选的官方应用有限板测已通过，原驱动及官方应用已恢复。**

- 原驱动下重新出现一次 `/axi/zyxclmm_drm` 的 `expected refcount 1 instead of 2`。
- 修复后三轮加载、同图推理、卸载均未新增该错误；Samoyed Top-1 始终为 `0.949879`。
- 单线程中位数原／修复为 `215.130 / 215.129 FPS`，双线程为 `238.837 / 238.885 FPS`。
- 4 条只读预检及 48 条主验证命令通过；原固件、模型、图片及测试程序等 11 份文件首尾哈希一致。
- 当前加载的是原 `0991D1B457855C8987936E6` 驱动，活动应用为 `kv260-benchmark-b4096` slot 0。

修复没有永久安装；设备树动态属性警告仍在；长期／并发运行和 M3 共存、AXI-Lite／运动模块尚未板测。

详见 [BOARD_REPAIR_REPORT.md](BOARD_REPAIR_REPORT.md)。旧 README、主机修复报告和验证计划中的“待板测／暂停”是此前封存的历史状态，保持原样。最终机器结果见 [board_validation_summary.json](evidence/board_validation_20261003T005805Z/board_validation_summary.json)。
