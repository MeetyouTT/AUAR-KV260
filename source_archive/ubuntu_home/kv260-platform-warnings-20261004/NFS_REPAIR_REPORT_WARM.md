# KV260 NFS 开机配置修复报告

日期：2026-10-04。用户回复“可以”，授权实施前轮遗留告警方案中的 NFS 修复与板端复验。本报告记录实际结果；初始只读诊断见 [WARNING_REPAIR_PLAN.md](WARNING_REPAIR_PLAN.md)。

## 结果

**NFS 配置修复与本次运行中的板端复验通过。新增配置的物理断电冷启动尚未验收。** 板卡保持运行，boot ID 仍为 `01ca88c1-93b6-414f-9646-774482d4b2f0`。前轮 manager 修复的冷启动发生在本轮 NFS 改动之前，不能用它证明本轮配置的冷启动通过。

- NFS 服务端 `nfs-server.service`、`nfs-mountd.service` 已停用开机启动，当前 disabled/inactive。
- 不受当前内核支持的 `proc-fs-nfsd.mount` 实际按条件跳过：`ConditionResult=no`、`ActiveState=inactive`，条件判断的单调时间戳非零。
- `systemctl list-units --failed` 输出为空，本次复验时失败单元数为 **0**。修复前的历史失败日志保留。
- DPU query 和原始 resnet18 模型、原始狗图分类各执行一次并通过；Top5 与基线完全一致。
- manager PID 保持 **999**，修复过程未重启它；watch_count=5、inotify_fd_count=1、原官方 overlay 和 renderD128 保持一致。
- 原始 26 项文件的 SHA-256 检查全部通过；NFS 客户端相关配置、服务状态和当前 PID 保持一致。
- TPM 固定属性只读查询再次返回 0。

结构化当前状态见 [NFS_REPAIR_STATUS.json](NFS_REPAIR_STATUS.json)。

## 实际改动

新增板端文件：

```text
/etc/systemd/system/proc-fs-nfsd.mount.d/20-kv260-nfs-capability.conf
```

内容：

```ini
# KV260: the current kernel has CONFIG_NFSD unset; NFS clients remain enabled.
# If NFS server support is introduced, review this guard and restore the server services.
[Unit]
ConditionPathExists=/sys/module/nfsd
```

文件 SHA-256：`44cdea126e714ef672a297ea457ee3e5b93035b082a426cb4ba1732e83b94ea0`。

由 `systemctl disable --now nfs-server.service nfs-mountd.service` 移除两个原始启用链接，原目标与状态均保存于板端 `/home/root/kv260-platform-warnings-20261004/nfs/recovery.json`。随后执行 `daemon-reload`、仅对原来失败的 mount 执行 `reset-failed`，再实际启动该 mount 验证条件跳过。

原厂 mount unit 及其 sysinit wants 链接仍在。当前内核 `CONFIG_NFSD` 未启用，`/sys/module/nfsd` 不存在，条件避免其独立开机入口尝试不支持的挂载。systemd 条件不满足的单元被跳过；这一行为与失败状态不同，依据 [systemd v249 单元条件说明](https://github.com/systemd/systemd/blob/v249/man/systemd.unit.xml)。

当前冻结镜像采用上述能力条件。如果以后启用 NFS 服务端内核或模块，需要重新审查条件与模块加载顺序，并恢复所需 server/mountd 服务。不能将此文件当作未来所有内核通用的 NFS 自动配置。

## 板端复验与主机回读

板端控制器 v3 完成 25 条命令、全部检查通过。原图 Top5：

| 类别索引 | 分数 |
| --- | --- |
| 258 | 0.949879 |
| 270 | 0.00931229 |
| 259 | 0.00821807 |
| 257 | 0.00498451 |
| 279 | 0.00388194 |

DPU：单 CU `DPUCZDX8G_ISA1_B4096`，300 MHz，地址 `0xa0010000`，fingerprint `0x101000056010407`。

客户端快照：rpcbind.service、rpcbind.socket、nfs-statd.service 保持 enabled/active；nfs-idmapd.service 原来不存在，保持原状态。当前无配置的 NFS 导出、无 NFS 挂载，root/boot 在本地 SD 卡。未实施外部 NFS 网络挂载功能测试。

- [实际安装及复验证据](/home/ghmd/kv260-dfx-state-boardtest-20261004/evidence/20261004T103343.431043Z-34-nfs-apply-verify-v3/status.json)。
- [UART 回读状态](/home/ghmd/kv260-dfx-state-boardtest-20261004/evidence/20261004T103447.021573Z-35-fetch-nfs-warm-evidence/status.json)：完整回传并恢复 console echo。
- [独立主机核验](/home/ghmd/kv260-platform-warnings-20261004/reviews/20261004T104303.770846Z-warm/review.json)：146 个文件逐一核对 SHA-256/大小，另有完整导出清单；检查原始命令输出及返回码、配置内容、所有必需观测实际存在、Top5、DPU 参数、原文件校验、两次自动回滚。全部通过。
- 回传原始归档：243301 字节，SHA-256 `94164cf9ec29c1740709da8e48daa572e07afe26ff3529908312ffea5b4b4b12`，见 [NFS_WARM_EXPORT.json](NFS_WARM_EXPORT.json)。

本轮验收只包含上述一次原图分类。前轮的 23 次分类、1000 次并发查询、10 次加载/卸载属于前轮 manager 修复，未重复计入本轮。

## 保留的失败及恢复

所有原始尝试和 stderr 均保留，没有用成功结果覆盖失败记录。

1. 预检使用 PATH 中不存在的 `systemd` 可执行文件，未改板端配置。改用实际存在的 `systemctl --version` 后通过。
2. 首次传输清单误写 `dest`，协议要求 `destination`；接收前停止，改正键名后传输通过。
3. v1 安装检查尝试从 `systemctl show Conditions` 匹配路径，实际 systemd 249 输出 `[unprintable]`。配置已加载但检查不成立，控制器自动恢复新增配置与两个原始链接。v2 改为核对合并 unit、DropInPaths 和实际跳过结果。
4. v2 对三个名字一起执行 `reset-failed`，其中已 disabled/inactive 的 server/mountd 被 systemd 释放为未加载单元，命令返回非零。再次自动回滚完成。v3 只重置原来失败的 mount 后成功。
5. 主机首次核验已完成并保存 passed=true，但打印摘要使用了 Python 3.9 的字典合并运算符，主机 Python 3.8.10 在打印时失败。改用兼容写法并重新核验通过；首轮核验文件保留。

两个板端安装失败目录均包含 `rollback.json`，其配置恢复和保护文件检查通过。回滚不重新触发原来已知不受支持的 nfsd 挂载。

控制器三版与共同验证脚本的 SHA-256 均经回读核对：v3 `9039dbcf5799f5ae3fcaf50cd414da2b7a39a355781c12306088cf3019f00487`；共同验证脚本 `276c81dfba6c282afaa1f911ae30ba4ff72c112504ead4c1643e53ba34629ddf`。

## 回滚方法

回滚依据为板端 `recovery.json` 和其 backup 目录，主机也已完整回读。控制器内的 `rollback()` 已在两次失败尝试中实际执行并验收。需要主动恢复时，应先核对新配置仍为上述内容和 SHA-256，再仅移除本次新增文件，按备份元数据恢复以下两个链接，并执行 `systemctl daemon-reload` 与 `sync`：

```text
/etc/systemd/system/multi-user.target.wants/nfs-server.service -> /lib/systemd/system/nfs-server.service
/etc/systemd/system/multi-user.target.wants/nfs-mountd.service -> /lib/systemd/system/nfs-mountd.service
```

不要覆盖外部改动或删除原厂 unit。恢复原开机配置会恢复原有的配置不一致，因此下次启动可能再次出现 nfsd 挂载失败。当前保持修复后的配置，未执行额外主动回滚。

## 冷启动验收与剩余事项

已向用户询问是否方便现场配合；收到实际答复前保持板卡运行。待配合时先正常卸载当前应用、停止 manager、sync 和系统关机，看到 UART `Power down` 后再断开板卡直流电源并重新上电。使用只读启动观察记录，确认新 boot ID，然后重新核对 NFS 条件跳过、服务启用状态、零 failed 单元、原图推理、客户端和原文件哈希。

TPM 256 提示已由内核初始化恢复，能力查询正常。overlay 属性生命周期与显示时钟权限问题尚未修复；IRQ 枚举和可选 section 日志的处理仍需对应驱动/设计验收。板端日期仍为 2021，记录采用主机 UTC 和板端单调时间，不将旧板端时间作为当前日期。

本轮未更换内核、DT、bitstream、xclbin 或启动固件。前轮已经封存的 source/native/board 修复包保持原样；本轮证据独立归档。
