# 当前状态：DFX manager 候选有限验证完成

- 重复 watch 登记的原因已复现并修复；固定 dfx-mgr commit 没有变化，仅改一个源文件。
- 原版及候选 AArch64 构建、主机扫描/生命周期/边界/同项并发回归、原镜像 ABI 与 loader 检查通过。
- KV260 上候选通过专门的 1,000 次列表循环、50 次目录增删、3 轮官方应用重载及官方/M3 同图推理；完整日志 `ERROR:` 为 0。
- 原管理器、原 ZOCL、官方活动应用和 VART 配置已恢复；26 文件哈希一致，boot ID 未变。没有烧录、重启或 PWM 操作。
- 24 条板端命令成功，另 1 条就绪探针因我错误使用 SOCK_STREAM 失败；保留证据，独立改为 SOCK_SEQPACKET 后完成续跑和恢复。
- 当前仍运行原程序，两项原有软件缺陷并未永久替换。基线重复 `/boot` 配置、overlay 属性警告、既有 DRC/时序限制及长期验收仍待处理。

报告：[DFX_MANAGER_REPAIR_REPORT.md](DFX_MANAGER_REPAIR_REPORT.md)。

同一已板测二进制的整理包：[kv260-dfx-watch-reviewed.tar.gz](release/kv260-dfx-watch-reviewed.tar.gz)。它包含候选与审阅信息，没有安装脚本或固件；整理后没有再次部署。

下一阶段是为备用卡形成两项修复的固定启用与长期复验方案，随后继续 PWM。不能把本轮有限通过解释为长期部署已经完成。
