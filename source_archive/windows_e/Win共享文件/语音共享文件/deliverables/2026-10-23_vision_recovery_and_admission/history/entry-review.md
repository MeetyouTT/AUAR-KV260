# SFace 受限恢复：入口与保护交接初审

**IdentityService与CameraFaceExtractor已有可用的Deferred通路，原则上无须为探测改动这两个文件。** 当前阻挡探测的是DpuSFace.feature的availability ready门；scheduler的恢复生命周期仅处理YuNet。先补这两层及启动交接，避免扩大身份逻辑。本轮为源码初审，未修改实现、未接板或运行新测试。

初审基线来自 `aura-vision-reliability-20261023/candidate/aura`，不是新实现验收；上一轮合同见 `aura-native-wait-20261023/independent-review/VART_PHASE_CONTROLLER_REVIEW.md`。

## 实际业务调用链

`FaceTargetService`发布合格人脸→`IdentityService.offer_face`写latest-only pending→`work`按既有interval取包→`process`核对目标/TTL→`CameraFaceExtractor.extract`核对face/blur、裁剪→`DpuSFace.feature`。

`offer_face`、`work`和`process`没有因feature availability=false停止请求，所以不应为恢复另加无目标后台推理。真正门是`DpuSFace.feature`入口的 `not self.availability()['ready']`。应区分“业务ready”与“允许真实新鲜请求尝试恢复准入”，同时保留COOLDOWN/PROBATION业务unready。

`IdentityService.process`专门捕获`DeferredIdentity`：增加deferred/discarded后直接return，保留旧结果原TTL和采样状态，不执行store.match、match_counts、sampling.offer或新result发布。因此前两次probe在DpuSFace中丢弃返回向量并抛Deferred足以阻断身份发布；不可返回None模拟正常识别失败，也不可抛一般RuntimeError进入普通错误分支。

`view`、`face_preview`、`sample_start`、`enroll`均读取feature ready；PROBATION保持false时不会展示旧KNOWN结果、导出其face preview或允许新登记。CameraFaceExtractor在调用feature前可能已经生成preview_png/enrollment_quality，但Deferred分支不把它们写进IdentityService.result。第三次真实成功的slot finally已把policy转RUNNING后，feature才能返回向量；process还会重新核对目标、原TTL和revision再发布。

## 最小文件范围

1. `vision/dpu_sface.py`：probe准入门、slot内完成标记、前两次Deferred、恢复状态health。
2. `vision/dpu_vision_schedule.py`：独立SFace policy、primary通知、recovery/native完成路由、恢复health与保护状态导入。
3. `vision/ui_camera_service.py`：独立显式恢复开关与启动时handoff应用，且须早于identity worker启动。
4. 受保护的状态交接文件/启动入口及其验证；若从已有policy另建同语义实例，`dpu_recovery_policy.py`可保持原YuNet行为。是否增加专用恢复状态模块由根代理决定，不需要改模型或身份库合同。

`identity/live.py`和`identity/camera_faces.py`以既有Deferred与availability接口集成，优先保留字节不变。它们仍应进入组合故障注入验证，防止只测后端成功而漏掉上层发布。

## 实现前的关键风险

- **slot内完成证明。** `PinnedRunner.execute_encoded`在slot范围内核验wait status0；SFace marker应放在`yield fresh`正常恢复之后且fresh/acquired=true的路径，不能放在slot外的self.completed自增。异常、fresh=false或未提交路径不能mark。诊断关闭也须正确。
- **disabled与PROBATION不能混作ready。** 首次recovery准入通常临时清disabled允许后续同轮正常调度；availability必须另看policy phase，否则第一次probe就会泄漏向量。重新故障后也要再次检查availability才能返回结果。
- **预算与成功是不同事件。** 2轮/600s在真实恢复轮准入时计，3次成功只计明确native status0且未越hardcap/guard；source/slot拒绝不算成功。三次success之间让给YOLO，不能空推理凑数。两种policy实例不得共享deque/phase或重置YuNet历史。
- **故障分类不能混用。** 同lease status0/body0/hardcap1/guard0可10s冷却；guard-only、both、未知/非0完成、owner_fenced保持LATCHED/原fencing。当前YuNet521属guard-only，不能因SFace恢复变更解锁；SFace610属hardcap-only，但必须承接其原始证据与计数后才可进入候选状态。
- **primary基线坐标。** 若policy.fault_primary_calls继承旧累计，而新scheduler.primary_calls归0，due可能很久不能满足。必须同步承接累计或明确来源计数与新进程基线，不能混用旧绝对计数和新0基线；故障后primary_overruns增加仍要保守锁定。
- **启动顺序。** handoff必须在创建/启动IdentityService前应用，不能先让SFace在默认RUNNING执行几次后再覆盖状态。旧版回退若没有状态导入能力，不能仅回退字节后默认启用被保护任务。
- **handoff不是重启清零。** 绑定boot、旧PID/birth、发布/模型SHA与最新fault lease、job及policy累计/预算历史。YuNet沿用LATCHED，SFace故障缺完成证明或guard字段时保守LATCHED，不能新建policy默认RUNNING覆盖disabled；重复/错boot/错版本或陈旧交接拒绝应用。先捕获最新状态并核对停止前没有新保护事件，无法证明时降级锁定。
- **统计来源透明。** 新进程计数窗口与继承的故障/恢复总数分别标来源；恢复不清faults/overruns/attempt_times。若本轮搬迁附带一次受控版本切换，不能拿新0计数声称原故障消失。

下一步收到实现后只进行独立故障注入：先核对上述入口与handoff fail-closed，再覆盖status/guard分流、3次成功/预算边界、primary失败、owner fencing和IdentityService前两probe不发布/不登记，以及旧YuNet状态保留。本报告不预告测试已通过。
