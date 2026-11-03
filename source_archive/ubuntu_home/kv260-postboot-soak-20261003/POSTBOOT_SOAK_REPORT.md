# KV260 持久化运行时冷启动后采样复测报告

## 结论

本轮约 30 分钟的冷启动后采样功能复测通过：60 次原 ResNet18/原图片分类全部返回 0，完整 Top-5 全部与基线一致；manager、修复 ZOCL、官方 B4096 应用及 DPU 配置维持预期状态。Ubuntu 收到全部证据后独立核验 19 项，全部通过。

测试不是持续满负载推理：实际执行方式为一次单图片分类后等待 30 秒，共 60 次。先前持久化前的持续推理测试仍是独立证据；本次不新增 FPS、断电、PWM 或执行器验收结论。

## 本轮结果

| 项目 | 实测结果 |
|---|---|
| 单调时钟时长 | `1799.56 s`，约 29 分 59.6 秒；结束检测误差不超过约 1.1 秒 |
| 分类别测试 | `60/60` 返回 0，完整 Top-5 匹配 |
| Top-1 | Samoyed，`0.949879`，60 次一致 |
| 运行状态采样 | `60` 份；manager PID 恒为 `1012`，ZOCL refcnt 恒为 `0` |
| Boot ID | `0251d729-0d3c-44e8-abb9-27121306c081`，没有重启 |
| 备用 SD 卡 CID | `0353445345333247805558c00401a100` |
| 修复 ZOCL srcversion | `9BDC942A6014BCCBD1DCB78` |
| manager/loader | 最终均 active、Result=success；manager 仍使用修复版路径 |
| 活动应用 | 官方 `kv260-benchmark-b4096`，slot 0 |
| 最终 DPU query | 返回 0；1 CU、`DPUCZDX8G_ISA1_B4096`、300 MHz、`0xa0010000` |
| DPU fingerprint | `0x101000056010407`，与原基线一致 |
| VAI 运行库版本 | 最终 query 中 VAI Version 与此前原基线 query 完全一致 |
| 原 26 项文件 | 测前关键输入及测后完整清单匹配；测后 `26/26` |
| 主机原持久化审阅包 | 原 `PLAN_SHA256SUMS` 的 `26/26` 仍匹配 |

完整 Top-5：Samoyed `0.949879`、white wolf `0.00931229`、Pomeranian `0.00821807`、Great Pyrenees `0.00498451`、Arctic fox `0.00388194`。

MemAvailable 初值 `3667848 KiB`，末值 `3653784 KiB`，范围 `3653784–3675220 KiB`。首尾减少 `14064 KiB`，约 13.7 MiB。本轮保存了采样和完整末态 meminfo，但没有对缓存、后台进程等因素做归因，不能据此单独排除或确认内存泄漏。

## 日志覆盖与保留的问题

最终 dmesg 是环形缓冲区快照，只保留本轮区间的 683 行，较早条目被覆盖。随后补充获取 `journalctl -k -b --no-pager -o short-monotonic`，返回 0，记录从开机 `0.0 s` 至 `3030.791306 s`，完整覆盖本轮 `1229.93–3029.49 s`；该区间有 2340 行内核记录，首末记录分别在 `1230.133918 s` 和 `3028.857773 s`。

测试区间没有 error/fail/warn/oops/BUG/Call Trace/panic/timeout/segfault 关键词候选。日志主要为客户端创建/释放、共享上下文添加/删除及 bitstream 引用释放。每轮出现一次 `skip kind 29(AIE_RESOURCES) return code: -22`，共 60 次；同类提示在本轮之前的冷启动基线日志中已存在。提示保留原文，本次未修复该提示，也没有把其负返回码改写成成功。分类及最终 query 的实际返回码均为 0。

已知未解决项仍包括 `/boot` FAT 未正常卸载警告、`/etc/fstab` 两条 `/boot` 条目、开机 `nfsd` 挂载失败及原 overlay/IRQ 提示。它们不能被本轮功能通过结论视为已解决。

板端日期未同步，保存的墙上时间仍显示 2021-11-19；时长依据启动 ticks、`/proc/uptime` 和 boot ID。主机证据收集日期为 2026-10-03。

初步摘要生成时 `collector.log` 尚在写入。初步清单保留为 `evidence.preliminary.sha256`，在循环和收集程序都结束后重新生成最终 `evidence.sha256` 并回读。最终清单的 106 项均匹配；补充内核包的 3 项清单也均匹配。

## 本轮新增文件与证据

主机工作目录：`/home/ghmd/kv260-postboot-soak-20261003/`。此前构建、修复和持久化报告目录保持原样，本轮只创建新的日志、采集脚本和报告。

- `TEST_METHOD.md`：测试方法、精确分类命令、输入哈希、计时及诊断限制。
- `scripts/collect_soak.py`：观察既有后台循环并收集最终状态的板端脚本；UART 上传后 SHA-256 回读匹配。
- `scripts/verify_evidence.py`：主机独立核验程序，实际执行返回 0。
- `HOST_VERIFICATION.json`：19 项核验结果及完整状态摘要。
- `KERNEL_REVIEW.json`：dmesg 保留区间的筛查。
- `KERNEL_JOURNAL_REVIEW.json`：完整 journal 的区间覆盖与筛查。
- `evidence/postboot-soak/`：60 份分类原始输出、采样、服务/模块/DPU/基线哈希证据等。
- `evidence/postboot-soak-kernel/`：完整开机内核 journal、采集记录及摘要。
- `SD_BACKUP_STEPS.md`：整卡备份、离线检查及复验步骤。

UART 传回的两个归档均与板端字节数和 SHA-256 一致：

| 归档 | 字节数 | SHA-256 |
|---|---:|---|
| `postboot-soak.tar.gz` | 49831 | `ed85e8e88773df6a3c14428dc4c7c1aa4cd5bbf7f4b9b7a51bea31601cee6700` |
| `postboot-soak-kernel.tar.gz` | 33559 | `ed980300c2191ce3a03cbf3b729eb94c6abd7ef2a4635af361523972c11ce77c` |

板端同名证据目录和归档位于 `/home/root/kv260-runtime-persistent-backup-20261003/`，均保留。

## 下一步

整卡镜像尚未创建。备用卡实测有 `62333952` 个 512 字节扇区，整盘预期镜像大小为 `31914983424` 字节。Ubuntu 已有 `dd`、`sha256sum`、`fsck.fat`，可用空间约 148 GiB；当前未检测到备用卡读卡器磁盘。

需要正常关闭板卡，将备用 SD 卡接到 Ubuntu 读卡器。识别实际整盘设备并卸载其自动挂载分区后，先制作、回读核验整卡镜像，再对 FAT 分区做只读检查并确定修复。当前板卡继续运行官方 B4096 应用；本轮未执行关机、SD 镜像写入、文件系统修复、应用切换或 QSPI 操作。
