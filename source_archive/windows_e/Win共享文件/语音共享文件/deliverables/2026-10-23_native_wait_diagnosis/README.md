# DPU 等待长尾：本轮结果与当前状态

已取得并核验板端实际 VART 二进制的 GIL 路径；一次真实 SFace 超限取得了外部运行队列计数包围窗。**尚未修好偶发长尾。** 只做了一次有证据保留的同版本可用性恢复，后续 YuNet 因新的 guard 越界再次退 CPU，没有继续重启来消除计数。

## 当前实板状态

以 `final-audit.json` 为准：boot `7924ac9f-311d-4fcd-98be-57bf023cf1aa`，camera588727 / GUI588755 / Xserver1077，camera unit `29786434…`、可靠性修复与隐藏预览修复保持。**YOLO仍DPU约9.92Hz；YuNet因guard越界退CPU，SFace又发生39.891329ms硬超限，现保护停用、ready=false。** SFace累计102次native完成、1次超限、83次deferred；没有混入FP32特征或新身份结果。新进程gap0、worker/诊断错误0、USB/音频告警新增0，单owner与GUI-only回退只读核对通过；GUI175份Python源、身份配置和新旧库SHA不变，监听关闭保持。早先SFace86次/ready=true见 `before-sface-second-fault-audit.json`，已不是最新状态。

`final-audit.passed=false` 表示当前没有满足“三模型均在DPU”的可用性条件，不表示源校验或回退检查失败。本轮一次相机及GUI同版本重启使进程计数重新开始；旧camera499773的2次YuNet故障、1次SFace故障、gap1保存在 `recovery-result.json.before`，不能与新进程计数拼成零故障。

## 已确认的证据

1. **精确绑定释放并重新获取GIL。** 实际 `vart.so` SHA `dc6bff9be31b8dc349a72489e06237f8503175805d042025558694823f61de34`，194720字节，BuildID `e359176b9761d3035b0301d4ec6c48de9a0af577`。已追踪 `execute_async` 方法名→pybind回调→`PyEval_SaveThread`→runner虚调用→`PyEval_RestoreThread`；不是只检查符号存在。故“再套一层释放GIL”缺乏依据；重获GIL或原生内部阻塞仍可能导致长尾。见 `independent-review/EXACT_ELF_REVIEW.md`。
2. **SFace event5788：可观测CPU排队不是这次30ms的主要解释。** execute标记30.167721ms、线程CPU0.580727ms，native正常完成/status0。完整包围它的39.587666ms外部读取窗，runqueue计数两端均4060123226ns，差0。仍不能区分GIL、锁/驱动/设备等主动等待；标记也含绑定准备/返回工作。原始两条数字样本与身份绑定见 `event-5788-raw.json`。
3. **YuNet event521：21ms也会触发保护。** occupancy21.037480ms、hardcap=0、guard=1，trace收尾超过guard约0.183572ms，native正常完成/status0。准入→guard仅20.909669ms，20ms估计之外只有0.909669ms余量；当前策略对guard越界锁定保护。`event-521-analysis.json` 只证明30ms保守准入估计会拒绝这一机会，不证明新策略已实施或吞吐改善。
4. **恢复后SFace event610：39.89ms硬超限，未越guard。** execute标记39.040631ms/线程CPU0.558185ms，wait0.093581ms；native完成/status0、guard约剩3.40ms、未fence owner。没有本次runqueue读数，不能套用event5788的Q=0。它在业务阶段probe预检前已停用；`event-610-raw.json` 保留，未再次纯重启来抹掉新进程故障。

## 两项测量方案未通过成本门槛

| 方案 | 实测 | 结论 |
|---|---|---|
| 缓存FD的原生schedstat完整适配器 | 平均线程CPU183.193µs，P99墙钟6.856249ms | 超过预声明平均CPU100µs/P99墙钟1ms；未接入生产 |
| 外部100Hz/60秒schedstat观察 | 实际91.84Hz、整进程4.9789%单核CPU | 超过2%成本门槛；已退出，不常驻 |

外部观察捕获了真实故障，但增加整板负载，不能把它称为无扰动故障率实验。上述成本均未从30ms保护时间中扣除。7项ARM隔离语义检查通过不等于成本通过；另有本机C解析/生命周期10项、适配器7项检查，初版fork问题及修订均保留。

## 已完成的可用性恢复与边界

`recover_availability.py` 固定boot/unit/源/argv与单owner，停止GUI确认PCM关闭后仅重启同版本相机一次，再启动同GUI；独立180秒guard、旧故障留存、GUI回退上下文按核验后的新PID衔接。短窗恢复后YuNet427次/SFace13次、0新超限；随后出现event521，**短窗通过没有升级为长期稳定通过**。没有改模型/阈值/身份模板/30ms/5ms/TTL，也未动运动/PL/Windows模型服务。

## 接下来按证据推进

四点UProbe的无DPU隔离检查已通过（`trace-isolated-result.json`）：同fixture/同BTI entry位置，修正Python append隐式seek后，500轮/2000事件完整、无丢失；平均额外线程CPU20.272040µs/四probe，P99完整CPU34.69µs、P99墙钟56.12µs，低于预设100µs/500µs成本门槛，文本实际量化1µs。前两失败和清理均保留；8项本机fake检查通过。

精确VART四阶段控制器 `trace_vart.py` 已实现，9项本机检查通过。**60秒业务采样未开始：预检发现SFace ready=false，早于guard/probe创建即拒绝。** `vart-phase-result.json` 和失败目录记录该结果；不能宣称取得native/GIL分段或成本通过。`cleanup-audit.json` 实板只读确认自身probe/instance均0，三个隔离guard与业务guard均inactive，预检worker failed/已退出。

下一步先实现SFace独立受限恢复，hardcap-only且status0可冷却/限次真实probe、业务ready与probe许可分开，3次合格后才发布身份；guard越界/未知完成仍锁定。然后才以已核定四个位点短采样区分native与GIL重获；common_pid过滤记录不消除YOLO等其他线程的trap开销，必须同时核对主周期增量。不会新建DPU owner或把墙钟当硬件忙时。

同时按独立候选处理准入余量；每次只改一项，保留故障计数及YOLO优先。当前没有部署准入余量或SFace受限恢复。陌生人/多人误认、同输入整板收益、冷启动及持续音视频业务仍未验收。

Tracefs方案参考 [Linux UProbe文档](https://docs.kernel.org/trace/uprobetracer.html) 和 [ftrace文档](https://docs.kernel.org/trace/ftrace.html)。它们说明接口；本板的具体支持、开销和清理须以实测为准。

本目录的ELF、全量反汇编和UART原始记录仅留本机；共享包只交付自有代码、哈希、数字证据与报告，不含权重、人脸图、模板向量、数据库或私有偏好内容。Windows接收/同步回执未代填。
