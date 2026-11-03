# 本地神经 TTS 接入（sherpa-onnx · VITS / Kokoro）· 技术记录

> 项目：AURA（`E:\share、\项目开发\FPGA-amd自主命题赛道\aura`）
> 主题：**S2** —— 把 TTS 从 Windows SAPI（拼接式）换成**本地离线神经 TTS**，让"语气变化"真正自然；
> 同时给出可选音色（用户诉求：**自己选一个合适的语音**）。
> 依据：D5 §14.4 / W12-04「中文 TTS：**已验证中文 VITS**，音色/发音不满足时比较 **Kokoro** 等替代方案」。
> 日期：2026-10-04　状态：**S2 已完成**（两模型真机跑通；单测 10/10；停声延迟 211 ms）
> 上游：S1（`docs\LLM驱动语音语气_emotion韵律与SSML_技术记录.md`）已把 LLM 的 `emotion` 接到韵律层。

## 一、结论先行

| 项 | 结果 |
|---|---|
| 后端 | 新增 `SherpaTtsBackend`（`engine="vits"`）：sherpa-onnx **CPU 离线**合成 + sounddevice 播放 |
| 分支 | **VITS**（有 `lexicon.txt`）/ **Kokoro**（有 `voices.bin`）自动识别，同一后端覆盖两种模型 |
| 语气 | SAPI 用 SSML；神经 TTS 用 **`speed`**（由同一张 `tts_style` 档位表折算，见 §四.2）——**两条引擎口径同源** |
| 降级 | `vits → sapi → scripted` 逐级回退（实测：模型目录写错 → 自动落到 `SapiTtsBackend`） |
| 模型 | ① `vits-icefall-zh-aishell3`（30.1 MB，**8 kHz**，174 说话人，**RTF 0.033**）② `kokoro-int8-multi-lang-v1_1`（140.2 MB，**24 kHz**，103 音色，RTF ≈1.1~1.3） |
| 停声 | 实测 **211 ms**（T19「停声 P95 ≤ 300 ms」的本地部分达标） |
| 试听 | `models\tts\_audition\audition.html`（两个模型 × 多个中文音色，同一句话，浏览器直接点播） |

## 二、背景与目标

- **S1 已解决**"LLM 的 emotion 有没有用到语音上"；但 SAPI 是**拼接式**语音：`pitch` 变调生硬，
  能驱动的只有语速/音高/音量/停顿四个自由度 → **"自然的语气"做不到**。
- D5 把 TTS 路线写成"**已验证中文 VITS**，不满意再比 Kokoro"；而 `audio/__init__.py` 里早已约定
  `tts.py` 是"板端唯一 TTS" → S2 = 在**同一个后端抽象**下加一个**离线神经**实现，不改任何事件合同。
- 用户诉求新增一条：**要能自己挑音色** → 需要可换 `sid`（说话人）的多音色模型 + 试听手段。

## 三、做了什么

| 文件 | 类型 | 要点 |
|---|---|---|
| `board/runtime/audio/tts.py` | 改 | ① `TtsBackend.speak_async(text, ssml, style)`（新增 `style`）；② `TtsConfig` 新增 `tts_model/sid/speed/num_threads`；③ **新增** `SherpaTtsBackend` + `_SherpaHandle` + `ascii_path()/find_tts_model()/_model_onnx()`；④ `TtsPlayer` 引擎分派；⑤ `build_player` 改成**逐级降级** |
| `board/runtime/audio/tts_style.py` | 改 | 新增 `RATE_MULTIPLIER` + `rate_multiplier()`：韵律档 → 语速乘子（SAPI 关键字档与神经 `speed` **同源**） |
| `board/runtime/audio/__init__.py` | 改 | 导出 `SherpaTtsBackend` / `TtsBackend` / `ascii_path` / `find_tts_model` / `rate_multiplier` |
| `tools/demo_stage.py` | 改 | `--tts-engine` 增加 `vits`；新增 `--tts-sid` / `--tts-model`，接入 `TtsConfig` |
| `tests/test_tts_style.py` | 改 | 单测 7 → **10 项**（新增语速乘子、`speed_for` 限幅、模型定位 + ASCII 链接） |
| `models/tts/vits-icefall-zh-aishell3/`、`models/tts/kokoro-int8-multi-lang-v1_1/` | 新增 | 两个离线模型（30.1 MB + 140.2 MB） |
| `models/tts/_audition/` | 新增 | 试听包（同名 `audition.html` + wav） |
| `docs/本地神经TTS接入_sherpa-onnx_VITS与Kokoro_技术记录.md` + `.docx` | 新增 | 本记录 |

## 四、关键决策与技术细节

1. **后端选 sherpa-onnx（而不是新装 TTS 框架）**：它是本项目 ASR 的同一生态（`asr.py` 已用），
   **纯离线、可冻结、Apache/MIT 友好**，且一张 wheel 里同时支持 VITS / Kokoro / Matcha —— 满足 D5 对"候选"的描述。
2. **语气仍走同一张表（红线：不出现第二套口径）**：`tts_style.rate_multiplier()` 把韵律档翻成**语速乘子**
   （`x-slow 0.80 / slow 0.90 / medium 1.00 / fast 1.12 / x-fast 1.25`），神经后端用它算
   `speed = TtsConfig.speed × 乘子`（限幅 `[0.5, 2.0]`）。于是**同一句 `emotion`**：
   SAPI 上表现为 `rate="fast"`，神经 TTS 上表现为 `speed=1.12` —— 同向、可单测。
3. **采样率适配**：模型采样率各不相同（aishell3 **8 kHz**、Kokoro **24 kHz**、melotts 44.1 kHz），
   而 sounddevice 对不支持的采样率会直接报错 → 播放前统一**线性重采样**到本机默认输出率（实测 44100），
   否则 8 kHz 模型会 `Invalid sample rate` 播不出声。
4. **非 ASCII 路径护栏（本工程路径含 `、`/中文）**：`ascii_path()` 在需要时用 `mklink /J`（**免管理员**）
   在 `%LOCALAPPDATA%\aura_tts_links\` 下建一个 **ASCII junction** 并返回它；
   链接名 = `ASCII 安全前缀 + 目标路径 crc32`（同一目录恒定复用，换路径也不会误指旧目标）。
5. **降级链 `vits → sapi → scripted`**：神经 TTS 依赖缺失/模型缺失只抛 `TtsUnavailable`，
   由 `build_player` 逐级回退，**演示永不静默**（实测：把模型目录写错 → 落到 `SapiTtsBackend`）。
6. **自动挑模型按 D5 顺序**：`find_tts_model()` 无参时**VITS 优先**（`vits*` 目录排在前面），
   没有 VITS 才用 Kokoro；也兼容 int8 量化包（`model.int8.onnx`）。
7. **播放与停声**：合成在**工作线程**里跑（`speak_async` 实测 0.000~0.034 s 返回），
   `handle.kill()` 与 `TtsPlayer.stop()` 的既有约定对齐 → 停声 = 置停止标志 + `sd.stop()`。

## 五、踩坑与修复

1. **kaldifst 只能打开窄字符路径**（第一次冒烟就炸）：
   `RuntimeError: ... kaldi-io.cc:Input:744 [E] Error opening input stream '…\phone.fst'` ——
   sherpa-onnx 的 C++ 依赖用窄字符路径开 `.fst`，本工程路径里的 `、`/中文必然失败。
   → 修法：`ascii_path()` 自动建 ASCII junction（**注意链接名也必须 ASCII**，否则等于没绕开 —— 这一点是被单测抓出来的）。
2. **Kokoro 多语模型必须传 `lexicon`**：不传时**构造能成功、引擎初始化才失败**
   （`offline-tts-kokoro-impl.h:InitFrontend:404 ... please pass --kokoro-lexicon or --kokoro-lang`）。
   → 教训：**探针必须把"构造配置"与"`OfflineTts(cfg)`"放在同一个候选里试**，否则会把不可用配置误判为可行（v1 探针就误判了）。
   正确写法：`lexicon = "lexicon-zh.txt,lexicon-us-en.txt,lexicon-gb-en.txt"`（逗号相连）。
3. **下载 URL 必须是 API 资产地址**：本机 `github.com` 不可达，`browser_download_url` 直接失败；
   必须取 release asset 的 `url`（`api.github.com/repos/.../releases/assets/{id}`）并带
   `Accept: application/octet-stream`，由 urllib 跟随 302 到 `objects.githubusercontent.com`。
4. **终端换命令会 Ctrl+C 掉长任务**：下载/实时播放探针都被打断过 → 一律 `Start-Process -WindowStyle Hidden`
   脱离终端 + 结果**增量落盘**（`open(..., buffering=1)`），不要指望 stdout 重定向（Python 会全缓冲）。
5. **Rule 的 fst 文件名两个包不一致**：VITS 是 `phone.fst/date.fst/number.fst`，Kokoro 是 `phone-zh.fst/date-zh.fst/number-zh.fst`
   → 统一按前缀挑选，避免写两套分支。
6. **（启动器）控制台窗口盖住 Tk 主窗口，吃掉全部点击** —— 远程操作时表现为"**动画在跑、HUD 在变，
   但按钮点不动、事件日志一条都没有**"（本地看还以为是 Tk 卡死）。
   根因：`launch_demo.py` 用 `DETACHED_PROCESS` 启动 venv 的 `python.exe`，而**控制台子系统**程序
   仍会被挂上一个**可见控制台窗口**；本机实测该窗口矩形 `(52,52)-(1045,571)`，**正好盖住按钮区**，
   于是"只有区域外的 VS Code 能点"。
   取证方法（可复用）：用 `EnumWindows` 按 PID 列出顶层窗口，看 **`ConsoleWindowClass` 的 rect**
   是否与主窗口重叠（脚本见技术记录附注）。
   修法（两重保险）：① `DETACH` 里加 **`CREATE_NO_WINDOW (0x08000000)`**；
   ② `python_exe()` **优先 `pythonw.exe`**（GUI 子系统，不建控制台）。
   另：`demo_stage.py` 增加 **F1~F12 键盘快捷键**（与按钮同一条路径），远程鼠标不灵时仍可整机操作。

## 六、验证方式与结果

| 验证 | 内容 | 结果 |
|---|---|---|
| 单测 | `tests/test_tts_style.py`（10 项，含语速乘子 / `speed_for` 限幅 / 模型定位 / ASCII 链接） | **10 passed / 0 failed** |
| 编译 | `py_compile`（tts.py / tts_style.py / audio `__init__` / demo_stage） | `COMPILE_OK` |
| S2 真机探针 | 加载 → 合成播放 → 停声 → 降级 | 见下表 |
| 试听包 | 两模型 × 多音色，同一句话 | `models\tts\_audition\audition.html` |

**实测（本机 CPU，RTX 4060 笔记本）**

| 模型 | 体积 | 采样率 | 说话人 | 加载 | 合成 RTF | 备注 |
|---|---|---|---|---|---|---|
| `vits-icefall-zh-aishell3` | 30.1 MB | **8 kHz** | 174 | 0.61~1.03 s | **0.033**（≈30× 实时） | 极快，但电话音质 |
| `kokoro-int8-multi-lang-v1_1` | 140.2 MB | **24 kHz** | **103**（sid 3–57 = 中文女 zf_*，58–102 = 中文男 zm_*） | 1.74~1.80 s | 0.887~1.022（4 线程） | 更自然；2 线程时约 1.3 |

- 语速档位生效：同一句 `speed=1.12` → 4.93 s，`speed=1.00` → 5.02 s，`speed=0.90` → 5.64 s（VITS）。
- **停声延迟 211 ms**；`speak_async` 返回耗时 0.000~0.034 s（完全异步）。
- 降级链实测：`engine=vits` + 模型名写错 → `got=sapi backend=SapiTtsBackend`。

## 七、边界与风险

1. **音质 vs 速度的取舍（需要拍板）**：aishell3 8 kHz 快但音质差；Kokoro 24 kHz 自然但 **RTF≈1.0**
   （4 字/秒的句子要 4~5 s 才出完整音频，首声延迟明显）。若要"首声快 + 音质好"，
   下一步应做**流式播放**（`generate(..., callback=...)` 逐块回调 + 边说边放），当前实现是"合成完整句再播"。
2. **`num_threads` 可调**：4 线程已明显优于 2 线程；上机可试 6~8（本次未做完整扫描）。
3. **⚠ 语速同源仍未闭环**：`avatar_timing.speed_for_state()`（素材变速 0.85~1.15）与 TTS `speed` 目前是**两条独立曲线**，
   同一个 `emotion` 两边可能不同步 → **下一步必须收敛到同一系数**，否则语音与玩偶口型/动作会错拍。
4. **Kokoro 是 `v1.1-zh` 特化包**：`af_*/bf_*`（sid 0–2）是英文音色，中文只有 `zf_*` / `zm_*`。
5. **磁盘占用**：两个模型合计约 **215 MB**（含 .tar.bz2 包未清理时更多）。
6. **板端仍是"主机侧 TTS"**：本实现跑在 PC/主机（与 D5 §14.4 分工一致）；板卡只做 MCP01 录放音。
7. **许可**：sherpa-onnx 为 Apache-2.0；模型分别来自 icefall（aishell3 数据集训练）与 hexgrad/Kokoro-82M（Apache-2.0）；
   正式交付前需按 `docs\LICENSE_MATRIX.md` 的口径补登记。

## 八、下一步

1. **把语速收敛到同一系数**（§七.3）——`avatar_timing` 与 `TtsStyle/RATE_MULTIPLIER` 共用，改完需重跑 `verify_v2_timing.py`。
2. **流式播放**（§七.1）：用 `generate(callback=...)` 边合成边播，压首声延迟；顺带把"停声"做到 <100 ms。
3. **音色定档**：打开 `models\tts\_audition\audition.html` 听后选定 1~2 个主音色（`sid`），写进 `TtsConfig` 默认值。
4. **接进板端 UI**：`qt_widgets` / `qt_app`（需装有 PySide6 的环境）。
5. **清理**：`models\tts\*.tar.bz2`（约 170 MB）可删；`%LOCALAPPDATA%\aura_tts_links` 为可重建的链接缓存。

## 九、涉及文件清单与回滚

| 文件 | 类型 |
|---|---|
| `board/runtime/audio/tts.py` | 改（`style` 形参 / `TtsConfig` 新字段 / `SherpaTtsBackend` / `ascii_path` / 降级链） |
| `board/runtime/audio/tts_style.py` | 改（`RATE_MULTIPLIER` / `rate_multiplier`） |
| `board/runtime/audio/__init__.py` | 改（导出） |
| `tools/demo_stage.py` | 改（`--tts-engine vits` / `--tts-sid` / `--tts-model`；**F1~F12 键盘快捷键**） |
| `tools/launch_demo.py` | 改（TTS 透传；**`CREATE_NO_WINDOW` + 优先 `pythonw.exe`**，见 §五.6） |
| `tests/test_tts_style.py` | 改（7 → 10 项） |
| `models/tts/vits-icefall-zh-aishell3/`、`models/tts/kokoro-int8-multi-lang-v1_1/`、`models/tts/_audition/` | 新增（模型 + 试听包） |
| `docs/本地神经TTS接入_sherpa-onnx_VITS与Kokoro_技术记录.md` + `.docx` | 本记录 |

**回滚**：运行时 `--tts-engine sapi`（或去掉 `style` 参数）即回 S1/旧行为；
代码 `git checkout` 上述文件（`SherpaTtsBackend` 及其助手可整段删除）；模型目录可直接删（不影响 S1）。

