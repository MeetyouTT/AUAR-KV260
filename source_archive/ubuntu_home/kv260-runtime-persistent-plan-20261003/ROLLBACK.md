# 回滚设计（待单独审阅后执行）

持久配置现已安装并通过一次冷启动验收。实际恢复点在备用卡 `/home/root/kv260-runtime-persistent-backup-20261003/`；其中 `original/` 保存原 manager、原 ZOCL、原 unit 和配置、26 项校验清单与原 baseline 归档副本，`backup.sha256` 核验原件。`postboot/` 保存本次启动和推理证据。以下是回滚步骤。

## 写入前的恢复点要求

1. 用 `board_preflight.py` 重新采集板端状态；确认备用卡 CID、内核、修复 manager/ZOCL 指纹、官方 slot 0、26 项原文件哈希及备份均符合记录后再操作。
2. 在板端独立目录保存原 manager、原 systemd unit 与 drop-in 清单、原 ZOCL 文件、26 项基线文件、活动应用、完整 `dmesg`、`/proc/cmdline`、boot ID、关键 systemd 状态及所有 SHA-256。回读验证后再传输主机副本。
3. 修复文件安装到全新版本目录 `/usr/local/lib/kv260-runtime-repair/`；禁止覆盖 `/usr/bin/dfx-mgrd`、`/lib/modules/.../zocl.ko` 或任何原固件。unit 草案必须先经审阅且 hash 固定。
4. 配置只能在新建的 systemd drop-in 中引用新目录的 manager 和 ZOCL loader；安装前保留 drop-in 不存在的证据和文件系统快照。发生任何既有 drop-in 或哈希漂移时停止。

## 正常回滚顺序

1. 使用 UART 控制台登录，不依赖网络或 SSH。读取当前活动应用、systemd 服务、ZOCL srcversion/引用数和 DRM 客户端；不直接重放旧命令。
2. 若 manager 正常，先正常卸载当前活动 overlay/app，确认 DPU 与 ZOCL 没有客户端/holder/refcnt。
3. 停止修复 manager；只移除本方案创建且逐份 SHA-256 与清单完全相符的 drop-in、unit 和独立 loader 文件，然后 `systemctl daemon-reload`。任何不匹配都停止并保存现场。
4. 如果修复 ZOCL 已加载，先确认无 overlay、客户端、holders/refcnt，再正常卸载；禁止 `rmmod -f`。从原备份按已记录的原始路径及哈希恢复原文件。若原始模块未被改动，不覆盖它。
5. 启动原 vendor manager，确认无 drop-in，加载 `kv260-benchmark-b4096` slot 0；检查 DPU 指纹和 1 CU，再用原 ResNet18 XMODEL 和同一图片核对完整 Top-5。
6. 收集完整日志、服务状态、模块参数、原文件哈希和 boot ID。恢复后不要清理独立备份目录。

## 启动失败时

若启动依赖失败，使用 UART 进入救援 shell/维护模式；先采集现场。根据实际 service、module 和活动 overlay 状态分步恢复，不强制卸载，不盲目重启。任何无法确认的状态都先停留在 UART 控制台并保留备份。

**特别门槛：** 如果新探针发现原 ZOCL 在 initramfs 或其他早期机制中先于 `kv260-repaired-zocl.service` 加载，当前 unit 草案不能使用。需先确定不会覆盖原驱动的启动集成方法并重新审阅。
