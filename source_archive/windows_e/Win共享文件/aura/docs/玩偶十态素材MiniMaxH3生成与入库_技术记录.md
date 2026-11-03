# 玩偶十态素材 MiniMax H3 生成与入库 —— 技术记录

> 日期：2026-10-04 ｜ 项目：AURA（AMD KV260）C 岗 · 鲸鱼娘十态帧序列素材
> 阶段：**PC / SIMULATED**（生成 + 入库）→ 产物供板端 LVGL 复用
> 上游底图：`玩偶素材\ControlNet正视\CNPOSE8_9107.png`（896×1280，用户认可的定稿）

## 一、目标与结果

| 项 | 结果 |
|---|---|
| 十态素材 | **9 态**（CANCELLED 在 `STATE_ASSET` 中映射到 `idle_normal`，不单独出） |
| 入库位置 | `aura\assets\avatar\<素材名>\` |
| 单态体积 | **4.61~4.86 MiB**（合计 42.10 MiB，预算 35 MiB/态，全部 OK） |
| 帧数 / 帧率 | **17 帧 / 10.462 fps**（保持原时长 1.625s） |
| 尺寸 | **336×480**（源 896×1280，长边限 480） |
| 校验 | **全部通过 ✓**（manifest sha256 逐帧核验） |

状态 → 素材名（`board/interaction/avatar_assets.py::STATE_ASSET`）：
IDLE→`idle_normal`、PRESENT→`idle_present`、LISTENING→`idle_listening`、
THINKING→`idle_thinking`、SPEAKING→`talking_normal`、SPEAKING_LOW→`talking_low`、
CAMERA_LOST→`emo_puzzled`、NETWORK_LOST→`idle_offline`、ERROR→`emo_sad`。

## 二、生成链（MiniMax H3，四项关键参数）

```
doll_final.png（定稿首帧）
  ──MiniMax H3 i2v（官方模板参数）──▶ 每态 39 帧 896×1280（源 24fps）
  ──抽帧 10fps + 长边 480──▶ 336×480 17 帧 ──▶ aura\assets\avatar\<素材名>\
```

**关键参数（都是踩坑换来的）**：
1. **`LEN = 39` 帧**（模型网格 17k+5 上 39=17×2+5 ✓）。
   - 124 帧（5.2 秒）会让模型**用"背景黑场淡入淡出"填充时间**：背景 std 88.30、峰峰 207.55 ✗
   - 39 帧：背景 std **0.09**、峰峰 **0.38** ✓（差异累积最大 68.19 → 7.20，降 89%）
2. **必须传 `last_frame`（= 首帧）**。`nodes_minimax_h3.py` 第 116-163 行：MiniMax H3 是
   **fl2va（首末帧双锚点）**，keyframe latent **每步 re-inject、永不 denoise**。
   只给首帧 = 半约束 → 5 秒内自由漂移；首尾同帧 → **末帧回归 32.90 → 0.41**（无缝循环 ✓）。
3. **`steps = 4`**（turbo LoRA 文件名为 `..._8step`，4 步对 39 帧够用；
   若要更长片段/更高画质可试 steps=8，时间约翻倍）。
4. **采样框架**：`SamplerCustomAdvanced + BasicGuider + BasicScheduler + KSamplerSelect`，
   sampler=`res_multistep`、scheduler=`simple`。

## 三、色调漂移：根因与解法（本次最大教训）

**现象**：LISTENING / SPEAKING 的**中间帧整体色调跑偏**（LISTENING 最大 |Δa|+|Δb| = 84.0、
25 帧越界；SPEAKING = 21.5、18 帧越界），而 IDLE / PRESENT 完全正常（0 帧）。

**根因（两个叠在一起）**：
1. **`fl2va` + 首末同帧要求"必须回到原点"，但模型必须产生变化** ——
   **prompt 越抽象，它越会挑一个"最省力的维度"做摆动**。IDLE/PRESENT 的 prompt 是
   **具体小动作**（`standing still, gentle breathing, slow blink`），模型有实事可做；
   而 LISTENING 的 `eyes attentive, calm concentrated expression`、SPEAKING 的
   `lively expression` 偏抽象 → 模型改去摆色调 ✗
2. **`first_frame` 与 `last_frame` 硬锚定**使"换背景色"这类 prompt 改动**完全无效**
   （实测品红版与白底版**逐像素几乎一致**：四角 240.6 vs 240.7、脸 159.0 vs 159.1）。

**解法（纯生成侧，零后处理）**：
- **prompt 具体化 + "保持"型描述**：
  `listening calmly, head upright with a very slight tilt, slow steady blink, faint small nod`
  **取代** `head tilted to one side AND HOLDING THAT TILT`（"保持姿态"给了模型摆色调的空间）
- **强化色调约束**：`absolutely consistent color and white balance in every frame,
  identical exposure and tone throughout, no color shift, no hue change, no saturation change`
- **seed 按状态名固定**（`SEED_MAP`），便于改动前后严格对比
- **结果**：**十态全部 0 帧越界**（最大偏移 2.0~8.3，判据阈值 8）✓
  - LISTENING 84.0/25帧 → **8.3/0帧**；SPEAKING 21.5/18帧 → **2.3/0帧**

**教训**：**不要用后处理"消漂移"**。试过 mask 贴回 / 照明场归一化 / 逐像素 de-flicker /
时域中值 / 稳定化 —— 数字上越修越小，**视觉上越来越诡异**（脸变"贴纸"、边缘剪影、
明暗扁平）。用户明确否决。**正确做法是从生成侧解决**。

## 四、抠图与画幅：两次决策

### 4.1 抠图 —— 最终放弃（用户决定）

探索过的路线与结论：

| 方案 | 结果 |
|---|---|
| 绿幕 + 色度键 | ✗ **有害**：绿↔蓝发青绿高光撞车（蓝发 42.9%→34.0%，发丝 18~20% 变绿） |
| 白底 + u2net | 蓝发 97.1%、**但**发丝间隙漏抠 10263px、色块入侵 199114px |
| 白底 + isnet-anime | 蓝发 98.7%、灰边 44.4→32.5（更好），**但**发丝间隙 16134px（更差） |
| 品红幕（模型生成）+ 色度键 | 品红与蓝发/白衣/肤色不冲突，**但**"蓝色布料也相邻白色布料"→ 判据难做 |
| 手动给底图换背景为品红 | 已实现（人物 79.6% 逐像素保留、仅补涂发丝间隙 58598px），**但仍有零星漏白** |

**最终决策**：**放弃抠图，使用"白底不透明"素材** —— 因为
**板端 UI 本身以白色背景为主，白底素材不会违和**（用户确认）。
素材按 `avatar_assets` 约定写为 **RGBA（alpha 全 255）**，透明通道留作后续演进。

### 4.2 画幅 —— 不裁切

项目定档口径是「**720×1280 全身 → 裁下部 42% → 480 档 466×480**」，
**但本批素材的生成 prompt 本身即 `upper body from head to waist, waist up`（腰部以上构图，不含腿）**，
再裁 42% 只会切掉裙摆。故采用 **`framing=full`（不裁切）**：
`896×1280 → 长边 480 → 336×480`，板端居中显示、两侧为白底留白。

## 五、⚠️ 项目侧遗留问题（未改动，仅记录）

`aura\scripts\prepare_avatar_frames.py` 第 45 行：
```python
from board.ui import avatar_assets, avatar_lod     # ← 模块已迁至 board.interaction
```
**执行 `--verify` 会 ModuleNotFoundError**。该文件是项目重构（`board/ui` → `board/interaction`）
的遗留，**本次未擅自修改**。临时以自写脚本 `verify_aura_assets.py` 按同一套
`avatar_lod` 函数完成校验。**建议项目负责人在重构收尾时同步该 import 路径。**

另：该脚本的抠像流程依赖桌宠 `src.matting`（`DEFAULT_MATTING_PROJECT`），
本批**不抠图**故未使用其主流程，只复用了 `board.interaction.avatar_lod` 的 LOD 函数。

## 六、验证方式与产物

**验证**（全部通过）：
- `tools/verify_aura_assets.py` → 九态 `verify_manifest` 全 OK，逐帧 sha256 校验 17 项/态
- 色调复核 `tools/tone_check.py`（在生成侧）：十态**0 帧越界**
- 逐帧平均差（抽帧后）：IDLE mean 6.48（对比 124 帧版 18.86）

**产物路径**：
| 类别 | 路径 |
|---|---|
| 入库素材（交付物） | `aura\assets\avatar\<素材名>\`（9 态 × 17 帧 + meta + manifest） |
| 原始帧（39 帧/态） | `ComfyUI\output\DOLL_<STATE>_*.png` |
| 定稿底图 | `…\玩偶素材\ControlNet正视\CNPOSE8_9107.png` |
| 生成脚本 | `ComfyUI_Windows_portable\tools\run_doll_states.py`（`--magenta` 可切品红背景） |
| 入库脚本 | `ComfyUI_Windows_portable\tools\pack_to_aura.py`（复用项目的 avatar_lod） |
| 校验脚本 | `ComfyUI_Windows_portable\tools\verify_aura_assets.py` |
| 检测脚本 | `wave_check.py` / `tone_check.py` / `bg_trace.py` / `compare_matting.py` 等 |

## 七、下一步（建议）

1. **项目侧**：修 `prepare_avatar_frames.py` 的 `board.ui` → `board.interaction` import
2. **板端**：用 9 态素材跑 UI，确认白底在"白色为主的 UI"上不违和
3. **可选增强**：帧数只有 17 帧（1.625 秒循环）；若需要更长循环，
   可用 `LEN=73`（3 秒 → 约 30 帧）重跑，仍是模型网格点，漂移应可控
4. **可选增强**：若日后要透明背景，可回到"品红幕 + 色度键"路线继续打磨判据

## 八、素材背景与系统 UI 背景的统一（2026-10-04 追加）

### 8.1 检测：两者严重不匹配

**素材背景实测**（`tools/check_bg_color.py`，九态 × 17 帧，抽样 24.2 万亮像素）：
```
均值 BGR  242.98 252.15 252.36   →  #FCFCF3（极浅黄白，B 通道偏低）
各态差异 <10；B 通道 std 4.78
（注意：素材背景**不是纯白**，是 #FCFCF3）
```
**系统 UI 令牌**（`ui/ui_tokens.json` 原值）：`bg #101820`、`panel_bg #16202B`（**深色**）
→ **亮度差约 220/255（86%）**，白底素材贴深色界面会成刺眼白方块 ✗

### 8.2 决策：把系统 UI 改为浅色主题（用户选定 C）

**关键判据**：该改的是 **`panel_bg`**（玩偶素材面板底色，必须与素材背景严格一致），
而 `bg`（整体背景）应**略深**以保留层次。

```
字段              旧深色      新浅色     说明
panel_bg         #16202B →  #FCFCF3   ★ 严格 = 素材背景实测值
bg               #101820 →  #F2F2E9   略深于面板，保留层次
panel_border     #2A3A4A →  #D5D5CB
text_primary     #E8EEF4 →  #1F242B   ★ 必须改深，否则白底白字
text_secondary   #9AA8B5 →  #5A6572
accent           #4FC3F7 →  #0B7FC4   浅蓝在白底不可读 → 加深
accent_dark      #0288D1 →  #025E8F
warning          #FFB300 →  #E08600
error            #E53935 →  #C62828
success          #66BB6A →  #2E7D32
privacy_mask     #1A1A2E →  #E8E8E0
box / zone                 同 accent / warning
```

### 8.3 改动清单（7 个文件 + 4 处断言）

| 文件 | 改动 |
|---|---|
| `ui/ui_tokens.json` | colors 段 13 项全部替换 |
| `ui/avatar_board_manifest.json` | `panel_bg` → `#FCFCF3` |
| `board/interaction/avatar_board.py` | `PANEL_BG_FALLBACK` + 2 处注释 |
| `board/interaction/lvgl/avatar_assets_table.h` | `AVATAR_PANEL_BG_RGB565 0x1105u → **0xFFFEu**` + 注释 |
| `scripts/ui_mock_draft.py` | 草案渲染器配色 4 行 |
| `scripts/make_demo_viewer.py` | 单文件 HTML 演示的 CSS 变量 |
| `tests/test_ui_layout.py` | 3 处断言（`#16202B`→`#FCFCF3`、`#16202b`→`#fcfcf3`） |
| `tests/test_avatar_board.py` | 2 处断言（`panel_bg`）；**`parse_hex_color` 那条保留**（函数输入样例） |

**板端 RGB565 换算**（沿用项目原有的**移位法**，已用 `#16202B` 验证：`22>>3=2, 32>>2=8, 43>>3=5` → `0x1105`，与头文件原始值完全吻合）：
```
#FCFCF3 → R=252>>3=31, G=252>>2=63, B=243>>3=30
        → (31<<11)|(63<<5)|30 = 0xFFFE   ✓
```

### 8.4 验证

- **残留搜检**：全库仅剩 `tests/test_avatar_board.py:39` 一处 `#16202B`（函数输入样例，**应当保留**）
- **JSON 合法性**：`ConvertFrom-Json` 通过，`panel_bg=#FCFCF3`、`bg=#F2F2E9`
- **未跑单测**：本机无 Python（ComfyUI 便携解释器未必装 pytest），**建议项目侧执行**
  `python -m pytest tests/ -q` 确认 4 处断言更新无误

### 8.5 本机模拟验证（实测输出，2026-10-04）

**环境**：本机无标准 Python；改用 `D:\sd-webui-aki-v4.11.1-cu128\_py310\python.exe`
（**Python 3.10.11，干净 stdlib**，无 pytest / PySide6 / PIL / numpy）。
另 ComfyUI 便携解释器为 Python 3.14.7（有 PIL 12.2.0 / numpy 2.3.2，仍然无 pytest、无 Qt）。

**验证脚本**：`%TEMP%\aura_verify_tokens.py`（**只读**，真实 `import board.interaction.avatar_board`）
**结果文件**：`%TEMP%\aura_verify_tokens.txt`

| 检查项 | 结果 |
|---|---|
| `panel_bg()`（真实函数调用） | ✅ `#FCFCF3` |
| `parse_hex_color("#FCFCF3")` / `("FCFCF3")` | ✅ `(252, 252, 243)` |
| `manifest.panel_bg` / `_rgb888` / `_rgb565` | ✅ `#FCFCF3` / `[252,252,243]` / `65534` |
| C 头 `AVATAR_PANEL_BG_RGB565` | ✅ `0xFFFE` |
| `ui_tokens.json` 13 项颜色 | ✅ 全部与预期一致 |
| **独立重算** `#FCFCF3` → RGB565 | ✅ `0xFFFE` |
| **sanity**：`#16202B` 重算 | ✅ `0x1105`（与头文件**改动前原值完全吻合** → **移位法确认无误**） |

> 结论：**颜色链路 17 项全部通过**。这也是"板端 RGB565 用移位法而非四舍五入"的实测证据
> —— 若用 `round()`，`#16202B` 的 R 会得 `3`（`0x1905`），与头文件原始值 `0x1105` 不符。

### 8.6 顺带发现的两个既有问题（**非本轮引入**）

#### 问题 1：`ui_spec/` 目录不存在 —— 目录改名未同步到代码（**已修**）

**根因**：`README.md:19-27` 记录，本仓由上游 `wujing-lite` **一次性"引入"**（团队 2026-09-26 拍板），
该操作**只做了物理移动目录**，**没有同步文件内部的 import / 路径引用**：

| 源（wujing-lite） | 目标（aura） | 文件 | 改为 |
|---|---|---:|---|
| `board\ui\*` | `board\interaction\` | 11 | `board.ui` → `board.interaction` |
| `ui_spec\*` | `ui\` | 4 | `ui_spec` → `ui` |
| `tools\*` | `scripts\` | 11 | `tools` → `scripts` |
| `schemas\*` | `common\schemas\` | 3 | （schema 引用需另行核对） |

**实测影响（修复前）**：
- `load_tokens()` 抛 `FileNotFoundError` → 被 `panel_bg()` 的 `except OSError` 吞掉 → **永远走 `PANEL_BG_FALLBACK`**
- `load_layout()` 无 try/except → **`board_table()` 直接抛 `FileNotFoundError`** → **`board_export.py` 导不出 manifest**
- `tests/test_ui_layout.py`、`test_ui_state.py` fixture **直接 error**
- 全部测试文件 **`from board.ui import …` 立即 ImportError**

**已执行修复（2026-10-04）**：
1. **`ui_spec` → `ui`（真路径 7 处）**：
   `avatar_board.py:34,35`（`LAYOUT_SPEC`/`TOKENS_SPEC`）、`qt_style.py:12`（`_SPEC_DIR`）、
   `board_export.py:37`（`MANIFEST_OUT`）、`test_ui_layout.py:15`、`test_ui_state.py:27,48`
2. **顺带修一个同源 bug**：`board_export.py:38` 的 `HEADER_OUT` 原为
   `_ROOT/"board"/"ui"/"lvgl"/…`（该目录同样不存在）→ 改为 **`board/interaction/lvgl`**
3. **批量改名（脚本 `aura_rename_refs.py`，dry-run 先审后 apply）**：
   **35 个文件 / 118 处**，规则：
   `board/ui/`→`board/interaction/`、`board.ui`→`board.interaction`、
   `from|import tools`→`from|import scripts`、`tools/`、`tools\`→`scripts`、
   `ui_spec/`、`ui_spec\`→`ui/`、`"ui_spec"`→`"ui"`
4. **刻意排除**（保留历史/上游原文）：`README.md`（源→目标对照表）、`docs/**`（上游提示词与 ADR 历史）、`__pycache__`、`*.docx`

**修复后验证**：
- 验证脚本 `%TEMP%\aura_verify_tokens.py` → **OVERALL: ALL PASS**
- 语法检查（`ast.parse` 全部 60 个 `.py`）→ **0 语法错误**
- 残留旧引用扫描 → **0 处**
- **import 冒烟（`%TEMP%\aura_import_smoke.py`）→ 14 OK / 0 真实失败**：
  `board.interaction.*`（6 个）、`board.runtime.fsm`、`scripts.*`（8 个）全部可导入；
  仅 3 个模块因**本机缺三方库**跳过 —— `scripts.ui_mock_draft`(PySide6)、
  `scripts.kws_benchmark`(numpy)、`scripts.md_to_docx`(python-docx)。
  **关键佐证**：`scripts.board_export` 修复前同时断裂于 `from board.ui import …`
  与 `from tools import …` 两处，现已可正常导入。

> 仍待项目侧确认的一项：`schemas\*` → `common\schemas\` 的引用是否也需同步（本记录未涉及）。

#### 问题 2：颜色改动有四类"搜不到"的引用形式（本轮已全部补上）

| 位置 | 原内容 | 为何正则漏掉 |
|---|---|---|
| `tests/test_avatar_board.py:50` | `== (22, 32, 43)` | **十进制元组** |
| `tests/test_avatar_board.py:128` | `((0x16>>3)<<11)\|((0x20>>2)<<5)\|(0x2B>>3)` | **移位表达式** |
| `ui/avatar_board_manifest.json:11-16` | `rgb888=[22,32,43]`、`rgb565=4357` | **已生成产物** |
| `board/interaction/avatar_board.py:266` | 兜底 `or (0x16, 0x20, 0x2B)` | **十进制元组** |

> **=> 教训：改主色时不能只搜 `#XXXXXX` 字符串，必须同时搜其 RGB 十进制元组、移位表达式、以及已生成的产物文件（manifest / .h）。**
