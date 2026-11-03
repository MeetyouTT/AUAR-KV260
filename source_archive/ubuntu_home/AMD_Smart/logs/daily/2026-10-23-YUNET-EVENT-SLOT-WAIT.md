# YuNet准入等待与取消锁竞争修复

用户连续要求继续，目标处理实时观察出现的2段更新gap。先重读ZIP README、项目规则、共享当前版本与故障证据。当前基线unit e893930d…，双模型DPU。只读一分钟对照60.06298秒：YOLO9.93957Hz、人脸发布2.71382Hz、CPU65.8337%、DPU native163；历史累计gap 6→6，代表该分钟没有新增gap。期间startup/recovery counters存在旧事件，故对照按帧与gap delta判断，不把累计数清零。

候选一新增100ms DPU时隙通知等待，不占slot，并在醒来后重新准入；142软件/17板端隔离和33 deploy PIN/事务测试通过。实板版本等待通知后仍用共享相机state lock做nonblocking提交前检查，UI/跟踪持锁时导致频繁busy撤回：估计一分钟段落内busy355、gap14，超出额外准备消耗约束。候选明确拒绝并通过独立restore关闭未ready GUI/PCM后回到父版，恢复GUI音频IDLE_READY。无成功版本假装接受。

候选二新增显式独立取消Event；只读close、不可变输入时刻及retry deadline可以在不获取状态锁时确认，close路径先置Event；DPU slot/context、当前帧TTl检查与实际业务状态提交仍按原owner/锁纪律。source、freshness与身份数据库不变。139旧runtime/retry回归+3取消/Event锁争用测试=142，33发布协议/回退反例、KV26017隔离状态/成本测试均过。封装候选首次部署前遇当前父版两次已恢复超限和一次camera watchdog restart时错误地要求全进程历史overruns为零，前者有恢复证明，后一项日志明确`Camera stopped producing frames`后systemd auto-restart；修正为按历史完成/恢复状态核验且候选期仍硬性要求无新故障。另一轮父音频GUI在startup中未ready，健康预检拒绝并安全恢复；controller标记其owned startup GUI、正确停止并关PCM后恢复，未改用户运行中GUI。失败日志、恢复结果与runtime unit hashes保留。

采用精确candidate pin和boottime/audio/unit独占保护，短切换前保存父版release/unit、active GUI原配置/偏好；改release内完整config仅新增`yunet_slot_wait_ms=100`，保留`yunet_dpu_recovery=true`。成功窗口60.326829秒：YOLO9.96240Hz、人脸发布3.76284Hz、227次DPU native完成、CPU57.2832%、USB0；通知delta80/80 ready、timeout0；freshness definite/observed gap0，BUSY/withdraw/TTL discard/native异常/observer失败均0。最大slot notification wait wall64.745ms；该上限只是outside-DPU prepared-wait，后续准入检查仍要满足primary deadline；不代表总时效硬界。最大optional DPU native occupancy 11.3257ms，0 overrun。Source age max291ms。

相对于旧一分钟只读窗口，人脸发布rate由2.714到3.763，整板CPU65.83到57.28。但帧序列不是配对输入，CPU含音视频/UI调度差异，不能声称strict A/B或因果CPU降幅。额外15.1524秒当前CU采样CPU55.331%、DPU task busy4.93436%、207 commands，finally关闭XRT CU statistics，最终状态核验计数静止。当前最终只读health audit：总optional调用952/overrun0/max26.418ms、slot-wait474 ready/no timeout、gap0、current frame216ms，primary累计period overrun1来自service lifetime，非短窗delta；音频IDLE_READY、CPU affinity[0..3]、CU统计/各附属timer/controller关闭、所有8780 model/gui/source/config和单owner保护通过。正式SFace仍Windows/旧库。camera unit `048ee59cf4f01d84f0442825926b38ae0940e3c566a005449385d34536734e2f`，camera298571/GUI298601/Xserver1077。11源当前回读、880 package seal与read-only rollback check通过；guard `--restore`真实事务未为证明工具而从已接受版本撤销。

交付`deliverables/2026-10-23_yunet_event_slot_wait`包括接受版本、退回过的通知-only候选、单分钟只读baseline/样本、源SHA、恢复协议/最后审计、15秒负载与回退。共享入口/Ubuntu回执/方案和本机ACTIVE/CHECKPOINT已指到unit048ee59。Windows回执未动、没有说对端收到同步；未共享raw UART/人像音频/embedding/DB/preferences/模型权重。剩余严格同输入基准、罕见长尾的原因、长稳/冷启动、正式SFace独立INT8身份域与真人准确率仍待后续。

交付校验：65项SHA256/长度校验、38个Python AST、20份JSON parse及source pin against board传输包通过。共享入口、Ubuntu执行回执、项目书导航和当前slot-wait路线已更新。失败尝试的原unit/source保护均在对应owned report中记录，当前正式unit和config读取以ACTIVE_RELEASE/accepted report/final audit为准。
之后又做只读当前health回查：camera PID298571/unit一致，YOLO9.92Hz、YuNet累计2478调用/overrun0/max26.418ms，1330 slot waits全部ready/timeout0、busy与withdraw0、freshness gap0、source age243ms；自动恢复RUNNING，音频IDLE_READY。控制器与XRT统计均inactive；回查未改config或启动额外DPU采样。
