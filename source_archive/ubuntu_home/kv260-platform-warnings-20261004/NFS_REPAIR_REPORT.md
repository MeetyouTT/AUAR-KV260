# KV260 NFS 开机配置修复报告

日期：2026-10-04。用户回复“可以”，授权实施前轮遗留告警方案中的 NFS 修复与板端复验。本报告记录实际结果；初始只读诊断见 [WARNING_REPAIR_PLAN.md](WARNING_REPAIR_PLAN.md)。

## 结果

**NFS 配置修复、运行中复验与本轮用户确认断电后的开机复验均通过。** 用户随后回复“已经断电启动”；实际新 boot ID 为 `20353da8-9e81-4b1b-9b15-cac06ac7923f`，manager 自动启动为 PID **1012**。本轮复验使用此次新启动的日志和实际推理结果。

修复后、断电之前的运行中复验结果如下；其原始报告另存 [NFS_REPAIR_REPORT_WARM.md](NFS_REPAIR_REPORT_WARM.md)。

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

## 本轮断电启动验收

用户确认“已经断电启动”后，先读取板卡身份与服务状态，再执行控制器原有的 postboot 复验，没有在新启动后手动启动 manager、加载官方应用、重置 failed 状态或再次尝试 nfsd 挂载。

- boot ID 从 `01ca88c1-93b6-414f-9646-774482d4b2f0` 变为 `20353da8-9e81-4b1b-9b15-cac06ac7923f`；首次查询 uptime=101.81 秒。
- SD CID 仍为 `0353445345333247805558c00401a100`，内核仍为 `5.15.36-xilinx-v2022.2`；新增配置的内容和 SHA-256 完整保留。
- NFS 条件在开机约 **13.084129 秒**求值为 no，mount 为 inactive/success。当前开机 NFS journal 只有“Condition check resulted in NFSD configuration filesystem being skipped.”；内核和本次完整 boot journal 没有原来的不支持 nfsd 挂载/相关依赖失败。
- server/mountd 为 disabled/inactive，两个服务本次启动的 ExecMainStartTimestampMonotonic 均为 0。
- ZOCL loader 在 **13.200171 秒**完成，manager 在 **14.014065 秒**开始执行，PID **1012**，enabled/active/running。自动启动顺序和保护文件检查通过。
- postboot 共执行 **19 条命令**，全部检查通过：失败单元 **0**，原始模型与原始狗图 Top5 完全一致，DPU 参数一致，26 项原文件哈希全部通过，客户端原启用/运行状态保留，TPM 能力查询 rc=0。watch_count=5、inotify_fd_count=1、原 overlay/render 保持一致。
- 新启动复验的完整证据归档为 290528 字节，SHA-256 `bf8d2f006f491a339275e1ce349df521d011e011e2690a42730e8c1c2dfd1ccf`。主机逐一回读核验 **194 个证据文件、446 项检查**，全部通过；两个早期安装失败及回滚仍保留。

证据：[新启动预检](/home/ghmd/kv260-dfx-state-boardtest-20261004/evidence/20261004T105130.940101Z-36-nfs-post-restart-preflight/status.json)、[实际 postboot 验收](/home/ghmd/kv260-dfx-state-boardtest-20261004/evidence/20261004T105257.612504Z-37-nfs-post-restart-verify-export/status.json)、[新启动证据回读](/home/ghmd/kv260-dfx-state-boardtest-20261004/evidence/20261004T105536.924534Z-38-fetch-nfs-postboot-evidence/status.json)、[独立冷启动核验](/home/ghmd/kv260-platform-warnings-20261004/reviews/20261004T105754.205000Z-user-coldboot/review.json)、[结构化验收](NFS_COLD_BOOT_VERIFICATION.json)。本轮实际新增一次原图分类；连同配置安装后的运行中复验，本轮 NFS 修复共两次。

验收依据为**用户确认物理断电、新 boot ID、持久化配置、开机单调时间及当前启动日志**。用户在本轮开始前已完成断电上电；没有观察此次关机命令、Power down 标记，也没有从上电起录制 UART。本报告不将前轮被动 UART 冷启动记录混入此次证据。

## 剩余事项

TPM 256 提示已由内核初始化恢复，能力查询正常。overlay 属性生命周期与显示时钟权限问题尚未修复；IRQ 枚举和可选 section 日志的处理仍需对应驱动/设计验收。板端日期仍为 2021，记录采用主机 UTC 和板端单调时间，不将旧板端时间作为当前日期。

本轮未更换内核、DT、bitstream、xclbin 或启动固件。前轮已经封存的 source/native/board 修复包及 NFS warm 证据包保持原样；本次开机证据另行封存，归档信息见 [NFS_RELEASE.json](NFS_RELEASE.json)。
