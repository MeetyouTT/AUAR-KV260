# THINKING 素材入库与跨代一致性核验 · 技术记录

> 日期：2026-09-12　|　素材：`idle_thinking`（THINKING / 托腮思考）　|　环境标签：PC · SIMULATED
> 上游规范：`assets/avatar/README.md` §三/§五、`docs/素材排队应对方案.md` §四（增量入库 SOP）、
> `docs/玩偶素材Seedance提示词包_技术记录.md` §4.3（本素材的提示词来源）
> 前序记录：`docs/聆听素材入库与一致性核验_技术记录.md`、`docs/PRESENT素材入库与跨素材一致性核验_技术记录.md`

---

## 一、背景与目标

第 3 条真素材（前两条：`idle_listening` / `idle_present`）到齐，按已定稿口径逐个入库并核验：

- **口径**：`--framing waist-up` + `--max-side 480` + `--budget-mb 35`（PNG）→ 预期入库 466×480 / 100 帧 / ≈23.5 MiB；
- **核验**：`--check-loop`（循环缝）+ `--find-loop`（最佳循环点）+ `--ref`（跨素材一致性）；
- **动作验收**：THINKING 必须真的是「托腮思考、视线左上」，不能只是站着；
- **收口**：`--verify` / `--status` / `run_ui.py --all-states` 证据图 / `pytest` 回归 / 文档留档。

本轮额外要回答一个**上轮遗留的判据问题**：上轮结论是「新代素材对**旧锚点**必然 FAIL（结构性）」，
那么**如果同代互比也 FAIL**，该怎么判？——本轮 `idle_thinking` 正好撞上这个情况（见 §三.1/§三.2）。

---

## 二、本次做了什么

### 2.1 素材落位与规格探测（源文件只读）

| 项 | 值 |
|---|---|
| 下载源 | `C:\Users\ZhangHang\Downloads\jimeng-2026-09-12-5646-Vertical 9_16 portrait shot of @characte....mp4` |
| 源体积 / mtime | **13,296,953 B** / 2026-09-12 01:31:36 |
| sha256 | `A4F12AAA2BF021F91F686CF616C8E0BE5ECD543A091AFA56FEC840679E0A5DA1` |
| 归档位 | `D:\share\项目开发\桌面AI桌宠\assets\videos\idle_thinking.mp4`（`Copy-Item -Force`，字节数一致，**不移动原件**） |
| 规格 | **720×1280 @24.06fps / 241 帧 / 10.02 s**（与 listening / present **完全同规格**） |

> 规格探测用 OpenCV 读**临时 ASCII 路径副本**（`%TEMP%\tk_probe.mp4`），避开中文路径在 `VideoCapture` 上的不确定性。

### 2.2 入库前核验（`tools/avatar_keyframes.py`）

```
--src ...\idle_thinking.mp4 --out-dir evidence_shots\keyframes --name idle_thinking \
  --count 3 --check-loop --find-loop --ref evidence_shots\avatar_ref_idle_normal_f000000.png
```

| 核验项 | 主体区 mean | 差异像素(>8) | 判定 |
|---|---|---|---|
| 循环缝 f0 vs f240（`--check-loop`） | **2.64** | **2.70%** | ⚠️ WARN（阈值 mean≤2.0 且 frac≤2%） |
| 跨素材 vs 旧锚点（`--ref`） | **25.97** | 63.56% | ❌ FAIL |
| 最佳循环点（`--find-loop`） | 0.00 | 0.00% | ✅ PASS（最佳帧就是 **f0**） |
| 同代互比 vs `idle_listening` 首帧 | **16.73** | 40.51% | ❌ FAIL（见 §三.2） |

- 循环缝 WARN 与 `idle_present`（2.60 / 2.57%）**同档**，优于 `idle_listening`（2.75 / 3.34%），目检三联图
  `evidence_shots/keyframes/idle_thinking_loop_check.png` 差异热力只有**淡轮廓** ⇒ 循环可用。
- `--find-loop` 最佳帧 = f0 ⇒ **不需要按 f0..fN 裁剪重排**（与 present 相同）。
- 关键帧产物：`idle_thinking_t00.00_f000000.png` / `_t05.03_f000121.png` / `_t09.98_f000240.png`，
  三联图 `idle_thinking_loop_check.png`、`idle_thinking_ref_check.png`。

### 2.3 动作时间线判读（抽 7 帧拼图，**本轮新增的质检手法**）

`--count 7` 抽帧后用 Pillow 拼成 4 列缩略 contact sheet（`%TEMP%\tk_timeline.png`，7 格 / 560×532），
一次目检即可看清动作结构（**省上下文**：不必逐张读完 7 张 720×1280 大图）：

| 时刻 | 帧 | 动作 |
|---|---|---|
| t00.00 | f000000 | 双侧站姿，双手垂在宽袖里，张嘴微笑（**起手**） |
| t01.66 | f000040 | **已托腮**（右手出袖、指尖轻抵下巴） |
| t03.33 / t05.03 / t06.69 | f000080 / f000121 / f000161 | **托腮保持**（视线左上、头微偏） |
| t08.35 | f000201 | 手开始收回 |
| t09.98 | f000240 | 回到起手站姿（**与首帧同姿态**） |

⇒ 素材结构 = **起手 1.7s → 托腮保持 ≈6.6s（约 66% 时长）→ 收手 1.7s**，
**首尾帧同姿态** ⇒ 作为 THINKING 循环素材成立，且托腮是主体状态（不是一闪而过）。

### 2.4 剪影度量（**本轮新增的量化判读**）

把「跨素材 FAIL」区分为**刚性错位（可消化）**还是**外观/尺度不一致（要重生成）**，
只靠三联图目检有主观性，故补一张数字表（绿幕容差 60，与 `avatar_keyframes` 同口径）：

| 首帧 | 非绿幕占比 | 头顶 y0 | 人物高 h | h/H | 质心 cx | 底部 |
|---|---|---|---|---|---|---|
| `idle_listening` | 65.9% | 72 | 1208 | 0.944 | 359.5 | 触底 1279 |
| `idle_normal`（旧锚点同源） | 63.9% | 84 | 1196 | 0.934 | 359.5 | 触底 1279 |
| `idle_present` | 65.9% | 72 | 1208 | 0.944 | 359.5 | 触底 1279 |
| **`idle_thinking`** | **67.9%** | **60** | **1220** | **0.953** | 359.5 | 触底 1279 |
| `idle_thinking` 托腮帧 f121 | 61.6% | 48 | 1232 | 0.963 | 366.5（头偏） | 触底 1279 |

**读法**：四者都**左右触边**（x0=0 / x1=719，头发出框）+ **质心正中对齐**（cx=359.5）+ **底部同触底**
⇒ 机位/取景一致；thinking 只比 listening **头顶高 12 px（+1.0%）**、非绿幕占比 +2.0pp（呆毛更高、发丝更蓬）
⇒ **近同取景的轻微尺度差**，**不是换装、不是换机位、不是整体位移**。

> 该表中 `idle_normal`（180×320 / full 入库版之外的**源素材首帧**）头顶比新代低 12 px，
> 印证了上轮「新代人物比旧锚点近一档」的**代次口径差**结论。

### 2.5 单态入库（工具跑在后台）

```
python tools/prepare_avatar_frames.py --state THINKING \
  --src "D:\share\项目开发\桌面AI桌宠\assets\videos\idle_thinking.mp4" \
  --framing waist-up --max-side 480 --budget-mb 35
```

- 抠像：`src.matting video … -m adaptive`，**241 帧 / 51.4 s**（与 present 52.4 s 同量级）；
- 取景：`waist-up` 裁掉下部 42%（720×1280 → 720×742）→ 长边 ≤480 缩放 → **入库 466×480 @9.98fps / 100 帧**；
- 体积：预估 32.00 MiB（工具保守系数）→ **实测 24,637,373 B = 23.50 MiB**，**246.4 KB/帧**，`[OK]`（预算 35 MiB）；
- 产物：`assets/avatar/idle_thinking/000000.png…000099.png` + `meta.json` + `manifest.json`（100 帧逐帧 sha256）；
- 原始 mp4 **只被读取**（`meta.json.source` 记 sha256），临时全分辨率帧用完即删。

### 2.6 校验、证据图与回归

| 动作 | 结果 |
|---|---|
| `prepare_avatar_frames.py --verify` | **4 素材全 [OK]**：`idle_listening` / `idle_normal` / `idle_present` / **`idle_thinking`（100 帧 / manifest 一致）** |
| `prepare_avatar_frames.py --status` | **4 / 8 已入库**；缺 `talking_normal` / `emo_puzzled` / `idle_offline` / `emo_sad` |
| `examples/run_ui.py --all-states --out-dir evidence_shots` | 9 张板端证据图**全部重出**（含 `ui_board_thinking.png`） |
| 目检 `ui_board_thinking.png` | 右侧玩偶面板渲染**托腮素材**（waist-up、抠像干净、与面板底色融合自然），状态标签「思考 [THINKING]」正确 |
| `python -m pytest -q --junitxml=…` | **tests=195 / failures=0 / errors=0 / skipped=0 / 5.39 s** |

### 2.7 文档更新

- `assets/avatar/README.md`：状态表 `THINKING` → ✅（466×480 / waist-up / 100 帧 / 23.5 MiB）+ 新增本素材实测块；
- `docs/素材排队应对方案.md`：头部计数 **3/8 → 4/8**、缺失清单收敛为 4 条、§五 新增第 6 条「同代互比也 FAIL 的判读」；
- 本文件（技术记录）+ 同名 `.docx`；
- `.cline-handover.md`（工作区根 `b站评论成分分析工具`）整体覆盖为最新进度。

---

## 三、关键修复细节与技术决策

### 3.1 「代次判读三步法」推广为**四步**

上轮固化的三步是：① 三联图看**等宽描边 vs 块状** → ② 同代互比 → ③ 看主体占比。
本轮 same-generation 互比**也 FAIL**，于是把第 ③ 步换成**剪影度量**（更硬）：

1. **三联图**（`*_ref_check.png`）：差异是**沿轮廓的描边**（可消化）还是**块状换装/换脸**（不可用）；
2. **同代互比**：`--ref` 指向**同代已入库素材首帧**（本次用 `evidence_shots/keyframes/idle_listening_t00.00_f000000.png`）；
   mean ≈2.0 ⇒ 同代；mean ≈16.7 ⇒ **跨代**（或姿态本就不同，见 §三.2）；
3. **剪影度量**（本轮新增，判「刚性错位 vs 尺度/外观差」）：`x0/x1/头顶 y0/人物高 h/质心 cx/非绿幕占比`；
   左右都触边 + 质心对齐 + 底部同触底 + 头顶差 ≤ 人物高的 1~2% ⇒ **可消化**；
4. **动作时间线目检**（本轮新增）：抽 7 帧拼 contact sheet，确认**动作内容正确 + 首尾帧同姿态 + 目标动作占足够时长**。

### 3.2 同代互比 FAIL 不等于素材缺陷（本轮核心结论）

`idle_thinking` 首帧 vs `idle_listening` 首帧 主体 mean=**16.73 / 40.51%**，看着很吓人，实为两个**必然差异**叠加：

- **姿态本就不同**：thinking 的**首帧是「起手站姿」**（素材结构见 §2.3），而 listening 的首帧是「正视站姿」。
  两个素材的**首帧不是同一姿势**，本来就不可像素级互比——**只有"同类姿态首帧"之间的互比才有判据意义**；
- **锚点图又换代**：thinking 首帧是**张嘴笑 + 呆毛更高 + 发丝更蓬**的一版（§2.4 头顶 +12 px），
  说明本次即梦生成用的**首帧锚点图与 listening/present 那次不同**，整体差异 ≈ 一个完整代差（16.7 ≈ 上轮的 16.6）。

⇒ 判据修正：**互比基准必须"同姿势且同代"**；不满足时**不能**用 mean 判 FAIL，改看**剪影度量**（§2.4）
与**动作时间线**（§2.3）。本素材两项均通过 ⇒ **可入库**。

### 3.3 「首帧是站姿」是双刃剑（一个必须记下的设计取舍）

- **好处**：切到 THINKING 时画面从**站姿**起手，与 IDLE/PRESENT 系的站姿首帧接近 ⇒ **切态不跳大小**；
- **代价**：每 10 s 循环会「放下手 → 再抬起」，托腮约占 66% 时长；如果希望「切过去立刻托腮」，
  需在 Seedance 提示词里把动作改成**起始即托腮、保持中段微动**（首帧锚点图也得换成托腮版）。
- **决策**：本轮**接受现状**（首帧站姿与切态稳定性的收益更大），若用户希望「立刻托腮」再重生成。

### 3.4 踩坑：`--src` 是**必填**（SOP 示例容易漏）

首次启动入库用了 `--state THINKING --framing waist-up --max-side 480 --budget-mb 35`，
进程**秒退**且 stdout 为空、stderr 仅 45 B —— 原因是 `prepare_avatar_frames.py::_targets()`：

```python
if not args.src:
    raise SystemExit("需要 --src（原始绿幕 mp4 或已抠好的帧目录）")
```

`--state` 只负责**把状态映射成素材名**，**不会**自动去 `桌面AI桌宠\assets\videos\` 找同名 mp4。
⇒ **SOP 里 `--state` 与 `--src` 必须成对出现**（`docs/素材排队应对方案.md` §四 的示例本身是对的，是我首跑漏写）。

### 3.5 踩坑：大图读取会被限流（`media omitted`）

`read_files` 读 720×1280 / 1024×600 的 PNG 时常返回 `[media omitted: invalid or exceeds size limit]`，
与文件"是否真的很大"关系不大，更像是**单次响应体总量**触发上限（同一张图单独读能进、与长文本一起读就被剔）。
⇒ 目检大图时按需**先缩图**：`PIL` 缩到宽 **760 px** 并转 **JPEG(q=82)** 再读；检查一批帧时改用 contact sheet。

### 3.6 长任务仍必须后台跑（沿用上轮结论）

抠像 51.4 s，前台 `Start-Process … -Wait` / `Start-Sleep` 会被"新命令复用终端"打断，
故一律：`Start-Process -FilePath python -WorkingDirectory <项目> -ArgumentList @(...) -RedirectStandardOutput <log> -RedirectStandardError <err> -PassThru`；
轮询用**读日志文件**（`read_files`）而非等终端输出。

### 3.7 待用户拍板的 3 项（本轮复核后结论未变）

1. `--ref` 核验基准是否**换成新代首帧**（否则每条新素材都报 FAIL 噪声）；
2. `idle_normal` 是否按 waist-up/480/35 MiB `--force` 重生成（现为 180×320/full，循环缝 FAIL mean 19.90）；
3. 是否做 **alpha 包围盒归一化**（可根治跨代/跨条 1% 尺度跳变，预估半天）。

---


## 四、验证方式与结果（可复现）

```powershell
cd "D:\share\项目开发\FPGA语音助手开发\wujing-lite"

# ① 规格探测（ASCII 临时副本，避开中文路径不确定性）
#    → 720x1280 @24.06fps / 241 帧 / 10.02 s

# ② 入库前核验（循环缝 / 最佳循环点 / 跨素材一致性）
python tools/avatar_keyframes.py --src "D:\share\项目开发\桌面AI桌宠\assets\videos\idle_thinking.mp4" `
    --out-dir evidence_shots\keyframes --name idle_thinking --count 3 --check-loop --find-loop `
    --ref evidence_shots\avatar_ref_idle_normal_f000000.png
#    → 循环缝 主体 mean 2.64 / 2.70% ⚠️WARN；--find-loop = f0 PASS；vs 旧锚点 FAIL(25.97/63.56%)

# ③ 同代互比（基准必须"同代"；本轮用于确认是跨代而非缺陷）
python tools/avatar_keyframes.py --src "D:\share\项目开发\桌面AI桌宠\assets\videos\idle_thinking.mp4" `
    --out-dir "%TEMP%\think_vs_listen" --name think_vs_listen --count 1 `
    --ref evidence_shots\keyframes\idle_listening_t00.00_f000000.png
#    → 主体 mean 16.73 / 40.51% FAIL ⇒ 转 §2.4 剪影度量判读

# ④ 动作时间线（7 帧 contact sheet，目检动作结构）
python tools/avatar_keyframes.py --src "...\idle_thinking.mp4" `
    --out-dir evidence_shots\keyframes --name idle_thinking_tl --count 7
#    → 站姿(f0) → 已托腮(f40) → 保持(f80/f121/f161) → 收手(f201) → 站姿(f240)

# ⑤ 单态入库（务必带 --src；长任务用 Start-Process 后台跑）
python tools/prepare_avatar_frames.py --state THINKING `
    --src "D:\share\项目开发\桌面AI桌宠\assets\videos\idle_thinking.mp4" `
    --framing waist-up --max-side 480 --budget-mb 35
#    → 466x480 / 100 帧 / 实测 23.50 MiB（预估 32.00）

# ⑥ 校验 + 证据图 + 回归
python tools/prepare_avatar_frames.py --verify      # → 4 素材全 [OK]
python tools/prepare_avatar_frames.py --status      # → 4 / 8
python examples/run_ui.py --all-states              # → 9 张 ui_board_*.png 重出
python -m pytest -q --junitxml="%TEMP%\tk_junit.xml"  # → 195 passed / 0 failed / 5.39s
```

| 验收项 | 判据 | 实测 | 结果 |
|---|---|---|---|
| 分辨率/比例 | 720×1280（9:16） | 720×1280 | ✅ |
| 首尾帧循环 | 主体 mean ≤2.0 且 frac ≤2% | 2.64 / 2.70% | ⚠️ WARN（可接受，优于 listening） |
| 最佳循环点 | 越接近 f0 越好 | f0 | ✅ |
| 动作正确性 | 托腮 + 视线左上 | 托腮保持 ≈6.6s / 66% | ✅ |
| 入库口径 | waist-up / ≤480 / ≤35 MiB | 466×480 / 23.50 MiB | ✅ |
| 清单一致性 | `--verify` 全 [OK] | 4/4 [OK] | ✅ |
| 回归 | 全绿 | 195 passed | ✅ |

---

## 五、涉及文件清单

**新增（本项目 `wujing-lite`）**

- `assets/avatar/idle_thinking/`：`000000.png…000099.png`（100 帧）+ `meta.json` + `manifest.json`（24,637,373 B 帧合计）
- `evidence_shots/keyframes/idle_thinking_t00.00_f000000.png`、`_t05.03_f000121.png`、`_t09.98_f000240.png`
- `evidence_shots/keyframes/idle_thinking_loop_check.png`、`idle_thinking_ref_check.png`、`idle_thinking_loop_best*`
- `evidence_shots/keyframes/idle_thinking_tl_t*.png`（7 帧时间线）
- `evidence_shots/ui_board_thinking.png`（及同批 8 张 `ui_board_*.png` 重出）
- `docs/THINKING素材入库与跨代一致性核验_技术记录.md` / 同名 `.docx`

**修改**

- `assets/avatar/README.md`（THINKING → ✅ + 实测块）
- `docs/素材排队应对方案.md`（4/8 计数 + §五.6 同代互比 FAIL 判读）
- `<工作区根>\b站评论成分分析工具\.cline-handover.md`（整体覆盖）

**只读（未修改/未移动）**

- `D:\share\项目开发\桌面AI桌宠\assets\videos\idle_thinking.mp4`（归档副本；下载原件仍在 `Downloads`）
- `evidence_shots/avatar_ref_idle_normal_f000000.png`（旧代锚点，**冻结不换**）

---

## 六、下一步

1. **等第 4 条素材**：`talking_normal`（SPEAKING / 口型循环，提示词见提示词包 §4.4），到齐后按本文件 §四 SOP 走一遍；
2. **3 项待确认**（§3.7）：`--ref` 基准换代 / `idle_normal --force` 重生成 / alpha 包围盒归一化；
3. **余 3 态**：`emo_puzzled`（CAMERA_LOST）、`idle_offline`（NETWORK_LOST）、`emo_sad`（ERROR）；
4. **8/8 齐后**：板端 `frames.rgb565` 打包（底色 `#16202B`，`--budget-mb ≈70`，产物不入库）
   → 按 `docs/ui_consistency_checklist.md` V2.0（L1~L14）落 LVGL → 验收后删 `tools/ui_mock_draft.py`。

