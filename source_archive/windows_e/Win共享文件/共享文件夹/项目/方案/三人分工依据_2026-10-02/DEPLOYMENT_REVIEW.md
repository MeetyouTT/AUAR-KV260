# KV260 DPU 4.1 独立对照工程：部署前审阅

日期：2026-10-01。结论：**主机构建、布线后检查和独立测试包准备完成；尚不能把它认定为板端已验收。** 本轮未换卡、加载应用、烧录或执行推理，也未改厂商 DRC 规则。固定源码 commit `a3a83f179503792226adf83082aee7c05de620b4`；修改与官方 DPU 4.1 TRD 来源见 [DPU41_BUILD_REPORT.md](DPU41_BUILD_REPORT.md) 和 [input_manifest.json](evidence/input_manifest.json)。原 DPU 4.0 参考工程和板卡基线保留。

## 已通过的主机检查

| 检查 | 结果和原始证据 |
|---|---|
| 构建和输出 | XO、DPU IP 生成、综合、Vitis link、实现及 bitstream 成功；`logs/xo.log`、`logs/probe.log`、`logs/overlay.log`、`logs/overlay_confirmation.log`。首次入口脚本在 `make all` 完成后遇到引号语法错误，修复后确认运行返回 0，主产物哈希未变。 |
| 布线 | 209,784 条需布线 net 全部布通，0 routing error；[route_status.rpt](evidence/postroute/route_status.rpt)。 |
| 已定义时序路径 | 最终 routed DCP：setup WNS `+0.001 ns`、TNS 0、失败端点 0/412,632；hold WHS `+0.009 ns`、THS 0、失败端点 0/412,554；pulse-width WPWS `+0.071 ns`、TPWS 0、失败端点 0/146,859；[timing_summary.rpt](evidence/postroute/timing_summary.rpt)。正裕量很小，新增逻辑必须重新实现核验。 |
| DRC 分类 | 600 条 Warning、0 Error；完整对象和文本在 [drc.rpt](evidence/postroute/drc.rpt)、[drc_objects.tsv](evidence/postroute/drc_objects.tsv)。HDPR-5 实际违规 0。 |
| 架构元数据 | 新 HWH 的 `SYS_IP_VER=0x41`、`SAVE_ARGMAX_ENA=1`、1 个 DPU CU 地址 `0xa0010000`；新 `arch.json` 为 `0x101000056010407`，与原 ResNet18 XMODEL 要求一致。XCLBIN 的 CU、地址和 GP0/HPC1、HP0/HP1、HP2/HP3 连接与参考一致；[compatibility_validation.json](evidence/compatibility_validation.json)。 |
| 独立包 | `test_bundle/` 的 14 个文件已通过 `sha256sum -c SHA256SUMS`；[bundle_hash_check.log](logs/bundle_hash_check.log)。候选 DTBO 在独立 DTC 1.7.2 上与原镜像基础 DTB 合并成功；仅 `firmware-name` 的语义改变；[dtbo_validation.json](evidence/dtbo_validation.json)。 |

## DRC 明细与 HDPR-5

以下数量来自**最终 routed DCP** 的 `report_drc -ruledecks default`，逐条对象记录见 [drc_objects.tsv](evidence/postroute/drc_objects.tsv)。所有列出的严重级别均为 Warning；不能仅因没有 Error 就忽略功能影响。

| 检查 | 数量 | 受影响对象和含义 |
|---|---:|---|
| AVAL-318 | 64 | DPU ALU 乘法树 DSP48E2；动态 PCIN/接地组合出现在非底部 DSP site，需审阅下方 DSP site 使用。 |
| DPIP-2 | 20 | DPU DSP 输入 pipeline 建议；可能影响性能裕量。 |
| DPOP-3 | 1 | DSP 输出 PREG pipeline 建议。 |
| DPOP-4 | 1 | DSP 输出 MREG pipeline 建议。 |
| REQP-1731 | 512 | DPU convolution PE 的 DSP48E2 pre-adder A 输入限制提示；需确认 26-bit 二补码/符号扩展条件。 |
| REQP-1934 | 1 | RAMB18E2 `NO_CHANGE` 读写碰撞 advisory。 |
| RTSTAT-10 | 1 | 无可布线负载的 net 汇总。 |

`src/kv260/overlays/examples/benchmark/binary_container_1/link/vivado/vpl/scripts/_vpl_pre_place.tcl:17` 是 Vitis 生成脚本，执行 `set_property SEVERITY {Warning} [get_drc_checks HDPR-5]`；`impl_1/runme.log:486` 的 Critical Warning 是**降低规则严重级别的提示**，不是 HDPR-5 命中。最终 DRC 规则和详情均没有 HDPR-5 项。该生成规则未被改动或隐藏，不能用“0 条 HDPR-5”推断其默认 Error 规则已原样执行。

## 时序约束范围和物理余量

[check_timing.rpt](evidence/postroute/check_timing.rpt) 给出 `no_clock=0`、`unconstrained_internal_endpoints=0`、`generated_clocks=0`；但 `no_input_delay=7`、`no_output_delay=9`。缺输入 delay 的端口为 IIC `scl/sda`、MIPI `data_p[0:3]`、`sdata_rx`；缺输出 delay 的端口为 IIC `scl/sda`、音频 `lrclk_rx/tx`、`mclk_out_rx/tx`、`sclk_rx/tx`、`sdata_tx`。这 16 个方向缺口使“全设计时序约束完整”**不成立**。若测试涉及这些接口，需要按板级时序补全约束并重跑实现；现有 setup/hold/pulse 通过仅适用于已覆盖路径。原始 [routed_constraints.xdc](evidence/postroute/routed_constraints.xdc)、[clock_interaction.rpt](evidence/postroute/clock_interaction.rpt)、[exceptions_coverage.rpt](evidence/postroute/exceptions_coverage.rpt) 均保留。异常覆盖报告存在 0% 项，应在涉及对应接口或新 IP 时逐条复核；未据此声称这些例外均有效。

资源使用来自实际 routed DCP 的 [utilization.rpt](evidence/postroute/utilization.rpt)、[utilization_hierarchical.rpt](evidence/postroute/utilization_hierarchical.rpt)：

| 资源 | 全设计 | DPU 层次 | 说明 |
|---|---:|---:|---|
| LUT | 70,110/117,120（59.86%） | 51,805 | 其余层次约 18,305；层次统计为综合映射资源，非一个独立可放置区域。 |
| FF | 131,725/234,240（56.24%） | 98,675 | 其余层次约 33,050。 |
| CLB site | 14,567/14,640（99.50%） | 未提供 DPU 独占 site 边界 | 只有 73 个完全空 CLB site，但已占 site 内可有空 LUT/FF；需实际 placement 判断。 |
| BRAM tile | 94.5/144（65.63%） | 75 等效 tile | DPU 为 70 RAMB36 + 10 RAMB18。 |
| URAM | 56/64（87.50%） | 48 | 余 8。 |
| DSP | 710/1,248（56.89%） | 710 | DPU 之外本次设计未用 DSP。 |

`Pblock=0`，可重配置 cell=0：这是完整静态 XRT_FLAT 设计，没有可预留给运动 IP 的独立 RP。未来最小 AXI-Lite 寄存器和 PWM 可以考虑接入现有静态控制路径，但**放置可行性未证明**；必须先明确 PWM 引脚、时钟/复位、AXI 地址与连接位置，再对加入 IP 后的整个设计重新综合、布局、布线、时序和 DRC。不能以全芯片 LUT/FF 剩余比例作放置保证。

## 产物类型与原板基线对照

主产物路径、字节数、SHA-256 集中在 [artifacts.json](evidence/artifacts.json)、[ARTIFACTS.sha256](evidence/ARTIFACTS.sha256)。其中平台 XSA/XPFM/SPFM 是原成功构建的逐字节复用输入；新构建成果是 link XSA、XO、XCLBIN、BIT、HWH、arch.json、routed DCP 及从新 BIT 生成的 BIN。link XSA 内的 HWH 与独立 HWH 哈希相同；其中 `vpl_gen_fixed.bit` 与 `sd_card` BIT 的文件头不同，但 `aa995566` 同步字之后的配置 payload 逐字节相同；[xsa_bit_comparison.json](evidence/xsa_bit_comparison.json)。运行包明确采用 `sd_card` BIT，并记录其哈希。

新 BIT 是 **xck26 的完整 PL bitstream**，不是可以叠在原 shell 上的 partial bitstream。原镜像运行时 `.bit.bin` 是带 Bootgen 头的完整 BIN；本次独立包从**新 BIT**以 ZynqMP PL BIF 生成同格式 BIN，前 64 字节与原镜像 BIN 相同。`-process_bitstream bin` 的 raw 输出没有相同头部，已明确排除于本包。新元数据 XCLBIN 的 BITSTREAM section 按官方 Makefile 移除，需与 BIN/DTBO 一起加载。完整格式证据见 [baseline_bin_format.json](evidence/baseline_bin_format.json)。

新 XCLBIN UUID `fffc3c97-c2d3-8e30-acd1-6fc7c367c274`，原板 UUID `eedb44e9-3f77-0244-9ea9-23b953894638`。原板 PetaLinux 2022.2、XRT/ZOCL 2.14、VART 3.0、DPU 4.1、1 CU `0xa0010000`；原 XMODEL SHA-256 `4d4d669c84b6d5aa6f731b389ebcf0f51fb1449752cf5fa4a4beddd496c3c0ef`，要求架构 `0x101000056010407`。本次主机文件的架构/地址/连接匹配，只说明**静态元数据兼容**，板卡 FPGA manager、ZOCL 和 VART 的实际互操作尚未测。

## 独立包、问题与待确认

应用目录为 [kv260-benchmark-b4096-dpu41](test_bundle/lib/firmware/xilinx/kv260-benchmark-b4096-dpu41/)，包含 `.bit.bin`、`.dtbo`、`.xclbin`、`shell.json` 四个运行文件。`shell.json` 声明 `XRT_FLAT`、1 slot；DTBO `firmware-name` 精确为 `kv260-benchmark-b4096-dpu41.bit.bin`，保留原 AFI/clocking/zocl 与 `fpga-config-from-dmabuf`。测试包副本和完整来源放在 `test_bundle/provenance/`，不能把其中的合并 DTB 或审阅文件复制到板卡 `/boot`。本机 PetaLinux DTC 1.6.1-dirty 合并原/新 DTBO 都报 `FDT_ERR_NOTFOUND`；独立 DTC 1.7.2 对原/新均成功。这是主机验证工具差异，目标板 kernel/dfx-mgr 加载仍待实测；见 [dtc172_merge_results.json](evidence/dtc172_merge_results.json)。

当前实际问题：16 个 I/O delay 方向缺口；600 条需审阅的 Warning（尤其 AVAL-318 与 REQP-1731）；setup 裕量仅 0.001 ns；DTC 1.6.1 主机合并失败但 DTC 1.7.2 通过；尚无新设计的板端加载/推理证据。待确认：原 Samoyed 图片路径与 SHA-256、原性能程序及参数；目标板的实际硬件架构寄存器、UUID、加载日志和同一模型/图片的 Top-1/FPS。历史 Top-1 `0.949879`、单/双线程 `214.381/238.479 FPS` 仅作原基线记录。

独立测试卡的原基线保存、候选包安装、`xmutil` 切换、同模型同图复测与换回原卡恢复步骤见 [TEST_CARD_PLAN.md](TEST_CARD_PLAN.md)。完成前先核对原图及测试命令，并在测试卡上先复测原 app；原卡保持原样。本报告**不授权也不表示已经执行板端切换**。
