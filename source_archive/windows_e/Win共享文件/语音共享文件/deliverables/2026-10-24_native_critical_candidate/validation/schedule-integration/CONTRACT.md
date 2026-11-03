# 原生调度 ABI v2 接口合同（本机候选，未部署）

正式定义见`native_bridge.h`，实际sizeof由`aura_native_*_size`及`test_abi_sizes`读回，不能靠猜测硬编码。保留原生30ms hardcap/5ms guard；`wait_optional`的100ms只是不持执行权的通知等待，VART在途仍等待确认、未知完成fence，不能取消在途作业。

- `AuraNativeReport`原有四时钟点保留，ABI=2；追加business_ready/result_fresh/recovery_phase/reserved与uint64 result_token。
- `AuraNativeState`有active_task（0/1/2，3=none）、fence_reason、quiesced、seed_loaded，primary_calls/primary_period_overruns/last_primary_ns，以及admissions/overruns/completed/native_failures/not_submitted[3]、pending_result_tokens[3]、两个恢复快照。
- `primary_calls`计所有有效参数、已结束的主任务周期，包括在入口或等待中因截止时间/源TTL而未提交的周期；`admissions[0]`只计真实取得原生执行权的周期，`not_submitted[0]`还包含上述准入前拒绝。因此精确idle seed允许`admissions[0] <= primary_calls`与`not_submitted[0] <= primary_calls`，不能再假定二者都受真实lease次数约束。入口/等待迟到仍计`primary_period_overruns`，锁定PROBATION；源TTL过期但周期未迟到仅计未提交，不捏造周期超限。`last_primary_ns`只在已确认成功native后更新，不用拒绝充当健康推进。
- `AuraRecoveryState` phase=0 RUNNING/1 COOLDOWN/2 PROBATION/3 LATCHED；reason=0 none/1 unsafe_or_unknown_completion/2 recovery_budget_exhausted/3 completed_hardcap_only/4 primary_overrun_after_fault/5 primary_overrun_during_probation。enabled按任务独立配置。

## 先seed，再接管

生产Context的gate强制seed：`restore_seed(ctx,&seed)`首次idle、没有adopt/runner前调用。再次导入、使用后导入、当前boot不符、非法计数/phase/时间/队列均拒绝，不能重建Context清故障或恢复预算。源PID/birth/manifest为来源元数据，外层负责验证精确、版本化、静止来源。source_pid/birth均0只允许全零clean初始状态，外层只在已验证fresh启动使用，不能拿来覆盖旧故障。

精确seed必须含完整两个attempt_times与故障primary基线。旧health不足以重建时，只允许**disabled且LATCHED**的`history_opaque=1`：已知faults/attempts/recoveries/probe计数保留；未知时间/基线字段用0作显式unknown，attempt_count/attempt_times必须0，health计数另放opaque_attempt_count。此分支不调用恢复policy、不准自动恢复、不把0队列当已证明没有预算。RUNNING/COOLDOWN/PROBATION缺精确历史须拒绝，不能伪造。

`checkpoint(ctx,current_manifest_sha,&seed)`仅idle且无pending结果时导出完整Native状态，并将旧gate设quiesced，禁止导出后计数继续变化。source PID/birth/currentboot由C层采集。外层先停供给/worker，成功导出后才关闭runner/Context。不会解除LATCHED或fence。Outcome新增9=seed_required、10=quiesced。

## post-release确认与业务发布

正常RUNNING成功结果token=0；result_fresh指native释放决策时fresh，Python还必须逐次复查TTL。PROBATION成功native生成一次token，**此时不计probe成功**：

1. 释放原生gate，返回已确认的原始输出，SFace第3轮也必须拿到原始输出以便后续使用；business_ready=false不等于未执行，不能混成"没人脸"。
2. Python重新得到GIL、复查源TTL后调用`ack_result(ctx,task,token,usable,&ack)`。C侧再次按当前clock<源expires确认，单次消费。返回0=消费、1=过期/重放/不匹配，-2=fenced，-1=参数错误。ACK结果有accepted/business_ready/result_fresh/recovery_phase/token。
3. SFace前2个合格ACK仍PROBATION/不可发布；第3个才RUNNING、recoveries+1并允许业务使用。过期/未提交/usable=false不凑probe。native completed与特征可发布分别计数。YuNet probation可返回有效检测结果，但恢复计数同样须ACK后推进。

同任务pending token时新准入拒绝，不能覆盖token；YOLO及另一个任务可正常使用已释放gate。pending到TTL自动作废且不计成功，晚ACK/重放不能推进新轮或新Context。release→ACK期间发生primary overrun会锁定PROBATION，旧ACK不能复活。unknown native仅fence，ACK不能解除。关闭runner遇未过期pending拒绝；过期pending可显式丢弃后正常关闭；Context不能带pending关闭。

`wait_optional(ctx,task,until_ns)`最多等待min(until,now+100ms)，不持active，由native completion/announce/ACK通知；返回0只是机会，真正准入/TTL/主任务优先仍在execute内重查，1为超时/禁用/pending/seed-required，-2 fence，-1非法。

checkpoint唤醒上述等待者时，等待循环先重查quiesced并返回1，不能在sealed来源上再宣告准入机会。100ms不用于VART wait或改写30ms hardcap，已提交作业仍必须确认完成。

旧Python schedule不可继续持另一把跨native调用的active锁。所有模型、模板域、阈值和输出解码保持原版；本机fake测试、头文件交叉编译均不能当作真实模型等价、精度或板级长稳验收。
