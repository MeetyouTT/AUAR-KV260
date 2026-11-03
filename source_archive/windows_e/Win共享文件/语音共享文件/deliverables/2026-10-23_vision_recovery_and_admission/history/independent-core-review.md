# SFace 恢复独立故障注入结果

**核心恢复16项独立注入通过；部署前仍需处理coldboot启动行为。** 本代理实际运行Docker测试，使用候选的真实`PinnedRunner.execute_encoded`、`DpuSFace`与`DpuVisionSchedule`，仅VART执行/状态为合成，未加载真实VART、连接板卡或提交DPU任务。没有修改根代理源文件。

执行：`python3 run_tests.py test_sface_recovery_review -v`。最终`core-injection-r2.log`：**16 tests / 0.014s / OK**。

覆盖：

- completed/status0的hardcap-only进入冷却，guard-only即使不足30ms以及both均LATCHED；非0状态/原生异常沿原NativeExecutionError触发owner fencing，未知完成不自动恢复。
- 三次有效probe前两次抛Deferred且availability=false，第三次才返回；通过真实IdentityService.process验证前两次不生成result、不match、不登记/采样，第三次正常发布。
- TTL入场前/slot后提交前过期不消费恢复attempt；native执行后TTL过期保留completed证明但不增加probe_successes。slot拒绝不消费attempt。
- probation期间primary超期锁定，owner fence阻断恢复；两轮恢复失败耗尽预算；SFace恢复前后旧YuNet的LATCHED、faults、attempt_times及job计数逐项保持。
- 合成handoff承接feature与primary坐标、旧YuNet锁定后，三个SFace native成功可进入RUNNING，旧故障数保持。

首轮`core-injection-r1.log`保留：有一个测试fixture直接将numpy float向量交IdentityService，遗漏真实CameraFaceExtractor转换为Python float的行为，导致第三次发布断言失败；纠正fixture后通过。首轮还因导入/继承测试类重复执行已有handoff测试，最终独立组已去重为16项。该失败不作为产品缺陷、也不删除或伪称首轮全过。

## 已查源及限制

adapter slot内正常yield返回后才调用native_completed，PinnedRunner在wait status0之后才退出slot，异常/取消不抵达该marker；`usable`独立标记源TTL，完成证明与恢复成功没有混为一谈。availability再检查policy phase，前两probe向量经Deferred丢弃；IdentityService与CameraFaceExtractor字节未改。

handoff限定同boot、两disabled、完整故障证据和旧YuNet零恢复轮历史；不同/未知历史拒绝，不重置成默认RUNNING。继承primary累计且_last_primary=None，需新YOLO完成才能probe。首次marker原子独占/写入fsync后应用；重复同boot启动SFace锁定，不能重放旧seed清恢复预算。当前单次限定seed语义与通用持续检查点不同，不能宣称已具备跨任意进程崩溃完整恢复。

## 快速部署/回退审查发现

`protected_rollback_entry.py`用旧源码构建scheduler并导入保护seed、强制两个optional保持disabled，避免回退旧代码直接解锁；源码不覆写parent。新GUI-only context通过替换unit SHA创建独立controller，不修改原66上下文，方向正确。

**当时读到的coldboot行为尚未达到根代理的发布目标：** `ui_camera_service.py`直接调用restore_protection，seed boot不匹配会ValueError退出整个run；`protected_rollback_entry.py`也在boot不符直接raise。若目标是“coldboot仅optional failclosed、YOLO仍启动”，发布前需添加专门hold-only路径并验证。此发现已即时发给根代理；本报告不追认随后尚未审查的修正。核心16项通过不等同部署可接受。

seed使用非原子health中schedule与diag部分；当前两optional均已disabled，故没有新optional作业竞争，但仍应在停止前核对最新owner/故障/计数，不能无条件当成原子进程退出快照。新primary故障相对于旧SFace故障的完整历史若缺失，应明确继承的是快照基线，不能声称已证明从旧故障时刻起没有YOLO新增超期。

不在本轮独立测试结论内：板端真实恢复、同输入收益、长尾根因、长稳、陌生人/多人精度、实际回退和coldboot。后续根代理的实板隔离与发布结果须单独记载，不能把本地fake VART通过写成真实推理通过。
