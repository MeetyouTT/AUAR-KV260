# KV260 状态修复：实际板测和冷启动通过的交付包

本包对应 2026-10-04 的同一 SD 卡验收。部署候选为 `bin/dfx-mgrd`（117856 字节，SHA-256 `369c7fb0ddd023a7cf7af14896a7fda6036219a36f4980c73640889720c95dfd`），配置为 `config/20-kv260-dfx-state-repaired.conf`。源码、补丁、本机普通/ASan/UBSan 回归和原镜像 ABI 证据保存在 `inputs/dfx-state-20261004-host-verified.tar.gz`。

实际板端压力、活动包生命周期、10 轮物理加载/卸载、回退、持久化和一次用户确认的冷启动已通过；完整板端归档 5223 个文件逐项回读，累计 23 次原模型/原图分类匹配。当前 boot ID 为 `01ca88c1-93b6-414f-9646-774482d4b2f0`。

先阅读 [板端报告](BOARD_REPAIR_REPORT.md)、[最终状态](FINAL_STATUS.json) 和 [冷启动独立核验](reviews/20261004T084536.786164Z-postboot/COLD_BOOT_VERIFICATION.json)。`PACKAGE_MANIFEST.json` 给出每个包内文件的字节数和 SHA-256；归档外 `PACKAGE_VERIFICATION.json` 记录打包后重新打开、逐成员核验的结果及整包哈希。

## 独立回读

将包解到一个新的目录，在该目录运行：

```sh
python3 scripts/review_board_evidence.py evidence/20261004T084214.824550Z-22-fetch-postboot/postboot-board-evidence-archive.output 77cda60f5390617d5242871ded445917cb3ed2fffd93a101f2350dd8ff084c0c postboot
```

该命令只在本机重读证据，写入新的 review 目录，不连接板卡。历史复核目录内的 `board/` 解包副本没有重复打包，板端原件完整保存在上述归档。回退说明见报告；旧 manager/模块/配置的恢复原件也在板端归档 `backup/` 内。

本包的验证范围为官方 XRT_FLAT 底座和一次冷启动。NFS、TPM、clock、overlay 等旧告警仍存在；真实 PL_DFX 部分重配置、硬件故障注入、TSan、连续断电可靠性，以及 DPU/自研运动 IP 共存和三人整机仍未验收。电源轨与断电时长没有仪器测量。不能把运行时验收替代比赛整机完成。
