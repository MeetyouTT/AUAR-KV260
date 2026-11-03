# todo —— avatar_candidates（AURA 说话素材）当前任务清单

> 续接方式（`cost control` 四.2“一窗一模块”）：新窗口开场白
> `@.cline-handover.md @avatar_candidates\todo.md → 只做 <某一项>`。
> 项目根：`D:\share、\项目开发\FPGA-amd自主命题赛道\deliverables\avatar_candidates\`

## 已完成（2026-10-06 本轮）

- [x] 漂移度量 v2 更正（区域/命名）→ `batch_002_probe\review\drift_report_v2.txt`
- [x] `drift_metrics_v2.py`：`--label-base/--label-probe` + `--spec`（中文路径走 JSON，绕开 PS 参数编码）
- [x] E2 中间帧锚定（`MiniMaxH3AddGuide frame_idx=62`）跑完 → `batch_003_guide_probe\raw\e2_rest_s421001_L124_guide62\`
- [x] E2 对照 A（vs 39 帧基线）/ B（vs E1，单变量）→ `batch_003_guide_probe\review\drift_report_e2_*.txt`
- [x] 眨眼变长探针 → `review\blink_report_e1_vs_e2.txt` + `blink_e1_e2.json`
- [x] 拼图看图 2 次并落档 → `review\sheet_a_endpoints.png`、`sheet_b_eye_band.png`、`review\看图记录_E2抽帧与眼区_2026-10-06.md`
- [x] 文档回填 → `batch_003_guide_probe\README.md` §6、`batch_001\HANDOVER.md` §11-7（md+docx）

## 待办（按优先级）

- [ ] **P0 · 等用户拍板 D1（＝ T2）**：`rest` 是否允许“自然眨眼”（现证据：E1/E2 均含前段闭眼 f44–47；E2 后段 f82–86 已恢复睁眼）
      → 拍板前**不改** `aura\docs\说话素材自然度提示词_v3.json`；**选项 A＝写入验收说明且不重跑（未决前的安全默认）；B＝改词重跑（设计变更）**
- [ ] **P1 · E4 锚点前移/加密（决策 D2 选项①，推荐先于 E3）**（单变量）
      - 依据：E2 峰值帧 f17/f19（手）、f26（胸/横带）**全部早于锚点 f62**，且手/前臂 ROI 反向变差 1.10–1.21×
      - 做法：`probe_v3_guide_mid.py --frame-idx 20`（或双锚 f20+f90），`--dry-run` 自证 diff 后提交
      - 验收：`drift_metrics_v2.py` 同表 + 1 次拼图看图（首/中/末 + 眼区）
- [ ] **P2 · E3 前置核查（决策 D2 选项②）**：`MiniMaxH3FunControlNetApply` 的 `model_patch` 权重本机是否存在（**未确认前不得开工**）
- [ ] **P3 · T3 抠像**：输出到候选目录，**严禁写** `aura\assets`
- [ ] **P4 · T4 体检 + 四对首尾接缝目测**（`check_naturalness_candidate.py`）
- [ ] **P5 · T5 `hold / enter / exit`**：被参考图 `doll_green_9x16_hold.png` 阻塞

## 未做/边界（不要谎报）

- E2 **未**逐帧目测全部 124 帧（仅 3 个全身时点 + 11 个眼区帧）
- 本轮**未**生成任何可交付素材、**未**改提示词、**未**碰 `aura\assets`、**未**改 `batch_001\raw\`
