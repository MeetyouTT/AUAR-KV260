# 视觉DPU恢复、准入余量与持久启用

**已在板上持久启用两项修复：SFace受限恢复、保守的可选任务准入余量。** 30ms hardcap、5ms guard、YOLO优先、模型/阈值/INT8身份库保持；没有靠延长阈值或空推理取得通过。罕见长尾的唯一根因尚未确认，真实人脸恢复和实际断电冷启动未复验。

当前boot `008f3e1b-c627-4b98-b120-d2a460cdbcbe`，camera29563 / GUI29588 / Xserver1077。有效源码根为`/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-vision-recovery-c76110abefc304bb`，新增独立持久覆盖`/etc/systemd/system/aura-camera-ui.service.d/zzzz-aura-vision-recovery-c76110abefc304bb.conf`。原unit SHA29786434…不变，旧运行时覆盖保留但不再优先。精确状态以CURRENT_STATE.json与final-audit.json为准。

## 实际改了什么

- **SFace恢复闭环。** 同lease明确native status0、body正常、只越hardcap且未越guard，才允许冷却10秒后探测。600秒最多2轮，每轮3次真正合格native才恢复ready；前两次Deferred，不产生KNOWN/UNKNOWN、不登记。过期、未提交和slot拒绝不算成功；guard/未知完成继续锁定，共享owner fence不清除。YuNet与SFace各有独立策略和预算。
- **拒绝过窄窗口。** 新配置`optional_admission_floor_ms=30`，准入与通知等待使用同一规则：至少剩余30ms预算＋5ms guard才可插入。硬上限仍30ms。它会拒绝历史YuNet event521那种仅剩20.91ms的机会，而不是提交后在21ms时触发guard锁定。不能保证Linux调度下所有长尾都消失。
- **跨进程/启动状态。** worker创建前加载哈希固定的同boot快照，继承schedule、故障和SFace请求计数。种子重复消费会锁定两可选任务，避免同boot重启清恢复预算。真实新kernel boot用独立计数窗口，并在health保留前一固定快照的来源/故障数；不重放旧单调时钟，不改旧文件。新启动分支已软件及板上隔离测试，未主动重启板卡。
- **持久启用与回退。** 只新增自身drop-in，不覆盖原unit。回退使用旧代码的保护入口；自身持久覆盖移除，临时保护入口只写`/run`，避免把旧boot固定入口留到下次启动。未知native完成时拒绝创建替代owner。GUI运行175份Python不变，回退上下文按新PID另建，历史上下文未覆盖。

相对最初可靠性修复版，实际变化仅4份运行源：`dpu_vision_schedule.py`、`dpu_sface.py`、`ui_camera_service.py`及新`dpu_protection_handoff.py`。IdentityService/裁剪对齐/模型/登记库/语音/PL/运动未修改。完整差异在runtime-changes.patch。

## 验证与数据边界

最新持久版本60.302826秒：YOLO **9.966Hz**、人脸处理 **3.897Hz**，窗口新增optional/primary超限、gap及USB告警0。启动阶段主周期超限另增1并保留，不能写整段零超时。SFace后端ready，新增SFace请求0，因此没有真实SFace恢复验证或三模型持续负载验收。

恢复组合主机198项通过；板端基础171项、恢复新增26项、准入组合61项、最终启动/恢复组合68项均通过。后一系列均是**软件隔离/fake native，无额外DPU作业**，彼此重复的测试不累计成独立用例总数。另有7项新boot分支、6项持久控制器行为、6项准入边界、4项phase解析及4项页面清理检查。测试日志和每轮source SHA/manifest一起交付。

在前一恢复版本上，main页面180秒702组和600秒2354组完整native/GIL分段；vision页面180秒682组，均无新超限/gap/主周期超限，观察CPU约0.23～0.41%单核、无丢记录、清理通过。native最大分别14.776/14.110/17.672ms，RestoreThread最大5.134/5.378/4.532ms。全部为一个YuNet线程，SFace新增0。

**最终版本随后捕获1次真实YuNet硬超限。** 计划600秒的vision窗口在25.27秒即按故障条件结束：81组完整调用，event12638总占用33.677557ms，hardcap1/guard0、native完成/status0、owner未fenced、主周期/gap未增。匹配的native段21.611ms、GIL重获0.094ms；Python wait标记区间9.695ms，不能据此把9.695ms全称为原生wait或设备计算。事件与完整分段见captured-fault-analysis.json。phase-result的passed=true只表示**测量/成本/清理通过，不是业务无故障**。

已实板确认同camera29563经10秒冷却和3次合格探测自动恢复YuNet DPU，faults1/attempts1/recoveries1均保留，没有重启。actual-yunet-recovery.json为实证，不能套成SFace真人恢复已通过。新八点+调度事件观察继续分离wait包装入口、内层调用、清理和CPU排队；结果以wait-sched-result.json为准。八点无DPU fixture500轮/4000记录、平均额外CPU38.36µs/轮、无丢失与清理通过。

准入版15秒资源快照（持久启用前）整板CPU48.12%、DPU任务busy约5%、209个真实驱动命令；GUI组23.11%整板/相机组19.79%。它不是同输入A/B或FPGA静态资源率，SFace无新请求。统计已关闭。最新版本资源快照以resource-result.json为准；首次新快照被“非零累计”前置检查拒绝，未开启统计，现改为在真实YOLO帧持续完成时验证计数是否静止，失败和修复保留。

## 仍未完成

旧boot中的YuNet guard锁定、SFace39.89ms等故障保留，没有因外部新boot或3次受控版本切换抹去。外部新boot不是本轮发起，原因未确定。`NRestarts=0`仅指各次服务的自动重启属性，不代表本轮没有人工版本切换。

实际`execute_async`释放/重新获取GIL的路径已由精确ELF确认；DDR库的wait函数确实直接返回0。因此wait很短不能排除execute内设备/驱动等待。现有观测未捕获30ms故障，仍不能把旧故障定因于GIL或硬件。原生/外部schedstat两个成本未过的方案未常驻；当前UProbe均有独立清理guard，结束以最终审计确认无残留。

进一步捕获event20476后已确认本次长尾是混合等待：native16.239ms中约14.006ms在可运行状态等CPU，重获GIL8.698ms中约8.415ms为睡眠；内层wait仅0.009ms。Nice=-5短试维持约8fps但相对长基线的P99收益不稳定，已恢复全部线程nice0，未持久修改调度优先级。详见VALIDATION.md及数字分析文件。

最终只读续查仍同camera29563，YOLO约9.96Hz，YuNet累计约5万次，两个真实故障均自动恢复，gap0；后续约112分钟快照间没有新增故障。最终资源快照CPU48.55%、DPU任务busy约4.93%，非配对收益。所有自有probe/instance/guard与统计已清理关闭，源/配置/登记库与GUI回退检查通过。

真实SFace恢复/陌生人及多人精度、实际断电冷启动和持续真实交互仍待现场输入；本轮未主动开麦、播放、转轴、改PL或重启板卡。Windows接收/同步回执未代填。包内不含权重、精确ELF、UART原始记录、人脸图/向量、数据库或私有偏好内容。
