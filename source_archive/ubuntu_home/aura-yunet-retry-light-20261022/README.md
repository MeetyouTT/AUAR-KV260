# YuNet 有界重试＋轻量时效观察：独立合并候选

状态：**两个开关默认关闭，软件通过，未上板，未测新增成本，未常驻生产。** 不可把 light1 已有的开销结果套到本 light2 合并版。

这是独立三方合并，不修改父目录：原d03e人脸服务为共同基线；重试父为 `/home/ghmd/aura-yunet-retry-integration-20261022`（root修正版39项）；观察父为 `/home/ghmd/aura-freshness-light-20261022`（light1，32项）。准确来源/候选SHA见manifest和parents.json。runtime/dpu_yunet完整沿用重试父，scheduler/原metrics/thread observer无改。

## 合并后的调用与开关

构造为 `FaceTargetService(..., freshness_metrics=False, slot_retry=False, retry_clock=time.monotonic)`。两开关独立验证bool。False/False时health没有两个新增feature字段；各自True才分别增加freshness_metrics或slot_retry。生产camera_faces构造未修改，没有自动启用方。

保留观察父的 `process → begin → try _process → finally finish`，并把admission_check与精确SlotAdmissionDenied返回值穿过wrapper；重试每一次attempt都会经过观察，不将一整个重试round冒充单次推理。原200ms成功/无脸节拍保持。

重试保留root修正版：只有精确纯准入拒绝才追加最多两次新帧准备，25ms从拒绝记账返回后开始，200ms绝对截止仍保守锚定首个拒绝准入尝试开始。状态/TTL/截止在CPU前、编码后及native前检查，DPU时隙内state.lock非阻塞；没有新帧时在槽外Condition.wait。30ms硬限/5ms guard、YOLO优先和超限CPU回退保持。200ms仍是继续开始/提交截止，不能中断正在运行的CPU/native。

## light2 schema 与取消

schema升为 `aura-face-freshness-light-2`，不可用占位也使用该schema；保留计数、原source年龄、16事件和相邻空窗上下界，仍无额外每attempt wall/CPU时钟。

- SlotAdmissionDenied按slot_unavailable计数及连续拒绝，不是假无脸。
- 启用guard的AdmissionCancelled/OptionalJobDisabled使用outcome_code=6、event_code=9，增加cancelled及分原因计数，**不记process_errors或slot_unavailable**。
- cancel_reason_code仅为枚举：other=0、closed=1、expired=2、deadline=3、disabled=4、busy=5。异常值映射other，不记录异常文本、图像或身份信息。取消会中断连续slot拒绝段。
- guard已经准入后的撤回仍增加slot_retry.withdrawn_after_slot；native_attempt/failure诊断可以包含这种明确撤回。真实native异常及非零status保持原异常传播，并记process_errors；不把实际失败改成取消。
- retry等待阶段在attempt外到达deadline/closed，没有额外创建一次attempt，因此此时只增加retry计数，不凭空增加observer cancelled事件。原输入TTL门直接拒绝仍记input_ttl_discarded；准备中失效被guard撤回则记cancelled_expired。

source clock仍假定原monotonic millis，不能用独立钟识别前跳。提交后观测过TTL不等于原门接受过期输入。未观测头尾不外推；观察异常不能替换原业务结果或异常。

## 软件证据与复现

```bash
python3 -B /home/ghmd/aura-yunet-retry-light-20261022/run_tests.py
python3 -B /home/ghmd/aura-yunet-retry-light-20261022/run_tests.py --regression
python3 -B /home/ghmd/aura-yunet-retry-light-20261022/verify_merge.py
```

82项通过：重试父39项原测试、观察父12项light＋20项service测试（只适配新增exception依赖及容器基线路径，明确不是full23整套）、新增11项合并测试。新增涵盖四开关组合的成功/health/200ms/close、每attempt计数、拒绝连续段、最新帧成功、TTL/closed/deadline/disabled/busy取消、guard撤回、真实VART失败传播及observer异常。另有冻结身份67＋计时66项回归通过。容器network=none、无设备、只用fake runner/合成帧及虚拟时钟。首次20项错误来自测试基线绝对主机路径在容器不可见，已改为本候选精确d03e副本，失败日志保留，不充作通过证据。

verify_merge检查父SHA未变化、runtime/adapter精确继承、重试方法AST和原work/close/hooks继承、默认开关、仅四份基线改动、最终测试日志与所有Python语法。manifest冻结明确工件，不含私人错误日志。

## 尚需执行

先独立审查两个父差异，再对light2合并源码重跑板端无设备功能和额外CPU/墙钟开销，固定0.5ms门槛；需要给便携工具更新schema/PINS和取消完整性，不可直接拿light1工具或评估通过替代。通过后才进行单变量实板短诊断及逐级10/30分钟验证。正式配置、GIL、亲和性、音频、身份库和运动均未由本任务改动。
