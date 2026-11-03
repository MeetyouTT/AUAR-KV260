# 受限恢复正式上板：受控注入与正常运行短窗口

2026-10-23用户继续，处理通知时隙后仍有的freshness gaps。对上版active evidence只读审查：晚期相机watchdog有重启是旧版之前的历史，之后unit e893930d版本继续active；新方案前置重新验证当前healthy。旧版60.06298秒只读baseline (camera252665)YOLO9.93957Hz、人脸2.71382Hz、CPU65.8337%，窗口native163；累计gap由6到6、BUSY累计为进程统计。纯slot-notification候选失败：虽schedule通知可用，但submit前共享state lock常busy，60秒以上采样出现busy撤回355、gap14、过期/发布丢弃0，不能接受。安全restore helper无绕过保护，关闭未ready GUI后恢复e893930d版本PID296517、音频296543，timerinactive。

修正为显式`independent_admission=true`时在DPU提交guard读取独立关闭Event＋不可变frame timestamp＋retry monotonic deadline，不争用UI/track共享锁；在native提交前仍重检。close先set Event，所以关闭可在共享锁争用时阻止尚未提交任务。其他默认版本使用旧锁检查。通知timeout100ms、最大轮次deadline200ms、freshness TTL1000ms、YOLO优先、硬限30ms/guard5ms、恢复策略和SFace/GUI未改。新增3项关闭token/锁争用反例，原139项加协议33项/隔离板17项。

当前含token正式helper `4970321c…`上板，通过受保护协调切换成功。有效60.32683秒：YOLO9.96240Hz/人脸发布3.76284Hz/CPU57.2832%，227 native完成、通知wait增量80/80 ready/0 timeout；freshness gap0、input/publish TTL discard0、native失败-准入撤回差0、BUSY撤回0，USB0，最大可选占用11.3257ms；最新帧龄274ms。旧版minute gap0减少了累计gap，但CPU/频率不是严格相同输入受控测量，故不宣称因果性加速比。两次此前部署启动失败皆在任何切换前退出；其一原camera watchdog短时重启，之后再预检通过。旧纯通知版本真实失败和恢复证据留档，不能混称已接受。

当前unit `048ee59cf4f01d84f0442825926b38ae0940e3c566a005449385d34536734e2f`，camera298571/GUI298601/Xserver1077，双视觉DPU、SFace仍Windows旧库。15.15239秒动态采样CPU55.33098%、DPU任务busy4.93436%、207命令、CU stats最后关闭；只读审计passed，controller与所有trial timer inactive，--check回退入口通过。正式源码11份回读封存，包880 files原件verified，配置只比父版加`yunet_slot_wait_ms=100`；AURA范围其他项目未更改。

后续用户问“现在好了么”时最新只读复查：同boot/相机252665/unit e893930d…，YOLO约9.94Hz、YuNet仍DPU，累计4402可选调用/超限0/max28.069ms、恢复RUNNING，三服务零重启；逐发布TTL缺口累计新增2段。第一段5ms：11 offers/8 attempts/7 denials；第二段下/上界30/31ms：12 offers/10 attempts/8 denials/1 busy。源帧龄当前671ms，input/publish TTL discard及process/callback/observer error均0。记录支持继续优化更新机会，不把间隙混同执行超限/无输入/接收过期结果。原短窗口与先前1601调用审计gap0仍是对应时间点实测，当前不能称业务时效全部通过；只读未改服务或放宽TTL。最新过滤证据和状态放共享协作任务/受限恢复_后续状态_20261023.md/json，原37工件冻结不改，Windows回执未代填。

用户“继续”，授权接续前一轮候选。按要求先读ZIP README、项目/共享规则、当前入口和117软件/24实板无设备检查、最新实际故障。当前boot7924ac9f…/相机198117/unit af337bce…仍为YuNet CPU fallback，原正式Windows身份/GUI空闲。新任务仅主任务接板，没有新增agent，最多两个终端。

独立目录aura-yunet-bounded-live-20261023，沿用候选4源码逐字节不变；新增当前父版本/各目标独立配置/注入状态判断的协调流程与短发布控制器。捕获原af337bce…为回退目标；source/config/GUI/偏好/owner/boot检查保持，独立timer先arm再关闭音频和切相机。原m.healthy只能接受0超限，此次仅对声明注入阶段接受一个完成/status0/guard未超且经过有限恢复的事件；正常阶段依旧0超限。未知、guard或多故障均拒绝并回退。

30项协议/PIN/注入/真实临时文件的完整发布与回退反例通过。首次测试fixture未将boot换为本机实际boot导致预检失败，补fixture后30项通过，错误日志保留；非板故障。只读故障定位记录增加错误文件/行号。helper SHA64daead0d60439fd…上板0传输重试，独立controller RuntimeMax480秒/restore timer600秒。

真实相机链路首次成功native且距primary至少60ms余量时，只在单独injection入口注入31ms墙钟等待一次。调度占用35.509185ms超过原30ms、guard提前37.849ms、waiting_primary0，故障1完整保留；冷却后1次探测周期/3次正常native完成，实测自动回DPU。音频启动期间已发生恢复，不报告精确10秒总恢复延迟。之后有效60.349080秒观察：YOLO9.975297Hz/人脸发布2.767234Hz、窗口native完成167、CPU59.1214%、USB0/gap0/无新增主周期超限。快照源帧龄max592ms。

协调关闭原音频、确认PCM closed后切到普通runtime_entry，无注入导入。正常独立进程有效60.400823秒：YOLO9.983308Hz/人脸发布3.228433Hz、窗口native195、CPU57.8943%、USB0/可选超限0/gap0/无新增主周期超限，最大可选占用28.069491ms，快照源帧龄max515ms。两个60秒是独立进程窗口，不合称连续120秒长稳，也不将有意注入当作原生硬件故障复现。

正式accepted并保留新unit **e893930d9f51540223e849c36409fdc225fe7cbb347cdc1cb75166d8271e83f7**，活动`/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-bounded-61abe4391d3a-251478`；相机252665/GUI监督252691/Xserver1077。新camera config只多yunet_dpu_recovery=true，与原config去除此项逐对象相等，正式身份仍WINDOWS_CPU_SFACE_ORT/旧库路径。880包文件首尾核验、原父包完整保持；11份当前关键源码与1ms启动记录实板回读通过。30ms/5ms、50ms失败轮次/成功200ms、light3/1000ms TTL、CPU affinity0..3保持。

15.157762秒动态负载：CPU57.0032%/DPU任务busy4.86811%/193命令，不新开推理runtime，finally关闭统计并验证计数冻结。四核整板占比：camera23.7997%、界面22.9255%、Xorg3.7440%、常驻音频3.7275%，不是阶段内部热点归因；后续CPU应定位界面与图像处理。不同现场输入窗口不报确定降耗或加速比，DPU busy不是MAC/PL静态资源率。

安装当前boot专用restore_previous.py，--check只读实板通过；--restore先arm独立timer并协调回af337bce…上一版。本次成功后未为测手动入口而撤销正式版本，事务故障回退路径已软件注入覆盖。最终只读audit：可选调用累计1601/硬超限0/gap0/真实native失败0/max28.069ms，正式两模型DPU、音频IDLE_READY、controller与timer inactive、CU统计关闭、单owner/源配置模型GUI校验通过。罕见31ms根因、SFace正式独立INT8身份、真人强交互、冷启动与同输入收益仍未完成。

代码、过滤证据、当前机器记录、11源与回退指引写共享deliverables/2026-10-23_bounded_yunet_live，旧117候选封存不改；共享当前入口/Ubuntu回执与本机断点更新。原始UART/图像/音频/特征/身份库/偏好原件未共享，语音模型/运动/位流未改，Windows回执与同步接收未代确认。

封存复核：37工件字节/SHA、26份Python AST与全部JSON解析通过，4处当前链接有效；上一轮18工件候选SHA不变。新机器记录已同步更新本机旧工作入口，原ACTIVE_RELEASE/CHECKPOINT完整另存PREVIOUS_*，不以旧af337bce状态误导下一轮操作。
