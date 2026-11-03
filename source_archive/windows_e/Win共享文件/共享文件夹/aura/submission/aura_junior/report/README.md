<!-- aura-architecture-generated -->
# 设计报告与完整功能框图

本目录已经包含全部框图及可编辑源；实际实验结论与最终整机交付仍待完成。

[设计报告框架](design_report.md) · [接口说明](interface_contracts.md) · [AI 协作记录](ai_collaboration.md) · [从零复现框架](reproducibility.md)

[八页 PDF 图册](framework_diagrams.pdf)

## 全项目总体功能框图

M1–M8 总体目标：感知、身份、调度、执行、交互与竞赛交付；细节见其余分图。

![全项目总体功能框图](figures/01_system_overview.svg)

源文件：`figures/01_system_overview.dot` / `.mmd`；导出：`.svg` / `.png` / `.pdf`。

## 软硬件划分与 FPGA 执行路径

官方 DPU 与既有相对租约已有有限板测；新的绝对源期限链路全部明确留位。

![软硬件划分与 FPGA 执行路径](figures/02_ps_pl_hardware.svg)

源文件：`figures/02_ps_pl_hardware.dot` / `.mmd`；导出：`.svg` / `.png` / `.pdf`。

## 视觉、目标、身份与记忆算法框图

CPU 参考、IoU、可选 ByteTrack 和最终 DPU 目标分别画出。

![视觉、目标、身份与记忆算法框图](figures/03_vision_identity.svg)

源文件：`figures/03_vision_identity.dot` / `.mmd`；导出：`.svg` / `.png` / `.pdf`。

## 核心创新：源期限 → 任务准入 → PL 监督

软件模型已联调；校准与新的 PL 独立期限执行仍待完成。

![核心创新：源期限 → 任务准入 → PL 监督](figures/04_freshness_admission_guard.svg)

源文件：`figures/04_freshness_admission_guard.dot` / `.mmd`；导出：`.svg` / `.png` / `.pdf`。

## 录音、看图问答、说话人和汐蓝交互框图

复用已选声线与动画；真实 MCP01、跨机媒体、ASD 同步链明确待接。

![录音、看图问答、说话人和汐蓝交互框图](figures/05_audio_speaker_avatar.svg)

源文件：`figures/05_audio_speaker_avatar.dot` / `.mmd`；导出：`.svg` / `.png` / `.pdf`。

## 官方提交物与工程成果对应框图

工程包 + Skill + 设计报告；七个推荐目录都留出可核验材料位置。

![官方提交物与工程成果对应框图](figures/06_submission_evidence.svg)

源文件：`figures/06_submission_evidence.dot` / `.mmd`；导出：`.svg` / `.png` / `.pdf`。

## 六组对照、共同指标与整机验收框图

G0–G5 全部属于待做真实实验；已有模拟联调不能抵扣这些实验。

![六组对照、共同指标与整机验收框图](figures/07_ablation_and_acceptance.svg)

源文件：`figures/07_ablation_and_acceptance.dot` / `.mmd`；导出：`.svg` / `.png` / `.pdf`。

## 尚未开展的扩展与现有模块接口

扩展只预留结构，不变成当前必交；I2S 双麦 / DOA 仍为已取消范围。

![尚未开展的扩展与现有模块接口](figures/08_future_extensions.svg)

源文件：`figures/08_future_extensions.dot` / `.mmd`；导出：`.svg` / `.png` / `.pdf`。

<!-- aura-structure-details -->
## 复核后的目录职责

主责：全队；运行/使用位置：评审与复现。

内容：设计报告、框图、接口、需求/证据索引、AI 协作与复现。

边界：解释原始数据，不能凭模板/图册宣称优化或整机完成。

依据：O3，见 report/structure_detail.md 的依据登记。

现有来源：

- 按关联模块清单回收，具体工件尚待冻结。

目标目录已建立；本轮没有将实际源文件迁移到此处。
