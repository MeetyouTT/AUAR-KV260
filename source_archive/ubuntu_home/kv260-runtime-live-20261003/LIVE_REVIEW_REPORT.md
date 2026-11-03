# KV260 实时连接与首次有限复验记录

## 结果

Ubuntu 沙箱外确实识别到同一 KV260，USB UART `/dev/ttyUSB1` 可用。此前沙箱中的设备不可见不能代表主机未连接。串口 root shell 已确认；备用卡 CID、根分区、内核、原管理器/驱动、官方槽位及 26 项文件哈希一致。

首次复验在 `10_start.py` 卸载原应用之后、加载修复驱动之前停止。问题来自本次自编测试脚本要求整个旧 `dmesg` 是新日志前缀：正常环形缓冲滚动不符合该条件。控制器已执行恢复，原模块、原服务、官方应用、原 VART 和 26 项哈希全部恢复；同模型同图完整 Top-5 与基线一致。boot ID 不变。

本次尚未加载修复二进制，没有执行 30 轮切换或 30 分钟观察，也没有永久启用、重启、烧录、PWM 或执行器操作。将在另一个独立目录修正测试脚本的增量日志算法后复验；不修改厂商源码或检查规则。

## 已执行证据

| 阶段 | 实际结果 |
|---|---|
| USB 主机枚举、UART 身份 | 连接确认；同一已测试备用卡 |
| 初始宽泛 DRM 检查 | 因 Xorg 打开 card0 停止，失败记录保留 |
| sysfs 驱动对照 | card0=zynqmp-display；card1/renderD128=ZOCL，无相关客户端，refcnt 0 |
| 原文件核对 | 26 项 SHA-256 一致 |
| 新恢复点 | 独立 `baseline/files/` 中 26 项逐份复制并校验；state/kernel/journal/fstab 原样保存 |
| 联合输入传输 | 162,841 B，54 帧全部 ACK，整包和 13 个成员校验通过 |
| 本机离线检查 | 16 项通过；不替代板测 |
| 首次 worker | `10_start.py` 日志前缀断言失败；后续实验阶段未运行 |
| 自动受控恢复 | `60_restore.py` 完成；原驱动 srcversion 0991D1B457855C8987936E6；原服务无 drop-in；官方 slot 0 |
| 原功能复跑 | 1 CU/B4096/300 MHz/0xa0010000/0x101000056010407；完整 Top-5 一致，Samoyed 0.949879 |

## 确认的失败原因

两份原始日志分别为 645 行、67,014 B 和 645 行、66,989 B。后者滚出了前 4 行，保留前者末尾 16 行的唯一连续匹配；匹配结束索引为 641，新增 4 行完整。新增错误仅为原 ZOCL 卸载的已知 `expected refcount 1 instead of 2` 一条。

因此本次是日志连续性判定过严，不能归因为修复驱动、DPU 或板卡故障。新判定将寻找旧日志尾部的唯一连续重叠，仍在不存在重叠、存在歧义或出现新增不允许错误时停止。

## 路径与哈希

- 板端工作目录：`/home/root/kv260-runtime-live-20261003T082232Z`。
- 测试输入包：`reviewed_package.tar.gz`，SHA-256 `21d636cdcb8f7f0176de41ed477ddbacbce6ce291206620cc89a86accfab5087`。
- 完整板端证据归档：`board_evidence.tar.gz`，71,597 B、28 个成员；SHA-256 `b89ad1baf4d30309c725f6e93a76a36bd33e59609acc8591b1cb575cd905db85`。逐成员读取和哈希验证通过。
- 真实日志和恢复输出：`board_evidence/logs/`、`board_evidence/agent_logs/60-restore/`。
- 原失败 UART 清单、输出和完整流：`evidence/`；来源和包：`reviewed_payload/`、`package_manifest.json`。

## 限制

板卡 wall clock 为旧日期，未改时间；主机采集时间另存，长测试使用单调时钟计时。控制器异常时会尝试受控恢复；若管理器已死亡但 overlay 仍活动，严格检查会停止，不强制卸载或盲目重放。
