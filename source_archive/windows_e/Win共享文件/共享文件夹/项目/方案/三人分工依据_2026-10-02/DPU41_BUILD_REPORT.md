# KV260 DPU 4.1 独立对照构建

日期：2026-10-01。当前状态：**独立 DPU 4.1 对照工程已在主机完成构建、routed DCP 审阅与测试包准备；板端尚未加载或复测**。部署前问题见 [DEPLOYMENT_REVIEW.md](DEPLOYMENT_REVIEW.md)。

## 原因与修复范围

原样参考工程已成功构建，使用 DPU 4.0；其指纹为 `0x101000016010407`。原板 DPU 4.1 与原 ResNet18 XMODEL 要求 `0x101000056010407`。差异是 bit 30 的 SAVE Argmax。仅修改 arch.json、模型元数据或跳过 VART 检查不能解决真实硬件差异。

本次在独立目录使用官方 DPU 4.1 TRD 的完整 IP/wrapper/封装依赖，保留原模型。没有加入自研运动 IP，也没有操作板卡。原目录 `/home/ghmd/kv260-reference-2022.2-20260930` 的固定源码与构建成果继续保留；本次属于独立兼容性派生工程。

## 固定输入与实际改动

| 输入 | 版本/来源 |
|---|---|
| Kria 平台源码 | `xlnx_rel_v2022.2`，commit `a3a83f179503792226adf83082aee7c05de620b4`，由原本机源码独立 clone |
| 平台 XSA/XPFM/SPFM | 复用原成功构建的 `kv260_ispMipiRx_vcu_DP` 平台；逐字节核对并复制到 `platform/`，本轮不计为新构建成果 |
| DPU 依赖 | [AMD DPUCZDX8G_VAI_v3.0.tar.gz](https://download.amd.com/opendownload/xlnx/DPUCZDX8G_VAI_v3.0.tar.gz)，83,014,878 bytes |
| 归档 SHA-256 | `e720dacbc7462a62a1d4c83c34f66a89109eb381481b046c43d238db0c78133f` |
| 硬件工具 | 本机 `/home/ghmd/Xilinx_2022.2` 的 Vivado/Vitis 2022.2；只在构建进程加载环境 |
| 并行度 | synthesis/implementation jobs 均为 4；未采用原 Makefile 的默认 32 |

DPU 参数：B4096，单 CU；300/600 MHz；URAM enabled，UBANK IMG/WGT/BIAS 为 6/17/1；ALU default、ReLU6/leaky ReLU 与 SAVE Argmax enabled。AXI 数据口保持 GP0→HPC1、HP0→HP1、HP2→HP3，控制地址维持 `0xa0010000`。

独立源码改动集中在 benchmark 的 Makefile、dpu_conf.vh、封装脚本和 kernel XML。4.1 kernel XML 的 S_AXI_CONTROL range 为 0x1000。具体 patch 见 [compatibility_changes.patch](evidence/compatibility_changes.patch)，来源/配置/平台哈希见 [input_manifest.json](evidence/input_manifest.json)。没有修改厂商 DRC/Tcl 规则。

## 已执行与证据

入口为 [run_dpu41_build.sh](run_dpu41_build.sh)，依次执行：

```bash
bash /home/ghmd/kv260-dpu41-control-20261001/run_dpu41_build.sh xo
bash /home/ghmd/kv260-dpu41-control-20261001/run_dpu41_build.sh probe
bash /home/ghmd/kv260-dpu41-control-20261001/run_dpu41_build.sh overlay
```

| 步骤 | 实际状态 | 证据 |
|---|---|---|
| 官方归档下载及提取 | 通过；506 个归档条目安全提取 | `logs/dpu41_download.log`、`evidence/dpu41_archive.json` |
| 4.1 XO 封装 | 通过 | `logs/xo.log`、`binary_container_1/dpu.xo` |
| K26 IP generate_target 探针 | 通过 | `logs/probe.log`、`evidence/dpu41_probe_properties.txt` |
| 生成架构指纹 | `0x101000056010407`，与原模型匹配 | `evidence/dpu41_probe_arch.json`；SYS_IP_VER=0x41，SAVE_ARGMAX_ENA=1 |
| DPU 综合 | 0 Error，0 Critical Warning；有原始 warning | DPU OOC `runme.log`，06:13:01 退出；完整 synth step 06:14:51 完成 |
| 完整 link/实现/打包 | 通过；Vitis link、bitstream、SD 卡目录生成完成；确认运行返回码 0 | `logs/overlay.log`、`logs/overlay_confirmation.log`、`binary_container_1/link/vivado/vpl/prj/prj.runs/impl_1/runme.log` |
| routed DCP 审阅 | 通过报告生成；600 Warning、0 Error、实际 HDPR-5 为 0；时序通过，但 I/O delay 覆盖不全 | `logs/review_routed.log`、`evidence/postroute/`、`evidence/{drc_summary,timing_validation,resource_validation}.json` |
| 独立测试包与哈希 | 准备完成；14 个 bundle 文件校验通过 | `test_bundle/`、`logs/bundle_hash_check.log` |
| 板端加载及推理 | 未执行 | 本轮边界 |

首次 `overlay` 调用在 `make all` 成功结束后，因运行期间更新入口脚本留下的引号语法错误而以 2 退出；并非 Vitis link 失败。修复入口脚本并通过 `bash -n` 后，再执行 `overlay` 返回 0；该次为已构建目标的确认运行，XO、XCLBIN、BIT 前后 SHA-256 相同。两份原始日志均保留。

## 主机设备树验证问题与处理

本机 PetaLinux native `fdtoverlay` 为 DTC 1.6.1-dirty：候选 DTBO 与未经修改的原镜像 DTBO 都发生 `FDT_ERR_NOTFOUND`。外部 fixup 标签与目标节点 phandle 均存在。诊断副本表明，旧工具覆盖已有 target 节点 phandle，使重复 target 和导出符号后续查找失败。

上游 DTC 1.7.2 已增加 `overlay_prevent_phandle_overwrite`。在 `dependencies/dtc-1.7.2` 单独构建 fdtoverlay，无 sudo、无系统安装、更未替换板端工具。使用该工具，原 DTBO 与候选 DTBO 都合并成功。[上游实现](https://github.com/dgibson/dtc/blob/v1.7.2/libfdt/fdt_overlay.c)

候选 DTBO 复用原镜像 DTBO，仅改 `firmware-name` 为 `kv260-benchmark-b4096-dpu41.bit.bin`；已反编译对比确认唯一语义变化，保留 `fpga-config-from-dmabuf`、AFI、clocking、ZOCL 等属性。候选并未采用用于定位问题的删 phandle/symbol 诊断文件。证据见 [dtbo_validation.json](evidence/dtbo_validation.json)、[dtc172_merge_results.json](evidence/dtc172_merge_results.json)、`logs/*dtc172*merge.log` 和 [dtc_provenance.json](evidence/dtc_provenance.json)。主机合并通过不等价于 kernel overlay 或实际加载通过。

## 产物与待确认项

对原镜像根分区的只读提取确认：原运行时 `kv260-benchmark-b4096.bit.bin` 为 7,807,932 bytes，SHA-256 `7d12c877e0fde40a243d2350b1a2227f565788bf9e2dcae4439d07f213d40a3f`；前 64 字节与 Bootgen 默认完整输出一致，而与 `-process_bitstream bin` 的 headerless raw BIN 不同。此前原参考审阅将 raw BIN 当作已核实的正确板端格式，这一结论不适用于当前原镜像。独立测试包改为从**本次新 BIT**生成带 Bootgen 头的完整 PL BIN，并要求头部与原镜像匹配；不会使用原镜像的预编译 BIN 作为新成果。提取记录见 `logs/baseline_bin_extract.log`，提取文件见 `evidence/baseline-kv260-benchmark-b4096.bit.bin`，格式对照见 [baseline_bin_format.json](evidence/baseline_bin_format.json)。

新构建产物已在 [artifacts.json](evidence/artifacts.json) 和 [ARTIFACTS.sha256](evidence/ARTIFACTS.sha256) 登记：link 导出 XSA、XO、带 DPU 4.1 的 BIT/HWH、架构 `arch.json`、元数据 XCLBIN、routed DCP 和从新 BIT 生成的完整 Bootgen BIN。平台 XSA/XPFM/SPFM 标记为**复用**；staging/原镜像/TRD 自带预编译固件均不计为新硬件成果。XSA 内的 HWH 与独立 HWH 哈希相同；XSA 内的 `vpl_gen_fixed.bit` 与测试包 BIT 文件哈希不同，但自 `aa995566` 同步字起的配置 payload 逐字节相同，只有文件头差异；证据见 [xsa_bit_comparison.json](evidence/xsa_bit_comparison.json)。测试包及其 Bootgen BIN 均以 `sd_card/kv260_ispMipiRx_vcu_DP_wrapper.bit` 为准。

待确认：I/O delay 缺口及 DRC Warning 对目标用法的影响；新板端硬件指纹与 UUID；目标 FPGA manager 对本次 Bootgen 完整 BIN/dmabuf 的实际加载；同一 ResNet18、同一 Samoyed 图片及相同测量命令的复测。原图片路径/哈希和原性能测试参数尚未建立，不能直接把用户之前的分数/FPS 当作新构建验收。
