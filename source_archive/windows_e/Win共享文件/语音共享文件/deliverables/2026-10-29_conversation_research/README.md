# 玩偶本地对话优化：联网调研与实验顺序

检索核对时间：2026-10-30 04:25 UTC（本地2026-10-29）。仅使用论文、官方项目源码、官方文档与官方仓库问题记录作技术依据。没有下载权重、安装依赖、接入外部服务、上传用户数据或操作现役设备。本报告完成的是调研，尚未执行下述新模型实验。

建议保留当前27B与OmniVoice16，先改善**结束说话的判断、分句供音余量、项目自身GPU准入**。更换全双工大模型会同时改变声线、对话行为和显存布局，当前16GB且保留其他模型运行的条件不适合直接替换。

## 先与本项目已有结果对齐

- 现役仍是voice r9，OmniVoice16按完整分句合成；源码明确它是分句流水线，并非模型原生逐音频token输出。已有参考音色prompt缓存，不能把“增加prompt复用”当成新优化。
- 最新供音IPC修复已部署，真实界面静音长句最大调度间隔18.28ms、0欠料；这不等于TTS/LLM首PCM已经提速或真人听感已验收。见[最新交付](../2026-10-29_audio_animation_polish/README.md)。
- r9实际有一轮双段回答测得约0.494秒模拟供给缺口。因此要分别检查“播放线程被阻塞”和“下一段还没合成好”。见[r9延迟报告](../2026-10-29_chat_latency/README.md)。
- 10月18的CosyVoice.cpp曾出现快速但内容错误的CUDA配置；保留25-token配置约0.63–0.65秒TTS首包，但自由回复数字/字词边界未验收。不能把该旧试验当成官方CosyVoice3或完整玩偶已通过。见[流式TTS验证](../2026-10-18_streaming_tts_validation/RESULTS.md)。
- 本机DFlash和原TTS CUDA Graph扩展A/B均未取得可采用的可靠整链路收益，不应因为网上吞吐数字再直接启用。见[既有试验](../2026-10-18_dflash_trial/README.md)。

## 适配现有项目的方案比较

下表“显存”指新增组件的方向性成本；没有本机测量的项目一律不填保证值。模型权重文件大小也不等于峰值显存或进程内存。

| 顺序与方案 | 对质量/体验的作用 | 延迟与显存 | 改动成本及判断 |
| --- | --- | --- | --- |
| P0：保持模型，记录分段到达与播放余量，有限预缓冲 | 避免先说一小句后等待下一段；保留原声线和字词 | 无新增GPU模型；可能用小幅首播等待换连续性 | 低；优先，需同文本/同PCM到达轨迹验证 |
| P0：项目GPU重任务协调 | 降低LLM解码和TTS峰值同时发生的机会 | 排队可能增加首PCM；必须测整体P95，不能只看显存下降 | 中；由GPU代理实现；不卸载其他模型 |
| P1：Smart Turn v3.2 CPU影子端点 | 根据语调和完整性补充静音VAD，减少“等一拍”和过早截句 | 官方CPU int8权重约8MB，中文在支持列表；运行内存与本机耗时待测 | 中；先影子预测，再与原700ms静音策略A/B |
| P1：现有声纹+人脸来源融合 | 给每轮对话留下当前说话者证据与不确定状态 | 先复用现有CPU ECAPA/板端人脸，不新增GPU模型 | 中；与身份代理集成，不把在场人脸自动当说话者 |
| P2：CosyVoice3官方实现 | 真正文本输入/音频输出双流，保留参考声线的可能性 | 官方称最低150ms，但不是本机成绩；峰值未知 | 高；与原音色、数字/长句和取消路径独立A/B |
| P2：Qwen3-TTS-12Hz-0.6B Base | 原生流式与参考音色克隆候选 | 官方最低97ms为TTS条件下首包，不能换算整链路；峰值未知 | 高；先小模型Base；API实际出包也须单独确认 |
| P2：原OmniVoice官方FlashInfer | 沿用原模型和参考音色的算子优化 | H100/FP16/32步官方基准不能套用5060Ti/16步；Graph占额外显存 | 高；原生Windows兼容性门槛未过，不直接装现役环境 |
| 后置：MiniCPM-o4.5/Moshi整套全双工 | 原生边听边说及主动交互研究方向 | 与现有27B共存空间不足或Windows支持受限 | 很高；不是当前增量修复路径 |

Smart Turn的官方说明为：与Silero等VAD结合，只在静音阶段判定；输入16kHz单声道、最多保留当前轮最后8秒，不宜在极短片段上反复推断。官方速度是参考环境数据，本机CPU已有ASR/VLM/声纹任务，仍须实测。可只移植本地ONNX调用，不必换整个对话框架。[官方模型](https://github.com/pipecat-ai/smart-turn)、[官方本地实现](https://github.com/pipecat-ai/pipecat/blob/main/src/pipecat/audio/turn/smart_turn/local_smart_turn_v3.py)。

CosyVoice3的官方代码支持双流与参考音色克隆，0.5B-2512发布在2025年12月；本次找到的仓库已从FunAudioLLM重定向至QwenAudio。官方公布的低延迟不解决本项目旧移植后端的内容问题，必须用官方实现重新验。Qwen3-TTS于2026-01-22发布0.6B/1.7B版本；克隆应选Base，不能用预设声线模型冒充原汐蓝音色。两者都不能未经听音直接替换。[CosyVoice官方](https://github.com/QwenAudio/CosyVoice)、[Qwen3-TTS官方](https://github.com/QwenLM/Qwen3-TTS)、[技术报告](https://arxiv.org/abs/2601.15621)。

## 同声线加速的关键限制

OmniVoice官方新增FlashInfer路径，针对batch=1建议可选CUDA Graph；官方H100/FP16/32步测得约2.4倍，但并未给出本机5060Ti16步及其他模型共存的成绩。当前FlashInfer安装文档明确Linux only，官方问题#3786还记录了Windows依赖阻碍。因此它是可研究的隔离后端候选，不能视为当前Windows环境的一行开关。[OmniVoice官方加速说明](https://github.com/k2-fsa/OmniVoice#flashinfer-acceleration)、[FlashInfer安装条件](https://docs.flashinfer.ai/installation.html)、[项目问题记录](https://github.com/flashinfer-ai/flashinfer/issues/3786)。

阅读官方加速源码还发现：非分桶Graph按输入形状缓存，持有静态buffer、logits及独立工作区；源码另有duration bucket选项。**推断：**持续自由对话若不断遇到新形状，必须先限制缓存和时长桶，再评估常驻峰值。源码的“lossless”宣传不能代替本项目音色/内容验收，也不能假定empty_cache会释放仍被Graph引用的对象。[官方源码](https://raw.githubusercontent.com/k2-fsa/OmniVoice/master/omnivoice/models/omnivoice_flashinfer.py)。

PyTorch官方区分活动张量显存与缓存显存；empty_cache只归还未使用缓存，不能腾空仍在用的模型。Ollama官方还说明并行数会按并行数×上下文扩展内存，并可能在空间不足时排队或卸载空闲模型。**本项目推断：**应在项目请求入口做有限队列/预算和取消交接，保持单slot/2048及其他模型；不能靠扩大全局并行或循环卸载掩盖冲突。对其他程序的未知未来分配，应用层检查不能承诺全系统永不OOM。[PyTorch显存语义](https://docs.pytorch.org/docs/main/notes/cuda.html#memory-management)、[Ollama并发说明](https://docs.ollama.com/faq#how-does-ollama-handle-concurrent-requests)。

## 唤醒、插话、持续身份与视觉

现有隔离KWS已经使用官方2025-12-20中英3M模型，所以“换成这个新模型”不是新方案。官方允许关键词逐条boost/threshold，但两者直接影响召回与误触发。下一步应补真实“汐蓝/欸/哎”正样本、相近词/电视声/玩偶自身声负样本和每小时误唤醒率；不能以调低阈值将旧失败填成通过。短“哎/欸”可作为注意力候选，是否启用须单独验收，不能解锁个人记忆。[官方KWS机制](https://k2-fsa.github.io/sherpa/onnx/kws/index.html)、[官方模型列表](https://k2-fsa.github.io/sherpa/onnx/kws/pretrained_models/index.html)。

原有Speex/AEC参考时钟先保留。WebRTC AEC3可作为之后双讲/回声鲁棒性对照，其原生接口区分render与capture并提供延迟信息；它不是“换库即支持自然插话”。当前自打断按用户反馈已解决，优先验新供音链路和参考完整性，不盲改阈值。[AEC3官方接口](https://webrtc.googlesource.com/src/+/master/modules/audio_processing/aec3/echo_canceller3.h)。

声纹确定“哪个已登记声音”，活跃说话人检测确定“哪张脸正在说话”，两者应分层。Light-ASD的CVPR2023论文给出约1M参数/0.6GFLOPs，可作为TalkNet之外的轻量声画候选；那是论文基准，不是本机吞吐或身份精度。[作者代码](https://github.com/Junhua-Liao/Light-ASD)、[论文](https://arxiv.org/abs/2303.04439)。

更近的2026-10-23预印本ROAM-ASD-CR将登记语音表征加入声画判断，研究了无可见目标时的发声人识别，方向与“视觉补充语音”相符。本次未确认可直接部署的权重/实时Windows接口，故仅跟踪，不加入现役。[论文](https://arxiv.org/abs/2610.33127)。

**本项目建议（推断）：**每轮都可持久记录为匿名会话；身份另存候选、已确认、冲突、过期及来源版本。人脸不在镜头内不阻止对话；有视觉时只提供新的辅助证据。多人/旁人/播放回声/换相机epoch时不能沿用上一人的归属。自动识别结果与个人记忆访问授权分开，不能用最高相似度或在场人脸直接解锁档案。

## 时间轴记忆怎么继续

当前SQLite来源/更正/遗忘与派生日摘要已经存在，应优先补“事件何时发生”与“何时被系统记录”的区别，以及current/historical/transition状态。2026年A-TMA论文专门讨论新旧事实混在召回中的ghost memory；它提出分开检验存储、检索、回答三层。此思路可用于项目现有来源链的验收，不要求换库。[A-TMA论文](https://arxiv.org/abs/2607.01935)。

Graphiti提供事实有效期、来源和混合检索，但需要图数据库、LLM及embedding等配套，自带查询治理也需应用实现。当前不宜把其论文速度套用到现有本机系统，或将私有记忆交给默认云服务。[官方框架](https://github.com/getzep/graphiti)、[Zep论文](https://arxiv.org/abs/2501.13956)。

可先做CPU上的时间/说话者过滤和FTS5候选检索，仍由权威原文与删除版本裁决。中文需验证分词：FTS5 trigram全文查询对少于3个Unicode字符不匹配，像“杯子”不能只靠这个索引；短词保留原匹配或独立中文token策略。[SQLite官方说明](https://sqlite.org/fts5.html#the_trigram_tokenizer)。

## 不适合当前直接上线的方向

MiniCPM-o4.5标准PyTorch全双工演示要求至少28GB显存；官方另列C++量化低资源路径至少12GB，并承认发音与中英混合等局限。**推断：**即使量化版独立可用，也不代表能与现有27B和其他模型在16GB里同时运行。Moshi官方PyTorch说明需约24GB显存，Windows没有官方支持，命令行客户端还不包含AEC。两者均后置为整套架构实验。[MiniCPM官方要求](https://github.com/OpenBMB/MiniCPM-V/blob/main/docs/minicpm_o4dot5_en.md#web-demo-deployment)、[其2026-04-30论文](https://arxiv.org/abs/2604.27393)、[Moshi官方](https://github.com/kyutai-labs/moshi)。

算术/日期等确定性问题也应优先走受限工具校验，而非仅换“更会思考”的模型；项目旧试验实际出现58×3被回答为156。它是质量缺陷，不能用首PCM更快掩盖。工具路由不应开放任意Shell/Python执行，仍需具体需求的回归。

## 建议先做的三个实验

1. **同模型连续性与GPU准入A/B**：固定公开短/中/长文字与无缓存TTS，比较原分句、有限预缓冲和项目GPU准入策略；采集每段文字就绪/合成起止/PCM到达/播放余量。要求内容、参数、取消边界保持，新增等待明确计入首PCM，零中途缺料；不用缓存短答或等待提示充当有效回答。
2. **CPU语义端点与身份事件影子评估**：Smart Turn先不控制正式状态；用停顿、犹豫、长句与换人/失脸事件，比较原700ms端点及新建议的漏截/误截、轮次来源与CPU时延。身份的已确认/未知/冲突分别评分，不将未知算作错误姓名，也不将所有最高分算成功。
3. **真正流式TTS隔离对照**：先复用D盘已有CosyVoice候选资料定位质量问题，再选官方CosyVoice3或Qwen3-TTS-0.6B Base之一。通过预算与平台门槛后，做数字/单位/名字/短句/30秒长句、声线盲听、取消接话及首PCM/间隙/峰值的A/B。原正式声线继续服务；本次调研不执行新下载、模型加载或替换。FlashInfer另先做Windows/隔离Linux可行性判定，不以此实验名义改现役环境。

实验边界、停止条件及验收指标见[EXPERIMENTS.json](EXPERIMENTS.json)，来源与已知发布日期见[SOURCES.json](SOURCES.json)。

现役Ollama 0.40.13的进程专属显存余量、单位、重启边界和WDDM限制已另行核对，见[只读补充报告](OLLAMA_VRAM_RESERVATION.md)。
