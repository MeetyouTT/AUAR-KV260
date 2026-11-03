# Windows同步与Ubuntu现有内容

2026-10-17，范围为本次“板端录音→电脑识别→板端文字显示”和已验收语音交付文件。没有取得Windows目录清单，因此不能据此列出全部两机差异。

## 本次需要的源码

原4文件补丁只补齐Windows已明确反馈缺少的4份文件，运行服务还要有既有ASR实现及包初始化。新的完整代码包：

`asr-host-complete-code-b9ac9d83fe24f179.zip`

12549字节，SHA256 `1d07cc2b30848a07f9c454e8d149c48a5647a71167ef93c57bfef1c7a4268255`。解压到Windows实际 `aura` 目录。包含8份源码/说明及11项必需文件校验清单，保留原4文件补丁包。

```text
scripts/start_board_asr.ps1
tools/asr_server.py
common/asr_wire.py
docs/BOARD_ASR.md
board/runtime/audio/asr.py
board/runtime/audio/__init__.py
board/runtime/__init__.py
common/__init__.py
```

本次将该包解压到隔离临时目录，用 `-I -B` Python运行其中服务代码，确认ASR和wire模块均从包内加载，并使用外部实际Paraformer模型识别真实样例成功。证明包内8文件可支撑这条ASR服务代码路径；Windows执行和局域网链路仍待验证。

## 另外同步的模型文件

Ubuntu原件：

`/home/ghmd/Win共享文件/共享文件夹/aura/models/asr/sherpa-onnx-paraformer-zh-2023-09-14/`

必须包含：

```text
model.int8.onnx
tokens.txt
test_wavs/0.wav
```

3份必需文件合计243626686字节。代码包没有包含模型权重，应通过微力同步保留上述相对目录；服务启动会使用0.wav做真实探针，因此测试音频也要同步。完整SHA清单见同目录 `ASR_REQUIRED_FILES.json`。

## Windows环境与检查命令

使用已验收Python3.10语音环境，sherpa-onnx/core1.13.8和已有numpy。Windows验收基线为numpy2.2.6；Ubuntu本轮隔离环境为Python3.8.10/numpy1.24.4。两机虚拟环境需分别建立，保留本机实际Python路径。

启动脚本可读取相邻 `deliverables/2026-10-11_omnivoice_dialogue/machine_config.json` / `stage_config.json` 的有效环境路径，也可显式传 `-VoicePython`。环境路径配置并非可直接照搬的跨机运行环境。

将本目录的 `check_asr_files.py` 和 `ASR_REQUIRED_FILES.json` 一起同步。在Windows使用实际语音Python执行：

```powershell
& '<语音Python完整路径>' -B '<本目录实际路径>\check_asr_files.py' --aura-root '<Windows实际aura目录>'
```

脚本逐项输出MATCH/MISSING/DIFFERENT，并列出执行它的Python和依赖版本；只做文件及安装包元数据核对，不自动覆盖、安装或启动服务。用户只检查文件时可附加 `--files-only`。文件差异需先由Windows Codex检查当前改动。

## Ubuntu现有与尚未确认

- 本次ASR所需11项文件均存在、长度/SHA一致；本轮实际ASR环境可识别真实样例。
- 已验收语音交付的31项文件重新按原清单逐项SHA256核对，全部通过，包括Paraformer、OmniVoice、Qwen3 4B Ollama权重、参考与冻结交付资料。详见 `ubuntu_inventory.json`。
- 当前ASR隔离环境没有torch/omnivoice/transformers，不能用该环境直接代表完整TTS运行环境。本轮PATH没有找到ollama或nvidia-smi；不能据此推断所有磁盘环境或GPU硬件不存在。Ubuntu本机完整LLM/TTS运行未在本轮验收。
- Windows目录、实际Python环境和最新未共享改动尚未取得；板端实时跨机ASR成功用例尚待验收。

## 共享目录之外的项目资料

以下内容在Ubuntu存在，但不在 `/home/ghmd/Win共享文件/共享文件夹` 内，微力若只同步共享目录则需要单独选取：

- `/home/ghmd/AMD_Smart/`：有效计划、资料导航与每日实测日志。
- `/home/ghmd/下载/项目.zip`：最初完整项目资料包。
- `/home/ghmd/aura-asr-integration-20261016/`：本轮上板报告、版本清单和串口证据；其host-env是Ubuntu本机环境。

这三类资料用于Windows继续接手开发与追溯。当前ASR运行依赖清单为上面的8份源码和3份模型数据。
