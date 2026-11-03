# AURA：论文方法、项目实现与验证对照

日期：2026-10-08。依据：10 月 8 日整体框架、10 月 7 日单一创新方向、10 月 4 日两份论文核查与实施建议，以及 Ubuntu 最新可核验记录。本文记录阅读结论与工程取舍，未开展新的模型复现、板测或机构实验。

## 阅读范围与资料身份

本轮完整补读以下共享文档：

- [第一份论文方法与 FPGA 实现核查](/home/ghmd/Win共享文件/output/AURA_论文方法_GitHub_FPGA实现核查_2026-10-04.md)。
- [第二份论文报告与 FPGA 实现核查](/home/ghmd/Win共享文件/output/AURA_第二份论文报告_GitHub_FPGA实现核查_2026-10-04.md)。
- [论文方法加入项目的实施建议](/home/ghmd/Win共享文件/output/AURA_论文方法加入项目的实施建议_2026-10-04.md)。

核对了下文主要论文的摘要、部分 PDF 引言/摘要及作者仓库说明。FILM-QNN 本轮只核对作者论文页；MagFace 核对作者仓库。没有声称逐篇通读全部论文、复查所有仓库源码或完成论文复现。10 月 4 日报告中的仓库缺件、许可证、固定提交检查属于当时的核查结果，不自动代表仓库今天的状态。

两份核查文档引用的近期 `deep-research-report.md`、`deep-research-report (1).md` 原始附件尚未在当前可访问共享文件中定位到。共享目录 `Docs/deep-research-report (1).md` 是带历史标记的 9 月统一项目方案，不能据同名将其当作第二份论文报告原稿。本轮研究判断使用上述核查文档、最新方案和可访问的论文/作者资料。

## 核心研究主线：四类文献分别支撑什么

最新方向为“控制误差约束下的可变感知有效期调度与 FPGA 执行监督”。以下连接是结合 AURA 的工程设计；论文引用本身不证明本队创新成立。

| 文献与原方法 | 在 AURA 中的落点 | 当前证据与缺口 | 需要的验证 |
| --- | --- | --- | --- |
| [Run Time Assurance 教程](https://arxiv.org/abs/2110.03506)：监测复杂控制输出，通过过滤或备用策略满足约束 | PS 提供运动建议，PL 按明确条件接受、拒绝或停止 | 自研 VSRV 的序号/代次、原子提交、范围/速率、STOP、相对租约有已有构建及有限板测；尚未完成新版完整源期限规则 | 注入旧命令、越界、失联、过期和重启；区分数字停止结果与机械实际停止 |
| [FPGA Stream-Monitoring of Real-time Properties](https://finkbeiner.groups.cispa.de/publications/emsoft19.pdf)：由 RTLola 规格生成 FPGA 时序流监控器 | 把源证据期限及失效条件写成独立、可验证的执行监督规则 | 当前是手写 VSRV RTL，不是 RTLola 自动生成器的复现；PL 源绝对期限和同一观测不得延长期限尚未验收 | 验证时钟换算误差、到期边界、重复观测、相机重连/对象代次变化与状态回读 |
| [Age-of-Information vs. Value-of-Information Scheduling](https://arxiv.org/abs/1903.05356)：信息价值结合时间和受控系统动态 | 依据速度及不确定性，把固定期限改为满足误差限的可变有效期 | 当前已有源时间/帧龄及相对租约基础；误差增长模型、参数校准和可变期限收益尚未验证 | 独立标注位置误差；校准与测试分开；比较越限率和有效跟踪覆盖率 |
| [Computation and Communication Co-scheduling for Multi-Task Remote Inference](https://arxiv.org/abs/2501.04231)：联合安排远程推理的计算、通信与信息更新 | 在单 CU DPU 上依据剩余源期限准入身份任务，维持检测更新 | AURA 拟用实测执行成本的准入规则；共享 DPU 检测/身份实验尚未完成，不是原文 MDP/MGF 策略的复现 | 固定同一平台与输入，测检测帧龄/更新间隔、身份服务等待及吞吐；压力下核验非抢占影响 |

新方案的候选模型为：

```text
U(dt) = u0 + (abs(v_hat) + delta_v) * dt + 0.5 * a_b * dt^2
deadline_source = t_capture + T_valid
```

`T_valid` 由允许误差和期限上限共同约束。`u0`、速度误差、加速度界及允许误差需要标定；不能把该工程模型当作已有论文定理或已证明的物理安全边界。PS/PL 的时间映射需要保守误差处理；同一观测重新提交不能获得新的源有效期。

现有 RTL 在 COMMIT 时装载 `lease_left` 并倒计时，PS 驱动先扣除源帧龄。这是已有基础，但不等于 PL 已实现新方案中的源绝对期限及防续期规则。证据见 [RTL](/home/ghmd/kv260-visual-servo-20261007/rtl/visual_servo.sv:82) 与 [最新计划复核](/home/ghmd/AMD_Smart/logs/daily/2026-10-08-LATEST-PLAN-ALIGNMENT.md)。

## 应用方法：功能基础与已有实现要分清

| 方法 | 项目位置与取舍 | 实际进度 / 下一项验收 |
| --- | --- | --- |
| [ByteTrack 作者实现](https://github.com/FoundationVision/ByteTrack)：利用高、低置信度检测的关联维护轨迹 | 项目 DPU 输出检测结果，PS 执行跟踪；保留低分框二次关联和空帧更新 | 当前实时链为 CPU YuNet + IoU/速度预测轨迹，不是 ByteTrack；需接实际项目检测，测遮挡、交叉、漏检和 ID 切换 |
| [MobileFaceNets](https://arxiv.org/abs/1804.07573)，配套 ArcFace 路线 | 轻量身份特征网络候选；ArcFace 属于训练方法，不是在 PL 上实时执行的训练损失 | 已通过的是 CPU YuNet/对齐/SFace 图片参考链；MobileFaceNet DPU 兼容性、量化精度、实时登记/未知人/SQLite 业务仍需独立验收 |
| [Light-ASD 作者实现](https://github.com/Junhua-Liao/Light-ASD) | Windows 音视频主动说话人识别基线，输出绑定轨迹与媒体时间窗 | 未见 AURA 实际同步音视频的离线及实时验收证据；先测两人轮流/同时说话、静音与画外声音，再接实时链 |
| [MagFace 作者实现](https://github.com/IrvingMeng/MagFace) | 人脸识别与质量评价的可选对照 | 现有 SFace 不等于 MagFace；不能把任意特征范数解释成 MagFace 质量。先完成身份基线，再决定是否引入 |
| [LoCoNet 作者实现](https://github.com/SJTUwxz/LoCoNet_ASD) | 长短时上下文说话人方法的可选对照 | 尚未验证；普通迟滞/防抖不等于 LoCoNet 复现。Light-ASD 基线完成后再评估增加上下文的收益 |
| hls4ml | 独立模型到 HLS 的硬件工具候选 | 不是一个现成身份/ASD 模型，也不代表上述网络已移植；需另行验证算子、资源、时序与精度 |

实际状态依据：[实时视觉记录](/home/ghmd/kv260-realtime-vision-20261007/CURRENT_RUNTIME.json:78)、[SFace 适配报告](/home/ghmd/kv260-adaptation-check-20261006/ADAPTATION_REPORT.md:9)、[DPU 与 VSRV 源码平台报告](/home/ghmd/kv260-visual-servo-20261007/SOURCE_PLATFORM_REPORT.md)。ResNet18 分类板测不能替代项目检测/身份 DPU 验收。

## 第二份报告六项：基线之后按瓶颈取舍

| 文献/工具 | 可借鉴内容 | 当前项目边界 |
| --- | --- | --- |
| [FPGA Resource-aware Structured Pruning](https://arxiv.org/abs/2308.05170) | 依据真实资源成本选择结构剪枝，而非只看稀疏率 | 可选身份模型优化。固定 DPU 位流上模型变小不自动降低已实例化 DPU 的 LUT/DSP；精度、时延和完整联合资源均须实测 |
| [SATAY](https://arxiv.org/abs/2309.01587) | CNN 自定义流水架构、外存缓冲和映射优化 | 当前应用层排队/帧池不等于 SATAY 硬件复现；其定制加速器需另建 KV260 集成路径 |
| [TAPA](https://github.com/tuna/tapa) | 多任务并行 HLS 工具及设计流程 | 自研多阶段 HLS 核确有需求时再评估；不是现有 DPU 或手写 AXI/PWM 的自动优化替代品 |
| [FILM-QNN 作者页](https://mengshus.github.io/publication/2022FPGA_FILM-QNN) | 层内混合精度 FPGA 加速研究 | 当前普通 INT8 量化不等于原文混合位宽计算硬件；本轮未阅读全文 PDF |
| [NAF 会议论文](https://past.date-conference.com/proceedings-archive/2023/DATA/607.pdf) | 网络与加速器联合搜索 | AURA 枚举输入尺寸/模型/频率是工程参数选择，不是该可微网络与加速器搜索的完整复现 |
| [H2PIPE](https://arxiv.org/abs/2408.09209) | 基于 HBM 的 CNN 流水、缓冲及停顿分析 | 不是可直接加入现有 DPU 的缓存模块；可先借鉴缓冲和停顿测量，具体硬件迁移需另行设计 |

这六项没有被最新单一创新方案全部列为必做贡献。先保留现有 DPU 路线、得到实际任务基线，再决定是否值得增加训练、HLS 核或定制网络加速器。现有综合时序问题也须按实际工程处理，不能用论文工具名称代替定位。

## 下一步可执行的实验顺序

1. 补齐实际项目 DPU 检测和 PS 跟踪基线，保留 CPU 对照；记录捕获、推理开始/结束、关联及提交时间，串联帧、轨迹代次和硬件结果。
2. 在固定相机/录制输入上建立独立标注和误差校准/测试划分，测真实检测与身份成本。该准备不能替代机构运动带来的相对运动校准。
3. 保持相同 DPU/监督/PWM 平台，优先比较 G0、G1、G5，再完成 G2/G3/G4 消融。G0 为固定期限+检测优先+软件源期限检查，G1 增加 PL 源期限监督，G5 使用可变期限+任务准入+PL 监督；具体六组定义以 [10 月 7 日方案](/home/ghmd/Win共享文件/output/aura_single_innovation_direction_20261007.md) 为准。
4. 共用独立位置误差指标，同时报告覆盖率、检测新鲜度和身份等待。始终停止不能算优化有效；不预设提升百分比，不套用论文速度、精度或资源数字。
5. C 线并行准备真实音视频/Light-ASD 录制片段验收，B 线补身份业务。机构继续按用户要求等待 3D 模型；数字监督通过不能替代最终机械验收。

论文相关工作当前完成的是资料核查、方法选择和已有实现边界的对齐。可变有效期、共享 DPU 准入及完整跨层对照实验仍属待实现/待验证事项。
