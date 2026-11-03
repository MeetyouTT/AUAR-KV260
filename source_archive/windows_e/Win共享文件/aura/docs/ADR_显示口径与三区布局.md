# ADR：显示口径与三区布局

> 状态：**已采纳（2026-09-11）** ｜ 决策人：用户 ｜ 记录：Cline
> 影响范围：`ui_spec/ui_layout_spec.json`(→1.1)、`ui_spec/ui_tokens.json`(→1.1)、
> `board/ui/qt_app.py`、`board/ui/qt_widgets.py`、`board/ui/avatar_lod.py`、
> `tools/prepare_avatar_frames.py`、`examples/run_ui.py`、
> `tests/test_ui_layout.py`、`tests/test_avatar_framing.py`

## 1. 背景

原 UI 为 **PC 口径 1280×720 · 55/45 分屏 + 顶栏 + 底部状态栏**（`ui_layout_spec.json` v1.0），
其中右列 45% 被「玩偶区(62%) + 对话区(38%)」竖向切分。板端确定为 **1024×600** 后，
用户重新定义了界面结构：**上（左=交互信息 / 右=玩偶动画）+ 下通栏（系统信息）**，
并要求玩偶**只显示腰部以上**、人物更大。

草案阶段用**真实素材**渲染了三区与 4 种玩偶变体（见 `docs/ui_draft/`、
`docs/UI三区布局草案渲染_技术记录.md`），据此做成本 ADR 的 4 项决策。

## 2. 决策（4 条，均已确认）

| # | 决策 | 关键数值 / 依据 |
|---|---|---|
| D1 | 玩偶区**满铺**（**不设**左右 8px 安全边） | 框内显示 **423×436**（占面板宽 100%、占上区高 84%、缩放 0.59×＝缩小采样）；安全边方案会降到 406×419（−4%）且不加清晰度 |
| D2 | 玩偶框保持 **423×516**，**上方 ~80px 空档留空**（不放松西、不缩框） | 空档作为**后续扩展位**（徽标/装饰/字幕未定），此轮不做内容 |
| D3 | 玩偶取景锁 **p=0.58**（`crop_bottom_ratio = 0.42`，保留上部 58%＝腰部以上） | 720×1280 → 裁后 **720×742**；不选 p=0.54（脸更大但留白更少，收益 ~7% 不值得再改） |
| D4 | **PC 1280×720 档废弃**，合同只保留板端单档 | 板端 1024×600 为唯一交付口径；顶栏（标题/模式/时间）随之删除，`mode`/`fps` 改由下栏呈现 |
| D5 | 玩偶框上方 **80px 扩展位**：内容待定，**先留空但接口先做好** | 合同 `right_inner.overlay_slot`（`reserved_height:80`, `content:"empty"`）+ Qt `overlay_slot_rect()` / `set_overlay_slot_painter()`；默认不绘制，板端 LVGL 预留同高区域 |

## 3. 三区合同（冻结值，`ui_layout_spec.json` 1.1）

| 区域 | 位置/尺寸 | 内容 |
|---|---|---|
| 上左·交互信息 | `(0,0) 585×556`，pad 8 | 摄像头 569×300 → 信息行 → 分隔线 → ASR/回复全文(80) → 延迟行(12) → 分隔线 → 事件流 4×14 |
| 上右·玩偶动画 | `(585,0) 439×556`，pad 8 | 状态标签 24 → 玩偶框 **423×516** → 底部渐隐收边 28 |
| 下栏·系统信息 | `(0,556) 1024×44` | 9 项：camera/npu/pl/audio/lan/save/privacy/mode/fps |

不变量：`585+439 = 1024`、`556+44 = 600`、左右/上下**无缝贴合**（单测逐项校验）。
字号档（`ui_tokens.json` 1.1）：title 16 / label 13 / small 11 / dialogue 14。

## 4. 后果

**正面**
- 人物显著变大且**不经过插值放大**：显示 423×436 来自 0.59× 缩小；
  宽度利用率从现状 290 px → **423 px（+46%）**。
- 一份合同同时驱动 PySide6 原型与板端 LVGL，三区数值可逐项核对
  （`docs/ui_consistency_checklist.md` V2.0）。
- 取景在**入库阶段**完成：只裁纵向、宽度与原点不变 → 缩放倍率不变，**原始 mp4 仍只读**。

**代价 / 连带项**
- 右下不再有对话区 → 对话全文移入左上区（`CameraPanel._paint_dialogue_area`），
  左上纵向预算需守住（单测 `test_left_inner_content_fits_in_panel`）。
- 入库**素材尺寸变了**（720×742 口径）→ 现役 `idle_normal`（180×320 全身）与新口径不一致，
  需按 `--framing waist-up --max-side 480` 重新入库（见 §5 第 3 条）。
- 下栏 9 项宽度 ≈ 850 px < 1024 px，暂无溢出风险；后续加项需复核。

## 5. 落地清单

1. 合同：`ui_spec/ui_layout_spec.json` 升 **1.1**（board 单档 + 三区 + `framing.crop_bottom_ratio:0.42`）、
   `ui_spec/ui_tokens.json` 升 **1.1**（板端字号档）。
2. Qt：`qt_app.MainWindow` 三区落位、删除 `TopBar`；`qt_widgets` 的
   `CameraPanel`（对话区移入）、`AvatarPanel`（去对话区 + 底部渐隐 + 帧序列**底部对齐**）、
   `StatusBar`（+fps 项）；`qt_style.ensure_cjk_font()` 解决离屏中文方框。
3. 素材：`avatar_lod.FRAMING_PRESETS{crop_bottom_ratio}` + `crop_box()` + `parse_framing()`；
   `prepare_avatar_frames.py --framing {full,waist-up} [--crop-bottom-ratio R]`，
   `meta.json.spec` 记录 `framing` / `crop_bottom_ratio`。
4. 单测：`tests/test_ui_layout.py`（11 项，合同自洽 + Qt 落位 + 底部对齐 + 1024×600 落盘）、
   `tests/test_avatar_framing.py`（12 项，比例/裁切/端到端入库）。
5. 证据：`evidence_shots/ui_board_{idle,present,listening,thinking,speaking,camera_lost,network_lost,error,cancelled}.png`（`--all-states` 一次出齐）、
   `ui_board_waist_up_preview.png`（腰部以上真实素材）。
6. 扩展位接口（D5）：合同 `overlay_slot` + `AvatarPanel.overlay_slot_rect()/set_overlay_slot_painter()`（默认留空，4 项单测）。
7. 排队期进度看板：`tools/prepare_avatar_frames.py --status`（2 项单测）；应对方案见 `docs/素材排队应对方案.md`。

## 6. 被否决 / 暂缓的选项（留档）

| 选项 | 否决理由 |
|---|---|
| 8px 左右安全边 | 只把人物缩小 4%，不改善清晰度；用户选满铺 |
| 玩偶框收到 464 并垂直居中（去掉空档） | 空档保留作后续扩展位（D2） |
| p=0.50 / p=0.54 更激进的裁切 | 0.54 仅比 0.58 大约 7%，0.50 会切到腰线以上风险高 |
| 保留 PC 1280×720 双 profile | 用户明确 PC 档不再需要，双档会增加两后端同步与核对成本 |
| 把安全边 / 裁切比例交给渲染端（运行时裁） | 运行端裁切会破坏「素材即产物」的可复现性，且板端多一份开销 |

## 7. 参考

- 草案与实测：`docs/UI三区布局草案渲染_技术记录.md`、`docs/ui_draft/{board_1024x600,variants}.png`
- 本轮落地记录：`docs/三区UI落地与取景裁切接入_技术记录.md`
- 定档/体积复核：`docs/板端显示定档与玩偶素材LOD复核_技术记录.md`
- 一致性核对表：`docs/ui_consistency_checklist.md`（V2.0）
