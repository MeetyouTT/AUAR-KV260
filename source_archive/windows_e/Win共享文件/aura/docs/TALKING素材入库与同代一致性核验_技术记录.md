# TALKING 素材入库与同代一致性核验 · 技术记录

> 日期：2026-09-12　|　素材：`talking_normal`（SPEAKING / 播报口型循环）　|　环境标签：PC · SIMULATED
> 上游规范：`assets/avatar/README.md` §三/§五、`docs/素材排队应对方案.md` §四（增量入库 SOP）、
> `docs/玩偶素材Seedance提示词包_技术记录.md` §4.4（本素材的提示词来源）
> 前序记录：`docs/聆听素材入库与一致性核验_技术记录.md`、`docs/PRESENT素材入库与跨素材一致性核验_技术记录.md`、
> `docs/THINKING素材入库与跨代一致性核验_技术记录.md`

---

## 一、背景与目标

第 4 条真素材（前三条：`idle_listening` / `idle_present` / `idle_thinking`）到齐，按已定稿口径入库并核验：

- **口径**：`--framing waist-up` + `--max-side 480` + `--budget-mb 35`（PNG）→ 预期入库 466×480 / 100 帧 / ≈23.5 MiB；
- **核验**：`--check-loop`（循环缝）+ `--find-loop`（最佳循环点）+ `--ref`（跨素材一致性）；
- **动作验收**：SPEAKING 必须是**真的在说话**（口型张合 + 自然手势），不能是站着不动；
- **收口**：`--verify` / `--status` / `run_ui.py --all-states` 证据图 / `pytest` 回归 / 文档留档。

本轮要回答的**新判据问题**（由上一轮遗留）：上两轮的结论是「新代素材 vs **旧锚点**必然 FAIL」，
thinking 又撞上「**同代互比也 FAIL**」，于是把第 ③ 步换成剪影度量。本轮 `talking_normal` 则**首次出现
「同代互比 PASS」**，正好用来把代次判读从「三步」升级为**可闭环的证据链**（见 §三.1）。

---

## 二、本次做了什么

### 2.1 素材落位与规格探测（源文件只读）

| 项 | 值 |
|---|---|
| 下载源 | `C:\Users\ZhangHang\Downloads\jimeng-2026-09-12-6011-Vertical 9_16 portrait shot of @characte....mp4` |
| 源体积 | **18,990,222 B**（比前三条 12.2~16.4 MB 大，故抠像更慢，见 §2.5） |
| sha256 | `7A92325F9E49534D8D0ECD312B758E8B201F51FC4F0AAF84CA22478E3E9B26AC` |
| 归档位 | `D:\share\项目开发\桌面AI桌宠\assets\videos\talking_normal.mp4`（`Copy-Item -Force`，逐字节一致，**不移动原件**） |
| 规格 | **720×1280 @24.06fps / 241 帧 / 10.02 s**（与 listening / present / thinking **完全同规格**） |

`--dry-run` 预检（入库前先看规格与预算，不产生任何文件）：

```
入库规格: 长边≤480 / 10.0 fps / 格式 png / 单素材预算 35.0 MiB / 取景 waist-up / 抠像 adaptive
取景 waist-up：裁掉下部 42%（保留上部 58%）：720x1280 → 720x742（宽度不变）
源 720x1280 @24.06fps / 241 帧  →  规格 466x480 @9.98fps / 100 帧（像素量 1/4.1）
体积预估: PNG 32.00 MiB → 合计 32.00 MiB（预算 35.0 MiB）  [OK]
```

### 2.2 入库前核验（`tools/avatar_keyframes.py`）

```
--src ...\talking_normal.mp4 --out-dir evidence_shots\keyframes --name talking_normal \
  --count 3 --check-loop --find-loop --ref evidence_shots\avatar_ref_idle_normal_f000000.png
```

| 核验项 | 主体区 mean | 差异像素(>8) | 判定 |
|---|---|---|---|
| 循环缝 f0 vs f240（`--check-loop`） | **2.90** | **4.21%** | ❌ FAIL（**临界**，见 §三.2） |
| 跨素材 vs 旧锚点（`--ref`） | **25.88** | 62.54% | ❌ FAIL（**代次口径差**，预期内） |
| 最佳循环点（`--find-loop`） | 0.00 | 0.00% | ✅ PASS（最佳帧就是 **f0**） |
| 同代互比 vs `idle_thinking` 首帧 | **2.04** | 1.06% | ✅ **PASS**（首例！） |
| 同代互比 vs `idle_listening` 首帧 | **16.65** | 39.99% | ❌ FAIL（**一整个代差**） |

- 关键帧产物：`talking_normal_t00.00_f000000.png` / `_t05.03_f000121.png` / `_t09.98_f000240.png`；
  三联图 `talking_normal_loop_check.png`、`talking_normal_ref_check.png`、`talking_normal_loop_best*`。
- `--find-loop` 最佳帧 = **f0** ⇒ 不需要按 f0..fN 裁剪重排（与 present / thinking 相同）。
- 判据阈值出处（`avatar_keyframes.verdict`）：`mean≤限制 且 frac≤限制 → PASS`；`2 倍阈值内 → WARN`；否则 `FAIL`。
  循环缝限制 = mean 2.0 / frac 2%（即 WARN 上限 4.0 / 4%）；跨素材限制 = mean 4.0 / frac 5%。

### 2.3 动作时间线判读（`--count 7` + contact sheet）

`--count 7` 抽帧后用 Pillow 拼 4 列缩略图（7 格 / 1120×996），一次目检看清动作结构：

| 时刻 | 帧 | 动作 |
|---|---|---|
| t00.00 | f000000 | 双侧站姿、双手垂在宽袖里、**抿嘴微笑**（起手） |
| t01.66 | f000040 | **双拳举起到胸前**、张嘴笑（说话起势） |
| t03.33 | f000080 | 双拳举起、**张嘴大笑**（口型最大） |
| t05.03 | f000121 | **右手张开**（挥手式）、张嘴说话（口型中等） |
| t06.69 | f000161 | 双拳举起、张嘴 |
| t08.35 | f000201 | 拳头置于胸前、张嘴笑 |
| t09.98 | f000240 | 回到起手站姿、**抿嘴微笑**（与首帧同姿态） |

⇒ 素材结构 = **站姿 → 举手握拳/挥手 ×5 段 → 回站姿**，**口型全程张合、手势丰富、首尾帧同姿态**
⇒ 作为 SPEAKING 循环素材**语义正确**（不是「站着不动」的伪 talking，也不是一闪而过的口型）。

### 2.4 剪影度量（绿幕容差 60，与 `avatar_keyframes` 同口径）

| 首帧 | 非绿幕占比 | x0 | x1 | 头顶 y0 | 人物高 h | h/H | 包围盒中心 | 真实质心 |
|---|---|---|---|---|---|---|---|---|
| `idle_listening` | 65.9% | 0 | 719 | 72 | 1208 | 0.944 | 359.5 | 369.8 |
| `idle_present` | 65.9% | 0 | 719 | 72 | 1208 | 0.944 | 359.5 | 369.7 |
| `idle_thinking` | 67.9% | 0 | 719 | **60** | **1220** | **0.953** | 359.5 | **369.0** |
| **`talking_normal` f0** | **68.0%** | 0 | 719 | **60** | **1220** | **0.953** | 359.5 | **369.0** |
| `talking_normal` f240（末帧） | 68.0% | 0 | 719 | **60** | **1220** | **0.953** | 359.5 | 369.1 |

**读法（本轮三条硬结论）**：

1. **`talking_normal` f0 与 `idle_thinking` f0 逐项相同**（y0=60 / h=1220 / boxcx=359.5 / 真质心 369.0）
   ⇒ 两者**同代、同取景、同姿态**；这与 §2.2 的「同代互比 mean 2.04 PASS」**互相印证**；
2. `talking_normal` 与 `idle_listening`/`idle_present` 的差 = **头顶高 12px（+1.0%）+ 非绿幕 +2.1pp**
   ⇒ 与上轮 thinking 对 listening 的差**完全同值** ⇒ 属**代次口径差**（新代人物近一档、发丝更蓬），非缺陷；
3. **f0 vs f240 剪影逐项相同**（只有真质心差 0.1px）⇒ 循环缝的差异**不在轮廓**，见 §2.5/§三.2。

> 口径澄清：前几轮文档表格里的 `cx` 实为**包围盒中心** `(x0+x1)/2`（恒为 359.5，因左右均触边）；
> 本轮脚本同时输出**真实质心**（前景像素质心的列均值），两者含义不同，勿混用（见 §三.3）。

### 2.5 循环缝差异定位（量化「差异到底在哪」）

对 f0 与 f240 做差异掩膜（通道最大差 > 8）定位：

| 指标 | 值 |
|---|---|
| 差异像素 | 89,502 / 921,600 = **9.71%**（含 <8 的淡差时 主体 mean 仅 2.90） |
| 差异 bbox | x[0,719] y[0,1279]（**铺满全图**） |
| 分带占比 | 头部 14.1% / 面颈 13.1% / 胸腹 37.6% / 58%H 以下 35.2% |

⇒ 差异**不是集中在口型区**，而是**全身均匀分布的轮廓描边**（热力图呈发丝/袖口/腰带/裙摆的细线），
与「剪影逐项相同」一致 ⇒ 定性为**整体轻微微动**（说话时重心与衣摆的自然摆动），**非姿态/结构跳变**。

### 2.6 单态入库（长任务后台跑）

```
python tools/prepare_avatar_frames.py --state SPEAKING \
  --src "D:\share\项目开发\桌面AI桌宠\assets\videos\talking_normal.mp4" \
  --framing waist-up --max-side 480 --budget-mb 35
```

- 抠像：`src.matting video … -m adaptive`，**241 帧 / 55.2 s**（present 52.4 s / listening 57.8 s / thinking 51.4 s，同量级）；
- 取景：`waist-up` 裁掉下部 42%（720×1280 → 720×742）→ 长边 ≤480 缩放 → **入库 466×480 @9.983fps / 100 帧**；
- 体积：工具预估 32.00 MiB（保守系数）→ **实测 100 帧合计 24,678,088 B = 23.52 MiB**（≈246.8 KB/帧），`[OK]`；
- 产物：`assets/avatar/talking_normal/000000.png…000099.png` + `meta.json` + `manifest.json`（100 帧逐帧 sha256）；
  `meta.json` 记 `spec.framing=waist-up` / `crop_bottom_ratio=0.42` / `matte_mode=adaptive`，
  `source.sha256` = 归档 mp4 指纹（即上文 7A92325F…）；
- 原始 mp4 **只被读取**，临时全分辨率帧（`%TEMP%\wujing_avatar_prep\talking_normal`）用完即删。

### 2.7 校验、证据图与回归

| 动作 | 结果 |
|---|---|
| `prepare_avatar_frames.py --verify` | **5 素材全 [OK]**：`idle_listening` / `idle_normal` / `idle_present` / `idle_thinking` / **`talking_normal`** |
| `prepare_avatar_frames.py --status` | **5 / 8 已入库**；缺 `emo_puzzled` / `idle_offline` / `emo_sad` |
| `examples/run_ui.py --all-states` | 9 张板端证据图**全部重出**（含 `ui_board_speaking.png`） |
| 目检 `ui_board_speaking.png` | 右侧玩偶面板渲染**真 talking 素材**（张嘴说话 + 举手势、waist-up、抠像干净、与面板底色融合自然），状态标签「播报 [SPEAKING]」正确 |
| `python -m pytest -q --junitxml=…` | **tests=195 / failures=0 / errors=0 / skipped=0 / 5.48 s** |

### 2.8 文档更新

- `assets/avatar/README.md`：状态表 `SPEAKING` → ✅（466×480 / waist-up / 100 帧 / 23.5 MiB）+ 新增本素材实测块；
- `docs/素材排队应对方案.md`：头部计数 **4/8 → 5/8**、缺失清单收敛为 3 条、§五 新增第 7 条「循环缝临界 FAIL 的判读」；
- 本文件（技术记录）+ 同名 `.docx`；
- `.cline-handover.md`（工作区根 `b站评论成分分析工具`）整体覆盖为最新进度。

---

## 三、关键修复细节与技术决策

### 3.1 代次判读：从「三步」定稿为**可闭环的五步证据链**

| 步 | 手段 | 判据 | 本轮实测 |
|---|---|---|---|
| ① | **三联图**（`*_ref_check.png` / `*_loop_check.png`） | 差异是**沿轮廓描边**（可消化）还是**块状换装/换脸**（不可用） | 旧锚点=块状；循环缝=描边 |
| ② | **同代互比**（`--ref` 指向同代素材首帧） | mean≈2.0 → 同代；mean≈16.7 → 跨代 | vs thinking **2.04 PASS**；vs listening **16.65** |
| ③ | **剪影度量**（x0/x1/y0/h/cx/非绿幕） | 左右触边 + 底部触底 + 头顶差 ≤1~2% → **刚性口径差**，非外观不一致 | f0 与 thinking **逐项相同** |
| ④ | **动作时间线**（7 帧 contact sheet） | 动作内容正确 + 首尾同姿态 + 目标动作占足够时长 | 口型张合 + 手势，首尾同姿态 |
| ⑤ | **差异定位**（差异掩膜分带统计 + 热力图） | 差异均匀铺满（微动）vs 集中单区（结构变化） | 铺满全图 = 轻微微动 |

> **本轮新增第 ⑤ 步**：thinking 那轮只到第 ④ 步就下结论，循环缝 FAIL 归因「淡轮廓」靠的是目检；
> 本轮补了**数字化的差异定位**（分带占比 14.1/13.1/37.6/35.2%），把「淡轮廓」变成可复算的证据。

**闭环逻辑（为什么能确信 talking 与 thinking 同代）**：

```
talking vs thinking  = 2.04  (PASS)   ⇒ 二者像素级同取景
talking vs listening = 16.65
thinking vs listening = 16.73         ⇒ 三者关系自洽：talking ≈ thinking ≠ listening
talking vs 旧锚点     = 25.88
thinking vs 旧锚点    = 25.97         ⇒ 对旧锚点的差也几乎同值 ⇒ 同代确认
```

### 3.2 循环缝「临界 FAIL」的判读（本轮核心结论）

`talking_normal` 循环缝 = **mean 2.90 / frac 4.21%**，判 FAIL。但：

- `verdict()` 是「mean 与 frac **同时**落在 2 倍阈值内才 WARN」。本例 mean 2.90 ≤ 4.0 ✅，
  而 frac 4.21% **只比 4% 上限高 0.21pp** ❌ ⇒ **临界 FAIL**；
- 幅度上与前三条真素材（2.60 / 2.75 / 2.64）**同档**，没有量级变化；
- 剪影逐项相同（§2.4）+ 差异全身均匀（§2.5）+ `--find-loop` 最佳点就是 f0 ⇒
  **不是姿态跳变、不是尺度跳变、也裁不出更好的循环点**；
- 结论：**判为可入库**。理由一句话：*「这是说话动画固有的全身微动，幅度与已入库素材同档，
  唯一越界的是 0.21pp 的差异像素比例」*。

> 反向校验：若把 f0 换成别的帧当循环起点，`--find-loop` 会给出更小差值——但它指出最佳点是 **f0**，
> 说明「0.21pp 越界」**无法通过裁剪消除**，属素材本身属性，只能靠重生成提示词改善。

### 3.3 剪影度量 `cx` 的口径澄清（修正历史记录的表意）

前几轮记录表里的 `cx=359.5` 实为**包围盒中心** `(x0+x1)/2`——因为头发出框使 x0=0 / x1=719，
它恒等于画面中心，**信息量很低**；本轮改为同时给出：

- `boxcx` = (x0+x1)/2 → 359.5（与前几轮文档口径一致，便于纵向比对）；
- `cx` = **前景像素质心**的列均值 → talking/thinking **369.0**、listening 369.8、present 369.7
  （反映人物**重心略偏画面右侧 ≈9px**，对「取景是否一致」更有判据意义）。

⇒ 后续记录请**两个都写**，避免「看起来都对、其实不是一个东西」。

### 3.4 沿用并再次验证的踩坑（别再撞）

1. **`--src` 是必填**（`prepare_avatar_frames.py::_targets()` 直接 `SystemExit`，stderr 仅 45 B）——
   本轮第一条命令就是 `--dry-run`，**先带齐 `--state`+`--src`**，避免秒退；
2. **长任务必须后台跑**：抠像 55.2 s，用
   `Start-Process -WorkingDirectory <项目> -RedirectStandardOutput … -RedirectStandardError … -PassThru`，
   再用**读日志文件**轮询（本轮日志涨到 243 行 = 241 帧 + 2 行表头，即可判断抠像结束）；
3. **`pytest -q` 重定向丢汇总行** ⇒ 用 `--junitxml` 读 `testsuite` 属性（本轮 tests=195 / failures=0）；
4. **大图读取被 `[media omitted]` 拒** ⇒ 先用 Pillow 缩到宽 760 + JPEG(q=82) 再读；一批帧改拼 contact sheet；
5. **中文路径与 `cv2.VideoCapture`/`imread` 有坑**：本工具链已内置 `np.fromfile + cv2.imdecode` 规避读图问题；
   规格探测建议走 `%TEMP%` ASCII 副本更稳。

### 3.5 待用户拍板的 3 项（本轮复核后结论未变）

1. `--ref` 核验基准是否**换成新代首帧**（否则每条新素材都报 FAIL 噪声；本轮已有更强的「同代互比」替代手段）；
2. `idle_normal` 是否按 waist-up/480/35 MiB `--force` 重生成（现为 180×320/full，循环缝 FAIL mean 19.90）；
3. 是否做 **alpha 包围盒归一化**（可根治跨代/跨条 1% 尺度跳变，预估半天）。

---

## 四、验证方式与结果（可复现）

```powershell
cd "D:\share\项目开发\FPGA语音助手开发\wujing-lite"

# ⓪ 素材落位（原始素材只读：归档副本，不移动原件）
Copy-Item -LiteralPath "C:\Users\ZhangHang\Downloads\jimeng-2026-09-12-6011-...mp4" `
    -Destination "D:\share\项目开发\桌面AI桌宠\assets\videos\talking_normal.mp4" -Force
#    → 18,990,222 B / sha256 7A92325F…26AC（与源逐字节一致）

# ① 入库预检（不产生文件）
python tools/prepare_avatar_frames.py --state SPEAKING `
    --src "D:\share\项目开发\桌面AI桌宠\assets\videos\talking_normal.mp4" `
    --framing waist-up --max-side 480 --budget-mb 35 --dry-run
#    → 720x1280@24.06fps/241 帧 → 466x480@9.98fps/100 帧，预估 32.00 MiB [OK]

# ② 入库前核验（循环缝 / 最佳循环点 / 旧锚点）
python tools/avatar_keyframes.py --src "...\talking_normal.mp4" `
    --out-dir evidence_shots\keyframes --name talking_normal --count 3 --check-loop --find-loop `
    --ref evidence_shots\avatar_ref_idle_normal_f000000.png
#    → 循环缝 2.90/4.21% FAIL；--find-loop = f0 PASS；vs 旧锚点 25.88/62.54% FAIL

# ③ 同代互比（本轮两发：同代 PASS、上代 FAIL，用来锁代次）
python tools/avatar_keyframes.py --src "...\talking_normal.mp4" `
    --out-dir "%TEMP%\talk_vs_think" --name talk_vs_think --count 1 `
    --ref evidence_shots\keyframes\idle_thinking_t00.00_f000000.png     # → 2.04 / 1.06% PASS
python tools/avatar_keyframes.py --src "...\talking_normal.mp4" `
    --out-dir "%TEMP%\talk_vs_listen" --name talk_vs_listen --count 1 `
    --ref evidence_shots\keyframes\idle_listening_t00.00_f000000.png    # → 16.65 / 39.99% FAIL

# ④ 动作时间线（7 帧 contact sheet 目检）
python tools/avatar_keyframes.py --src "...\talking_normal.mp4" `
    --out-dir evidence_shots\keyframes --name talking_normal_tl --count 7

# ⑤ 单态入库（务必带 --src；长任务用 Start-Process 后台跑）
python tools/prepare_avatar_frames.py --state SPEAKING `
    --src "D:\share\项目开发\桌面AI桌宠\assets\videos\talking_normal.mp4" `
    --framing waist-up --max-side 480 --budget-mb 35
#    → 466x480 / 100 帧 / 实测 23.52 MiB（预估 32.00）；抠像 adaptive 55.2 s

# ⑥ 校验 + 证据图 + 回归
python tools/prepare_avatar_frames.py --verify      # → 5 素材全 [OK]
python tools/prepare_avatar_frames.py --status      # → 5 / 8
python examples/run_ui.py --all-states              # → 9 张 ui_board_*.png 重出
python -m pytest -q --junitxml="%TEMP%\tk_junit2.xml"   # → tests=195 / failures=0 / 5.48s
```

| 验收项 | 判据 | 实测 | 结果 |
|---|---|---|---|
| 分辨率/比例 | 720×1280（9:16） | 720×1280 | ✅ |
| 首尾帧循环 | 主体 mean ≤2.0 且 frac ≤2% | 2.90 / 4.21% | ⚠️ **临界 FAIL，判为可入库**（§3.2） |
| 最佳循环点 | 越接近 f0 越好 | f0 | ✅ |
| 动作正确性 | 口型张合 + 手势，首尾同姿态 | 7 帧时间线全部符合 | ✅ |
| 同代一致性 | 同代互比 mean≈2 | vs thinking 2.04 PASS | ✅ |
| 入库口径 | waist-up / ≤480 / ≤35 MiB | 466×480 / 23.52 MiB | ✅ |
| 清单一致性 | `--verify` 全 [OK] | 5/5 [OK] | ✅ |
| 回归 | 全绿 | 195 passed | ✅ |

---

## 五、涉及文件清单

**新增（本项目 `wujing-lite`）**

- `assets/avatar/talking_normal/`：`000000.png…000099.png`（100 帧）+ `meta.json` + `manifest.json`（24,678,088 B）
- `evidence_shots/keyframes/talking_normal_t00.00_f000000.png`、`_t05.03_f000121.png`、`_t09.98_f000240.png`
- `evidence_shots/keyframes/talking_normal_loop_check.png`、`talking_normal_ref_check.png`、`talking_normal_loop_best*`
- `evidence_shots/keyframes/talking_normal_tl_t*.png`（7 帧时间线）
- `evidence_shots/ui_board_speaking.png`（及同批 8 张 `ui_board_*.png` 重出）
- `docs/TALKING素材入库与同代一致性核验_技术记录.md` / 同名 `.docx`

**修改**

- `assets/avatar/README.md`（SPEAKING → ✅ + 实测块）
- `docs/素材排队应对方案.md`（5/8 计数 + §五.7 循环缝临界 FAIL 判读）
- `<工作区根>\b站评论成分分析工具\.cline-handover.md`（整体覆盖）

**只读（未修改 / 未移动）**

- `D:\share\项目开发\桌面AI桌宠\assets\videos\talking_normal.mp4`（归档副本；下载原件仍在 `Downloads`）
- `evidence_shots/avatar_ref_idle_normal_f000000.png`（旧代锚点，**冻结不换**）

---

## 六、下一步

1. **等第 5~7 条素材**：`emo_puzzled`（CAMERA_LOST）/ `idle_offline`（NETWORK_LOST）/ `emo_sad`（ERROR），
   提示词见 `docs/玩偶素材Seedance提示词包_技术记录.md` §4.5~§4.7；到齐后按本文件 §四 SOP 各走一遍；
2. **3 项待确认**（§3.5）：`--ref` 基准换代 / `idle_normal --force` 重生成 / alpha 包围盒归一化；
3. **观感验收**：目前 5/8（含 1 条口径落后的 `idle_normal`），建议至少 7/8 后再做 9 态观感验收
   （跨代 1% 尺度差 + 表情差需在整组切换时一并目检）；
4. **8/8 齐后**：板端 `frames.rgb565` 打包（底色 `#16202B`，`--budget-mb ≈70`，产物不入库）
   → 按 `docs/ui_consistency_checklist.md` V2.0（L1~L14）落 LVGL → 验收后删 `tools/ui_mock_draft.py`。
