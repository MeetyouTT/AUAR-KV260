# KV260 文件系统修复后的冷启动验收

## 结果

备用卡重新插回 KV260 后，已完成新一次冷启动、持久化运行时检查及原模型/原图片分类。板端 15 项检查通过；证据传回 Ubuntu 后，独立核验 27 项全部通过，53 个板端清单文件全部匹配。

本轮收尾完成的是官方 B4096 运行环境的修复与复验：持久化运行时可自动启动，FAT 脏标志和重复 `/boot` 条目已离线修复，新启动日志未再检出这两个问题，原推理结果保持一致。自研 AXI-Lite/PWM、与 DPU 共存的硬件设计及比赛整机功能仍属于后续工作。

## 身份与启动依据

| 项目 | 本轮证据 |
|---|---|
| 主机收集日期 | 2026-10-03；准确 UTC 时间见 `HOST_VERIFICATION.json` |
| 新 boot ID | `a7733edd-db41-4527-b8fb-cefdcbfe7b3a` |
| 上次 boot ID | `0251d729-0d3c-44e8-abb9-27121306c081` |
| 同一备用 SD CID | `0353445345333247805558c00401a100` |
| 系统 | PetaLinux `2022.2_release_S10071807` |
| 内核 | `5.15.36-xilinx-v2022.2` |
| root | `/dev/mmcblk1p2`，ext4 |
| boot | `/dev/mmcblk1p1`，vfat |
| 原始启动 journal 覆盖 | 单调时钟 `0.000000–517.576465 s`，覆盖启动、检查与本次分类 |

板端墙上时间尚未同步，仍显示 2021-11-19。本报告使用主机日期、boot ID 与单调时钟追溯，不能将板端旧日期当作本轮实际日期。

## 修复结果与运行时

- 当前 `/etc/fstab` SHA-256 为 `580d18ee47a5dbe98b86ccec7670518c00fe8bc7b58990e186a00d9f559329f0`，与事前审阅和离线修复结果一致。
- 原件 `/etc/fstab.kv260-pre-dedup-20261003` SHA-256 为 `b1978c1e094cd260b761afbaab75f0d9e659a78044d1d4fd86807bc44ef158bd`。Ubuntu 逐字节核对确认，只删除重复的 `/dev/mmcblk1p1 /boot vfat defaults 0 0` 行；保留原 `LABEL=boot        /boot   vfat    defaults    0   2` 及其他内容。
- 本次完整启动 journal 未检出 FAT 脏标志/未正常卸载/损坏错误，以及重复 boot 挂载错误。离线 FAT 检查及一字节修复证据仍保存在整卡备份目录；本次没有对已挂载 boot 重新运行 fsck。
- 修复 ZOCL srcversion 为 `9BDC942A6014BCCBD1DCB78`，`enable_xgq_ert=1`，采集时 refcnt 为 0。
- `kv260-repaired-zocl.service` 为 active/exited、Result=success、ExecMainStatus=0；在启动 `13.176530 s` 完成，早于 manager 在 `13.757041 s` 开始启动。
- `dfx-mgr.service` 为 active/running、Result=success、ExecMainStatus=0，PID 1012，实际程序为 `/usr/local/lib/kv260-runtime-repair/dfx-mgrd`，drop-in 为 `/etc/systemd/system/dfx-mgr.service.d/10-kv260-repaired.conf`。
- 官方 `kv260-benchmark-b4096` 在 slot 0，其他候选目录均未激活。
- 原 26 项文件 SHA-256 清单全部匹配，包括原厂运行库、原 ZOCL/manager 文件、官方固件、模型、图片、分类程序、恢复副本及已有 M3 固件。两个修复候选二进制的 SHA-256 也与已审阅版本一致。

| 修复候选 | SHA-256 |
|---|---|
| `dfx-mgrd` | `db9c25f09f1178177884b1114c57f32c076f1e7f9cdd0d12b7a896039038a46c` |
| `zocl.ko` | `5cef5e0eba083419b3ece6fd4829a9f3112e3f0daaee513e1617d60ed1f7f412` |

## 推理复验

`xdputil query` 返回 0，实测为 1 个 `DPUCZDX8G_ISA1_B4096` CU、300 MHz、地址 `0xa0010000`、fingerprint `0x101000056010407`。DPU IP Spec、VAI Version 与此前官方应用实测 query 完全一致；kernel 字段逐项匹配时只排除了进程相关的 `cu_handle`。

本轮执行的分类命令如下，返回 0；三个输入路径及其原文件清单均保持一致：

```sh
/home/root/Vitis-AI/examples/vai_library/samples/classification/test_jpeg_classification \
  /usr/share/vitis_ai_library/models/resnet18/resnet18.xmodel \
  /home/root/kv260-test-20261001/pytorch-resnet-dog.jpg
```

| 排名 | 索引 | 结果 | 分数 |
|---|---:|---|---:|
| 1 | 258 | Samoyed | 0.949879 |
| 2 | 270 | white wolf | 0.00931229 |
| 3 | 259 | Pomeranian | 0.00821807 |
| 4 | 257 | Great Pyrenees | 0.00498451 |
| 5 | 279 | Arctic fox | 0.00388194 |

完整 Top-5 与此前基线一致。原始分类结果位于 stderr，主机核验同时读取 stdout/stderr，保留实际返回码。本轮是修复后单次功能复验；没有新增 FPS、持续满负载、断电可靠性、PWM 或执行器验收。此前 60 次、约 30 分钟的采样复测证据仍是独立记录，不能改写成本次冷启动的测试。

## 保留的问题与待确认项

| 本次日志中的项目 | 实际结果及处理 |
|---|---|
| `proc-fs-nfsd.mount` 失败及 NFS 依赖失败 | `systemctl --failed` 实际列出 1 个失败单元：`proc-fs-nfsd.mount`。此前证据也存在相关提示；本轮未恢复 NFS 服务 |
| overlay property memory leak warnings | 本次 16 行，旧基线也存在。未修改 overlay 或移除规则来消除提示 |
| `IRQ index 8 not found` | 本次 1 行，旧基线也存在；本轮推理通过，但未解释该 IRQ 提示原因 |
| `ERT_EXEC_WRITE is obsoleted` | 本次 1 行，旧基线也存在；没有把兼容提示视为已修复 |
| XCLBIN 可选 section skip `-22` | 本次 `AIE_RESOURCES` 2 行，`DEBUG_IP_LAYOUT`/`AIE_METADATA` 合计 2 行，旧基线也存在；实际 query 和分类返回 0 |
| 时钟 divider/PLL 操作 `ret=-13` | 本次 2 行，旧基线含同类提示；未修改时钟配置 |
| TPM self-test error 256 | 当前启动有 1 行；所比较的旧基线未检出同一模式。原因和是否偶发仍待专项诊断，本轮不能归类为已解决或已证明无害 |
| fuse 模块、音频配置和桌面图标错误 | 当前原始日志有记录；本轮未专项诊断，不能单凭与旧 kernel 基线的比较判断是否新增 |
| 板端时间未同步 | 保留实际旧墙上时间，测试追溯采用单调时钟和主机 UTC |

完整警告原文和筛查候选位于 `KERNEL_REVIEW.json`，原始启动、服务及内核日志均保留。功能验收通过不等于系统全无告警；关键词筛查也不能排除所有潜在缺陷。

## 备份和恢复点

已独立回读验证的整卡镜像仍保存在：

`/home/ghmd/kv260-sd-backup-20261003/kv260-spare-runtime-fixed-20261003.img`

- 字节数：`31914983424`，即 `62333952` 个 512 字节扇区。
- SHA-256：`518942a62c0d0ed32b2a90b4736b821b3e24006157ab420d02d5b54d0470546b`。
- 镜像是本轮 FAT/fstab 修复之前的恢复点，包含已修复并持久化的运行时。恢复它会恢复当时的 FAT 标志和重复 fstab 条目。本轮没有创建第二份修复后整卡镜像，也没有覆写原镜像。
- 离线备份报告中 `board_reboot_verified=false` 是当时尚未插卡启动的历史记录；保持其文件及原清单不变。本报告和新 boot ID 补齐后续启动验收证据。
- 需要恢复时，使用既有 `RECOVERY_STEPS.md`，先核对目标卡身份、容量和覆盖授权，再执行镜像校验、写入和目标回读。旧文件内“正在制作镜像”的语句属于事前步骤状态；实际备份完成状态以 `IMAGE_VERIFICATION.json` 与 `BACKUP_REPORT.md` 为准。

此前记录：

- [持久化运行时结果](/home/ghmd/kv260-runtime-persistent-plan-20261003/PERSISTENT_ENABLEMENT_REPORT.md)
- [约 30 分钟采样复测](/home/ghmd/kv260-postboot-soak-20261003/POSTBOOT_SOAK_REPORT.md)
- [整卡备份与离线修复](/home/ghmd/kv260-sd-backup-20261003/BACKUP_REPORT.md)
- [恢复步骤](/home/ghmd/kv260-sd-backup-20261003/RECOVERY_STEPS.md)

## 本轮新增文件与验证方法

本轮只新增 `/home/ghmd/kv260-fs-repair-reboot-20261003/` 中的采集程序、证据、报告和清单；固定官方源码、原构建产物及此前封存记录保持原样。本轮未写 QSPI、未部署新硬件固件、未切换活动应用，也未连接执行器。

- `scripts/collect_post_repair.py`：实际执行的板端采集程序，上传后 SHA-256 匹配。
- `scripts/verify_evidence.py`：Ubuntu 独立核验程序，实际运行返回 0，27 项全部通过。
- `HOST_VERIFICATION.json`：核验结果、UTC 时间、启动身份、输入结果、归档哈希及日志覆盖范围。
- `KERNEL_REVIEW.json`：日志原文候选及旧基线对照。
- `evidence/kv260-fs-repair-reboot-20261003/`：53 个已封存板端文件与 `evidence.sha256`，包括 15 条采集命令的 argv、stdout、stderr、returncode。
- `kv260-fs-repair-reboot-20261003.tar.gz`：实际从板端 UART 分块传回的原归档，`59779` 字节，SHA-256 `440cc0a8b74abebb29268b035c2e463733e10b8bd07a47d0fe3b95ae1d1d494e`。
- `SERIAL_CLOSE.json`：串口交互恢复 echo 后正常退出 picocom 的结果。
- `HOST_SHA256SUMS`：本目录最终清单，生成后逐项回读校验。

板端目录 `/home/root/kv260-fs-repair-reboot-20261003/` 和同名 `.tar.gz` 保留。串口退出后板卡继续运行官方 B4096 应用。当前这一步验收已结束，可在保留该可恢复对照环境的基础上另建自研 IP 工程。
