# 备用 SD 卡整卡备份方法与边界

本轮开始时，SD 已插入 Ubuntu 读卡器，板卡串口不在线；本轮未执行板端 `systemctl poweroff`。Ubuntu 已自动挂载 `sda1` 和 `sda2`。接入日志有原 FAT 未正常卸载提示，ext4 报 `recovery complete`。因此镜像对应的是接入、日志恢复并正常卸载后的卡状态，不应宣称是取卡前运行态的逐扇区快照。

## 来源核对

- 新出现的 USB 读卡器整盘 `/dev/sda`，通过 `/dev/disk/by-id/usb-Mass_Storage_Device_121220160204-0:0` 引用。
- 磁盘大小 `31914983424` 字节、`62333952` 个 512 字节扇区，与板端备用卡记录一致。
- MBR disk signature `40bd38f0`；两个分区为 75.5 MiB vfat 启动分区和 ext4 root 分区。分区表类型为 `0x0c`，实际 fsck 识别为 FAT16；本轮保留该既有分区表。
- 卡内修复 manager SHA-256 `db9c25f09f1178177884b1114c57f32c076f1e7f9cdd0d12b7a896039038a46c`。
- 卡内修复 ZOCL SHA-256 `5cef5e0eba083419b3ece6fd4829a9f3112e3f0daaee513e1617d60ed1f7f412`。
- PetaLinux 2022.2、持久化 manager drop-in 与此前备用卡记录对应。

读卡器 serial 是读卡器自身信息，不作为 SD CID。完整来源记录在 `PRE_BACKUP_CARD_IDENTIFICATION.json`；接入日志在 `HOST_CARD_ATTACH_KERNEL.log`。

## 权限与执行

`sudo -n true` 提示需要密码；UDisks 非交互只读备份请求返回 `NotAuthorizedCanObtain`。随后通过 Ubuntu 标准认证窗口获得 `UDisks2.Block.OpenForBackup` 的只读句柄。没有收集登录密码，也没有调整设备权限或绕过系统认证。

`udisksctl unmount -b /dev/sda2 --no-user-interaction` 和 `udisksctl unmount -b /dev/sda1 --no-user-interaction` 均成功。备份脚本在打开设备前、认证后、复制后检查相关设备没有挂载。

实际命令为：

```sh
python3 /home/ghmd/kv260-sd-backup-20261003/scripts/create_verified_image.py
```

脚本确认设备 by-id、容量、UDisks Drive、非系统盘属性、只读 FD、FD 的实际设备号、MBR 签名及可用磁盘空间，之后复制整盘。先写独立 `.img.partial` 文件，权限 `0600`；源流读取时计算 SHA-256。写入 fsync 完成后，独立回读镜像文件并计算 SHA-256，长度与摘要完全匹配后才重命名为 `.img` 并写 `IMAGE_VERIFICATION.json`。

源 SHA-256 是完整复制读取过程中计算；本轮不额外重复读取源盘。镜像 SHA-256 来自已写入文件的独立完整回读，两者相同才视为复制校验通过。不能把 `.partial` 当作完成的备份。

## 当前产物

预期最终镜像：`kv260-spare-runtime-fixed-20261003.img`。实时状态在 `progress.jsonl`；正式完成状态以 `IMAGE_VERIFICATION.json` 的 `verified` 和 `IMAGE_SHA256SUMS` 为准。

备份后可从已验证镜像提取 FAT 和 root 分区副本，只在副本上做只读检查。对原卡的文件系统或 fstab 修改必须另行记录修改范围、原件备份、写入方式和复验结果。

镜像包含这张备用卡的完整系统、修复运行时及其运行证据，是当前修复版的恢复点。整卡镜像含系统配置及访问凭据，所以镜像设置为仅当前用户可读写，整个备份目录权限为 `0700`。
