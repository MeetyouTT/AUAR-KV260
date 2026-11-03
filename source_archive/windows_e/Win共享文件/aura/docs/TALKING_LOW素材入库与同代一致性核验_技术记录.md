# 说话·低落素材（talking_low）入库与同代一致性核验 · 技术记录

> 日期：2026-09-12 ｜ 工程：`wujing-lite` ｜ 环境标签：PC / SIMULATED
> 对象：**`talking_low`**（运行时状态 **`SPEAKING_LOW`** —— 播报·情绪低落）
> 源素材：`jimeng-2026-09-12-3869-Vertical 9_16 portrait shot of @characte....mp4`
> （即梦 Seedance 产出，**11,061,593 B**，sha256 `1663ecc4…adc7`）
> 关联：`docs/情绪分档扩展_播报高低落两档SPEAKING_LOW_技术记录.md`（**分档设计/代码改动**）、
> `docs/玩偶素材Seedance提示词包_技术记录.md` **§4.8**（本素材提示词）、
> `docs/TALKING素材入库与同代一致性核验_技术记录.md`（同代的 `talking_normal`，上一轮）。

---

## 一、背景与目标

`SPEAKING_LOW` 于同日随"情绪分档"扩展加入（10 态合同），当时只有提示词与回退链（未入库时播 `talking_normal`）。
本轮把**真素材**做完闭环。

| # | 目标 | 判定 |
|---|---|---|
| G1 | 素材与同代 `talking_normal` **同代同取景同姿态** | `--ref`（基准 = `talking_normal` 首帧）PASS |
| G2 | 可**无缝循环**（首尾帧同姿态） | `--check-loop` 非 FAIL |
| G3 | 演出符合 §4.8：**说话 + 嘴角下垂 + 无手势 + 无一次性动作** | 7 帧时间线目检 |
| G4 | 入库规格与既有 4 条一致（466×480 / waist-up / 100 帧 / ≤35 MiB） | 干跑 + `--verify` |

---

## 二、做了什么（SOP 全流程 · 实测数据）

### ⓪ 归档（源素材只读）

```powershell
Copy-Item -LiteralPath "<Downloads>\jimeng-2026-09-12-3869-…mp4" `
          "D:\share\项目开发\桌面AI桌宠\assets\videos\talking_low.mp4" -Force
```

- 归档后 **11,061,593 B**，sha256 `1663ECC423BB4402C572528827EADC47DC3BFB1F034C517BDED4FBA19493ADC7`
- **源与副本 sha256 一致** ⇒ 纯拷贝、未改动源文件（`meta.json.source.sha256` 同步记录）

### ① 入库前干跑（规格 + 体积预估）

```
python tools/prepare_avatar_frames.py --state SPEAKING_LOW --src "...\talking_low.mp4" `
    --framing waist-up --max-side 480 --budget-mb 35 --dry-run
```

| 项 | 实测 |
|---|---|
| 源 | **720×1280 @24.06 fps / 241 帧 / 10.02 s** |
| 取景 | waist-up 裁掉下部 42% → 720×742 |
| 入库 | **466×480 @9.983 fps / 100 帧**（像素量 1/4.1） |
| 体积预估 | PNG **32.00 MiB**（预算 35）→ `[OK]` |

⇒ 与 `idle_listening / idle_present / idle_thinking / talking_normal` **规格逐项一致**（同批即梦参数）。

### ② 关键帧核验（`--check-loop` / `--find-loop` / `--ref`）

```powershell
python tools/avatar_keyframes.py --src "...\talking_low.mp4" `
    --out-dir evidence_shots\keyframes --name talking_low --count 3 --check-loop --find-loop `
    --ref evidence_shots\keyframes\talking_normal_t00.00_f000000.png
```

| 核验项 | 全图 mean | 全图差异像素(>8) | 主体 mean | 主体差异像素(>8) | 判定 |
|---|---|---|---|---|---|
| 循环缝 **f0 vs f240** | 2.47 | 2.13% | **2.63** | **2.77%** | ⚠️ **WARN** |
| 一致性 **f0 vs `talking_normal` f0** | 2.12 | 0.85% | **2.13** | **1.16%** | ✅ **PASS** |
| 最佳循环点（`--find-loop`） | 0.00 | 0.00% | 0.00 | 0.00% | ✅ 就是 **f0**（无需裁帧重排） |

> **判据回顾**：`--check-loop` 主体 mean ≤2.0 且差异 ≤2% → PASS；2 倍阈值内 → WARN；超出 → FAIL。
> `--ref` 主体 mean ≤4.0 且差异 ≤5% → PASS。
> ⇒ 本轮 **「全部通过（PASS/WARN）」**，退出码 0。

### ③ 判读（三联图 / 时间线 / 剪影 / 差异定位）

**a) 三联图（`talking_low_ref_check.png` / `talking_low_loop_check.png`，`--ref` 与循环缝各一张）**

- ref 三联：左 = `talking_normal` f0（**抿嘴站姿、双手在袖内**），中 = 本素材 f0（**嘴微张在说话、嘴角略垂、视线偏低**），
  右 = 差异×4 → 差异呈**面部（眼/嘴）+ 发丝 + 袖口边缘的细描边**，**无块状换区**；
- loop 三联：f0 与 f240 同姿态同表情，差异只在**发丝/袖口/裙摆边缘**。

**b) 7 帧动作时间线（`--count 7` → contact sheet）**

| t | 0.00 | 1.66 | 3.33 | 5.03 | 6.69 | 8.35 | 9.98 |
|---|---|---|---|---|---|---|---|
| 帧 | f0 | f40 | f80 | f121 | f161 | f201 | f240 |
| 形态 | 站姿·嘴微张 | 微张·头微动 | 微张 | 微张 | 微张·袖/发丝微动 | 微张 | **回到站姿**（同 f0） |

⇒ 全片 = **持续说话（小幅口型开合）+ 站姿微动**，**无手势、无一次性动作**，首尾同姿态 —— 与 §4.8 要求吻合。

**c) 剪影度量（绿幕容差 60，与工具同口径）**

| 图 | 前景占比 | x0 | x1 | y0 | y1 | 高 h | h/H | 包围盒中心 | **真实质心** |
|---|---|---|---|---|---|---|---|---|---|
| `talking_low` f0 | 67.9% | 0 | 719 | **60** | 1279 | **1220** | 0.953 | 359.5 | **369.1** |
| `talking_normal` f0 | 68.0% | 0 | 719 | **60** | 1279 | **1220** | 0.953 | 359.5 | **369.0** |
| `idle_thinking` f0（同代） | 67.9% | 0 | 719 | 60 | 1279 | 1220 | 0.953 | 359.5 | 369.0 |
| `idle_listening` f0（**旧代**） | 65.9% | 0 | 719 | **72** | 1279 | **1208** | 0.944 | 359.5 | 369.8 |

⇒ 本素材与 `talking_normal` / `idle_thinking` **逐项相同**（y0、h、包围盒中心、前景占比、质心差 0.1 px）
⇒ **同代 · 同取景 · 同尺度**；`idle_listening`（旧代）头顶高 12 px 的差别在本素材上**不存在**。

**d) 差异定位（`talking_low` f0 vs `talking_normal` f0）**

- 差异像素（>8）：26,965 / 921,600 = **2.93%**；差异 bbox 覆盖全图（描边型差异，非块状）
- 最集中的行：y=439 / 443 / 472 / 488 / 496（面部—颈胸过渡带）、728、1142、1151
- 分带占比：头部(0~15%H) **8.4%**、面颈(15~30%) **12.5%**、胸腹(30~58%) **39.4%**、58% 以下 **39.7%**

> 判读：差异**沿轮廓均匀铺开**（无明显单区集中），结合"剪影逐项相同"⇒
> 属**表情 + 口型 + 衣摆/发丝微动**的整体轻微差，**不是换装 / 换机位 / 换姿势**。
> 换言之：这是"**同一个人、同一个机位，情绪从高涨切到低落**"该有的差异形态。

### ④ 入库

```powershell
python tools/prepare_avatar_frames.py --state SPEAKING_LOW --src "...\talking_low.mp4" `
    --framing waist-up --max-side 480 --budget-mb 35
```

| 项 | 结果 |
|---|---|
| 抠像 | `adaptive`，241 帧，**55.2 s** |
| 落盘 | `assets/avatar/talking_low/000000.png … 000099.png`（**100 帧**）+ `meta.json` + `manifest.json` |
| 实测体积 | **24.83 MiB**（预估 32.00 / 预算 35 → `[OK]`） |
| meta.json | `fps 9.983` / `size [466,480]` / `frames 100` / `spec.framing=waist-up` / `crop_bottom_ratio=0.42` / `matte_mode=adaptive`；`source.sha256=1663ecc4…adc7`（与归档指纹一致） |
| 临时目录 | 抠像中间产物已自动清理 |

### ⑤ 入库后验证

| 命令 | 结果 |
|---|---|
| `--verify` | **6/6 `[OK]`**（`idle_listening / idle_normal / idle_present / idle_thinking / talking_low / talking_normal`，均"100 帧 / manifest 一致"） |
| `--status` | **6 / 9**；缺 `emo_puzzled / emo_sad / idle_offline`；**受影响状态降到 3 个**（`CAMERA_LOST / ERROR / NETWORK_LOST`，`SPEAKING_LOW` 已移出） |
| `run_ui.py --all-states` | 出 **10 张** 1024×600 板图；`ui_board_speaking_low.png` 玩偶区**已是 `talking_low` 真素材**（此前是回退的 `talking_normal`） |
| `pytest` | **tests=205 / failures=0 / errors=0 / skipped=0**（6.932 s） |

---

## 三、关键判读与决策

### 3.1 基准选择：`--ref` 用**同代** `talking_normal` 首帧（不是旧锚点图）

`talking_low` 与 `talking_normal` **同源**（同一锚点图、同一构图段、同一机位、同一批即梦参数），
所以正确基准是 **`evidence_shots/keyframes/talking_normal_t00.00_f000000.png`**。

- 实测：主体 mean **2.13** / 差异 **1.16%** → **PASS**
- 若误用旧锚点图 `avatar_ref_idle_normal_f000000.png`，会读出 ≈26 的"代差"数字（同 `idle_thinking` / `talking_normal`
  的历史读数 25.88~25.97），那是**代次口径差**而非素材缺陷 —— 该口径已在提示词包 §4.8 与本轮 SOP 中固化。

### 3.2 「剪影逐项相同」是本轮最有力的同代证据

`y0=60 / h=1220 / 包围盒中心 359.5 / 前景 67.9%（对 68.0%）` 四项全等 ⇒ 排除
"取景偏近/偏远、机位变动、人物缩放"这三类常见问题；剩下的差异必然只来自**表情与微动**。
（方法学沿用 `docs/TALKING素材入库与同代一致性核验_技术记录.md` 的**五步证据链**。）

### 3.3 循环缝 **WARN 2.63 / 2.77%** 的判读：无需返工

- 主体 mean 2.63 与同代实测（present 2.60 / thinking 2.64 / normal 2.90）**同档**；
- 差异 **2.77% 未越 4% 上限**（对照 `talking_normal` 的 4.21% 曾判"临界 FAIL"），本轮**连 FAIL 都没碰到**；
- `--find-loop` 最佳点就是 **f0** ⇒ 没有更优裁剪点，裁帧无法改善；
- 三联图显示差异只在**发丝/袖口/裙摆**的细描边 ⇒ 是"说话时衣摆与发丝的自然微动"。

⇒ **判 WARN 可用、直接入库**；若日后要压到 PASS，需在提示词里进一步降低"说话时衣摆/重心微动"幅度（成本高，本轮不做）。

### 3.4 演出符合度：**无手势**是关键差异点

§4.8 明确要求"**手势几乎为零**（手留在振袖里）、低落但不哭不闹"。
7 帧时间线显示：全片**双手始终在袖内/腹前**、只有小幅口型开合 + 发丝与袖子微动 ⇒ 与要求一致；
这也让它在**运动模式**上与 `talking_normal`（举拳 → 张手说话 → 握拳）形成鲜明对比 —— 面板上切换状态时观感明确。

### 3.5 踩坑记录（本环境可复用）

- **源文件名含空格 / `@` / 连续点号**（`…of @characte....mp4`）：
  PowerShell 里必须用 `-LiteralPath`（避免 `[`、`*` 等被当通配符），Python 侧作为**单个带引号参数**传入即可；
- **长任务必须 `Start-Process -RedirectStandardOutput/-Error -PassThru` + 轮询日志**：
  抠像 241 帧 ≈55 s，终端 shell integration 会丢输出，靠日志文件读进度（本轮共轮询 12 次到完成）；
- **读图先缩图**：720×1280 三联图（2.3 MiB）直接读会被判超限，用 `%TEMP%\tk_view.py small` 缩到宽 760 转 JPEG；
- **剪影度量脚本要同时打印质心与包围盒中心**：历史文档里的 `cx=359.5` 其实是**包围盒中心**（因左右触边而恒为 359.5），
  真实质心是 **369.0~369.8**，两者必须都记录，避免后续误判"质心漂移"。

---

## 四、验证结果汇总

| 环节 | 判据 | 实测 | 结论 |
|---|---|---|---|
| 干跑规格 | 与既有同批一致 | 720×1280@24.06 / 241f → 466×480@9.983 / 100f，预估 32.00 MiB | ✅ |
| 循环缝 | mean ≤2.0 且 ≤2% → PASS；2× 内 → WARN | 主体 **2.63 / 2.77%** | ⚠️ WARN（可用） |
| 同代一致性 | mean ≤4.0 且 ≤5% → PASS | 主体 **2.13 / 1.16%** | ✅ PASS |
| 最佳循环点 | 无更优裁剪点 | **f0** | ✅ 无需重排 |
| 剪影 | 同代应逐项相同 | y0=60 / h=1220 / boxcx=359.5 / fg 67.9% | ✅ 同代同取景 |
| 入库体积 | ≤35 MiB | **24.83 MiB** | ✅ |
| 清单校验 | 100 帧 + manifest 一致 | `--verify` **6/6 [OK]** | ✅ |
| 进度 | — | `--status` **6/9**（受影响状态 3 个） | ✅ |
| UI 证据 | 10 张板图 | `ui_board_speaking_low.png` 已是真素材 | ✅ |
| 回归 | 0 失败 | pytest **205 passed** | ✅ |

---

## 五、涉及文件清单

**素材（入库）**：`assets/avatar/talking_low/`（100 帧 PNG + `meta.json` + `manifest.json`，24.83 MiB）

**证据**：`evidence_shots/keyframes/talking_low_t00.00_f000000.png`、`_t05.03_f000121.png`、`_t09.98_f000240.png`、
`talking_low_tl_t*.png`（7 帧）、`talking_low_loop_check.png`、`talking_low_ref_check.png`、
`talking_low_loop_best_f000000.png`、两者 `*_view.jpg`；`evidence_shots/ui_board_speaking_low.png`（真素材版）、
`ui_board_speaking{,_low}_view.jpg`、`compare_speaking_vs_low_view.jpg`

**归档（只读）**：`D:\share\项目开发\桌面AI桌宠\assets\videos\talking_low.mp4`（sha256 `1663ecc4…adc7`）

**文档（本轮同步）**：本文件（+ 同名 `.docx`）、`assets/avatar/README.md`（状态表 + 体积核算）、
`docs/玩偶素材Seedance提示词包_技术记录.md`（§3.1 状态、§11 执行结果）、`docs/素材排队应对方案.md`（6/9 + §五.8 实测）、
`docs/ui_consistency_checklist.md`（§五 证据说明）

---

## 六、下一步

1. **素材队列剩 3 条**（提示词均已在提示词包）：`emo_puzzled`（§4.5，CAMERA_LOST）→ `idle_offline`（§4.6，NETWORK_LOST）
   → `emo_sad`（§4.7，ERROR）⇒ 每条按本文同一 SOP 走（干跑 → 关键帧 → 同代互比 → 入库 → 验证）。
2. 三条到齐后（**9/9**）：10 态**观感验收**（表达性 6 逐条目检；系统·故障 4 只判"不白屏 + 语义正确"）
   → 板端 `frames.rgb565` 打包（bg `#16202B`，预算 ≈70 MiB，不入库）→ LVGL 按 `ui_consistency_checklist.md` **V2.1** 核对。
3. **仍待决策 3 项**（沿用）：① `--ref` 基准是否统一换"新代首帧"（本轮已按新代执行，建议正式固化为 SOP）；
   ② `idle_normal` 是否 `--force` 重生成 waist-up；③ 是否做 alpha 包围盒归一化（≈半天）。

