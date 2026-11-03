# KV260 运行时扩大复验报告

## 结论

**修复版通过本次有限板端复验，原官方基线已恢复。** Ubuntu 已通过真实 USB UART 连接板卡，完整证据回收到主机并逐成员校验。本轮没有烧录、重启、永久启用、PWM/执行器操作，未重新构建硬件或把已有固件列作新产物。

本次使用此前板测的 DFX manager 与 ZOCL 原二进制。30 轮官方应用卸载/重载、同图推理、至少 30 分钟观察、M3 的 DPU 参数及同图复核、原基线恢复均通过。新构建的主机复现二进制没有替代本次输入。

## 实测结果

| 项目 | 结果 |
|---|---|
| 板卡与系统 | 已测试备用卡；mmcblk1p2；PetaLinux 2022.2 / kernel 5.15.36-xilinx-v2022.2 |
| 官方应用切换 | 30 轮；原始 remove/load 各 30/30 次成功 |
| 连续观察 | 1802.124 秒；872 次同图推理；60 份内存/监视采样 |
| 全部功能复跑 | 35 次 DPU 查询、905 次分类，全部匹配 |
| DPU 参数 | 1 CU、B4096、300 MHz、0xa0010000、指纹 0x101000056010407 |
| 同图结果 | 全部 Top-5 一致；Samoyed 0.949879 |
| M3 | 固件哈希、DPU 查询及同图复核通过；本轮未重新执行寄存器/MMIO、PWM 或 FPS 测试 |
| 管理器完整日志 | SIGINT 后保存 2,708,388 B，ERROR 0 |
| 内核增量诊断 | 165 份审阅；修复阶段新增不允许错误 0；原驱动卸载已知错误 1 条 |
| 原基线恢复 | 原 manager、原 driver、官方 slot 0、VART 和 26 项哈希一致；临时 drop-in 移除；boot ID 不变 |
| 独立结束检查 | 原服务 active、worker Result=success / ExecMainStatus=0；无 ZOCL 客户端或模块占用 |

Top-5 按类别编号及原分数逐项比较：258/0.949879、270/0.00931229、259/0.00821807、257/0.00498451、279/0.00388194。使用原 ResNet18 XMODEL、原图片、原分类程序，不重新编译模型。

## 内存与监视情况

下表取 30 分钟阶段的 60 份真实采样，单位为 kB；最大采样间隔 31.930 秒。

| 项目 | 首次 | 最后 | 最小 | 最大 |
|---|---:|---:|---:|---:|
| 监视数 | 5 | 5 | 5 | 5 |
| manager RSS | 9524 | 9524 | 9524 | 9524 |
| MemAvailable | 3634836 | 3594152 | 3584396 | 3634976 |
| Slab | 75136 | 79812 | 74696 | 79884 |
| SUnreclaim | 37768 | 37324 | 37092 | 37768 |

管理器监视数始终为 5、RSS 始终为 9,524 kB；各采样中 ZOCL refcnt 为 0、参数 enable_xgq_ert=1，同一 candidate PID/starttime 连续。系统 MemAvailable 下降 40,684 kB，Slab 增加 4,676 kB；SUnreclaim 下降 444 kB，SReclaimable 增加 5,120 kB。测试会生成大量日志与文件缓存，当前没有把全部内存变化归因于某个模块，也不据此声称所有内存泄漏已排除。

原始采样及 CSV 保存；同图循环包含进程启动、查询、哈希检查、日志和间隔，**不能作为 FPS 吞吐测试**。

日志回收后又只读采集一次完整 meminfo：测试 logs/agent_logs 文件共 16,886,958 B；Cached 409,236 kB、Buffers 53,972 kB、Dirty 76 kB、Slab 79,388 kB、SUnreclaim 36,800 kB。该补充点已恢复原 driver，不能代替修复版长测样本，也不是受控释放缓存实验；原始记录在 evidence/memory-after-review.snapshot.output。

## 已确认的问题及本轮实际处理

1. **真实连接判断。** 沙箱内看不到 /dev/serial/by-id；沙箱外枚举和 UART 确认板卡已连接。此前设备不可见结论已纠正。
2. **相关 DRM 占用。** 最初测试脚本将 Xorg 使用 card0 判成阻塞。sysfs 明确 card0=zynqmp-display，card1/renderD128=ZOCL；实际 ZOCL 节点无占用，单独检查通过。没有停止桌面或绕过驱动占用。
3. **首次复验失败。** 自编 10_start.py 要求整个旧 dmesg 是新日志前缀，正常环形缓冲滚动导致失败。完整原始日志证明前 4 行移出、旧尾 16 行唯一连续重叠、新增 4 行完整；修复驱动尚未加载。该次受控恢复成功，失败输入和日志单独保留。
4. **只修正测试器。** 在新的独立目录用旧日志尾部唯一连续重叠判断增量；没有匹配或存在歧义仍失败，新增不允许错误仍停止。真实日志和 10 项边界验证通过。没有修改厂商 Tcl、内核规则、速度参数、DPU 配置或硬件固件。
5. **原运行时缺陷。** 本次临时使用之前修复并板测的 manager 去重与 ZOCL 引用平衡版本进行扩大复验；其来源、源码补丁和许可证仍在原封存附件。测试结束恢复原二进制，因此原版缺陷并未因本轮测试而永久消失。

## 保留的问题与未完成项

- 新增 544 条不同时间戳的 overlay 属性警告原样保存；它们与实际触发的目标引用错误分开统计，没有通过改变严重级别或厂商规则消除。
- 已有 /boot 重复 fstab 条目未修改。旧 DRC/约束/时序审阅限制不因运行时复验通过而自动通过。
- 观察时长有限；长期使用、异常掉电、热拔插竞态和永久开机顺序/重启验收仍未覆盖。
- 自动控制器异常时尝试正常恢复；若 manager 死亡且 overlay 仍活动，严格检查会停止，需要另行诊断，不 force 卸载或盲目重试。
- 板端 wall clock 是旧日期；未调整时钟。主机采集时刻独立记录，观察时长使用单调时钟。
- PWM、自研运动 IP 和完整 AURA/参赛项目并未因此全部完成。M3 本轮复核限于 DPU 路线和同图结果。

## 输入版本与哈希

| 输入 | 固定值 |
|---|---|
| DFX source | bc06691eb35d7f0acb7c2508b6d050d77b0264a0 |
| XRT source | 43926231f7183688add2dccfd391b36a1f000bea |
| Linux source | 19984dd147fa7fbb7cb14b17400263ad0925c189 |
| 本次 manager SHA-256 | db9c25f09f1178177884b1114c57f32c076f1e7f9cdd0d12b7a896039038a46c |
| 本次 ZOCL SHA-256 | 5cef5e0eba083419b3ece6fd4829a9f3112e3f0daaee513e1617d60ed1f7f412 |
| 修复 ZOCL srcversion | 9BDC942A6014BCCBD1DCB78 |
| 恢复原 ZOCL srcversion | 0991D1B457855C8987936E6 |
| 新复验包 SHA-256 | 6138c1a576eec27a8c8bd550ada566ea4c160be0e40a47a51188567714ae0f38 |
| 完整 manager log SHA-256 | 135a3f4b58f729fd8065300640f6f3a48d789be56fcd32e1d8c2afd01f2cd7ae |
| 完整证据归档 SHA-256 | 3384ec011a254ddb2b6baaf489d23ade09844c385e5363af495625f6ccb3b3b0 |

## 证据路径

- 主机本轮目录：/home/ghmd/kv260-runtime-live-20261003-retry1。
- 板端独立工作目录：/home/root/kv260-runtime-live-20261003T085031Z。
- 板端原文件恢复点：baseline/files/ 原路径树；26 项逐份复制、哈希一致，原路径没有被覆盖。
- board_evidence.tar.xz：522,748 B，3,480 个成员，全部回读校验。
- board_evidence/：完整 stdout/stderr、命令元数据、DPU query、kernel/snapshot、SIGINT 后 manager log、controller 与恢复记录。
- analysis/summary.json、commands.json、samples.csv、metrics.csv：独立逐输出/逐阶段审阅，overall_pass=true、baseline_restored=true、issues=0。
- evidence/final-state.guard.output：控制器结束后的独立实时核对。
- agent_review/：日志比较补丁、真实边界 fixture、聚合脚本及独立审阅。
- 原失败目录 /home/ghmd/kv260-runtime-live-20261003 和其 LIVE_REVIEW_REPORT.md/28 成员归档保留。
- 原源码附件 /home/ghmd/kv260-runtime-submission-20261002 的 1,052 项封存索引核对通过，没有改写。

## 后续顺序

先依据本轮结果准备可恢复的开机加载方案，明确修复驱动、manager 与默认 app 的顺序，再做单独重启验收。随后推进 PWM 与自研运动 IP 的设计、引脚/电平审阅和新的硬件构建。当前板卡仍运行原官方基线；本轮不执行永久切换或烧录。
