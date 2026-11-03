# AURA / KV260：第二份论文报告的 GitHub FPGA 实现核查

核查日期：2026-10-04。对应附件：deep-research-report (1).md。

本次按上一份报告的标准核查论文、作者关联仓库、实际文件和平台要求。附件中的方案与操作步骤作为研究材料处理。本次完成公开源码与交付工件核查，没有安装这些工具、运行仓库脚本，也没有在 KV260 上综合或板测。

## 1. 结论

六篇核心论文中，**资源感知剪枝、SATAY、TAPA** 找到了可核验的公开实现。三者分别提供剪枝与 HLS 工具、YOLO 优化及板端工件、任务并行 HLS 编译工具链，交付内容不同。**FILM-QNN、NAF、H2PIPE** 有原论文中的 FPGA 实验，但本次未找到能确认对应论文方法的完整公开 GitHub 实现；H2PIPE 另找到相关 HPIPE 的 GitLab 项目入口。

如果目标是阅读真实 FPGA 代码，优先查看 **hls4ml 剪枝分支和 SATAY / fpgaConvNet**。如果目标是尽快改进现有 AURA，优先沿用 DPU，做通道剪枝、INT8 精度验证和任务调度，再根据实际瓶颈决定是否增加 HLS 核。以下适用性判断属于结合项目现状的工程推断。

| 论文 | 找到的公开实现 | 实际交付 | KV260 / AURA 判断 |
|---|---|---|---|
| FPGA Resource-aware Structured Pruning，ICFPT 2023 | [hls4ml：hardware-aware-pruning](https://github.com/fastmachinelearning/hls4ml/tree/hardware-aware-pruning) | 背包求解、Keras 剪枝、DSP/BRAM 资源目标、HLS 配置与测试 | 可以复现资源感知方法的小模型实验；其资源公式面向 hls4ml 生成硬件，不能直接用来预测固定 DPU 的资源释放 |
| SATAY，ICFPT 2023 | [SATAY](https://github.com/AlexMontgomerie/satay)、[作者链接的板端工程](https://github.com/ptoupas/amd-open-hardware-23)、[fpgaConvNet HLS](https://github.com/AlexMontgomerie/fpgaconvnet-hls) | 优化器与论文结果脚本；ZCU104/ZCU106 位流、硬件描述、权重与驱动；另有 HLS 硬件生成库 | 最值得研究 YOLO 的 FPGA 数据流；KV260 需要重建硬件和运行环境，已有位流不能直接加载到 KV260 |
| TAPA，TRETS 2023 | [论文版 UCLA-VAST/tapa](https://github.com/UCLA-VAST/tapa)、[现维护版 tuna/tapa](https://github.com/tuna/tapa) | C++ 任务/流接口、软件仿真、RTL 生成、布局优化和示例 | 可用于后续自定义 HLS 数据流设计；未找到现成的 AURA / KV260 联合工程 |
| FILM-QNN，FPGA 2022 | [作者论文页](https://mengshus.github.io/publication/2022FPGA_FILM-QNN)；未找到可核验的完整 GitHub 实现 | 原文报告 PYNQ-Z2 / ZCU102 的混合精度 HLS 加速器 | 同层 W4/W8、A5 和 DSP packing 需要配套计算硬件；当前 INT8 DPU 不能直接复现这些机制 |
| NAF，DATE 2023 | [会议原文](https://past.date-conference.com/proceedings-archive/2023/DATA/607.pdf)；未找到可核验的官方 GitHub 实现 | 原文给出网络、位宽、多核结构及映射的联合搜索和 ZCU102 实验 | 可以借鉴联合优化思路；自行枚举模型与调度参数，不能称为复现原文的可微网络/加速器搜索 |
| H2PIPE，FPL 2024 | [作者原文](https://arxiv.org/html/2408.09209v1)、[相关 HPIPE GitLab 项目](https://gitlab.com/mathewkhall/hpipe) | 原文为 Stratix 10 NX + HBM 的 CNN 流水加速；GitLab 入口的 HBM 扩展源码本次未核实 | KV260 使用 DDR4，没有论文要求的 HBM 和 Intel AI Tensor Block；可参考缓冲思路，直接移植代价高 |

“未找到”仅表示截至核查日期没有定位到可核验的公开实现，不等于作者没有代码或论文没有硬件实验。论文列表、同名无关仓库和只提供论文下载的网页不计作复现。

## 2. 资源感知剪枝：有直接对应论文的代码

[原论文](https://arxiv.org/html/2308.05170v2)明确将方法链接到 hls4ml 的 hardware-aware-pruning 分支，并说明 Apache 2.0 开源。它按共享 DSP / BRAM 的权重组建立资源预算，进行背包优化与迭代训练。论文实验使用 Keras / TensorFlow、hls4ml 0.7.1、Vivado / Vivado HLS 2020.1，目标器件为 XCVU9P。

关键代码入口：

- [knapsack.py](https://github.com/fastmachinelearning/hls4ml/blob/hardware-aware-pruning/hls4ml/optimization/knapsack.py)：背包求解，包含动态规划、贪心和 OR-Tools 求解路径。
- [vivado_objectives.py](https://github.com/fastmachinelearning/hls4ml/blob/hardware-aware-pruning/hls4ml/optimization/objectives/vivado_objectives.py)：VivadoDSPEstimator、VivadoMultiObjectiveEstimator 等资源目标。
- [Keras 优化模块](https://github.com/fastmachinelearning/hls4ml/tree/hardware-aware-pruning/hls4ml/optimization/keras)：训练、掩码与正则化。
- [使用说明](https://github.com/fastmachinelearning/hls4ml/blob/hardware-aware-pruning/docs/advanced/model_optimization.rst)：剪枝目标、Reuse Factor 和硬件生成配置。

当前 hls4ml 主线也保留了这类功能，代码入口已改为 [optimization/dsp_aware_pruning](https://github.com/fastmachinelearning/hls4ml/tree/main/hls4ml/optimization/dsp_aware_pruning)。因此，复现论文应固定旧分支；使用现版本应按现接口和依赖配置，不能混用两代示例。

一个与 AURA 特别相关的限制：当前 [VivadoDSPEstimator 源码](https://github.com/fastmachinelearning/hls4ml/blob/main/hls4ml/optimization/dsp_aware_pruning/objectives/vivado_objectives.py)对权重位宽小于 9 的层直接跳过 DSP 优化。这进一步说明它的资源模型与现有 INT8 DPU 不是同一硬件映射。

**建议实验边界：**先用可训练的小型分类网络验证“原模型 → 资源感知剪枝 → 重新生成 HLS → 布局布线资源对比”。若继续使用现有 DPU，则采用实际删除通道的模型压缩，重点测精度、延迟和数据量；保持位流不变时，不能报告 PL 的 LUT/DSP 因剪枝下降。

## 3. SATAY：最有价值的 YOLO 硬件参考，需要区分三个仓库

### 3.1 SATAY 仓库：论文优化与结果复现

[SATAY README](https://github.com/AlexMontgomerie/satay/blob/main/README.md)将论文、fpgaConvNet 扩展和配套板端工程连在一起。实际树包含 fpgaconvnet-model / fpgaconvnet-optimiser 子模块、平台描述、ONNX 模型、结果与运行脚本。

README 中的运行步骤生成 report.json 和论文相关结果；这个步骤完成的是建模与优化结果复现，不能据此声称已经生成了可上板位流。仓库的平台描述包含 ZCU102、ZCU104、ZCU216、U250、VCU110 和 VCU118，本次没有发现 KV260 平台描述。

### 3.2 amd-open-hardware-23：可以检查实际板端交付

[该工程](https://github.com/ptoupas/amd-open-hardware-23)由 SATAY README 直接推荐，提供 YOLOv5n 的 FPGA 检测演示。核实存在：

- hardware/ 下的 ZCU104 / ZCU106 .bit 和 .hwh，以及默认 fpgaconvnet.bit / .hwh。
- [fpgaconvnet_driver.py](https://github.com/ptoupas/amd-open-hardware-23/blob/main/hardware/fpgaconvnet_driver.py)：PYNQ Overlay、DMA 与 FIFO 控制。
- weights/、权重查找表、yolov5n.onnx 与 yolov5n_head.onnx。
- predict_yolo.ipynb、validate_yolo.ipynb、comparison.ipynb：摄像头演示、验证与 CPU/FPGA 对照。
- [yolov5n.toml](https://github.com/ptoupas/amd-open-hardware-23/blob/main/yolov5n.toml)：输入 320、位流、权重、定点小数位和 FIFO 深度配置。

[README](https://github.com/ptoupas/amd-open-hardware-23/blob/main/README.md)要求 PYNQ 3.0.1，并说明生成位流使用 Vivado 2022。它还明确 ONNX 用于 FPGA 场景下的检测 head；后处理也有 Python 实现。因此，评估端到端速度时要计入 ARM 侧工作。该工程声明 GPLv3。

**公开目录中没有找到直接重建这些位流所需的完整 HLS 源工程和 Vivado block-design 重建脚本。** 有位流、权重和驱动说明已有板端交付；要迁移器件，还需确定生成器版本、YOLO 层支持、硬件配置、约束与系统封装。

### 3.3 fpgaConvNet HLS：读取实际硬件模块

[fpgaConvNet HLS](https://github.com/AlexMontgomerie/fpgaconvnet-hls)确实提供硬件模块及生成流程。本次核实有 conv.hpp、sliding_window.hpp、pool.hpp、relu.hpp、mem_read.hpp / mem_write.hpp、HLS 综合/仿真脚本，以及 gen_bd.tcl / gen_hw.tcl。

[README](https://github.com/AlexMontgomerie/fpgaconvnet-hls/blob/main/README.md)介绍 GenerateNetwork 和分区硬件生成，并列出 Vivado HLS 2019.1 / 2019.2。这与配套板端工程的 Vivado 2022 环境不同；需要确认对应版本，不能假定当前库直接重建原位流或支持全部 SATAY 扩展。

**对 AURA 的判断：**这是研究“自定义 YOLO FPGA 加速器”的优先参考。若保留现有 DPU，只能借鉴流水、缓存与搬运分析。将此加速器加入 DPU+PWM 联合设计，或替换 DPU，均需要重新评估资源、时序和运行接口。

## 4. TAPA：源码完整的 HLS 工具链，迁移边界需要明确

[UCLA-VAST/tapa README](https://github.com/UCLA-VAST/tapa/blob/main/README.md)已经注明旧仓库归档，并将 [tuna/tapa](https://github.com/tuna/tapa)指定为当前维护仓库。研究论文版本和采用新工具版本应分别固定代码。

当前 [README](https://github.com/tuna/tapa/blob/main/README.md)描述 C++ 数据流到 Verilog RTL / .xo，再经 Vitis 生成位流的流程。实际代码树存在编译前端、RTL 生成、floorplan 与测试，已读取 [VecAdd 示例](https://github.com/tuna/tapa/blob/main/tests/apps/vadd/vadd.cpp)，确认任务之间通过 stream 并行连接。

当前列出的基础环境是 Linux、g++、CBC；RTL 综合和板端执行还需要 Vitis HLS 2022.1+。其示例及公开应用包含 Alveo U250 / U280。它的并行任务和布局优化机制值得研究，但本次没有找到可直接接入当前 KV260 DPU+运动控制工程的模板。

**对 AURA 的判断：**将来实现有多个流水阶段的 HLS 预处理核时，可以单独评估 TAPA。现有手写 AXI / PWM 和已生成 DPU IP 的布线、时序问题，应先按当前工程定位关键路径和拥塞，再判断是否需要改变设计结构。

## 5. 三篇尚未定位到完整 GitHub 复现的论文

### FILM-QNN

[作者论文页](https://mengshus.github.io/publication/2022FPGA_FILM-QNN)及其 [原文 PDF](https://mengshus.github.io/files/2022FPGA_FILM-QNN.pdf)确认有 PYNQ-Z2 / ZCU102 的 HLS 实验，核心包含同层 filter 混合位宽、DSP packing、权重与数据重排。作者网页的通用 GitHub 导航不是该论文源码链接。本次按标题、缩写、作者及实验机构检索，没有找到可确认完整方法的公开仓库。

GitHub 搜索返回的若干 Awesome Quantization 列表只是引用论文，没有提供对应硬件核。普通 INT8 PTQ / QAT 可用于当前系统，但不能称为复现 FILM-QNN 的 W4/W8/A5 加速器。

### NAF

[DATE 原论文](https://past.date-conference.com/proceedings-archive/2023/DATA/607.pdf)描述网络操作、位宽、异构核结构和映射的联合可微搜索，并给出 ZCU102 硬件结果。本次没有定位到官方可核验的公开搜索器和加速器源码。

搜索到的 [PietPtr/NAF](https://github.com/PietPtr/NAF)实际是 ColorLight 板的 UDP / Clash 平台，与该论文无关，已排除。

报告建议自行做“模型宽度、输入尺寸、剪枝比例、调度周期”的参数探索，可以作为项目工程优化。它与原文的网络/硬件架构共同搜索有启发关系，但算法、搜索空间和硬件目标均不同。

### H2PIPE

[作者原文](https://arxiv.org/html/2408.09209v1)使用 Stratix 10 NX、HBM 和 AI-Optimized Tensor Blocks，将部分权重缓冲移到 HBM，并处理伪通道共享、非确定性读延迟与 FIFO 停顿。

找到了同作者体系的 [Mathew Hall / HPIPE GitLab](https://gitlab.com/mathewkhall/hpipe)入口，页面列出提交、分支和 MIT 许可证。但 README / 分支内容本次未能读取，**不能确认它包含 H2PIPE 的 HBM 扩展，也不能把原 HPIPE 自动当成 H2PIPE 完整复现**。GitHub 的 H2PIPE / HPIPE 同名结果多为其他项目，未找到能核验的论文完整实现。

[AMD KV260 数据表](https://docs.amd.com/r/en-US/ds986-kv260-starter-kit/Product-Details)列出 4 GB DDR4。结合论文硬件要求，KV260 上采用 H2PIPE 需要改变存储接口、资源模型和计算模块。报告提出的帧池 / ROI 缓存属于应用层借鉴，其收益需要在 AURA 上独立实测。

## 6. MobileFaceNets 与 ArcFace：沿用上一轮结果

- **MobileFaceNets：**上一轮已核查 [whattflib123/kv260_face_recognition](https://github.com/whattflib123/kv260_face_recognition)，有 VART / XIR 的 MobileFaceNet DPU 推理、量化/编译脚本与 .xmodel。训练定义、原权重和校准材料不齐，仍需核对真实 arch.json 和精度。它可以作为 DPU 人脸链参考。
- **ArcFace：**本次读取 [InsightFace 官方 arcface_torch](https://github.com/deepinsight/insightface/tree/master/recognition/arcface_torch)。这是 PyTorch 训练实现并支持 ONNX 导出。ArcFace 主要是训练损失；板端运行训练得到的特征网络，再做特征比较，不能将该训练仓库列作 FPGA 加速核。

相关详细限制见 [上一份核查报告](C:/Users/uuh56/Desktop/项目/output/AURA_论文方法_GitHub_FPGA实现核查_2026-10-04.md)。

## 7. 这份报告应修正的项目假设与复现表述

**项目状态需要更新。**附件开头仍引用 10 月 2 日的 CLB site 99.50%、WNS +0.001 ns 和“最小 AXI 尚未证明”。工作区 10 月 3 日的 [后续开发评估](C:/Users/uuh56/Desktop/项目/output/AURA_KV260_后续开发与环境缺项评估_2026-10-03.md)已记录：M3 最小 AXI-Lite 与 DPU 联合构建和有限板测通过；M3 仍没有 PWM / 完整监督逻辑；报告中的 M3 资源为 LUT 60.23%、CLB site 99.45%、URAM 87.50%，最差余量约 +0.009 ns。该文件还说明最新启动时活动配置为官方 benchmark，M3 候选未激活。这些均是历史材料记载，本次没有新增板测。

**模型优化与硬件重建分开计量。**[Vitis AI 3.0 官方流程](https://xilinx.github.io/Vitis-AI/3.0/html/docs/workflow-model-development.html)说明 DPU 的 INT8 量化、通道剪枝、算子检查和按目标 arch.json 编译。结合固定 DPU 架构，改变模型可降低计算和存储需求；保持同一硬件配置时，其已综合的 LUT/DSP 不会随模型自动减少。若更换 DPU 架构或增加加速核，需要重新实现硬件和编译目标模型。

**报告里的组合创新要标注“论文启发”。**latest-frame、deadline / freshness 调度、身份结果缓存、ROI 复用、tiny motion_guard 以及模型参数枚举，不是上述六篇论文提供的同一套源码。可以作为 AURA 的独立设计，但须分别给出实现与实验，不能将引用论文视为已经复现这些功能或证明性能提升。

## 8. 适合当前项目的使用顺序

| 顺序 | 使用方式 | 应取得的证据 |
|---|---|---|
| 1 | 现有 DPU 上选定人体/人脸模型，做 INT8 和真正删除通道的剪枝对照 | 同任务精度、实际输入下延迟、CPU/DPU 分工、帧龄与数据量 |
| 2 | 小模型单独复现 hls4ml 资源感知剪枝 | 固定源版本、训练数据、HLS 配置、原/剪枝模型布局布线资源和精度 |
| 3 | 阅读 SATAY、fpgaConvNet HLS 和板端驱动，分析实际流水与缓冲 | 列出能复用的组件、缺失的重建材料和 KV260 资源预算 |
| 4 | 测得预处理瓶颈后，评估普通 HLS 或 TAPA 实现 | 与当前实现同输入对照，端到端收益和联合资源/时序结果 |

FILM-QNN、NAF、H2PIPE 可以作为论文阅读与设计依据。当前不宜将其列成“已有可下载、可直接在 KV260 跑通的复现项目”。

## 9. 本次核查的固定点

| 仓库 / 分支 | 核查提交 | 提交日期（UTC） |
|---|---|---|
| hls4ml / hardware-aware-pruning | [d81b7f96788d0285c38f40eec085d1e3f3a84ae7](https://github.com/fastmachinelearning/hls4ml/commit/d81b7f96788d0285c38f40eec085d1e3f3a84ae7) | 2023-12-04 |
| AlexMontgomerie/satay / main | [dc0760ee0e9177008981755fb15cd9b9fddad8fc](https://github.com/AlexMontgomerie/satay/commit/dc0760ee0e9177008981755fb15cd9b9fddad8fc) | 2023-10-26 |
| ptoupas/amd-open-hardware-23 / main | [4c1108f78b959b653f83c7fdcaa0067fe550e42c](https://github.com/ptoupas/amd-open-hardware-23/commit/4c1108f78b959b653f83c7fdcaa0067fe550e42c) | 2023-09-04 |
| tuna/tapa / main | [d249ff92301c279d38e4af5e38ab54942c634346](https://github.com/tuna/tapa/commit/d249ff92301c279d38e4af5e38ab54942c634346) | 2026-09-21 |

核查深度为 README、相关源码、目录树、交付工件和原论文；“源码存在”“原板工件存在”“KV260 上复现成功”是三个不同证据等级。本报告确认前两类中已注明的项目，第三类尚需实际实验。
