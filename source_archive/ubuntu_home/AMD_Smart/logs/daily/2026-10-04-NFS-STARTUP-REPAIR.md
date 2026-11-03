# 2026-10-04：KV260 NFS 开机配置修复与运行中复验

用户回复“可以”，授权实施前轮遗留告警方案。本轮先处理确认无用途且不受内核支持的 NFS 服务端启动。读取项目书及平台资料、最新实际记录后，备份原配置/启用链接，通过同一 UART 实施并回读全部证据。

## 实际结果

- 新增 `/etc/systemd/system/proc-fs-nfsd.mount.d/20-kv260-nfs-capability.conf`，以 `ConditionPathExists=/sys/module/nfsd` 对当前 CONFIG_NFSD 未启用的内核跳过挂载。文件 SHA-256 为 `44cdea126e714ef672a297ea457ee3e5b93035b082a426cb4ba1732e83b94ea0`。
- `nfs-server.service`、`nfs-mountd.service` 已 disabled/inactive，原启用链接及配置完整备份；客户端相关配置、状态、PID 保持一致。
- mount 实际 ConditionResult=no、inactive、条件时间戳非零，失败单元输出为空。修复前历史失败日志保留。
- 原始狗图、原始 resnet18 模型分类一次通过，Top5 与基线完全一致；DPU B4096 单 CU / 300 MHz / fingerprint 与基线一致。
- manager PID 999、watch 5、inotify fd 1、原 overlay/render 保持一致。原 26 项文件哈希全部通过；TPM 能力查询 rc=0。
- 主机回读核验 146 个证据文件及清单，完整命令 stdout/stderr 的哈希和返回码、配置、必需观测与两次回滚均通过。UART echo 恢复。

## 失败与恢复

预检的 systemd PATH 问题、首次传输键名错误均未改动配置。v1 的 Conditions 文本显示假设和 v2 的未加载 service reset-failed 返回码导致两次安装检查失败，均自动恢复配置与原始启用链接；v3 通过。主机 Python 3.8 的摘要打印兼容性问题已改正并重新核验。所有原始失败证据保留。

## 当前边界与后续

配置安装后最初尚未进行新的物理断电冷启动，旧 boot ID 为 `01ca88c1-93b6-414f-9646-774482d4b2f0`。此前 manager 冷启动验收先于本轮 NFS 改动。

后续用户确认“已经断电启动”，本次新 boot ID 为 `20353da8-9e81-4b1b-9b15-cac06ac7923f`，首次查询 uptime=101.81 秒。同一 SD CID/内核和新配置哈希保持一致；NFS 条件在开机 13.084129 秒自动判断为 no，完整当前 boot journal 中没有原来不支持 nfsd 的挂载/依赖失败。两个服务端为 disabled/inactive，开机执行时间为 0。

ZOCL 在 13.200171 秒完成，manager 在 14.014065 秒自动执行为 PID 1012。postboot 19 条命令全部通过：失败单元 0、原图分类/DPU/26 项哈希/客户端状态/TPM 能力查询全部通过。主机回读核验 194 个证据文件、446 项检查，全部通过；本轮 NFS 修复的实际原图分类累计两次，未混入前轮 manager 的分类次数。

本次物理断电由用户确认，新启动由 boot ID、配置和日志佐证；本轮未观察关机命令或 Power down，也未从上电起录制 UART。详见 [本次结构化冷启动验收](/home/ghmd/kv260-platform-warnings-20261004/NFS_COLD_BOOT_VERIFICATION.json) 与 [独立回读核验](/home/ghmd/kv260-platform-warnings-20261004/reviews/20261004T105754.205000Z-user-coldboot/review.json)。原运行中报告/状态及其封存证据包保留，本次开机验收另行封存。

TPM 当前能力查询正常；overlay/显示时钟内核平台问题仍待处理。未测试外部 NFS 网络挂载，未更换内核/DT/FPGA/启动固件；前轮封存包保持原样。

完整 [NFS 修复报告](/home/ghmd/kv260-platform-warnings-20261004/NFS_REPAIR_REPORT.md)、[当前结构化状态](/home/ghmd/kv260-platform-warnings-20261004/NFS_REPAIR_STATUS.json) 与 [最新独立回读核验](/home/ghmd/kv260-platform-warnings-20261004/reviews/20261004T105754.205000Z-user-coldboot/review.json) 可追溯实际结果。
