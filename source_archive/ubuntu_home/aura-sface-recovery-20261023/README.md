# SFace受限恢复与等待长尾诊断

已实现并在当前开机运行版本中启用SFace独立受限恢复，原模型、INT8模板库、阈值、30ms hardcap、5ms guard及YOLO优先保持。不是长尾根因已修复，也尚未完成真人恢复/冷启动验收。

恢复仅适用于同一lease已确认native status0、body正常、hardcap越界且guard未越界的任务：冷却10秒，要求YOLO继续正常完成，600秒最多两轮真实探测；连续3次合格native才恢复业务ready。前两次向量通过DeferredIdentity丢弃，不匹配身份、不发布KNOWN/UNKNOWN、不登记。过期、未提交或拒绝不算成功；guard越界、未知完成和共享owner fence继续锁定。SFace与YuNet使用独立policy实例，新增恢复不解锁已有YuNet保护。

4份运行源改变：调度器、SFace适配器、相机启动接线，以及新的受保护状态交接模块。IdentityService、裁剪/对齐、模型、库、GUI运行源码未改。完成证明在slot内且wait status0后记录；同时检查结果新鲜度，完成事实与probe成功分开。

当前使用私有`/run/systemd/system/aura-camera-ui.service.d/`覆盖，原`/etc` unit SHA29786434…保持；**此轮仅当前boot启用，下次boot回原正式入口**。带boot/PID/源SHA的种子在worker启动前加载，继承任务/故障/主周期和SFace请求计数；重复消费同boot种子锁定两可选任务，不能通过重启重置恢复预算。回退使用原相机代码加保护启动入口，两可选任务保持停用，避免回退时默认解锁。GUI-only回退另有本轮新PID对应的独立上下文，历史66cde…上下文没有改写。

原计划基于旧boot7924ac9f…/camera588727的双保护状态；发布前发现板卡已由外部原因进入新boot008f3e1b…。旧boot校验拒绝了传输，尚未修改生产。这次外部重启不是本轮发起，其原因未确定。新boot原相机1017已有三模型DPU且0故障，因此本轮以新实际快照迁移，旧boot的YuNet521/SFace610故障仍在上一轮诊断包和本轮preflight中，不能称被新0计数修复。

新运行版camera5842/GUI5867，源码根`release-sface-recovery-4bcbe0999c62a348`。60.306秒检查通过：YOLO约9.81Hz，YuNet仍DPU，0新optional超限/gap/USB告警；SFace ready=true、恢复功能启用，但窗口新增SFace请求0，**没有新真人SFace推理或真实故障恢复验证**。对应`promotion-result.json`的actual_recovery_validated=false/live_sface_sampled=false；不以功能已加载代替实际恢复验收。

验证：197项原组合软件回归、增加clean同boot迁移后198项通过；KV260软件隔离171项及新增26项恢复故障注入通过，均fake VART/无新DPU作业。后者覆盖真实PinnedRunner/适配器/调度器及IdentityService前两probe不发布/不登记。5项发布纯函数检查、4项分段解析/精确ELF指令检查通过。新增独立审查初版fixture漏转Python float的失败和修订、旧boot传输拒绝均留证。

本轮继续以已核定实际VART的四非分支指令做有界阶段观察：native前后与RestoreThread前后分开；既有线程自己产生业务，不增DPU owner，不主动空推理。结果、正常分布/真实故障及清理以phase-result.json为准，尚无结果时不预填通过。完整trace只保存数字ID/单调时间，不保存图像、向量、用户语音/正文。

长尾根因、准入尾部余量、真人恢复/精度、冷启持久启用及整机长稳继续按实测推进。Windows接收及同步回执未代填。
