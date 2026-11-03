# KV260 修复版运行时持久启用方案审阅

> 本文记录安装前的准备与只读审阅阶段。后续已完成安装和冷启动验收；最终状态以 [PERSISTENT_ENABLEMENT_REPORT.md](</home/ghmd/kv260-runtime-persistent-plan-20261003/PERSISTENT_ENABLEMENT_REPORT.md>) 为准。

## 结论

主机侧已准备可审阅的候选安装与回滚材料，并经 UART 对备用卡做了新鲜只读检查。输入复用此前已在这块备用卡上在线板测通过的二进制。本轮**没有**向板卡写入文件、修改启动配置、切换运行时或重启；永久启用和冷启动仍未验证。

本次 UART 检查未在 initramfs、启动 DTB 中发现 ZOCL，也未发现显式 modules-load/modprobe/udev 配置加载 ZOCL；`xlnx-firmware-detect` 脚本只验证默认固件配置和目录，不加载 overlay 或内核模块。内核存在 OF modalias 到 `zocl` 的自动匹配，因此 overlay 创建设备节点时可能触发自动加载。拟议 loader 排在 `systemd-modules-load`、udevd、udev-trigger 之后，并由 manager drop-in 的 `Requires`/`After` 保证先于 manager。此机制与现有证据相符，但冷启动关系仍未实际验证；板端没有 `systemd-analyze`，故 unit 依赖还需在正式文件名下做静态校验。

## 已确认的输入与证据

| 项目 | 已核对值 |
|---|---|
| 板端系统 | PetaLinux 2022.2，kernel `5.15.36-xilinx-v2022.2` |
| 测试卡 | 备用卡 CID `0353445345333247805558c00401a100` |
| DFX manager 源码 | `bc06691eb35d7f0acb7c2508b6d050d77b0264a0` |
| XRT / Linux 源码 | `43926231f7183688add2dccfd391b36a1f000bea` / `19984dd147fa7fbb7cb14b17400263ad0925c189` |
| 候选 manager | 117,488 B，SHA-256 `db9c25f09f1178177884b1114c57f32c076f1e7f9cdd0d12b7a896039038a46c` |
| 候选 ZOCL | 339,600 B，SHA-256 `5cef5e0eba083419b3ece6fd4829a9f3112e3f0daaee513e1617d60ed1f7f412`，srcversion `9BDC942A6014BCCBD1DCB78` |
| 驱动参数 | `enable_xgq_ert=1` |
| 原版状态指纹 | ZOCL srcversion `0991D1B457855C8987936E`；原 manager SHA-256 `bdbd8ee09b3f767a53bd5111240c9ade3bb19b1da83d73bd06785ae86260e9a2` |
| 官方应用 | `kv260-benchmark-b4096`，之前复验恢复 slot 0 |
| 在线复验 | 30 轮切换、1802.124 秒观察、872 次同图推理、35 次 DPU query、905 份分类结果一致；报告指出原基线恢复成功 |
| 本次 UART 检查 | 备用卡 CID 与 `mmcblk1p2` 符合；原 manager 与 ZOCL 哈希相符；原 manager active、无 drop-in；官方 benchmark slot 0；ZOCL refcnt 0，DRM 节点无占用 |
| 本次基线核对 | 历史清单 26 项文件 SHA-256 全部重新计算并一致 |

在线复验报告：[LIVE_REVIEW_REPORT.md](/home/ghmd/kv260-runtime-live-20261003-retry1/LIVE_REVIEW_REPORT.md)。封存目录和旧失败轮次均保留。本方案包中的二进制是拷贝件，不是本轮重新构建的产物。

## 本目录内容

- `bundle/`：原样复制的板测二进制、补丁、来源/依赖/基线元数据。
- `board_preflight.py`：板端只读采集器；输出 JSON，收集 CID、内核、模块、systemd、initramfs 候选项、`modules-load`、DRM、活动应用和 26 项原文件哈希。此次因用 UART 手工读取关键字段，尚未在板端运行该脚本。
- `templates/`：systemd loader、manager drop-in 与加载脚本的提案模板，已按只读启动顺序证据加入 udev/modules-load 顺序约束；还需 unit 静态校验及冷启动验收。
- `install_plan.json`：固定版本、哈希与安装门槛。
- `ROLLBACK.md`：按文件哈希限定的回滚设计及 UART 失效恢复原则。
- `PLAN_SHA256SUMS`：本目录文件清单，在封存完成后生成。

## 开机顺序风险与硬门槛

在线复验使用运行时临时 systemd override 成功替换 manager，并显式加载修复模块；这证明运行时组合有效，不证明冷启动时模块竞争顺序有效。initramfs 的 uImage 被流式解包检查；清单没有 `lib/modules`、ZOCL 或 modules-load 配置。根文件系统的 `/etc/modules`、modules-load、modprobe、udev 和 systemd 规则未发现 ZOCL 加载条目；两个启动 DTB 没有 zocl/embedded_sched 节点。板端内核有 OF modalias `xlnx,zocl` 到 `zocl` 的映射；默认 app 创建 overlay 设备时可由内核/udev 请求模块。`dfx-mgr.service` 已 enabled，在 `multi-user.target` 前运行；其 `ExecStartPre` 默认固件检测脚本只检查固件名与目录。modules-load 和 udev-trigger 在 `sysinit.target` 前完成；候选 loader 排在它们之后、manager 之前。loader 遇见已加载的非目标 ZOCL 会失败关闭，不会卸载或替换模块；manager drop-in 通过 `Requires` / `After` 依赖 loader。

这个 fail-closed 机制降低误替换风险；当前证据支持 loader 能在 manager 开始默认固件处理前加载目标模块。但仅有正在运行系统的观察，未经历冷启动。因此持久启用前仍需：

1. 板卡仍为指定备用卡和内核，官方原基线及 26 项文件哈希未漂移。
2. 保留本次证据，并在正式 `.service` 文件名下检查 unit；目标板没有 `systemd-analyze`，需在匹配 systemd 249 的开发环境/离线 root 校验。
3. 冷启动首轮收集 `dmesg`、模块 srcversion 和 service 时间戳，确认修复模块在默认 app overlay 之前加载。若观察到 stock ZOCL 先加载，停止并恢复，不强卸载或改写厂商规则来掩盖顺序问题。
4. 对新建文件、unit 和 drop-in 逐项审阅与哈希；验证回滚文件在板端可读，UART 可用；另行批准写入后才能重启。

满足这些门槛后，安装批次应先安装新目录中的候选文件，再安装 loader unit 和 manager drop-in；运行 `systemd-analyze verify` 审阅 unit；先在当前启动周期做受控服务切换和功能复测，只有成功才单独安排备用卡重启验收。若实际系统的早期模块加载顺序无法被安全控制，应停用持久方案，继续保持原启动配置，考虑通过重建整体启动镜像解决，并另行审阅。

## 通过项、实际问题、待确认项

### 已通过

- 精确的修复版 manager 与 ZOCL 二进制在相同备用卡/内核上完成了在线联合复验。
- 运行时恢复到原官方 manager、原 ZOCL、官方 slot 0；26 项原文件哈希一致；此前记录无临时 drop-in，boot ID 未变化。
- 新方案目录包含经摘要核对的候选输入及明确的恢复流程。
- `board_preflight.py` 的 Python 语法检查通过；候选 manager/ZOCL 的文件大小和 SHA-256 与板测记录一致。

### 当前实际问题

- 修复未持久启用，板卡仍使用原官方运行时；原版本已知运行时缺陷仍存在。
- 冷启动顺序未实测；目标板缺 `systemd-analyze`，当前 `.in` 草案不能直接部署。
- 长测不是冷启动、异常掉电或长期稳定性验证。内存变化在在线报告中也未完全归因。
- systemd unit 语法/依赖校验未通过：板端没有 `systemd-analyze`；主机只有 systemd 245，较目标 249 旧，且受限环境拒绝 systemd/varlink socket、临时校验又无法解析板端绝对 ExecStart 路径。此项必须在匹配目标版本的环境复核。

### 待确认

- `board_preflight.py` 尚未在板端运行；本次通过 UART 单独重算全部 26 项历史基线哈希，26/26 一致。
- 正式 unit 的目标版本静态校验、安装前新恢复副本、UART 回滚演练，以及持久化后冷启动验收。

## 本轮边界

只准备 Ubuntu 本地审阅包和脚本，并通过 UART 执行了只读检查；没有触碰板端文件、SD/QSPI、网络、执行器或 PWM。下一步完成全量基线核对与 unit 静态审阅后，方进入持久写入和单独重启验收。
