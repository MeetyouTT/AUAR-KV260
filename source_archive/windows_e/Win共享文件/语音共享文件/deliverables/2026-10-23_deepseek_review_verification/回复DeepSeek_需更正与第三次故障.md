请修订上一份审查，先核对下述源码事实与新故障，再给可审阅的最小补丁设计。此轮仍是审查，不执行板端操作。

新增真实故障C（同unit a29082ba/camera333557）：YuNet累计14399次完成/3次超限，C占用82.926870ms，execute marker墙钟82.077971ms/调用线程CPU2.163218ms，wait0.106431ms；native_status0/completed1，guard越界，last_overrun记录+0.358214ms、diagnostic记录+0.395344ms。C的execute区间probe自愿切换+69、非自愿+0，两次采样总墙钟0.135942ms。当前YuNet disabled=true、CPU fallback、recovery LATCHED，attempts2/recoveries2，第三次没有恢复。YOLO约9.94Hz、SFace2534次/超限0、gap累计0。完整原始单调字段见evidence/third_fault_snapshot.json。

请优先纠正：

1. pipeline_metrics.native_mark在196行取now/cpu，197～199行才做return侧probe；原文说return侧sample先于now，与实际相反。source/pipeline_metrics.py有最新实板读回依赖SHA证明。可直接用fake probe在return侧推进3ms，execute_return端点不包含它。
2. runner在获得slot之前已经校验shape并分配4个np.empty。A的22.7ms不能归因到slot前的分配；execute marker区间也包含start marker收尾/pre_execute/绑定边界，不能一律当execute_async纯native内部。短wait不证明任务在进入wait之前一定已结束。
3. scheduler occupancy与diagnostic optional_wall的差，是结束偏移减起始偏移。不能用A的-0.490ms精确推出起点偏移，更不能用wait_end→optional_end当整个finish开销。finish取now之后还有锁与聚合。
4. 当前入口board_camera_motion.py的SHA与gil_camera_launcher的CAMERA_SHA、formal process_setting完全一致，它会调用ui_camera_service.main；当前已是1ms。不应重新pin到ui_camera_service、绕开motion feed入口。已有5/1ms和亲和性历史实验可补充阅读，不能当作尚未做过。
5. YOLO循环末sleep也按wait前的started补足100ms。请说明你所谓锚点错误的业务期限定义，并解释为什么改为frame_started+100ms不会给optional放宽到旧周期之外。只有一个串行YOLO循环时，下一次传入deadline单调增加；“新来的更早deadline”需给当前代码可达交错，而非假设另一个调用者。
6. 自愿/非自愿切换不是GIL/CPU排队二分类标签；runqueue小也无法区分GIL、其他锁和驱动阻塞。完整schedstat模式已有平均0.763ms/慢读7.234ms、未过原0.5ms前置，不能用轻量getrusage的75µs代替其成本。环境变量只在构造时读取，没有现成的热关API。
7. 对未知native异常直接catch后继续、释放owner或重建runner存在在途状态风险。请区分未提交撤回、wait已完成但失败、native完成未知，给出fail-closed、可见性和有界监督策略，不提出无限继续重试。
8. SFace持续可用性4源候选已完成92软件/16板隔离但未部署，请复用而非重做。不要把候选通过当生产已修。源码事实见原包以及本补充核验报告。
9. SFace正常最大trace的wait是0.076061ms；单个极值不足证明与YuNet同一分布。49.2346分钟是所取诊断端点窗口，不自动证明每个模块计数完全同起点。published-native_completed差不能精确当fallback调用数。1000ms源TTL下，2秒p95/5秒max发布间隔与零结果gap要求冲突，请给一致的业务判据。

请将“已证缺陷/设计取舍/仅风险/报告自身误读”分列；每个结论给文件、函数和行号。重新优先排序三个实验，一次只改变一项，不把改finish、guard、buffer、进程架构合并。1～3分钟用于验证测量有效性和业务影响；未复现罕见故障不能宣布排除某根因。保持30ms/5ms保护与故障计数，优先解释新C事件，不预设GIL或硬件。

最后给出可安全评审的最小patch轮廓：记录真实释放端点、缩短诊断关键区、SFace/人脸worker持续可用性与故障可见性。保护状态更新/trace归属/异常释放必须通过确定性故障注入；生产切换单独评审，不直接执行。
