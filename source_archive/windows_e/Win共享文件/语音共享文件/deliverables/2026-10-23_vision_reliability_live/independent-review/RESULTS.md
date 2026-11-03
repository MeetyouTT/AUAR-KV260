# 独立审查结果

结论：本次候选在明确的释放、保护、worker锁定与可观测性范围内，**23项独立离线检查全部通过，未发现新增阻断项**。不等于YuNet长尾根因修复、未知在途native作业的全局隔离、SFace自动恢复或实板验收完成。

实际执行：

```sh
python3 run_tests.py test_release_audit -v
```

现有离线Vitis-AI Docker镜像，网络关闭，挂载只读，测试均用内存对象、fake clock/fake detector，未访问板卡/UART、真实DPU、录放音、身份库或生产服务。首轮15项通过（release-audit-tests-r1.log）；第二轮补查后23项通过，0.009秒（release-audit-tests-r2.log）。没有修改业务源，只写独立测试与本目录报告。

覆盖的关键行为：

- begin/finish/error/snapshot辅助Exception及BaseException不能保留执行权；native/primary业务自身BaseException仍按原异常传播，资源释放。
- 未准入调用不清理另一个owner；waiting_primary保留优先；准入内begin延迟仍触发原30ms，guard仍按原5ms保护。
- 已完成硬超限进入COOLDOWN且故障计数在释放前生效；guard越界及未证明native完成仍锁定，不出现自动native重投；已知native_not_submitted撤回不误算native故障。
- 用真实线程阻塞finish或snapshot，YOLO仍能进入；旧finalizer返回不会清掉已经进入的YOLO owner。
- 用真实OptionalDiagnostics验证partial begin异常的TLS清理；旧trace迟到finish/discard不清新trace；lease边界顺序及diagnostic_snapshot_atomic_with_schedule=false明确保留。
- CPU fallback直接累计次数、失败数、耗时和原因，native分支不得被误调用。
- detector/factory故障后worker仍存活但ready=false/fault_latched，拒绝后续packet且不重复创建/调用detector；正常close后也不伪ready。

审查中提出的正常关闭ready残留问题，主任务已在worker finally清ready，并将worker故障捕获扩至BaseException；本副任务未代改源，关闭反例已通过。

边界与部署要求：

1. 原occupancy终点仍是释放前保护决策点，返回值已用occupancy_scope明示；诊断finish迁出减少关键区工作，但不能把变化解释成根因消失或严格提速。
2. 诊断snapshot与scheduler副本为非原子，部署检查不应把两个子快照的累计计数强制当同一时刻。三模型功能、故障计数/代次和源SHA须另行确认。
3. 本轮worker锁定保证故障kind不会自动重投。候选仍保留原primary异常处理语义，不能据此宣称任意VART异常已证明硬件结束或整owner已隔离。不要用超时直接回收可能仍在途的资源。
4. 23项测试没有产生真实native作业。上板的短窗口和故障恢复/回退审查仍由主任务执行，不能用此日志替代。

审查后观测的源SHA见reviewed-source-manifest.json；正式封包前主任务应与其最终源清单比较，后续源若再改变需评估受影响测试。
