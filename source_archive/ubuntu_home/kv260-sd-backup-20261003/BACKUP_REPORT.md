# KV260 备用 SD 卡整卡备份与离线修复结果

## 已完成

备用卡整卡镜像已创建并独立回读校验通过；随后在保留该修复前恢复点的条件下，完成 FAT 脏标志修复和 `/etc/fstab` 重复 `/boot` 条目清理。实际卡的 FAT/root 最终只读检查返回 0，原 26 项文件在 fstab 修改前后均为 26/26 匹配。

最终主机核验 12 项全部通过，随后 `udisksctl power-off -b /dev/sda --no-user-interaction` 返回 0，读卡器已安全弹出，可以取卡。弹出记录保存为 `EJECT_RESULT.json`。

修复后的板卡开机和推理还未验收，需要用户把卡插回断电的 KV260 并重新启动。本报告不把离线检查等同板端验证，也不表示原 nfsd/overlay/IRQ 提示已全部解决。

## 整卡备份

| 项目 | 实测结果 |
|---|---|
| 设备 | USB 读卡器整盘 `/dev/sda`，by-id 为 `usb-Mass_Storage_Device_121220160204-0:0` |
| 容量 | `31914983424` 字节，`62333952` 个 512 字节扇区 |
| 镜像 | `kv260-spare-runtime-fixed-20261003.img` |
| 镜像字节数 | `31914983424`，与源盘相同 |
| 源盘完整读取 SHA-256 | `518942a62c0d0ed32b2a90b4736b821b3e24006157ab420d02d5b54d0470546b` |
| 镜像独立完整回读 SHA-256 | `518942a62c0d0ed32b2a90b4736b821b3e24006157ab420d02d5b54d0470546b` |
| 复制及回读总时长 | `1748.14 s`，约 29 分 8 秒 |
| 镜像权限 | `0600`；备份目录 `0700` |
| 源设备读取权限 | Ubuntu 标准认证后的 UDisks2 OpenForBackup，只读 FD 确认通过 |

本轮开始时，卡已插入读卡器并被自动挂载，板卡串口已离线；本轮未执行板端关机。接入时原 FAT 告警仍存在，ext4 自动日志恢复完成。之后正常卸载两分区再制作镜像。因此镜像是该接入和恢复后的离线状态，保留了已持久启用的修复运行时及原基线，不能宣称是取卡前运行态逐扇区快照。

读卡器不能直接提供 SD CID，设备识别依据容量、MBR 签名 `40bd38f0`、卡内修复二进制与配置，以及镜像中完整复测证据包。两份卡内归档经 debugfs 从镜像分区副本提取，SHA-256 与先前 UART 接收的证据包完全一致：

- `postboot-soak.tar.gz`：`ed85e8e88773df6a3c14428dc4c7c1aa4cd5bbf7f4b9b7a51bea31601cee6700`
- `postboot-soak-kernel.tar.gz`：`ed980300c2191ce3a03cbf3b729eb94c6abd7ef2a4635af361523972c11ce77c`

这些证据包中记录的备用卡 CID 为 `0353445345333247805558c00401a100`。

## 诊断与实际修复

1. 从已验证镜像提取分区副本，保留原件。root 副本 `e2fsck -f -n` 返回 0。boot 副本 `fsck.fat -n -v` 返回 1，仅检出脏标志。实际文件系统为 FAT16，既有 MBR 分区类型为 `0x0c`，分区表保持原样。
2. 在 FAT 副本上运行标准 `fsck.fat -a -v`，随后只读复查返回 0。比较确认只有相对偏移 37 的字节由 1 变为 0；无文件数据或 FAT 链重分配。
3. 对已核对且未挂载的实际备用卡 `/dev/sda1` 运行标准 fsck 修复。修复命令返回 1，实际进行了修复；随后 `fsck.fat -n -v` 返回 0。整个分区回读 SHA-256 为 `33a10404abf33d181160dfb58b5b8905611eb64ef6f78abd2b52e7019a40f2db`，与已审阅的一字节修复副本完全相同。
4. 把 root 分区挂载到专用目录，保存原 `/etc/fstab` 为卡上 `/etc/fstab.kv260-pre-dedup-20261003`，仅删除重复 `/dev/mmcblk1p1 /boot vfat defaults 0 0` 那一行。保留原 `LABEL=boot /boot vfat defaults 0 2` 的所有选项和 pass 字段，以及其他行。原件也保存在主机 `offline-inspection/fstab.original`。
5. 回读新 fstab，SHA-256 为 `580d18ee47a5dbe98b86ccec7670518c00fe8bc7b58990e186a00d9f559329f0`，与已审阅配置匹配。原 26 项运行时/固件/模型/图片/程序文件在修改前后均匹配。正常卸载 root 分区，再对实际 root 分区运行 `e2fsck -f -n`，返回 0。

修复通过标准 Ubuntu 管理员认证执行，使用已安装的 fsck/mount 工具；没有安装或升级软件。源卡修改是文件系统标志、fstab 及其原件备份，附带正常 mount/umount 的 ext4 日志元数据变化。本轮没有构建硬件、替换 DPU 固件、改模型、写 QSPI 或连接执行器。

## 保留的失败与限制

直接 `sudo -n` 和 UDisks 非交互备份请求均需要系统认证；随后通过标准认证窗口得到只读备份权限。完整记录在方法和来源文件中，密码没有收集到日志。

首次副本检查脚本错误地要求修复命令返回 0，因此在修复返回 1 时断言中止。实际只影响本地副本检查，没有写原卡。核对工具说明和完整输出后，对该副本执行独立只读复查并核对准确字节差异，确认通过，再形成正式修复方案。失败记录、修复 rc=1 和复查 rc=0 均保留。

镜像作为修复前恢复点保持原样，因此恢复该镜像会恢复修复前的 FAT 标志和两条 boot 挂载记录。需要再次修复时，应在重新识别目标设备后按已审阅方案执行；不能把该文件名中的 runtime-fixed 理解成已经包含本轮文件系统修复。

## 文件与原始证据

- `IMAGE_VERIFICATION.json`、`IMAGE_SHA256SUMS`：整卡长度及源/文件独立摘要。
- `PRE_BACKUP_CARD_IDENTIFICATION.json`、`PARTITION_LAYOUT.json`、`HOST_CARD_ATTACH_KERNEL.log`：来源、布局及接入恢复日志。
- `progress.jsonl`：权限请求、复制进度及回读完成记录。
- `offline-inspection/`：原分区副本、只读检查、FAT 修复副本、原 fstab 和卡内复测证据包。
- `FILESYSTEM_REPAIR_REVIEW.md`、`FILESYSTEM_REPAIR_PLAN.json`、`fstab.reviewed`、`fstab.diff`：事前审阅和精确修改范围。
- `FILESYSTEM_FIX_RESULT.json`、`card-*.stdout/stderr/rc`、`stock-check-before-fstab.json`、`stock-check-after-fstab.json`：实际执行及验证。
- `scripts/`：实际使用的备份、离线检查和受限修复脚本。
- `RECOVERY_STEPS.md`：整卡恢复方法。

## 回板复验

安全弹出读卡器后，将备用 SD 插回断电板卡，接好 USB 串口及供电。启动后采集 boot 日志，确认无本轮 FAT 脏标志及重复 boot 挂载错误，核对 `/boot` 挂载源。

检查修复 ZOCL srcversion `9BDC942A6014BCCBD1DCB78`、manager/loader service、官方 B4096 slot 0；执行 `xdputil query` 核对 1 CU、300 MHz、`0xa0010000` 和 fingerprint `0x101000056010407`，再以原模型、原图片和原分类程序核对完整 Top-5。新一轮启动证据使用新的目录保存。

后续自研运动/PWM IP 工作应在独立工程和测试应用中推进，保留当前官方 DPU 对照与本次恢复镜像。
