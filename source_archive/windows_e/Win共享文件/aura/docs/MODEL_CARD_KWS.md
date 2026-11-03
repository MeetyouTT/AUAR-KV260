# MODEL CARD · KWS（关键词唤醒）—— sherpa-onnx Zipformer 3.3M 中文

> 版本：V1.0 ｜ 日期：2026-09-12 ｜ 维护：**人3（运行时 / 语音对话）**
> 环境标签：**PC 基线（CPU，单线程）**——本文所有指标均为开发主机实测，**非板端实测**。
> 关联：`board/runtime/audio/kws.py`（集成点）、`examples/run_kws_demo.py`（演示）、
> `tools/kws_benchmark.py`（测速）、`evidence_shots/kws_benchmark.json`（原始数据）、
> `docs/LICENSE_MATRIX.md`（许可矩阵）。

---

## 一、模型标识（Model Details）

| 项 | 值 |
|---|---|
| 名称 | `sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01` |
| 任务 | **关键词唤醒（KWS, keyword spotting）**——不是通用 ASR |
| 结构 | Zipformer（小型 transducer），**建模单元 = 拼音（声母 + 韵母）** |
| 参数量 | 约 3.3 M（包体 31.1 MB，含 fp32 与 int8 两套 + 7 条测试音频） |
| 训练数据 | **WenetSpeech L（约 10,000 小时中文语音）** |
| 上游来源 | ModelScope：`pkufool/sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01` |
| 推理引擎 | `sherpa-onnx` 1.13.8（`sherpa-onnx-core` 1.13.8），CPU provider |
| 许可 | **Apache License 2.0**（模型卡 README 明示 `license: Apache License 2.0`） |
| 入库位置 | `models/sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01/`（**不入 git**，见 §六） |

## 二、用途与边界（Intended Use / Factors）

- **本项目用途**：桌面终端「雾镜 Lite」的**本地唤醒**——用户说出唤醒词后，系统由
  `IDLE / PRESENT / NETWORK_LOST` 进入 `LISTENING`（倾听）并开始后续 ASR/对话。
- **支持的唤醒词形式**：模型自带 8 个示例词（你好军哥 / 蛋哥蛋哥 / 小爱同学 / 你好问问 /
  小艺小艺 / 小米小米 / 林美丽 / 你好西西）；**自定义唤醒词通过 `keywords.txt` 增删**
  （格式：`<拼音 token 序列> @<中文词>`，见 §五）。
- **不适用**：通用语音转写（ASR）、远场/多人重叠语音、方言、非中文语种、
  需要**真人声纹**判定的场景（KWS 只认"说了什么"，不认"谁说的"）。
- **部署形态**：PC 基线（Python + sherpa-onnx CPU）；板端阶段需实测 CPU/NPU 占用与实时性（BOARD_REQUIRED）。

## 三、指标（Metrics · PC 基线实测）

来源：`tools/kws_benchmark.py`（真实模型，官方 `test_wavs/0~6.wav`，共 7 条 35.6 s 音频，块长 100 ms）。

| 指标 | 实测 | 说明 |
|---|---|---|
| 单块解码延迟 **p50** | **0.309 ms** | 每 100 ms 音频块解码耗时 |
| **p95 / p99 / max** | **15.27 / 18.62 / 20.25 ms** | 最坏 20 ms ≪ 100 ms 块长 → 可实时 |
| 实时率 **RTF（均值）** | **0.0416** | = 解码耗时 ÷ 音频时长；**≈24× 实时** |
| 命中率 | **4 / 7 条命中**（0.571） | 0~2.wav 为官方**负样本**（未含关键词），未命中属预期 |
| 误触发 | **0 次 / 15.29 s 负样本 → ≈0 次/小时** | 样本量小，置信度低（见 §七） |
| 首命中偏移（均值） | **1800 ms** | 从音频起点到"确认命中"已解码时长 |
| CPU | **≈87%（单线程，1 thread）** | `process_time / wall`；单线程几乎跑满一核 |
| 峰值工作集（RSS） | **89.7 MB** | `GetProcessMemoryInfo` 实测（纯链路基线 29.4 MB） |

> 复现：`python tools\kws_benchmark.py`（约 30 s，自动读模型自带的 `test_wavs/`）；
> 纯链路对照：`python tools\kws_benchmark.py --synthetic`（无模型，p50≈0.002 ms、RSS≈29.4 MB）。

## 四、集成方式（本项目契约）

```
音频帧(16k/单声道/float32)  →  KwsRunner.feed(samples)
       命中 ──► EventBus.publish(EventEnvelope(
                     event_type = "audio.kws_detected",
                     payload = {keyword, tokens, timestamp_ms, engine}))
       ──► RuntimeFSM: IDLE / PRESENT / NETWORK_LOST → LISTENING
       ──► UiState: devices.audio = busy("kws hit") → 板端三区 UI 的音频状态项
```

| 命令 | 用途 |
|---|---|
| `python examples\run_kws_demo.py --synthetic` | **无模型/无麦克风**链路自检（默认模式） |
| `python examples\run_kws_demo.py --wav <wav> --json evidence_shots\kws_demo_wav.json` | 离线音频真实解码 |
| `python examples\run_kws_demo.py --mic --seconds 20` | 实时麦克风（需录音设备） |
| `python tools\kws_benchmark.py [--synthetic]` | 延迟/误触发/CPU/内存 benchmark |

- **事件合同零改动**：`events.py` / `fsm.py` / `ui_state.py` 均未修改——
  A1 阶段已定义 `audio.kws_detected` 并实现状态迁移与 UI 渲染。
- 依赖登记：`pyproject.toml` 的 `[project.optional-dependencies].kws = ["sherpa-onnx>=1.13.0", "sounddevice>=0.5.0"]`。

---

## 五、唤醒词与自定义（`keywords.txt`）

格式：每行 **`<拼音 token 空格分隔> @<中文唤醒词>`**，token 必须与模型 `tokens.txt` 中的
字符一致（带声调，如 `n ǐ h ǎo j ūn g ē @你好军哥`）：

```text
n ǐ h ǎo w èn w èn @你好问问      ← 官方自带示例
```

| 文件 | 说明 |
|---|---|
| `keywords.txt` | 官方 8 个示例唤醒词（你好军哥 / 蛋哥蛋哥 / 小爱同学 / 你好问问 / 小艺小艺 / 小米小米 / 林美丽 / 你好西西） |
| `keywords_raw.txt` | 上表对应的**纯中文**原词（便于改词；转换工具待补，见 §八） |
| `test_wavs/test_keywords.txt` | 与本包 7 条测试音频配套的关键词（文森特卡索 / 周望军 / …） |

- 自定义「小镜小镜 / 你好雾镜」的做法：中文 → 带调拼音（`pypinyin`）→ 按声母/韵母切分 →
  写成 `keywords.txt`，再用 `--keywords-file` 指定。**本轮先用官方词验证链路，自定义词列为待办。**
- 模型支持任意数量的唤醒词，但**每个词需单独调 `--threshold`**（默认 0.25）。

## 六、获取与校验（模型不入库）

```powershell
$w = "D:\share\项目开发\FPGA语音助手开发\wujing-lite"; cd $w
# 本机实测：github.com 直连不通，走可达代理（hf-mirror/modelscope 亦可）
$url = 'https://ghfast.top/https://github.com/k2-fsa/sherpa-onnx/releases/download/kws-models/sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01.tar.bz2'
Invoke-WebRequest -Uri $url -OutFile models\kws-model.tar.bz2
tar -xjf models\kws-model.tar.bz2 -C models
```

| 校验项 | 实测值 |
|---|---|
| 包大小 | **32,654,866 B（≈31.1 MiB）** |
| SHA-256 | **`B2F7C89690DC8CE4C6ED6AFEAB7CD800C36AD1421FB6B6302B4A4B194CF7F35F`** |
| 解压后关键文件 | `tokens.txt`(1.6 KB)、`encoder-epoch-12-avg-2-chunk-16-left-64.onnx`(12.2 MB)、`decoder-…onnx`(675 KB)、`joiner-…onnx`(253 KB)（另有 `.int8.` 与 `epoch-99` 变体） |

- **不入 git**：`.gitignore` 已忽略 `models/`、`*.onnx`、`*.bin`；
  加载优先级见 `board/runtime/audio/kws.py::find_kws_model`（**非量化 `epoch-12-avg-2` 优先**，int8 备选）。
- 备选通道：`https://ghproxy.net/<同一条 GitHub URL>`；ModelScope 源：
  `git clone https://www.modelscope.cn/pkufool/sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01.git`。

## 七、局限与红线（Caveats）

1. **样本量极小**：仅 7 条官方音频（35.6 s），误触发"0 次/小时"**置信度低**；
   正式评测需自建 ≥100 条正负样本集（含噪声/远场/方言）。
2. **正/负样本自动分类**（按是否命中），非人工标注 → 命中率 0.571 不等于准确率/召回率。
3. 未评估：远场拾音、多人重叠、背景噪声、非中文语种、儿童/老人音色。
4. **CPU 单线程 ≈87% 一核、RSS ≈90 MB**：板端是否可接受属 **BOARD_REQUIRED**，
   需在板卡阶段实测（可选 int8 变体或 NPU 移植）。
5. KWS 只判断"是否说了唤醒词"，**不做说话人识别**；隐私相关的声纹能力**不在本模型范围**。
6. 严禁把本文 PC 数据写成板端实测（人3 任务书 §九 红线）。

## 八、变更记录与待办

| 日期 | 版本 | 变更 |
|---|---|---|
| 2026-09-12 | V1.0 | 接入 `board/runtime/audio/kws.py`（依赖可选 + 优雅降级）；`examples/run_kws_demo.py` 三模式；
`tools/kws_benchmark.py` 出指标；7 条真实音频实测；`tests/test_kws.py` 22 项单测；模型卡首版 |

**待办**：① 自定义唤醒词「小镜小镜 / 你好雾镜」（`pypinyin` → `keywords.txt` + 阈值调参）；
② 自建正负样本集（正 ≥50 / 负 ≥50，含噪声与远场）并出正式指标；
③ 与 VAD 联动（`audio.vad_start/end` 做 turn 切分，A3 · 9/17 起）；
④ 板端移植评估（CPU 单线程 / int8 / NPU，板卡阶段）。
