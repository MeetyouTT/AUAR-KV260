# KV260 DFX manager 状态修复：板测、持久化与冷启动验收

日期：2026-10-04。证据使用主机 UTC、板卡 boot ID 和单调时钟；板端墙上时间仍为 2021 年。

## 结果

新 manager 已完成实际板测、持久化部署和一次用户确认的断电冷启动验收。冷启动后 `dfx-mgr.service` 为 `enabled`、`active/running`，PID 999，官方 `kv260-benchmark-b4096` 自动加载到 slot 0，inotify 监听为 5、持久 inotify fd 为 1。原 26 项文件哈希全部保持一致。

安全关机成功后，用户按照拔板卡电源、等待、重新上电的说明确认“已重新上电”；主机被动捕获完整新启动并发送 0 字节 UART 输入。新 boot ID、同一 SD CID、实际新程序、ZOCL 启动顺序、官方 DPU 与原图分类均通过，主机独立回读核验 5223 个证据文件和累计 23 次有效阶段分类。物理断电操作以用户确认记录，实际断电时长和电源轨没有仪器测量。

本轮完成 manager 的共享状态、目录监听回收和活动包生命周期修复的板端验收。当前 PL 为官方 B4096；自研 AXI-Lite/PWM、DPU 与运动 IP 共存、三人整机功能仍需后续实现与验收。

## 实际部署

| 项目 | 实测值 |
|---|---|
| SD CID | `0353445345333247805558c00401a100` |
| 当前 boot ID | `01ca88c1-93b6-414f-9646-774482d4b2f0`，物理操作后新启动 |
| 冷启动前 boot ID | `a7733edd-db41-4527-b8fb-cefdcbfe7b3a` |
| 内核 | `5.15.36-xilinx-v2022.2` |
| root / boot | `/dev/mmcblk1p2` ext4 / `/dev/mmcblk1p1` vfat |
| 当前 manager | `/usr/local/lib/kv260-dfx-state-repair-20261003/dfx-mgrd` |
| manager 大小 / SHA-256 | 117856 字节 / `369c7fb0ddd023a7cf7af14896a7fda6036219a36f4980c73640889720c95dfd` |
| 新增持久化配置 | `/etc/systemd/system/dfx-mgr.service.d/20-kv260-dfx-state-repaired.conf` |
| 配置 SHA-256 | `b46fd13058a791972516355663ff64da8c0692628ea2467e5627476aa9a5ce16` |
| ZOCL | 保持先前已验证版本，srcversion `9BDC942A6014BCCBD1DCB78`，`enable_xgq_ert=1` |
| ZOCL 二进制 SHA-256 | `5cef5e0eba083419b3ece6fd4829a9f3112e3f0daaee513e1617d60ed1f7f412` |
| 旧 manager 恢复点 | `/usr/local/lib/kv260-runtime-repair/dfx-mgrd`，SHA-256 `db9c25f09f1178177884b1114c57f32c076f1e7f9cdd0d12b7a896039038a46c` |

旧 `/etc/systemd/system/dfx-mgr.service.d/10-kv260-repaired.conf`、原厂 unit、原客户端、原运行库、原固件、模型、图片和已有 ZOCL 均保留。新配置继承原有 `Requires/After=kv260-repaired-zocl.service`；临时 `/run` 验收配置已在回退复验时移除。

## 验证

| 验证 | 实际结果 |
|---|---|
| 接入核对 | 板卡身份、boot、旧 manager、ZOCL、原 26 项哈希与上次验收记录一致 |
| 包传输与解包 | 229371 字节原 host-verified 包 SHA-256 匹配；154 个文件，清单成员逐项通过 |
| 官方默认加载 | 新候选自动加载官方 B4096，真实 overlay/render 节点存在 |
| 并发查询 | 4 个查询线程各 250 次，共 1000 次；压力查询没有自动重试，全部成功 |
| 目录变化 | 与查询并发执行 100 轮父目录创建、子目录重命名、父目录删除；每轮 3 子包、6 孙目录 |
| 监听回收 | 有相似前缀邻包时，加入后 16、删除父目录后 6；邻包移出后回到 5，相似前缀邻包保留 |
| 活动目录消失 | 专用官方固件副本加载后移出扫描目录；从可加载列表退出，slot 与实际硬件节点保留；显式卸载后 overlay/render 消失、runtime 为空 |
| 同名复用 | 同一专用包重新引入后为 inactive，随后正常加载、同图推理、卸载；最终移出专用目录并恢复官方应用 |
| 真实加载/卸载 | 10 轮官方应用加载/卸载，每轮同时核对协议、实际节点、slot、query 和 Top-5 |
| 越界请求 | slot 255、-2 返回错误；官方推理保持一致 |
| 守护进程状态 | 压力和循环期间 PID、5 个监听和最终 fd 数保持基线；持久化服务重启 PID 59580，冷启动后 PID 999 |
| 回退演练 | 临时配置移除后恢复旧 manager，官方默认加载、原图推理和全部恢复文件哈希通过 |
| 持久化复验 | 新增 20 配置后再次正常切换；实际 ExecStart、依赖、原图推理、原 26 项哈希通过；最终 `is-enabled` 返回 `enabled` |
| 断电冷启动 | 同一 CID、新 boot ID、新 manager 实际程序、ZOCL/默认官方应用自动加载、原图推理和原 26 项文件通过 |
| 启动顺序 | ZOCL 装载完成于 13.214874 秒，manager 实际 ExecStart 于 14.038433 秒；Requires/After 保留 |
| boot 挂载 | `/dev/mmcblk1p1` vfat；fstab 仅一个 `/boot` 条目，未检出 FAT 未正常卸载、文件系统错误或重复 boot 条目 |
| 主机独立回读 | 冷启动证据归档 5223 个文件逐个匹配；23 次有效阶段分类的原模型/图片路径和完整 Top-5 逐次匹配，query 逐字段一致（排除进程相关的 `cu_handle`） |

并发查询延迟：中位数 29.47 ms，P95 48.74 ms，P99 60.01 ms，最大 100.82 ms。这个指标针对本轮 4 个客户端加目录变化的列包请求，不是 DPU 推理延迟或 FPS。

原图 Top-5 为：258/0.949879、270/0.00931229、259/0.00821807、257/0.00498451、279/0.00388194。实测 1 个 `DPUCZDX8G_ISA1_B4096` CU、300 MHz、地址 `0xa0010000`、fingerprint `0x101000056010407`。

上一轮 8 项普通回归、8 项 ASan/UBSan（含泄漏检测）及原镜像加载器枚举通过；本轮部署与其相同的 AArch64 二进制，未追加改动候选源码。TSan 仍未运行。

## 本次冷启动过程

1. 主机于 `2026-10-04T08:27:11.393822+00:00` 确认内核 `reboot: Power down`；此前正常卸载官方应用、核对实际节点移除、停止 manager 并 sync。
2. 用户确认物理重新上电。仅读串口采集到新的 U-Boot/Linux 启动、自动 root 登录和提示符，共 52410 字节；采集器发送 0 字节，不中断 U-Boot 倒计时。
3. 新启动的 `validate_v5.py postboot` 全部检查通过：同一备用卡、修复模块、新 manager、正式 20 配置、默认应用、官方 DPU profile、原图 Top-5、原 26 项哈希、5 个监听、boot 挂载。
4. 实际 systemd 单调时间证明 ZOCL 先装载完成，再启动新 manager。ZOCL loader 本身为 disabled，由 enabled 的 manager 的 Requires 拉起；该依赖与实际启动顺序均已核对。
5. 将 749298 字节证据归档回读主机，逐文件复核 5223 个文件及 23 次分类通过，并同时核验安全关机、用户确认、仅读启动串口和新 boot ID 的证据。

## 不完整尝试与修正

四次不完整尝试及所有原始错误保留，详见 [HARNESS_CHANGES.md](HARNESS_CHANGES.md)：

1. 旧 manager 卸载后返回空 slot 文案，脚本最初仅接受 `No active design`。实际硬件已卸载；恢复官方推理后，对旧版本单独接受其已核验的空 slot 文案。
2. `Type=simple` 的首次客户端请求早于默认 FPGA 加载和 socket 监听。加入最多 30 秒的只读启动就绪检查；压力查询不重试。
3. 并发短连接关闭时 `/proc/<pid>/fdinfo/7` 消失。采集器跳过瞬时消失的描述符，仍要求恰好一个持久 inotify fd；完整 1000 查询/100 轮目录测试重新执行通过。
4. 活动包移出后，新的 VART query 因原位置 xclbin 文件不存在而返回 134。错误原文已确认。仅给测试子进程设置 `XLNX_VART_FIRMWARE` 指向移出后的同一文件（先校验原文件哈希），实际 query、原图推理和显式卸载随后通过；再次完整重跑活动生命周期用例。未重写全局配置来掩盖这个缺失输入，也未关闭 fingerprint 检查。

第四项说明新启动的 VART 进程仍需要可读 xclbin；manager 保留已加载硬件和 slot 不会使被移走的文件重新出现。部署和热更新应保存当前活动 release 的输入文件，直到正常卸载并完成服务切换。

冷启动主机复核的第一次尝试另外记录了一次关键词误报：`Oops:` 子串命中了原启动同样存在的 `mtdoops: mtd device (mtddev=name/number) must be supplied`。匹配规则补上单词边界后，对同一归档重新完整回读通过。首次主机复核失败报告保留，未重写板端原始日志；它不计入前述四次板端不完整尝试。

## 日志范围与剩余事项

本轮验收内核窗口新增 702 行，关键词检查未检出 kernel panic、Oops、Call trace、锁死、I/O/文件系统错误或 timeout。128 条告警候选均属于已有 overlay property leak、IRQ index 8 和 XCLBIN 可选 section `-22` 类型，原文已保存。它们没有在本轮修复；关键词检查不证明系统不存在其他缺陷。此前 NFS、TPM、时间同步等问题仍按原报告记录。

本次新启动内核日志有 46 条宽松关键词候选，包含条件跳过提示及已有 clock `ret=-13`、TPM self-test 256、overlay property leak、IRQ 8、可选 section `-22` 等；`systemctl --failed` 仍有 `proc-fs-nfsd.mount`。这些遗留问题未修复。新启动未检出所列严重内核/文件系统错误或重复 boot 挂载条目；这个结论只针对本次日志和检查规则。

真实板端覆盖 XRT_FLAT 官方应用和正常物理卸载；PL_DFX 部分重配置及真实硬件卸载失败/进行中没有在本轮故意触发。对应失败保留策略的本机测试替身结果不能代替真板故障处理验收。本轮冷启动仅一次，未做连续断电循环、长期满载或执行器测试。

本轮运行时修复的板测、部署和冷启动验收已完成。后续项目关卡是冻结三人共用接口，并在同一次启动、同一有效 PL 中验收 DPU 与自研运动 IP 共存；本报告不能代替该关卡或比赛整机验收。

## 证据和恢复

- [冷启动主机独立复核](/home/ghmd/kv260-dfx-state-boardtest-20261004/reviews/20261004T084536.786164Z-postboot/review.json)：5223 文件、23 次分类，installed/cold_boot_verified 均为 true。
- [物理冷启动证据复核](/home/ghmd/kv260-dfx-state-boardtest-20261004/reviews/20261004T084536.786164Z-postboot/COLD_BOOT_VERIFICATION.json)：安全关机、用户确认、仅读串口、新 boot、实际启动顺序和遗留告警。
- [冷启动板端证据归档](/home/ghmd/kv260-dfx-state-boardtest-20261004/evidence/20261004T084214.824550Z-22-fetch-postboot/postboot-board-evidence-archive.output)：749298 字节，SHA-256 `77cda60f5390617d5242871ded445917cb3ed2fffd93a101f2350dd8ff084c0c`。
- [板测通过交付包](/home/ghmd/kv260-dfx-state-boardtest-20261004/release/dfx-state-20261004-board-verified.tar.gz)：本次报告、候选二进制/配置、原本机验证包、板端证据、主机原始串口和回读记录；成员哈希以同目录 `PACKAGE_VERIFICATION.json` 为准。
- [冷启动后最终只读检查](/home/ghmd/kv260-dfx-state-boardtest-20261004/evidence/20261004T084633.179449Z-23-final-coldboot-state/status.json)：新 boot/PID 999、enabled、官方 slot 0、5 个监听、fd 7 和原 26 项哈希均通过，串口 echo 已恢复。
- [原修复与本机验证封存检查](/home/ghmd/kv260-dfx-state-boardtest-20261004/SEALED_INPUTS_REVIEW.json)：1898 + 1301 个文件哈希保持一致。
- [持久化后的主机复核](/home/ghmd/kv260-dfx-state-boardtest-20261004/reviews/20261004T081409.073077Z-installed/review.json)：5139 文件、22 次分类。
- [持久化证据归档](/home/ghmd/kv260-dfx-state-boardtest-20261004/evidence/20261004T081048.599960Z-17-fetch-installed-evidence/installed-board-evidence-archive.output)：640987 字节，SHA-256 `207afa3c23dc76e0a7c67823b040ed78d257260bf53326cf36357f4bb034cc03`。
- [冷启动前只读检查](/home/ghmd/kv260-dfx-state-boardtest-20261004/evidence/20261004T081528.350500Z-18-final-readonly-state/status.json)：enabled、实际新进程、原件哈希与监听检查均通过，串口 echo 已恢复。
- 板端恢复原件：`/home/root/kv260-dfx-state-boardtest-20261004/backup/`；相同字节已包含在上述主机证据归档及解包目录中。
- [原系统整卡恢复镜像](/home/ghmd/kv260-sd-backup-20261003/kv260-spare-runtime-fixed-20261003.img) 保持原样，本轮未写 SD 整卡、QSPI、原厂库或已验证 ZOCL。

持久化回退时：先停止实际 DPU 使用者并以当前 manager 正常卸载，确认 overlay/render 均移除，再停止 manager；核对本次 20 配置路径、内容和上表哈希，仅移除这一新增配置；`daemon-reload` 后必须实际解析为旧 `/usr/local/lib/kv260-runtime-repair/dfx-mgrd`，再启动并复跑官方 query/原图分类。保留 10 配置及已验证 ZOCL。临时配置的回退已实际演练；持久化配置回退的上述步骤本轮没有再执行。
