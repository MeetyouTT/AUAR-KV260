# 父侧集成接口（候选，未部署）

候选根为本目录candidate，路径均相对aura。正式A源码未覆盖，服务/模型/板卡未重启；没有主动加载或卸载模型。请一次性合并候选与父侧ModelHost改动后再做受控部署。

## 文件所有权

- common/gpu_coordination.py：纯标准库、内存采样/实际驻留探针、有限准入与延后事件缓冲。
- tools/cuda_memory_stats.py：TTS每次推理的allocator峰值，不新增同步、不加载模型、不改变音质参数。
- tools/selected_voice_service.py：VoiceWorker新增可选gpu_coordinator参数，非缓存请求准入；缓存不占槽，准入失败不破坏暖worker就绪状态。
- tools/voice_channel_source.py：LLM迭代租约、TTS等待期间有界排空，不改变240字/8192字节回复上限、原timeout或r6合成完成后丢弃旧结果的语义。
- board/runtime/audio/omnivoice_voice.py：新增cuda_inference统计；r9原合成后empty_cache完整保留，16步/seed8701/声线/精度保持。
- config/gpu_runtime.local.json：观察模式初始配置；未校准时不自动开启显存阈值强制。

## ModelHost初始化

在当前self.voice=VoiceWorker之前创建以下对象，保留既有self.root及其他初始化顺序。

```python
from common.gpu_coordination import (
    GpuCoordinator, GpuPolicy, NvidiaMemoryProbe, OllamaResidencyProbe,
)
gpu_config = json.loads((AURA/'config/gpu_runtime.local.json').read_text(encoding='utf-8'))
self.llm_residency = OllamaResidencyProbe(OLLAMA_HOST, MODEL)
self.gpu_coordinator = GpuCoordinator(
    GpuPolicy.from_dict(gpu_config), NvidiaMemoryProbe(gpu_index=0),
    llm_residency=self.llm_residency,
)
self.voice = VoiceWorker(self.root, python=python, model_path=model_path,
                         engine='omnivoice', gpu_coordinator=self.gpu_coordinator)
```

`channel_frames`已通过models.gpu_coordinator自动连接。模型`stream_factory`只在迭代时发HTTP，LLM准入在其之前。记忆直答/登记/视觉专用交换不假占27B槽。

健康接口可新增独立字段，保持旧ready含义及老测试的`__new__`兼容：

```python
if getattr(self, 'llm_residency', None) is not None:
    health['llm_residency'] = self.llm_residency.status()
if getattr(self, 'gpu_coordinator', None) is not None:
    health['gpu_resources'] = self.gpu_coordinator.public()
```

`ready`目前表示ASR/TTS就绪、Ollama可达且/api/tags有模型，不表示LLM驻留。新增`llm_resident`、`llm_gpu_resident`、`llm_gpu_bytes`来自/api/ps；不可用时是null，实际空列表才为false/0。不要将HTTP健康探针变为推理或预热请求。

父侧还应为ModelHost.answer内旧WAV接口的dialogue.build_response、ModelHost.warmup内直接27B预热套同一个LLM租约。沿用各自原绝对deadline，不能从准入后重新计时。旧WAV接口本来先完整LLM后TTS，没有首句重叠；目前候选只覆盖streaming channel，不能声称未集成的调用者已受保护。

更新common/voice_service_capabilities.SOURCE_FILES，新增common/gpu_coordination.py、tools/cuda_memory_stats.py、config/gpu_runtime.local.json；原选中的三个业务源已有指纹覆盖。需要父侧统一新revision/能力和启动器校验，不能拿r9的旧指纹宣称已加载新代码。

## 策略和调用签名

`GpuPolicy.from_dict(config)`只允许已知字段：mode、max_pending(1—8)、max_wait_seconds(0—5)、sample_max_age_seconds(0.05—5)、reserve_mib、llm_extra_mib、llm_cold_extra_mib、tts_extra_mib、tts_cold_extra_mib、gpu_uuid、calibration_id。

- observe默认模式：保留原LLM/TTS流水线，不强制未校准的显存门槛，仍维持每类最多1个GPU重操作。probe不可用只报告，不伪造显存。
- adaptive模式：必须显式给GPU UUID、校准标识、reserve>=128MiB、正数LLM/TTS预算；LLM冷加载预算不能小于驻留解码预算，tts_cold_extra_mib不能小于steady tts_extra_mib。旧配置遗漏冷TTS值时不能开启强制模式。
- serial模式仅用于隔离诊断，不能默认用它代替自适应并称延迟优化。

```python
lease = coordinator.acquire('llm'或'tts', deadline=原绝对时限,
                            cancelled=Event或无参取消函数,
                            cold=False, wait_deadline=可选共享准入截止)
with lease:
    ... # 不延长预算，不抢占另一所属任务
```

不足/采样失败时只在原预算内等，最多配置的5秒，之后GpuBusy；原deadline过期是TimeoutError，取消是InterruptedError。不会调用卸载、kill或任何模型管理API。取得TTS租约后直到原transport调用完成才释放，不能提前释放原生合成仍在运行的显存预算。

TTS warmup、worker不活/失败/隔离，或未确认同一Popen进程已完成非缓存工作时必须cold=True。VoiceWorker把暖态绑定到进程对象，不把缓存WAV当模型已加载。若steady准入等待时进程刚好退役，真正创建前的_worker_command会拒绝新建，释放steady额度并在同一绝对预算和同一准入截止内重新申请cold，未取得冷额度不会Popen。transport、原取消锁与所属退役逻辑没有改动。

父侧已测得一次cold warmup peak_reserved=4972347392、peak_allocated=4857359872、baseline=0，而稳态allocated约2039825920。这证明不能把约1.90GiB持有值或短句steady增量用于冷启动。tts_cold_extra_mib需覆盖未驻留进程的完整冷加载/预热峰值加余量；tts_extra_mib只覆盖当前暖进程的额外增长，分别校准。warmup_inference、cold_start_inference及steady last_inference单列，max_cold_reserved_peak_bytes不混入max_reserved_extra_peak_bytes。

准入时预留活动租约的未兑现峰值，容量评估偏保守。冷/未知驻留采用llm_cold_extra_mib；/api/ps确认模型驻留后，继续解码只算llm_extra_mib，避免已加载权重在TTS阶段重复计算。若常规对话因驻留权重挤满GPU一直拒绝，说明容量规划未解决，不能把有限拒绝当优化成功；需父侧调整项目所属11435的真实GPU余量/层offload并验证，不动11434或其他模型。

内存探针默认TTL250ms，单次CLI超时<=400ms且lock等待受调用剩余时限约束；失败缓存TTL内保持不可用。/api/ps健康缓存默认TTL2秒；`status(*,deadline=None,refresh=False)`让锁、连接、发送及整个头体读取共享一个绝对时限（最多400ms），读取最多1MiB，并以所拥有socket的shutdown定时器限制慢流。临近截止的短caller失败不会污染下一次完整探针预算的缓存。

LLM准入绕过2秒健康缓存强制刷新；TTS在将活动LLM的冷加载预留降为decode预算时，也需要本轮租约之后的新鲜驻留观测。失败、陈旧、采样早于本轮都按cold；观测序号区分Windows粗粒度时钟中相同时间戳的实际新请求。自定义测试探针的status应接受deadline和refresh关键词，不得无界等待。不存台词、身份、音频或私有模板。外部进程仍能在采样后分配显存或重启daemon，因此这并不消除TOCTOU，也不提供物理VRAM隔离或全系统永不OOM保证。

## 峰值校准

1. 记录GPU UUID、总量、现有其他模型PID/驻留、27B配置/2048上下文、OmniVoice声线/16步、实际Ollama版本与runner参数。`/api/ps=[]`是可利用的自然冷起点，不要为了测冷加载主动卸载其他模型。
2. 先仅observe重载所属语音进程。TTS warmup本来就强制合成“嗯，我在呢”；健康gpu_resources.tts_stats.warmup_inference将单列其峰值及是否包含CUDA初始化，不把它混成常规生成峰值。
3. 保持其他模型运行，用短/中/长公开非缓存句验证，确认cache_hit=false。`tts_stats.last_inference`记录baseline allocated/reserved、峰值及两种增量，`max_reserved_extra_peak_bytes`只包含实际非缓存生成。缓存命中和warmup各有独立计数。
4. 显存余量按TTS相对已驻留allocator的增量加安全余量确定；不能把已由free扣除的整份TTS模型再重复计一次。冷27B加载预算应覆盖其新增GPU驻留与解码峰值；驻留解码预算只算后续增量。现有两套/api/ps均空、GPU约2.3GiB已用的快照不是推理峰值。
5. 父侧验证实际启动层预留有效、常规问答不会永远拒绝后，写入测量ID/绑定GPU UUID并启用adaptive；再做同输入、非缓存、保持其他模型的延迟/峰值与取消对照。不得增加超时、改变音色/步数或降低校验来获得“通过”。

## 测试与已知边界

最终88项通过：新GPU/冷加载/有界缓冲、deadline锁/慢流、驻留TTL/本轮证据、冷TTS完整生命周期，以及原channel、worker生命周期/取消、服务健康、首句与延迟测试。首次68过/1失败保留在tests_first_failure.*：低余量时100ms排空周期使8槽队列每批token等待过久；候选已把有协调器时的future轮询改为10ms，原无协调器路径仍100ms。静态审阅后首次本轮证据测试暴露Windows时间戳相等，tests_deadline_ttl_first_failure.log保留；现用严格后继时间或新的探针序号验证。

真实只读探针通过（candidate_probe.json），没有真实推理A/B或峰值校准，没有部署。LLM/TTS合计容量、外部模型压力与真人听感必须由父侧整合验收。
