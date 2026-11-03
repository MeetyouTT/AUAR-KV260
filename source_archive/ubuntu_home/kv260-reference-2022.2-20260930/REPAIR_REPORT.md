# KV260 2022.2 Clocking Wizard 阻塞修复与官方参考构建结果

更新日期：2026-10-01。源码固定为 `Xilinx/kria-vitis-platforms` `xlnx_rel_v2022.2` commit `a3a83f179503792226adf83082aee7c05de620b4`。未改官方源码、厂商 Tcl、速度参数或时钟模块；未烧录、部署或重启板卡，也未将 `staging` 中的预编译固件算作本轮成果。

## 结论

阻塞原因已由安装记录和同一探针的前后对照确认：原 Vivado 安装有 Kria SOM/Starter Kit 支持，因此能枚举 K26/KV260；但缺少通用 `Zynq UltraScale+ MPSoC` 器件组件。Clocking Wizard 在查询 K26 MMCM 速度参数时收到错误文本 `Unable to get value from speedsfile for keyword MM`，因把该文本当浮点数解析而失败。向现有 Vivado 2022.2 增补 MPSoC 器件支持后，原探针通过，最小 IP 综合完成，随后官方 platform 和 B4096 benchmark overlay 均构建成功。

这确认了安装缺少器件组件是本机故障的修复原因；`MM` 是失败查询返回的键值文本，不能据此推断某个单独速度文件或伪造参数。厂商脚本和速度数据没有被直接改动。构建完成不等于板端部署或推理已验收。

## 原始故障与诊断证据

1. 首次 platform 日志 `logs/platform_vivado_first.log` 中，最早致命错误是 `expected floating-point number but got "Unable to get value from speedsfile for keyword MM"`；随后错误定位到 `clk_wiz_audio` 的 `create_bd_cell`，调用从 `scripts/main.tcl`、`scripts/config_bd.tcl` 进入音频子系统创建流程。
2. `evidence/probe_clk_wiz.tcl` 在独立 K26 工程中重现同错，排除了平台 BD、DPU 和固定仓库代码作为触发条件。沙箱外、C locale、干净环境的对照均已在先前诊断中完成，本轮没有重复。
3. 原安装记录 `evidence/installer/installed_modules_before_add.txt` 只有 `Xilinx_Kria_Som` 对应的 Kria 支持；没有 `Zynq_MPSoC_WP`。`logs/probe_device_parts.log` 中 K26 和 KV260 可列举，但 ZCU102/ZCU104 为空。由此证明“可枚举 Kria 器件”并不代表 Clocking Wizard 所需的器件速度数据可正常使用。
4. `clk_wiz_v6_0_utils.tcl` 中的 `GetClkwizProperty` 会从 IP 速度数据查询器取回 MMCM 参数。原始错误表示查询结果不是可解析数值；不单独证明是某一速度文件损坏，也不能用补写参数绕过。
5. AMD 2022.2 官方安装说明支持为现有工具安装增补器件。Xilinx 官方 GitHub 上有相同错误字符串的记录，但该记录没有确认修复，因此仅用作症状对照。

## 实际修复

- 用户在本机安装器自行生成有效认证令牌；凭据和令牌没有写入本报告。
- 初次用 Vitis 产品配置的尝试没有选中有效器件包；选择父级时预估需下载约 66 GB，未开始安装。随后改用 AMD 2022.2 安装器的 **Vivado ML Standard** 配置，仅选择 `Zynq UltraScale+ MPSoC`，其余器件组件关闭，目标仍为现有 `/home/ghmd/Xilinx_2022.2`。预检列出 57 个归档、约 3.14 GB。
- 按要求先核查了 `/home/ghmd/Xilinx`、`/home/ghmd/Xilinx_2022.2`、`/opt`、`/tools`、`/usr/local`、`/mnt`、`/media` 等旧安装位置，没有发现另一套完整可启动的 Vivado 2022.2。Add 操作前已备份原 Vivado 树与安装器记录/注册表，回退材料保留在 `installation_backup/`；本次增补正常完成，无需回退。
- 使用 `/home/ghmd/Xilinx_2022.2/.xinstall/Vitis_2022.2/xsetup -x -a XilinxEULA,3rdPartyEULA -b Add -c /home/ghmd/kv260-reference-2022.2-20260930/evidence/installer/install_config_vivado_mpsoc.txt` 执行增补，没有重装 Vivado、升级版本或覆盖源码。安装日志的邮件地址已在交付副本中遮盖；原始日志保留于 `evidence/installer/`。
- 当前安装记录显示 `Zynq_MPSoC_WP`（值 `Zynq UltraScale+ MPSoC`）和 `Xilinx_Kria_Som` 均已登记，产品仍为 VitisProd。安装器配置和已遮盖日志位于 `evidence/installer/install_config_vivado_mpsoc.txt`、`evidence/final_build/sanitized_installer_logs/`。
- 补装后 K26/KV260 仍能枚举；ZCU104 现在可枚举，ZCU102 仍未枚举。此安装是 Vivado ML Standard；这个余项不影响本次 K26/KV260 工程，但不能据此认为所有 MPSoC 器件都已安装。

## 修复后的验证与构建

| 阶段 | 结果 | 证据 |
| --- | --- | --- |
| K26 Clocking Wizard 最小探针 | 成功创建 `clk_wiz`；PART=`xck26-sfvc784-2LV-c`，BOARD=`xilinx.com:kv260_som:part0:1.4` | `logs/probe_clk_wiz_after_vivado_add.log` |
| Clocking Wizard IP 输出产品与独立综合 | 成功；综合状态 `synth_design Complete!`，进度 100% | `logs/clk_wiz_postrepair_synth.log`、`evidence/clk_wiz_postrepair/clk_wiz_synth_utilization.rpt`、`clk_wiz_synth_timing_summary.rpt` |
| `bash run_reference_build.sh platform` | 成功导出 XSA 与 XPFM | `logs/platform_after_repair_unrestricted.log` |
| `bash run_reference_build.sh overlay` | 成功完成 DPU XO 打包、Vitis `v++ --link`、Vivado 实现、写 BIT、生成 XCLBIN 并打包 SD 目录 | `logs/overlay_after_repair_unrestricted.log`、构建目录内 Vitis/Vivado 日志 |

Platform 和 overlay 在受限环境中的首轮运行都被本机 HLS/Vitis 工具申请本地端口的权限限制中止；未更改工程绕过。分别在允许工具正常使用本机端口的进程环境完整重跑后成功。platform 日志中 Vivado 为 v2022.2，SW Build 3671981、IP Build 3669848；Vitis 日志中 `v++` 为 v2022.2、SW Build 3671529，XRT build 2.14.0。

源码配置核验：`benchmark/dpu_conf.vh` 定义 `B4096`；`prj_conf/prj_config_1dpu` 指定一个 `DPUCZDX8G_1`，时钟 300/600 MHz，内存端口连接 HPC1/HP1/HP3。`xclbinutil --info` 确认生成文件来自 v++ 2022.2、FPGA `xck26`、平台 VBNV `xilinx_kv260_ispMipiRx_vcu_DP_kv260_ispMipiRx_vcu_DP_1_0`，kernel 为 `DPUCZDX8G`。这只验证本次构建配置与元数据，不代表与现有板端镜像位流同源或兼容。

## 新构建产物

下面均为本轮固定源码和安装环境生成的文件。部署包集中在 benchmark 的 `binary_container_1/sd_card/`；`dpu.xclbin` 中 BITSTREAM section 已由官方打包步骤剥离，独立 `.bit` 与 `.xclbin` 一同交付。

| 类型 | 相对路径 | 大小 |
| --- | --- | ---: |
| Platform XSA | `src/kv260/platforms/vivado/kv260_ispMipiRx_vcu_DP/project/kv260_ispMipiRx_vcu_DP.xsa` | 78,788,869 B |
| Platform XPFM | `src/kv260/platforms/xilinx_kv260_ispMipiRx_vcu_DP_202220_1/kv260_ispMipiRx_vcu_DP.xpfm` | 610 B |
| Overlay DPU XSA | `src/kv260/overlays/examples/benchmark/binary_container_1/dpu.xsa` | 5,884,901 B |
| DPU XO | `src/kv260/overlays/examples/benchmark/binary_container_1/dpu.xo` | 1,392,413 B |
| XCLBIN | `src/kv260/overlays/examples/benchmark/binary_container_1/dpu.xclbin` | 39,058 B |
| BIT | `src/kv260/overlays/examples/benchmark/binary_container_1/sd_card/kv260_ispMipiRx_vcu_DP_wrapper.bit` | 7,797,826 B |
| HWH | `src/kv260/overlays/examples/benchmark/binary_container_1/sd_card/kv260_ispMipiRx_vcu_DP.hwh` | 1,298,039 B |
| DPU 架构描述 | `src/kv260/overlays/examples/benchmark/binary_container_1/sd_card/arch.json` | 36 B |
| XCLBIN（SD 目录副本） | `src/kv260/overlays/examples/benchmark/binary_container_1/sd_card/dpu.xclbin` | 39,058 B |

SHA-256 清单 `evidence/final_build/ARTIFACTS.sha256` 覆盖上述工件、构建日志、关键配置、IP 最小综合结果和路由后报告，可在工作区根目录运行 `sha256sum -c evidence/final_build/ARTIFACTS.sha256` 复核。路由后资源与时序报告也复制到 `evidence/final_build/reports/` 便于查阅。

## 实现资源、时序与警告

路由后 `impl_1_full_util_routed.rpt` 与 `impl_1_kv260_ispMipiRx_vcu_DP_wrapper_timing_summary_routed.rpt` 显示：

| 指标 | 实测 |
| --- | ---: |
| LUT | 69,615 / 117,120（59.44%） |
| FF | 131,094 / 234,240（55.97%） |
| BRAM tile | 94.5 / 144（65.63%） |
| URAM | 56 / 64（87.50%） |
| DSP | 710 / 1,248（56.89%） |
| MMCM / PLL | 2 / 1 |
| WNS / TNS | +0.001 ns / 0 ns，0 个 setup 失败端点 |
| WHS / THS | +0.010 ns / 0 ns，0 个 hold 失败端点 |
| WPWS | +0.071 ns，0 个脉宽失败端点 |

Timing Summary 报告 `All user specified timing constraints are met.` DRC 在 placement 阶段报告 0 errors、63 warnings；写 bitstream 前报告 0 errors、579 warnings，bitstream 写出成功。日志还包含关键警告 `[Vivado 12-4430]`：Vitis 生成的实现流程降低了 DRC `HDPR-5` 的 severity，Vivado 文本提示这可能影响板上运行安全或功能。我们未改该脚本，也没有板端运行验证；在任何后续硬件部署前应审阅对应 DRC 检查及 Vitis 生成流程的严重级别设置。其他数百条 DRC warning 也保留在完整 `binary_container_1/logs/link/vivado.log` 与 `link/vivado/vpl/prj/prj.runs/impl_1/runme.log` 中，不能仅凭 timing closure 忽略。

## 下一步板端复测边界

当前官方板卡、SD 卡、QSPI 和固件均未修改。新 BIT、HWH、arch.json、XCLBIN 虽已打包，尚未证明它们能与板上的现有运行时、设备树、Vitis AI 运行时及模型配合，也没有在板上重跑 ResNet18。后续按 [REPORT.md](REPORT.md) 中的独立测试卡方案操作：先保存原卡与原始模型/图片/命令的校验和，制作独立测试卡并核对应用包命名与 DTBO `firmware-name`，在测试卡确认 DPU CU 后再用同一 XMODEL、同一图片、相同预处理和线程数复测；原卡作为可回退基线保留。

## 官方资料

- [AMD UG973 2022.2：增补工具与器件](https://docs.amd.com/r/2022.2-English/ug973-vivado-release-notes-install-license/Adding-Additional-Tools-and-Devices)
- [AMD UG973 2022.2：命令行安装器与 Add 操作](https://docs.amd.com/r/2022.2-English/ug973-vivado-release-notes-install-license/Running-the-Installer)
- [AMD UG973 2022.2：各 Vivado 版本支持的器件](https://docs.amd.com/r/2022.2-English/ug973-vivado-release-notes-install-license/Supported-Devices)
- [AMD UG896 2022.2：IP 输出产品和 Tcl 流程](https://docs.amd.com/r/2022.2-English/ug896-vivado-ip/Using-IP-Tcl-Commands-In-Design-Flows)
- [Xilinx GitHub：相同 Clocking Wizard 错误字符串的讨论](https://github.com/Xilinx/open-nic-shell/discussions/46)（症状参考，未给出经验证修复）
