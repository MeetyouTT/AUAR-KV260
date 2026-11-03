# 来电后自主恢复与CPU/DPU验证

用户明确电力恢复并授权约两小时自主规划推进，最多两个终端。主任务独占UART/板卡与交付，唯一并行任务resume_retry在独立目录完善重试和软件测试，不接板。此前两个离线任务因额度中断，本轮接续其源码而不将未完候选写成完成。

开工阅读ZIP README、完整方案相关范围、项目/共享AGENTS及断电断点/实际数字证据。新boot为7924ac9f-311d-4fcd-98be-57bf023cf1aa，原相机1017/GUI1081/Xserver1077均active/NRestarts0，原单元84116d8f…及原runtime保持。相机无错、YuNet DPU、576累计调用/0真超限、原埋点关闭；UI/音频IDLE_READY，无录音或转写pending。只读首检没有复用旧boot/PID写操作。

本机诊断工具已补拒绝-O/PYTHONOPTIMIZE及错误PID等反例，13项评估器检查通过；冻结23项时效源测试与真实时钟微基准分进程，续跑本机完整通过，仍不是板端证据。板端合成前置helper fae37bfe…固定新boot和8源SHA，私有隔离目录运行fake依赖/空检测与准入拒绝原/off/on各200次、满16事件health含外层RLock，不加载真实模型/runner/相机/音频；新增DPU作业0，当前正在暂存执行，结果待读回。

后续顺序：合成开销前置→准确新boot隔离实时时效诊断→重试候选独立软件/兼容性审查→短测/10分钟/30分钟，保留30ms/5ms/YOLO优先/旧身份库和自动回退。用户离场不做需要真人的正式身份登记/阈值，也不以无脸时影子请求冒充有效身份业务。现阶段未预报根因解决或板端收益。

合成前置结果：首轮因Python3.9 unittest.mock间接导入socket被导入限制拦截，没有网络/设备操作。预加载纯测试框架并加实际socket/device/process audit拒绝后，板上同23项全部通过，但完整observer正常路径平均新增CPU0.73896ms/墙钟0.96646ms，未过预设0.5ms，因此未启用该完整观察器。初版失败、修框架及开销失败证据均保留。

据此新增轻量counts/source-age观察，不采每attempt wall/CPU；原14源的native wall/threadCPU计时保持。轻量12项＋service适配20项共32功能/18评估检查本机通过，板端同32功能通过。正常路径新增CPU0.265907ms/墙钟0.266317ms、拒绝路径CPU0.145681ms、满16事件health快照CPU0.106084ms，所有比较均低于原0.5ms门槛；服务PID/原源未动、相机计数推进。此为合成开销前置，非实时收益或TTL改善。

新boot USB只读核对MCP01仍17ef:a03b/path1-1.2，但devnum从旧4变3；首个实时helper在任何生产切换前被旧编号前置拒绝。按真实新boot更新为devnum3，保留设备VID/PID和所有保护，重新版本化helper4260e299…，当前正在执行120秒轻量实时诊断（1ms为此前已测配置，重试关闭）。

重试离线父候选37＋67＋66通过；主任务修正拒绝后25ms实际退让、显式health/提交前撤回计数后39＋67＋66通过，第二任务复跑与5项独立反例通过。runtime/SFace默认接口、30ms/5ms/Yolo优先保持；诊断native_failed允许精确对照已准入但未提交的withdrawn计数，不把它们统算硬件失败。尚未板测新重试。第二任务正将轻量观察与重试做三方合并，独立测试后仍需合成开销重验，不直接套用light-1成本。

**组合重试＋light2＋1ms板测续验：** v3组合helper在生产切换前因复用旧`postpower-retry-launches`目录，被已有`launch-result.json`保护性拒绝；未覆盖旧记录、未启动试验。将启动命名空间改为独立`postpower-combined-launches`（helper SHA `ad0e9047…`）后，120秒前置复核通过：120.98秒，YOLO 9.886Hz、YuNet 3.232Hz、整板CPU 56.31%、USB告警0、自动回退verified。随后600秒候选SHA `67ceb160…`，每5秒121样本，RuntimeMax900秒/独立回退1200秒，且回退finalizer AST与短测一致。板测完整600.09秒（有效观测600.33秒），YOLO 9.953Hz、YuNet 3.073Hz、实采12.493Hz、CPU56.04%、native完成1845、USB告警0、YuNet硬超限0，吞吐/保护门槛通过；原服务回退verified，回退后进程112143、原unit SHA `84116d8f…`保持。**整体`passed=false`**：121个采样中第84个（约415秒）YuNet最后结果源帧龄1097ms，前后采样749ms/100ms；源帧输入/发布TTL丢弃、处理错误均为0；另有7个light2计数器确认的definite clipped gap intervals（下界已跨过TTL），不是单纯健康采样波动。不能写成长期时效通过。保留30ms/5ms，不延长30分钟；下一步分析该1次时效缺口及7个已观测发布间隙的边界证据后，再决定复测，禁止通过放宽阈值掩盖。过滤数值证据位于`/home/ghmd/aura-post-power-20261022/combined-v4-600-result-inspection.log`和`combined-v4-600-outlier2.log`；原始UART保持私有。

后续隔离取证候选`/home/ghmd/aura-yunet-retry-gap-audit-20261023`：原16事件混合环有1607次驱逐，不能定位间隙；light3在gap发生时最多保存32条由已有时间戳构造的纯数值记录，不增加每attempt clock。14项light测试通过，30,000次host合成publish×5的中位数基线10.509μs/次、候选10.398μs/次（仅host，不代表板上成本）。父light2目录未改；尚未与retry service合并，也未上板或启用。manifest/说明已建立，下一步先审查health JSON成本和板端0.5ms额外CPU门槛，未通过不得做下一轮长测。
