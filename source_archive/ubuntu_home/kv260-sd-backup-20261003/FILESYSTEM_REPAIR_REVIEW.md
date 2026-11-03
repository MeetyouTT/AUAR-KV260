# 备用卡文件系统修复审阅

## 恢复点与诊断

整卡镜像 `kv260-spare-runtime-fixed-20261003.img` 已验证，大小 `31914983424` 字节，源流与文件独立回读 SHA-256 均为 `518942a62c0d0ed32b2a90b4736b821b3e24006157ab420d02d5b54d0470546b`。镜像保留为修复前恢复点。

从已验证镜像提取的 root 分区执行 `e2fsck -f -n` 返回 0。boot 分区执行 `fsck.fat -n -v` 返回 1，唯一检出问题为脏标志；它实际为 FAT16，分区表既有类型为 `0x0c`，不调整分区表。

在副本上执行 `fsck.fat -a -v` 返回 1，实际进行了修复；随后 `fsck.fat -n -v` 返回 0。逐扇区比较确认唯一差异为启动分区相对偏移 37 的字节从 1 改为 0。两份原始日志及首次检查脚本错误断言的记录均保留，未把返回码 1 改写成 0。

## 精确修改范围

1. 对未挂载的 `/dev/sda1` 运行标准 `fsck.fat -a -v`，修复已确认的脏标志。修复前后整个分区 SHA-256 分别必须为：
   - 原件：`27e40502c706762014ae172bef80f0c516d34bcf6d3180c880b02f268d3dc623`
   - 修复：`33a10404abf33d181160dfb58b5b8905611eb64ef6f78abd2b52e7019a40f2db`
2. 仅删除 root 分区 `/etc/fstab` 中重复的 `/dev/mmcblk1p1 /boot vfat defaults 0 0` 记录。保留已有 `LABEL=boot /boot vfat defaults 0 2` 的全部选项及 pass 字段；其他行保持原文。
   - 原 fstab：`b1978c1e094cd260b761afbaab75f0d9e659a78044d1d4fd86807bc44ef158bd`
   - 修复 fstab：`580d18ee47a5dbe98b86ccec7670518c00fe8bc7b58990e186a00d9f559329f0`

精确差异保存为 `fstab.diff`，计划和字节差异保存为 `FILESYSTEM_REPAIR_PLAN.json`。

## 实施与检查

`scripts/apply_filesystem_fix.py` 由标准 Ubuntu 管理员认证后执行。先核对整卡恢复点、已通过的 root/证据包检查、设备 by-id、容量、MBR 签名、源分区无挂载和原 FAT 摘要；使用标准 fsck 工具修复后回读核对预定分区摘要与只读检查。

之后把 root 分区挂载到专用目录 `rootfs-mount`，核对实际挂载设备和原 fstab 摘要，校验原 26 项基线。原 fstab 另存到卡上 `/etc/fstab.kv260-pre-dedup-20261003`，新配置原子替换并保留 owner/group/mode。复核 fstab 摘要和原 26 项基线，正常卸载，最后对 root 分区做只读检查。

执行结果、命令返回码和完整 stdout/stderr保存为 `FILESYSTEM_FIX_RESULT.json` 等文件。实际成功与否以执行后的记录为准。

## 恢复与后续

如需只恢复 fstab，可从卡上原件恢复，或使用主机 `offline-inspection/fstab.original`。若要恢复修复前的整张备用卡，使用已验证整卡镜像，重新确认目标设备并回读校验。修复前镜像包含修复前 FAT 脏标志与两条 boot 挂载记录。

离线文件系统检查和文件回读不等同板卡开机验收。修复后仍需把卡安全弹出、插回断电板卡，启动后重新检查 boot 挂载、修复运行时、官方应用、DPU query 和原模型原图片分类。此时才能判断启动日志中的 FAT/重复挂载问题是否消失。原 `nfsd` 及其他运行时提示不在这两项修复范围内。
