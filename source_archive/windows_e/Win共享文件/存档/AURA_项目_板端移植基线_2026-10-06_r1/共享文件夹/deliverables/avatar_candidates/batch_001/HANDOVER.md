# HANDOVER —— 交给下一个 AI 的工作交接（AURA 说话素材 v3 / batch_001）

> **接收端复核更新（当前客户端日期 2026-10-05）**：已在 `E:\项目\共享文件夹` 复核全部12条源文件及数值，并完成全部12条首/峰/末的全身、脸与双手目测。**12条均因中段手位或躯干姿态变化被退回，不可接入正式素材**。当前完整测试重新运行509项通过。最新依据为 [`review_20261005/验收结论与下一步.md`](review_20261005/验收结论与下一步.md) 和同目录 `visual_review.json`；图像证据与逐帧脸部接触表已归档。原文“rest_s421001基线通过”“blink_s421002无眨眼”已被可见帧证据纠正。下方原交接及同名DOCX保留为历史版本，本段和新增报告尚未同步到旧DOCX。

> **生成机侧回应（2026-10-06 14:3x，本机生成机会话）**：参考图名歧义已消除、生成机可用约束已**实测落盘**，见 `review_20261005\生成机可用约束调研_2026-10-06.md`（+docx）与下方 §11。**本批 12 条仍按接收端结论退回，不接入。**

> 写于 2026-10-06 08:1x（本机会话）｜写作者：Cline
> **请先读本文件，再读同目录 `MANIFEST.md`（素材清单/校验）与 `aura\docs\本机镜像同步与v3素材生成_2026-10-06.md`（技术记录）。**
> 一切路径均在 `D:\share、\项目开发\FPGA-amd自主命题赛道\`（本机镜像）。

## 0. 一句话现状

`batch_001` 的 **12 条说话素材（4 类 × 3 种子）已全部生成并结构/数值双通过**，素材本体已在项目目录内；
**下一步不是"生成"，而是"验收（全脸目测）+ 抠像 + 归档"**；另有一个**必须由用户拍板的语义口径问题**（`rest` 是否允许自然眨眼）。

### 开工前三条只读校验（期望输出已给，任何一条不符先报告、不要往下改）

```powershell
$py = 'D:\share、\项目开发\FPGA-amd自主命题赛道\aura\.venv\Scripts\python.exe'
$b  = 'D:\share、\项目开发\FPGA-amd自主命题赛道\deliverables\avatar_candidates\batch_001'
# 1) 素材本体在不在：应输出 480 / 708.3
$g = Get-ChildItem -LiteralPath "$b\raw" -File -Recurse; "$($g.Count) / $([math]::Round((($g|Measure-Object Length -Sum).Sum/1MB),1))"
# 2) 数值复算；API与原帧指纹另外核验，数值通过不代表视觉通过
& $py -B "$b\tools\v3_qc.py" --batch-root $b --report "$b\qc\qc_rerun.json"
# 3) 眨眼复算：应与 reports\blink_report_20261006_0758.txt 的 12 行 dip 值一致
& $py -B "$b\tools\blink_probe_v2_iris.py" --batch-root $b
```

## 1. 背景（30 秒版）

- 目标：AURA 玩偶（FPGA 自主命题赛道）的**说话播放层**需要一批"看起来活着"的说话帧序列素材。
- 本批 v3 用 **ComfyUI API 工作流**（以静息参考动作图为锚）生成，**4 类**：
  `talking_calm_rest_v3`（静息说话）、`talking_calm_blink_v3`（带眨眼提示的说话）、
  `talking_low_rest_v3`（低落）、`talking_warm_rest_v3`（温暖）；每类 **3 个种子**（421001/2/3）。
- 规格：**39 帧 / 条**、864×1536、播放口径 24 fps；提示词与构建器见 §9。
- 已遵守的边界：**只写候选交付目录 `deliverables\avatar_candidates\`，未碰 `aura\assets`、未加 `--force`、未改任何设计文档 API。**

## 2. 产物索引（都在项目内，不再依赖 `%TEMP%`）

| 路径 | 内容 |
|---|---|
| `batch_001\raw\<id>_s<seed>\` | **素材本体**：39 帧 PNG + `meta.json`（含 prompt_id / api sha256 / 首末帧 sha256） |
| `batch_001\workflows\` | 12 份 `*_api.json` + `workflow_manifest.json`（可复现） |
| `batch_001\qc\qc_20261006_075517.json` | **正式数值体检留档**（含 `eye_band_*`、`lr/ef/ec` 等指标） |
| `batch_001\reports\` | `qc_report_20261006_0755.txt`（结构+数值）、`blink_report_20261006_0758.txt`（眨眼判定表）、运行日志 |
| `batch_001\tools\` | 本批全部脚本：`v3_batch_submit.py`、`v3_run.ps1`、`v3_next_pipeline.ps1`、`v3_qc.py`、`blink_probe_v1_pixel_diff.py`（**失败尝试，留作反例**）、`blink_probe_v2_iris.py`、`eye_contact_sheet.py` |
| `batch_001\evidence\` | 眼区逐帧接触表 PNG（`blink_rest_s421001`、`all12`）——**看图最快路径** |
| `batch_001\logs\`、`run_manifest.json` | 提交日志与清单（id/seed/prompt_id/status） |

## 3. 已确立的口径与判据（**改判据＝改设计，须先经用户确认**）

| 项 | 值 / 判据 | 依据 |
|---|---|---|
| 帧数 / 尺寸 | 39 帧、864×1536 | 本批全一致 |
| 眼区定位框 | `x∈[0.41,0.59]`、`y∈[0.125,0.175]`（全画幅比例） | 2026-10-06 目测 `blink/rest_s421001` 的 f16 帧标定 |
| 闭眼判据 | 眼区**蓝瞳占比**曲线 `dip=(med−min)/med`：`≥15%` 强 / `8–15%` 弱 / `<8%` 无；另看 `closed_frames`（`<0.72×med`） | `blink_probe_v2_iris.py` |
| ⚠ 探针 `BLINK/WEAK` 标签**不可当硬判据** | 例：`rest_s421001 dip=23.9%` 却被标 WEAK（因 `med−min=0.118 < 3×sd=0.121`）⇒ **看 dip 数值 + 接触表目测** | 已核 |
| 运动分布阈值 | `tail ≤ 0.5`、`low ≤ 0.55`（以目测通过的 `rest_s421001` 标定） | `v3_qc.py` |
| `STRUCTURE_VALID_REQUIRES_VISUAL_REVIEW` | **仅代表结构 + 运动分布合格，不等于视觉通过**；必须再做全脸目测 | 规则/记录 |
| 失败处理 | 换种子或改动作句后**重跑**；**不许用裁剪切掩盖**（脸不一致/多指/缩放都是硬失败） | 项目纪律 |
| 素材只读 | `raw\` 不改动；重跑生成新 `prompt_id`，旧结果保留以备比较 | 本轮做法 |

## 4. 已完成结论（可直接引用）

1. **结构**：`api_graphs=12 raw_OK=12 raw_BAD=0`，每条 `png=39 / meta.frame_count=39 / state=ok`。
2. **数值**：`count=12 status=STRUCTURE_VALID_REQUIRES_VISUAL_REVIEW`，**`FAIL_IDS=- / FLAGGED_IDS=-`**；
   `peak 15.03–19.77`（峰帧 f12–f19）、`last 1.57–2.07`、`tail 0.093–0.121`、`low 0.20–0.25`，与基线同量级、无离群。
3. **眨眼（专项）**：**四类都出现闭眼事件；`blink` 与 `rest` 在"是否眨眼"上无系统差异**（差异只在动作句）。
   - 目测已确认：`blink_s421001` **f14–f18 闭眼**、`rest_s421001` **f7–f8 闭眼**（见 `evidence\` 接触表）。
   - 多条 `s421003` 的 `dip@f0` 是**头部/发型缓慢漂移**（f0..f3 单调变化，如 0.486→0.492→0.499→0.506），**不是眨眼**。

## 5. 待办任务（按优先级；每条给命令 + 验收判据）

### T1（最高优先，纯只读）其余 9 条全脸目测
- 抽帧：每条看 **首帧 `000000.png`、`peak` 帧、末帧 `000038.png`**；峰帧号：blink 13/16/17、rest 13/14/13、low 19/15/14、warm 13/13/12。
- 看什么（5 项硬判据）：**脸与参考一致 / 无缩放或镜头位移 / 双手保持（不融手）/ 无多指 / 无严重崩坏**。
- 现状：仅 `rest_s421001`（基线 3 帧）与两条眼区专项已目测，**其余 9 条未看**。
- 验收：输出一张表（id → PASS/FAIL + 理由）；失败 → 换种子或改动作句重跑。

### T2（需用户拍板，先问再做）`rest` 是否必须"全程不闭眼"
- 现状：`rest_s421001` 23.9%@f8、`low_rest_s421001` 31.5%@f12–13、`warm_rest_s421001` 32.2%@f12–14 都含一次自然眨眼。
- 若必须"全程不闭眼"：属**设计变更** → 改 `aura\docs\说话素材自然度提示词_v3.json`（`common_prompt` / `assets[].prompt`）
  → `aura\tools\build_naturalness_workflows.py` 重建 → `$b\tools\v3_batch_submit.py submit --only <该类>` 重跑 → 重新体检 + 目测。
- **未获用户确认前：不改提示词、不重跑。**
- 🆕 **D1 证据已齐（2026-10-06；E2 已跑完，见 §11-7）**：E1（124 帧）`dip 20.6%@f84`，在 **f44–47 与 f82–86** 各闭眼一次；
  **E2（E1 + 中间帧锚定 `frame_idx=62`）只剩 f44–47**，f82–86 已恢复睁眼
  （数值 `batch_003_guide_probe\review\blink_report_e1_vs_e2.txt`；看图 `review\sheet_b_eye_band.png`；
  留档 `review\看图记录_E2抽帧与眼区_2026-10-06.md`）。
  ⇒ 请**下一个 AI / 用户直接拍板**：**A** 允许自然眨眼（把“含一次前段闭眼”写进验收说明，**不重跑**）或
  **B** 必须零闭眼（按上面流程改 `说话素材自然度提示词_v3.json` 后重跑该类，属**设计变更**）。
  **未决前的安全默认：按 A 继续。**
- 🆕 **D2 下一步实验方向（E2 已划出边界，别重复无效路线）**：E2 峰值帧 **f17/f19（手）、f26（胸/含手横带）全部早于锚点 f62**
  ⇒ **“加长 `length`”与“只锚中间一帧”都不是漂移的解法**；**建议 E4：锚点前移/加密**（`frame_idx=20` 或双锚 `f20+f90`，仍单变量），
  验收＝`batch_002_probe\tools\drift_metrics_v2.py --spec <UTF-8 JSON>` 同表 + **1 次拼图看图**。
  **E3（区域掩码）前置未满足**：`MiniMaxH3FunControlNetApply` 的 `model_patch` 权重**本机未确认存在**，须先核查再排队。
- 📍 完整证据链与选项对比另见**项目级交接** `D:\share、\项目开发\FPGA-amd自主命题赛道\.cline-handover.md`
  **§1（E/F 项）与 §3（0b/0c/0d 条）**。

### T3 抠像（输出到**候选目录**，严禁写 `aura\assets`）
```powershell
& $py -B aura\scripts\prepare_avatar_frames.py --src "<batch_001\raw\某条>" --name <同名> `
  --matte-src --mode adaptive --post-despill ad1 --matting-project '<用户提供的实际抠像工程路径>' `
  --framing waist-up --max-side 480 --fps 24 --src-fps 24 --formats png --budget-mb 12.5 `
  --out-root "deliverables\avatar_candidates\batch_001\prepared" --temp-dir "<...\batch_001\temp" --keep-temp
```
- 参数以 `--help` 为准；**先跑 1 条**，人眼确认 alpha 边缘/发型/手指后再批量。
- 验收：`prepared\<同名>\` 生成、39 帧、每套PNG总量 ≤ `budget-mb`、无绿边。

### T4 体检 + 四对首尾接缝目测
- `aura\tools\check_naturalness_candidate.py`（先 `--help`）对 `prepared\` 逐条体检。
- 接缝四对叠加：**静息末帧→进入首帧 / 进入末帧→保持首帧 / 保持末帧→退出首帧 / 退出末帧→静息首帧**。

### T5 `hold / enter / exit` 三类（被参考图阻塞）
- 阻塞点：ComfyUI `input\` 缺 **`doll_green_9x16_hold.png`**。补齐后：
```powershell
& $py -B "$b\tools\v3_batch_submit.py" build  --only talking_calm_hold_v3 talking_calm_enter_v3 talking_calm_exit_v3
& $py -B "$b\tools\v3_batch_submit.py" submit --only talking_calm_hold_v3 talking_calm_enter_v3 talking_calm_exit_v3
```
（脚本可重入、自动跳过已完成项；参考名已内置。**长任务必须脱离终端启动**，见 §6。）

### T6 git 提交（本机当前无 git 环境）
- 由带仓库的环境/用户执行；内容＝`batch_001\`（raw/ workflows/ qc/ reports/ tools/ evidence/ MANIFEST.md HANDOVER.md）+ `aura\docs\` 新记录。

## 6. 本机环境事实与操作纪律（踩过的坑，照做可省 1 小时）

- **无系统 Python**：`python` 是 Microsoft Store 别名，调用即失败；本批一律用
  `D:\share、\项目开发\FPGA-amd自主命题赛道\aura\.venv\Scripts\python.exe`（**实测可用**，含 numpy/PIL）。
  ⚠ 与旧记录"本机无 `.venv`"矛盾 → **以实测为准**；若该路径失效，先探测再报告，不要盲试。
- **无 pandoc**；md→docx 走 Word COM：
  `powershell -NoProfile -ExecutionPolicy Bypass -File "D:\share、\项目开发\b站评论成分分析工具\cline全局规则配置\scripts\render_docx.ps1" -Md "<绝对路径.md>"`
  （约 1 min/份；**渲染期间不跑其它前台命令**，用输出文件时间戳判完成；异常退出留 `WINWORD` 僵尸 → `Get-Process WINWORD | Stop-Process -Force`）。
- **长任务（>20 s）必须脱离终端**：`Invoke-CimMethod Win32_Process.Create` + 重定向到文件，之后**只用 `read_files` 轮询**；
  否则"下一条前台命令"会把上一个进程掐死（本轮实测两次）。
- 路径含中文与顿号：命令中一律加引号；**脚本源码必须纯 ASCII**（PS 5.1 按 ANSI 读无 BOM 的 UTF-8）。
- **`.ps1` 直接用 `&` 调用会被执行策略拦下**（`PSSecurityException` / "在此系统上禁止运行脚本"）→ 必须走
  `powershell -NoProfile -ExecutionPolicy Bypass -File <script> -Arg ...`；`batch_001\tools\v3_*.ps1` 同理。
- **PS 变量名不区分大小写**：`param([string]$Out)` 之后若再写 `$out = @()`，会把参数**覆盖成数组**，
  报错表现为"路径中具有非法字符" → 参数名与局部变量名不要撞（本轮实测，改名 `$OutFile` 即好）。
- **`foreach($x in @($a+'\\b.md', $c))` 在单行 `-Command` 里会被压平成单串**（实测两次）→ 改用
  `$v1=...; $v2=...; foreach($x in $v1,$v2)`。
- 用 `-File` 调脚本时，**含中文但不含空格的路径可以不加引号**（本轮 WMI 脱离启动即靠此避开嵌套引号地狱）。
- `read_files` 偶发 `ENOENT`（文件正在写）→ **重读即可**，别判失败。
- 终端捕获不可靠：命令结果**写文件再读**（本会话 `run_commands` 一律显示"无法观察完成"，但文件都写成了）。

## 7. 禁做清单

1. 不要写 `aura\assets\`（本批只允许写 `deliverables\avatar_candidates\`）。
2. 不要加 `--force`、不要覆盖已生成素材、不要删 `raw\`。
3. 不要改 `aura\docs\说话素材自然度提示词_v3.json` 与设计文档 API/口径（须用户确认）。
4. 不要用裁剪/缩放"掩盖"脸不一致、多指、崩坏等硬失败。
5. 不要把 `STRUCTURE_VALID_REQUIRES_VISUAL_REVIEW` 当成"视觉通过"。
6. 不要盲信 `blink_probe_v2_iris.py` 的 `BLINK/WEAK` 标签（看 dip 数值 + 接触表目测）。

## 8. 未解项 / 风险

1. **语义口径未定（T2）**：影响 6 条 `*_rest` 素材的验收结论。
2. 探针 `WEAK` 降级规则偏保守，标签与数值可能不一致（§3 注）。
3. `.venv` 存在性与旧记录矛盾（§6），换机器需重新探测。
4. 抠像工程路径 `--matting-project` 需用户提供，未确认前无法施工。
5. 盘符/镜像口径见 `aura\docs\镜像与盘符口径_2026-10-06.md`（旧命令里的 `E:` 在本机不存在）。

## 9. 相关文档（均在 `aura\docs\`）

| 文件 | 用途 |
|---|---|
| `本机镜像同步与v3素材生成_2026-10-06.md`（+docx） | **本轮技术记录**：A 镜像口径、B 本批全过程（§4.5 批次结果 / §4.6 眨眼专项 / §4.7 待办） |
| `说话素材自然度提示词_v3.json` | **提示词唯一来源**（`common_prompt` + 每条 `prompt`），构建器读它 |
| `说话素材生成与验收工作流_v3.md` | v3 工作流与判据 |
| `说话素材自然度提示词包_v3.md` | 提示词包说明（人读版） |
| `AI生成提示词与工作流.md`（+docx） | 提示词三层结构与跨项目工作流模板 |
| `镜像与盘符口径_2026-10-06.md` | 本机盘符/路径口径 |

## 10. 交接元信息

- 本批次**未接入任何运行时**（`aura\assets` 与播放层都没动）⇒ 后续操作**不会破坏现有演示**。
- 建议下一窗口开场白：
  `@deliverables\avatar_candidates\batch_001\HANDOVER.md @deliverables\avatar_candidates\batch_001\MANIFEST.md → 先跑开工前三条只读校验，再按 T1→T4 推进，T2 先问用户`
- 本文件与 `MANIFEST.md` 已同步渲染同名 `.docx`。

## 11. 生成机侧回应（2026-10-06 14:3x 补写；只增事实，不改接收端结论）

**结论一句话**：参考图歧义已消除；**本机确实具备局部锚定能力**（本批 API 图未使用）；且发现本批 `length=39` **远低于模型训练范围（~124–362）**——这是当前最有价值的待验证假设。

1. **参考图歧义（已闭环）**：12/12 份 API 图 `LoadImage.image` 均为 `doll_green_9x16.png`；
   ComfyUI `input\` 内 `doll_green*` **仅 1 个**（`1,061,336 B`，`2026-10-04 15:19`，
   SHA256 `FBE9EFA3BE94A2C1359C93C50A28273788789323D886364EB1EB3C06119E8780`）；
   `aura\`、`deliverables\`、ComfyUI `output\` 搜 `doll_green*` **均 0 命中**。
   ⇒ `MANIFEST` 的 `_rest.png` 是误记；`_hold.png` **确实不存在**（T5 属文件级缺失，非路径笔误）。
2. **生成机环境**：ComfyUI **0.38.0** / Python 3.14.7 / RTX **5060 Ti 15.9GB** / 服务 `127.0.0.1:8188` 在线 / 节点 **3602**。
3. **本批只用了 13 类节点**（纯 MiniMax H3 管线）＋**首末帧同图**，无 mask、无逐帧锚点、无参考保持
   ⇒ 与接收端“只使用首尾图条件”的判断一致。
4. **可用局部约束（实测存在，未使用）**：`MiniMaxH3AddGuide`（**任意帧锚定**，可串联多帧；17k+5 网格）、
   `MiniMaxH3FunControlNetApply`（**带 mask** 的局部驱动，但**缺 model_patch 权重**）、
   `MiniMaxH3ReferenceToVideo`（参考图/视频身份保持）。
5. **`length` 训练范围**：官方 tooltip “`124 = ~5s; trained range is ~124-362`”，网格 `17k+5`（39 合法但**远低于下限**）。
6. **不可行（缺权重，需下载）**：Fun ControlNet / Wan / LTX / Hunyuan / AnimateDiff（缺 SD 底模）。
7. **下一步**：见 `review_20261005\生成机可用约束调研_2026-10-06.md` §5 实验矩阵 **E1–E6**（单变量）。
   **E1 已完成（2026-10-06 14:53:12）**：`length` 39→124，仅此一处差异（逐字比对 `all_diff_paths` 只有 `/7/inputs/length`），
   脚本 `batch_001\tools\probe_v3_length124.py`（`--dry-run` 只出图不提交），产物在**新目录** `batch_002_probe\`
   （`workflows\`、`raw\e1_rest_s421001_L124\`、`logs\probe_*.log`、`review\`、`tools\drift_metrics.py`、`README.md`）。
   **结果**：124/124 帧、`success`、**1020.9 s（≈17 min）**、显存峰值 **15.6/16.3 GB 未 OOM**；
   数值漂移（**v2 更正版** `batch_002_probe\review\drift_report_v2.txt`，864×1536 原图像素）：
   下部外缘（原误称“左右手”）20/18→16/10 px（0.80/0.56）、腰下 74→38 px（0.51）、腿 6→2 px（0.33）、
   外接框横向中点 5→4 px（0.80）；**但手与躯干区域不改善甚至更差**——手/前臂 ROI 位移
   （x300–555,y540–770 肤色中心，与接收端同法）**10.26→10.57 px（1.03）**、含手横带 78→112 px（1.44）、
   胸部 46→64 px（1.39），峰值集中在前 1/3（frame 16–40）⇒ **`length` 只证明“跑得通”，不是漂移的解法**。
   ⚠ **本条早前引用的“手位带 0.67 / 腹部 1.23”已作废**：v1 `drift_metrics.py` 的 `hand_l/hand_r` 取相对高度
   0.58–0.78，实测落在 **y=892–1188 的长发/腿区**（手在 y≈650–740），`w@0.45` 只是含手/围裙/长发的横带跨度，
   `cx` 是外接框中点（详见 `batch_002_probe\README.md` §3.1 作废声明与接收端 `review_20261006\接收端验收结论.md` §3）。
   **E2 已按接收端 §4 跟进并跑完（2026-10-06 15:35:40 提交 / 15:59:36 完成）**：在 E1 之上**只加一处**中间帧锚定
   `MiniMaxH3AddGuide(frame_idx=62)`（`/object_info` 实测存在、**无额外权重依赖**），干跑自证 `diff paths=2`;
   产物目录 `batch_003_guide_probe\`（脚本 `tools\probe_v3_guide_mid.py`，完整证据见该目录 `README.md` §6）。
   **结果**：124/124 帧、`state=ok`、**1435.4 s（比 E1 的 1020.9 s 慢 40.6%）**。
   隔离单变量的对照（`batch_003_guide_probe\review\drift_report_e2_vs_e1.txt`，原图 864×1536 像素）：
   外接框中点 4→1（0.25）、胸 64→36（0.56）、含手横带 112→86（0.77）、腰下 38→30（0.79）、腿 2→1（0.50）、
   下部外缘 16/10→4/4（0.25/0.40）；**但手/前臂 ROI 9.08→11.01（1.21）反向变差**。
   ⇒ 锚点**只约束它之后的区间**：E2 峰值帧仍为 **f17/f19（手）、f26（胸/横带）**，全部早于 f62
   ⇒ **单锚中间帧 + 加长 `length` 都不是终局解法**，下一步应把锚点**前移/加密**（如 f≈20 与 f≈90 各一）。
   **眨眼（同判据变长探针）**：E1 dip 20.6%@f84（BLINK）、E2 dip 14.0%@f46（WEAK）；
   看图（眼区 2× 接触表）确认 E1 在 f44–47 与 f82–86 各有一次闭眼，**E2 只剩前段 f44–47**、f82–86 已恢复睁眼
   ⇒ 锚点顺带消掉后半段眨眼，但**前段闭眼仍在**（T2 仍待用户拍板）。
   看图已做（本批 2 次，`review\sheet_a_endpoints.png` + `sheet_b_eye_band.png`，留档见
   `review\看图记录_E2抽帧与眼区_2026-10-06.md`）：三组全身同角色同姿势、无肢体崩坏。

8. **边界**：本轮**未生成任何新素材**、未改提示词 JSON、未碰 `aura\assets`、未改 `batch_001\raw\`。

