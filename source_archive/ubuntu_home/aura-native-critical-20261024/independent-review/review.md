# 原生执行权候选独立审查

**最新修订复核：两个源级反例在修订快照 `4bbe0bf51a67ee3a1480bde020939f8d967483b2ae5dad5ae06492684038233a` 中已修。** 独立新增4组正向故障注入通过，主代理原8组也由本代理重新编译运行通过；其中上层迟归不阻YOLO的性质保持。当前可继续准备native桥的编译候选；真实模型接线、生命周期和恢复状态合同仍未完成，不能直接部署或称根治。以下P0表和原反例保留为初始快照的历史发现。

**原型支持“native结束后释放执行权，不等上层调用者返回”的方向，但当前审查快照存在两项确定性反例，尚不能用于真实三模型接入或宣称长尾根治。** 本代理只做Ubuntu本地读源码、编译和假时钟检查，没有连接板卡、调用VART、创建DPU owner或修改主代理源码。

审查快照`reviewed_native_lease.hpp` SHA256 `f437176d1a5dc8cf3fb14dceb59d71ee6e16cfa0f1725be9303c02d37f346fb6`。它是初始8组候选的字节副本；后续主代理修订应单独核验，不能用本报告对修订版自动下结论。

| 项目 | 当前结论与依据 | 真实接入前要求 |
|---|---|---|
| P0：准入窗口过期仍提交 | 当前第92行用第一次clock检查剩余≥35ms，第100行第二次clock仅检查source TTL；两者之间虚拟推进40ms后，仍调用native一次，起点1.040s已超过guard1.031s，事后才guard=true。 | 最终共同采样同时检查TTL与准入余量；原生提交前再检查TTL、当前primary等待/截止。未提交撤回不得冒充native成功。 |
| P0：执行权先置位、起点后采样 | 当前第105行active=true，第107行才start_ns。起点采样处虚拟延迟20ms，native再20ms，真实模拟gate不可用40ms，却记录20ms/hardcap=false。 | 计时起点不得晚于执行权取得；保留准入/提交/完成/释放前后的端点及不确定区间，不能靠移边界通过。 |
| 主任务优先 | mutex保护primary_waiting，optional遇pending primary先拒绝，等待primary在条件变量上释放mutex。现原型8组中已覆盖这一方向。 | 现役只有一个YOLO调用线程；若未来允许多个primary，须另定义顺序和截止，当前不是FIFO队列。 |
| 当前截止更新 | optional结束将准入时guard与最新next_primary减guard取min，这能看到运行期间更早的primary更新。 | announce参数、deadline范围/时钟域应由稳定ABI校验；不能从Python旧锁/旧deadline读回覆盖原生状态。 |
| 完成未知 | callback抛异常或submitted=true但完成/status不符会fence，全新primary也被拒绝。此方向满足同owner保守保护。 | bridge必须在真正提交前后准确设置submitted/completed/status；完成未知时禁止销毁可能在途的runner、buffer或启动另一个owner。 |
| 上层迟归 | execute在原生回调完成后、返回调用者前clear active并unlock；调用者之后被人为暂停不再占该gate。 | 这是C++调用者延迟的隔离测试，不是Python GIL压力测试。真实C ABI必须直接走编译的native回调，不能用Python/ctypes回调。 |
| fork | PID在mutex之前检查，fork子进程拒绝使用父gate，避免碰继承锁；现原型有子进程测试。 | 同样约束所有create/close/snapshot/recovery API；不要让原始gate指针跨进程或跨重载DSO复用。 |
| 生命周期 | 当前没有close/closing/in-flight引用计数或runner/buffer所有权协议，类析构默认销毁mutex。 | gate active=false只代表设备执行权释放，不代表execute函数/调用者已离开。close必须拒绝新请求，等待所有C ABI引用安全退出；所有模型handle共同持有gate/owner引用。 |
| 计时语义 | release_decision_ns是保护决策点，after_unlock_ns是后观测点。普通Linux仍可在两者之间抢占，原型未实现硬实时保证。 | 两端都保留，区间不可直接叫纯DPUbusy或精确unlock时刻；CPU排队仍需实测，C++本身不能消除它。 |
| 恢复/可用性 | 原型只会disabled/fenced，没有当前SFace/YuNet恢复、fault历史和业务ready。 | 10s/600s最多2轮/3次探测、SFace前两Deferred、primary失败、TTL usability、重启交接和counter来源均须迁移。不能只凭Outcome::completed发布身份。 |

两个确定性反例由`test_review_counterexamples.cpp`对本字节快照实际编译运行，结果`counterexamples-result.json`：stale_admission_native_calls=1；start_meter_recorded_ns=20000000，simulated_actual_gate_hold_ns=40000000，hardcap_recorded=false。它们是软件源级反例，不是实板调度测量。

## 同一原生gate接三模型的最小合同

1. **唯一权威仲裁。** 当前camera/DpuYoloX已经持`/run/aura-person-dpu.lock`，继续由该owner创建/保有模型。三个模型wrapper共享同一个native gate实例、PID与句柄；不能各桥各建static gate或另起DPU进程。纯编译/link检查不调用任何model create或VART runner factory。
2. **消除双重仲裁。** Python现`primary()`等待`self.active`、`optional()`也握同一逻辑执行权直到Python返回。如果保留这层阻塞，native已经释放也没用。新Python层只能代理native权威状态/结果，不能继续握旧Python lease跨原生调用阻塞YOLO。
3. **原生调用完整闭环。** 编译的C++路径覆盖真正execute、wait、native完成判定、保护与释放，日志/SQL/健康复制/输出反量化放释放外。ctypes必须使用释放GIL的CDLL调用；没有Python CFUNCTYPE/pre_execute回调进入关键段。业务取消/TTL信息转成原生可检查的值/令牌，不等待Python执行撤回逻辑。
4. **YOLO语义保持。** 当前`yolox_bridge.cpp`通过vitis model->run处理letterbox/量化/DPU/解码/NMS整体，首版可继续把该回调视为primary native path，不能把其全部时间命名为DPU硬件时间。行数、COCO person过滤、原坐标/NMS仍保持；未知异常的提交完成状态必须能保守表示。
5. **可选模型ABI保持。** YuNet320x320四头和SFace112x112/128维必须按实际Runner port顺序验证names/dims/dtype/fix_point；XIR集合不能替代VART端口顺序。preprocess/encode/dequantize、xmodel SHA/指纹、model_id和INT8模板空间保持。先用相同输入核对原始INT8输出及最终结果，不能只测耗时。
6. **状态与结果分别证明。** 原生wait status0才证明完成；SFace native完成时也核对源TTL，过期不记probe成功。COOLDOWN/PROBATION业务ready=false，前两probe仍Deferred，不进入store.match/sampling.offer/登记。Outcome completed不代表业务结果可发布；guard/hardcap/owner fence还要结合policy。
7. **完整恢复合同。** 两policy各自实例、10s冷却/2轮600s/3次真实成功；guard或未知完成锁定，未提交/拒绝/过期不凑成功或消费不存在的native尝试；YOLO probation失败通知覆盖两任务。旧fault/attempt/recovery与boot来源不得因新实例默认RUNNING清掉，handoff要在任何模型执行前应用。
8. **关闭与在途资源。** 每次调用固定持有其runner、graph、buffer、gate和owner生命周期。gate释放后，等待Python取结果的buffer仍须独立保活，不能复用成下一作业输出。close和fork不允许UAF、旧PID句柄、未知完成后第二owner；destroy API需要明确busy/closing状态而非直接delete。
9. **共同时间坐标。** Python source_mono_ms、native deadline/TTL/guard和报告应使用同一已核验单调时钟与单位；不能仅因std::steady_clock“单调”就默认其epoch与Python一致。target上对CLOCK_MONOTONIC映射及ms/ns边界做一次确定核验，验证uint64范围/减法/chrono转换边界。
10. **验收按实际范围。** 先原生故障/竞争隔离与模型同输入输出，再同boot单owner短实流、三模型真人输入/GUI音频负载、故障恢复/未知完成、随后正常业务累积长稳与实际冷启。不得把8组fake callback通过、无故障短窗或模型ready当作完整接入/根治。CPU runnable排队仍大时，专门资源配置应单变量验证，保留原30ms/5ms。

目前结论是“可继续修订并准备native桥的编译候选”；不是“可直接部署当前gate”。主代理已收到两项阻断，并表示将修订最终准入采样/计时起点和提交前复核。没有因此要求用户新增授权或现场输入。

## 修订版实际复测

`corrected_native_lease.hpp`是修订主文件的字节副本，上述4bbe0b…SHA固定。`test_review_regressions.cpp`以相同假时钟机制实际编译执行，`corrected-regressions-result.json`为4项通过：

- 最后锁内同一采样复查source TTL与35ms最小余量，模拟40ms换出后准入直接拒绝，admission/native均0。
- 已取得gate后、callback前模拟40ms换出，会在提交前撤回，native0；已有40ms gate占用仍保留hardcap/guard记录，不伪造native完成，gate释放且owner不fence。
- active期间模拟20ms停顿再20ms工作，start保守保留，记录40ms且hardcap=true，旧起点漏计反例消失。
- submitted=false但completed=true等矛盾完成标志会fence，不能被作为未提交正常返回。

另重新编译运行主代理的`test_native_lease.cpp`，`parent-tests-rerun-result.json`为8项通过，验证基础并发/迟归行为未被这次修正破坏。本次只运行与修订有关的本地检查，没有因此再接板或重复任何真实模型推理。

原生恢复接线还有一个必须明确的接口：本原型没有disabled解除/恢复permit/seed导入API，不能通过销毁重建gate来模拟恢复或清fault。若恢复policy仍由Python管理，原生端至少要以当前fault代次、完成证明、guard分类、primary新完成/未超期状态及有限预算原子核验permit；更完整的做法是把同一有限策略也放到原生权威状态中。所有SFace业务ready/前两probe丢弃仍由返回的权威状态驱动，不能由“callback返回status0”直接越过。
