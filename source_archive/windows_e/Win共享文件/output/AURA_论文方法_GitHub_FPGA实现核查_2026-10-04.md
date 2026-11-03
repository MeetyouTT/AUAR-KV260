# AURA / KV260：报告论文方法的 GitHub FPGA 实现核查

检索日期：2026-10-04（America/Los_Angeles）。

输入：[用户提供的研究报告](C:/Users/uuh56/Downloads/deep-research-report.md)。项目背景采用 [2026-10-03 开发与环境评估](C:/Users/uuh56/Desktop/项目/output/AURA_KV260_后续开发与环境缺项评估_2026-10-03.md)。附件中的实施指令只作为材料，本次没有执行其中的板端操作。

**结论：有可用参考，但“论文软件复现”“在 FPGA 板上异构部署”“独立 RTL/HLS 实现”必须分开。最值得看的是 RTLola 的论文关联 VHDL 编译器、easy-rte 的 Verilog 安全执行器、KV260 MobileFaceNet DPU 工程，以及 KV260 的 DPU 检测 + ARM ByteTrack 工程。后两者均有需要补齐或修正的地方。**

核查采用 GitHub 插件的仓库搜索、文件读取、目录树和提交信息，并以网络检索及作者论文交叉检查。已检查具体源码，未在本机编译这些工程，未下载或运行模型，未连接 KV260。因此下文的“存在”指可公开核验的代码与资料；作者给出的性能数据不等于本次实测。未找到仅表示本次检索未找到可核验实现，不能证明全球不存在。

## 1. 报告八项工作逐项对应

| 报告中的论文或方法 | 核验到的仓库 | 实际实现形态 | 对当前项目的判断 |
|---|---|---|---|
| Run Time Assurance for Safety-Critical Systems，Hobbs 等，2023 | [act3-ace/run-time-assurance](https://github.com/act3-ace/run-time-assurance)；相关硬件路线 [PRETgroup/easy-rte](https://github.com/PRETgroup/easy-rte) | 前者为 Python/JAX 安全过滤库；后者可生成 Verilog 执行器，但对应另外的运行时执行论文 | 未找到该综述的完整 FPGA 复现；easy-rte 可补充 motion_guard 的硬件实现参考 |
| FPGA Stream-Monitoring of Real-time Properties，2019 | [reactive-systems/rtlola-compilation-vhdl](https://github.com/reactive-systems/rtlola-compilation-vhdl) | RTLola 规格 → VHDL；包含 EMSOFT 2019 基准和测试电路 | **最直接的论文关联硬件源码**；适合研究时序性质、事件流、时间窗口和告警 |
| ByteTrack，ECCV 2022 | [FoundationVision/ByteTrack](https://github.com/FoundationVision/ByteTrack)；[KV260 检测跟踪工程](https://github.com/A46628/Detection_And_Tracking_Real_Time) | 作者实现是软件；KV260 工程为检测在 DPU、跟踪在 ARM/Python | 有异构部署参考，未核验到完整 ByteTrack 的 RTL/HLS 实现 |
| Light-ASD，CVPR 2023 | [Junhua-Liao/Light-ASD](https://github.com/Junhua-Liao/Light-ASD) | 作者模型、训练、评估和演示代码；软件推理 | 未找到可核验 FPGA 复现；适合作为当前 Windows 端基线 |
| MobileFaceNets，2018 | [whattflib123/kv260_face_recognition](https://github.com/whattflib123/kv260_face_recognition) | MobileFaceNet + SCRFD 的 INT8 DPU 模型、VART 推理及量化脚本 | **与当前 KV260/Vitis AI 路线最接近**；存在从零复现缺项 |
| MagFace，CVPR 2021 | [IrvingMeng/MagFace](https://github.com/IrvingMeng/MagFace) | 作者公开的精简软件实现及模型入口 | 未找到可核验 FPGA 复现；适合人脸质量评价对照 |
| LoCoNet，Active Speaker Detection | [SJTUwxz/LoCoNet_ASD](https://github.com/SJTUwxz/LoCoNet_ASD) | 作者软件训练、测试、配置和权重入口 | 未找到可核验 FPGA 复现；注意不要与铁路控制的 LocoNet 同名仓库混淆 |
| hls4ml 工具体系 | [fastmachinelearning/hls4ml](https://github.com/fastmachinelearning/hls4ml) | 模型转换为 HLS，实现 FPGA 推理 | 有真正的硬件生成工具；不等于已有 Light-ASD/MagFace 的完整移植 |

## 2. 优先看这四个工程

### 2.1 RTLola VHDL 编译器：论文关联最明确

仓库：[reactive-systems/rtlola-compilation-vhdl](https://github.com/reactive-systems/rtlola-compilation-vhdl)。

关联证据不仅是名称。包作者包括原论文作者 Jan Baumeister、Maximilian Schwenger；源码实际生成 VHDL，目录包含 [EMSOFT 2019 基准](https://github.com/reactive-systems/rtlola-compilation-vhdl/tree/master/benchmarks/emsoft_2019)、VHDL 模板及 GHDL 测试。[包定义](https://github.com/reactive-systems/rtlola-compilation-vhdl/blob/master/Cargo.toml)、[测试构建脚本](https://github.com/reactive-systems/rtlola-compilation-vhdl/blob/master/end_to_end_tests/bool_and_comp_test/build_script.py)。

作者论文的实验平台是 Zynq Z-7010/Artix-7 逻辑级别，不是 KV260。它证明了这种监控方法能落在 FPGA 上，不能直接把原论文的资源、功耗和响应时间当作 K26 的结果。[作者论文，§4](https://finkbeiner.groups.cispa.de/publications/emsoft19.pdf)。

**对 AURA 的用途：**把命令到达、序号、租约有效性、STOP 和输出许可看成流与时序性质，借鉴其规格和监控结构；无需同时搬入无人机或网络监控应用。

**源码中的实际限制：**当前生成函数遇到 trigger 会报未实现，并要求改用 output streams。可用布尔输出表达告警，再接到项目自己的输出许可逻辑；它本身不会自动提供 motion_guard 的 AXI ABI、PWM、恢复规则或运动限幅。[src/lib.rs，第 120—122 行](https://github.com/reactive-systems/rtlola-compilation-vhdl/blob/92817a1024fab6ff940b945dbba972c58f262f83/src/lib.rs#L120)。

建议先用一个小性质验证生成、仿真和综合，再决定是否引入编译器。也可仅借鉴结构，继续手写现有运动保护 RTL。

### 2.2 easy-rte：比单纯告警更贴近“拦截执行”

仓库：[PRETgroup/easy-rte](https://github.com/PRETgroup/easy-rte)。

它是相关工作补充，并非报告中 Hobbs 综述的对应复现。README 将其关联到 2020 年 Smart I/O Modules 论文，并延续 2017 年 Runtime Enforcement of Cyber-Physical Systems 的方法。

其思路是从策略与状态机生成执行器，阻止或修改违反规则的控制输出。已核验 [Verilog 生成模板](https://github.com/PRETgroup/easy-rte/blob/master/rtec/rteVerilogTemplate.go)、[Verilog 构建目标](https://github.com/PRETgroup/easy-rte/blob/master/Makefile) 和示例策略。它需要提供输入输出连接，不是现成 KV260 IP。

**对 AURA 的用途：**参考合法状态迁移、命令拒绝、输出禁能与恢复条件，生成或对照一个小保护模块。其声明的证明与模型检查适用于工具规定的语义；项目集成后的 AXI、计时、复位、PWM 和物理执行器行为仍需单独验证。

RTA 原报告论文是教程/综述。[act3-ace/run-time-assurance](https://github.com/act3-ace/run-time-assurance) 提供 Simplex、ASIF 等软件方法，但仓库对应的论文是 2023 ACC 的通用 JAX 框架，不能写成“原综述的 FPGA 代码”。简单 lease/范围检查也不能自动等同于完整的基于动力学模型的安全过滤证明。

### 2.3 KV260 MobileFaceNet：最贴近现有 DPU，但复现材料不完整

仓库：[whattflib123/kv260_face_recognition](https://github.com/whattflib123/kv260_face_recognition)。

核验到的内容包括：SCRFD 检测、人脸对齐、MobileFaceNet 特征提取、余弦数据库匹配、INT8 量化及编译脚本。模型目录实际包含 mobilefacenet.xmodel（1,482,000 字节）和 scrfd_det10g.xmodel（5,404,137 字节）；运行代码实际通过 XIR/VART 调用 DPU。[模型目录](https://github.com/whattflib123/kv260_face_recognition/tree/main/models)、[mfn.py](https://github.com/whattflib123/kv260_face_recognition/blob/main/mfn.py)、[编译脚本](https://github.com/whattflib123/kv260_face_recognition/blob/main/quantize/compile_mfn.sh)。

这属于 **MobileFaceNet 网络的 DPU 部署参考**，而非公开的专用 MobileFaceNet RTL。README 声称使用 Vitis AI 3.0 和 B4096；尚未核验模型二进制内部的架构指纹，也未实测其精度或速度。

静态检查发现：

- 重新量化脚本导入 mobilefacenet.MobileFaceNet，但公开目录中没有对应模型定义文件；原始 mobilefacenet.pt 权重和校准图片也未包含。因此推理材料比从零重建材料更完整。[量化脚本第 19 行](https://github.com/whattflib123/kv260_face_recognition/blob/c349c8e45e582c838c256fbac854a46a931025a3/quantize/quantize_mfn.py#L19)。
- 公开 demo 的入口是注册、单图识别和目录测试；没有完整相机持续运行入口。identify 仅选检测分数最高的一张脸，尚未按多个 track 逐一管理身份。[demo.py](https://github.com/whattflib123/kv260_face_recognition/blob/main/demo.py)、[pipeline.py](https://github.com/whattflib123/kv260_face_recognition/blob/main/pipeline.py)。
- Docker 使用 latest，没有锁定镜像；编译脚本硬编码环境路径。不能仅凭 README 的版本声明认定在你的开发机上可直接重建。
- 核验的公开目录未见 LICENSE。

**建议借鉴：**对齐、VART 输入输出缩放、embedding 和数据库接口。复现时补齐与权重一致的模型定义，固定工具环境，并对照你最终联合配置的 arch.json / DPU fingerprint。多人身份、质量门控、track generation、UNKNOWN 阈值和调度应由当前项目补齐。README 的速度与准确率只作为作者自述参考。

### 2.4 KV260 + ByteTrack：异构架构可参考，论文核心需要修正

仓库：[A46628/Detection_And_Tracking_Real_Time](https://github.com/A46628/Detection_And_Tracking_Real_Time)。

[inference_DPU/main.py](https://github.com/A46628/Detection_And_Tracking_Real_Time/blob/main/inference_DPU/main.py) 实际调用 VART 做 YOLO 推理；[trackers.py](https://github.com/A46628/Detection_And_Tracking_Real_Time/blob/main/inference_DPU/trackers.py) 调用 supervision.ByteTrack。因此硬件分工是：**检测网络在 PL/DPU，ByteTrack 在 PS/ARM 软件。**

源码存在两处对论文方法有实际影响的行为：

- main.py 用检测阈值先过滤所有检测框，同时用同一阈值设置 ByteTrack 的高置信度激活阈值。原作者实现会保留低于高阈值的一批框用于第二次关联；这里先过滤会使这批低分框无法进入跟踪器。[工程过滤逻辑第 135 行](https://github.com/A46628/Detection_And_Tracking_Real_Time/blob/010aa8c602bcdef12f1ed232b3678ea1fd896405/inference_DPU/main.py#L135)、[作者两阶段关联实现](https://github.com/FoundationVision/ByteTrack/blob/main/yolox/tracker/byte_tracker.py#L178)。
- ByteTrackAdapter 只在存在检测框时调用更新。空检测帧没有正常推进跟踪器，会影响 LOST 和轨迹寿命处理。[trackers.py 第 20 行](https://github.com/A46628/Detection_And_Tracking_Real_Time/blob/010aa8c602bcdef12f1ed232b3678ea1fd896405/inference_DPU/trackers.py#L20)。

所以该工程适合参考检测与跟踪的连接方式，不宜直接作为严格复现或最终运动目标管理基线。

**对 AURA 更稳的路线：**保留当前 DPU 人体检测，用 [作者 ByteTrack](https://github.com/FoundationVision/ByteTrack) 或 [独立 C++ 跟踪库](https://github.com/Vertical-Beach/ByteTrack-cpp) 接收检测结果。后者不绑定检测模型，适合接自己的 DPU 输出；需要交叉编译和验证，尚非现成板端二进制。两者都是软件跟踪器。再由项目增加帧时间、轨迹代次和失效后的停止续租规则。

## 3. MobileFaceNet 的其他硬件候选

| 仓库 | 实际核验结果 | 是否值得直接作为完整复现 |
|---|---|---|
| [zhixain/FPGA-Project](https://github.com/zhixain/FPGA-Project) | README 声称 PYNQ-Z1 + HLS；公开树主要是模型代码、PS 驱动和 C++ testbench。抽查卷积 testbench 只有函数声明，未见对应完整 HLS kernel、硬件工程或位流 | **否**。可参考接口与软件组织，不能仅凭性能表认定完整硬件源码已公开 |
| [ztszzz733/fpga-cnn](https://github.com/ztszzz733/fpga-cnn/tree/main/mobilefacenet) | 最新子目录明确为 8×8 脉动阵列 Conv/Depthwise；不支持完整网络的激活、残差等。根 README 的历史描述与当前子目录不同 | **否**。有真实 RTL，可研究算子，属于部分实现 |
| [Felixnsg/fpga-face](https://github.com/Felixnsg/fpga-face) | Cyclone IV / DE2-115 目标；README 明确进行中，部分基础模块已仿真，Depthwise 尚在实现 | **否**。未完成完整 MobileFaceNet 流水线 |
| [prajju-yatheesh/Face_Recognition](https://github.com/prajju-yatheesh/Face_Recognition) | 明确写当前在笔记本运行，KV260 是未来计划 | **否**。不能计为已部署 FPGA |
| [AleBera03/pynqz2-facial-recognition](https://github.com/AleBera03/pynqz2-facial-recognition) | 有 PYNQ-Z2 / DPU 人脸方案，但模型实际选 ResNet50，非 MobileFaceNet，且使用旧 DNNDK 路线 | 可参考身份业务，**不能列作 MobileFaceNets 复现** |
| [VectorBlox-SDK](https://github.com/Microchip-Vectorblox/VectorBlox-SDK) | 历史 release-v1.3.0 有 MobileFaceNet-ArcFace 转换和 FPGA 模型生成脚本，面向 Microchip PolarFire / VectorBlox | 有厂商加速器部署参考；**不能直接迁移为 AMD 自研 RTL** |

VectorBlox 核验到的 [历史脚本](https://github.com/Microchip-Vectorblox/VectorBlox-SDK/blob/release-v1.3.0/tutorials/mxnet/mobilefacenet-arcface/mobilefacenet-arcface.sh) 下载模型、转换并生成 VNNX，再进行仿真。当前 master 的目录树没有这一教程，但部分旧应用说明仍链接到它。因此需要固定历史版本，不能按旧说明直接使用当前 master。实际 FPGA 设计还依赖厂商参考设计/IP。

[Microchip 的门禁演示](https://github.com/MicrochipTech/iot_solutions_for_access_control) 明确说明其 GitHub 仓库不包含 FPGA 工程，而是提供定制步骤。这进一步说明“有 FPGA 演示”与“完整硬件设计开源”不同。

## 4. Light-ASD、MagFace、LoCoNet 与 hls4ml

**Light-ASD：**作者仓库提供论文对应的软件训练、评估、权重和视频演示。未找到可信的对应 RTL/HLS/DPU 移植。按当前项目分工先用 Windows 端软件基线，并保留音视频时间窗、对象代次与拒判。[作者仓库](https://github.com/Junhua-Liao/Light-ASD)。

**MagFace：**作者说明公开仓库是精简版，提供识别与质量评价流程；未核验到 FPGA 移植。质量评价依赖模型学到的特征幅值，不应把任意 MobileFaceNet 特征长度直接解释成 MagFace 质量。[作者仓库](https://github.com/IrvingMeng/MagFace)。

**LoCoNet：**正确仓库是 LoCoNet_ASD，提供环境、训练、测试与权重下载入口。搜索“LocoNet FPGA”会混入模型铁路总线项目，不能据此判断说话人检测有硬件实现。[作者仓库](https://github.com/SJTUwxz/LoCoNet_ASD)。

**hls4ml：**这是已公开的 FPGA 硬件生成工具。官方文档列出 Vitis HLS 后端，测试版本包括 2022.2—2024.1，与你现有工具版本相交。但整网可转换性仍取决于算子、形状、前端和后端组合，不是把任意 PyTorch 模型自动变成可用 KV260 核。[仓库](https://github.com/fastmachinelearning/hls4ml)、[官方支持状态](https://fastmachinelearning.org/hls4ml/intro/status.html)。

本轮适合用 hls4ml 做小网络或小算子的独立实验；现有 DPU 已有基线时，不建议仅因找到了工具就替换整条推理路线。

## 5. 对当前项目的取舍

以下是结合本地项目材料作出的工程判断，而非上述仓库已实现的 AURA 功能。

1. **A / PL 运动保护：**优先看 easy-rte 的输出约束状态机和 RTLola 的时序监控，把可借鉴部分落实到现有 motion_guard。自主实现仍应覆盖 AXI 原子提交、seq、epoch、lease、STOP、范围、速率和恢复。
2. **B / 视觉跟踪：**检测复用现有 DPU；跟踪采用原作者或独立 C++ ByteTrack。用 KV260 异构工程参考连接方式，修正低分框处理与空帧更新。
3. **B / 板端身份：**优先检查 KV260 MobileFaceNet 工程的推理接口；从固定图片开始，补齐从零模型重建材料，再接多人轨迹与身份服务。
4. **C / 说话人：**Light-ASD 保持作者软件基线。MagFace、LoCoNet 暂作对照研究，hls4ml 暂作独立硬件实验。

本地 10 月 3 日评估记载现有联合设计的布局/时序余量较紧；这只是项目历史证据，本次未重测。基于该条件，新增小型保护模块和复用 DPU 比并行加入完整人脸专核更符合当前状态。

如果你要“最像论文硬件复现”的源码，从 RTLola 开始；如果要“最贴现有 KV260 应用”的代码，从 MobileFaceNet DPU 工程和 ByteTrack 软件接口开始；如果要“最贴运动保护”的生成方法，从 easy-rte 开始。

## 6. 已核验的重点版本

以下提交通过 GitHub 提交接口核验；应固定版本再继续复现实验。

| 仓库 | 核验提交或版本 |
|---|---|
| rtlola-compilation-vhdl | [92817a1024fab6ff940b945dbba972c58f262f83](https://github.com/reactive-systems/rtlola-compilation-vhdl/commit/92817a1024fab6ff940b945dbba972c58f262f83) |
| easy-rte | [8c93b70270cb84305e75a3c3a080a7977ec86dc7](https://github.com/PRETgroup/easy-rte/commit/8c93b70270cb84305e75a3c3a080a7977ec86dc7) |
| kv260_face_recognition | [c349c8e45e582c838c256fbac854a46a931025a3](https://github.com/whattflib123/kv260_face_recognition/commit/c349c8e45e582c838c256fbac854a46a931025a3) |
| Detection_And_Tracking_Real_Time | [010aa8c602bcdef12f1ed232b3678ea1fd896405](https://github.com/A46628/Detection_And_Tracking_Real_Time/commit/010aa8c602bcdef12f1ed232b3678ea1fd896405) |
| fpga-cnn | [b650a147b9f5f64438febffd595ed1eaaf8301c0](https://github.com/ztszzz733/fpga-cnn/commit/b650a147b9f5f64438febffd595ed1eaaf8301c0) |
| hls4ml | [2ed80fb9a6d5150a7f1ec21a8cf6564900244a0e](https://github.com/fastmachinelearning/hls4ml/commit/2ed80fb9a6d5150a7f1ec21a8cf6564900244a0e) |
| VectorBlox MobileFaceNet 教程 | release-v1.3.0 |

核验到的许可证：RTLola VHDL 编译器为 AGPL-3.0；easy-rte、ByteTrack-cpp 为 MIT；hls4ml 为 Apache-2.0。两个优先 KV260 第三方工程的公开目录未见许可证文件；模型权重的条件也应与代码许可分别核对。

代表性检索组合包括 RTLola/VHDL/FPGA、MobileFaceNet/FPGA/Vitis/KV260、ByteTrack/FPGA/Vitis/Verilog、Light-ASD/FPGA、MagFace/FPGA、LoCoNet/active speaker/FPGA 和 runtime assurance/FPGA。仓库名称、README 的未来计划或论文引用本身都未被当作硬件实现证据。

