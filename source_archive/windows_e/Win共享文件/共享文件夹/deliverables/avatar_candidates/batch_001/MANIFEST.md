# batch_001 说话素材清单与索引（v3 自然度批次）

> **接收端当前结论**：12条源产物均通过指纹和结构复核，原数值结果可复现；但本轮首/峰/末全身、脸及双手目测已全部完成，**12条均未通过固定姿势口型循环要求**。见 [`review_20261005/验收结论与下一步.md`](review_20261005/验收结论与下一步.md)。所有API图实际引用 `doll_green_9x16.png`；下方 `_rest.png` 名称缺少输入指纹支持，须向生成机核实。旧表为生成与数值清单，不是视觉放行清单；同名DOCX仍是历史版本。

> 生成人：Cline（2026-10-06 会话）｜生成窗口：2026-10-06 07:07–07:49（单条 175–245 s，串行）
> 素材来源：ComfyUI API 工作流（`workflows\*_api.json`），参考图＝ `doll_green_9x16.png`
> （**2026-10-06 实测更正**：全盘仅此一个 `doll_green*` 文件，`1,061,336 B`，SHA256 `FBE9EFA3BE94A2C1359C93C50A28273788789323D886364EB1EB3C06119E8780`；`_rest.png`/`_hold.png` **均不存在**）
> 状态：**12/12 结构通过、数值体检无 FAIL/无 FLAGGED**；**视觉全脸目测仅完成 1 条（基线）**，其余 9 条待办
> 交接文件：同目录 `HANDOVER.md`（下一个 AI 请先读它）

## 1. 目录结构

| 目录/文件 | 内容 | 说明 |
|---|---|---|
| `raw\<id>_s<seed>\` | 每条 39 帧 PNG（`000000.png`…`000038.png`）+ `meta.json` | **素材本体**，864×1536，共 12×40=480 文件 / 708.3 MB |
| `workflows\` | 12 份 `*_api.json` + `workflow_manifest.json` | 构建产物，**未提交过**时 status 为 BUILT_NOT_SUBMITTED…；提交后以本目录为准复现 |
| `logs\` | `submit_*.log` | 批量提交运行日志（可重入） |
| `qc\` | `qc_*.json` / `qc_*.txt` | 自动体检留档；**正式一份＝`qc_20261006_075517.json`** |
| `reports\` | `qc_report_20261006_0755.txt`（结构+数值）、`blink_report_20261006_0758.txt`（眨眼判定）、`batch_run_*.log`、`blink4_run_*.log` | 由 `%TEMP%` 归入的项目内证据 |
| `tools\` | `v3_batch_submit.py`、`v3_run.ps1`、`v3_next_pipeline.ps1`、`v3_qc.py`、`blink_probe_v1_pixel_diff.py`、`blink_probe_v2_iris.py`、`eye_contact_sheet.py` | 本批全部脚本，只读素材、不写 `aura\assets` |
| `evidence\` | `eye_contact_sheet_blink_rest_s421001.png`、`eye_contact_sheet_all12.png` | 眼区逐帧接触表（看图判"何时闭眼"用） |
| `run_manifest.json` | 提交清单（id/seed/prompt_id/status） | 由 `v3_batch_submit.py` 维护 |

## 2. 12 条素材（结构 + 校验）

| # | 资产 id | seed | 帧 | 大小 | 状态 | 耗时(s) | prompt_id(前8) | api SHA256(前16) |
|---|---|---|---|---|---|---|---|---|
| 1 | talking_calm_blink_v3_s421001 | 421001 | 39 | 59.2 MB | success | 230.2 | c4dfa299 | C212E249F449449F |
| 2 | talking_calm_blink_v3_s421002 | 421002 | 39 | 58.7 MB | success | 245.3 | f7864d9c | 440868DC6388975A |
| 3 | talking_calm_blink_v3_s421003 | 421003 | 39 | 59.1 MB | success | 245.3 | 8a11a7f4 | 64A6A78525FBF869 |
| 4 | talking_calm_rest_v3_s421001 | 421001 | 39 | 59.3 MB | success | 225.5 | 7c1cc520 | 9F624FE49A2FBF22 |
| 5 | talking_calm_rest_v3_s421002 | 421002 | 39 | 58.7 MB | success | 190.9 | 82cc850e | 6855BF470268CFC6 |
| 6 | talking_calm_rest_v3_s421003 | 421003 | 39 | 59.1 MB | success | 195.4 | 38eb2dad | 2BAC6C929D7AA2A5 |
| 7 | talking_low_rest_v3_s421001 | 421001 | 39 | 59.1 MB | success | 215.6 | ab9457b8 | F540CB65A43EA0FE |
| 8 | talking_low_rest_v3_s421002 | 421002 | 39 | 58.7 MB | success | 195.3 | e38b7a46 | D4EFD7E2DB7A852C |
| 9 | talking_low_rest_v3_s421003 | 421003 | 39 | 59.1 MB | success | 190.5 | 26cfdc2c | 29000B3F9AB1CDE5 |
| 10 | talking_warm_rest_v3_s421001 | 421001 | 39 | 59.4 MB | success | 215.6 | fdcccaf8 | 5329EAFA67CE6793 |
| 11 | talking_warm_rest_v3_s421002 | 421002 | 39 | 58.8 MB | success | 175.4 | 0077c769 | 6D3A2FFEE9351990 |
| 12 | talking_warm_rest_v3_s421003 | 421003 | 39 | 59.1 MB | success | 180.5 | 23f31196 | 20C1C3EBB7D543BE |

合计：**480 文件 / 708.3 MB**。`api SHA256` 可由 `Get-FileHash -Algorithm SHA256` 重算比对（12 份与 `meta.json.api_graph_sha256` 完全一致）。

## 3. 数值体检摘要（正式留档见 `qc\qc_20261006_075517.json`）

| 资产 | peak@帧 | last | tail | 资产 | peak@帧 | last | tail |
|---|---|---|---|---|---|---|---|
| blink_s421001 | 16.401 @f13 | 1.781 | 0.109 | low_rest_s421001 | 15.412 @f19 | 1.860 | 0.121 |
| blink_s421002 | 15.032 @f16 | 1.567 | 0.104 | low_rest_s421002 | 15.713 @f15 | 1.711 | 0.109 |
| blink_s421003 | 16.068 @f17 | 1.775 | 0.110 | low_rest_s421003 | 17.269 @f14 | 1.959 | 0.113 |
| rest_s421001 | 16.164 @f13 | 1.783 | 0.110 | warm_rest_s421001 | 17.844 @f13 | 1.802 | 0.101 |
| rest_s421002 | 16.877 @f14 | 1.737 | 0.103 | warm_rest_s421002 | 18.404 @f13 | 1.707 | 0.093 |
| rest_s421003 | 18.971 @f13 | 2.070 | 0.109 | warm_rest_s421003 | 19.769 @f12 | 1.940 | 0.098 |

`status=STRUCTURE_VALID_REQUIRES_VISUAL_REVIEW`、`FAIL_IDS=-`、`FLAGGED_IDS=-`；
**该状态仅代表"结构 + 运动分布合格"，不等于视觉通过。**

## 4. 复现/校验命令（只读）

```powershell
$py = 'D:\share、\项目开发\FPGA-amd自主命题赛道\aura\.venv\Scripts\python.exe'
$b  = 'D:\share、\项目开发\FPGA-amd自主命题赛道\deliverables\avatar_candidates\batch_001'
# 结构 + 数值体检（可重入，只读素材）
powershell -NoProfile -File "$b\tools\v3_next_pipeline.ps1"
# 只做数值体检
& $py -B "$b\tools\v3_qc.py" --batch-root $b --out "$b\qc"
# 眨眼量化（眼区蓝瞳占比，判 BLINK/WEAK/NONE）
& $py -B "$b\tools\blink_probe_v2_iris.py" --batch-root $b --out "$b\reports\blink_report_rerun.txt"
# 眼区逐帧接触表（供一次目测）
& $py -B "$b\tools\eye_contact_sheet.py" --batch-root $b --items talking_calm_blink_v3_s421001 talking_calm_rest_v3_s421001 --out "$b\evidence\eye_contact_sheet_blink_rest_s421001.png"
```

## 5. 未完成 / 下一步（详见 `HANDOVER.md`）

1. 其余 9 条**全脸目测**未做；2. `rest` 是否必须"全程不闭眼"**待用户拍板**（关乎提示词改动）；
3. 抠像 → `check_naturalness_candidate.py` → 四对首尾接缝目测未开始；4. `hold/enter/exit_v3` 三类因缺
`doll_green_9x16_hold.png` 仍未构建；5. 提交到 git 需在带仓库的环境执行。
