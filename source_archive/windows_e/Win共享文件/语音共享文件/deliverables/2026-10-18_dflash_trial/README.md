# 保留27B的独立加速实测（2026-10-18）

本轮已获用户同意进行独立对照。结论：**暂不向正式通道接入DFlash、TTS权重搬移、CUDA缓存清理或TTS CUDA Graph。** 这些方案在当前RTX 5060 Ti 16GB上没有表现出足够可靠的完整语音收益。原27B、量化精度、推理参数、声线和既有正式通道保持。

唯一的原配置增补是 `aura/config/model_storage.local.json` 中的 `draft_directory`，用于记录项目外候选草稿位置，不启用候选，也不改变原目标模型或Ollama目录。

## 实际完成的工作

- 从固定revision下载DFlash2 Q4_K_M草稿，文件1,143,006,816字节，SHA256核验通过。目标27B的原文件SHA256在每组独占实验前重新核对。
- 使用已安装的同一llama-server build `b1-620d2225c` 和CUDA v13后端，独立监听127.0.0.1:51888。核对原模板、2048上下文、单slot、原GGUF路径、GPU完整加载，保留原GBNF与采样参数。
- 对照DFlash关闭/开启的原27B，另测原OmniVoice16完整通道；没有用缓存音频冒充重新合成，没有实际向玩偶播放测试片段。
- 测试TTS闲置时CPU停车、仅释放闲置CUDA缓存，以及CUDA Graph，包括6种不同闲聊内容的24次扩展验证。
- 每组只在板端和电脑语音空闲时临时暂停电脑8792与其TTS子进程、卸载项目目标模型；实验后原启动器恢复。未修改板端源码、FPGA overlay、DPU或ASR服务。
- 恢复检查使用动态视觉健康接口，确认原ASR、27B回复、16步TTS配置及YOLOX视觉健康。`restored.json`是最终状态，不把启动命令成功当成恢复完成。

## 结果

下表均为本机实验，不是5090 Laptop测试，也不是“用户说完到实际出声”的声学测量。

| 实验 | 数据 | 决定 |
|---|---|---|
| 原27B单独运行，DFlash ABBA | 普通聊天台词就绪中位数：原路径886.64ms，DFlash1069.28ms，各6次；自由生成措辞有差异，不是固定台词的因果提速实验。两个贪心探针输出一致 | 短聊天没有可采用的收益 |
| 27B + 原OmniVoice16完整主机通道 | 原路径两次首PCM4905.90/1896.21ms；DFlash7541.52/6165.71ms。每次实际TTS、缓存未命中，未播放。首次可能含GPU驻留暖机，各组回复不同，不能宣称稳定倍率 | 当前16GB不采用GPU DFlash |
| TTS闲置CPU停车，ABBA | 首PCM中位数：常驻2038.57ms，停车2669.57ms，各4次；同输入的回复与PCM哈希均一致。每次模型搬运约增加1秒，且个别诊断字典被后续阶段引用更新；原始首PCM/语音数据不受影响 | 保留GPU常驻 |
| 仅清理未用CUDA缓存，ABBA | 首PCM中位数：常驻2022.82ms，清理2018.89ms，各4次，PCM一致；仅约4ms差别 | 没有可靠收益，不采用 |
| CUDA Graph初探，ABBA | 首PCM中位数：常驻1799.13ms，Graph1610.42ms，各4次，PCM一致；包含重复形状复用 | 仅初步线索，未据此上线 |
| CUDA Graph扩展验证 | 6种内容、共24次；首PCM中位数：常驻1648.21ms，Graph1630.83ms，各12次。6种内容的回复与PCM均逐一一致；Graph组记录首次捕获成本，约17ms差异受暖机/时序漂移影响，最后常驻组常比Graph更快 | 小样本优势未得到可靠扩展，不采用 |

CPU停车和缓存清理均未降低TTS步数或改变声线；CUDA Graph复用原有算子，未改变16步、精度和参考音频。但“音频一致”只能证明这些已测试句子，不能证明任意后端/输入组合都等价。

DFlash需要额外约1.1GB草稿权重及运行空间，单独加载后显存已接近16GB上限。共存实测明显变慢，因此不能把网页中的桌面5090高token/s套用到本机。当前结果也不能直接否定未来24GB移动5090上的收益。

暖机后的部分主机通道首PCM可以在约1.4–2.1秒，但本轮没有新增ASR录音、板端出声和用户听音验收；首轮曾超过4秒，不能宣称稳定3秒或整机目标完成。

## 证据与审计说明

- `draft_download.json`：固定远端revision、下载字节数、SHA256与D盘路径。
- `dflash_summary_retained.json`：已完成DFlash控制台摘要及独立通道证据入口。
- `runner-cuda-0-baseline.log`、`runner-cuda-1-dflash.log`、`runner-cuda-2-dflash.log`、`runner-cuda-3-baseline.log`：对应四组加载、采样与计时日志。
- `pipeline-baseline.json`、`pipeline-dflash.json`：独立保存的完整通道事件、原27B计时、TTS缓存未命中与PCM哈希。
- `memory_schedule.json`、`trim_cache.json`、`cuda_graph.json`、`graph_validation.json`：各组完整事件和语音一致性数据。
- `restored_before_storage_entry.json`：增补草稿路径前，18份已验收源码/配置与原ZIP逐字节一致的核对。
- `restored.json`：增补路径后的最终恢复、原生成参数与视觉健康核对。

首次独立启动遗漏CUDA DLL加载路径而回退CPU，已停止，`probe.json`及`runner-0-baseline.log`明确排除。随后显式指定 `GGML_BACKEND_PATH` 为CUDA后端DLL文件，并用CUDA0和完整显存分配检查阻止静默CPU回退。[Ollama加载实现](https://github.com/ollama/ollama/blob/main/llm/llama_server.go)

另有一处归档错误：辅助显存实验最初复用了 `probe_cuda.json`，覆盖了原DFlash详细探针汇总。已修复为各实验独立报告路径；该文件不再作为DFlash整组证据。DFlash控制台统计保存在 `dflash_summary_retained.json`，四组runner日志和两个独立完整通道JSON仍保留。此限制如实保留，不补造原逐条JSON。

初次恢复检查错误沿用历史相机PID987，造成核查失败。动态健康接口实际显示视觉正常，当前PID在本轮核查时为141309，DPU架构指纹 `0x101000056010407`，错误字段为空。核查脚本已按动态服务健康验证；本轮未操作视觉服务，不能声称PID始终未变化。

## 文件位置与复测

候选草稿及全部下载分段在 `D:\AIModels\dflash2-qwen3.8-27b`，主权重与Ollama库继续使用原D盘位置。E盘只保存脚本、报告、生成音频与小型证据；本轮没有模型目录联接或权重复制进入共享目录。

`run_exclusive.ps1`支持独立DFlash、停车、缓存清理、Graph初探与扩展验证。它会临时暂停电脑语音并在finally中启动恢复，复测后仍须运行 `check_restored.py`。应在新的归档目录复测或先保留本轮证据，不直接覆盖已记录结果。实验重启会清空现有易失会话历史，不新增跨重启长期记忆。

本轮没有更换正式语音引擎，没有启用投机解码，也没有把未验证草稿发送给玩偶。原27B与自然连续播放保持。后续较有价值的是目标5090 Laptop上的重新验证，以及原生流式TTS/正式服务与独立通道耗时差异的定位；这些尚未完成，不能提前计作提速成果。
