# 三区 UI 落地与取景裁切接入 —— 技术记录

> 触发：用户确认「上左右 + 下通栏」三区结构，并冻结 4 项显示口径
> （满铺 / 玩偶框留空 / p=0.58 / PC 档废弃，见 `docs/ADR_显示口径与三区布局.md`）。
> 本轮把草案从「图」落成**可跑的合同 + 代码 + 单测 + 证据图**。

---

## 一、背景与目标

上一轮只交付了**草案图**（`docs/ui_draft/`，非交付工具）。本轮目标：

1. 冻结合同：`ui_layout_spec.json` / `ui_tokens.json` 升 **1.1**（板端单档三区）；
2. 两后端同名实现：PySide6 原型改成三区（板端 LVGL 后续按同一份合同实现）；
3. 素材侧可复现地「只保留腰部以上」：入库工具加取景参数 + 元数据留痕；
4. 可验证：合同数值自洽单测 + Qt 落位单测 + 入库端到端单测 + 真实面板证据图。

---

## 二、做了什么

### 2.1 合同（`ui_spec/`）

| 文件 | 版本 | 变化 |
| --- | --- | --- |
| `ui_layout_spec.json` | 1.0 → **1.1** | 画布 1280×720 → **1024×600**；删 `top_bar`/`status_bar`（旧键名）、`right_inner.avatar_ratio/dialogue_ratio`；新增 `top_area`/`bottom_bar`/`left_inner`/`right_inner{label_h,avatar_box,fade_h}`/`framing`；`status_items` 8 → **9 项**（+fps） |
| `ui_tokens.json` | 1.0 → **1.1** | 字号改板端档：title 18→**16**、label 14→**13**、small 12→**11**、dialogue 16→**14**；颜色/动画不变 |

三区冻结值：`585+439 = 1024`、`556+44 = 600`；玩偶框 **423×516** 由
`439 − 2×8(pad) − 24(标签)` 精确推出（单测逐步校验）。

### 2.2 Qt 三区（`board/ui/`）

- `qt_app.MainWindow`：删除 `TopBar`，按 `left_panel/right_panel/bottom_bar` 三区落位；
  窗口固定 1024×600。`__init__` 调 `ensure_cjk_font()`。
- `qt_widgets.CameraPanel`（上左）：改为**纵向逐段排布**，全部数值取自 `left_inner`；
  新增 `_paint_separator()` / `_paint_dialogue_area()`；对话全文（ASR + 回复 + 延迟）**从右列移入**。
- `qt_widgets.AvatarPanel`（上右）：去 `_paint_dialogue`；`label_h` 取自合同；
  **新增底部 28px 渐隐收边**（`QLinearGradient` alpha 0→255 用 `panel_bg`）；
  帧序列 `_draw_sprite_frame` 由**垂直居中**改为**底部对齐**（腰部切线贴框底，被渐隐带化掉）。
- `qt_widgets.StatusBar`（下栏）：高度取 `bottom_bar.height`(44)；`_status()` 新增 `fps` 分支。
- `qt_style`：新增 `area()` 与 `ensure_cjk_font()`（幂等注册 msyh.ttc）。

### 2.3 素材取景（`avatar_lod` + 入库工具）

- `avatar_lod`（纯逻辑，无 Qt）：
  - `FRAMING_PRESETS = {"full": 0.0, "waist-up": 0.42}`（冻结比例）；
  - `parse_framing(name, ratio)`：显式比例优先，未知取景名**抛错不静默**；
  - `crop_box(w,h,ratio) -> (x,y,w,h)`：**只裁纵向**，`x=y=0`、宽度不变，`h=round(h×(1−r))`。
- `prepare_avatar_frames.py`：
  - 新参数 `--framing {full,waist-up}`、`--crop-bottom-ratio R`（覆盖预设）；
  - `plan_spec()` 先算裁切矩形，再用**裁后尺寸**规划目标尺寸/体积；
  - 写帧时先 `QImage.copy(crop)` 再 `scaled(...)`（**裁切在缩放之前**）；
  - `meta.json.spec` 记录 `framing` + `crop_bottom_ratio`（可追溯）。

---

## 三、关键细节与技术决策

1. **裁切必须发生在缩放之前，且只裁纵向。**
   若先缩放再裁，等于用更小的输入做放大；只裁纵向 ⇒ `x/y/w` 不变 ⇒ contain 倍率不变
   （仍 0.59× 缩小），"人物变大"来自**可视区变矮**而不是拉伸。
2. **底部对齐 + 渐隐收边，而不是居中。**
   素材已裁到腰部，若垂直居中，腰部切线会漂在框中央很突兀；底部对齐后切线落在框底，
   28px 渐隐把它与面板底色融掉（`panel_bg` alpha 0→255）。
3. **下栏 9 项的选择**：合同原有 8 项（camera/npu/pl/audio/lan/save/privacy/mode），
   加 **fps** 凑够 9 项（草案图观感）；草案图里的「信号 dBm / 延时 ms」需要 *新数据字段*
   （`UiState` 无 rssi/latency 来源，属板层事件），**本轮不加**，列入后续扩展位，避免假数据。
4. **离屏中文方框**（踩坑）：`QT_QPA_PLATFORM=offscreen` 下 Qt 不加载系统字体，
   三区截图里**所有中文变方框**。修法：`qt_style.ensure_cjk_font()` 注册
   `C:/Windows/Fonts/msyh.ttc`（缺则 simhei），并让 `MainWindow` 构造时调用；只注册一次。
5. **体积预估系数偏保守**（踩坑）：工具用 `PNG_BYTES_PER_PIXEL = 1.5` 估体积，
   实测本轮 466×480 只有 **1.02 B/px**（229 KB/帧，见 §四），于是 `--budget-mb 18` 会报"超预算"。
   处置：**不改默认系数**（它按小尺寸标定，改了对 320 档会失真），试点用 `--budget-mb 35` 显式传参，
   并在文档里给出实测值。
6. **dry-run 会被已有帧短路**（踩坑）：`prepare_one` 在"目标目录已有帧且无 `--force`"时直接 `[跳过]`，
   于是 `--dry-run` 打不出规格。想只看规格就把 `--out-root` 指到空目录（如 `%TEMP%\avatar_probe`）。

---

## 四、验证方式与结果

| 验证 | 命令 | 结果 |
| --- | --- | --- |
| 全库回归 | `python -m pytest tests/ -q` | **186 passed**（163 → 186，新增 23） |
| 合同/Qt 落位 | `pytest tests/test_ui_layout.py -q` | 11 项通过（三区无缝拼满、玩偶框 423×516、底部对齐、1024×600 落盘） |
| 取景/入库 | `pytest tests/test_avatar_framing.py -q` | 12 项通过（含真实写出 PNG + meta 留痕 + 上半身保留/下半部裁掉像素级判定） |
| 规格实算 | `prepare_avatar_frames.py --framing waist-up --max-side 480 --dry-run` | 720×1280 → **720×742** → 入库 **466×480 @9.98fps/100 帧**（宽度不变） |
| 体积实测 | 真实抠像帧试点入库（`%TEMP%\avatar_probe`） | **229 KB/帧**（466×480 PNG）→ **22.4 MiB/状态**（100 帧）；RGB565 = 466×480×2B = **447 KB/帧 ≈ 43.7 MiB/状态** |
| 真实面板证据 | `run_ui.py --state PRESENT --screenshot ...` | `evidence_shots/ui_board_present.png`、`ui_board_speaking.png`（1024×600，中文正常） |
| 腰部以上观感 | `preview_avatar_frames.py --frames-root %TEMP%\avatar_probe` | `evidence_shots/ui_board_waist_up_preview.png`（423×436 满铺、底部渐隐，人物明显更大） |

对比（同一玩偶框 423×516）：

| 口径 | 素材 | 框内显示 | 占宽 | 缩放 |
| --- | --- | --- | --- | --- |
| 现状（`full`，180×320 档） | 180×320 | 290×516 | 69% | ×1.61（放大，糊） |
| **本轮（`waist-up`，480 档）** | 466×480 | **423×436** | **100%** | **×0.91（缩小，清晰）** |

---

## 五、涉及文件清单

**新增**
- `docs/ADR_显示口径与三区布局.md`（+docx）
- `docs/三区UI落地与取景裁切接入_技术记录.md`（本文，+docx）
- `tests/test_ui_layout.py`（11 项）、`tests/test_avatar_framing.py`（12 项）
- `evidence_shots/ui_board_present.png`、`ui_board_speaking.png`、`ui_board_waist_up_preview.png`

**修改**
- `ui_spec/ui_layout_spec.json`、`ui_spec/ui_tokens.json`（→1.1）
- `board/ui/qt_app.py`、`board/ui/qt_widgets.py`、`board/ui/qt_style.py`
- `board/ui/avatar_lod.py`（+`FRAMING_PRESETS`/`parse_framing`/`crop_box`）
- `tools/prepare_avatar_frames.py`（+`--framing`/`--crop-bottom-ratio`）
- `tools/ui_mock_draft.py`、`tests/test_ui_mock_draft.py`（去掉 PC 档）
- `examples/run_ui.py`（文案/口径）
- `docs/ui_consistency_checklist.md`（V2.0）、`README.md`、`docs/NEW_WINDOW_PROMPT.md`

**删除**
- `docs/ui_draft/pc_1280x720.png`（PC 档废弃）

---

## 六、下一步

1. **7 态素材**：用户在 Seedance 产出 mp4（提示词不变）→ 入库统一用
   `--framing waist-up --max-side 480 --budget-mb 35`（板端再加 `--formats png,rgb565 --rgb565-bg 16202B`）；
2. 现役 `idle_normal` 是否按新口径重新入库（`--force`，mp4 只读）——**已定：等 7 态齐了一次性重跑**（用户 2026-09-11 确认按建议执行）；
3. 板端 LVGL 实现按 `ui_consistency_checklist.md` V2.0 逐项核对并留证据；
4. 玩偶框上方空档的**扩展位用途**（D2 未定）后续单独设计；
5. 若需下栏「信号强度 / 端到端延时」真实数据，需先补 `UiState` 字段与板层事件源。

---

## 七、9 态证据图基线（补充，同日）

代码与合同定稿后，补上「9 态证据图」的**批量产出能力**，并修掉一个证据图尺寸隐患：

- **新增** `examples/run_ui.py --all-states [--out-dir evidence_shots]`：状态清单直接取自
  `board/ui/avatar_fsm.all_states()`（9 态唯一权威来源，避免手抄漏态），逐态设
  `runtime_state` 后离屏落盘 `ui_board_<state>.png`；SPEAKING 额外塞一句回复，
  便于目检左上对话区排布。
- **修复（真踩坑）**：`--all-states` 原先未走 offscreen → 按真实屏幕 DPR 抓图，
  在 **200% 缩放的屏**上得到 **2048×1200**（合同是 1024×600，证据图尺寸必须一致）。
  处置两层保险：
  1. `--all-states` 与 `--screenshot` 一样 `setdefault("QT_QPA_PLATFORM", "offscreen")`；
  2. `MainWindow.render_to_file()` 把 `grab()` 得到的 pixmap **归一化到窗口逻辑尺寸**
     （不等则等比缩放回 1024×600）。
- 单测 `tests/test_ui_layout.py::test_render_to_file_writes_1024x600` 已覆盖"落盘即 1024×600"。

产物（全部 **1024×600**，环境标签 PC / SIMULATED）：

| 范围 | 文件 |
| --- | --- |
| IDLE / PRESENT / LISTENING / THINKING / SPEAKING | `evidence_shots/ui_board_{idle,present,listening,thinking,speaking}.png` |
| CAMERA_LOST / NETWORK_LOST / ERROR / CANCELLED | `evidence_shots/ui_board_{camera_lost,network_lost,error,cancelled}.png` |
| 玩偶腰部以上预览（waist-up 素材） | `evidence_shots/ui_board_waist_up_preview.png` |

复现：

```powershell
cd "D:\share\项目开发\FPGA语音助手开发\wujing-lite"
python examples/run_ui.py --all-states     # 9 态证据图一次出齐
python -m pytest tests/ -q                 # 全库回归
```

> 说明：图内 `fps` 为证据机渲染节奏（非板端实测），板端 LVGL 阶段的 fps 证据另行采集。

---

## 八、玩偶框上方「扩展位」接口预留（D2）

用户确认：**空档要放东西，但具体内容待定 → 先留空、接口先做好**。落地如下：

| 层 | 内容 |
| --- | --- |
| 合同 | `ui_layout_spec.json → right_inner.overlay_slot = {enabled:true, align:"top", reserved_height:80, content:"empty"}` |
| Qt | `AvatarPanel.overlay_slot_rect()` 按合同算出矩形（面板内 **(8, 32, 423, 80)** = pad 8 + 标签 24 → 框顶 80px）；`set_overlay_slot_painter(fn)` 接入内容，签名 `fn(p, rect, st, snap)`；默认 `_paint_overlay_slot()` 空实现 |
| 绘制顺序 | 玩偶素材 → **扩展位** → 底部渐隐（扩展位叠在素材之上，不会被渐隐吃掉） |
| 板端 LVGL 义务 | 用同一算式推导矩形并预留同高区域（见 `ui_consistency_checklist.md` V2.0 的 L14） |

**重要前提（实测发现）**：空档**只在「腰部以上」素材下存在**。
现役 `idle_normal` 是 full 取景（180×320，contain 后 290×**516**，顶满框高）→ 顶部 80px 被素材占用；
换成 waist-up（466×480 → 423×**436**）后才有 80px 真空档。
因此：**扩展位内容要能容忍被素材部分覆盖**（当前实现叠在最上层），或待素材口径统一后再定版式。

单测：`tests/test_ui_layout.py` 4 项 —— 合同+矩形、默认留空（像素级）、接入钩子生效、`enabled/height=0` 时不绘制。

---

## 九、排队期进度看板（`tools/prepare_avatar_frames.py --status`）

素材逐条到达时，需要一眼看出「缺哪几态 / 取景对不对」。新增 `--status`：

- 逐行列出 9 态对应素材（`avatar_assets.STATE_ASSET` 去重后 8 个目录）的
  **帧数 / 尺寸 / 取景 / 体积 / 清单状态**；
- 取景 ≠ `waist-up` 时显式标注（避免"帧齐了但要重跑"）；
- 末尾给「小计 n/m」与「待产出状态」。

实跑输出（2026-09-11，真实工程）：

```
素材入库状态（根目录: ...\wujing-lite\assets\avatar）
  素材名                  帧数     尺寸          取景        体积         状态
  idle_normal          100    180x320     full      8.4 MiB    [OK] 已入库／取景=full ≠ 板端 waist-up
  emo_puzzled          -      -           -         -          [缺失] 待产出
  ...（共 7 个素材目录缺失）
  小计：1/8 个素材目录已入库
  待产出状态：CAMERA_LOST, ERROR, LISTENING, NETWORK_LOST, PRESENT, SPEAKING, THINKING
```

单测：`tests/test_avatar_framing.py` 2 项（进度行内容、取景不符提醒）。
排队期完整应对方案（换渠道 / 本地生成 / 派生占位序列 / 矢量兜底 + 增量入库 SOP）见
`docs/素材排队应对方案.md`。
