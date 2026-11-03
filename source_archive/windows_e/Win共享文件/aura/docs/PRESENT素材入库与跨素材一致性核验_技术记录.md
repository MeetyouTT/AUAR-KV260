# 注视（PRESENT）素材入库与跨素材一致性核验 技术记录

> 日期：2026-09-12 ｜ 环境标签：PC / SIMULATED（帧序列入库；板端 LVGL 只复用产物）
> 关联：`docs/聆听素材入库与一致性核验_技术记录.md`（**单态增量 SOP 的母文档**）、
> `docs/素材排队应对方案.md`（排队期路线 + §四 SOP + §五.5 代次基准）、
> `assets/avatar/README.md` §二/§四/§五、`assets/avatar/idle_present/`、
> `ui_spec/ui_layout_spec.json` **1.1**（玩偶框 439×556、腰部以上口径）

## 一、背景与目标

排队期**第 2 条真素材**（注视 / PRESENT，即「抬头、注视」）到达。按母文档固化的**单态增量 SOP**
跑完「落位 → 核验 → 按定稿口径入库 → 出证据图 → 回归」。冻结口径不变：
满铺显示、**腰部以上 waist-up（裁掉下部 42%）**、入库长边 **480**、单素材预算 **35 MiB**、本轮只出 **PNG**。

本轮**额外产出**：发现并量化了跨素材一致性判据里的**「代次口径差」**现象（§2.3），
据此给出 `--ref` 基准图的更新建议（§3.2）——这是母文档里 `--ref` FAIL（16.59 / 38.99%）一直悬而未决的**统一解释**。

## 二、做了什么

### 2.1 素材落位（重命名 + 归档进桌宠素材库）

| 项 | 值 |
| --- | --- |
| 下载原文 | `C:\Users\ZhangHang\Downloads\jimeng-2026-09-12-5560-Vertical 9_16 portrait shot of @characte....mp4`（11,747,596 B） |
| 归档路径 | `D:\share\项目开发\桌面AI桌宠\assets\videos\idle_present.mp4` |
| 命名依据 | 素材名 = `avatar_assets.STATE_ASSET["PRESENT"]` = `idle_present`（`--state PRESENT` 自动映射，无需 `--name`） |
| 规格探测 | **720×1280 / 24.06 fps / 241 帧 / 10.02 s**（与 `idle_listening`、现役 `idle_normal` **完全同规格**，9:16 成立 → `crop_box` 只裁纵向的假设有效） |
| 源指纹 | `sha256=2C38F2D005BC3D847DF046EE050C7DCB00D3C416048D6577C63E57E2504C9429`（写入 `meta.json.source`） |
| 落位方式 | `Copy-Item`（**复制而非移动**）：下载目录原文保留（`Test-Path` 复核 = True） |

### 2.2 入库前关键帧核验（`tools/avatar_keyframes.py`）

```powershell
python tools\avatar_keyframes.py --src "D:\share\项目开发\桌面AI桌宠\assets\videos\idle_present.mp4" `
    --out-dir evidence_shots\keyframes --name idle_present --count 3 --check-loop --find-loop `
    --ref evidence_shots\avatar_ref_idle_normal_f000000.png
```

| 核验项 | 实测 | 判定 | 结论 |
| --- | --- | --- | --- |
| 循环缝 f0 vs f240 | 全图 mean 2.79 / p99 10.0 / max 35.3 / 差异 1.99%；**主体 mean 2.60 / 差异 2.57%**（主体占全图 **65.9%**） | ⚠️ WARN（阈值 ≤2.0 / ≤2%） | **优于** `idle_listening`（2.75 / 3.34%）→ 可用；差异热力仅衣褶/发丝抖动，无位移 |
| 跨素材一致性 vs **旧锚点图** | 全图 mean 13.35 / p99 120.7 / max 197.0 / 差异 28.12%；**主体 mean 16.69 / 差异 39.57%** | ❌ FAIL（阈值 ≤4.0 / ≤5%） | 见 §2.3 —— **不是素材缺陷** |
| 最佳循环点 `--find-loop` | f0（t=0.00s） | PASS | 全片最接近首帧者仍是 f0 → 无需裁剪重排（与 listening 一致） |

产物：`evidence_shots/keyframes/idle_present_{t00.00_f000000,t05.03_f000121,t09.98_f000240}.png` +
`idle_present_loop_check.png` + `idle_present_ref_check.png` + `idle_present_loop_best_f000000.png`。

### 2.3 判读 `--ref` FAIL：三联图 + 同代互比 → **代次口径差**

**① 三联图**（`idle_present_ref_check.png` = 首帧｜参考图｜差异热力×4）：
同一角色、同一绿幕、同一正面机位；差异热力呈**沿轮廓的等宽描边**（头发/衣袖/裙摆/面部轮廓），
**不是块状换装或换脸** ⇒ 典型**刚性错位（整体缩放 + 平移）**。若为外观不一致，热力会是**面积块状**。

**② 同代互比**（把基准换成同代已入库素材的首帧）：

```powershell
python tools\avatar_keyframes.py --src "D:\share\项目开发\桌面AI桌宠\assets\videos\idle_present.mp4" `
    --out-dir "%TEMP%\pres_vs_listen" --name pres_vs_listen --count 1 `
    --ref "evidence_shots\keyframes\idle_listening_t00.00_f000000.png"
```

| 结论性数字 | 数值 |
| --- | --- |
| `idle_present` vs **旧锚点图**（`idle_normal` 首帧） | 主体 mean **16.69** / 差异 **39.57%** → FAIL |
| `idle_listening` vs **旧锚点图** | 主体 mean **16.59** / 差异 **38.99%** → FAIL |
| `idle_present` vs **`idle_listening` 首帧** | 主体 mean **2.00** / 差异 **1.02%** → ✅ **PASS** |

**判读**：两条**同一代次**素材的偏差**几乎同值**（16.69 vs 16.59），且**彼此互为像素级同取景**（mean 2.00 ≈ 噪声级）；
主体占全图比例**也都是 65.9%**。

⇒ **根因 = 代次口径差**：从 `idle_listening` 起这一代（同一提示词包 + 同一张全幅锚点图 + 同渠道）
产出的素材，人物取景**整体比旧锚点图（`idle_normal` 那一代）近一档**，且在**同代各条之间高度稳定**。

⇒ **工程含义（好消息）**：9 态切换**不会跳**（同代素材彼此一致）；偏差是**基准图代次问题**，**不必重生成素材**。
`--ref` 报 FAIL 的阈值（mean ≤4.0）本身就隐含了「基准图口径必须与素材同代」这一前提。

### 2.4 按定稿口径入库

```powershell
python tools\prepare_avatar_frames.py --state PRESENT `
    --src "D:\share\项目开发\桌面AI桌宠\assets\videos\idle_present.mp4" `
    --framing waist-up --max-side 480 --budget-mb 35
```

产物 `assets/avatar/idle_present/`：

| 项 | 值 |
| --- | --- |
| 帧数 / 帧率 | **100 帧** / 9.98 fps（源 24.06 fps → 目标 10 fps 抽帧） |
| 入库尺寸 | **466×480**（waist-up + 长边 480） |
| 体积 | **23.62 MiB（247.7 KB/帧）**（工具预估 32.00 MiB → 实际比估值小 26%；预算 35 MiB → `[OK]`） |
| 抠像 | 桌宠 `python -m src.matting video … -m adaptive`，全分辨率 241 帧，**耗时 52.4 s**（`idle_listening` 为 57.8 s） |
| 中间目录 | `%TEMP%\wujing_avatar_prep\idle_present` **已自动清理**（原始素材未被修改/移动） |
| 校验 | `--verify` → `[OK] idle_present: 100 帧 / manifest 一致`（全部通过，exit 0） |

**几何链路（无插值放大）**：`720×1280` →(裁下部 42%)→ `720×742` →(长边 ≤480)→ **`466×480`**。
与 `idle_listening` **同尺寸、同帧数、同体积档（23.62 vs 23.85 MiB）** ⇒
**466×480 档可稳定按 ≈23.6~23.9 MiB/状态 核算**（9 态 ≈213 MiB PNG；板端 RGB565 ≈43.7 MiB/状态 → 9 态 ≈393 MiB）。

### 2.5 证据图重出

```powershell
python examples\run_ui.py --state PRESENT --screenshot evidence_shots\ui_board_present.png
python examples\run_ui.py --all-states
```

`ui_board_present.png` 目检：玩偶区 = **真素材帧序列**（腰部以上、底部对齐 + 28px 渐隐、玩偶框上方 80px 扩展位留空），
状态栏 `状态 -> PRESENT` / `场景事件: scene.person_enter` / `模式 DIALOGUE_LAN` —— 与合同 **1.1** 一致（通过）。
`--all-states` 重出 **9 张** `evidence_shots/ui_board_*.png`。

### 2.6 回归

```powershell
python -m pytest -q --junitxml=%TEMP%\pp_junit.xml
```

→ **tests=195 / failures=0 / errors=0 / skipped=0 / 4.95 s / EXIT=0**（"放入即生效"未破坏既有断言，无需改测试）。

## 三、关键决策与踩坑

### 3.1 判 `--ref` FAIL 的**三步判读法**（本轮固化）

1. **打开三联图**（`*_ref_check.png`）：**等宽描边** = 刚性错位（可消化）；**面积块状** = 外观不一致（需重生成）；
2. **跑同代互比**：`--ref <同代已入库素材首帧>` → PASS 即证明「素材彼此一致」，问题在基准代次；
3. **看主体占比**：本例两条都是 **65.9%**（同值）→ 进一步佐证同取景。

⇒ 三步过完才可判"可入库"，**单看 `--ref` 的数字会误杀素材**。

### 3.2 决策建议：`--ref` 基准图应改用**新代首帧**（**待用户确认**）

- **现状**：`--ref` 固定指向 `evidence_shots/avatar_ref_idle_normal_f000000.png`（**旧代**，`idle_normal` 那一代）。
- **问题**：新代素材对旧基准**必然 FAIL**（结构性问题，非个案），核验会持续报警并钝化注意力。
- **建议**：核验基准改为**新代首帧**（推荐 `evidence_shots/keyframes/idle_listening_t00.00_f000000.png`，
  或 `idle_normal` 按 waist-up 重生成后改用**重生成后的**首帧）；旧锚点图留作 **Seedance 首尾帧输入图**专用
  —— 二者**语义不同，不应共用一张**。
- **⚠️ 冻结项不变**：Seedance **首尾帧锚点图仍是那张全幅 720×1280 图**
  （与上游 `实体桌宠\…\refs\idle_normal_t00.00_f000000.png` sha256 相同），**不要换成 waist-up 裁切版**
  （否则模型按腰以上重构图，入库再裁 42% → 变胸口大特写）。本节建议**只改 `--ref` 核验基准**，不改生成用锚点图。

### 3.3 踩坑 · 本机 shell 会**杀掉前台长任务**（本轮最大时间损失）

- 症状：入库命令跑到 `65/241 帧…` 后日志出现 `Traceback … ^C`、产物目录为空 —— 因为**核验命令与入库命令先后跑在同一终端**，
  Cline 复用终端时打断了前一个前台进程；
- 更隐蔽：**`Start-Sleep` 轮询也会被杀**（终端一关就没），靠 sleep 等结果**永远等不到**；
- **解法（已实测）**：用 **`Start-Process` 脱离终端后台跑**，stdout/stderr 分文件重定向，PID 落盘：
  ```powershell
  $env:PYTHONIOENCODING='utf-8'
  Start-Process -FilePath 'python' -WorkingDirectory $wd `
    -ArgumentList @('tools\prepare_avatar_frames.py','--state','PRESENT','--src','<mp4>',
                    '--framing','waist-up','--max-side','480','--budget-mb','35') `
    -RedirectStandardOutput "$env:TEMP\pp_out.txt" -RedirectStandardError "$env:TEMP\pp_err.txt" `
    -PassThru -WindowStyle Hidden
  ```
  → 之后再跑别的命令**不会**影响它；轮询改为「**真命令 + 换新文件名快照**」（`Copy-Item log log_N.txt`，再读新文件）。
  本轮实测后台跑满 `241/241 帧…` → `(adaptive, 52.4 s)` → `[写入] 100 帧` → `[清理]`，全链路无中断。

### 3.4 踩坑 · `cmd /c` 里**嵌套引号会串味**

`cmd /c "set …&& python … --src "D:\路径\x.mp4" …"` 的内层引号会**提前闭合外层字符串**，
实测表现为参数**多出一个前导空格** → `[错误] --src 不存在:  D:\…\x.mp4`。
本工程素材路径**不含空格**（中文不影响）⇒ **直接不加引号**最稳。

### 3.5 踩坑 · `pytest -q` 重定向日志**会丢汇总行**

日志只留到 `[100%]` 进度点（连 `-Tail` 也读不到 `N passed`）。**取硬数字必须用 `--junitxml`**：
`testsuite … errors="0" failures="0" skipped="0" tests="195" time="4.948"`，并单独记录 `$LASTEXITCODE`。

### 3.6 与母文档一致的口径决策

- 单条素材**仍按定稿口径跑**（waist-up / 480 / 35 MiB），不"先将就 full"——否则 6 条齐了要全部重跑；
- **本轮只出 PNG**（RGB565 是**板端打包步骤**，届时一键再生且不入库；注意 `--budget-mb` 会把两格式**合计**计入，
  同开时预算给 ≈70 MiB）。

## 四、验证方式与结果（可复现）

```powershell
cd "D:\share\项目开发\FPGA语音助手开发\wujing-lite"
# ① 核验（旧基准）：循环缝 WARN / 一致性 FAIL（代次差）/ 最佳循环点 f0
python tools\avatar_keyframes.py --src "D:\share\项目开发\桌面AI桌宠\assets\videos\idle_present.mp4" `
    --out-dir evidence_shots\keyframes --name idle_present --count 3 --check-loop --find-loop `
    --ref evidence_shots\avatar_ref_idle_normal_f000000.png
# ② 同代互比（关键一步）：PASS（主体 mean 2.00 / 1.02%）
python tools\avatar_keyframes.py --src "D:\share\项目开发\桌面AI桌宠\assets\videos\idle_present.mp4" `
    --out-dir "$env:TEMP\pres_vs_listen" --name pres_vs_listen --count 1 `
    --ref evidence_shots\keyframes\idle_listening_t00.00_f000000.png
# ③ 入库 / ④ 校验 / ⑤ 状态 / ⑥ 证据图 / ⑦ 回归
python tools\prepare_avatar_frames.py --state PRESENT --src "D:\share\项目开发\桌面AI桌宠\assets\videos\idle_present.mp4" `
    --framing waist-up --max-side 480 --budget-mb 35
python tools\prepare_avatar_frames.py --verify      # 3 个素材全部 [OK]，exit 0
python tools\prepare_avatar_frames.py --status      # 3/8；idle_present = 100 帧 / 466x480 / waist-up / 23.6 MiB
python examples\run_ui.py --state PRESENT --screenshot evidence_shots\ui_board_present.png
python examples\run_ui.py --all-states
python -m pytest -q --junitxml=%TEMP%\pp_junit.xml # tests=195 / failures=0 / errors=0，EXIT=0
```

## 五、涉及文件清单

- **新增**：`assets/avatar/idle_present/`（`000000.png…000099.png` + `meta.json` + `manifest.json`）
- **新增**：`evidence_shots/keyframes/idle_present_{t00.00_f000000,t05.03_f000121,t09.98_f000240}.png`、
  `…_loop_check.png`、`…_ref_check.png`、`…_loop_best_f000000.png`
- **重出**：`evidence_shots/ui_board_present.png`（矢量回退 → 真素材）+ 9 张 `ui_board_*.png`
- **更新**：`assets/avatar/README.md`（状态表 PRESENT → ✅ 已入库 / §四 同口径复用实测 / §五 PRESENT 核验实测）、
  `docs/素材排队应对方案.md`（现状 **3/8** + §五.5 代次基准）、本文件（md + docx）
- **外部（桌宠工程，只增不改）**：`D:\share\项目开发\桌面AI桌宠\assets\videos\idle_present.mp4`（下载原文保留）

## 六、下一步

1. **（待确认）`--ref` 核验基准换新代首帧**（§3.2；改 1 处默认值 + 文档，约 10 min）；
2. **（待确认）`idle_normal` 按 waist-up / 480 / 35 MiB 重生成**（`--force`，约 2 min）——顺带解决其循环缝 FAIL（主体 mean 19.90）；
3. **（待确认）alpha 包围盒归一化**：把各态人物高度/中心对齐到同一口径，根治切态**轻微缩放跳变**（预估半天）；
4. **余 5 态到一条跑一条**：`idle_thinking` / `talking_normal` / `emo_puzzled` / `idle_offline` / `emo_sad`
   （提示词见 `docs/玩偶素材Seedance提示词包_技术记录.md`，SOP 见 `docs/素材排队应对方案.md` §四）；
5. **板端 RGB565 打包**：素材齐后出 `frames.rgb565`（底色 `#16202B`，预算 ≈70 MiB，**不入库**），
   按 `ui_consistency_checklist.md` V2.0（L1~L14）实现，验收后清理 `tools/ui_mock_draft.py`。
