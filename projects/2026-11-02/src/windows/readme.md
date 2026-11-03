# Windows 推理服务

现役主机是 RTX 5090 Laptop，承担 27B 和 OmniVoice16 推理。板端负责 ASR、声纹、记忆和角色业务。入口为本目录的 start_inference.ps1。请先在完整工程解压副本上运行根目录校验，再在独立运行副本中准备模型和环境。服务会写 sessions、运行锁和状态文件。

1. 准备 Python 3.10.11、与 CUDA 12.8 PyTorch 匹配的 NVIDIA 环境和 Ollama 0.40.13。按 requirements-5090.txt 安装，torch/torchaudio 2.7.0+cu128 取自 PyTorch 的 cu128 wheel 源。omnivoice==0.2.1 使用同目录 omnivoice_source，先用相同解释器执行 python -m pip install --no-deps ./omnivoice_source。其余包使用锁文件中的具体版本。原运行环境为 D:/AURARuntimes/voice-py310。
2. 原 GGUF 位于 D:/AIModels/qwen3.8-27b-abliterated，Ollama 模型库位于 D:/AIModels/Ollama-AURA。models/host_llm.json 指明 Hugging Face 仓库、固定 revision、文件名和 SHA-256。原机可直接复用，新机可按下例将权重下到工程之外。OmniVoice 必须下载指定 revision 的完整模型目录，含 audio_tokenizer。
3. 以下示例使用 Hugging Face CLI 并在 src/windows 目录执行。对工作副本运行 prepare_weights.py 后会按清单校验全部所需 TTS 文件，并将其放入服务期望的位置。27B 留在外部目录。

~~~powershell
hf download huihui-ai/Huihui-Qwen3.8-27B-abliterated-GGUF Huihui-Qwen3.8-27B-abliterated-UD-IQ4_XS.gguf --revision 1c69098e9c32db6dc06fc48f1d6cc75ad07da89e --local-dir D:/AIModels/qwen3.8-27b-abliterated
hf download k2-fsa/OmniVoice --revision c5fdb5ccb189668d56333f77ba2629f4cd7535f4 --local-dir D:/AIModels/omnivoice-source
python prepare_weights.py --gguf D:/AIModels/qwen3.8-27b-abliterated/Huihui-Qwen3.8-27B-abliterated-UD-IQ4_XS.gguf --tts-cache D:/AIModels/omnivoice-source
~~~

4. 在 aura/config/model_inference.local.json 设置本机解释器，aura/config/model_storage.local.json 对应独立 GGUF/Ollama 路径。原机策略 ollama_runtime.local.json 固定原 GPU UUID 和实测 fit_target。新显卡应按真实 UUID 和容量重新确认配置。原进程使用专用 Ollama 127.0.0.1:11435，模型标签 aura-qwen3.8-27b-abliterated:iq4_xs。首次导入时把 modelfile.txt 复制至 GGUF 所在目录，针对该专用服务执行 ollama create aura-qwen3.8-27b-abliterated:iq4_xs -f modelfile.txt。设置 OLLAMA_HOST=127.0.0.1:11435、OLLAMA_MODELS=D:/AIModels/Ollama-AURA，先确认当前服务归属与模型库，再导入。
5. 准备完毕后执行 .\start_inference.ps1 -Action Start，随后执行 .\start_inference.ps1 -Action Status。业务端点 192.168.50.1:8797，允许板侧 192.168.50.2，状态端点 /health。结束时执行 .\start_inference.ps1 -Action Stop。原机已经运行服务时只做 Status。原始实测和参数见根目录 data/results/performance。本次打包未在另一台 Windows 上冷装并调用模型。
