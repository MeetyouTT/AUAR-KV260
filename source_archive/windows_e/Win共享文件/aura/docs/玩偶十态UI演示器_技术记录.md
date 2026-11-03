# 玩偶十态 UI 演示器 技术记录

> 产出日期：2026-10-04 ｜ 项目：AURA（FPGA-amd 自主命题赛道）
> 定位：**PC / SIMULATED 视觉演示**，不是板端实测。用途是让干系人**双击一个 HTML** 就能看到
> 浅色主题下的十态玩偶动画，无需装 PySide6 / ffmpeg / 任何运行时。

## 1. 背景与目标

项目此前只有三类"看得见"的东西，各有硬依赖：

| 已有通路 | 依赖 | 本机可用性 |
|---|---|---|
| `board/interaction/qt_app.py` 原型 | **PySide6** | ✗ 未安装 |
| `scripts/make_demo_viewer.py`（313 帧剧情播放器） | **ffmpeg + 已渲染的 demo_frames** | ✗ 帧未生成 |
| `scripts/make_asset_gallery.py`（帧带/循环 GIF） | Pillow | ✓ |

于是需要一条**零运行时依赖**的演示通路：把十态素材直接编成**单文件自包含 HTML**，双击即看，
并且**必须用真实的浅色主题令牌**（否则演示的不是交付形态）。

## 2. 交付物

| 文件 | 说明 |
|---|---|
| `evidence_shots/avatar_states_demo.html` | **6.62 MiB 单文件演示器**，双击浏览器打开 |
| `scripts/make_doll_demo.py` | 生成器（可复现），只依赖 Pillow |

演示器内包含：

- **按 `ui/ui_layout_spec.json` 还原的 1024×600 三区**：左 585×556 / 右 439×556 / 下通栏 1024×44；
- **按 `ui/ui_tokens.json` 上色的浅色主题**（见 §3）；
- **10 个运行态 × 17 帧 = 170 帧**内嵌为 WebP base64；
- 顶部 10 个状态按钮 + **「自动剧本 ▶」**（11 步流转一遍后循环）；
- 左区模拟 ASR / 回复 / 端到端延迟 / 事件流，下栏 9 项系统状态（含告警/错误配色）。

## 3. 关键技术决策

1. **素材是 `white-opaque` 白底，不是透明底。**
   `assets/avatar/*/meta.json` 里 `spec.bg = "white-opaque"`，PNG 却是 RGBA。做法是
   **把每帧 alpha 合成到 `panel_bg = #FCFCF3` 上再编码**——白底落在近白面板上视觉融合，
   比强行抠图安全，也顺带暴露了"素材底色与面板色是否协调"这个问题（结论：协调）。
2. **用 WebP 而不是 PNG 内嵌。**
   336×480 RGBA PNG 单帧约 285 KB × 170 帧 = 47 MB，浏览器打不开。转 **WebP q=82** 后
   每态约 500 KiB，**总计 4.95 MiB**（上游 `demo_scenario.gif` 是 6.4 MB，同量级）。
3. **帧率取自素材而非拍脑袋。**
   `meta.json` 的 `fps = 10.462`（源 24 fps 降采样到 10 fps 后的实际值）。播放器用
   `requestAnimationFrame` + 累积时间戳补步进，避免 `setInterval` 在后台标签页漂移。
4. **所有尺寸/颜色都从 JSON 读，不硬编码。**
   除 `#fade` 渐变的 rgba 外，HTML 里没有一个手写色值；`__C_*__` / `__LW__` 占位符由生成器
   从 `ui_tokens.json` 注入，`avatar_box`、`canvas` 等取自 `ui_layout_spec.json`。
   生成器末尾会**自检残留占位符**（输出 `unresolved plc`），本次为 `(none)`。
5. **不引入任何板端代码路径。**
   演示器是纯静态 HTML，不 import 项目模块，因此改名/重构不会静默破坏它；
   代价是文案与状态机是**模拟的**，已在 UI 与本文档中标注 `PC / SIMULATED`。

## 4. 踩坑与根因

| 现象 | 根因 | 处置 |
|---|---|---|
| `SyntaxError: invalid character '（' (U+FF08)` | 不是编码问题。用 `old_text = "boot();\n\"\"\""` 做锚点编辑时，把 `boot();` 和 `TPL_JS` 的**结尾三引号一起替换掉了** → 字符串未闭合 → 后面 `_status_html` docstring 的三引号反而闭合了它，`（` 变成裸字符 | 补回 `boot();` + `"""`。先用"文件能否 UTF-8 解码"排除了编码嫌疑 |
| 终端回显丢失 | ComfyUI 便携版 Python 启动会重置控制台，shell integration 抓不到输出 | 所有结果写文件再读（沿用既有约定） |

## 5. 验证方式与结果

生成器自带日志（`%TEMP%\aura_make_ui_demo.txt`）：

```
OK    IDLE        -> idle_normal     frames=17  webp= 512 KiB
...（10 行，十态全部命中，无一 MISS）
states / frames : 10 x 17
webp payload    : 4.95 MiB
html output     : avatar_states_demo.html (6.62 MiB)
unresolved plc  : (none)
theme tokens    : bg=#F2F2E9 panel=#FCFCF3 border=#D5D5CB accent=#0B7FC4
```

**令牌注入核对**（直接读产物 HTML）：`#canvas` = `#F2F2E9`；`.panel`/`#bottom` =
`#FCFCF3`；边框 `2px solid #D5D5CB`（线宽取自 `line_widths.box = 2`）；强调色 `#0B7FC4`；
隐私遮罩 `#E8E8E0`；文字 `#1F242B` / `#5A6572`。

**十态到素材的映射**（与 `board/interaction/avatar_assets.py` 的 `STATE_ASSET` 一致）：

| 运行态 | 素材目录 | 运行态 | 素材目录 |
|---|---|---|---|
| IDLE | idle_normal | SPEAKING_LOW | talking_low |
| PRESENT | idle_present | CAMERA_LOST | emo_puzzled |
| LISTENING | idle_listening | NETWORK_LOST | idle_offline |
| THINKING | idle_thinking | CANCELLED | idle_normal（复用） |
| SPEAKING | talking_normal | ERROR | emo_sad |

## 6. 涉及文件清单

- **新增**：`evidence_shots/avatar_states_demo.html`（产物）、`scripts/make_doll_demo.py`（生成器）
- **只读引用**：`ui/ui_tokens.json`、`ui/ui_layout_spec.json`、`assets/avatar/*`（10 个目录）
- **未改动**任何板端 / 测试 / 现有脚本代码

## 7. 下一步

1. **体量优化（可选）**：6.62 MiB 偏大，可加 `--scale 0.75` / `--quality 70` 降到 ~3 MiB；
   或每态只留首尾+中间 6 帧做"精简版"。当前保持全帧以保证动效真实。
2. **补上真实数据**：左区文案目前是模拟值；接板后可把真实延迟/事件流灌进同一模板。
3. **仍挂起的项目侧事项**：单测未跑（本机无 pytest）；`schemas → common/schemas` 引用未确认；
   `evidence_shots/demo24/demo_frames` 未在本机生成（需 PySide6 渲染场景）。
