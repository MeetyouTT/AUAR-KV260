# aura — AURA KV260 主仓（人3 / C 岗：玩偶 UI · 语音 · 音响）

## 最新：下巴边缘修复（2026-10-08）

五套独立口型已保护下巴／脸颊边缘，151 帧下巴区域改变像素降为 0，550 项回归通过。默认临时剧本与实时演示均已应用；旧移机包需合并修复补丁。详见 [修复说明](../deliverables/2026-10-08_chin_fix/README.md)。

## 最新：汐蓝实时交互基础（2026-10-06）

DeepSeek 鲸鱼娘现名为“汐蓝”。双击 `tools/run_demo_stage.bat` 启动真实桌面素材／音频演示，浏览器同步入口 <http://127.0.0.1:8773/>；支持输入台词、三档表情、点头／摇头／惊讶／疑惑、独立眨眼、暂停和打断。四段新名台词已缓存，移机后无需语音模型即可体验。对话模型按用户安排留给另一台电脑，移机包默认关闭对话；源目录已开启的配置和后续语气优化记录均保留，本次未调用对话服务。547 项回归通过，最近 20,000 次桌面采样最长提交间隔 60.48ms、无超过 100ms 的间隔；实际设备暂停／恢复和打断通过，具体证据与移机限制见交接。

接手先读[汐蓝移机交接](../deliverables/2026-10-06_xilan_live/移机交接_汐蓝实时演示.md)；当前实际验证见同目录 `latest_verification.json`。旧“小光”参考转写、试听及已接受剧本保留历史原件，不能直接改声线参考中的精确转写。下文为历史进度。

## 最新：任意台词与独立眨眼（2026-10-06）

网页 <http://127.0.0.1:8772/> 已支持输入新台词，用选定“柔亮俏皮”声线在本机生成、验证缓存、暂停／重播／打断；生成等待、说话和结束后的待机都独立眨眼。三档五套现有嘴部随音强平滑开合，打断从最后实际开合程度收口。六套眼部复用现有素材，嘴部／身体及原透明通道检查通过；完整回归531项、专项34项通过，桌面和浏览器实际验证见[语音与独立眨眼交接](../deliverables/2026-10-06_voice_blink/语音与独立眨眼交接.md)及[最终验证](../deliverables/2026-10-06_voice_blink/final_verification.json)。

双击 `tools/run_demo_script.bat` 默认播放独立眨眼有声剧本；新台词输入在网页提供。用 `tools/run_demo_script_accepted.bat` 或8771查看已接受基线；参考声线、接受记录及旧剧本音频保留。新版本待用户观看确认。当前为PC非流式生成与音强口型，麦克风入口／具体音素／正式UI和板端仍需后续接入。下文旧进度作为历史基线阅读。

## 当前临时剧本：真实语音与口型（2026-10-06）

**用户已确认当前版可以接受，作为后续工作的演示基线。** 选择记录见[演示接受记录](../deliverables/2026-10-06_voice_script_sync/acceptance.json)。

选定“柔亮俏皮”已用于47.27秒完整演出：问候、解释长句、点头后兴奋、安慰，以及中途打断。双击 `tools/run_demo_script.bat` 启动有声版本；原66秒无声验收使用 `tools/run_demo_script_silent.bat`，原素材对照保留。音频样本是演出时间主轴，较长停顿会平滑收口；当前仍是发声活动同步，尚未具体音素对嘴。PC演出素材预加载后，超过100ms的提交间隔从11次降为0，最长约191→24ms；完整回归516项及专项19项通过，实际演出最终IDLE，无状态错误或拒绝。正式板端缓存策略仍待设备预算验证。

浏览器观看入口为 <http://127.0.0.1:8771/>，支持暂停、重播、场景跳转；网页使用同一剧本／播放核心提前缓存的画面。验证结果、源码职责和板端接入建议见[音画接入与后续交接](../deliverables/2026-10-06_voice_script_sync/音画接入与后续交接.md)。

## 当前选定声线：柔亮俏皮（2026-10-06）

用户已选择“柔亮俏皮”为小光当前声线。已用所选原始音频建立固定参考，并用同一参考生成日常问候、解释长句、兴奋、低落与安慰四段；24 kHz 单声道文件的格式、哈希、电平与削波检查通过。独立试听入口为 <http://127.0.0.1:8770/>。生成方法、精确参考、模型版本与限制见[柔亮俏皮固定声线与后续接入](../deliverables/2026-10-06_voice_selected_soft_young/柔亮俏皮固定声线与后续接入.md)。用户随后授权继续，四段已接入上一节临时剧本，正式板端接入仍待验。

## 少女声线第二轮：2026-10-06

针对第一轮“声音仍过于成熟”的反馈，已完成“清脆元气”“柔亮俏皮”两款 VoiceDesign 短样及同台词 Vivian 对照。试听入口为 <http://127.0.0.1:8769/>；三段音频检查通过，生成原件、提示词、模型版本与哈希见[少女声线重做与交接](../deliverables/2026-10-06_voice_design_young/少女声线重做与交接.md)。用户随后选择“柔亮俏皮”；本节保留候选过程，当前状态以上一节为准。

## 新增声音试听：2026-10-06

用户最新偏好为清亮活泼、具有游戏少女角色感。已完成 Vivian、Serena、现有 Kokoro 中文女声的 12 段同台词对照，保留原件和音量近似对齐版，音频检查通过。浏览器试听入口为 <http://127.0.0.1:8768/>；提示词、生成记录及后续路径见[声音试听与后续交接](../deliverables/2026-10-06_voice_audition/声音试听与后续交接.md)。声音尚未选定，当前仍为独立试听，正式 TTS 和临时剧本未换声；此项发生在下方 r1 归档之后。

## 最新接手入口：2026-10-06 存档基线

当前默认临时剧本已使用中性两套、高涨两套、低落一套局部复用口型。说话循环较稳，持续闭口已改善；实测窗口平均约 20.69fps，仍有 11 次超过 100ms 的跨状态／素材切换间隔，最长 206.52ms。本轮完整回归 509 项通过。真实音频对嘴、独立眨眼调度及板端实测待做。

先读[流畅度复核与保留意见](../deliverables/2026-10-06_avatar_reuse/流畅度复核与保留意见_2026-10-06.md)与[板端移植交接](../deliverables/2026-10-06_avatar_reuse/板端移植交接_2026-10-06.md)。默认入口为 `tools/run_demo_script.bat`，原版对照为 `tools/run_demo_script_original.bat`。最新三档口型仍在临时剧本适配层；正式 Qt／共用播放器与板端合同 1.2 尚未纳入新策略。板端底色以当前 manifest 的 **#FCFCF3** 为准。

归档基线名为 `AURA_项目_板端移植基线_2026-10-06_r1`，本机保存于 `E:\项目\存档`；完整性状态见该目录最终报告。归档保留共享目录整体结构，排除本机虚拟环境／缓存／同步状态，实际运行依赖另有记录。以下 2026-10-05 及更早说明保留追溯，环境和素材进度以本段及最新交接为先。

> 本仓按 `Docs\amd_kv260_full_work_requirements_v3.md`（下称 **D5**）**§19.2 目录蓝图**建立；
> 首批内容由上游旧赛道工程 `wujing-lite` **复用引入**（团队 2026-09-26 拍板，D5 §6.1 / §23.2 的 W17-16、W17-21 均已 `[x]`）。
> 盘点与衔接过程见 `Docs\AURA_KV260_C岗玩偶与语音_复用清单与衔接行动_20261002.md`。

## 0. 历史开发进度与接手入口（2026-10-05）

**最新同步：播放自然度第二步已完成。** 当前使用连续源帧游标、主窗口平滑折返、相邻帧插值及原动作收尾，停用不兼容窗口的直接切换。15态、16套素材和573张PNG保持原口径；板端合同为1.2，并提供C连续游标参考。
双击 `tools/run_demo_script.bat` 启动66秒剧本，F5重播。启动器会检查Python/Tk/Pillow，并将窗口放到前台。
本轮同步及验证入口：[最新工作说明](../deliverables/2026-10-05_avatar_naturalness/最新工作说明.md)。交接以[说话播放层完善与素材交接](docs/说话播放层完善与素材交接_2026-10-05.md)为准。已提供v3素材工作流、七类提示词及21份API图；新素材未生成、未接入。

**2026-10-05 更新：** Tk和正式Qt现统一调用`board/interaction/avatar_player.py`；
语音结束时渲染层保留旧素材沿原动作收尾，唤醒动画完成向同一EventBus发送结束事件。
当前合同为15态，16套素材均已打包RGB565（含3套播报变体），JSON与C资源表已同步。
完整本地回归及Qt离屏绘制已通过；KV260/MCP01真实设备验收待连接后执行。
旧修复记录见[`docs/共享播放器修复与验证_2026-10-05.md`](docs/共享播放器修复与验证_2026-10-05.md)，下面环境及旧引入记录保留追溯。

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest tests -q
python tools/demo_qt.py
python tools/demo_qt.py --selftest --outdir <证据目录>
python scripts/board_export.py --force
```

正式Qt须与业务FSM共用EventBus：`RuntimeFSM(bus=bus)`、`UiState(event_bus=bus)`、
`MainWindow(ui, event_bus=bus)`。不要另建一个只改单独显示状态的FSM；可运行例子见`tools/demo_qt.py`。

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

1. 玩偶状态字段**唯一**为 `runtime_state`，当前取值 **十五态**：
   `IDLE / PRESENT / LISTENING / THINKING / SPEAKING / SPEAKING_NEUTRAL / SPEAKING_LOW / AWAKE / PUZZLED / ACK_NOD / DENY_SHAKE / CAMERA_LOST / NETWORK_LOST / CANCELLED / ERROR`
   定义见 `board/runtime/fsm.py` 与 `ui/ui_state.schema.json`。历史十态、七态记录保留追溯；不得另建命名域。
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
