# 汐蓝语音已验收：其他主机接手说明

2026-10-11，用户确认：“目前这个语音效果合格，写入项目文件夹中保存，由其他主机进行后续工作”。本版作为已接受的语音基线保存，见 `acceptance.json`。后续以当前音色、参考音频及 OmniVoice 16 步为起点。

## 已保存的内容

- 运行入口：项目根目录下 `deliverables/2026-10-11_omnivoice_dialogue/`，网页端口 8775，对话 WS 端口 8766。
- 完整 OmniVoice 权重：`aura/models/tts/OmniVoice/`，官方 revision `c5fdb5ccb189668d56333f77ba2629f4cd7535f4`。
- 完整 Qwen3 4B Ollama manifest/blobs：`aura/models/dialogue/ollama/`，模型名 `qwen3:4b-instruct-2507-q4_K_M`。上述两组模型共 5,764,763,543 字节，全部已核对 SHA256，清单 `model_files.json`。
- 中文识别模型沿用项目内 `aura/models/asr/sherpa-onnx-paraformer-zh-2023-09-14/` 的 `model.int8.onnx` 与 `tokens.txt`，指纹在 `baseline_files.json`。
- 已选参考：`deliverables/2026-10-06_voice_selected_soft_young/selection.json` 与 `reference/soft_young.wav`。参考转写为逐字技术记录，其中旧名“小光”必须保留；当前角色名为“汐蓝”。
- `accepted_source.zip` 保存本次运行源码、测试、前端、参考与验证记录的冻结副本，内部路径相对项目根；属于基线备份，运行仍用共享项目原目录。模型不重复压缩，完整项目的动画素材等仍需同步。
- 本目录有实际运行版本记录、接手机器依赖清单、模型导入和校验脚本。虚拟环境含本机路径，需在其他主机重建。

## 接手顺序（Windows）

1. 等 VerySync 将完整项目及模型同步完毕。本机文件保存成功不代表远端同步已完成。先在项目根执行：

   ```powershell
   python .\deliverables\2026-10-11_voice_accepted\verify_saved.py
   ```

   应输出 PASS。脚本校验冻结包、参考、识别模型和完整语音／对话模型；源码以后继续修改时不会影响冻结包校验。

2. 安装 Ollama。退出接手机器上的 Ollama 后，将权重合并到它实际使用的模型目录（有 `OLLAMA_MODELS` 时必须用该目录）：

   ```powershell
   python .\deliverables\2026-10-11_voice_accepted\import_ollama_model.py --models-dir '<该机 Ollama 模型目录>'
   ```

   若不指定参数，采用当前进程 `OLLAMA_MODELS`，否则采用用户目录 `.ollama/models`。脚本先校验，遇到不同内容的现有文件会停止，不覆盖。重新启动 Ollama，`ollama show qwen3:4b-instruct-2507-q4_K_M` 应能看到模型，无需重新下载。当前本机的全局 Ollama 设置未调整。

3. 建立两个独立环境：UI 使用 Python 3.14，安装 `aura/requirements-live.txt` 所列依赖（实测版本见 `runtime_versions.json`；该旧文件头的 Python 3.12 注释不代表本次实测版本）。语音／识别使用 Python 3.10，先安装 CUDA 12.8 PyTorch，再安装本目录依赖：

   ```powershell
   & '<语音环境 Python>' -m pip install torch==2.7.0 torchaudio==2.7.0 --index-url https://download.pytorch.org/whl/cu128
   & '<语音环境 Python>' -m pip install -r .\deliverables\2026-10-11_voice_accepted\requirements-voice.txt
   ```

   本机实测 RTX 5060 Ti 16GB，语音 CUDA/float16/SDPA；必须检查 CUDA 可用及可用显存。依赖文件记录已运行版本，重建尚未在第二台机器执行。对话主机为标准库实现，无额外 WebSocket 库。不要将旧 Qwen TTS 的 transformers 4.57.3 环境直接改成此环境。

4. 在项目根启动，明确覆盖本机 Python 路径：

   ```powershell
   & '<UI Python>' -B .\deliverables\2026-10-11_omnivoice_dialogue\launch.py --ui-python '<UI Python>' --voice-python '<语音环境 Python>'
   ```

   OmniVoice 默认路径已改为 `${PROJECT_ROOT}/aura/models/tts/OmniVoice`，自动随项目所在目录解析，也可用 `--model-path` 覆盖。`stage_config.json` 中的 Python 路径只是原机器示例，启动器写出的 `machine_config.json` 也不能直接照搬。已有 8766/8775 端口会复用，切换配置须先退出该机本任务进程。浏览器打开 `http://127.0.0.1:8775/`，等待语音与识别就绪后按住说话、松开发送，首次允许麦克风。

## 保持的语音基线

“柔亮俏皮”参考 SHA256：`0d252fc92cfd0002f61d05f107b816d092fd5086a281e98e94d3cdc5ccf66604`。16 步、speed 1.0、guidance_scale 2.0、denoise/preprocess_prompt/postprocess_output 均开启，seed 8701，float16、SDPA。独立缓存身份含模型／参考／文本／参数，保留全角标点。加载后实际计算预热，不用缓存替代预热。

当前对话采用 Qwen3 4B 的 `--strict --fast`：2048 上下文、120 输出 token、关闭思考、最近四轮记忆、驻留 30 分钟，模型失败明确报错。识别为本地 CPU Paraformer，2 线程；麦克风按键结束一句，尚无自动 VAD 或全双工。说话复用已接受的待机动画，音频样本时钟驱动口型，不新增身体动态。

实测录音夹具提交到实际开口 1.250／1.094 秒，新文字对话 1.594／1.031 秒，均为本机小样本，不能当作其他机器固定延迟。完整链路、打断及 26 项相关回归记录已归档。用户这次确认语音效果合格；物理麦克风的自动化测试覆盖、LLM 复杂理解／事实质量、板端部署验收仍应分别记录。4B 曾混淆自身台词与用户台词、提到未知天气。

其他主机后续可继续改善对话质量、交互与板端接入，改动时保留此语音基线对照。OmniVoice 代码 Apache-2.0，模型权重 CC-BY-NC，完整许可证随模型保存。根目录 `.cline-handover.md` 的最新条目为本次交接状态；其下历史“模型仅在 C 盘／语音待人耳验收”描述已被本记录更新。
