# 2026-10-04：DFX 状态修复通过板测、持久化与断电冷启动

## 结果

承接用户“已接好”，通过 KV260 USB UART 继续前一轮源码修复后的板端验收。最初沙箱 `/dev` 未显示串口，但 `/sys/class/tty` 检出四个 ttyUSB；申请沙箱外只读检查后发现 Xilinx ML Carrier Card，使用固定 if01 UART 接入。当前备用卡 CID 和 boot ID 与 2026-10-03 最后冷启动记录一致，旧 manager、已修复 ZOCL、原 26 项文件哈希一致。

本轮完成 1000 次实际并发列包、100 轮多层目录创建/重命名/删除及监听回收、活动专用固件包移出后的硬件/slot 保留与显式卸载、同名复用、10 轮真实官方加载/卸载及原图分类。临时配置的回退与旧 manager 复验通过；之后新增持久化 20 配置，实际新 manager 的服务重启、默认官方应用和推理再次通过。主机逐文件核验 5139 个证据文件及 22 次有效阶段的原图 Top-5 均通过。

断电前 `dfx-mgr.service` 为 enabled、active/running、PID 59580，实际程序为新 `/usr/local/lib/kv260-dfx-state-repair-20261003/dfx-mgrd`，官方 B4096 在 slot 0，监听为 5。原 26 项文件保持一致。用户随后要求开始断电冷启动，安全关机并由用户确认重新上电后，已完成下述新启动复验。

## 断电冷启动实测

主机于 `2026-10-04T08:27:11.393822+00:00` 确认 `reboot: Power down`；此前正常卸载并确认 overlay/render 移除、停止 manager 和 sync。用户按照拔板卡电源、等待、重新接通的说明确认“已重新上电”。被动串口采集发送 0 字节，捕获新 U-Boot/Linux 和自动 root 登录，共 52410 字节；实际断电时长与电源轨未测量。

同一 SD CID 下新 boot ID 为 `01ca88c1-93b6-414f-9646-774482d4b2f0`，不同于之前的 `a7733edd-db41-4527-b8fb-cefdcbfe7b3a`。新 manager 自动启动，PID 999，正式 20 配置生效、临时配置不存在；ZOCL 装载结束于单调时间 13.214874 秒，manager 实际启动于 14.038433 秒，Requires/After 保留。ZOCL loader 为 disabled，通过 enabled 的 manager Requires 自动拉起。

官方 B4096 自动加载 slot 0，DPU 1 CU/300 MHz/fingerprint 保持基线，原模型原图完整 Top-5 相同，原 26 项文件、旧修复模块/脚本/10 配置哈希一致，监听仍 5。root/boot 挂载正确，fstab 仅一个 `/boot` 条目，未检出 FAT 非正常卸载或重复挂载。主机逐文件复核 5223 个板端证据文件及累计 23 次有效分类通过；安全关机、用户确认、仅读启动和新启动结果分别校验后，`cold_boot_verified=true`。

- [冷启动独立复核](/home/ghmd/kv260-dfx-state-boardtest-20261004/reviews/20261004T084536.786164Z-postboot/review.json) 与 [物理启动证据](/home/ghmd/kv260-dfx-state-boardtest-20261004/reviews/20261004T084536.786164Z-postboot/COLD_BOOT_VERIFICATION.json)。
- 回读板端归档为 749298 字节，SHA-256 `77cda60f5390617d5242871ded445917cb3ed2fffd93a101f2350dd8ff084c0c`。
- 原源码修复与本机验证封存的 1898 + 1301 个文件再次逐项核验一致。

## 改动与证据

- [板测工作目录和报告](/home/ghmd/kv260-dfx-state-boardtest-20261004/BOARD_REPAIR_REPORT.md)：新串口传输、分阶段验收、独立回读脚本及不可覆盖的原始日志。
- [最终持久化主机复核](/home/ghmd/kv260-dfx-state-boardtest-20261004/reviews/20261004T081409.073077Z-installed/review.json)：5139 个文件、22 次分类验证。
- 新 manager SHA-256：`369c7fb0ddd023a7cf7af14896a7fda6036219a36f4980c73640889720c95dfd`，117856 字节，与上一轮本机回归和原镜像 ABI/loader 通过的同一候选一致；本轮没有追加改动候选源码。
- 新板端配置：`/etc/systemd/system/dfx-mgr.service.d/20-kv260-dfx-state-repaired.conf`，SHA-256 `b46fd13058a791972516355663ff64da8c0692628ea2467e5627476aa9a5ce16`。旧 10 配置、旧修复 manager、原厂 unit/client/libs/firmware/model/image、已验证 ZOCL 和整卡备份保留。
- 临时 `/run` 配置已移除；当前 20 配置继承原 ZOCL Requires/After，没有改原 unit 或模块装载脚本。

## 失败记录与边界

四次不完整验收尝试全部保存，详见报告和 `HARNESS_CHANGES.md`：旧版空 slot 文案、Type=simple 启动未就绪、采集 `/proc` 短连接描述符关闭的竞态，以及移出活动目录后新 VART 进程缺少原路径 xclbin。修正验收输入/采集行为后完整重跑对应用例。最后一项通过子进程专用固件路径读取同一已核验 xclbin，不修改全局配置或关闭 fingerprint 校验。

验收内核窗口有 128 条旧类型告警（overlay property leak、IRQ index 8、可选 section -22）；严重错误关键词检查没有命中。告警未修复，关键词检查不能保证全无问题。TSan 仍未运行，真实硬件卸载失败/进行中与实际 PL_DFX 部分重配置未在本轮触发；本机替身验证不能替代这些真板事项。

冷启动主机复核首次出现关键词误报：`Oops:` 命中基线也存在的 `mtdoops` 驱动提示。补上单词边界后，对原归档重新完整核验通过；首次主机失败报告保留，板端日志没有改动。

新启动内核宽松关键词候选为 46 条，仍有 clock `-13`、TPM 256、overlay 等旧告警，`proc-fs-nfsd.mount` 仍 failed；这些问题未修复。本轮仅一次用户确认的冷启动，不代表连续断电可靠性或系统全无缺陷。运行时修复本轮验收已完成，下一项目关卡是冻结三人接口并验收同一有效 PL 下 DPU 与自研运动 IP 共存。

## 最终交付

冷启动后的最后一次只读检查通过：boot ID 保持新值、PID 999、enabled/active、官方 slot 0、监听 5、fd 7、原 26 项文件一致，UART echo 恢复。结果保存于板测工作目录 `FINAL_STATUS.json`。

[板测通过交付包](/home/ghmd/kv260-dfx-state-boardtest-20261004/release/dfx-state-20261004-board-verified.tar.gz) 已生成并重新打开逐成员回读，180 个成员全部匹配，4378924 字节，SHA-256 `f04f9e1b63fef1ff978dbb4165610ed670cfd15701dafe7d9dd9d91d8b3efac6`。成员含候选二进制、配置、源码/本机回归原包、完整板端归档、主机串口、各次失败及最终复核报告；整包回读结果见同目录 `PACKAGE_VERIFICATION.json`。没有发布到外部系统。
