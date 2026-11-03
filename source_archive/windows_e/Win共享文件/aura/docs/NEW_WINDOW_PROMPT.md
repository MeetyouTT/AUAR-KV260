# 🧭 雾镜 Lite · 新窗口开发提示词（粘贴给 AI）

> 用途：在新对话窗口继续开发"雾镜 Lite 固定式豆包头"（人3：运行时/UI/语音对话/系统集成）。
> 由前一个开发会话生成（2026-08-31）。请 AI 先阅读下方"必读文档"再动手，不要臆造进度。

## 一、你是谁 / 任务
你是嵌入式 AI 助手开发工程师，继续本竞赛项目的人3 部分。本项目为 2026 全国大学生嵌入式芯片与系统设计竞赛·FPGA 创新设计赛道（复旦微电子 FMQL30TAI），产品为固定式桌面多模态交互终端"雾镜 Lite"（无转轴）。

## 二、环境与命令
- 工作目录：`D:\share\项目开发\FPGA语音助手开发\wujing-lite`
- **git：系统无 git**，使用便携版 `D:\share\项目开发\tools\PortableGit\cmd\git.exe`（仓库已 init，未关联远程）
- Python 3.12（语法兼容板端 Ubuntu 20.04 / 3.8+）；依赖见 `pyproject.toml`（jsonschema、PySide6）
- 测试：`python -m pytest tests/ -q`（基线 **77 passed**）
- 截图：`python examples/run_ui.py --state <状态> --screenshot out.png`
- 冒烟：`python examples/smoke.py`
- 注意：PowerShell 重定向输出为 UTF-16，读结果用 `Out-File -Encoding utf8` 或直接 read_files

## 三、当前进度（以 git 历史为准，先核对再继续）
| 阶段 | 状态 | commit |
|---|---|---|
| A1 运行时骨架（EventBus/FSM/Validator/Adapter/MockBoard） | ✅ | 9cf7689 |
| A2 UI 骨架（PySide6 55/45 分屏 + ui_spec 一致性合同）→ **9/11 落地为板端三区 1024×600** | ✅ | 4afb333 |
| UI 问题修复（lan 状态/初始同步/事件区/检测框标签） | ✅ | e09bed0 |
| 玩偶猫脸（还原参考图线描 + 曲线化 + 眨眼/左右看） | ✅ 曾实现 | 6bcafe3 / 41756d3 / ec6209c / 1ec0b9e |
| **手绘猫脸方案废弃**：移除全部 QPainter 手绘与动画实现，仅留**方案 C 接口** | ✅ | 6bca2cf |
| **玩偶方案 B2V 接入**：QPainterPath 矢量主体替代位图底图 + 程序化表情层（`_face_anchor` 几何锚框，执行层 M7/M8 完成） | ✅ | docs/GPT_AVATAR_B2V_DELIVERABLE.md |
| **玩偶帧序列素材接入**：`avatar_assets` 帧序列优先（`assets/avatar/`）+ B2V 矢量回退；复用桌宠 matting 预抠像管线 | ✅ | board/ui/avatar_assets.py |
| A1 Gate 报告（有条件通过） | ✅ | docs/A1_Gate_Report.md |
| A2 剩余：KWS、UI 联调录屏 | ⬜ 待办 | — |
| A3（LAN 对话/GA）、A4（soak/GB）、10 月板端 | ⬜ 后续 | — |

## 四、必读文档
1. 人3 任务书：`D:\share\项目开发\FPGA语音助手开发\month\雾镜Lite_无板开发月_人3_运行时对话与系统集成技术任务书_V2.0.md`
2. 主计划：`D:\share\项目开发\FPGA语音助手开发\31日计划安排\00_团队方案_只读\雾镜 Lite 固定式"豆包头"首版一个月技术实施计划.md`
3. 板卡延期调整：`D:\share\项目开发\FPGA语音助手开发\31日计划安排\01_G0计划与分工\11_板卡延期调整计划.md`
4. 工程说明：`wujing-lite/README.md`
5. 运行时架构：`wujing-lite/docs/runtime_architecture.md`
6. UI 一致性核对表：`wujing-lite/docs/ui_consistency_checklist.md`
7. 数据合同：`wujing-lite/ui_spec/*.json`（布局/令牌/状态 schema 为唯一权威数值）

## 五、关键约束（不可违反）
- **环境标签**：PC / SIMULATED / BOARD_REQUIRED 严格区分，任何 PC 结果不得写成实体板卡实测（人3 任务书 §九 红线）
- **UI 动画采用方案 C 三层接口**：
  - 数据层 `UiState.set_avatar_anim(name, params, enabled)` / `snapshot()["avatar_anim"]`（`ui_state.py` + `ui_state.schema.json`）
  - 映射层 `avatar_fsm.ANIMATION_FRAMES` + `animation_frames(name)`（帧表）
  - 执行层 `AvatarPanel._anim_state(t)`（统一引擎）+ `_draw_eyes/_draw_mouth`（绘制原语）
  - **渲染接入点：`AvatarPanel._render_avatar`（当前占位，enabled=False 静态）**——新渲染方案（sprite 贴图 / LVGL / 美术素材）在此实现，需先与用户确认方案
- 数据合同以 `ui_spec/*.json` 为唯一权威数值；改合同须同步提升 schema 版本并通知依赖方
- git 提交规范：`feat:`/`fix:`/`refactor:`/`chore:` + 中文说明
- 不得同时维护两套 UI / 两套 ASR / 两套 TTS；不得把 MockBoard 结果写成板端实测

## 六、下一步行动项（按优先级，先与用户确认再做）
1. ~~玩偶渲染新方案~~（✅ 已接入方案 B2V：QPainterPath 矢量主体 + 程序化表情层，见 `docs/GPT_AVATAR_B2V_DELIVERABLE.md`）
1b. **玩偶帧序列素材**（✅ 播放器已接入 `avatar_assets`：帧序列优先 + B2V 矢量回退；**已入库 5/9 个素材名**，
   进度用 `python tools/prepare_avatar_frames.py --status` 看；规范见 `assets/avatar/README.md`。
   ⚠️ **2026-09-12 情绪节点由 9 态扩为 10 态**：播报拆 `SPEAKING`（高涨/`talking_normal`）与
   **`SPEAKING_LOW`**（低落/`talking_low`），由回复 `emotion` 命中 `fsm.LOW_EMOTIONS` 驱动；
   新增状态时记得同步 `fsm.RuntimeState` / `ui_state.schema.json` 枚举 / `avatar_assets.STATE_ASSET` /
   `avatar_fsm.AVATAR_MAP` / 单测 / `ui_consistency_checklist.md` —— 见
   `docs/情绪分档扩展_播报高低落两档SPEAKING_LOW_技术记录.md`）
2. **A2·KWS**：`pip install sherpa-onnx` + 中文关键词模型（Zipformer 3.3M）→ 延迟/误触发/CPU/内存 benchmark → `docs/MODEL_CARD_KWS.md`
3. **UI 全链路联调**：`run_ui.py --demo` 录屏（EventBus→FSM→UiState→UI）
4. 补强 A1 Validator 反例集（目标 100 组正反例，9/24 节点前）
5. （A3）LAN 对话：FunASR + 唯一 TTS + Adapter/Validator + GA 审查

## 七、执行时注意事项
- 每次改动后跑 `python -m pytest tests/ -q` 确认无回归（当前 **96 passed**，新增 `tests/test_avatar_assets.py` 9 项）
- 涉及 UI 改动用 `--screenshot` 出图到 `evidence_shots/`
- 完成后 `git add -A && git commit`（用便携版 git）；不关联远程
- 环境标签务必标注在输出/证据中

## 八、技术探讨入口（**只读探讨**，与上面的开发入口互不干扰）

- **主题**：I2V 视频生成的原理与开源生态（**明确不落地、不改任何代码**）
- **提纲**：`wujing-lite/docs/技术探讨_I2V视频生成_提纲.md`
  （顶部含**可直接粘贴到新窗口的启动词**；正文为 8 章讨论提纲 + 术语表 + 待核实清单）
- **纪律**：不装 ComfyUI / torch、不改 `wujing-lite` 任何文件；型号/参数量/显存/许可等具体数字
  **必须联网核实并标来源**，查不到就写"未核实"；每个概念都要回扣本项目约束
  （板端只显示 423×436、素材只保留腰部以上、绿幕 ≈#0FE91B 走 adaptive 抠像、闭环判据 mean≤2.0 且差异≤2%）
- **边界**：探讨结论若要落地，另立方案文档与 ADR，不混进本入口
