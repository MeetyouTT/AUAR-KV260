# aura — AURA KV260 主仓（人3 / C 岗：玩偶 UI · 语音 · 音响）

> 本仓按 `Docs\amd_kv260_full_work_requirements_v3.md`（下称 **D5**）**§19.2 目录蓝图**建立；
> 首批内容由上游旧赛道工程 `wujing-lite` **复用引入**（团队 2026-09-26 拍板，D5 §6.1 / §23.2 的 W17-16、W17-21 均已 `[x]`）。
> 盘点与衔接过程见 `Docs\AURA_KV260_C岗玩偶与语音_复用清单与衔接行动_20261002.md`。

## 0. 当前开发进度与接手入口（2026-10-04）

**如果你是来接手的 AI / 开发者，请先读
[`docs/项目接手说明_AI_当前进度与待办.md`](docs/项目接手说明_AI_当前进度与待办.md)** —— 含：
当前进度、代码结构与数据流、**素材动作 SOP**、**待办清单（P0/P1/P2）**、验收约定、坑与禁忌、文档索引。

- 当前主题：**玩偶「生命感」**（潜动层 + 匀速化 + 三段式 + 打断衔接）；
  **播放侧已完成并接入生产层**（`qt_widgets` / `demo_stage` 共用同一份 `avatar_timing` 口径）；
  **素材侧待重制**（现素材无"保持段"，详见接手文档 §7）。
- 样品页：`docs/demo_alive/index.html`（双击即看，12 组动图对比）。
- 环境要点：本机**无系统 Python / 无 pytest / 无 PySide6** → 用 `aura\.venv\Scripts\python.exe`，
  实机效果看 `tools\demo_stage.py`（tkinter）。

## 1. 引入方式（可复现）

| 项 | 值 |
|---|---|
| 源 | `D:\share、\项目开发\FPGA语音助手开发\wujing-lite`（**只读，未改动上游任何文件**） |
| 脚本 | `tools\build_aura_repo.ps1`（纯 ASCII；`-Check` 预演 / `-Apply` 落盘 / `-IncludeHeavy` 含重件） |
| 本批范围 | 代码 + 合同 + 文档：**129 文件 / 3,335,727 B** |
| 完整性清单 | `tools\_aura_import_manifest.tsv`（129 行 = SHA256 + 字节 + 目标绝对路径） |
| 复现命令 | `powershell -NoProfile -ExecutionPolicy Bypass -File tools\build_aura_repo.ps1 -Source <wujing-lite> -Dest <aura> -Apply [-IncludeHeavy]` |

## 2. 已引入内容（源 → 目标 对照）

| 源（wujing-lite） | 目标（aura） | 文件 | 字节 |
|---|---|---:|---:|
| `board\runtime\*` | `board\runtime\` | 20 | 113,746 |
| `board\ui\*` | `board\interaction\` | 11 | 158,710 |
| `ui_spec\*` | `ui\` | 4 | 15,402 |
| `schemas\*` | `common\schemas\` | 3 | 5,552 |
| `tests\*` | `tests\` | 21 | 185,845 |
| `tools\*` | `scripts\` | 11 | 190,637 |
| `docs\*`（md + docx 成对） | `docs\` | 59 | 2,665,835 |

子目录实测：`board\runtime\{audio,dialogue_client,logging,mocks,validator}`、`board\interaction\{image,lvgl}`、`tests\data`、`docs\ui_draft`。

## 3. 未引入的重件（待确认后一次性搬入）

| 源 | 目标 | 文件 | 说明 |
|---|---|---:|---|
| `assets\avatar\*` | `ui\assets\avatar\` | ~606 | 玩偶态帧流（rgb565），**上游只有 6 个态**，其余 3 态见素材补做记录 |
| `models\*` | `models\` | ~39 | onnx 权重（含 KWS） |
| 合计 | — | 645 | 约 **454 MB** |

→ 追加 `-IncludeHeavy` 执行 `-Apply` 即搬入（D 盘内复制，预计 1–3 分钟）。

## 4. 与 D5 §19.2 蓝图对照

- **已建（已有内容）**：`board/runtime`、`board/interaction`、`ui/`、`common/schemas/`、`tests/`、`scripts/`、`docs/`
- **待建（尚无内容，由各 owner 产出后按蓝图补齐）**：
  `hardware/{rtl,sim,platform,constraints,hls}`、`board/{motion,vision,fusion}`、`host/{vlm,speech,identity,memory}`、
  `ui/views`、`config/{toolchain_lock.json,model_manifest.json,runtime.yaml,servo_calibration.yaml,direction_calibration.yaml}`、
  `models/{manifests,model_cards}`、`data/{calibration_manifest,test_manifest,golden}`、
  `tests/{rtl,vision,audio,motion,identity,dialogue,system}`（现为平铺，待归类）、`metrics/{raw,plots,environment}`、
  `artifacts/{hardware,models,release_manifest}`、`skill/README.md`

> 目录名与蓝图不同处仅 1 处：上游 `board/ui` → 蓝图 `board/interaction`（其余保持一致）。

## 5. 口径红线（施工前必读）

1. 玩偶状态字段**唯一**为 `runtime_state`，取值 **十态**：
   `IDLE / PRESENT / LISTENING / THINKING / SPEAKING / SPEAKING_LOW / CAMERA_LOST / NETWORK_LOST / CANCELLED / ERROR`
   定义见 `ui\ui_state.schema.json`。**不得**引入第二套命名（20 天执行计划 §C2 的 7 态属历史材料，已裁决以十态为准）。
2. 运动侧为 **6 态**（D5 §6.1），与玩偶十态**分属两个域、不共用字段名**；两者映射待写入 `Docs\AURA_KV260_无声源定位版_项目对齐登记_v1_0.md` §7。
3. 玩偶素材、UI 布局与设计令牌**原样沿用**：不重构、不改命名、不重排目录语义。
4. `scripts\` 与 `tests\` 中来自 PC 的延迟 / 性能结论（MockBoard、KWS 等）**不得当作板端指标**，必须在 KV260 + MCP01 实测后替换。
5. 音响路径为 **MCP01（USB 一体式音频）**；双麦 I2S、`audio_doa_ip`、T13/T14 已在本版本删除，不得作为依赖。

## 6. 验证方式

```powershell
# 文件数与清单行数应一致（129 = 129）
(Get-ChildItem -LiteralPath aura -Recurse -File).Count
(Get-Content -LiteralPath tools\_aura_import_manifest.tsv -Encoding UTF8).Count
# 抽查哈希（示例）
(Get-FileHash -LiteralPath aura\ui\ui_state.schema.json -Algorithm SHA256).Hash
```

## 7. 许可与模型卡

- 逐文件许可结论：`docs\LICENSE_MATRIX.md`（同名 docx 并存）
- KWS 模型卡：`docs\MODEL_CARD_KWS.md`（同名 docx 并存）→ 支撑 D5 §23.1 / W14-32
