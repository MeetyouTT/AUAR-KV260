# 已构建工程评价与后续自建 DPU 的影响

审阅日期：2026-10-02。工作目录：`/home/ghmd/kv260-dpu41-control-20261001`。

## 结论

**当前 DPU 4.1 工程的固定输入推理验证通过，能够作为后续修改的开发对照；外围接口完整验收、长期运行、反复热切换和加入新 IP 后的实现可行性仍未证明。**

本轮读取已有构建及板端原始证据，重新校验工件和证据索引，查阅对应版本的 AMD 官方资料。没有重新构建、切换板端应用或重新运行板端推理。以下板端结论来自 UTC 2026-10-02 07:52:43 至 08:48:24 的已完成测试；最后成功核验为官方应用运行、候选应用 inactive，不能用历史记录代替未来操作前的实时状态检查。

## 1. 具体构建了什么

| 工程 | 内容与定位 |
|---|---|
| `../kv260-reference-2022.2-20260930` | 固定官方参考源码的原样平台与 benchmark 构建，DPU 4.0 架构指纹为 `0x101000016010407`。这份设计未作为兼容原 ResNet18 的候选上板成果。 |
| 当前 `kv260-dpu41-control-20261001` | 在独立工程中使用官方 Vitis AI 3.0 的 DPU 4.1 IP，匹配原模型要求并构建、部署、复测。没有加入运动 IP。 |

参考源码固定为 `Xilinx/kria-vitis-platforms` 的 `xlnx_rel_v2022.2`，commit `a3a83f179503792226adf83082aee7c05de620b4`。当前独立工程包含已登记的 Makefile、DPU 配置、kernel XML 和 IP 打包脚本改动，不能称其为未改动的官方原样工程。

实际 DPU 配置为 B4096、1 CU、300 MHz 主时钟、600 MHz 倍频、URAM enabled，控制地址 `0xa0010000`，架构指纹 `0x101000056010407`。工具链为 Vivado/Vitis/PetaLinux 2022.2，板端为 XRT/ZOCL 2.14、VART 3.0，沿用 XRT/ZOCL 与 overlay 路线。

新生成的工件包括 XO、link 导出 XSA、BIT、HWH、arch.json、XCLBIN、routed DCP 和从新 BIT 生成的完整 Bootgen BIN。平台 XSA/XPFM/SPFM 是从原参考工程复用的输入。完整登记见 [artifacts.json](evidence/artifacts.json)；镜像或 staging 中的预编译固件不计入新构建成果。

## 2. 已通过的验证

| 项目 | 实际证据 |
|---|---|
| 工件与证据完整性 | 本轮再次执行 `sha256sum --check --quiet evidence/ARTIFACTS.sha256 evidence/candidate_board_20261002.sha256`，返回 0；分别覆盖 15 项和 104 项。 |
| 实际硬件加载 | 候选 FPGA manager 为 operating；UUID 和 IP 内部生成标记与官方对照不同，实际指纹、地址和时钟符合预期。 |
| 同模型、同图片分类 | Samoyed Top-1 为 0.949879；Top-5 在程序打印精度下与官方对照完全一致。 |
| 单线程性能 | 三次 60 秒测试中位数 214.944 FPS；官方为 214.961 FPS。 |
| 双线程性能 | 三次 60 秒测试中位数 238.826 FPS；官方为 238.777 FPS。 |
| 一次切换与恢复 | 完成官方→候选→官方，并核验官方固件、实际 DPU 标记、默认 VART 路径与恢复后的同图分类。 |
| 已约束路径时序 | Setup WNS +0.001 ns、hold WHS +0.009 ns、pulse-width WPWS +0.071 ns；三类失败端点均为 0。 |

性能与官方基本相当，不据此宣称性能提升。FPS 来自预加载、预缩放图片的 benchmark，不包含摄像头采集、逐帧 JPEG 读盘解码或运动控制整条流程。单模型、单图片的结果也不能证明其他模型或完整场景的准确率。

板端证据及限制见 [CANDIDATE_BOARD_TEST_REPORT.md](CANDIDATE_BOARD_TEST_REPORT.md) 和 [candidate_board_summary.json](evidence/candidate_board_20261002/candidate_board_summary.json)。`DPU41_BUILD_REPORT.md` 是主机构建阶段的历史记录，其板端未测试状态应结合后续板端报告阅读。

## 3. 仍需处理的实际问题

### 布局与时序余量

最终 routed 设计的 LUT 为 59.86%、FF 为 56.24%、DSP 为 56.89%、BRAM 为 65.63%、URAM 为 87.50%。CLB site 使用 14,567/14,640，即 99.50%。

CLB site 是已经被逻辑占用的物理位置；已占 site 内仍可能存在空 LUT/FF。因此 99.50% 不能解释成所有逻辑资源只剩 0.50%，也不能根据 LUT 还剩约 40% 保证新 IP 可放下。布局、布线、控制集和时序均需对修改后的设计实际实现验证。现有 setup 裕量仅 +0.001 ns，没有证明后续扩展的时序余量。

当前没有 Pblock 或可重配置 cell，为完整静态 XRT_FLAT 设计。加入自研寄存器或 PWM 后，需要将 DPU 和新模块放进同一硬件设计重新实现；加载另一份完整 PWM 位流会替换现有 PL 配置。原始资源报告见 [utilization.rpt](evidence/postroute/utilization.rpt) 和 [utilization_hierarchical.rpt](evidence/postroute/utilization_hierarchical.rpt)。

### 约束和 DRC

`no_clock=0`、`unconstrained_internal_endpoints=0`，但有 7 个 input delay 和 9 个 output delay 方向缺口，涉及 IIC、MIPI 和音频。全设计完整时序约束的结论不成立；使用对应接口前需要核对并补齐实际板级约束。

最终 DRC 为 600 条 Warning、0 Error：AVAL-318 为 64，DPIP-2 为 20，DPOP-3/4 各 1，REQP-1731 为 512，REQP-1934 为 1，RTSTAT-10 为 1。实际 HDPR-5 违规为 0；Vitis 生成脚本降低该检查严重级别的提示仍保留，不能把它混同为实际违规，也不能声称该规则默认严重级别未经修改。没有为了消除警告修改厂商规则。

原始证据见 [timing_summary.rpt](evidence/postroute/timing_summary.rpt)、[check_timing.rpt](evidence/postroute/check_timing.rpt)、[drc.rpt](evidence/postroute/drc.rpt)。详细分类见 [DEPLOYMENT_REVIEW.md](DEPLOYMENT_REVIEW.md)。

### 板端 overlay 生命周期

卸载官方和卸载候选时均实际触发 `/axi/zyxclmm_drm` 的节点引用计数错误：expected 1、actual 2。官方基线也存在属性生命周期警告。问题实际持有者及完整 kernel/ZOCL patch 来源尚未确认，不能直接归因于候选 DPU RTL；恢复官方应用不会修复该释放路径。

因此一次加载、推理和恢复通过，不代表长期反复热切换可靠性通过。当前不应增加无目的的切换次数。

## 4. 后续“自建 DPU”有哪些影响

| 路线 | 可复用内容 | 主要影响 |
|---|---|---|
| 使用官方 DPU IP，自行配置并集成 | 当前工程、工具链、模型部署和运行时流程 | 当前已经完成这一类工作。以后可在独立工程修改公开配置、连接和外围模块；每次修改都需重新检查资源、时序、配套工件与板端行为。 |
| 从零编写自己的神经网络加速器 RTL | KV260 平台、AXI/DDR 连接经验、测试和恢复流程；现有 DPU 可作性能及数值对照 | 自有指令集、算子和数据格式通常需要配套编译或代码生成、运行时、驱动及数值一致性验证；不能假定现有 XMODEL/VART 可以直接驱动它。 |
| 保留 DPU，只训练或更换模型 | 现有硬件与运行环境 | 在模型及算子支持条件满足时，完成量化、按当前架构编译和部署，通常可复用位流；仍需实际验证模型行为与性能。 |

官方 DPU 的公开配置和接口支持自主集成。本工程使用的核心 HDL 中有 `pragma protect begin_protected`，例如 `dependencies/DPUCZDX8G_VAI_v3.0/dpu_ip/DPUCZDX8G_v4_1_0/hdl/DPUCZDX8G_v4_1_0_vl_top.sv:17`；它不是可直接任意改写内部实现的完整明文 RTL。

模型兼容性需区分：

- 修改 B4096 规模或影响指令集/算子能力、架构指纹的配置：生成新 `arch.json`，使用匹配工具重新编译对应量化模型，核对新的 XMODEL 与实际 DPU 要求。不能编辑指纹文件或跳过校验来获得兼容性。
- 只增加外围 AXI-Lite 模块，DPU 架构和指纹保持一致：通常可以保留当前 XMODEL，但需要重新实现整个硬件，更新对应元数据/设备树，并复测 DPU。时钟或其他非模型相关配置变更也仍需重新核验实际架构和运行条件。
- 不是每个 DPU 参数变化都必然要求重新编译模型。当前官方 `dpu_conf.vh` 将架构规模、RAM_USAGE、CHANNEL_AUGMENTATION、ALU 等列为模型相关，而 URAM/DRAM 选择注释明确为不需要更新模型。仍以生成架构和实际模型要求核验结果为准。

AMD 说明 `arch.json` 用于模型编译，DPU 配置修改后需生成相应架构描述；DPU 执行 XMODEL 中针对其指令集编译的指令。见 [UG1414：DPU](https://docs.amd.com/r/3.0-English/ug1414-vitis-ai/Deep-Learning-Processor-Unit) 与 [Vitis AI 3.0：DPU 系统集成](https://xilinx.github.io/Vitis-AI/3.0/html/docs/workflow-system-integration.html)。从自有指令集通常需要额外编译与运行时适配的结论，是基于该机制的工程推断。保持当前 Vitis/XRT 路线有利于复用现有运行环境；若改为纯 Vivado 的独立 VART 集成，官方文档要求的 VART/XRT 组合不同，不能直接混用。

## 5. 适合当前项目的下一步

以 DPU 与运动 IP 共存为目标时，先保留已验证 DPU 配置，在新的独立工程加入最小 AXI-Lite 寄存器：`IP_ID`、`ABI_VERSION`、`BUILD_ID` 和读写 scratch。先验证 CPU 能访问这些寄存器、DPU 原分类仍一致，然后再加入监督和 PWM；暂不连接执行器。

每一步重新进行综合、布局布线、时序/DRC 审阅和必要的板端验证。若实际实现难以收敛，再评估更小 DPU 配置或降低时钟等方案；目前没有证据保证第二个 B4096 可以放入，也不能按资源比例预测 FPS。

当前原卡、官方固件和恢复证据保持为运行对照，不会妨碍另建工程。后续约束来自芯片物理资源、时序以及模型/运行时兼容性，而非保存对照本身。

## 6. 本轮改动与未执行事项

新增本报告与独立审阅清单 `evidence/build_assessment_20261002/review_manifest.json`、`SHA256SUMS`；不改已有报告、厂商源码、硬件工件或既存 SHA 索引。

本轮未重新完成任何板端核验。此前新建系统终端的独立核验记录位于 `evidence/official_restore_20261002T102513Z`，仅记录建立串口会话及不完整输入，没有完整状态命令结果或恢复结果；用户纠正为新 Codex 对话后已停止后续动作。这份记录不列为通过证据。当前评价使用前述已经完整完成的候选测试与恢复证据。
