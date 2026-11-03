# 并行候选整合只读审阅

审阅时刻：2026-10-30 04:54 UTC（洛杉矶仍为2026-10-29）。这是源码静态审阅，不是部署或整机验收。没有运行真实模型、访问板卡、录音、播声、修改候选、环境或官方调研结论。新增匿名身份绑定增量不在本次冻结基础范围内；人脸、声纹和姓名绑定仍不能自动取得个人记忆授权。

后续状态：GPU代理已反馈完成驻留探针deadline与强制刷新两项P2候选修复并通过其79项回归；父侧正在整合。以下表格和SHA保留原审阅快照，不把该反馈当作本子任务已完成最终整合复测。冷TTS新增预算与启动接点另见STARTUP_VRAM_UNLOAD.md。

## 需要父侧处理的接点

|级别|位置（候选内行号）|具体问题与建议|
|---|---|---|
|P1，父侧已确认正在修复|parallel_interaction/candidate/windows/tools/board_model_host.py:255–269|旧WAV `answer()` 在ASR和准入后重新使用完整 `budget_ms` 申请LLM租约；LLM调用没有剩余时限，TTS使用默认 `generate()`。外层最后才检查预算，新增等待可能超出原请求预算。应由 `do_POST` 传同一绝对deadline，LLM传剩余预算，TTS用 `generate_bounded`；补充“ASR已耗时、准入失败不启动TTS”的测试。父侧已表示将修复，本审阅未宣称已验证修复后的哈希。|
|P2|gpu_coordination/candidate/common/gpu_coordination.py:92–117、213、257|`OllamaResidencyProbe.status()` 的锁无等待时限，HTTP固定0.4秒，准入调用未传剩余deadline。仅剩10毫秒的请求仍可等待约400毫秒；健康刷新持锁时还可能多等一次刷新。将锁等待、连接及读响应放入调用剩余预算，或准入只读缓存、独立刷新；过期返回未知并采用冷预算。`NvidiaMemoryProbe` 已限制锁和子进程等待，不要在修复中退回无界采样。|
|P2，强制策略启用前验收|gpu_coordination/candidate/common/gpu_coordination.py:99–117、173–177|驻留探针缓存2秒，`_llm_extra()` 仅检查 `llm_resident`，不检查驻留证据年龄或所属daemon是否变化。曾驻留模型自然卸载或daemon重启后，缓存短暂仍可按warm预算接纳真正的冷加载。建议LLM准入时取得足够新的驻留证据，未知/过旧/所属实例改变按cold；补“曾驻留→自然空载→下一请求”用例。即时采样也不能消除外部进程并发分配的TOCTOU。|
|P2，生命周期限制|speaker_visual_cooperation/candidate/tools/speaker_turn_host.py:78–117；tools/speaker_turns.py:16–24、52–86|取消只标记Event/终态；排队job的PCM要等工作线程处理/遗忘才释放，当前不会立即清引用。hub的12秒分析TTL只阻止迟到写回，不中止已执行的CPU `analyze(meta,pcm)`，它仍持PCM到返回。建议立即释放已取消排队项的PCM，并验证活动CPU调用慢/阻塞时文本对话继续、旧结果不写回。不能把12/14秒标为原始PCM硬删除时限。|

原始PCM生命周期进一步限定：`speaker_capture_scope` 在交接或退出时清自身引用，HTTP handler自己的 `pcm` 局部变量仍可存在到请求结束；loopback编码/解码和CPU调用也有临时引用。`maximum_ram_jobs=3` 是recorder持有的任务上限，不能表述为整机只有3份PCM。未发现本增量将原始PCM、声纹向量或人脸像素写入归属SQLite表。

## 已检查且未发现阻断的问题

- LLM事件队列8槽；延期缓冲最多1024事件/64KiB；GPU等待队列默认2项、上限8项；recorder最多3个RAM任务/2个排队项；hub结果最多256项且CPU分析门禁只有1个。TTS等待时继续有界排空LLM事件，LLM租约先于EOF入队释放，避免队列满导致的互等。
- TTS非缓存请求在 `finally` 释放租约；准入失败不把暖worker标为故障。现有r6语义仍是完成当前受限原生合成后丢弃断开客户端结果，并由最终清理处理超时/退役；没有为了插话提前释放正常活动TTS预算。缓存不占新推理槽有合理依据。
- speaker捕获使用线程局部作用域，核对完整context/cid后只交接一次。归属回写按原request/context/cid核对，终态不被普通迟到结果复活，记忆版本变化改为取消。旧的已播放轮次可以独立完成描述性分析，这是明确设计，不能误当新一轮身份。
- `personal_memory_allowed` 强制为false；视觉标记不是主动说话者证明，声纹连续三次候选也不是凭据。`turn_profile()` 重新检查原本授予的可撤销grant；个人选择过期/撤回后归属回写取消。未发现候选自动选择个人档案的路径。
- 冷/未知LLM预算与驻留解码预算已经分开；活动LLM从冷转驻留后预算会下调，避免把已加载权重始终双算。TTS模型常驻已体现在设备free里，实测预算应计后续增量和余量。串行并不释放27B权重；普通请求永久因显存不足被拒绝不能算优化通过。
- 父侧 `gpu_runtime.local.json` 当前是 `observe`。它不强制未校准的显存门槛，因此现阶段不能宣称已经解决显存争抢；adaptive需要冷加载、驻留解码、TTS非缓存峰值和所属11435真实offload余量验收。没有建议动11434或其他模型。

## 最小补充验证

1. 使用假时钟/假探针验证剩余预算小于探针刷新耗时、健康探针持锁，以及原ASR已消耗大部分预算；没有新的推理在超时后启动。
2. 使用受控夹具覆盖recorder排队取消、活动分析超时、撤回个人grant、记忆版本变化；确认原始turn唯一归属、终态不复活，排队PCM尽快清引用。
3. 整合后检查LLM/TTS成功、错误、准入拒绝、断开四种路径active/queued回到0；实际显存校准再区分自然冷加载和已驻留请求。以上静态审阅不替代真实延迟、声音连续性、识别准确率和整机验收。

## 读取时版本

以下SHA-256标识本次读取快照；其他代理仍可能继续提交候选。行号随父侧修复变化，需要复核最终整合源。

|相对deliverables路径|SHA-256|
|---|---|
|2026-10-29_parallel_interaction/candidate/windows/tools/board_model_host.py|`a23e3111c69904481bccdea56a63f7e3c859588a66c79c38b71f9e4b3640df1e`|
|2026-10-29_parallel_interaction/candidate/windows/tools/speaker_capture_scope.py|`b5a11963927db2544c309f7add18aee79d60a568e3bbee74644ba664f6ab5b70`|
|2026-10-29_gpu_coordination/candidate/common/gpu_coordination.py|`b90d647dafef9297aec59ff1f5be371083c5995128786cb22d40a2c2682f41d4`|
|2026-10-29_gpu_coordination/candidate/tools/selected_voice_service.py|`f7a01b01d963bcb967d9cdec90a7752fc91a264a3ae823dfe443ba50ae8d7dff`|
|2026-10-29_gpu_coordination/candidate/tools/voice_channel_source.py|`2de193f98ab1348db24009a7a03c4f74ebd128d230e1ce677ba4eaed4f187a2f`|
|2026-10-29_speaker_visual_cooperation/candidate/tools/speaker_turn_host.py|`60a740b9e4110bed75d1c7c5a836778f683702877f31579126f0277d4fcba554`|
|2026-10-29_speaker_visual_cooperation/candidate/tools/speaker_turns.py|`554777a6e476134f9b22b19ddc21622f5dbf6f68f314cd341e10cacda381348f`|
|2026-10-29_speaker_visual_cooperation/candidate/common/conversation_store.py|`6670ffb06fefa86fee534d416c47e9da83c7ddffc75cfa87a27cc0754645a41d`|
|2026-10-29_speaker_visual_cooperation/candidate/common/speaker_turns.py|`7d10ce5fa2b9dffbcf291c1ab03619f0e21687cb53c455e799a691e2a2d47783`|
|2026-10-29_speaker_visual_cooperation/candidate/common/speaker_visual.py|`e8a732ae13bfb5e73346d9b26ced78fba25861cda37a9e3ff922e0185373e7e1`|
