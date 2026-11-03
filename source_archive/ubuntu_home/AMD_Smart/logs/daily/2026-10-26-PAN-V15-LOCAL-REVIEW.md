# v15分段计时本地独立审查

用户改为两个终端后，子任务按主端分工只读取本机源码、运行隔离测试；未访问UART、板端HTTP、MMIO、服务或模型，不改冻结v15。已读ZIP入口、共享入口及相应规则。

审查实际FaceTargetService→DpuYuNet→YuNetCompat→YuNetNetwork→NativePinnedRunner链及operator包装，未发现正常返回、原异常、回调次序、TLS隔离方面的部署阻塞。原54项及独立6项测试通过；7个本目录运行源指纹与冻结manifest匹配。长数字/最长上下文压力包4009B<8192；本机Fake调用中位1.257→26.134us，仅是假链包装成本，不是KV260或DPU成本。

全256个像素值、4种随机/全黑/全白/非连续BGR输入经过原resize/blob/NHWC/encode(fix7)与整数式逐字节等价。整数实现须先提升uint16再加一；uint8在255处会溢出为0。本轮未实现生产优化、未证明模型性能或板端提升。

保留限制：detector_timing和detector_stages可能短暂为相邻帧，须按frame_id/source_mono_ms对齐；若计时API自身异常，业务调用前的取时可改变行为，该情况未在目标观察，列为诊断韧性改进，不作已发故障/当前阻塞。嵌套阶段不能相加或当纯DPU核时间，wall减本线程CPU包含等待/GIL/调度等。

详细结果位于 `/home/ghmd/aura-pan-follow-shadow-20261024/v15_local_review_20261026/`，共享审查副本在 `/home/ghmd/Win共享文件/协作任务/2026-10-26_转轴交接复核与闭环修复/v15本地独立审查/`。未改共享主入口/Windows原回执，交主端合并；无权重、原图、个人身份数据或venv复制，未代验Windows或实板。
