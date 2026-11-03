# LICENSE MATRIX · 第三方组件与素材许可矩阵（骨架）

> 版本：V0.1（骨架）｜ 日期：2026-09-12 ｜ 维护：**人3（运行时 / 系统集成）**
> 环境标签：**PC 基线**。目的：满足任务书 A2 要求（`MODEL_CARD_YOLO11 / KWS / LICENSE_MATRIX` 骨架），
> 并为「开源复用 + 自研边界」提供可核查依据。
> 状态列含义：✅ 已核实（本机可查版本/许可声明）｜🟡 待核实（需查上游仓库 LICENSE 原文）｜ℹ️ 仅开发工具

## 一、运行/开发依赖（Python）

| 组件 | 本机版本 | 许可 | 用途 | 是否随产物分发 | 状态 |
|---|---|---|---|---|---|
| Python | 3.12.7 | PSF-2.0 | 运行时 | 否 | ✅ |
| jsonschema | 4.26.0 | MIT | 数据合同校验（Schema 层） | 否 | ✅ |
| PySide6 (Qt for Python) | 6.11.2 | **LGPL-3.0 / 商业双许可** | PC 侧 UI 原型与离屏渲染 | 否（板端为 LVGL，不装 Qt） | ✅ |
| sherpa-onnx | 1.13.8 | **Apache-2.0** | KWS 推理引擎 | 否 | ✅ |
| sherpa-onnx-core | 1.13.8 | Apache-2.0 | 同上（native core） | 否 | ✅ |
| sounddevice | 0.5.6 | MIT | 麦克风采集（仅 `--mic`） | 否 | ✅ |
| numpy | 2.5.2 | BSD-3-Clause | 数值/音频缓冲 | 否 | ✅ |
| opencv-python / -headless | 5.0.0.93 | Apache-2.0 | 抠像/抽帧/转码（工具链） | 否 | ✅ |
| Pillow | 12.3.0 | HPND（MIT 类） | 帧序列/GIF/JPEG | 否 | ✅ |
| imageio | 2.37.4 | BSD-2-Clause | 视频读写（辅助） | 否 | ✅ |
| imageio-ffmpeg | 0.6.0 | BSD-2-Clause（**内含 ffmpeg 二进制**） | 演示页转码（H.264/VP9） | **否**——⚠️ 见 §三 | ✅ |
| python-docx | 1.2.0 | MIT | md→docx 文档同步 | 否 | ✅ |
| pytest | 9.1.1 | MIT | 回归测试 | 否 | ✅ |
| cffi / pycparser | 2.1.1 / 3.0 | MIT / BSD-3 | sounddevice 依赖 | 否 | ✅ |
| PortableGit | — | GPL-2.0 | 版本管理（开发工具） | 否 | ℹ️ |

## 二、模型与素材

| 资产 | 版本/来源 | 许可 | 是否入库 git | 状态 |
|---|---|---|---|---|
| KWS 模型 `sherpa-onnx-kws-zipformer-wenetspeech-3.3M-2024-01-01` | ModelScope `pkufool/…`（训练数据 WenetSpeech L） | **Apache-2.0**（模型卡 README 明示） | **否**（`models/` 已忽略；下载命令见 `docs/MODEL_CARD_KWS.md` §六） | ✅ |
| YOLO11（视觉侧） | AIBS / ultralytics 系 | 待视觉线（人2）确认 | 否 | 🟡 |
| 玩偶帧序列素材（6 态 × 100 帧 PNG，466×480） | **本团队**用 Seedance 生成绿幕视频 → 自研抠像/降采样管线（`tools/prepare_avatar_frames.py`） | 团队自产（AI 生成内容）；生成平台条款需在赛中声明 | ✅ 入库（142.7 MB） | 🟡 条款待核 |
| 字体 | Windows 系统字体（Microsoft YaHei 等） | 系统授权（未随产物分发） | 否 | ✅ |
| 界面/图标 | 自绘（QPainterPath / 自研矢量），无第三方图库 | 团队自产 | ✅ | ✅ |

## 三、分发注意事项（重要）

1. **ffmpeg（GPL 构建）**：`imageio-ffmpeg` 自带的是 **gyan.dev essentials（GPL v3）** 构建，
   仅用于**开发期**把演示 MP4 转成浏览器可播的 H.264/VP9。
   → 交付物**只包含转码后的视频与自包含 HTML**，**不打包 ffmpeg 二进制**；
   若将来需要随产品分发转码能力，必须换成 LGPL 构建或改为「服务端/离线转码」。
2. **Qt / PySide6（LGPL-3.0）**：PC 侧原型使用；板端最终形态为 **LVGL（MIT）**，不装 Qt。
   若评审要求交付 PC 可执行程序，需按 LGPL 要求**动态链接**并提供替换库的途径。
3. **大文件策略**：模型（31 MB）、`frames.rgb565`（256 MB）、演示 MP4/GIF 中可再生成的部分均不入 git；
   `.gitignore` 已固化该策略（见仓库根 `.gitignore` 的「板卡/模型工件」「演示/取证的中间产物」两段）。
4. **开源复用边界**：本项目**未修改**任何第三方源码；Open-LLM-VTuber 仅作为 **LAN 主机独立服务**
   （A3 计划），不嵌入板端、不与自研 Adapter/Validator 代码混合分发。

## 四、下一步

- [ ] 补 YOLO11（人2 线）与 Open-LLM-VTuber / FunASR / TTS 的许可与版本（A3 · 9/16—9/19 逐个冻结）
- [ ] 核 Seedance 生成内容的平台条款（是否允许用于竞赛提交与公开演示）
- [ ] 由 Reviewer 复核本矩阵（与 A1 Gate 的「第二人复核」一并签字）
