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

- [ ] **P0 · D1 已按接收端口径定调（不再需要拍板）**：基础类“无眨眼”要求**不因“未决默认允许”改变**；
      自然眨眼仅作**独立素材选项**；仅当用户明确要求“零闭眼”时才改 `aura\docs\说话素材自然度提示词_v3.json`（设计变更）
- [~] **P1 · E4 锚点前移/加密 —— 已暂停（历史路线）**：用户判定“继续生成收益有限”，转“复用现有素材”
      - 参考（仅恢复时用）：`probe_v3_guide_mid.py --frame-idx 20 --dry-run` → `drift_metrics_v2.py` 同表 + 1 次拼图看图
- [~] **P2 · E2 口径更正归档（勿再误引）**：手/前臂**二维**代理 **E1 10.57 → E2 11.82**（9.08→11.01 只是 x 分量）；
      **不得引用“锚点只约束其后区间”**（接收端分段复算：0–61 段轮廓同样改善）
- [~] **P2b · E3 前置核查 —— 已暂停（历史路线）**：恢复前先查 `MiniMaxH3FunControlNetApply` 的 `model_patch` 权重是否存在
- [ ] **P6 · 当前主线 A｜复用线**（`deliverables\2026-10-06_avatar_reuse\`，139 文件）：先解决真实窗口**平均 20.69 fps**
      与 11 次跨状态切换 **>100 ms（最长 206.52 ms）**；再接真实音频/眨眼；复核跨状态接缝与正式配置接入
      - 入口 `run_reuse_script.bat`；先读 `流畅度复核与保留意见_2026-10-06.md`、`板端移植交接_2026-10-06.md`（正式板端合同仍 1.2）
- [x] **P7 · 声音线已定稿**（`deliverables\2026-10-06_voice_audition\`，49 文件）：**「柔亮俏皮」已选定并固定参考**（2026-10-06）
      - 进度：① 12 段试听 → ② 少女候选（选定「柔亮俏皮」）→ ③ 固定参考＋四场景 → ④ 47.27 秒音画演示**已获用户接受**（8771）→ ⑤ 任意台词＋独立眨眼（8772，**待用户观看确认**）
      - 关键记录：`2026-10-06_voice_selected_soft_young/selection.json`、`2026-10-06_voice_script_sync/acceptance.json`（ACCEPTED_BY_USER）、`2026-10-06_voice_blink/final_verification.json`（531＋34 PASS）；待办：音素口型（现为振幅同步）、麦克风入口、正式 UI 与板端接入（合同 1.2）
- [ ] **P3 · T3 抠像**：输出到候选目录，**严禁写** `aura\assets`
- [ ] **P4 · T4 体检 + 四对首尾接缝目测**（`check_naturalness_candidate.py`）
- [ ] **P5 · T5 `hold / enter / exit`**：被参考图 `doll_green_9x16_hold.png` 阻塞

## 未做/边界（不要谎报）

- E2 **未**逐帧目测全部 124 帧（仅 3 个全身时点 + 11 个眼区帧）
- 本轮**未**生成任何可交付素材、**未**改提示词、**未**碰 `aura\assets`、**未**改 `batch_001\raw\`
