# IDLE 素材取景口径统一（C 方案）——技术记录

> **环境标签：PC / SIMULATED** —— 本文全部证据为 PC 侧预处理与离屏渲染产物，**不含任何板端实测数据**。
> 日期：**2026-09-12（第 2 轮）** ｜ 工程：`wujing-lite` ｜ 角色线：人3（运行时 / UI / 系统集成）
> 工作区：`D:\share\项目开发\FPGA语音助手开发\wujing-lite`

## 1. 背景与目标

### 1.1 现象

13 秒剧本化交互演示（`examples/run_demo_scenario.py`：IDLE→PRESENT→LISTENING→THINKING→SPEAKING→IDLE）
在状态切换瞬间出现明显的「**小 ↔ 大**」玩偶尺寸跳变。

### 1.2 目标

消除该跳变，使 **IDLE 与其余 5 个表达性状态取景口径一致**。
用户裁定：**开场即应为「半身」构图，不应是全身**。

## 2. 根因：不是渲染缺陷，是素材入库口径遗留

| 素材 | 入库日期 | `spec.max_side` | `spec.framing` | 入库结果 |
|---|---|---|---|---|
| `idle_normal` | **09-02** | 320 | **字段缺失 → 默认 `full`** | 180×320（全身） |
| 其余 5 态 | 09-12 | 480 | `waist-up`（`crop_bottom_ratio: 0.42`） | 466×480（半身） |

三条佐证：

1. **规范里早已写明两档口径** —— `board/ui/avatar_lod.py` §1.5：

   - `"full": 0.0` —— 不裁切（膝上全身，**历史口径**，注释直接点名「现役 idle_normal 即此档」）；
   - `"waist-up": 0.42` —— 裁掉下部 42%（腰部以上，**板端定稿口径**）。

2. **入库时间差** —— 09-02 入库 `idle_normal` 时，「板端玩偶框 423×516 + waist-up 定稿」尚未确立，
   于是走了当时默认的 `full`；09-12 补其余 5 态时口径已改为 `waist-up / 480`，
   但**没有回头重跑 `idle_normal`**，留下一档"历史口径"素材。

3. **工具与文档早有告警，只是未处置**：

   - `prepare_avatar_frames.py --status` →
     `idle_normal 100 180x320 full 8.4 MiB [OK] 已入库／取景=full ≠ 板端 waist-up`
   - `assets/avatar/README.md` §2.1 → `⚠️ 已入库但口径落后（180×320 / full，待按 waist-up 重生成）`
   - `ui_spec/avatar_board_manifest.json` 中 IDLE 的
     `dst_rel = {x:66, y:0, w:290, h:516, scale:1.6125}` ——
     渲染层**忠实地**把 9:16 竖构图 contain 进 423×516 玩偶框，人物自然偏小、下半高度被浪费。
     ⇒ **问题 100% 在素材口径，渲染层无 bug。**

## 3. 修前量化（跳变的硬数据）

板端渲染像素（玩偶框 423×516 @ (593,32)，取景 `contain+bottom`）：

| 版本 | 素材 | 渲染框 | 人物实际占位 | vs PRESENT 宽度 |
|---|---|---|---|---|
| **修前** IDLE（full） | 180×320（alpha bbox 180×300） | **290×516** | **290×483** | **−31.4%** |
| PRESENT（waist-up） | 466×480 | 423×436 | 423×395 | 基准 |

实测演示帧：`demo_00` 包围盒 `x660..949 / y65..547`；`demo_10` 包围盒 `x593..1015 / y153..547`：

- 切换瞬间人物宽度 **290 → 423（×1.459）** ⇒ 即肉眼所见的「小→大」；
- **底部对齐一致**（两者均贴底 y=547）⇒ 差异全部来自素材构图口径，非渲染异常。

## 4. 处置：C 方案（重裁同一份源视频，不重新生成）

**决策**：把 `waist-up` 确立为**唯一**板端口径，**只重裁 `idle_normal`**；
`idle_normal.mp4` 本体**只读不动**（sha256 校验一致），故无需重新生成视频，其余 5 态完全不受影响。

### 4.1 干跑（零写入）

```powershell
$w = "D:\share\项目开发\FPGA语音助手开发\wujing-lite"
python "$w\tools\prepare_avatar_frames.py" --state IDLE `
    --src "D:\share\项目开发\桌面AI桌宠\assets\videos\idle_normal.mp4" `
    --framing waist-up --max-side 480 --budget-mb 35 --force --dry-run
```

输出（关键三行）：

```
取景 waist-up：裁掉下部 42%（保留上部 58%）→ 720x1280 → 720x742（宽度不变）
源 720x1280 @24.06fps / 241 帧  →  入库 466x480 @9.98fps / 100 帧（像素量 1/4.1）
体积预估: PNG 32.00 MiB → 合计 32.00 MiB（预算 35.0 MiB）  [OK]
```

⇒ 与其余 5 态入库规格 (`466×480 / 100 帧 / max-side 480 / waist-up`) **完全一致**。

### 4.2 正式入库

同命令去掉 `--dry-run`（长任务，用 `Start-Process` 脱离 + 文件轮询）：

```
[video] idle_normal.mp4 → %TEMP%\wujing_avatar_prep\idle_normal  (adaptive, 57.2 s)
[写入] 100 帧 PNG 至 assets\avatar\idle_normal
[清单] manifest.json：100 帧 / 实际 23.36 MiB（预估 32.00 MiB）
[清理] 已删除中间目录；原始素材未改动
```

### 4.3 刷新板端输入合同（**踩坑点**）

```powershell
python "$w\tools\board_export.py" --force
```

> ⚠️ **必须带 `--force`**：首次不带 `--force` 时，`frames.rgb565` 已存在 →
> 工具输出 `[跳过] idle_normal 已有 frames.rgb565（10.99 MiB）`，
> 导致**清单已按 466×480 更新、帧流却仍是旧的 180×320 数据**（IDLE 帧流 10.99 MiB ≠ 其余 42.66 MiB）。
> 带 `--force` 重打包后 IDLE 帧流恢复为 `44,736,000 B（42.66 MiB）`，与其余素材一致。

## 5. 验证结果（3 层，全部 PASS）

### 5.1 素材层

`assets/avatar/idle_normal/000000.png`：**466×480**，alpha 包围盒 `(0,53,466,480)`（人物 466×427），
与预览预测 `(0,54,465,479)` 差 ≤1px。

### 5.2 合同层（`ui_spec/avatar_board_manifest.json`）

IDLE 条目由

```json
"src_w": 180, "src_h": 320, "dst_rel": {"x":66,"y":0,"w":290,"h":516,"scale":1.6125}
```

变为

```json
"src_w": 466, "src_h": 480, "dst_rel": {"x":0,"y":80,"w":423,"h":436,"scale":0.907725}
```

⇒ **与 PRESENT / LISTENING / THINKING / SPEAKING 逐字段相同**（`rgb565_bytes` 亦为 `44,736,000 = expected`）。
板端帧流合计：逐素材去重 **224.30 → 255.98 MiB**；逐状态 426.64 MiB（不变）。

### 5.3 渲染层（重跑演示后的实际帧）

| 帧 | 人物包围盒 | 宽 × 高 | 底边 |
|---|---|---|---|
| 修前 `demo_00`（IDLE） | x660..949 / y65..547 | 290×483 | 547 |
| **修后 `demo_00`（IDLE）** | **x593..1015 / y163..547** | **423×385** | **547** |
| 参考 `demo_10`（PRESENT） | x593..1015 / y153..547 | 423×395 | 547 |

- **宽度跳变消除**：290 → 423，修后与参考**同为 423**（`×1.459` 的跳变归零）；
- **残余尺度差 385 / 395 = −2.5%**：源于素材"代次"差（旧代素材人物在源视频里略小），
  非口径问题；如需根治见 §7。
- 复核脚本结论：**`PASS —— 最终呈现与预览裁切效果一致`**（`evidence_shots/_verify_c.py`）。

### 5.4 回归

`pytest -q --junitxml` → **tests=217 / failures=0 / errors=0 / skipped=0 / 5.811s**（与修前一致）。

### 5.5 证据文件

| 文件 | 说明 |
|---|---|
| `evidence_shots/_c_preview_compare.png` | 先验三联图：现状 full ／ 拟修 waist-up（绿幕原帧）／ 参照 PRESENT |
| `evidence_shots/_c_before_after.png` | **修前 / 修后 / 参照** 板端渲染帧并排（已嵌入 `demo_viewer.html`） |
| `evidence_shots/demo_frames_before/` | 修前 27 帧备份（27 张，无 0 字节） |
| `evidence_shots/demo_scenario_before.gif` | 修前动图备份（1,271,450 B） |
| `evidence_shots/demo_frames/` + `demo_scenario.gif` | **修后** 27 帧 + 动图（1,283,821 B，27 帧） |
| `evidence_shots/demo_viewer.html` | 查看页：动图 + 时间轴 + 修前/修后对照 + 27 帧全览 |
| `evidence_shots/_verify_c.py` | 复核脚本（临时，可删）：素材 alpha bbox ／ 渲染包围盒 ／ 并排出图 |

> 例外说明：`_c_preview_make.py` 中"现状"一栏的人物占位用 **alpha 包围盒**、"拟修后"一栏因是**绿幕原帧**
> 用**绿幕色差键控**（绿幕基准 `#0FE91B`、容差 60）——两者口径不同，故对比以 §5.3 的**渲染层同口径**为准。

## 6. 涉及文件清单

**改动**

- `assets/avatar/idle_normal/`（100 帧 PNG 重裁 + `meta.json` 增 `framing: waist-up` / `crop_bottom_ratio: 0.42` / `max_side: 480` + `manifest.json` 重算）
- `assets/avatar/idle_normal/frames.rgb565`（10.99 → **42.66 MiB**）
- `ui_spec/avatar_board_manifest.json`、`board/ui/lvgl/avatar_assets_table.h`（`board_export.py --force` 重生成）
- `assets/avatar/README.md` §2.1 状态行
- `evidence_shots/demo_frames/*`、`demo_scenario.gif`、`demo_viewer.html`

**新增（证据 / 临时）**

- `docs/IDLE素材取景口径统一_技术记录.md`（+ `.docx`）
- `evidence_shots/_c_preview_make.py`、`_verify_c.py`、`_c_preview_compare.png`、`_c_before_after.png`、
  `demo_frames_before/`、`demo_scenario_before.gif`

**未改动（红线遵守）**

- `D:\share\项目开发\桌面AI桌宠\assets\videos\idle_normal.mp4`（只读，sha256 `ce007253…59ecdf` 不变）
- `evidence_shots/keyframes/idle_normal_t00.00_f000000.png`、`evidence_shots/avatar_ref_idle_normal_f000000.png`
  （旧锚点图；本轮抽帧另存 `evidence_shots/_c_preview/`）

## 7. 遗留与下一步

1. **残余 −2.5% 尺度差**：属素材代次差。根治手段 = **alpha 包围盒归一化**（把各态人物 bbox 统一到同一占位再入库），
   约半天工时，可复用 `tools/avatar_keyframes.py` 的剪影度量逻辑（交接文档待决③）。
2. **`idle_normal.mp4` 循环缝 FAIL**（首帧 vs 末帧：mean 19.90 / 差异 47.3%）**本次未解决**，
   与取景口径无关，需重新生成视频（提示词见 `docs/玩偶素材Seedance提示词包_技术记录.md`）。
3. **`--ref` 核验基准**是否正式固化为「新代首帧」（交接文档待决②）—— 本次未涉及。
4. 建议把 `evidence_shots/_verify_c.py` 转正为 `tools/verify_framing_consistency.py`，
   纳入以后"每次入库后自动跑一次口径一致性"的 SOP。
5. `_c_preview_make.py` / `_verify_c.py` / `_*.log` 属临时产物，确认后可清理。

