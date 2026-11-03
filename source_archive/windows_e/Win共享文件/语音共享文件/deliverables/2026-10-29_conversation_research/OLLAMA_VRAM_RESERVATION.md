# Ollama 0.40.13：项目进程显存余量核对

只读核对，2026-10-30 UTC。本轮未改环境、重启进程、启动模型或下载文件。实际版本由父代理读取11435 `/api/version`确认为0.40.13；本文同时读取对应官方tag，未用main源码代替现役结论。[官方发布v0.40.13](https://github.com/ollama/ollama/releases/tag/v0.40.13)对应04088e7，发布页显示2026-10-28。

结论：**当前GGUF llama-server路径不要把`OLLAMA_GPU_OVERHEAD`当成有效显存隔离；可在仅项目所属daemon的环境中评估`LLAMA_ARG_FIT_TARGET`，但必须验证实际加载布局与峰值。** 纯串行不会归还仍驻留的27B权重，应用层排队也不能保证未知外部程序不再分配显存。

## 设置的单位、作用与边界

| 设置 | 实际单位/含义 | v0.40.13中的边界 |
| --- | --- | --- |
| `OLLAMA_GPU_OVERHEAD` | 每GPU的字节数，十进制uint64，默认0；例如3221225472表示3GiB，`3G`不是合法值 | envconfig存在；当前GGUF路径未完整传给llama.cpp的fit目标，不可单靠它预留TTS空间 |
| `LLAMA_ARG_FIT_TARGET` | MiB；例如3072表示3GiB，单个值用于各设备的目标余量 | 影响自动布局估算，不申请一块占位显存、不形成配额；示例不是本机已确定的安全预算 |
| `LLAMA_ARG_FIT` | `on/off`，上游默认on | 对未显式指定的布局参数做fit；关闭会失去这层自动调整，不建议为解决预算而关闭 |
| API `options.num_gpu` | GPU卸载层数，不是GPU数量或字节上限 | `-1`默认让后端自动选择；`0` CPU；正数生成`-ngl N`，显式布局可能越过自动fit可调范围 |
| `options.num_ctx` / `OLLAMA_CONTEXT_LENGTH` | token上下文容量 | 影响KV/计算缓冲，不降低模型权重本身；本项目保持2048，不以缩小能力范围冒充显存优化 |
| `OLLAMA_NUM_PARALLEL` | 同模型并行slot数 | v0.40.13将`num_ctx × parallel`传为runner上下文；项目保持1，不扩大并行 |

单位解析可直接核对[v0.40.13 envconfig/config.go，Uint64/GpuOverhead/AsMap](https://github.com/ollama/ollama/blob/v0.40.13/envconfig/config.go#L271-L303)。`GPU_OVERHEAD`是预算概念，语义上也不是CUDA物理占位分配。

## 为什么GPU_OVERHEAD在此版本不够

在[v0.40.13 server/sched.go](https://github.com/ollama/ollama/blob/v0.40.13/server/sched.go#L619-L630)，`FreeMemory - GpuOverhead - MinimumMemory`被用来打印available日志，接着仍把原loadGpus传给`llama.Load`。仅看到日志中的overhead非0不能证明实际offload已经留出相应余量。

对应[v0.40.13 llm/llama_server.go](https://github.com/ollama/ollama/blob/v0.40.13/llm/llama_server.go#L691-L726)的`extraEnvsForStart/mmprojFitTargetMiB`只处理多模态projector余量，没有把GpuOverhead加入fit目标。官方[问题#18679](https://github.com/ollama/ollama/issues/18679)与[修复PR#18680](https://github.com/ollama/ollama/pull/18680)在本次浏览中均显示Open；本文的判断同时由已读取的v0.40.13源码支持，不只依赖问题报告。

该tag会继承所属daemon环境给runner；无projector时返回原extraEnvs，用户的`LLAMA_ARG_FIT_TARGET`可以继承。`num_gpu=-1`不传`-ngl`，让后端选择；正数和0分别显式传层数或CPU。上下文是`-c num_ctx*numParallel`。这些都属于加载布局，并非每次TTS开始时动态重分配。[v0.40.13启动参数与环境](https://github.com/ollama/ollama/blob/v0.40.13/llm/llama_server.go#L368-L478)。

llama.cpp官方将fit定义为调整未设置参数，fit-target按MiB转换，单值广播到设备；当前上游文档的默认目标是1024MiB。**本轮未执行安装的llama-server二进制，因此默认值/开关仍须用该二进制的`--help`只读核对，并以实际runner日志确认。** [上游参数文档](https://github.com/ggml-org/llama.cpp/tree/master/tools/server)、[解析源码](https://github.com/ggml-org/llama.cpp/blob/master/common/arg.cpp)。

## 怎样限定为项目11435，而不改11434

本地只读查看的`deliverables/2026-10-18_board_dialogue/project_ollama.py`已通过`Popen(env=...)`独立指定HOST=11435、D盘模型库、NO_CLOUD、单parallel/单model/2048；没有显式设上述两个预留变量。它仍继承父进程其他环境，本轮没有读取活动daemon的整个环境块，不能据此断言当前变量一定为空。

如果后续实施，设置应进入**只创建项目daemon的env副本**，而不是写用户/系统全局环境。Windows子进程继承创建时的环境，修改外部shell或启动器文件不会改变正在运行的daemon。此启动器`ready()`成功立即return，所以单纯修改配置再运行ensure也不会应用新值；需要父代理在空闲保护下仅重启所属11435，并确认PID/创建时间/命令行归属。不要按官方一般“退出托盘Ollama”说明去停止属于另一套11434的进程。[Microsoft进程环境规则](https://learn.microsoft.com/windows/win32/procthread/environment-variables)、[Ollama Windows配置说明](https://docs.ollama.com/faq#how-do-i-configure-ollama-server)。

**作用域推断：**只为项目进程创建env不会改另一套11434的环境、调度表或已有runner，也不需要它重启。但两个进程共享同一张物理GPU，项目加载时消费显存仍会改变另一套进程所见的free和性能；这不是互相隔离的硬件分区。

## TTS 1.9GiB与WDDM测量

TTS已驻留部分通常已经扣在LLM加载前的设备free里。额外fit目标应根据**TTS实际峰值减去已驻留部分**、其他已知增长和安全余量制定，不能只把1.9GiB再次机械相加，也不能仅看空闲值推断整个合成峰值。

GPU代理的`idle_audit.json`在该次采样中两套`/api/ps`均为空；那是“daemon运行而模型当时未驻留”，不能把CPU VLM的llama-server进程当成27B runner，也不能拿空闲状态当27B与TTS共存峰值。本轮没有为验证预算主动加载27B。

NVIDIA官方说明，WDDM下逐进程`usedGpuMemory`可返回`NVML_VALUE_NOT_AVAILABLE`，因为由Windows KMD管理。不能把N/A当0，也不能靠逐进程数相加算整卡剩余。应同时记录整卡total/free、TTS进程自己的allocated/reserved峰值、Ollama实际GPU层与buffer日志，以及失败/延迟结果。[NVIDIA NVML字段说明](https://docs.nvidia.com/deploy/nvml-api/latest/api/structnvmlProcessDetail__v1__t.html)、[PyTorch显存计数边界](https://docs.pytorch.org/docs/main/notes/cuda.html#memory-management)。

## 交给集成的验证条件

1. 保留原27B权重/量化、2048、单slot及声线16步。先核对安装runner的fit帮助和实际加载命令；不要把`OLLAMA_NUM_GPU`等未定义环境变量当作设置，正数层数用API的`num_gpu`才是明确接口。
2. 若项目决定采用FIT_TARGET，只改项目daemon的创建环境。实际加载后记录层数、CPU/GPU buffer和剩余显存；再测同一公开短/长TTS的峰值与LLM/TTS相邻请求，并计入可能增加的CPU卸载延迟。
3. 不用“overhead日志非0”“模型加载成功”或某一次空闲free来填通过。若外部模型增长或实际峰值超过预算，保留有界排队/拒绝与明确错误；不能卸载其他模型来掩盖条件不满足。

因此可以改善项目的显存布局与失败边界，但本轮资料不支持承诺任意外部并发下永不OOM、所有请求固定低延迟，或不改实际布局就使27B驻留权重自动缩小。
