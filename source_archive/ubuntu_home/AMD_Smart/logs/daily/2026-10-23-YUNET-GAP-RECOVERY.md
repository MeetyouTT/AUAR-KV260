# YuNet更新间隙取证与恢复节拍

延续用户“继续”授权，仅主任务串行操作板卡，无新子任务。boot仍7924ac9f…；本轮首检原相机112143、GUI20748、Xserver1077 active/零重启，YuNet DPU且关键区无硬超限。

light3完善gap独立32条保留，并记录两次发布之间offers/attempts/denials/busy/deadline/expired计数差，复用已有时钟。schema错误占位同步light3。完整85项软件检查、评估器19项通过；板端无设备合成35项、额外0.5ms门槛通过：正常CPU+0.285647ms，满32gap/16混合事件health CPU+0.287403ms，JSON15649B；原相机进程保持。helper99e52c48…没有额外DPU作业。

light3受保护实时120.386秒（有效120.932秒）诊断helper54bbfd64…：YOLO9.88987Hz/YuNet3.10919Hz，CPU56.99%，USB0，关键区最大21.7125ms/硬超限0，原unit与UI/Xserver保持，回退verified。严格总体passed=false：稀疏25快照最大源帧龄616ms，但gap捕获1段下/上界175/175ms，发布观察间隔1038ms，13个offer、7次attempt，其中5次slot拒绝、1次busy取消、1次成功；未丢记录。该段证据排除“无新帧输入”，支持连续拒绝/取消与轮次间固定200ms等待放大更新间隙；不是全部历史长尾根因已解决的证明。输入/发布TTL未放宽。

新独立副本`/home/ghmd/aura-yunet-recovery-20261023`加`retry_recovery_ms=None`默认关闭；实验50ms仅缩短未发布轮次后的等待，成功无脸/人脸均保持200ms，仍等新帧、同原重试/硬保护。完整89项软件通过。精确新service observer合成35项板测也通过（helperf5e984bd…），正常CPU+0.280494ms、拒绝+0.155680ms、满history health+0.287587ms。原文件未改，当前helper7b9b767d…的120秒短测进行中，观察额外CPU、YOLO、TTL空窗与自动回退，不能预报收益。

恢复候选首个短测helper7b9b767d…在正式窗口前因新增USB告警被保护中止（当时recovery_waits=0，未实际执行50ms节拍），rollback_verified=true。随后原进程124718在26.911609ms、finish_after_guard1.903709ms时回退CPU；不是30ms硬cap触发。5.35秒只读after-cursor窗已达5000告警上限（slot3 ep3），CPU90.29%，journald16.34%/syslog8.68%整板占比，不能当完整告警计数或归因于恢复节拍。

UI/录音/转写空闲后，独立原音频生命周期恢复helperc58c50ee…执行完成：停止音频PCM关闭、原相机在audio closed期重启，再恢复原音频。最终8.106秒完整窗0匹配告警、CPU51.88%、原YuNet DPUmax16.343ms/无超限；相机127091/UI127112/Xserver1077，原配置/偏好SHA保持，guard timer inactive。仅短窗恢复、非USB根因修复。相同恢复候选只换独立启动namespace的r2 helper10261c1b…开始120秒重测，失败记录保留；不盲目连续重试。

r2同候选再次在观测开头因USB告警退出，当时recovery_waits仍0，rollback_verified=true；停止继续切换实验，未启动准备好的600秒helper。第二次原音频恢复helpera8767789…完成，原相机130028/UI130049/Xserver1077 active，8秒完整窗USB0/CPU52.18%，guard timer inactive。未声称USB根因已修复或50ms策略板测通过。下一工作为相机切换与原常驻音频的有界协调流程；必须先补等价恢复保护再试，不简单删UI PID校验。共享`2026-10-23_yunet_gap_recovery`冻结代码与过滤证据，原始UART/生物数据不共享，Windows回执未改。

后续独立只读状态与5.136秒窗：原相机130028仍DPU_YUNET_INT8/关键区max16.170102ms/overruns0，捕获12.37/检测9.87Hz；USB0且after-cursor完整、CPU52.70%，UI IDLE_READY，无录音/转写pending。共享冻结56工件SHA、40 Python AST、14 JSON解析及实际source/cost PIN相同、两次中止且回退通过校验；下一步文档不冒充实现。

最终独立恢复审计passed=true：原unit84116d8f…、7份原源、原YuNet模型/manifest、Windows身份配置与原runtime核验通过；实验metrics/retry/shadow关闭，两次trial rollback timer均inactive，UI IDLE_READY。审计源码与过滤JSON已冻结，SHA重算和本地文档引用通过。
