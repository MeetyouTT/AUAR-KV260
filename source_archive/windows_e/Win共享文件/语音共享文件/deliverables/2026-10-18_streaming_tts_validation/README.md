# 原生流式语音独立验证（2026-10-18）

**已完成：** 最新结论见 [RESULTS.md](RESULTS.md) 和 `verification_summary.json`。已找到内容初筛通过的CUDA高精度缓存/关闭FlashAttention/25-token模式，用户接受候选样本声线；原27B联动3.12–4.32秒，不含ASR和板端播放，尚未稳定3秒。原生思考样本首文字15.69秒且算错58×3，必须补正确性校验。正式服务已恢复，候选未上线，5090未实测。下方为原始试验设计，12次方案的实际执行数分别记录于结果文件，Vulkan在6次后提前停止。

本目录是独立实验，正式27B、量化、推理参数、OmniVoice16和板端程序没有切换。候选为社区 Windows C++/GGML CosyVoice3，不能把官方 Python 实现的最低延迟当作本机结果。

## 基线

`baseline_channel.json`：同一历史真实录音连续3次经过正式 ASR→27B→OmniVoice16，主机接收首PCM为5031、2422、2391毫秒，三次TTS缓存命中均为0。三次措辞不同，首轮准备开销较大；不是固定台词的因果性能对照，不证明稳定3秒，未播放到玩偶扬声器。

## 候选与边界

- 原27B及IQ4_XS保持；`model_before.json`和`restored.json`记录模型哈希。
- 候选TTS为 `CosyVoice3-2512_Q8_0`，参考前端为INT8，均在 `D:/AIModels/cosyvoice3-streaming-validation`。使用Q8的是独立语音候选，不是27B。已中止的F16部分下载也留在D盘，没有发布为模型。
- 完整使用原9.52秒汐蓝参考音频和匹配文本，SHA256见 `before.json`。未裁短参考以制造延迟优势。
- 程序固定 `Lourdle/cosyvoice.cpp v0.2.0`，GGML固定 `b11723` Vulkan，发行包哈希见 `assets.json`。使用Vulkan是为规避该项目记录的部分预编译CUDA产生噪声问题，不代表CUDA已在本机对比。
- `probe_streaming.py`比较整段返回、25和50 token音频分块，12次固定台词交错测试。数据到达、非静音信号到达和根据到达轨迹估算的无断流最早播放时间分开记录，HTTP头不算语音。
- `check_audio.py`只筛查内容漏字，不是声线相似度或自然度验收。
- `probe_pipeline.py`保留原27B及原复杂问题768 token思考预算，使用完整台词字段再启动原生分块音频合成，并与剩余元数据生成重叠。此实验不含ASR和板端扬声器，不是正式界面集成；复杂问题暂按完整台词启动，不能等同正式首分句流水线。
- `run_exclusive.ps1`只在玩偶空闲且正式服务身份确认后，临时停止PC8792及其TTS进程，保留项目Ollama、27B、ASR和板端视觉；无论候选成功失败均重新启动原服务。
- `check_restored.py`等待正式服务就绪，核对62个原文件、27B权重SHA、ASR、相机健康，并执行一次真实完整通道。

## 验收

性能结论以本轮实际JSON结果为准。未完成的结果不得标为通过；声线与连续性还需要听音。即使首包很快，如果音频生成跟不上播放而需要大量预缓冲，也不采用。

5090笔记本尚不在当前机器上，`5090_validation_profile.json`是待执行的验收配置，没有5090实测数字。不能保证任意复杂问题3秒内完成有效回答，也不将等待提示计为答案。

## 来源

[CosyVoice.cpp](https://github.com/Lourdle/cosyvoice.cpp)、[固定版本接口说明](https://github.com/Lourdle/cosyvoice.cpp/blob/v0.2.0/docs/TOOLS.md)、[GGUF转换资源](https://huggingface.co/Lourdle/Fun-CosyVoice3-0.5B-2512-GGUF)、[Qwen3-TTS官方接口](https://github.com/QwenLM/Qwen3-TTS)。主线初选CosyVoice.cpp实际验证，未把Qwen3-TTS README中的流式能力视为已安装Python API能直接返回分块。
