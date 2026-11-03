# 视觉恢复/准入持久修复与真实长尾归因

用户授权自主继续并离开约两小时，最新约束为仅一个终端。此前副任务完成16项独立核心故障注入后结束，后续全部由root单路完成，UART串行，没有新开子代理。项目材料、共享入口和最新证据已核对。交付：[当前持久版本、源码与数字证据](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-23_vision_recovery_and_admission/README.md)。本机 `/home/ghmd/aura-vision-persistent-20261023`，前两阶段分别为aura-sface-recovery-20261023、aura-admission-floor-20261023。

## 结果与运行版本

已持久启用SFace独立受限恢复和optional准入30ms保守下界。status0/body正常/hardcap-only→10s冷却→YOLO正常推进→最多2轮/600s、3次真实合格native才ready；前两Deferred、不匹配/发布/登记。guard、完成未知、owner fence仍锁定，两个模型策略独立。未提交/TTL过期不记成功，native完成事实和结果可用性分开。

准入/通知等待同用至少30ms预算＋5ms guard；30ms硬上限不改，拒绝历史仅剩20.91ms的插入机会。新boot与同boot重启分流：哈希固定种子在worker前加载，同boot承接保护与来源累计，重复消费锁optional；真实新kernel boot开启新窗口、旧快照保留，不复用旧单调时间。实际断电冷启动未执行。

boot008f3e1b-c627-4b98-b120-d2a460cdbcbe，camera29563/GUI29588/X1077。release为`release-vision-recovery-c76110abefc304bb`，持久覆盖`/etc/systemd/system/aura-camera-ui.service.d/zzzz-aura-vision-recovery-c76110abefc304bb.conf`，SHA ebf6d52ce1848f2fc1af73e284688a70372bbd9ec585f9cbbc09af7035631b3d；原unit29786434…字节保持。相对最初可靠性版只变4源，相机214份Python/GUI175份源核对，GUI源码不变，身份配置398ece…/INT8库ee22b…保持，监听false/main/IDLE_READY。GUI-only回退--check实板过；完整相机回退为旧码保护入口，只移自身持久覆盖、临时回退放/run，未知native完成拒绝新owner。

持久版本短窗60.302826秒YOLO9.966365/face3.896998Hz，窗口新增optional/primary超限/gap/USB0；startup primary另+1保留。SFace新请求0，真实SFace恢复/陌生人多人精度未验。三次相机/GUI受控版本切换各阶段保留来源，NRestarts0只指自动重启计数，不能写全程未重启。

## 已捕获两条真实故障，均自动恢复

event12638：33.677557ms/hardcap1/guard0/status0，native21.611ms、GIL重获0.094ms、Python wait标记9.695ms；该标记还含包装/调度，不能等同原生wait或硬件计算。四点窗口25.27s遇fault即停；测量/成本/清理过不等于业务无故障。

event20476：32.964330ms/hardcap1/guard0/status0。八点和sched_switch/wakeup直接对齐：native16.239ms含runqueue14.006ms、sleep1.506ms；GIL重获8.698ms含sleep8.415ms、runqueue0.069ms；内层wait仅0.009ms。本事件是CPU排队与GIL重获睡眠叠加，不能泛化全部旧故障或称DPU纯计算。两fault均在同camera29563冷却/3probe后恢复，faults2/attempts2/recoveries2保持，无重启。当前YuNet仍DPU、gap0、owner未fenced。

前一阶段main180/600秒与vision180秒702/2354/682组均无fault，不能覆盖后来故障。八点600秒2240组、loss0但板端解析CPU3.136%未过2%门槛；未常驻。改为板上收集、Ubuntu解析，65.61秒捕获上述第二fault，controller1.738%成本/清理过；原始trace不共享，数字记录与SHA完整。wait DDR库函数反汇编为直接return0，说明wait短不能排除execute内部设备/驱动耗时；准确源码提交与具体虚调用对象仍未完全匹配。

Nice=-5单变量180秒试验694组、GUI8.004fps/P95134.77ms、0新fault；关键区P99=10.812ms，与长正常基线10.827ms相近，短坏基线17.383ms不能单独当收益。全部8线程已恢复nice0，无独立变更被覆盖，未持久保留优先级设置。CPU配额无限、原无绑核/实时策略已核对。

## 验证与最终状态

最终组合237项，0失败/0错误、2项私有ELF检查在Docker跳过；原始指令另经本机实际匹配。最终KV260软件隔离68项通过，前序171/26/61均过但大量重复不相加。四点/八点解析、页面恢复、3项nice恢复、7项新boot及6项持久回退行为等相关检查已留日志。没有拿fake native或软件隔离当真实推理。

最新最终审计仍同PID，YOLO9.96Hz，YuNet50768累计calls/故障2/恢复2，SFace继承2次、新窗口0。相隔6739.24秒（约112分钟）的两个最终审计快照间，optional fault/gap/primary overrun增量0；只证明累计续查，不是持续真人三模型验收。另最终清理审计probe/instance0、worker/timer inactive、nice均0；真实YOLO继续15帧时CU完成计数保持454，确认统计已停。

最终15.064秒资源快照：整板CPU48.5495%，camera19.6991/GUI23.6987/X3.5515%整板；DPU任务busy4.93386%、209真实驱动命令。非同输入收益、非FPGA静态资源率、无SFace新负载。首次因旧统计累计非零被前置拒绝且未开启统计；改为实际推理推进时计数静止判据，4项检查及前后实板证据保留。

交付163条SHA/164文件、97 Python AST/44 JSON核对通过；不含权重/ELF/UART原始数据/人脸/向量/库/私有偏好。Windows接收未代确认。原外部新boot不是本轮触发，旧boot7924…故障仍归档，原因未确定；错误boot的首次传输被校验阻止，没有生产mutation。

## 尚待闭环

罕见长尾完全消除、SFace真人恢复及精度、实际断电冷启动、持续音视频/多人业务和严格同输入整板收益。已保留的是恢复/保护/准入与持久接线；没有放宽30ms/5ms/TTL、混用FP32模板域、造空推理提升忙时、改PL/运动/Windows语音或替用户开麦/播放。
