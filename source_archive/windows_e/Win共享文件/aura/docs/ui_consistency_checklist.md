# UI 一致性核对表（PySide6 原型 ↔ 板端 LVGL）

> 版本：V2.1 ｜ 2026-09-12 ｜ 环境标签：PC / SIMULATED
> **V2.1 变更（情绪分档扩展）**：运行时状态 **9 态 → 10 态** —— 播报拆成
> `SPEAKING`（情绪**高涨** / `talking_normal`）与 **`SPEAKING_LOW`**（情绪**低落** / `talking_low`），
> 由对话回复的 `emotion` 命中 `board/runtime/fsm.LOW_EMOTIONS` 驱动；
> **本表 §一（布局数值）与 §二/§三（颜色/字号令牌）未变**，仅新增一个状态的玩偶表现与素材。
> **情绪节点口径（2026-09-12 拆分）**：这 10 态分两组 —— **① 表达性节点 6 个**
> （待机 / 探头·注视 / 倾听 / 思考 / 说话·高涨 / 说话·低落）；**② 系统·故障态 4 个**
> （CAMERA_LOST / NETWORK_LOST / CANCELLED / ERROR，由系统事件驱动、允许复用或降级）。
> 该分组**仅是文档口径**：`RuntimeState` 成员、`ui_state.schema.json` 枚举、`STATE_ASSET` / `AVATAR_MAP`
> 映射与单测**全部未改动**（仍 10 态）；依据见 `docs/玩偶素材Seedance提示词包_技术记录.md` §12。
> **V2.0 变更（板端三区落地）**：合同升 **1.1** —— 画布改 **1024×600**，结构改为
> **上左（交互信息 585×556）+ 上右（玩偶动画 439×556）+ 下栏（系统信息 1024×44）**，
> 删除顶栏与 `avatar_ratio / dialogue_ratio`；玩偶**只显示腰部以上**
> （`framing.crop_bottom_ratio = 0.42`，入库用 `--framing waist-up`）；
> 对话全文移入上左区。**PC 1280×720 档已废弃**。
> 决策留档：`docs/ADR_显示口径与三区布局.md`；落地记录：`docs/三区UI落地与取景裁切接入_技术记录.md`。
> 目的：保证无板阶段 PySide6 原型与板端 LVGL 版的**布局/配色/逻辑/数据**逐项一致。
> 唯一权威数值：`ui_spec/ui_layout_spec.json`、`ui_spec/ui_tokens.json`、`ui_spec/ui_state.schema.json`。
> 用法：板卡阶段 LVGL 版完成后，按本表逐项核对并勾选；"实测一致"列留证据路径。

## 一、布局数值（ui_layout_spec.json）

| # | 项 | 合同值 | PySide6 实现 | LVGL 实现 |
|---|---|---|---|---|
| L1 | canvas | **1024×600** | ✅ | ⬜ |
| L2 | 上左·交互信息 | x0=0 x1=585 y0=0 y1=556 pad=8 | ✅ | ⬜ |
| L3 | 上右·玩偶动画 | x0=585 x1=1024 y0=0 y1=556 pad=8 | ✅ | ⬜ |
| L4 | 下栏·系统信息 | x0=0 x1=1024 y0=556 y1=600 h=**44** | ✅ | ⬜ |
| L5 | 上区总高（无顶栏） | 556 | ✅ | ⬜ |
| L6 | 左区·摄像头画面 | 内宽 569 × 高 **300** | ✅ | ⬜ |
| L7 | 左区·信息行 / 延迟行 | 20 / 12 | ✅ | ⬜ |
| L8 | 左区·对话区（ASR+回复） | 高 **80**（ASR 20 + 回复 3×20） | ✅ | ⬜ |
| L9 | 左区·事件流 | 4 行 × 14 | ✅ | ⬜ |
| L10 | 右区·玩偶框 | **423×516**（=439−2×8−24） | ✅ | ⬜ |
| L11 | 右区·状态标签 / 底部渐隐 | 标签 24 / 渐隐 **28** | ✅ | ⬜ |
| L12 | 玩偶取景 | contain + **底部对齐** + `crop_bottom_ratio` **0.42**（腰部以上） | ✅ | ⬜ |
| L13 | 下栏项顺序 | camera/npu/pl/audio/lan/save/privacy/mode/**fps**（9 项） | ✅ | ⬜ |
| L14 | 右区·扩展位（玩偶框上方空档） | 预留高 **80**（`overlay_slot.reserved_height`），内容 **留空** | ✅ 接口就绪（未放内容） | ⬜ 需预留同高区域 |

## 二、颜色令牌（ui_tokens.json → colors）

| # | 令牌 | 值 | 使用位置 | PySide6 | LVGL |
|---|---|---|---|---|---|
| C1 | bg | #101820 | 摄像头画面底 | ✅ | ⬜ |
| C2 | panel_bg | #16202B | 面板背景 | ✅ | ⬜ |
| C3 | panel_border | #2A3A4A | 分隔线 | ✅ | ⬜ |
| C4 | accent | #4FC3F7 | 检测框/玩偶主色/模式 | ✅ | ⬜ |
| C5 | accent_dark | #0288D1 | （保留） | ✅ | ⬜ |
| C6 | warning | #FFB300 | 降级/zone | ✅ | ⬜ |
| C7 | error | #E53935 | 错误状态 | ✅ | ⬜ |
| C8 | success | #66BB6A | 就绪状态 | ✅ | ⬜ |
| C9 | privacy_mask | #1A1A2E | 隐私遮罩 | ✅ | ⬜ |
| C10 | text_primary | #E8EEF4 | 主文字 | ✅ | ⬜ |
| C11 | text_secondary | #9AA8B5 | 次要文字 | ✅ | ⬜ |
| C12 | box | #4FC3F7 | 检测框 | ✅ | ⬜ |
| C13 | zone | #FFB300 | presence zone | ✅ | ⬜ |

## 三、线宽 / 字号 / 间距 / 动画

| # | 令牌 | 值 | PySide6 | LVGL |
|---|---|---|---|---|
| T1 | line_widths.box | 2 | ✅ | ⬜ |
| T2 | line_widths.zone | 1 | ✅ | ⬜ |
| T3 | fonts.title | **16** | ✅ | ⬜ |
| T4 | fonts.label | **13** | ✅ | ⬜ |
| T5 | fonts.small | **11** | ✅ | ⬜ |
| T6 | fonts.dialogue | **14** | ✅ | ⬜ |
| T7 | spacing.panel_padding | 8 | ✅ | ⬜ |
| T8 | spacing.status_gap | 12 | ✅ | ⬜ |
| T9 | anim.breath | 3000ms/0.06 | ✅ | ⬜ |
| T10 | anim.attention | 1500ms/0.04 | ✅ | ⬜ |
| T11 | anim.listen | 800ms/0.03 | ✅ | ⬜ |
| T12 | anim.think | 1200ms/0.02 | ✅ | ⬜ |
| T13 | anim.speak | 500ms/0.08 | ✅ | ⬜ |

## 四、逻辑层（框架无关，两后端共用）

| # | 项 | 源文件 | 状态 |
|---|---|---|---|
| M1 | **10 态**→表现映射（含 `SPEAKING_LOW` 低落播报） | `board/ui/avatar_fsm.py` AVATAR_MAP | ✅ 复用 |
| M2 | 表情几何参数 | `board/ui/avatar_fsm.py` EXPRESSION_EYES | ✅ 复用（待新方案消费） |
| M3 | UI 状态聚合 | `board/ui/ui_state.py`（事件→UiState） | ✅ 复用 |
| M4 | 数据合同 | `ui_spec/ui_state.schema.json` | ✅ 复用 |
| M5 | 方案C·动画数据接口 | `UiState.avatar_anim`（name/params/enabled） | ✅ 接口就绪（enabled=False 静态） |
| M6 | 方案C·动画帧表 | `avatar_fsm.ANIMATION_FRAMES` + `animation_frames()` | ✅ 接口就绪 |
| M7 | 方案C·执行层 | `AvatarPanel._anim_state` + `_draw_eyes/_draw_mouth` | ✅ 已实现（B2V：帧表插值/intensity + 眼/嘴原语，锚框 `_face_anchor`） |
| M8 | 渲染入口 | `AvatarPanel._render_avatar` | ✅ 帧序列素材优先（`avatar_assets`）+ B2V 矢量回退 |
| M9 | 素材回退链（含**状态专属中间兜底**） | `board/ui/avatar_assets.py` `fallback_chain()` | ✅ 复用（`SPEAKING_LOW` → `talking_normal` → `idle_normal` → B2V） |
| M10 | **板端帧流与 10 态资源表**（RGB565 + 几何 + 体积） | `board/ui/avatar_board.py` + `tools/board_export.py` → `ui_spec/avatar_board_manifest.json` / `board/ui/lvgl/avatar_assets_table.h` | ✅ **已产出**（2026-09-12，6 素材已打包，去重 224.30 MiB） |

## 五、UI 状态截图（PC 证据）

### V2.0 板端三区（1024×600，本轮）

| 证据 | 文件 | 说明 |
|---|---|---|
| 10 态·三区 | `evidence_shots/ui_board_{idle,present,listening,thinking,speaking,speaking_low,camera_lost,network_lost,cancelled,error}.png` | `python examples/run_ui.py --all-states` 一次出齐，全部 **1024×600**；SPEAKING / SPEAKING_LOW 含左上对话区回复（`talking_low` 已于 2026-09-12 入库；未入库时玩偶区会按回退链放 `talking_normal`） |
| 玩偶·腰部以上 | `evidence_shots/ui_board_waist_up_preview.png` | `--framing waist-up` 素材（720×742 → 466×480）在 423×516 框内满铺 + 底部渐隐 |
| 草案对照 | `docs/ui_draft/board_1024x600.png`、`variants.png` | 设计阶段 4 变体对比（定稿依据） |

### V1.x 历史基线（PC 档 1280×720，已废弃，仅留档）

| 状态 | 文件 | 备注 |
|---|---|---|
| PRESENT | evidence_shots/ui_present.png | 有人在场 + 检测框（V1.1 基线） |
| SPEAKING | evidence_shots/ui_speaking.png | 播报表情（V1.1 基线） |
| CAMERA_LOST | evidence_shots/ui_camera_lost.png | 摄像头丢失（V1.1 基线） |
| ERROR | evidence_shots/ui_error.png | 错误状态（V1.1 基线） |
| **B2·IDLE** | evidence_shots/b2_idle.png | 待机/呼吸 + neutral 表情 |
| **B2·PRESENT** | evidence_shots/b2_present.png | 注视 + curious（O 嘴） |
| **B2·LISTENING** | evidence_shots/b2_listening.png | 聆听 + attentive |
| **B2·THINKING** | evidence_shots/b2_thinking.png | 思考 + thinking（视线 up_right） |
| **B2·SPEAKING** | evidence_shots/b2_speaking.png | 播报 + happy |
| **B2·CAMERA_LOST** | evidence_shots/b2_camera_lost.png | 摄像头丢失（warning 色） |
| **B2·NETWORK_LOST** | evidence_shots/b2_network_lost.png | 本地模式（warning 色） |
| **B2·ERROR** | evidence_shots/b2_error.png | 错误状态（error 色 + sad，B2 位图版·已被 B2V 取代） |
| **B2·CANCELLED** | evidence_shots/b2_cancelled.png | 已取消（warning 色，B2 位图版·已被 B2V 取代） |
| **B2V·IDLE** | evidence_shots/b2v_idle.png | 矢量主体待机 + neutral 表情 |
| **B2V·PRESENT** | evidence_shots/b2v_present.png | 注视 + curious（O 嘴） |
| **B2V·LISTENING** | evidence_shots/b2v_listening.png | 聆听 + attentive |
| **B2V·THINKING** | evidence_shots/b2v_thinking.png | 思考 + thinking（视线 up_right） |
| **B2V·SPEAKING** | evidence_shots/b2v_speaking.png | 播报 + happy |
| **B2V·CAMERA_LOST** | evidence_shots/b2v_camera_lost.png | 摄像头丢失（warning 色） |
| **B2V·NETWORK_LOST** | evidence_shots/b2v_network_lost.png | 本地模式（warning 色） |
| **B2V·ERROR** | evidence_shots/b2v_error.png | 错误状态（error 色 + sad） |
| **B2V·CANCELLED** | evidence_shots/b2v_cancelled.png | 已取消（warning 色） |

## 六、板卡阶段待办

- [x] **板端帧流与 10 态资源表**（人3 侧输入合同）：`python tools/board_export.py` 产出
      `assets/avatar/*/frames.rgb565`（大端 R5G6B5，底色 `#16202B`）+ `ui_spec/avatar_board_manifest.json`
      + `board/ui/lvgl/avatar_assets_table.h`（2026-09-12，去重 224.30 MiB / 双缓冲 0.85 MiB）
- [ ] LVGL 版按 §一/§二/§三 数值实现；**取帧/贴图直接消费 M10 的表**（双缓冲 + 按 `fps_milli` 步进）；
- [ ] 复用 §四 逻辑层（或移植为等价实现）；
- [ ] 逐项勾选本表并截图对比；
- [ ] 一致性结论由 Reviewer 签字。
