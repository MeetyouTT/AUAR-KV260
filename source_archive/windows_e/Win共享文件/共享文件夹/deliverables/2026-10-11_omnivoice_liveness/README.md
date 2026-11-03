# 汐蓝语音活人感：OmniVoice 独立对照

日期：2026-10-11。目标：比较自然接话、重音、停顿、句尾语调、情绪恰当程度与角色音色一致性。默认演示、已接受音色、生产缓存均未修改。

## 当前状态

- Qwen、OmniVoice 16 步、OmniVoice 32 步各八条，共 24 条已生成。24kHz 单声道 PCM16 格式与 SHA256 验证通过，全部原始音频无幅度削波。浏览器已实际验证两组 OmniVoice 安慰音频可播放。
- 用户确认其他共享机器未下载，继续本机下载后，官方权重已齐全。编码器 805,665,628 字节、主模型 2,450,344,112 字节、文本分词器 11,423,986 字节均通过官方 LFS SHA256 校验，详见 `model_verification.json`；此前超时与分块续传现已完成。
- 本机 RTX 5060 Ti 上，排除各次加载后首次生成：Qwen 完整合成 3.75–14.19 秒，RTF 1.81–2.07；OmniVoice 16 步 0.61–0.75 秒，RTF 0.11–0.20；32 步 1.14–1.48 秒，RTF 0.22–0.67。不同输出时长、小样本及首次生成不能混作严格基准；详见 `comparison_summary.json`。计时不是实际开口延迟，也不代表板端性能。
- OmniVoice 峰值 PyTorch allocated 约 2.05 GiB，Qwen 约 4.44 GiB。32 步首次生成用了 10.77 秒，与后续耗时差异明显；不能直接按后续速度承诺首次交互响应。
- 已完成 24 条 CPU ASR 内容辅助检查，逐条转写见 `asr_verification.json`。16 步短回应的开头“嗯”未被识别，疑问句“一步”识别为“部”，需重点人耳核对；32 步对应两处识别完整。专名“汐蓝”识别为“西兰”、啦／了及得／的等差异不能仅凭 ASR 判定发音错误。
- 声音自然度与角色一致性尚未由人耳评价。波形、格式和哈希通过不能证明“更像真人”。

## 实验口径

复用 `../2026-10-06_voice_selected_soft_young/selection.json` 固定的完整 9.52 秒参考音频与逐字转写。参考转写中的历史名字“小光”保持原样，目标台词使用“汐蓝”。参考 SHA256：`0d252fc92cfd0002f61d05f107b816d092fd5086a281e98e94d3cdc5ccf66604`。

`cases.json` 包含六个日常场景与两项全／半角标点对照。同一引擎各条固定随机种子 8701。相同种子不代表两个不同引擎的随机过程一致。实验直接传入原台词，不经过生产 NFKC 归一化；标点作用需试听验证，不预设全角更自然。

`run_comparison.py` 独立加载模型，用 SDPA；Qwen 用 bfloat16，OmniVoice 用 float16。Qwen 最大 1200 新 token、非流式；OmniVoice 分别 16／32 步、语速 1.0。第一次推理与后续推理在记录中区分，GPU 同步后计时。未增加笑声／叹气标签或更换参考，避免混淆引擎效果。

每条保留 FLOAT 原始 WAV 与按活跃段 RMS 近似匹配到 0.1、峰值限制到 0.95 的 PCM16 试听 WAV；不剪停顿、不变语速。完整合成时间不含之后的文件保存及播放器启动。原始峰值、削波比例、输出时长、RTF、峰值 PyTorch 显存和音频哈希写入各组 `report.json`。显存记录为 PyTorch allocated，非整张 GPU 的总占用。

## 试听

运行 `build_audition.py` 校验音频并生成 `index.html`，可直接在浏览器打开。切换音频自动暂停上一条；评价可以导出 JSON，页面不自动提交或保存评价。先听“短回应”“安慰”“疑问接话”，每项按自然感／情绪／音色一致性各给 1–5 分。

## 多机接手

- 共享：本目录的脚本、台词、试听页、音频与报告。脚本以自身位置定位共享根，避免固定 D／E 盘路径。
- 本机 Qwen 运行环境：`D:\share、\项目开发\tmp\qwen-voice-audition-venv`；模型：同级 `Qwen3-TTS-12Hz-1.7B-Base`。revision：`fd4b254389122332181a7c3db7f27e918eec64e3`。
- 本机 OmniVoice 环境：`C:\Users\35870\.codex\visualizations\2026\10\09\01a12110-3ba4-7651-b3d7-2e6560916eb6\omnivoice-runtime-py310`。只读追加现有 Qwen site-packages，复用 CUDA PyTorch 2.7；新依赖安装到自身目录，优先于追加目录。另一台机器应独立建环境，不复制此虚拟环境或照抄绝对路径。
- 环境实测：OmniVoice 0.2.1／Transformers 5.3.0／huggingface-hub 1.33.0／hf-xet 1.7.0／torch 2.7.0+cu128；CUDA 可用。原 Qwen 环境仍为 Transformers 4.57.3／huggingface-hub 0.36.2。新环境可见旧 qwen-tts 元数据引发依赖冲突提示，但不在新环境运行 Qwen；两个引擎分别用各自 Python。
- OmniVoice 固定模型 revision：`c5fdb5ccb189668d56333f77ba2629f4cd7535f4`。完整权重位于上述任务目录中的 `models/OmniVoice`，本机已离线生成成功。`download_ranges.py` 对官方 LFS 文件支持分块续传并按官方 SHA256 校验。模型与虚拟环境不在共享项目目录；其他机器试听已有 WAV 无需下载模型，再生成需自行准备环境和同版本权重。
- 官方项目：<https://github.com/k2-fsa/OmniVoice>；模型：<https://huggingface.co/k2-fsa/OmniVoice>。代码 Apache-2.0，官方权重说明为 CC-BY-NC；商业用途需单独确认权重授权。

重跑示例（替换为本机真实环境／模型路径，OmniVoice revision 以下载记录为准）：

```powershell
& '<Python路径>' -B -u '.\run_comparison.py' --engine omnivoice --model '<本地模型路径>' --revision '<下载SHA>' --steps 16
& '<Python路径>' -B -u '.\run_comparison.py' --engine omnivoice --model '<本地模型路径>' --revision '<下载SHA>' --steps 32
& '<Python路径>' -B '.\build_audition.py'
```

脚本可续跑已记录条目；不覆盖已存在但未登记的音频。若模型版本、参考或参数改变，应新建实验目录，不能把旧结果当作新结果。
