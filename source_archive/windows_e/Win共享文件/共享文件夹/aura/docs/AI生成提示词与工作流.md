# AURA 演示台 · AI 生成提示词与工作流（可粘贴 / 供其他 AI 复核）

> 读者：接手本项目的**其他 AI（含新窗口）**与开发者。目的：把"**用什么提示词让 AI 干活 →
> AI 按什么流程干 → 怎么确认干对了**"固定下来，避免每次都重新发明。
> 最后更新：2026-10-06（本机镜像同步：播放核心改为 `avatar_player.py`、演示入口改为
> `run_demo_script.bat`、板端合同 1.2、项目侧 pytest 509 项、新增 §7 提示词资产索引 / §8 镜像与盘符口径）。

## 1. 提示词分三层（缺一层 AI 就会跑偏）

| 层 | 作用 | 放在哪 |
|---|---|---|
| ① 任务提示词 | 你是谁 / 做什么 / 做到什么算完 | 新窗口第一句（§2 模板） |
| ② 约束提示词 | 不许违反的硬线（环境 / 接口 / 文档 / 验收） | Cline 全局规则 + 本文 §4 |
| ③ 交接提示词 | 只动哪个文件、先读哪些文件、下一步做什么 | `.cline-handover.md` + `docs\项目接手说明_AI_当前进度与待办.md` |

## 2. 任务提示词模板（方括号处替换，可整段粘贴）

```
你是 [项目] 的 [角色，如：Python 桌面端工程师]。
任务：[一句话目标 + 产物路径]
必读（先读再动手，不要臆造进度）：[接手说明] / [目标文件] / [接口来源]
硬约束：见 aura\docs\AI生成提示词与工作流.md §4（环境、命名、单一来源、不改设计文档 API）
验收：1) 必须给出**可执行**的验证命令与预期输出，不许"看起来对"；
      2) 关键结论给**数值判据**（计数 / 阈值 / 时间戳先后）；
      3) 文档 md+docx 成对；4) 收尾更新 .cline-handover.md。
输出：只给 Diff（除非我明确要求完整文件）；结论 ≤3 行摘要。
```

## 3. 本项目实际生效的提示词（实例·据会话还原）

- **任务**：为 AURA 玩偶演示台补"看着演"的真窗口验收路径 —— `tools/demo_script.py --window`：
  复用 `demo_stage.StageCore` 与 `ScriptRunner._fire`（**不复制任何剧本逻辑**），真实时钟演 66 s 剧本。
- **约束**：类名/方法名必须遵循 `docs/` 既有约定；本机无 Python ⇒ 一律 `.venv\Scripts\python.exe`；
  文档 md↔docx 成对；办不到的事如实标注，不许谎报产物。
- **验收**：连续渲染（约 12 fps）、三档情绪都能走到、`reset` 零残留、素材池轮换肉眼可见。
- **追加任务（用户反馈）**："点击重播后没反应" ⇒ 按 **症状 / 根因 / 修复 / 验证** 四段式定位并修，
  必须附**可跑的**冒烟证据。

## 4. 硬约束清单（改代码前必读）

1. **环境**：`python` 是 Store 别名不可用；一律 `".venv\Scripts\python.exe" -s <工具>`。
2. **接口**：`docs/` 约定的类名 / 方法名 / 信号不得擅改；要改先与用户确认。
3. **单一来源**：**播放核心只允许一处** —— `board/interaction/avatar_player.py`（`AvatarPlayer`：
   续接 FSM + 素材池 + 连续源帧游标，**独立于 Tk / Qt，两个 UI 与演示剧本共用**）；取帧与时间映射的
   纯函数仍在 `board/interaction/avatar_timing.py`；素材状态判定只在 `avatar_assets`
   （`BURST_STATES` / `is_burst_asset`）。`tools/demo_stage.py` 已重构（61 KB → 39 KB / 672 行），
   **演示工具里不许重写第二套播放口径。**
4. **终端**：Cline 的 `run_commands` 换命令会掐死上一个前台命令 ⇒ 长任务（Word COM 渲染、GUI）
   必须**脱离终端进程树**（WMI `Win32_Process.Create`）；存活核对看**窗口标题**，不看 PID
   （`.venv` 的 `python.exe` 是转发 stub）。
5. **文档**：`docs\*_技术记录.md`（写根因 / 决策 / 验证）+ 同名 docx；跨会话写 `.cline-handover.md`。
6. **本机做不到的要写清**：无 git / 无 `.git`（提交由用户做）；`.venv` **未装 dev 依赖**
   ⇒ `pytest` / `PySide6` / `jsonschema` / `opencv-python-headless` 缺失（`requirements-dev.txt`
   已随工程提供，装了才能跑完整回归）。项目侧已在验证 venv 跑通 **509 项**，见
   `docs\说话播放层完善与素材交接_2026-10-05.md` 与交付集合的 `验证/pytest.log`；
   未装 dev 依赖时回归退化为 `tools\run_tests_light.py`。

## 5. 生成工作流（7 步，每步都有判据）

| 步 | 做什么 | 判据 / 命令 |
|---|---|---|
| 1 定位 | 先检索后读取，只读相关几行 | 能指出 `文件:行号` |
| 2 复用 | 找既有口径（`avatar_timing` / `StageCore` / `_fire`） | 新代码里没有第二套播放逻辑 |
| 3 改前编译 | `cd /d "<repo>" && ".venv\Scripts\python.exe" -m py_compile tools\demo_script.py` | 打印 `COMPILE_OK` |
| 4 冒烟 | 无窗口 / 脚本化点击，不许靠肉眼猜 | `RESULT/VERDICT: OK`，计数随时间**线性增长** |
| 5 场景核对 | `--list` 列剧本、`--quiet` 全速跑、`--window` 真窗口（日常入口＝`tools\run_demo_script.bat`，窗口内 F5 重播） | 29 拍 / 66 s / 三档情绪都出现 |
| 6 落文档 | 技术记录 md + docx（**docx 晚于 md** 才算成功） | `dir /tw <两个文件>` 比时间戳 |
| 7 交接 | 更新 `.cline-handover.md`（必要时同步接手说明） | 新窗口只 `@` 文档即可续接 |

## 6. 可复用验证脚本（本机已跑通）

```powershell
cd /d "D:\share、\项目开发\FPGA-amd自主命题赛道\aura"
".venv\Scripts\python.exe" -u -s "%TEMP%\zz_window_smoke.py" 6000
# → SMOKE: photos=71 wall=6.05s fps=11.7 cb_errors=0 script_errors=0 / VERDICT: OK
".venv\Scripts\python.exe" -u -s "%TEMP%\zz_replay_smoke.py"
# → REPLAY SMOKE: buttons=1 cb_errors=0 marks=3 / 8 项全 PASS / VERDICT: OK
```

- `zz_window_smoke.py`：真开 Tk 跑 N ms 自毁，数 `ImageTk.PhotoImage` 调用次数 ⇒ 证明 tick 连续在跑。
- `zz_replay_smoke.py`：`patch tk.Tk.mainloop` + 定时 `button.invoke()` ⇒ **脚本化点击**，断言
  "重播分隔行之后又出现第 1、2 拍标记"。**本机 GUI 无法人工点击时，这是唯一可靠姿势。**

## 7. 提示词资产索引（本项目三条线，别串线）

| 线 | 单一来源 | 管什么 | 何时用 |
|---|---|---|---|
| ① AI 协作 / 生成工作流 | **本文** | 提示词分层、可粘贴模板、硬约束、7 步工作流、复核清单 | 让 AI **改代码 / 做验收**时 |
| ② 素材生成 v3 | `docs\说话素材生成与验收工作流_v3.md`、`docs\说话素材自然度提示词包_v3.md`、可执行源 `docs\说话素材自然度提示词_v3.json`（**改提示词以 JSON 为准**） | 七类说话素材的英文提示词、已验证模型预设、构建 / 提交 / 抠像 / 体检流程 | 要**生成新素材**时 |
| ③ 历史提示词 | `docs\NEW_WINDOW_PROMPT.md`、`docs\GPT_PROMPT_AVATAR_B2V.md`、`docs\玩偶素材Seedance提示词包_技术记录.md` | 早期玩偶图 / 视频素材的提示词与体例 | 查历史做法；**勿直接复用动作句** |

- 线②两类：**P0**（`talking_calm_rest_v3` 静息循环 / `talking_calm_hold_v3` 手势保持循环 /
  `talking_calm_enter_v3` 进入 / `talking_calm_exit_v3` 退出）、**P1**（`talking_calm_blink_v3` 眨眼 /
  `talking_warm_rest_v3` 温和愉快 / `talking_low_rest_v3` 低落）；39 帧 @24 fps ≈ 1.625 s/条，每类 3 种子。
- 线②工具：构建器 `aura\tools\build_naturalness_workflows.py`、体检 `aura\tools\check_naturalness_candidate.py`、
  抠像 `aura\scripts\prepare_avatar_frames.py`；产物＝21 份 API 图在
  `deliverables\2026-10-05_avatar_naturalness\素材生成工作流\`（`talking_*_v3_s421001/2/3_api.json`，**只构建未提交**）。
- 线②的 `gen_talking_variants.py` 动作句**已作废**（把"十几次口型＋抬手＋两次强调＋两次眨眼"压进 1.625 s 循环即不自然）。

## 8. 本机镜像与盘符口径（2026-10-06 实测，接手先看这条）

| 角色 | 路径 | 本机可达 | 说明 |
|---|---|---|---|
| 权威工作副本 | `E:\项目\共享文件夹\aura` | **否（本机无 E 盘）** | 另一侧会话的实际工作区；新文档里的 `E:\...` 命令**照抄必失败** |
| 本机镜像 | `D:\share、\项目开发\FPGA-amd自主命题赛道\aura` | 是 | 同步副本；本轮抽查新文件（`avatar_player.py` / `avatar_board_manifest.json` / v3 提示词包等）均在 |
| 共享交付 | `E:\项目\共享文件夹\deliverables` ↔ 镜像 `...\deliverables` | 镜像可达 | `2026-10-05_avatar_latest`、`2026-10-05_avatar_naturalness`、`avatar_candidates`（候选批次**尚未创建**） |
| 项目级文档树 | `...\Docs\`（大写 D：方案 / 对齐登记 / D5 需求…） | 是 | 与 `aura\docs\` **不是同一层**，别混引 |
| 项目树（zip 解压） | `...\项目\`（`方案\` / `aura_fpga\` / `Verilog\` / `参赛资料\`） | 是 | 主机模型服务骨架等在此 |

- **盘符纪律**：写给别人执行的命令必须注明目标副本；在本机跑时把 `E:\项目\共享文件夹` 换成
  `D:\share、\项目开发\FPGA-amd自主命题赛道`，反之亦然。**未核实的盘符不得声称已验证。**
- **本机可跑**：`.venv` 播放 / 剧本 / 冒烟、ComfyUI 提交、Word COM 渲染。
- **本机不可跑**：`git`（无 `.git`）、`pytest`（`.venv` 未装 dev 依赖）。
- **生成机就是本机**：ComfyUI 便携版 `D:\sd-webui-aki-v4.11.1-cu128\ComfyUI_Windows_portable_cu130.7z\ComfyUI_Windows_portable`
  （服务已在 `127.0.0.1:8188` 监听），四个模型齐：`diffusion_models\minimax_h3_fl2va_pruned_int8_convrot.safetensors`(≈19.5 GiB)、
  `text_encoders\qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors`(≈14.6 GiB)、
  `vae\minimax_h3_video_vae_int8_convrot.safetensors`(≈2.6 GiB)、
  `loras\minimax_h3_fl2v_turbo_8step_v1.0_comfyui_bf16.safetensors`(≈1.8 GiB)。
- **素材阻塞项**：ComfyUI `input\` 里 `doll_green_9x16.png`（静息参考）**在**（10-04 15:19 / 1036.5 KB），
  `doll_green_9x16_hold.png`（保持参考）**缺** ⇒ P0 的"手势保持循环 / 进入 / 退出"三类**被这一张图阻塞**，
  只依赖静息参考的 4 类（静息循环 / 眨眼 / 温和愉快 / 低落）可先做。

## 9. 供其他 AI 的确认清单（逐条可核，别凭感觉）

1. 命令是否用了 `.venv\Scripts\python.exe`（而不是 `python`）？
2. 改完是否 `py_compile` 且拿到 `COMPILE_OK`？
3. 是否给出**能跑**的验证与**实际输出**（不是"应该没问题"）？
4. 关键结论是否有数值判据（帧数线性 / PASS 计数 / 时间戳先后）？
5. md 改完 docx 是否重渲染，且 **docx 时间戳晚于 md**、`WINWORD` 残留为 0？
6. `.cline-handover.md` 是否已更新（含"下一步读哪些文件 / 跑什么命令"）？
7. 本机做不到的事（git 提交、PySide6、pytest）是否**如实标注**而非假装完成？
8. 本轮新踩的坑是否写进 `docs\*_技术记录.md`？
9. 命令是否写清**目标副本盘符**（本机镜像 `D:` / 权威 `E:`）？有没有把未核实的盘符当成已验证结论？

## 10. 反面清单（本项目真踩过，别再犯）

- **只改状态、漏了驱动**：`replay()` 重置了 `cursor/done/wall` 却没补 `root.after(...)`
  ⇒ 点重播"没反应"（详见《演示剧本_情绪调度与节奏_技术记录》§6.2）。
- **漏 import 吞掉整条链**：`from PIL import ImageTk` 却用 `Image.LANCZOS` ⇒ 首帧 `NameError`，
  异常使 `root.after(...)` 永不执行 ⇒ 窗口空白、日志一条不出（同文 §6.1）。
- **用 `start` 拉窗口**：下一条命令连带杀死 ⇒ 必须脱离终端进程树。
- **把 stderr 块缓冲当"没有错误"**：加 `-u`，或用 `report_callback_exception` 捕获。
- **kill 过滤器命中自己**：`-match 'demo_script'` 会匹配到自身命令行 ⇒ 加 `-ne $PID` 或写 `demo_scr[i]pt`。
- **对带 alpha 的素材 `convert("RGB")`**：会丢透明背景（见 `docs\项目接手说明_AI_当前进度与待办.md` §9）。
- **谎报 docx 已生成**：渲染失败必须明说原因 + 给出用户可自行执行的命令。
- **把镜像当权威**：照抄 `E:\项目\共享文件夹\...` 在本机执行 ⇒ 路径不存在（本机无 E 盘）；反过来把镜像里
  跑出的结果当成 E: 侧已验证结论同样错。写命令先确认盘符（§8）。
- **镜像 `.venv` 与验证 venv 混用**：`.venv` 未装 dev 依赖 ⇒ `pytest` / `PySide6` 直接报缺模块；
  完整回归必须用装了 `requirements-dev.txt` 的解释器（如 E: 侧 `aura-validation-venv`）。
- **把"素材已就绪"当默认**：v3 的手势保持 / 进入 / 退出三类实际被缺失的保持参考阻塞；引用前先核实文件是否存在（§8 末条）。

## 11. 相关文档索引

- `docs\项目接手说明_AI_当前进度与待办.md`（接手入口）
- `docs\演示剧本_情绪调度与节奏_技术记录.md`（本轮剧本 + `--window` + §6.1 / §6.2 复盘）
- `docs\说话素材生成与验收工作流_v3.md`、`docs\说话素材自然度提示词包_v3.md`、`docs\说话素材自然度提示词_v3.json`（线②：素材生成，见 §7）
- `docs\说话播放层完善与素材交接_2026-10-05.md`（播放自然度第二步：连续源帧游标 / 平滑折返 / 相邻帧插值 / 509 项回归）
- `docs\镜像与盘符口径_2026-10-06.md`（本机镜像 / 盘符对照与本机能力实测，见 §8）
- `docs\NEW_WINDOW_PROMPT.md`、`docs\GPT_PROMPT_AVATAR_B2V.md`、
  `docs\玩偶素材Seedance提示词包_技术记录.md`（既有提示词类文档，体例参照）
- `.cline-handover.md`（跨会话交接）
