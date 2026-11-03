# KV260 遗留告警：实际诊断与修复顺序

日期：2026-10-04。承接用户“这些问题要怎么解决”。本轮完成只读诊断与修复方案，没有更改板端服务、内核、设备树、TPM 状态或启动固件。

后续实施状态：用户随后回复“可以”，NFS 开机配置已修复并完成运行中复验；再由用户确认“已经断电启动”，新增配置的开机验收也通过。新 boot ID 已确认，开机按条件跳过 nfsd，失败单元为 0，原图推理与原文件校验通过；本次没有关机/上电起的 UART 观察。见 [最新实际修复报告](NFS_REPAIR_REPORT.md)、[当前状态](NFS_REPAIR_STATUS.json) 和 [验收依据](NFS_COLD_BOOT_VERIFICATION.json)。下文保留最初只读诊断时的记录。

## 结论

首先处理不需要的 NFS 服务端开机配置。TPM 的启动 256 返回码已由内核后续初始化恢复，当前只读能力查询返回 0，不能继续将它笼统称为持续 TPM 故障。overlay 需要在最终平台的设备树和内核属性生命周期中处理；显示时钟需要核对实际 DisplayPort 链路与固件资源权限。

当前仍为同一新 boot ID `01ca88c1-93b6-414f-9646-774482d4b2f0`，新 manager PID 999、active/running。之前的 DPU/原图分类和冷启动验收证据保持原样。本次未重复运行推理或压力回归。

## 1. NFS：已锁定配置不一致

实际板端证据：

- `/proc/config.gz`：`# CONFIG_NFSD is not set`，`CONFIG_NFS_FS=y`。
- `/proc/filesystems` 没有 nfsd；`modprobe -n -v nfsd` 报模块不存在（只做 dry run，没有加载模块）。
- 启动日志明确是 `unknown filesystem type 'nfsd'`。
- `nfs-server.service` 与 `nfs-mountd.service` 为 enabled；`/lib/systemd/system/sysinit.target.wants/proc-fs-nfsd.mount` 又直接开机拉起挂载。因此只停用 server 并不能完整取消这个独立启动入口。
- 当前导出条目为 0、NFS 挂载为 0，root/boot 在本地 SD 卡。

按目前实际用途，修复方法是备份服务启用状态和挂载启动入口，然后停用 NFS server/mountd 的开机启动，并通过 `/etc/systemd/system` 的可回退配置取消 nfsd 挂载的自动启动。保留 NFS 客户端支持与客户端所需服务，不删除原厂 unit。最后清理该单元的 failed 状态。

若最终项目确实需要把板卡作为 NFS 服务端，则选择另一条方案：在最终内核中启用 CONFIG_NFSD，提供与该内核匹配的模块/依赖，并配置实际导出。当前无服务端用途时增加这个内核功能没有必要。

验收条件：配置确实持久化，下次启动不尝试不受支持的 nfsd 挂载、不出现相应 mount/dependency 失败，DPU 与项目服务保持正常。仅 `reset-failed` 不满足验收条件，因为它没有修复开机配置。

官方接口说明：[Linux nfsd 管理接口](https://cdn.kernel.org/doc/html/latest/admin-guide/nfs/nfsd-admin-interfaces.html)。

## 2. TPM：已确认后续初始化恢复

日志在 `A TPM error (256) occurred attempting the self test` 后紧接 `starting up the TPM manually`。板端设备 `/dev/tpm0`、`/dev/tpmrm0` 存在，绑定 `tpm_tis_spi`，协议 2.0。

本轮实际执行只读命令：

```sh
tpm2_getcap -T device:/dev/tpmrm0 properties-fixed
```

返回 0，读出 TPM 2.0 / IFX 的能力和版本信息。对应源码将 `0x100` 定义为 `TPM2_RC_INITIALIZE`；`tpm2_auto_startup()` 遇到此码会执行 Startup 再做自检，成功后才继续注册设备。

处理办法：在健康检查中区分首次未初始化返回码与最终初始化结果，将当前情况记录为启动时已恢复的初始化提示。若最终镜像希望调整日志，应仅针对这个已确认可恢复的初始化分支处理，保留其他 TPM 失败报告。没有证据支持现在清空 TPM、重写其固件或判定硬件损坏。

依据：[TCG TPM 2.0 返回码定义](https://trustedcomputinggroup.org/wp-content/uploads/TCG_TPM2_r1p62_Part2_Structures_7july2020.pdf)；本地对应源码 [tpm2_auto_startup](/home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/drivers/char/tpm/tpm2-cmd.c:723)、[TPM 设备注册](/home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/drivers/char/tpm/tpm-chip.c:552)。能力查询只证明本次命令成功，不替代 TPM 的全部安全功能验收。

## 3. overlay：属于内核与设备树的属性生命周期

对应 [add_changeset_property](/home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/drivers/of/overlay.c:304) 在更新非 OF_OVERLAY 的存量节点属性时发出该提示。本次涉及 fpga-full、显示节点、__symbols__。前轮 manager 的内存/监听回收验收不覆盖内核的这些属性对象；监听数回到 5 不能据此证明内核属性无泄漏。

项目当前路线是三人共享同一有效 PL 和 release。可先使固定的 DPU/运动共存配置在开机加载一次，运行期间保持同一配置，从而减少反复 overlay 卸载的触发。此安排只是减少触发，不是修复内核泄漏。

彻底处理需要在可回退的最终平台中审查基础 DTB/DTBO 修改范围，并选择经过审查、适合 2022.2 内核的属性引用/释放修复，重新构建相配套的内核与模块。验收必须包含反复加载/卸载、属性/节点恢复、内核对象增长和 DPU/显示功能检查。未做实际内核属性泄漏量测，不能承诺简单删掉警告或删除属性即可修复。

参考：[Linux 5.15 overlay 文档](https://www.kernel.org/doc/html/v5.15/devicetree/overlay-notes.html)。

## 4. 显示时钟 ret=-13：继续核对资源权限与平台描述

告警来自 `dpdma_ref_div1` 设置分频和 `dpll_int` 禁用路径。对应固件调用把 XST_PM_NO_ACCESS 转为 -EACCES，也就是 -13，见 [zynqmp_pm_ret_code](/home/ghmd/kv260-runtime-reproduce-20261003c/sources/linux/drivers/firmware/xilinx/zynqmp.c:83)。

当前 `card0-DP-1/status` 为 connected，DPDMA/DP audio 时钟也在使用。连接状态不等于显示功能完全验收，但足以说明不能将此显示链路视为无人使用。

后续修复应对照实际 QSPI/PMUFW、内核和 DT 的显示时钟请求，确认资源许可、请求值和显示功能；再决定配套 DT/驱动或固件改动。当前启动日志分别显示 2023.2 固件与 2022.2 内核，但版本字符串本身不足以确认此次权限拒绝的唯一原因。该根因仍待进一步验证。

## 5. IRQ 8 与 xclbin section -22：先核对触发条件

当前 [ZOCL probe](/home/ghmd/kv260-runtime-reproduce-20261003c/sources/xrt/src/runtime_src/core/edge/drm/zocl/zocl_drv.c:1064) 逐项取中断，在第 8 索引没有下一项时停止；这种枚举方式会打印缺项信息。后续可按 DT 的实际中断数量限定枚举边界，但要先核对实际 IRQ/设计关系，再对候选驱动验收。

当前 [zocl_read_sect](/home/ghmd/kv260-runtime-reproduce-20261003c/sources/xrt/src/runtime_src/core/edge/drm/zocl/zocl_xclbin.c:279) 对缺失 section 记录 `DRM_INFO` 后返回长度 0；AIE/debug 等缺失要按实际设计判定是否可选。原官方 DPU query 和推理已经通过，不应把所有 `-22` 文本一概作为推理失败。

## 证据与范围

- [NFS/内核/TPM/时钟只读采集](/home/ghmd/kv260-dfx-state-boardtest-20261004/evidence/20261004T085613.788558Z-25-readonly-warning-diagnostics/status.json)。
- [TPM 能力查询与 NFS 启动入口](/home/ghmd/kv260-dfx-state-boardtest-20261004/evidence/20261004T100638.016386Z-26-readonly-tpm-and-nfs-startup/status.json)。
- 首次诊断命令超出 UART 单行长度，在发送任务命令前停止；echo 恢复，失败证据保留。拆成四个短命令后采集通过，没有放宽串口协议限制。

以上是已确认的诊断和修复方案。NFS 配置清理、内核 overlay 修复、显示时钟修复尚未实施，也没有进行新一轮物理断电验收。之前封存的交付包没有覆盖或重打包。
