# AURA 玩偶「生命感」— 项目接手说明（当前进度与待办）

> 2026-10-05 最新同步：本共享工作区项目根为 `E:\项目\共享文件夹\aura`。播放自然度第二步已完成，当前采用连续源帧游标、主窗口平滑折返、相邻帧插值和原动作收尾，停用不兼容窗口硬切。板端输入合同1.2及C参考已同步。最新交接以 `docs/说话播放层完善与素材交接_2026-10-05.md` 及 `../deliverables/2026-10-05_avatar_naturalness/最新工作说明.md` 为准。已提供v3生成工作流、七类提示词和21图；新素材未生成、未接入，实机音画同步仍待验证。下方旧环境和历史“全部完成”声明不能替代当前范围。

> **2026-10-06 本机镜像核对（本地补注，未改下文）**：本机（**无 E 盘**）看到的是 `E:\项目\共享文件夹\aura`
> 的同步镜像 `D:\share、\项目开发\FPGA-amd自主命题赛道\aura`；本文与 v3 文档里的 `E:\...` 命令在本机
> **不可直接执行**，须换盘符。本机 `.venv` **未装 dev 依赖**（`pytest` 不可用），文中 `509 项` 为项目侧
> 验证 venv 的结果；两侧均**无 git 仓库**。详见 `docs\镜像与盘符口径_2026-10-06.md`。

> **这份文档写给下一个接手的 AI / 开发者。**
> 读完 §1~§4（约 5 分钟）你就能知道：项目在做什么、代码在哪、现在做到哪、下一步做什么、哪些坑不能踩。
> 更细的技术细节见 §10 的文档索引（不必一次读完）。**最后更新：2026-10-04。**

## 1. 三十秒上手

| 问题 | 答案 |
|---|---|
| 项目根目录 | `D:\share、\项目开发\FPGA-amd自主命题赛道\aura` |
| 当前主题 | 让"帧序列玩偶"看起来**活着**：动作自然、状态可辨、循环看不出接缝 |
| 本阶段状态 | **播放侧全部完成并已接入生产层**；**素材侧待重制**（见 §7） |
| 先跑这条验环境 | `".venv\Scripts\python.exe" -s tools\verify_idle_alive.py` → 期望 `RESULT: OK` |
| 先看这个样品 | 浏览器打开 `docs\demo_alive\index.html`（双击即看，12 个动图对比） |
| 最容易踩的坑 | §9（**分析带 alpha 素材绝不能 `convert("RGB")`**、**Word COM 渲染期间不能跑别的命令**） |

## 2. 本机环境事实（决定"什么能做、什么不能做"）

| 事实 | 含义 |
|---|---|
| **没有系统 Python**（`python` 指向 Store 别名，调用即失败） | 一切 Python 命令都用 `aura\.venv\Scripts\python.exe` |
| `.venv` 已装 | numpy / pillow / onnxruntime / sherpa-onnx / sounddevice；**没有 pytest** |
| **没有 PySide6** | `board/interaction/qt_widgets.py`（板端渲染层）**本机跑不了**，只能 `py_compile` 检查语法；要看实机效果用 `tools/demo_stage.py`（tkinter） |
| 有 tkinter 9.0 + PIL | 所以演示台用 Tk，出片用 PIL |
| 有 Microsoft Word 16（COM） | md→docx 走 `render_docx.ps1`（**很慢，约 1~3 分钟；渲染期间不要跑别的命令**，否则会被掐死） |
| 路径含中文与顿号 | 命令行传参加引号；**脚本源码保持纯 ASCII**（PowerShell 5.1 会把无 BOM 的 UTF-8 当 ANSI 读） |
| 终端行为 | **换命令会掐死上一个前台命令** → 长任务要么等它跑完，要么 `Start-Process` 脱离 |

## 3. 代码结构与数据流

```
素材（assets/avatar/<素材名>/）
  000000.png … 000NNN.png    帧序列（RGBA 透明 PNG；按文件名排序 = 播放顺序）
  meta.json                  fps / size / framing / source
  motion.json      ← 预计算  逐帧运动量 diffs + 放慢倍率（匀速化用）
  segments.json    ← 预计算  enter / loop / exit 三段帧区间（三段式用）

        ↓ 读取（avatar_assets.read_motion / read_slowdown / read_segments，零像素开销）

board/interaction/avatar_timing.py     ★ 播放逻辑的**唯一来源**（纯函数，无 Qt / PIL）
  idle_offsets()           潜动层：呼吸 / 重心 / 微摆（锚点 = 显示框底边中心，全局时间基）
  warp_time()              匀速化：按累积运动量重参数化时间 ⇒ 循环点速度连续
  playback_time()          ★ 统一播放入口：burst 原样 / loop → 匀速化 + 放慢
  Segments / segment_time() / segment_at() / stage_seconds()    三段式（含"阶段独立求值"）
  segment_blend_seconds()  阶段切换的交叉淡化时长（SEGMENT_BLEND_MS = 150）
  pingpong_time()          往返映射（用于**保持段**来回 / 呼吸往返；⚠ 不要用于整段素材）

        ↓ 两端共用同一份口径（这是刻意的，见下"为什么"）

tools/demo_stage.py（tkinter，本机可跑）          board/interaction/qt_widgets.py（PySide6，板端）
  StageCore.sop()                                    _SpriteSequence(diffs/segments/slowdown)
  StageCore._apply_offsets()（PIL）                  _playback_time()
  frame_at() → playback_time / segment_time          _draw_sprite_frame(…, off)（QPainter 变换）
        ↓                                                  ↓
  屏幕上：玩偶在缓慢呼吸、循环看不出接缝            AvatarPanel 绘制（锚点 = 底边中心）
```

**为什么播放逻辑要单独一个模块**：`qt_widgets` 依赖 PySide6，而本机装不了 → 验收脚本会拿不到取帧口径，
出现"验收测的不是播放层"。所以**所有**取帧/时间映射都定义在 `avatar_timing`，渲染端只负责调用。

## 4. 已完成的里程碑（2026-10-04 一天内）

| 里程碑 | 交付物 | 验收 |
|---|---|---|
| **运动量体检**（先算后看） | `docs\玩偶素材运动量与可辨识度_数值体检_技术记录.md` | 数值报告 |
| **潜动层 L0**：呼吸(8s) / 重心 / 微摆；复合周期 **133 分钟** | `avatar_timing.idle_offsets` | `tools\verify_idle_alive.py` → OK |
| **循环无缝**：匀速化 + 放慢（循环点速度突变比 **0.22 → 1.18**） | `avatar_timing.warp_time / playback_time` | `tools\verify_loop_seam.py` → OK |
| **素材 SOP**：批量预计算运动量表 + 体检 | `tools\build_motion_table.py` → **13 个 `motion.json`** | 11/13 达标 |
| **三段式**：抬手 → 空中保持（往返）→ 放下 | `avatar_timing.Segments / segment_time` | `tools\split_avatar_segments.py` → 13 个 `segments.json` |
| **打断衔接**：阶段独立求值 + 150ms 交叉淡化 | `segment_at / stage_seconds / segment_blend_seconds` | 样品 `cut_hard` vs `cut_blend` |
| **生产层接入（S3）** | `qt_widgets` / `demo_stage` 共用新口径 | `tools\demo_stage.py --selftest` → **SELFTEST OK** |
| **样品页**（12 个动图对比） | `docs\demo_alive\index.html` | 浏览器直看 |

## 5. 现在就能跑起来看什么

| 目的 | 命令 | 期望 |
|---|---|---|
| **看玩偶实机效果**（tkinter 演示台） | `".venv\Scripts\python.exe" -s tools\demo_stage.py` | 窗口里点「来访者进入 → 唤醒 KWS → 说完 VAD」→ 输入文本 → 看播报（应看到**抬手 → 空中轻晃 → 放下** + **缓慢呼吸**） |
| 演示台自检（无窗口） | `".venv\Scripts\python.exe" -s tools\demo_stage.py --selftest` | `SELFTEST OK` + 拼图 `docs\demo_stage\stage_selftest.png` |
| 潜动层数值验收 | `".venv\Scripts\python.exe" -s tools\verify_idle_alive.py` | `RESULT: OK`（呼吸 2.62px / 帧间 0.086px / 复合周期 3432s） |
| 循环接缝验收 | `".venv\Scripts\python.exe" -s tools\verify_loop_seam.py` | `RESULT: OK`（现状突变比 0.22 → 匀速化 ≈1） |
| **状态合同验收** | `".venv\Scripts\python.exe" -s tools\verify_state_contract.py` | **`RESULT: OK`**；`C4` 警告 = 板端清单待重导（本机无 PySide6），可先忽略 |
| **语音事件链回归** | `".venv\Scripts\python.exe" -s tools\verify_voice_chain.py` | **`RESULT: OK`**（6 条链：按键 / KWS 唤醒 / 唤醒播完 / 麦克风 / 快路径 / 取消回迁） |
| **取消完整性** | `".venv\Scripts\python.exe" -s tools\verify_cancel.py` | **`RESULT: OK`**（6 项：正常轮 / **取消后旧响应作废** / 取消后重发 / 标志位 / 非法代次 / FSM 回迁） |
| **三段式退出编排** | `".venv\Scripts\python.exe" -s tools\verify_segment_exit.py` | **`RESULT: OK`**（7 项：阶段推进 / 中途打断 / 淡化无跳变 / 停在末帧 / 1.0·3.7·9.3s 任意时长） |
| **测试（无 pytest 轻量跑）** | `".venv\Scripts\python.exe" -s tools\run_tests_light.py [--only test_fsm]` | `RESULT: OK`；其余模块 `SKIP`（缺 pytest / opencv，本机未装，非代码问题） |
| 看样品对比页 | 双击 `docs\demo_alive\index.html` | 12 组动图（潜动层幅度 / 呼吸快慢 / 说话三段式 / 打断衔接） |
| 重出样品页 | `".venv\Scripts\python.exe" -s tools\make_alive_sample.py` | webp 已存在则跳过；加 `--force` 全量重建（约 5 分钟） |

**想放大呼吸幅度看效果**：把 `demo_stage.StageCore.idle_gain` 改成 `2.0` / `4.0`（生产恒 1.0）。

## 6. 素材侧 SOP（**新素材入库后必须跑**）

源素材（i2v 生成，约 5 秒量级）**动作又快又大** → 直接循环会"顿一下 + 节奏急促"。统一处理四条：

```
① 匀速化（warp_time）  按累积运动量重参数化时间 ⇒ 循环点速度连续
② 整体放慢 ×1.5        LOOP_SLOWDOWN = 1.5 ⇒ 节奏舒缓、每帧变化更小
③ 潜动层叠加           呼吸 8s / 重心 / 微摆 ⇒ 持续生命感（不再依赖素材循环）
④ 三段式（若有保持段） enter → loop（**往返**）→ exit；被打断时 150ms 交叉淡化
```

**新素材入库后的两条命令**（无需改任何代码）：

```powershell
cd /d "D:\share、\项目开发\FPGA-amd自主命题赛道\aura"
".venv\Scripts\python.exe" -s tools\build_motion_table.py --write     # → 每素材 motion.json
".venv\Scripts\python.exe" -s tools\split_avatar_segments.py --write  # → 每素材 segments.json
```

**判据**（脚本会打印，超阈值标 `★需检查`）：
- `motion.json`：处理后**循环点速度突变比** `|x-1| < 0.35`（≈1 = 看不出循环）；
- `segments.json`：`loop` 段**首尾姿态差 < 6 灰阶**（能自然衔接）且长度 `≥ 8 帧`。

### 6.1 ⚠ 动作类型分治（**先分清类型，再谈处理**）

素材分两类，处理方式**完全不同**，不能一把梭：

| 类型 | 素材 | 播放语义 | **禁止** |
|---|---|---|---|
| **burst（一次性动作）** | `ack_nod`（点头）、`deny_shake`（摇头）、`emo_surprised`（惊讶） | **整段播一次** → 末帧停住 → 由上层续接（回 IDLE / 接播报） | **禁止**三段式 / 循环 / **从中间帧起播** —— 点头摇头"取中间帧"会变成"半路卡住"，动作语义全毁 |
| **loop（持续动作）** | `idle_*`、`talking_*`、`emo_puzzled`、`emo_sad` | 匀速化 + 放慢；有 `segments.json` 时走三段式（enter → loop 往返 → exit） | — |

**判定依据（单一来源）**：`avatar_assets.BURST_STATES`（运行时状态）与
**`BURST_ASSETS`**（素材名集合，由前者反查）；工具链用 `avatar_assets.is_burst_asset(name)`。

**已做的三重保护**（用户 2026-10-04 指出后加固）：

1. `tools\split_avatar_segments.py` **跳过 burst 素材**（不生成 `segments.json`）—— 实测 13 → **10 个**；
2. `demo_stage.StageCore.sop()` 对 `BURST_STATES` **不返回 `seg`**（目录里即便有残留也忽略）；
3. `qt_widgets._sprite_sequence()` 对 `BURST_STATES` 同样**不加载 `segments`**。

⇒ **结构上不可能把点头 / 摇头当三段式播**，而不是"靠调用顺序侥幸"。


## 7. 待办清单（按优先级）

### P0 — 立刻可做（播放侧收尾）

1. **三段式打断编排（运行时状态机）** —— 把 `enter → loop → 被打断 → 150ms 淡化 → exit` 接进
   `qt_widgets` / `demo_stage`。
   - 引擎已就绪：`segment_at(t, seg, fps, stage=…)` / `stage_seconds()` / `segment_blend_seconds()`；
   - 还需新增：播放层的**阶段字段**（enter/loop/exit）+ "该走了"触发（`AUDIO_PLAYBACK_STOP` / 用户插话 / 状态迁移）；
   - 现状：`demo_stage` 用的是 `segment_time`（**固定周期版**，按句长估循环次数），**没有真正的打断**。
2. **刷新 `segments.json` 的 `loops_hint`**：是旧公式残留（26）。运行时**不用**它（用 `loops_for_duration`），
   重跑 `split_avatar_segments.py --write` 即刷新 —— 小事，但别被它误导。
3. **PySide6 端目视复核**（唯一"没有眼睛看过"的地方）：在有 PySide6 的机器上跑 `qt_app.py`，
   确认 `AvatarPanel` 的呼吸/三段式观感与 `demo_stage` 一致。

### P1 — 素材重制（**根治**，需要生成侧配合）

4. **重制待机/说话族素材，显式包含"保持段"**：
   - 现状问题：自动切段实测 **loop 段首尾姿态差 9~17 灰阶**（比素材平均帧间差还大）⇒
     **素材里没有"手停在空中小幅动"的段落**，强行三段式只能"带小跳地循环"；
   - 生成侧口径（5 秒素材）：`抬手 1s → 保持 3s（手停在半空、仅手腕/手指轻微动、**不回起始姿态**）→ 放下 1s`；
   - 提示词要点：`…动作结构：抬手打招呼 → 手停在半空保持 3 秒（只做轻微自然晃动，手不要放下、不要回到起点）→ 再自然放下…`；
   - 完成后跑 §6 两条命令；判据变成 "loop 段首尾差 < 6 灰阶"。
5. **待机族差异化**（可选，提升"状态可辨度"）：`idle_present` 抬手定格 / `idle_listening` 侧头 12° /
   `idle_thinking` 托下巴 + 视线偏上 / `idle_offline` 头低垂。
   验收门用"**时间中位帧两两距离 ≥ 3 灰阶**"（现有 `verify_v2_amp.py` 只测"在动"，测不出"不同"）。

### P2 — 可选增强

6. `qt_app.py` 主定时器 `50ms → 25ms`（20Hz→40Hz），消除"24fps 素材在 20Hz 刷新下丢帧"。
7. TTS 包络驱动口型（`avatar_timing` 已有 `speed_for_state`，可与 TTS 的 `speed` 收敛到同一系数）。
8. `avatar_lod.py` 第 37/39 行**重复定义** `DEFAULT_BUDGET_MB`（生效 10.0；注释里想改成 12.5 但**未生效**）→ 待清理。

## 8. 验收约定（改动后请按此自查）

| 改了什么 | 必须跑 | 通过标准 |
|---|---|---|
| `avatar_timing`（时间映射 / 潜动层） | `verify_idle_alive.py` + `verify_loop_seam.py` | 两个都 `RESULT: OK` |
| 素材入库 | `build_motion_table.py`（**先不带 `--write`** 看报告） | 无 `★需检查`（或人工确认可接受） |
| 切段 | `split_avatar_segments.py` | `loop` 段首尾差 < 6 灰阶 |
| 渲染层（`demo_stage`） | `demo_stage.py --selftest` | `SELFTEST OK` |
| 渲染层（`qt_widgets`，本机无 PySide6） | `py_compile` + **在有 PySide6 的机器目视** | 语法通过 + 观感与演示台一致 |
| 出片 / 页面 | 双击 `docs\demo_alive\index.html` | 动图正常、页面数值与脚本一致 |

**"先算后看"原则**：能用数值判断的（速度突变比 / 首尾姿态差 / 幅度 / 周期）**一律先算**；
只有"观感是否自然"这类主观项才需要看图、看动图。

## 9. 坑与禁忌（都实际踩过，请务必遵守）

### 分析 / 素材类

1. **带 alpha 的素材绝不能 `convert("RGB")` 判白底** —— 透明区会被烤黑/烤白当前景，"边缘剧烈运动"是假象。
   移动分析必须用 **alpha 通道做掩膜**（本项目统一 `alpha > 100`）。
2. **口型 / 眨眼 / 表情这类小尺度细节，禁止用整图或缩略拼图判断** —— 必须裁局部放大，或先做分区数值。
3. **不能用"帧索引差"当速度** —— 它恒为 1（采样步长决定），什么都测不出；要用**画面运动量**
   （累积帧间差 `S[next] - S[now]`）。
4. **统计窗口不能用"前 3 个间隔"** —— 单点取整抖动会污染结论（曾误报 6 个素材需检查）；
   用**前 / 后 1/4 窗口均值**。
5. **放慢周期不改变幅度** —— 只降低"每帧变化率"；要降"起伏本身"得改 `IDLE_BREATH_AMP` 等**幅度常量**。
6. **乒乓（往返）只适用于小幅度区间** —— 整段素材（大动作）往返 = "倒带"（已被否决）；
   **保持段**（小幅微晃）往返才自然。

### 代码类

7. **给多行签名的函数在"第一行前"插代码会把第二行孤立 → `IndentationError`**（本项目踩了 4 次）。
   插入前**先看清完整签名范围**。
8. **脚本源码保持纯 ASCII**（含中文的 `.ps1` 会被按 ANSI 读 → 中文路径失效）；命令行传参加引号。
9. **脚本 print 重定向到文件时 stdout 可能是 GBK** → 统一
   `sys.stdout.reconfigure(encoding="utf-8", errors="replace")`；**不要用 U+2212（−）** 这类 GBK 无映射符号。
10. **HTML 模板是 `%` 格式化字符串 → CSS 里的 `%` 必须写 `%%`**（`transform-origin:50% 100%` 漏转义会直接崩）。
11. **同一元素叠多条 CSS `animation` 会互相覆盖 `transform`** → 必须嵌套三层 `div`；
    且 `@keyframes` 里**不要用 `var()` / `calc()`**（部分浏览器不生效 → 动画完全不动）。

### 工具 / 流程类

12. **Word COM 渲染（md→docx）很慢（1~3 分钟），且渲染期间执行任何别的 `run` 都会把它掐死**
    → 发一条渲染命令后**只用 `read_files` 轮询输出文件**，靠"输出文件 LastWriteTime 晚于 md"判断完成。
    异常退出会留 `WINWORD` 僵尸，清理：`Get-Process WINWORD | Stop-Process -Force`。
13. **终端换命令会掐死上一个前台命令** → 长任务（批产 / 下载 / 渲染）要么等它跑完，要么 `Start-Process` 脱离。
14. **`Get-Content` 的 `.Count` 不能用来数行号**（CRLF/LF 混排会少算）→ 行号以 `read_files` 视角为准。
15. **不要用 `python`（Store 别名）**，用 `aura\.venv\Scripts\python.exe`。
    **本机没有 pytest** → `tests\*.py` 的 pytest 用例在本机跑不了，
    等价断言要写在 `tools\verify_*.py` 里（零依赖、可直接跑）。

## 10. 文档索引（需要细节时再读）

| 文档 | 读它的场景 |
|---|---|
| `docs\项目接手说明_AI_当前进度与待办.md` ← **本文** | 接手第一份 |
| `docs\玩偶生命感潜动层_技术记录.md`（+ docx） | 潜动层 / 匀速化 / 三段式 / 打断 / 生产层接入的**全部技术细节、决策与踩坑**（§1~§10） |
| `docs\玩偶素材运动量与可辨识度_数值体检_技术记录.md` | "动作幅度够大但状态不可辨"、"顿"的根因（体检数据） |
| `docs\玩偶状态系统重设计_技术记录.md` | 14 态状态机 / 素材映射 / burst 语义的设计依据 |
| `docs\本地LLM玩偶实机演示台_技术记录.md` | `tools\demo_stage.py` 的设计与用法 |
| `docs\语音对话链路_技术记录.md` / `docs\本地神经TTS接入_…技术记录.md` | 语音链路（ASR / VAD / TTS） |
| `docs\玩偶帧序列素材接入_技术记录.md` | 素材入库规格（LOD / 取景 / 体积预算） |
| `.cline-handover.md`（项目根） | 逐会话工作流水（很长；按需检索第 40/41 条） |

## 附：本次改动文件清单（供交接核对）

| 文件 | 改动 |
|---|---|
| `board\interaction\avatar_timing.py` | **核心**：潜动层（`idle_offsets`）/ 匀速化（`warp_time`）/ 统一入口（`playback_time`）/ 三段式（`Segments`、`segment_time`、`segment_at`、`stage_seconds`）/ 打断淡化（`SEGMENT_BLEND_MS`、`segment_blend_seconds`）/ 往返（`pingpong_time`） |
| `board\interaction\avatar_assets.py` | 新增 `read_motion` / `read_slowdown` / `read_segments` |
| `board\interaction\qt_widgets.py` | `_SpriteSequence` 加 SOP 字段；新增 `_playback_time()`；`_draw_sprite_frame(…, off)`；`_render_avatar` 改口径 |
| `tools\demo_stage.py` | 新增 `sop()` / `_apply_offsets()`；`frame_at()` 改口径；`idle_gain` |
| `tools\verify_idle_alive.py`、`tools\verify_loop_seam.py` | **新增**验收脚本（均 OK） |
| `tools\build_motion_table.py`、`tools\split_avatar_segments.py` | **新增**预计算脚本（素材 SOP） |
| `tools\make_alive_sample.py` | **新增**样品出片（12 组对比） |
| `docs\demo_alive\*` | 样品页 + 12 动图 + 静态图 |
| `assets\avatar\*\motion.json`、`segments.json` | **新增**预计算数据（各 13 个） |
| `docs\玩偶生命感潜动层_技术记录.md`、`docs\项目接手说明_AI_当前进度与待办.md` | 技术记录 / 本文档 |
| **未改动** | `fsm.py`、`avatar_assets.STATE_ASSET`、`assets\avatar\*\*.png`（素材本体）、`qt_app.py` |

## 11. 外部审查发现（2026-10-04，**下一轮修改清单**）

> 来源：`E:\项目\output\共享玩偶审查_2026-10-04\共享文件夹_玩偶部分详细审查.md`
> （审查者**未改动**本仓源码与素材）。**请把本节与 §7 合并看** —— 本节是**实测复现出来的问题**，
> 优先级高于 §7 里我自己列的增强项。

### 11.1 总体定位

**素材与 PC 原型有实质内容、值得沿用；但还需一轮「集成修正」才能作为稳定的整机交付。**
对方认可：13 组动画 / 456 张透明 PNG、**逐帧哈希全部匹配**；工程拆分合理（事件 / 状态机 / 素材解析 /
播放时序 / 界面 / 语音 / 对话适配器分离）；交互设计（高·中·低情绪播报、点头、摇头、困惑、断网）已考虑；
呼吸与微摆有实际实现；留下了检查工具与交接说明（但**部分检查与当前运行路径已脱节**）。

### 11.2 必修清单（按对方建议顺序）

| # | 问题 | 复现 / 证据 | 归属 |
|---|---|---|---|
| 1 | **正常唤醒流程会卡住**：状态停在"聆听"、回复事件被拒；需**连发两次"说完"**才进思考 | 实测"唤醒 → 一次说完 → 收到回复"；`demo_stage` 自检也是绕过去的 | ✅ **已修（2026-10-04，见 §13）**：`fsm.py` 补 3 条迁移（`AWAKE+VAD_END→THINKING`、`AWAKE+PLAYBACK_STOP→LISTENING`、`AWAKE/LISTENING+回复→SPEAKING`）+ 新增 `tools\verify_voice_chain.py` 回归探针（6 链全绿） |
| 2 | **麦克风后续流程缺口**：已进"聆听"后，识别文本送模型时**没有推进到"思考"** → 可能"回复已显示、声音已播，玩偶仍停在聆听" | 语音链路 | ✅ **已修（2026-10-04，见 §13）**：`demo_stage._send_llm()` 原来只在"不在 LISTENING/THINKING"时推进 ⇒ 已在聆听时**不发 VAD_END**；现改为"在 LISTENING 也发"⇒ 识别完成即进 THINKING |
| 3 | **状态定义不统一**：运行时/素材映射已 **15 态**，而 UI 数据合同 / 显示标签 / 板端导出仍 **10 态**；新增的中性播报 / 唤醒 / 困惑 / 点头 / 摇头没贯穿；**中性播报还是默认档**（影响普通回复） | 代码对照 | ✅ **合同与映射已对齐（2026-10-04，见 §12）**：`AVATAR_MAP` 与 `ui_state.schema.json` 均补齐 15 态 + 新增 `tools\verify_state_contract.py` 校验；**板端清单仍待重导**（#7） |
| 4 | **取消未完整取消对话**：取消事件**没停 TTS**；取消后迟到的旧回复仍被显示并念出 | 调用实际回调方法复现 | ✅ **已修（2026-10-04，见 §14）**：新增**对话代次**（`StageCore.new_turn/cancel/accept_response`）+ `_on_response` 代次校验 + **`cancel_talk()`**（停 TTS + 作废在途 + 送取消事件，**Esc** 绑定）+ `tools\verify_cancel.py`（6 项 → OK）。⚠ `tts.stop()` 的**实际停声**需有音频环境复核 |
| 5 | **动画收尾未完成**：12/13 组素材**未达项目自己的保持段标准**；三段式按预计句长循环，**"说完 / 被打断 → 平滑退出"未接入**；几种待机姿态接近 | 切段检查 | ✅ **播放侧已修（2026-10-04~05，见 §15 / §18 / §19）**：① 固定周期 → **事件驱动阶段机**（enter → loop 往返 → 说完/被打断 → 150ms 淡化 → exit），`verify_segment_exit.py` 8 项 OK；② **loop 段多窗口轮换**（`E9`：loop 段 21 个不同帧 vs 单窗口 8）；③ **跨素材交替**：素材池 `avatar_assets.POOLS/pool_assets()` 已就绪 + 生成脚本 `tools/gen_talking_variants.py`（3 段变体，⏳待执行生成）；⚠ **素材侧仍待重制**（保持段首尾差 9~17 灰阶；**口型跟随语音**需口型素材）；⚠ 播放层阶段机**目前只接演示台**，`qt_widgets` 仍用旧固定周期（待统一） |
| 6 | **随机相位验收误判**：程序打印的相位/速度不同，但三段式取帧分支**没用这些值** → 重复 4 次进入同一播报态、连续 10 秒取帧序列**完全相同**，自检仍"通过" | 实测复现 | ⚠ **本轮改动引入的验收盲区** → 已修，见 §11.3 |
| 7 | **板端交付物是旧版本**：资源表记录"100 帧 ≈10fps"，实际是 **39/22 帧 24fps**；共享目录**没有 `frames.rgb565`**；LVGL 目录只有资源头文件、**未见动画播放器** | 目录对照 | 板端导出 + 上板验证 |
| 8 | **测试**：抽跑无夹具用例 → **52 通过 / 5 失败**（完整对话流程、重复定义测试辅助函数、引用未定义变量）；共享 `.venv` 指向**舍友电脑的 D 盘路径**，本机无法直接启动 | 跑 `tests/` | ✅ **已处理（2026-10-04，见 §16）**：`requirements.txt` 已补（venv 的 `home` 实为**本机** ComfyUI 便携 Python 绝对路径 ⇒ 换机须重建）；`test_fsm.py` 的**重复定义 + 未定义变量 + 1 条 v2 过时断言**已修（`run_tests_light --only test_fsm` → **PASS 19 / FAIL 0**）；新增无 pytest 也能跑的 `tools\run_tests_light.py`；其余 8 模块缺 pytest、1 个需 opencv（本机依赖现状） |

### 11.3 本轮已修（#6：验收盲区 **+ 其根因**）

**① 验收改为"看画面"**（`demo_stage --selftest`）：
- 原来看**参数**（打印的 `phase` / `speed`）→ 现在对同一状态连续采样约 10 秒的
  **帧索引序列（指纹）**，比较"两次进入是否真的不同"；
- 新增 **SOP 生效检查**（`motion.json` / `segments.json` 是否真被读到）；
- 新增 **"序列不能恒定"** 检查（动画真的在动）；
- `SELFTEST OK` / **`SELFTEST FAIL`** 都会出现 —— **它现在真的会失败**。

**② 修根因：保持段补上随机相位**
- 问题：接三段式时**保持段（loop）没有随机相位** → 两次进入同一播报态，帧序列完全相同
  （enter / exit 段本就不该随机，但 **loop 段应该随机**）。
- 修法：`segment_time()` / `segment_at()` 新增 `loop_phase`（作用于**保持段起点**；
  `pingpong_time` 内部取模 ⇒ 相位是整体平移、**不产生跳变**）；两端调用处传入各自随机相位
  （`demo_stage` 用 `self._phase`，`qt_widgets` 用 `_loop_phase(sequence)`）。

**③ 修复前后实测（同机器、同种子）**

| | 修复前 | 修复后 |
|---|---|---|
| 两次入场帧序列 | 相同 → `SAME [FAIL]` | **不同 → `DIFFERENT [OK]`** |
| 自检结论 | `SELFTEST FAIL（1 项）` | **`SELFTEST OK`** |

> ⚠ **#5 仍然成立**：**12/13 素材未达保持段标准**，且**"说完 / 被打断 → 平滑退出"未接入**。
> `--selftest` 目前**不会**因这两条失败（不在其覆盖范围）→ 请以 §6 两条命令的输出为准。


### 11.4 对方建议的执行顺序（与 §7 合并后）

> **先修状态合同（#3）、语音事件链（#1 / #2）和取消逻辑（#4）→ 再整理测试（#8）、接通动画退出（#5）
> → 最后重新生成板端资源（#7）并联调。**
> 对方原话：现在继续增加动作数量对整体完成度帮助有限；**把现有动作接进可靠的交互流程，更能提升展示效果。**

**尚未实测**（对方声明）：未连 KV260 / MCP01、未跑 Qt 实时界面 → 板端性能、真实录放音、实时动画观感仍需实测。

### 11.5 第三方运行检验（2026-10-04，第二位审查者，**在真实 Tk 窗口 + 真实 `StageCore` 上跑**）

来源：`C:\Users\35870\Downloads\玩偶实际运行状态检验.md` + `runtime_results.json`（内含**源码 SHA256 指纹**）。

**① 指纹核对：与本仓库当前代码完全一致** ✅ ⇒ **它的结论对应同一版本，可直接采信**

| 文件 | 指纹（它记录 = 本地实测） |
|---|---|
| `tools\demo_stage.py` | `e42d7d78…08c95` ✅ |
| `board\runtime\fsm.py` | `e23baa70…11111` ✅ |
| `board\interaction\avatar_timing.py` | `4f8bd81e…0c841` ✅ |
| `board\interaction\avatar_assets.py` | `78048f7e…c7d65` ✅ |

**② 它更正了上一轮的结论（§11.3 的修复被独立验证）**
- **"随机相位已接入"**：`IDLE` / `LISTENING` / `THINKING` / `SPEAKING_NEUTRAL` 各重复进入 3 次、
  每次采样 30 秒 @30Hz ⇒ **三次帧索引序列均不完全相同** ⇒ 保持段相位确实作用于**画面**；
- 进入段仍从第 0 帧起播（**这是设计**：抬手 / 放下必须完整），所以"首帧相同"**不代表**相位无效；
- 保持段已改**往返**播放 ⇒ 上一轮"单向保持段接缝"的判断**不能套用**；
- 它**保留**的两条限制（正确）：① 显示的 `speed` **没有**直接进三段式取帧（句长目前只影响**循环次数**）；
  ② 三段式仍是**固定周期**，**未接入**独立阶段（`segment_at`）与过渡混合（`segment_blend_seconds`）；
- 它明确：**本机`能`跑 Tk 窗口**（不应再说"项目无法在本机运行"）。

**③ 它实测确认可用**
- **15/15 态均可取帧**、无素材缺失；帧数/帧率与本站记录一致（39 或 22 帧 @24fps）；
- 按键 → **一次**句尾 → neutral / happy / sad 回复 → 播放结束：**均通过**（`LISTENING→THINKING→SPEAKING_*→IDLE`）；
- 相机丢失 / 断网恢复：通过；有人 → 聆听 → 思考 → 取消：回到 `PRESENT`；
- 计时链路：`0.09s ACK_NOD → 0.94s SPEAKING_NEUTRAL → 3.33s IDLE`（点头 → 说话 → 空闲的续接机制有运行基础）。

**④ 它复现的缺口（与 §11.2 一致，并给出 Qt 侧证据）**
- 来访者 → **KWS 唤醒** → 一次句尾 → 收到回复：**失败**（`PRESENT→AWAKE→LISTENING`，回复被拒）⇒ **#1**；
- KWS 唤醒 → 播放结束：仍停在 `AWAKE`、结束事件被拒 ⇒ **缺"唤醒动画结束编排"**（#1 附）；
- **Qt 标签回落"待机"**的状态：`SPEAKING_NEUTRAL`、`PUZZLED`、`ACK_NOD`、`DENY_SHAKE`、`AWAKE`
  ⇒ 这是 **#3（15 态 vs 10 态合同不一致）的直接现场证据**（见 `runtime_results.json` 的 `qt_label` 字段）；
- 观感：聆听 / 思考 / 高情绪播报**姿态有区别**；但**低落 / 错误 / 离线在小尺寸下不易一眼分清**，
  相机丢失与断网**共用素材**（`idle_offline`）。

**⑤ 它的完成度判断（我认同）**

> **可演示的 PC 动画原型；整机交互流程和板端交付待修正、待实测。**
> 下一步最优先：**把一次正常语音事件链修通、统一状态合同**，再接入真正的结束 / 取消编排。

**⑥ 与 §7 / §11.4 的关系**：它的优先级与本接手文档一致（先 #3 合同 → #1/#2 语音链 → #4 取消 → #8 测试 → #5 退出编排 → #7 板端），
**没有新增待办**，但把 #1 / #3 从"代码推断"升级为"**实测复现**"。




