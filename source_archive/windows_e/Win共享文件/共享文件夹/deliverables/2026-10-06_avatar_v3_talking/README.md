# 2026-10-06 说话素材 v3（batch_001）交付入口

> 接收端已完成后续复核：12条指纹与结构无误，数值可复现；全部12条首峰末目测因姿势/手位变化未通过，暂不接入。见 [最新验收与下一步](../avatar_candidates/batch_001/review_20261005/验收结论与下一步.md)。以下是生成机交付时的历史快照。

本日交付（本机镜像 `D:\share、\项目开发\FPGA-amd自主命题赛道\`）：

| 内容 | 位置 |
|---|---|
| **素材本体 + 证据 + 脚本 + 清单** | `..\avatar_candidates\batch_001\`（`raw\` 12×39 帧 / 708.3 MB） |
| **交接主文件（下一个 AI 从这里开始）** | `..\avatar_candidates\batch_001\HANDOVER.md` |
| 素材清单与校验（12 条 × sha256 / 指标） | `..\avatar_candidates\batch_001\MANIFEST.md` |
| 数值体检留档 | `..\avatar_candidates\batch_001\qc\qc_20261006_075517.json` |
| 眨眼专项判定表 | `..\avatar_candidates\batch_001\reports\blink_report_20261006_0758.txt` |
| 眼区接触表（看图证据） | `..\avatar_candidates\batch_001\evidence\` |
| 技术记录（A 镜像口径 + B 本批全过程） | `..\..\aura\docs\本机镜像同步与v3素材生成_2026-10-06.md`（+docx） |

**状态**：12/12 生成成功；结构 `raw_BAD=0`、数值 `FAIL_IDS=- / FLAGGED_IDS=-`；
眨眼专项已闭环（四类都有闭眼事件，`blink` 与 `rest` 无系统差异）；
**全脸目测仅完成基线 1 条 + 2 条眼区专项，其余 9 条待办**；
抠像/接缝验收未开始；`hold/enter/exit_v3` 因缺 `doll_green_9x16_hold.png` 未构建；
**本批未接入运行时（未写 `aura\assets`、未加 `--force`）**。

> 待用户拍板：`rest` 类是否必须"全程不闭眼"（影响 6 条验收结论）——详见 `HANDOVER.md` §5 T2。
