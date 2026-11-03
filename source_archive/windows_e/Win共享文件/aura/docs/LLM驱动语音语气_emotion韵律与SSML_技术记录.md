# LLM 驱动语音语气（emotion → 韵律 / SSML）· 技术记录

> 项目：AURA（`E:\share、\项目开发\FPGA-amd自主命题赛道\aura`）
> 主题：把 LLM 已经给出的 `emotion` 接到 **TTS 语音韵律** 上（"S1"），并给出一条**一行回退**路径。
> 触发：用户提出"要自己选一个合适的语音，且要有自然的语气变化"，并确认"用大语言模型驱动语气变化"。
> 日期：2026-10-04　状态：**S1 已完成**（单测 7/7、真机 SSML 探针 5/5 `rc=0`）
> 范围：**只做 S1**（不改默认引擎、不换音色）；神经 TTS（VITS / Kokoro）与"演员级情感演绎"见 §八。

## 一、结论先行

| 项 | 结果 |
|---|---|
| 通道 | LLM 的 `DialogueResponse.emotion` → `tts_style.for_emotion()` → SSML → SAPI `SpeakSsml()` |
| 单一来源 | 分档**不新建词表**，直接复用 `fsm.speaking_state_name()`：玩偶演哪条 `talking_*` 素材，语音就用哪个档 |
| 三档韵律 | 高涨 `fast/high/loud/110ms`；中性 `medium×3/200ms`；低落 `slow/low/soft/330ms` |
| 逐句起伏 | 按标点**切段**，逐段套 `prosody` + 段间 `<break>`（整句一个参数是"平推"，不算起伏） |
| 回退 | `player.speak_async(text)` 不传 `style` → 后端收到 `ssml=None` → 走旧的 `Speak()`，**与旧行为逐位一致** |
| 实测 | SAPI **接受全部 SSML 变体**（4 种档位 + 纯文本回退，`rc=0`）；语调听感需人耳验收（本机已验证"能出声且不报错"） |

## 二、背景与目标

### 2.1 文档取证（先纠正前提）

| 出处 | 原文 | 结论 |
|---|---|---|
| `Docs\amd_kv260_full_work_requirements_v3.md:389`（D5） | 「中文 TTS ｜ 已验证中文 VITS ｜ Windows ｜ 音色/发音不满足时比较 Kokoro 等替代方案」 | TTS 引擎的规划是 **VITS / Kokoro**，未写"语气" |
| D5 `:500`（W12-04） | 「用固定中文和姓名测试 VITS 候选，记录音色、发音、音频格式、资源和延迟」 | 验收只看 4 项，**无韵律指标** |
| D4 `:169` | 「语音合成先试现成中文 VITS；若音色或发音不满意，再比较 Kokoro 的中文模型」 | 同上 |
| 全 `Docs\` 检索 | 「语气 / 韵律 / SSML / mstts / prosody」**0 命中** | **"LLM 驱动 TTS 语气"在文档里没有规划原文** |

→ 记忆里的"LLM 驱动"真实存在，但它落在**玩偶表演**：`emotion` → `fsm` 三档 → `talking_normal/neutral/low` 素材 + `avatar_action`（`ACK_NOD/AWAKE/PUZZLED`）。
**缺的那一跳**正是本记录做的：把 `emotion` 延伸到 **TTS 语音韵律**。这不改任何数据合同、不新增事件类型。

### 2.2 改前状态（代码级事实）

- `board/runtime/audio/tts.py` 用 `$s.Speak('...')` —— **SSML 从未启用**，语气恒定；
- `emotion` 字段、`allowed_emotions` 白名单、`policy_validator` 校验、三档路由**全都已就绪**；
- 接线点已在手边：`tools/demo_stage.py::_on_response()` 里 `data["emotion"]` 与 `tts.speak_async()` 相隔数行。

## 三、做了什么

| 文件 | 类型 | 要点 |
|---|---|---|
| `board/runtime/audio/tts_style.py` | **新增** | 语气层：`TtsStyle` 值表 + `for_emotion()` + `clamp_style()` + `split_segments()` + `build_ssml()`；纯逻辑、无依赖 |
| `board/runtime/audio/tts.py` | 改 | 后端接口加 `ssml` 形参；`SapiTtsBackend._script()` 支持 `SpeakSsml`；`TtsPlayer.speak_async/speak` 加 `style`；`stats()` 增加 `style` |
| `board/runtime/audio/__init__.py` | 改 | 导出语气层（`TtsStyle` / `for_emotion` / `build_ssml` …） |
| `tools/demo_stage.py` | 改 | 播报时用 `tts_style.for_emotion(data.get("emotion"))` 传 `style`；日志打印 `style.describe()` |
| `tests/test_tts_style.py` | **新增** | 7 项单测：同源映射 / 脏输入兜底 / 限幅 / 切段 / SSML 结构与转义 / **回退契约** / describe |


## 四、关键决策与技术细节

1. **单一来源（不新建词表）**：`for_emotion()` 内部**委托** `fsm.speaking_state_name()`（延迟导入，避免与 `audio` 包初始化顺序纠缠），
   只把 `SPEAKING / SPEAKING_NEUTRAL / SPEAKING_LOW` 翻译成韵律。这样"玩偶演哪条素材"与"语音用什么语气"**永远同档**，不会长出第二套口径。
2. **只用 SSML 关键字，不写百分比 / Hz**：`rate=x-slow..x-fast`、`pitch=x-low..x-high`、`volume=x-soft..x-loud`。
   理由：关键字是 **SAPI 与 W3C 都保证支持**的写法；百分比/Hz 一旦不被接受，整段 SSML 可能解析失败（退化成不出声）。
3. **逐段韵律（"起伏"的真正来源）**：`split_segments()` 按标点切段（标点跟随前一段），
   `_merge_short()` 把 <6 字的碎片并入相邻段（否则"嗯，"单独成段会磕巴）；`build_ssml()` 对**每段**单独套 `prosody`，段间插 `<break>`。
4. **限幅（防"变调变鬼叫"）**：`clamp_style()` 把非法关键字回落 `medium`，音高最多偏离 1 档（±`PITCH_MAX_STEP`）、
   语速/音量 ±2 档、停顿夹到 `[0, 2000]ms`；模块级 `ENABLE_PITCH=False` 可**一键关掉音高**（只留语速 + 停顿）。
5. **回退开关 = 不传 `style`**：`TtsPlayer.speak_async(text)` 与旧调用**逐位一致**（`ssml=None` → `$s.Speak()`）；
   另有第二层回退——`SapiTtsBackend._script()` 只在 `ssml` 非空时才走 `SpeakSsml`。
6. **事件契约零改动**：收尾仍由 `TtsPlayer.poll()` 发既有的 `AUDIO_PLAYBACK_STOP`，`fsm` 三档收尾逻辑不变（不新增事件类型）。

## 五、踩坑与修复

1. **（真 bug，被单测当场抓到）`_merge_short` 末尾合并越界**：写成 `merged[-2] += merged.pop()` 时，
   Python 求值顺序是"先算下标 → 取右值 → 存回"，而 `pop()` 已把列表缩短，**存回时 `-2` 越界** → `IndexError`。
   触发条件：末段 <6 字且总段数 >1（如 `新行为的一句话。第二句。`）。
   修法：先把末段 `pop()` 到变量，再 `merged[-1] += tail`。
   → **这条正是"不写单测就上线"会漏的坑**：只跑一次"正常长句"根本不会碰到。
2. **Cline 终端会杀掉仍在跑的前台长任务**：实时播报探针第 3 例返回 `rc=0xC000013A`（`STATUS_CONTROL_C_EXIT`，即被 Ctrl+C/关终端），
   **不是代码失败**。改法：用 SAPI 的 `SetOutputToNull()` 在校验路径上跑（每例 ~0.4s），既不发声也不会被实时播放拖长。
3. **Python 重定向到文件时 stdout 全缓冲**：结果文件在进程结束前一直是空的，容易误判"命令没跑"。
   改法：探针自己 `open(path, "w", buffering=1)` + 逐例 `flush()`，边跑边落盘。
4. **工具链缺失**：本机**无 pandoc**，`aura\tools\` 内**无 md→docx 渲染脚本**（历史会话用的 `render_docx.ps1` 只存在于 `%TEMP%`，已随会话清理）。
   改法：用**系统 Python 的 `python-docx`**（实测 1.2.0 已安装）渲染本记录的 docx，满足"md + docx 成对"。

## 六、验证方式与结果

| 验证 | 命令 | 结果 |
|---|---|---|
| 语法 | `python -m py_compile`（tts_style / tts / audio `__init__` / demo_stage） | `COMPILE_OK` |
| 单测 | 本机无 pytest → 最小 runner 跑 `tests/test_tts_style.py` | **7 passed / 0 failed**（第 1 轮 6/1 暴露 §五.1 的 bug，修复后全绿） |
| 真机 SSML | 真实 `_script()` + `SetOutputToNull()`，覆盖 4 档 + 回退 | **5/5 `rc=0`**，每例 0.36~0.41s |
| 真机发声 | Volume=0 静默真实播放 | 高涨 `rc=0` 4.7s；低落 `rc=0` **10.5s**（`rate=slow` 生效、时长变长符合预期） |

**未覆盖（如实标注）**：① 音色与韵律的**听感**需人耳验收（本记录只证明"被 SAPI 接受，且时长受快/慢档控制"）；
② `qt_widgets` / `qt_app`（PySide6 板端 UI）**仍未接 TTS**，本机无 PySide6，接线只在 Tk 演示台完成。

## 七、边界与风险（重要）

1. **现役 SAPI 是拼接式语音**：LLM 能驱动的只有"语速 / 音高 / 音量 / 停顿"四个自由度，其中音高变调偏生硬。
   **"自然的语气变化"必须换神经 TTS**（D5 §14.4 / W12-04 的 VITS、Kokoro 候选）——`TtsStyle` 表届时**一行不动**即可复用。
2. **⚠ 架构级提醒：语音语速与素材变速必须同源**。项目已有 `avatar_timing.speed_for_state()`（0.85~1.15，按状态 + 句长）在给**素材**变速；
   如果将来 TTS 也按 emotion 变语速而不共用同一系数，就会出现"语音与玩偶口型/动作不同步"。**S2 必须把两者收敛到一个语速系数。**
3. **语速基准不一致**：TTS 实测 ≈3.3 字/秒，而 P0-2 的 `CHARS_PER_SECOND=4.5` 偏快（历史遗留，未动已验收行为）。
4. **联网神经语音的口径冲突**：Edge 免费接口（`speech.platform.bing.com` 实测可达）**不支持** `mstts:express-as style`，
   其 `VoicePersonalities` 只是音色标签；且它是**公网服务**，与"不能把 Windows 本地服务与公网云服务延迟混为一个数字"（入口文档 §186）冲突，
   并影响 **T19 停声 P95≤300ms**。若采用，须补口径/ADR 并保留本地降级。
5. **回退成本**：一行（不传 `style`）；`ENABLE_PITCH=False` 关音高；未提交前可整体 `git checkout`。

## 八、下一步

1. **S2（按 D5 口径）**：`TtsBackend` 增加 `SherpaVitsBackend`（离线、可冻结、与现役 ASR 同生态），按 W12-04 记录音色/发音/音频格式/资源/延迟；`TtsStyle` 表复用。
2. **S2 必须同时做**：把 TTS 语速与 `avatar_timing` 素材变速**收敛到同一系数**（§七.2）。
3. **试听台（人选音色）**：把 14 个中文神经音色对同一句批量合成 → HTML 播放列表，人耳选定 1~2 个主音色后固化。
4. **板端接线**：把 TTS/语气层接进 `qt_widgets` / `qt_app`（需装有 PySide6 的环境）。
5. **待拍板**：是否把 `CHARS_PER_SECOND` 由 4.5 校准到 ≈3.3（会影响已验收的 P0-2，须重跑 `verify_v2_timing.py`）。

## 九、涉及文件清单与回滚

| 文件 | 类型 |
|---|---|
| `board/runtime/audio/tts_style.py` | 新增（语气层，可整文件删除） |
| `board/runtime/audio/tts.py` | 改（后端 `ssml` 形参 / `_script` 双分支 / `speak_async(style)` / `stats.style`） |
| `board/runtime/audio/__init__.py` | 改（导出） |
| `tools/demo_stage.py` | 改（`for_emotion` 接线 + 日志） |
| `tests/test_tts_style.py` | 新增（7 项） |
| `docs/LLM驱动语音语气_emotion韵律与SSML_技术记录.md` + `.docx` | 本记录 |

**回滚**：① 运行时——`demo_stage` 去掉 `style=` 参数即恢复恒定语气；② 代码——`git checkout` 上述文件（`tts_style.py` 与测试可直接删）。
