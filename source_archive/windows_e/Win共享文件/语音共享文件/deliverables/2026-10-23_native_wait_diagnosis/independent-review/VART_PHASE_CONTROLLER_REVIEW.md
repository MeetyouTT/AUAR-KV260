# 现有 SFace 线程的单次有界 VART 分段观测审查

**实际业务观测被前置ready检查拒绝，没有执行60秒采样，也没有创建生产探针。** 静态审查与9项本地检查通过，不能替代这一实际结果。当前SFace已保护停用，根代理没有通过再次重启绕过计数或继续强行采样；后续应先审查受限恢复的可用性语义。本报告不是根因已解决或业务性能验收。

审查对象 `../trace_vart.py` SHA256 `0b69843e8b7c38fa7af5113be28c95dd797fecca87696386c3f86aec4a839523`。复用无seek tracefs helper SHA `9c8f8702f68a4d24c76be06e1c1ad575d0c53a77e353a78b8bb89b15e1e658e4`。只读本机源码、精确ELF及fake测试，没有接板。

| 检查 | 结论 |
|---|---|
| cleanup别名 | `h.cleanup`的全局引用来自模块h。重绑其SOURCE/ROOT/GROUP/INSTANCE/GUARD后，ownership检查和清理写向新的vart-phase命名空间。fake验证保留旧fixture的group及ownership文件。 |
| 对象绑定 | boot、camera PID588727、process/thread birth、unit SHA、library SHA、maps的path/inode、四opcode与单owner检查均在创建探针前验证，结束再核对；初始断言失败时尚无探针。 |
| 位点 | 0x10a04=`aa1403e0`、0x10a10=`aa0003f6`、0x10a1c=`aa1303e0`、0x10a24=`a94ad7f3`，已再次逐字匹配本地精确vart.so。均为正常路径非分支指令。 |
| 全局/临时修改 | 用O_APPEND单次命令注册自身唯一group，不截断全局定义；filter/clock/buffer/trace均在新instance内。结束要求自身events和instance清空、全局设置/定义保持、guard inactive。 |
| 中断边界 | ownership先原子保存，独立75s清理timer active后才创建/注册；正常或Python异常走finally。SIGTERM/SIGKILL或health读取阻塞依赖独立timer；worker本身另有90s RuntimeMaxSec。staging源与两个固定helper必须保持原件。 |
| 线程与解析 | `common_pid`选择记录的TID；解析又断言TID一致。四相位完整且时间非倒退才生成cycle，缺相位不拼接成假cycle；支持6或9位小数并保留显示位数，实际内核已知量化1µs。 |
| 成本 | 完整controller CPU从run入口计至cleanup/stopguard后；明确不含child systemctl CPU和最后JSON序列化。另保留60秒环数据。≤2%门槛与fixture的目标trap成本是不同指标，未相加冒充整板CPU。 |
| 业务保护 | `common_pid`只过滤记录，同ELF的YOLO等线程仍可能承受trap开销；代码scope已说明。新optional fault/gap/primary overrun/worker与owner状态独立记录，measurement通过不代替业务无故障。 |

`incomplete_phase_sequences`会把起点孤立的return相位分别计数，不能等同未完整“调用个数”。窗口边界出现partial可以接受；结果归因只能使用明确完整的cycles，内部缺相位/异常或注册范围差异应按实际报告，不因至少一条cycle就宣称60秒所有SFace调用均被完整覆盖。loss stats缺失会失败，三类丢事件字段均须为0。

native区间包括调用前三条参数/虚表准备指令与probe；Restore区间包括一次参数move、PLT/RestoreThread调用、调度/GIL等待及probe。它们是带观测开销的wall时间，均不是DPU硬件busy时间。若某次长尾落在Restore区间，可缩小到GIL重获调用附近；仍不能用纯wall数值分离CPU排队、kernel调度和仪器自身扰动。没有捕获故障也不证明罕见长尾已经修复。

实际本地验证：`python3 independent-review/test_vart_phase_review.py` **9项通过，0.008s**，源码SHA与上述一致。测试直接编译执行原 `parse_trace` 的AST，覆盖正常数字区间、同量化时间、group前缀、跨TID拒绝、缺相位/边界partial、倒退/超9位时间拒绝；另核对四位点原始字和模块重绑cleanup。未重复此前已过的采样器/fixture测试，未将本地结果算作生产板端通过。

本次执行后只需补齐实际结果和清理证据，按原限定收尾；不根据短窗自动扩大为常驻探针、新owner、阈值放宽或反复重启。

## 实际预检拒绝

根代理保存的 `../vart-phase-result.json` 与 `../failures/vart_phase_preflight_r1/` 显示：相同0b69843e…源码的worker在 `run()` 第72行断言 `before['feature_inference']['ready'] and before['worker_alive']` 失败。主任务确认该时点为SFace ready=false。断言位于ownership/report保存、独立timer arm以及探针注册之前，所以该轮 **observation_started=false、production_probes_created=false、report_missing=true、unit_state=failed**。没有完整cycles、60秒观测窗口或真实VART位点成本结果；不能把fixture通过或本地解析测试写成本轮业务采样通过。启动journal与failed状态已另存，本代理只读核对，没有连接板卡或发恢复操作。

最新保存的 `../event-610-raw.json` 解释了该ready状态：同camera588727，SFace累计102次完成后出现event610，occupancy39.891329ms，hardcap=1/guard=0、native_completed=1/status0/body_failed=0；execute标记39.040631ms而线程CPU0.558185ms，wait0.093581ms。该事件发生时生产UProbe尚未启用；**没有runqueue测量**，不能挪用event5788的Q=0归因。它符合下方“completed hardcap-only”的未来受限恢复候选条件，但现役SFace没有这条自动恢复实现，本轮没有解除停用或重启。YuNet另一个event521是guard-only，按原策略继续LATCHED，两者不能混用分流。

`../cleanup-audit.json`只读确认本轮全部自有uprobe定义/instance剩余0，所有相关cleanup timer inactive；业务采样worker维持failed退出状态。这是清理通过，**不是观测通过**。

## 下一步 SFace 受限恢复的最小源码审查要点（尚未实现）

现役 `dpu_sface.py` 通过availability ready门在进入feature前拒绝disabled任务；scheduler的恢复入口、native完成标记和primary失败通知仅处理YuNet。只添加policy对象或解除disabled不足以闭环。应复用现有YuNet安全语义，保留独立任务状态，逐项检查下面合同，不先扩大架构。

| 条件 | 应审查的分流 |
|---|---|
| 同一lease内明确wait返回status0，body无异常，hardcap=true且guard=false，owner未fenced | 进入10s COOLDOWN；满足YOLO新完成、last_primary≤0.5s、故障后primary_overruns未新增及普通准入时才允许真实请求probe。 |
| guard-only（即使总占用不足30ms）或hardcap+guard | LATCHED，不自动恢复；不能因native status0或只越少量guard就当hardcap-only。 |
| status非0、异常导致完成未知、owner fenced | 不自动probe；保留任务停用和现有全owner fencing规则，不用“completed计数有增加”替代这一次lease的完成证明。 |
| 未提交、source过期、slot拒绝、等待超时 | 保持Deferred；不算native成功，不消耗尚未真正准入的恢复轮数，也不伪造故障或UNKNOWN身份。 |
| probation正常native完成且未越hardcap/guard | 只累积真实成功；达到3次才RUNNING。probe期间再次故障按同一分流重新冷却或锁定，预算仍受限。 |

最小代码审查范围：

1. **完成证明在正确位置。** SFace的成功标记应与现YuNet `_confirm_completed()`相同：位于调度slot内、`wait` status0后、无异常返回的路径，并验证kind/调用线程/当前lease。现在SFace `self.completed += 1`发生在slot结束及输出转换之后，不能拿它驱动finally中的恢复策略；诊断开关关闭也必须可确认，fresh=false或提前撤回不能标记成功。
2. **probe通路与业务ready分开。** 当前`feature()`入口 `not self.availability()['ready']`会将disabled任务永远挡在恢复准入前。需要允许满足recovery_due且新鲜的真实请求进入probe，而health/UI在COOLDOWN与PROBATION仍明确degraded/unready；登记、照片/结果缓存消费保持禁止。前两次probe向量不能被当作正常KNOWN/UNKNOWN发布；第三次成功后才可按现有INT8域和TTL发布。不使用CPU/Windows单向量回退。
3. **3次成功是实际已准入native成功。** 拒绝、取消、TTL失效、没有人脸、缓存命中都不算probe成功；probe原样经过YOLO优先、普通deadline准入、30ms hardcap/5ms guard，不制造空推理来凑3次。slot之间可以正常让给YOLO。
4. **2轮/600s预算与原YuNet兼容。** 沿用10s冷却、滚动600s最多2次实际恢复轮、每轮3次成功；轮数在真实首次probe准入时计入，后续成功不清历史attempt_times/faults/overruns。SFace和YuNet应持各自policy实例/计数，不共享可变状态；不能因新增SFace恢复把已LATCHED的YuNet重置，也不能把原YuNet2轮预算悄悄改成新口径。预算耗尽保持LATCHED，时间流逝本身不隐式解锁。
5. **primary与owner保护覆盖两任务。** primary在probation期间失败时，应对各自PROBATION策略发出通知并停用相应任务；不能仍只通知YuNet。owner_fenced是共享安全状态，任何任务恢复都不能清除它。所有policy调用继续受原condition保护，不添第二owner。
6. **计数和可见性不被恢复抹去。** fault/overrun/native completed/deferred/recoveries保持单调；只重置当前轮probe_successes等瞬时状态。health暴露SFace phase/reason/cooldown/attempts/probe_successes与recovery_required，沿现IdentityService feature状态透传；不将PROBATION的临时disabled=false误报业务ready。部署或进程更替另标统计窗口，不能拿重启后0计数宣称旧故障消失。
7. **必要离线反例。** 覆盖status0+hardcap-only、status0+guard-only、both、非0/未知完成、slot/TTL取消不计成功；3次真实成功恢复、第二轮失败及600s边界/预算耗尽；primary失败、owner fencing、health/IdentityService拒绝登记与不发布UNKNOWN；同时断言现YuNet状态与既有测试行为保持。
8. **既有停用状态的迁移不能变相解锁。** 若候选面对已有disabled任务，必须用可核验的同lease fault信息及计数建立phase；缺完成证明、guard信息或预算历史时保守LATCHED，不能新建policy默认RUNNING就覆盖原保护。当前最新SFace故障若属于guard-only/both，同YuNet现策略应继续LATCHED；新增hardcap-only恢复功能本身不授权将其改类或靠重启恢复。

依据为现役导出 `active_source/camera/aura/board/vision/{dpu_sface,dpu_vision_schedule,dpu_vision_runtime,dpu_yunet}.py`，及同一可靠性候选的 `candidate/aura/board/vision/dpu_recovery_policy.py`（该文件未单独出现在partial active_source导出，故作为既有策略参考，不能冒充本轮重新读回的板端原件）。以上仅为后续最小审查合同，没有编写恢复补丁、部署、接板或执行新测试。本轮第二路在此结束。
