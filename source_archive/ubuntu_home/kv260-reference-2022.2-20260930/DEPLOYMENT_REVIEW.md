# KV260 官方参考平台：部署前审阅

审阅日期：2026-10-01  
源码固定版本：`Xilinx/kria-vitis-platforms` `xlnx_rel_v2022.2`，commit `a3a83f179503792226adf83082aee7c05de620b4`。  
部署结论：**HOLD，不得将本次构建切换到原基线板卡。** 本轮只读板端证据、审阅主机产物并准备隔离 bundle；没有向板卡写入、加载或卸载任何固件。

后续主机核查已定位指纹差异：固定参考工程采用 DPU 4.0，原板采用 4.1；两者仅差 bit 30 的 SAVE Argmax 标志。具体处理路径、编译器核验、DTBO 差异以及资源表述修正见 [COMPATIBILITY_NEXT_STEPS.md](COMPATIBILITY_NEXT_STEPS.md)。旧审阅版本及其清单已归档，原始 Vivado 报告保持原样。

**BIN 格式更正（2026-10-01）：**对原官方镜像根分区只读提取后，原运行时 `kv260-benchmark-b4096.bit.bin` 的 SHA-256 为 `7d12c877e0fde40a243d2350b1a2227f565788bf9e2dcae4439d07f213d40a3f`，大小 7,807,932 bytes，文件头与 Bootgen 默认生成的完整 PL BIN 一致。此报告早期把 headerless/raw BIN 判为该镜像正确的运行时格式，是错误结论；以下相关条目已更正。原参考候选 bundle 保留供审阅，**不得把其中 raw BIN 部署到该镜像作为已验证方案**。提取日志与原 BIN 只读副本在独立工作区 `../kv260-dpu41-control-20261001/logs/baseline_bin_extract.log` 和 `../kv260-dpu41-control-20261001/evidence/baseline-kv260-benchmark-b4096.bit.bin`。

## 审阅结果

| 项目 | 状态 | 证据/结论 |
|---|---|---|
| DRC 规则运行 | 通过（有警告） | 最终 routed DCP 的默认规则集共 579 条，均为 Warning、0 Error；分类见下表。完整原始报告已保留。 |
| HDPR-5 | 未发现实际违规 | 最终 DRC 报告没有 HDPR-5 条目。日志里的降级提示由 Vitis 生成的 `_vpl_pre_place.tcl:17` 将 HDPR-5 从 Error 降到 Warning 引起；这是规则严重级别修改提示，不是检查命中的违规。未修改厂商规则或生成脚本。 |
| 内部时序 | 通过 | 409,870 setup endpoints、409,792 hold endpoints、145,695 pulse-width endpoints 均 0 failing；WNS +0.001 ns、WHS +0.010 ns、WPWS +0.071 ns。 |
| 完整 I/O 时序覆盖 | 未通过/待设计约束确认 | 7 个输入没有 input delay，9 个输出没有 output delay；内部 unconstrained endpoints 为 0 不代表这些 I/O 被约束。涉及 I²C、MIPI 输入和音频接口。 |
| 静态区/RP/Pblock | 无 RP/Pblock | routed DCP `PBLOCK_COUNT=0`；这是完整静态 XRT_FLAT bitstream，不是带已预留可重配置区的 DFX shell。 |
| 小型 AXI-Lite/PWM 物理可放置性 | 尚未验证 | CLB site 14,579/14,640（99.58%）表示有单元放置的站点比例，并不表示 99.58% 的 LUT/FF 已消耗；已占用 CLB 中仍可能有可用 BEL。小模块不能仅凭总量或空站点数判断能否放置，需集成后重新实现。 |
| BIT/BIN 与 bundle 文件结构 | **BIN 格式不通过原镜像对照** | BIT 是 xck26 Vivado 2022.2 BIT 容器；旧候选 `.bit.bin` 是 Bootgen `-process_bitstream bin` 产生的 headerless/raw BIN，而原镜像运行时是带 Bootgen 头的完整 BIN。其余 DTBO 命名、XCLBIN/HWH CU 地址、`XRT_FLAT`/slot 核验独立保留。 |
| 新产物与原板 DPU/model 指纹 | **阻断同一 XMODEL 复测** | 新 `arch.json` 为 `0x101000016010407`；原板之前的硬件查询及 ResNet18 XMODEL 为 `0x101000056010407`。两者仅差 bit 30，即 SAVE Argmax 特性。新 HWH `SYS_IP_VER=0x40`，固定工程使用 DPU 4.0；原板为 4.1。 |
| 候选 bundle 可部署性 | **不批准** | 模型指纹未匹配，且 DTBO 比原板缺少 `fpga-config-from-dmabuf` 等结构；其加载方式尚未与目标 rootfs 核对。新 BIN/XCLBIN 的哈希不同属于重新构建的预期现象，不单独视作部署故障。 |

## DRC 明细

来源为最终已布线 checkpoint `kv260_ispMipiRx_vcu_DP_wrapper_routed.dcp`，在 Vivado 2022.2 重新打开并执行默认 `report_drc`；未载入用于 pre-place 的严重级别覆盖脚本。原始清单和对象逐条信息见 [routed_drc.rpt](evidence/deployment_review/routed_drc.rpt) 与 [routed_drc_objects.tsv](evidence/deployment_review/routed_drc_objects.tsv)，分类摘要见 [drc_rule_summary.tsv](evidence/deployment_review/drc_rule_summary.tsv)。

| 检查编号 | 级别 | 数量 | 受影响对象/含义 |
|---|---:|---:|---|
| AVAL-318 | Warning | 63 | DPU ALU 乘法树的 DSP48E2。PCIN 使用/接地组合出现在非底部站点；规则提示关注其下方 DSP 站点被使用时的影响。 |
| DPOP-3 | Warning | 1 | DPU DDR reader 的 DSP P 输出未流水化，性能提示。 |
| DPOP-4 | Warning | 1 | DPU save/fetch 参数乘法器 M stage 未流水化，性能提示。 |
| REQP-1731 | Warning | 512 | DPU convolution PE 的 DSP48E2 pre-adder A 输入宽度提示：应满足 26-bit 二补码限制以避免溢出/下溢。 |
| REQP-1934 | Warning | 1 | audio I2S transmitter 异步 FIFO 中 RAMB18E2 的 NO_CHANGE 写模式碰撞提示。 |
| RTSTAT-10 | Warning | 1 | 一条规则记录枚举 34 个无可路由负载的 net，位于 audio formatter/异步时钟转换及音频/MIPI 相关逻辑。需结合原始报告逐网审查。 |

总计 579 条，0 Error。这里记录的是报告里的 DRC violation records；其 Warning 严重级别不等同于构建通过保证，也没有通过调规则来消除。HDPR-5 只在生成脚本的 severity 设置中出现，实际 routed DRC 命中数为 0。日志调用位置：`src/kv260/overlays/examples/benchmark/binary_container_1/link/vivado/vpl/scripts/_vpl_pre_place.tcl:17`：

```tcl
set_property SEVERITY {Warning} [get_drc_checks HDPR-5]
```

Vivado 随后记录了“lowering the severity from an ERROR”提示。它说明脚本改了该检查的严重级别；routed DRC 的规则汇总和详情均无 HDPR-5，不能把这条提示计为一次 HDPR-5 违规。

## 时序与约束覆盖

原始报告：[routed_check_timing.rpt](evidence/deployment_review/routed_check_timing.rpt)、[routed_timing_summary.rpt](evidence/deployment_review/routed_timing_summary.rpt)。AMD 的时序审阅流程将 `check_timing` 用于发现未约束对象；Timing Summary 里的 unconstrained path table 也单独列出相关路径。[Vivado Design Methodology UG949](https://docs.amd.com/r/2022.2-English/ug949-vivado-design-methodology/Checking-That-Your-Design-is-Properly-Constrained)

| 类别 | 数值 | 结论 |
|---|---:|---|
| 无时钟寄存器 / 多时钟 / 缺失 generated clock / 内部最大延迟未约束端点 | 各 0 | 通过 |
| Setup | 0 / 409,870 fail；WNS +0.001 ns；TNS 0 | 通过，裕量很小 |
| Hold | 0 / 409,792 fail；WHS +0.010 ns；THS 0 | 通过，裕量很小 |
| Pulse width | 0 / 145,695 fail；WPWS +0.071 ns；TPWS 0 | 通过 |
| 缺 input delay | 7 ports | 未完整约束：`iic_scl_io`、`iic_sda_io`、`mipi_phy_if_data_p[0..3]`、`sdata_rx` |
| 缺 output delay | 9 ports | 未完整约束：`iic_scl_io`、`iic_sda_io`、`lrclk_rx`、`lrclk_tx`、`mclk_out_rx`、`mclk_out_tx`、`sclk_rx`、`sclk_tx`、`sdata_tx` |

Timing Summary 的 unconstrained path table 还列出若干时钟源/目标为 `(none)` 的路径。`check_timing` 认为内部端点均已约束，但 I/O 延迟覆盖不全，因此本审阅不签署“全设计约束完整”。需由接口时序责任人确认这些异步/板级接口的时序意图，并在目标设计的 XDC 中补齐约束或明确、可审阅的例外；现阶段不代填假设时序值。

## 资源与区域可实现性

完整报告：[routed_utilization.rpt](evidence/deployment_review/routed_utilization.rpt)、[routed_utilization_hierarchical.rpt](evidence/deployment_review/routed_utilization_hierarchical.rpt)。DCP inventory 为器件 `xck26-sfvc784-2LV-c`，`PBLOCK_COUNT=0`。

| 资源 | 已用/可用 | 使用率 | 审阅意义 |
|---|---:|---:|---|
| CLB site | 14,579 / 14,640 | 99.58% | 只有 61 个完全未占用站点；已占用 CLB 不一定满载，仍可能容纳额外 LUT/FF。不能据此推导最多只能增加 61 个 CLB 的逻辑。 |
| LUT | 69,615 / 117,120 | 59.44% | 聚合 LUT 仍有余量，但不能反映局部拥塞、站点类型和布线可达性。 |
| FF | 131,094 / 234,240 | 55.97% | 全局尚有余量，不代表适合放置在 IP 周边。 |
| BRAM tile | 94.5 / 144 | 65.63% | 尚有余量，但需看具体列/区域及端口连接。 |
| URAM | 56 / 64 | 87.50% | 余量有限。 |
| DSP | 710 / 1,248 | 56.89% | 总量有余量，不能消除 CLB/布线问题。 |

当前工程中没有静态区与 RP 的物理分区，也没有已预留给 AXI-Lite/PWM 的 Pblock。若加入最小 AXI-Lite 寄存器 bank 和 PWM，应作为 flat 静态设计的一部分重新跑实现，检查新增逻辑周围的 BEL、control set、布线及相关时钟裕量。CLB site 占用率不能直接当作 LUT/FF 容量使用率，也不能据此判定放不下。

原始实现日志 `src/kv260/overlays/examples/benchmark/binary_container_1/link/vivado/vpl/prj/prj.runs/impl_1/runme.log` 的 Router Utilization Summary 给出全局垂直布线使用率 48.0865%、水平 40.9205%，Failed/Unrouted/Partially routed nets 和 node overlap 均为 0；这些是当前设计完成布线的证据，并不提供新增 IP 的局部拥塞保证。

层次资源报告进一步显示 DPU 使用 LUT 51,300、FF 98,052、BRAM tile 75、URAM 48、DSP 710；其余平台逻辑合计 LUT 18,315、FF 33,042、BRAM tile 19.5、URAM 8、DSP 0。这是逻辑层次划分，并不是物理 RP 划分。后续小型控制逻辑可考虑挂到现有 100 MHz 控制总线，但地址空闲、接口、时钟/复位、引脚和实际 placement 仍需独立集成验证。

## 工件、板端基线与模型兼容性

本机隔离 bundle 位于 [test_bundle](evidence/deployment_review/test_bundle/)。文件核验清单见 [bundle_manifest.txt](evidence/deployment_review/bundle_manifest.txt)，运行文件 SHA-256 见下文生成的 `evidence/deployment_review/SHA256SUMS`。

| 内容 | 新参考构建候选 | 原板基线/一致性 |
|---|---|---|
| BIT | `file` 识别为 Xilinx BIT data，Vivado 2022.2，`xck26-sfvc784-2LV-c`；7,797,826 bytes | BIT 容器本身不是运行时 `.bit.bin`。 |
| 旧候选 raw BIN | 7,797,692 bytes；由 Bootgen `-process_bitstream bin` 从此 BIT 转换 | 与原镜像运行时 7,807,932 bytes 的完整 Bootgen BIN 头部不同；此旧候选仅保留为格式对照，不作为该镜像可加载工件。镜像中的 `firmware-name` 仍须匹配目标 BIN 文件名。[Bootgen UG1283](https://docs.amd.com/r/2022.1-English/ug1283-bootgen-user-guide/process_bitstream) |
| DTBO | 2,344 bytes；由固定源码 `firmware-reference/boards/kv260/benchmark-b4096/kv260-benchmark-b4096.dtsi` 编译 | `firmware-name` 与 BIN basename 一致；原板镜像中的 DTBO 已只读提取并反编译，候选缺少 `fpga-config-from-dmabuf`、部分 label/phandle，且 AFI/clocking 节点位置不同。详见 `compatibility_diagnosis/dtbo_difference.diff`，加载方式待核对。 |
| XCLBIN | 39,058 bytes；UUID `d698c28f-5d6b-9ffc-7777-99e332911f22`；一个 `DPUCZDX8G_1` CU；基址 `0xa0010000` | 与 HWH 的 `C_BASEADDR=0xA0010000`、`C_HIGHADDR=0xA0010FFF` 一致；与原板 XCLBIN 不同。 |
| HWH | 1,298,039 bytes | DPU 实例名/地址窗口与 XCLBIN 对得上。 |
| arch.json | `0x101000016010407` | 与原板活动 DPU、原板模型要求的 `0x101000056010407` 不同，**不兼容证据，阻断部署**。 |
| `shell.json` | `XRT_FLAT`, `num_slots="1"` | 符合本候选包的 flat shell 类型；与原板 shell JSON 语义相同。 |

原板只读快照记录：PetaLinux 2022.2、kernel `5.15.36-xilinx-v2022.2`、XRT/ZOCL `202220.2.14.0`、VART/Vitis AI Library 3.0；活动应用 `kv260-benchmark-b4096`，单 DPU CU 位于 `0xa0010000`，DPU IP v4.1.0，板端 DPU 架构指纹 `0x101000056010407`。原板 ResNet18 XMODEL 是 `/usr/share/vitis_ai_library/models/resnet18/resnet18.xmodel`，SHA-256 `4d4d669c84b6d5aa6f731b389ebcf0f51fb1449752cf5fa4a4beddd496c3c0ef`，其元数据同样要求指纹 `0x101000056010407`、名称 `DPUCZDX8G_ISA1_B4096`。这些证据来自 `/home/ghmd/AMD_Smart/logs/fpga/2026-09-30-kv260-readonly/REPORT.md` 和 `host-image-root-files.json`，本轮没有重新运行板端推理。

原板运行时文件的只读哈希：BIN `7d12c877e0fde40a243d2350b1a2227f565788bf9e2dcae4439d07f213d40a3f`、DTBO `36338937904e5ec988566d7341f6504edba34c01bd7e2e3f2025ab0069337e35`、XCLBIN `fc3abb934eec544e49a17c484336cf177258f475522cefc994ec458b726f69ac`；原 XCLBIN UUID `eedb44e9-3f77-0244-9ea9-23b953894638`。当前候选 bundle 文件和原板文件不是逐字节相同构建。

此前用户提供的原板 ResNet18 基线为 Samoyed Top-1 0.949879、单线程 214.381 FPS、双线程 238.479 FPS；本审阅没有复跑，不能将其称为本次验证结果。

## 独立测试 bundle 与复测/恢复步骤

当前准备目录的结构与运行时关键文件：

```text
evidence/deployment_review/test_bundle/
  lib/firmware/xilinx/kv260-benchmark-b4096/
    kv260-benchmark-b4096.bit.bin
    kv260-benchmark-b4096.dtbo
    kv260-benchmark-b4096.xclbin
    shell.json
  provenance/hardware/   # 本次 BIT、旧候选 raw BIN、HWH、arch.json
  provenance/            # DTSI、XCLBIN info
  build/                 # Bootgen/DTC 输入输出及日志
```

官方 Kria 应用打包结构支持由应用目录中的 bitstream、DTBO、可选 XCLBIN 和 shell metadata 组成运行包；本目录采取同类目录布局，但尚未在目标 rootfs/`xmutil` 上执行 app install 或 load。[AMD kria-apps-firmware](https://github.com/Xilinx/kria-apps-firmware)。`firmware-name` 仅负责 device-tree 对应 BIN 文件，不会证明 XCLBIN、DPU IP 和 XMODEL 架构兼容。

**部署批准前必须先处理：**解释新旧 DPU fingerprint 差异并产出与目标 ResNet18 XMODEL 匹配的 XCLBIN/arch 组合；由接口负责人补齐或正式确认 I/O timing intent；目标用途若包含 AXI-Lite/PWM，则完成集成后的重新实现并审查资源/时序。测试必须使用独立测试卡或可整体恢复的克隆介质，不能覆盖唯一基线卡。

获批后建议按以下顺序操作（以下是后续方案，不表示本轮执行过）：

1. **锁住原基线。** 关机后读回整张原 SD 卡为镜像并计算 SHA-256；另将板端 `/lib/firmware/xilinx/kv260-benchmark-b4096/` 整目录复制到主机，记录 `sha256sum`、`xmutil listapps`、`xmutil boardid`、XRT/VART 版本、活动 XCLBIN UUID/arch fingerprint。保留用户之前的同一 ResNet18 XMODEL 与同一 Samoyed 图片，分别计算哈希。优先使用另一张测试 SD 卡；不要只备份覆盖前的单个 overlay 文件。
2. **先做静态兼容检查。** 对拟部署目录执行 `sha256sum -c SHA256SUMS`；将候选 BIN 的 Bootgen 头部与原镜像实际运行时 BIN 对照，核对 BIN 的生成方式与目标 FPGA manager 要求；确认 DTBO `firmware-name` 与 BIN basename 完全一致；检查 `shell.json` 的 `XRT_FLAT`/slot 数量、XCLBIN kernel/CU 地址、HWH 地址、`arch.json` fingerprint 与目标 XMODEL fingerprint 匹配，并核对 `fpga-config-from-dmabuf` 等属性。任何一项不符即停止，不加载。
3. **独立测试卡加载。** 在已批准且已备份的测试卡上按该镜像自带 Kria `xmutil` app 管理流程安装/选择应用，确认应用 inactive 后再按该镜像支持的方法加载 overlay；记录命令、返回码、完整串口日志、`xmutil listapps`、`dmesg`、`xbutil examine`/相应 XRT 查询、XRT UUID 和实际 DT 状态。加载失败时立即卸载测试应用并从其基线恢复，勿在推理运行时移除 overlay。
4. **同图同模型复测。** 使用备份的同一个 `resnet18.xmodel` 和同一个 Samoyed 图片（哈希需与基线记录一致），运行原板相同的 `test_accuracy`/Vitis AI Library 命令；保存完整 stdout/stderr、Top-1 类别/分数、预热策略、线程数、FPS 测量窗口、温度/频率。单线程与双线程各重复至少 3 次并报告中位数，同时确认输出类别和分数与基线一致到预先约定容差。需要比对的是相同输入与同一模型文件，不是仅复用模型名。
5. **恢复原基线。** 关机并换回只读保管的原 SD 卡/原镜像；如果在克隆卡测试则直接撤下克隆卡。启动后核验原 `xmutil listapps`、原应用 `kv260-benchmark-b4096`、XCLBIN UUID `eedb44e9-3f77-0244-9ea9-23b953894638`、DPU fingerprint `0x101000056010407`、原运行时文件哈希，再用同一模型和图片跑一次短 smoke test。若这些基线校验失败，停止使用该卡并从整卡镜像恢复，不以复制单个新旧 overlay 文件作为回滚替代。

## 保留证据

- DRC、timing、utilization 原始报告、Vivado DCP 重开日志及对象清单均保留在 `evidence/deployment_review/`。
- 旧候选 bundle、BIT/raw BIN 转换输入和日志保留在 `evidence/deployment_review/test_bundle/`；其中 `bootgen_default_image.bin` 是对照用 Bootgen 完整输出，其前 64 字节与原镜像实际运行时 BIN 匹配。此文件由 DPU 4.0 BIT 生成，只供格式对照。
- 完整 routed DCP 和既有构建产物未改写；未改 vendor DRC 规则；没有执行板端切换、固件烧录或推理。
- 证据 SHA-256 清单：`evidence/deployment_review/SHA256SUMS`。
