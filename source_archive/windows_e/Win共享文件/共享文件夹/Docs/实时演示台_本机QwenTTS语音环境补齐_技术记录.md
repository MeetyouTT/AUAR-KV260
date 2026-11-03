# 实时演示台：本机 Qwen TTS 语音环境补齐（对话出声）技术记录

日期：2026-10-07　主机：Windows 11 / RTX 5060 Ti 16GB　范围：PC 端本地合成（非板端推理）

## 1. 背景与目标

上一阶段已打通"本机 Ollama 对话"，但 `/api/state` 报 `error=Qwen Python runtime is unavailable`，
对话只有文字、**没有语音与表情动作**（代码设计为失败可见，不静默换系统音色）。

本阶段目标：补齐本机 Qwen3-TTS 运行时，使对话**真正出声**（含情绪 `friendly`、动作 `ack_nod`）。

## 2. 契约核对（结论：无需改配置）

`deliverables/2026-10-06_xilan_live/stage_config.json`：

```json
"voice": { "python": "tmp/qwen-voice-audition-venv/Scripts/python.exe",
           "model_path": "tmp/Qwen3-TTS-12Hz-1.7B-Base" }
```

`aura/board/runtime/audio/selected_voice.py`：`WORKSPACE=AURA.parent.parent`（= `D:\share、\项目开发`），
默认 `model_path=WORKSPACE/'tmp/Qwen3-TTS-12Hz-1.7B-Base'`，并要求 `selection.json`、
`base_model_verification.json`、`reference/soft_young.wav` 且参考音频 SHA256 一致。

→ 两个相对路径与本阶段落盘位置**完全吻合**，**配置未做任何改动**。

## 3. 关键落地步骤

### 3.1 模型（4.3GB，11 个文件）

- 版本：`Qwen/Qwen3-TTS-12Hz-1.7B-Base`，revision **`fd4b254389122332181a7c3db7f27e918eec64e3`**（固定）。
- 直接从 `https://hf-mirror.com/.../resolve/<rev>/<file>` 用 **curl -L** 拉取（实测 **16.85MB/s**）。
- 大文件校验通过：
  - `model.safetensors` 3,857,413,744B → SHA256 `38fc7fc5…b857c` **match=True**
  - `speech_tokenizer/model.safetensors` → SHA256 `836b7b35…571258` **match=True**
- 落盘：`D:\share、\项目开发\tmp\Qwen3-TTS-12Hz-1.7B-Base`。

### 3.2 解释器与 CUDA 运行时（本阶段最曲折处）

| 尝试 | 结果 |
|---|---|
| 官方 Python 3.12.10 静默安装到 `D:\py312` | ✅ 成功（pip 25.0.1） |
| torch cu128 cp312（3.46GB）从阿里 pytorch-wheels | ❌ `Read timed out`，重试 4 次失败 |
| 清华/中科大/北大 `pytorch-wheels` 镜像 | ❌ 404 |
| 交大 `mirror.sjtu.edu.cn/pytorch-wheels/cu128/` | ⚠️ 可用但仅 **1.27MB/s**（3.46GB ≈ 45 分钟） |
| 清华 pypi | ⚠️ 仅 667KB/s |
| **pip 缓存里发现完整 `torch-2.7.0+cu128` wheel（3.18GB）** | ✅ 但 tag 为 **cp310** |
| 官方 Python 3.10.11 安装器 | ❌ `WixBundleInstalled=1`（注册表残留 `CPython-3.10`）→ 静默跳过 |
| 注册表定位到**本机已有 Python 3.10.11**：`D:\sd-webui-aki-v4.11.1-cu128\_py310\python.exe` | ✅ **与 cp310 wheel 完全匹配** |

**最终方案**：用本机既有的 Python 3.10.11 建独立 venv（隔离 ComfyUI，不污染其 site-packages），
把 pip 缓存中的 wheel 复制为 `.whl` **零下载复用**（3.18GB 安装仅 51 秒）。

```powershell
# 从 pip 缓存提取（body = 完整 wheel）
C:\Users\35870\AppData\Local\pip\cache\http-v2\7\2\0\0\a\7200ae92….body
→ %TEMP%\zz_wheels\torch-2.7.0+cu128-cp310-cp310-win_amd64.whl
# 建 venv（3.10.11）并安装
D:\sd-webui-aki-v4.11.1-cu128\_py310\python.exe -m venv "D:\share、\项目开发\tmp\qwen-voice-audition-venv"
```

### 3.3 最终环境（实测）

```
python 3.10.11
torch 2.7.0+cu128     cuda_available True
GPU   NVIDIA GeForce RTX 5060 Ti   capability (12, 0)   ← sm_120 Blackwell
cuda_runtime 12.8
qwen-tts 0.1.1 / transformers 4.57.3 / accelerate 1.12.0
librosa 0.11.0 / soundfile 0.14.0 / sox 1.5.0 / onnxruntime 1.23.2 / einops 0.8.2 / gradio 6.17.3
```

## 4. 踩坑与规避（可复用）

1. **`HttpWebRequest` 不跟随 308**：hf-mirror 返回 308 Permanent Redirect → 全部文件失败。
   → 改用 `curl.exe -L`（同时获得断点续传与稳定速率）。
2. **wheel 文件名不能用 URL 编码**：初版把 torchaudio 存成 `…2.7.0%2Bcu128-…whl`，
   pip 报 `Invalid wheel filename (invalid version)`，并导致**同一条命令里的 torch 一起回滚**。
   → 文件名必须是字面 `+`（`torchaudio-2.7.0+cu128-cp310-cp310-win_amd64.whl`）。
3. **Python 官方安装器被注册表残留欺骗**：`WixBundleInstalled=1` 时静默 exit 0 且不装任何文件，
   必须用 `/log` 才能看出；本机因此改用既有 `_py310`。
4. **前台 `powershell -Command` 内联双引号会被 cmd 破坏** → 一律改为「脚本文件 + 参数传中文路径」；
   含 `|`/`"` 的正则与 `-Filter` 表达式尤其容易炸。
5. **kill 的模式匹配会命中自身命令行**（自杀导致命令中断、后续步骤不执行）→ 用字符串拼接规避
   （如 `'zz_install'+'310'`）。
6. **前台命令约 90–120s 会被超时中断**（`Start-Sleep 150` 那次连输出文件都没写成）
   → 长任务一律 WMI 脱离终端 + 日志落盘 + 轮询。

## 5. 验证结果

### 5.1 独立合成（`selected_voice.py` worker 协议）

```
SYNTH_OK {"status":"COMPLETE","duration_seconds":3.84,"sample_rate":24000,"channels":1,
          "generation_seconds":53.46,"cache_hit":false,"path":"…\tmp\voice_cache_live\dfa12e1e….wav",
          "sha256":"cbc6a7bc…b5c1"}
```

### 5.2 端到端（重启演示台后 `POST /api/command {"type":"dialogue",…}`）

```
phase=SPEAKING  playing=True  duration=4.96  audio_time=0.995  error=""
turns={"text":"你好呀,我是汐蓝,一个喜欢和你聊天的桌面玩偶!","emotion":"friendly","action":"ack_nod",
       "cache_hit":false,"request_to_audio_seconds":39.37,"duration_seconds":4.96,
       "audio_sha256":"2cb9d18c05d2747f3326b798f08babf5bd75783fc7776272eef268f68493f623"}
```

→ 文字回复 + 情绪 + 动作 + **语音播放**全链路打通；`error` 字段已清空
（此前为 `Qwen Python runtime is unavailable`）。

### 5.3 无害告警（已确认可忽略）

- `SoX could not be found!`：缺 SoX 二进制，qwen_tts 自动回退 soundfile/librosa，合成正常。
- `flash-attn is not installed`：按代码设定使用 `attn_implementation='sdpa'`，符合预期。

## 6. 涉及文件

| 类型 | 路径 |
|---|---|
| 模型（新） | `tmp\Qwen3-TTS-12Hz-1.7B-Base`（4.3GB，11 文件，SHA256 校验通过） |
| venv（新，3.10.11） | `tmp\qwen-voice-audition-venv`（torch/torchaudio cu128 + qwen-tts 0.1.1） |
| 解释器（复用既有） | `D:\sd-webui-aki-v4.11.1-cu128\_py310\python.exe`（3.10.11） |
| 复用 wheel（新提取） | `%TEMP%\zz_wheels\torch-2.7.0+cu128-cp310-cp310-win_amd64.whl`（3.18GB） |
| 辅助脚本（临时） | `%TEMP%\zz_dl_model.ps1`、`zz_torch_fetch.ps1`、`zz_extract_torch.ps1`、`zz_install310.ps1`、`zz_install310b.ps1`、`zz_verify.py`、`zz_runverify.ps1` |
| **未改动** | `aura\**` 全部代码、`stage_config.json`（路径契约本就吻合） |

## 7. 下一步

1. 首次合成 ~39–53s（含 CUDA kernel 编译），后续同文本命中缓存；如需更快可预warmup、或评估安装 `flash-attn`。
2. SoX 二进制可选安装（消除告警，非必需）。
3. 音色辨识度 A/B/C 仍待在具备 VoiceDesign 的机器生成（与本阶段无关的历史遗留）。
4. 日常开机流程：先启动 `dialogue_host_ollama.py --backend ollama --model huihui_ai/qwen3-abliterated:14b`，
   再双击 `aura\tools\run_demo_stage.bat`（后者会自动选中 `.venv-live`）。
