---
name: kv260-runtime-review
description: Review DFX manager and ZOCL runtime failures on Kria Linux, compare inotify bookkeeping with kernel watches, check Unix socket readiness, and preserve reproducible repair evidence. Use for overlay runtime diagnosis and validation planning.
---

# KV260 运行时证据审阅

用于 Kria Linux 上 DFX manager / ZOCL 的运行时排错、修复复验与恢复证据整理。先确认用户当前要执行诊断、临时切换还是永久启用；已有构建或历史板测不替代实时板端检查。

## 关键判断

- 先固定 daemon、XRT、内核、镜像与源码 commit。SDK 的器件枚举、ELF 构建、离线 ABI 检查、目标板推理分别记录。
- 对反复扫描产生的 watch 耗尽，同时记录程序内部登记数量与同一 PID 的内核 inotify 数量。内核 wd 必须和所属 inotify FD 组合计数。内部表满而内核数量稳定，优先检查重复登记、删除和表洞复用；不要直接增大容量掩盖重复登记。
- Unix socket 就绪检查按服务端源码的实际类型执行。这个固定 dfx-mgr 版本是 AF_UNIX / SOCK_SEQPACKET；其它版本先核对。连接成功只证明 IPC 可达，仍要核对服务 PID/可执行文件与客户端功能。
- 初次就绪失败时保留失败日志，读取进程、unit、socket 和源码，再决定续测或恢复。候选已经启动时，禁止仅为重试探针而盲目重放驱动与服务切换。
- ZOCL 查询函数的返回值可能持有设备引用。逐一审查成功、失败及提前返回路径，并区分借用的 drvdata；补齐引用释放不等于证明并发热卸载安全。

## 工具与案例

- 只读采样 PID、RSS、系统内存、slab、FD/inotify、ZOCL 参数：[scripts/watch_snapshot.py](scripts/watch_snapshot.py)。PID 必须来自本次观察；进程更替或无法读取时输出错误，不能当作零 watch。多次采样才可讨论趋势，工具不执行应用重载。
- 单次 socket 检查：[scripts/socket_probe.py](scripts/socket_probe.py)。指定路径，确认协议；无自动重试、服务启动或固件加载。
- 要分析已发生的重复登记及就绪误判时，读 [references/verified_cases.md](references/verified_cases.md)。
- 要准备临时切换、恢复或长期复验时，读 [references/controlled_validation.md](references/controlled_validation.md)。

## 范围和交付

这些脚本不授予部署权限。缺少目标连接时完成主机源码、补丁、许可、日志与复现准备，明确留下板端待办。更换镜像、内核、卡号、应用或模型后重新检查，不能套用此案例的固定值。

交付需包含固定来源、最小补丁、原始失败与成功日志、同一模型/图片的对照、恢复结果和待确认项。保留厂商 DRC 与内核原始诊断；没有长期数据时不写“无泄漏”。本技能不承诺 PYNQ 加分、比赛得分或完整作品验收。
