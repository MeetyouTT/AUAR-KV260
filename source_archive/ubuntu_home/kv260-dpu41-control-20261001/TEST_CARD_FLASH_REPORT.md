# KV260 独立测试卡烧录记录

烧录状态：**官方镜像烧录完成，两项完整读回校验通过，烧录结束时备用卡已安全弹出。** 完成时间：2026-10-01 22:40 PDT。后续用户已换卡开机，启动、官方 DPU 和模型核验见 [TEST_CARD_BASELINE_REPORT.md](TEST_CARD_BASELINE_REPORT.md)；分类与六轮性能复测也已完成，见 [BASELINE_INFERENCE_REPORT.md](BASELINE_INFERENCE_REPORT.md)。

本次将现有官方 PetaLinux 2022.2 / Vitis AI 3.0 镜像写入用户提供的备用 SD 卡，供后续在测试卡上先复测原固件。未将本次新 DPU 4.1 产物替换为默认启动固件，未操作板卡或 QSPI。

| 项目 | 实测记录 |
|---|---|
| 镜像 | `/home/ghmd/下载/xilinx-kv260-dpu-v2022.2-v3.0.0.img` |
| 镜像字节数 | 9,482,799,104 |
| 镜像 SHA-256 | `b5de568c8f008dd251cdc3c7fcc0b3942e973e752943152628519768f845aa9c` |
| 目标卡 | `/dev/sda`，USB 可移除设备，型号 `Storage_Device`；写入前只有一个 FAT32 分区 |
| 卡容量 | 31,914,983,424 bytes，约 29.7 GiB |
| 镜像分区 | MBR；启动 FAT32 从 sector 8 开始、154,590 sectors；Linux 根分区从 sector 154,600 开始、18,366,492 sectors |
| 写入 | `dd bs=4M conv=fsync`；成功写入全部镜像字节，745.291 秒，平均 12.7 MB/s |
| 常规读回 | `cmp -n 9482799104` 全部镜像字节一致，22:39:47 PDT 通过；烧录脚本返回 0 |
| 直接读回 | `dd iflag=direct,count_bytes` 对镜像完整范围读取，SHA-256 与源镜像完全一致，22:37:00 PDT 通过；校验脚本返回 0。读取 897.667 秒，平均 10.6 MB/s |
| 最终分区 | 75.5 MiB FAT32 启动分区、8.8 GiB ext4 根分区，均正常识别且未挂载 |
| 安全弹出 | `udisksctl power-off --block-device /dev/sda` 返回 0；随后确认 `/sys/class/block/sda` 已不存在。临时只读是主机内核标志，重新连接后不保留 |

入口为 [flash_test_card.sh](flash_test_card.sh) 和 [verify_test_card.sh](verify_test_card.sh)。写入前对 USB/可移除属性、设备序列标识、卡容量和镜像哈希进行检查，卸载分区后才写入。管理员环境未提供 `rg`，第一次校验等待脚本在尚未开始读回前停止并改用 `/usr/bin/grep`；写卡未受影响，失败记录保留。

原始日志：[test_card_flash.log](logs/test_card_flash.log)、[test_card_direct_readback.log](logs/test_card_direct_readback.log)；源镜像校验记录：[test_card_source_image.sha256](evidence/test_card_source_image.sha256)、直接读回范围和哈希：[test_card_direct_readback.sha256](evidence/test_card_direct_readback.sha256)、汇总：[test_card_flash.json](evidence/test_card_flash.json)。

后续按 [TEST_CARD_PLAN.md](TEST_CARD_PLAN.md) 执行：先在测试卡复测原 app，再依据 [DEPLOYMENT_REVIEW.md](DEPLOYMENT_REVIEW.md) 的待确认项验证候选 app。镜像写入及读回校验不等于板卡启动或 DPU 推理验收，也没有验证 SD 卡超出镜像范围的全部容量。
