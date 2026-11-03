# 视觉运行可靠性修复

本轮按用户要求使用主任务＋一个独立审查任务，板端UART仅主任务顺序访问。目标是完成明确的软件正确性修复和短业务验收，不把稀有82ms等待的根因写成已消除。

**已正式接受并保留新版本。** unit `29786434…`，camera450495、GUI450525、Xserver1077；YOLO/YuNet在DPU，SFace正式后端DPU_SFACE_INT8已恢复可用。当前状态见ACTIVE_RELEASE.json、CHECKPOINT.json和accepted-release-evidence.json。

60.518819秒实流：YOLO9.9308Hz、YuNet发布3.8170Hz/231次真实native完成，整板CPU56.9187%，新增主周期超限/optional超限/gap/USB/诊断错误均0。进程启动累计primary超限1保留，不称全生命周期零超限。SFace启动阶段完成5次，60秒观察窗新作业0，接受后读回累计6次；本轮没有重新验收本人/陌生人精度或持续三模型满负载。CPU与之前真人窗口输入不同，不作降幅/加速比结论。

最终12份活动源码读回SHA、880文件相机包、175份GUI Python单文件差异、原INT8/Windows身份库SHA和配置保持、音频IDLE_READY及回退--check均通过；controller/恢复timer inactive。见OPERATIONS.md。稀有长尾根因、SFace自动恢复、长期/冷启动和CPU同输入收益仍未完成。

最终只读续查：同camera450495，YOLO累计9.89Hz，YuNet累计1479次、SFace累计52次完成，两者超限0、gap0、diagnostic_failures0、owner_fenced=false，身份ready。52次包含正式观察前后自然运行，不改写60秒窗口内新增0的原记录，也不作为现场准确率证明。

## 改动

- dpu_vision_schedule.py：辅助诊断finish移出执行权及condition；begin/finish/error/snapshot异常不泄漏调度active，旧trace不能清掉新owner；保护/恢复决定仍在释放前完成。新增lease代次及明确的非原子诊断快照口径。
- pipeline_metrics.py：失败trace按线程和对象身份清理，避免旧finish/discard移除后继trace。记录的是释放前决策及释放后观测点，不伪称精确解锁时刻。
- dpu_vision_runtime.py：YuNet/SFace的native调用完成不明确时抛类型化错误；共享scheduler停用YOLO/YuNet/SFace的新准入，不盲重投或宣称已取消在途硬件任务。成功status0但墙钟超限仍沿用原保护/恢复逻辑。
- face_targets.py：worker故障后ready=false、清当前目标、拒新帧并等待协调关闭，实际线程存活/故障计数可见；关闭后不残留ready。没有做无限重启、直接重建runner或盲目CPU重投。
- dpu_yunet.py：CPU fallback直接记录次数、失败、末次/总耗时及原因，不用publish/native计数差推算。
- dpu_sface.py、camera_faces.py、live.py：复用已验证的SFace持续可用性修复，停用后不显示缓存匹配/脸预览，暂停登记/采样，删除和取消可用；普通时隙繁忙不是故障。
- spoken_query.py：在真实GUI消费侧处理ERROR→identity_unavailable，与UNKNOWN区分；不是只改相机副本。

不改30ms/5ms、YOLO周期锚点、预算估计衰减、原GIL1ms、模型、阈值0.50/margin0.10、INT8身份域或数据库。SFace自动恢复尚未实现；停用可见性和有界协调恢复是不同事项。

## 验证及发布过程

210项相关软件回归通过，包含独立23项资源/并发审查；最终26项部署/恢复检查通过。板端71项隔离检查禁止VART/XIR、只用合成内存库，验证代码不能当新真实DPU推理或现场身份准确率。

第一轮helper60d81145…的候选相机实际出帧且YuNet无超限，但验收器错误要求“无当前人脸时SFace也已建立job计数行”，45秒未就绪后拒绝；已协调恢复旧unit a29082ba、camera445907/GUI445937，自己的GUI override移除，guard/controller inactive。原程序没有该计数要求，这是发布验证器错误，不将本轮拒绝写成DPU故障。已增加“模型加载ready但无目标/零请求”反例并将部署检查23→24；模型真不可用仍拒绝。

第二轮helper18df18c3…沿用同一9份业务源，只修无作业判据；相机已正常就绪，但GUI clone错误复用了旧stage.log软链接，启动器按路径约束拒绝，控制器超时后恢复原两组件。原始拒绝原因、source/hash和恢复结果保留。已排除运行时stage.log并增加对应克隆反例；部署检查24→25，业务源不变。

第三轮helper269026b9…仅修GUI日志排除规则，但在切换前发现旧版SFace真实36.742758ms超限停用，完成20次status0后持续defer而顶层仍ready；30秒前置健康校验拒绝，未停止服务或切换。此为另一个旧进程447318的故障，与原333557的YuNet三次故障分开记。

已保存该SFace故障完整数值并确认native完成/status0。第四轮helperf7624754…仅允许这种“旧父版已确认完成但被保护停用”的状态进入有保护的协调重启，候选仍要求fault0，未放宽30ms/5ms；新增部署反例25→26。旧三条YuNet及新SFace故障全部保留，不以进程重启后计数清零声称根因消失。后续短窗结果单独写接受证据。

第四轮最终已接受：完成协调切换和上述60秒观察，原身份库/config/source保持及最后主周期检查通过后才停止独立timer；未留下延迟注入、新观测profiler或第二套DPU owner。前两轮实际恢复、第三轮前置拒绝与全部失败报告保留。

部署创建独立camera release及GUI源树；GUI现役175份Python中仅spoken_query改变，资源目录和原生库软链接保持，设置分别复制。原GUI配置与所有既有dropin保持，自有override有SHA和集合检查。先arm独立恢复timer，再关GUI/确认PCMclosed、切相机和GUI，60秒通过后最终严格检查主周期/optional/worker/源/库，再停timer接受；失败恢复原两组件。

## 计时与验收边界

原scheduler occupancy字段含义保留为准入至释放前保护判定；辅助finish现在发生在释放后。lease_release_decision不是精确解锁时间，after_release_observed是退出锁后的观测，线程被换出时是上界。未把finish少计问题包装成根因修复或纯DPU速度提高，也不直接比较新旧optional_wall分布。

短测验证正常业务和新健康状态，不替代陌生人/多人、声音交互、冷启动或长期稳定。没有当前人脸时SFace可以零调用，若如此必须明确本轮没有新SFace真人推理/精度验证。

回退工具随接受版本写入OPERATIONS.md；默认--check只读，显式--restore先建立独立timer并协调恢复。旧固定boot/unit/PID的历史helper不可直接重用。新旧身份库与既有归档均保留，交付仅包含源码/过滤数值，不含真实图像、声音、姓名向量、数据库、模型权重或原始UART。
