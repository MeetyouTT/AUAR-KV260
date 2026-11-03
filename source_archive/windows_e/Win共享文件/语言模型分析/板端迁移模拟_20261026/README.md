# Windows功能迁往KV260：离线模拟与迁移候选核验

日期：2026-10-26，按用户时区。目的：判断现有Windows功能哪些值得迁往板卡，未实施迁移或部署。

**结论：记忆存储/检索、上下文构建、对话规则、声纹模板管理已通过本轮离线功能验证，适合先做PS端迁移候选；单独VAD有历史实板计算余量证据。ASR和声纹特征模型本轮仅证实可在Windows CPU真实推理，仍需板端适配和整机负载实测。现有TTS候选各有内容或速度限制；27B与当前CUDA版OmniVoice不能按现方案原样搬到板卡。**

本轮没有可用的已配置ARM/PetaLinux仿真来宾：本机WSL列表只有docker-desktop，Docker引擎未运行。因此这是功能隔离模拟、CPU推理、静态ARM包核验和历史板测复核，**不是完整ARM仿真，更不是本轮新板测通过**。没有把Windows速度按任意倍数换算为A53速度。

## 1. 结果和证据等级

| 功能 | 本轮实际结果 | 迁移判断 |
| --- | --- | --- |
| 会话数据库、明确记忆、更正/遗忘 | 新建合成SQLite，进程重启后恢复；更正拒绝旧ACK；遗忘后上下文不再召回旧值；两会话不串事实 | 离线逻辑通过，优先迁PS；不是完整个人长期档案已验收 |
| 上下文与对话规则 | 标准库独立运行，保留上下文预算、未播放回复不入召回、称呼容错和思考路由 | 离线逻辑通过，优先迁PS；LLM生成本身未迁 |
| 声纹模板库/相似度决策 | 192维合成向量完成保存、重启、KNOWN/UNKNOWN/AMBIGUOUS和删除 | 管理/匹配逻辑可进入PS迁移候选，不代表真人声纹精度 |
| 单独Silero VAD | 本轮5组公开/合成输入通过基本起止检测；另有2026-10-21单独VAD历史板测 | 值得优先做板端候选，尚缺当前整机组合验收 |
| Paraformer INT8 ASR | 3段上游公开录音，各重复2次，6次均返回非空且同样本两次文本一致 | Windows CPU推理通过；板上延迟、内存和并发负载未证明 |
| ECAPA声纹特征模型 | 4段上游公开录音完成CPU特征提取；2条独立查询匹配对应公开说话人 | CPU算法路径通过；板上PyTorch/SpeechBrain依赖和速度未证明 |
| 轻量VITS TTS | 原有约30MB模型生成2段全新非零波形，但自动回识别有明显差异 | 仅波形合成通过，不能填内容/听音或板端迁移通过 |
| Kokoro INT8 TTS | 原有约114MB模型生成2段波形，回识别更接近目标；单线程合成RTF约1.16～1.58 | 可生成但速度仍有明显风险，暂不作为直接上板实时方案 |
| 当前OmniVoice | 执行原加载方法并注入“无CUDA”，得到`OmniVoice requires PC CUDA runtime` | 当前实现不能原样走PS CPU；未加载或重测OmniVoice模型 |
| 当前27B | 只读文件长度：14,403,496,864字节，约13.41GiB | 不能按当前常驻推理方案装入4GB板卡内存；未运行、读取或复制LLM权重 |

PS端执行属于板上运行；上述模拟不等于PL/DPU加速。语音模型的DPU量化、算子与编译兼容性，本轮没有验证。

## 2. 纯逻辑与回归结果

- [core.json](core.json)：7组集成场景通过，使用205条合成轮次、两份合成数据库，不读取真实用户库。
- 核心探针以Python `-S`执行，未加载NumPy、Torch、ONNX Runtime、Sherpa或SpeechBrain，说明这些控制/存储能力没有必须依赖电脑模型运行时的条件。
- 100次上下文构建在本机的中位数约1.22ms、P95约1.39ms；进程峰值工作集约27.26MiB。这些都是Windows数据，不是板端指标。
- 加载的18份业务Python源通过Python 3.9语法解析；[source_recheck.json](source_recheck.json)确认前后指纹未变。语法解析不代替Python 3.9实际执行和系统ABI验证。
- 最终**155项不同pytest用例通过**，另有26个subtest通过，分别计数，不合并夸大。

回归过程保留了环境失败：

1. [regression.log](regression.log)、[regression_summary.json](regression_summary.json)：153通过、2失败。两项HTTP测试被本轮最初完全禁用套接字的隔离规则阻止，不是业务断言失败。
2. [regression_http.log](regression_http.log)：只允许本进程自己绑定的127.0.0.1临时端口后，仍遇到沙箱WinError 10013。
3. 对具体回环测试执行获准的沙箱提升后，[regression_http_permitted.log](regression_http_permitted.log)、[对应摘要](regression_http_permitted_summary.json)：两项均通过。脚本继续拒绝外部连接，测试使用假ASR/LLM/TTS，结束时关闭测试服务。

最初Windows测试进程退出时出现第三方pyreadline3析构警告，原日志保留。没有把它当业务断言失败，也没有删掉失败记录。

测试入口：[run_regression.py](run_regression.py)、[probe.py](probe.py)。现有输出目录保留首次状态；需要重复完整实验时，应在`语言模型分析`下创建新的空输出目录并复制这几份小脚本，不复制业务库、环境或模型。`core`遇到已有合成状态目录会拒绝覆盖。

## 3. 真实CPU模型测试

### ASR

[asr.json](asr.json)：使用原项目`model.int8.onnx`，243,371,218字节，单CPU线程。

- 输入：上游`0.wav`、`1.wav`、`2.wav`，约4.53～5.61秒，不是用户录音。
- 六次识别约204～262ms；初次模型构造约6.79秒。
- 本机进程峰值工作集约572MiB，峰值提交约909MiB。进程内存包含Python/运行时和初始化，不是模型独占内存，更不是板上内存。
- 校验了非空输出、同样本重复文本和样本/模型哈希；没有人工标注WER，也没有测真实麦克风、噪声、插话或板端延迟。

### VAD

[vad.json](vad.json)：单独Silero v5，5组输入，包括静音、生成白噪声和3段加前后静音的公开语音。两个非语音输入均0起点，三个语音输入各形成一段并结束，输出PCM保持原始切片。

新复核的历史板测为[board_benchmark_v5.json](../../语音共享文件/deliverables/2026-10-21_environment_frontend/board_benchmark_v5.json)：

- **单独VAD**：墙钟RTF约0.164～0.203，即处理1秒音频约需0.16～0.20秒；20ms输入帧的feed P95约6.6～11.5ms。
- 不能据平均余量保证每帧达标：记录中最大单帧约20.1～30.0ms，强噪声例有一段语音被拆为两段。
- 这是2026-10-21隔离环境的历史数据，不是本轮重新上板或当前完整业务负载测试。

相对地，[GTCRN＋VAD历史板测](../../语音共享文件/deliverables/2026-10-21_environment_frontend/board_sdk_benchmark.json)的墙钟RTF为1.258、1.352、1.508，当前组合跟不上持续输入。不能把单独VAD的通过套给整个降噪组合。

### 声纹特征模型

[speaker_model.json](speaker_model.json)、[speaker_probe.py](speaker_probe.py)：在既有独立CPU环境运行，禁网，仅加载经现有manifest核对的本地模型，不调用下载/收集文件流程。

- 用原`EcapaEncoder.encode`执行；为避免写入模型目录，初始化改用只读本地checkpoint钩子，跳过嵌入推理不需要的分类器和标签checkpoint收集。
- 四份公开样本各约1.76～3.15秒；本机单线程编码约77～133ms。
- 同人跨句相似度约0.7295、0.6649，异人约0.0552、0.0060。
- 独立公开样本库固定使用0.6门槛和0.1分差做冒烟；不是生产门槛建议、正式登记或现场校准。这些短公开样本不满足正式登记的数据质量协议。
- 本机进程峰值提交约1196MiB，含完整Python/Torch/SpeechBrain环境；不能直接代表ARM实现需求。

## 4. 两个轻量TTS候选的结果

复用已有模型，未下载新模型、未切换正式声线。直接复用原`SherpaTtsBackend._build_tts`创建模型，跳过声卡查询、播放和异步播放入口。

| 候选 | 本机单线程合成 | 自动回识别观察 | 判断 |
| --- | --- | --- | --- |
| VITS aishell3，约30MB | 约118ms生成2.22秒、192ms生成5.03秒；8kHz | 两句相对目标的字符编辑距离4/6、7/15 | 合成快但内容核对差异明显，不能按“有波形”判语音质量通过 |
| Kokoro INT8，约114MB | 约2.84秒生成1.79秒、4.42秒生成3.80秒；24kHz | 两句字符编辑距离2/6、1/15；名字被转写为“西兰” | 内容较接近但单线程速度不足，不推断A53上的速度或实时性 |

证据：[VITS合成](lightweight_tts.json)、[VITS回识别](tts_content.json)、[Kokoro合成](kokoro_tts.json)、[Kokoro回识别](kokoro_content.json)。回识别依赖同一个Paraformer，是自动观察，不是独立人工听音质量评分；错误不能全部归给TTS。

第一次VITS尝试因Windows kaldifst不能打开中文路径下的FST失败，见[原始错误](lightweight_tts.log)、[失败记录](lightweight-tts_failure.json)。后续只把必要的非LLM TTS资源暂存到当前任务获准的ASCII目录，哈希校验后运行；VITS/Kokoro暂存均已删除。未创建任何目录联接，未复制虚拟环境或LLM。

Kokoro使用现有sherpa后端和官方示例中的`sid=0`；本轮没有进行音色筛选。[官方Kokoro用法](https://k2-fsa.github.io/sherpa/onnx/tts/all/Chinese-English/kokoro-multi-lang-v1_1.html)

## 5. ARM兼容条件与未验证项

[compatibility.json](compatibility.json)核查既有3份aarch64 wheel内7个ELF库，机器类型均为183（AArch64）；没有在本轮解包、安装或执行这些ARM库。

历史目标是aarch64、Python 3.9.9；曾有系统ORT Python包导入异常，后续独立ORT/Sherpa环境已有隔离板测。不能把“有ARM wheel”写成当前系统依赖已装好。

- ASR：需以板卡实际Python/系统库重新验证导入、加载、单句延迟、内存及视觉/UI共存。
- 声纹模型：本轮为Windows Python 3.12 CPU；现板端Python 3.9的PyTorch/SpeechBrain兼容性尚未解决或验证。声纹库逻辑的通过不替代特征模型通过。
- 记忆/上下文：已有匿名会话逻辑通过；用户已有的新个人长期记忆入口还需对齐。正式迁移要明确数据库单写者、备份/故障恢复和跨端协议，不能只是复制SQLite。
- 当前27B GGUF约13.41GiB，板卡DDR标称4GB，还要运行其他业务。[AMD KV260规格](https://www.amd.com/content/dam/amd/en/documents/products/som/kria/k26/kv260-product-brief.pdf) 本轮只读权重文件元数据，不读取权重、不做换页实验、不修改存储路径。
- 当前OmniVoice受CUDA加载门限制，见`compatibility.json`；本轮没有证明替换后能保留其音色。

## 6. 建议下一批上板候选

1. 先迁会话/记忆库、上下文与对话规则、声纹模板管理到PS。调整协议使板卡拥有状态，避免两端各自写不同的会话库；Windows先保留模型推理接口。
2. 单独VAD优先于整套降噪，保留原PCM前导、取消、回声保护和20秒预算，在当前视觉/UI负载下测每帧尾延迟和真人起止效果。
3. 用现有INT8 Paraformer做隔离板端候选，固定线程并记录启动、峰值内存、识别耗时及UI/视觉影响；通过后再接正式音频链路。
4. ECAPA特征提取单独解决ARM依赖；轻量TTS继续以内容、实际板端速度和可接受音色为条件，不能沿用本机波形生成成功宣称通过。

本轮没有登录或更改Ubuntu/KV260，没有打开麦克风或扬声器，没有启动正式8791/8792/8795/Ollama服务，没有访问真实个人库、改变监听选择、切换声线或改动业务源码。新增的是模拟脚本、合成/公开数据证据及分析索引。
