# Windows GPU协调候选：待父侧整合和峰值校准

本子任务完成候选实现和88项相关回归，未部署、未重启/卸载/主动加载模型，没有访问板卡、开麦、录音或播声。正式A中三个原业务源相对初次基线的SHA见PROGRESS（父侧可能已开始集成）；其他模型和D盘存储保持。

发现：现有完整请求锁和单TTS执行器并不禁止同一轮27B解码与首句TTS重叠。直接套串行锁会与8槽LLM事件队列背压形成死锁。现有health通过/api/tags确认文件可用，不能说明实际驻留；本轮只读/api/ps两套均为空，TTS约1.9GiB allocated，GPU约2.3GiB使用，这些是空闲快照，不是推理峰值。

候选支持项目内每阶段单操作、有限排队、取消和原绝对时限；自适应策略有余量时保持流水线，低余量时有限等待或明确拒绝，不杀进程或卸载其他模型。默认observe不启用未经校准的硬阈值。强制模式必须提供GPU UUID、测量ID及冷加载/解码/TTS额外峰值预算。

TTS等待期间有界排空生产者事件至64KiB/1024事件，保持顺序并允许LLM租约完成。新增TTS allocator峰值，预热、非缓存生成和缓存命中分别记录，保留r9 empty_cache及r6原生合成完成后丢弃旧结果的暖态交接。

最终tests.xml与tests_tts_cold.log为88通过，涵盖原channel、worker生命周期/取消、健康、首句和延迟路径及新准入/冷加载/缓冲检查。增加锁和HTTP共用绝对deadline、慢流及驻留TTL跨卸载验证；LLM准入强制刷新，降活动租约预算需本轮新鲜观测，仍不消除TOCTOU。冷TTS单独预算，真正Popen前守卫覆盖准入后退役竞态，同一原deadline及准入截止内升级额度；冷启动、warmup、steady峰值不混合。首次100ms排空周期导致低余量测试超时的tests_first_failure.*及Windows粗时钟首次测试失败保留；当前协调路径10ms排空、旧无协调器路径100ms。candidate_probe.json和idle_audit.json是只读实测；真实warmup/长句校准由父侧执行，不是本子代理测试。

精确ModelHost接点、配置字段、旧WAV/预热调用者、校准及容量规划要求见INTEGRATION.md。显存不足导致普通问答持续拒绝不算优化完成；父侧会用保持其他模型运行的公开非缓存问答校准，并核对项目11435实际offload余量设置。采样后外部进程仍可分配显存，因此不能承诺全系统永不OOM。

文件清单与哈希见SOURCE_MANIFEST.json，阶段状态见PROGRESS.json。不得重跑prepare_candidate.py覆盖现有候选或用候选报告冒充已部署。
