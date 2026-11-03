# KV260 官方参考平台：部署前审阅

审阅日期：2026-10-01  
源码固定版本：`Xilinx/kria-vitis-platforms` `xlnx_rel_v2022.2`，commit `a3a83f179503792226adf83082aee7c05de620b4`。  
部署结论：**HOLD，不得将本次构建切换到原基线板卡。** 本轮只读板端证据、审阅主机产物并准备隔离 bundle；没有向板卡写入、加载或卸载任何固件。

## 审阅结果

| 项目 | 状态 | 证据/结论 |
|---|---|---|
| DRC 规则运行 | 通过（有警告） | 最终 routed DCP 的默认规则集共 579 条，均为 Warning、0 Error；分类见下表。完整原始报告已保留。 |
| HDPR-5 | 未发现实际违规 | 最终 DRC 报告没有 HDPR-5 条目。日志里的降级提示由 Vitis 生成的 `_vpl_pre_place.tcl:17` 将 HDPR-5 从 Error 降到 Warning 引起；这是规则严重级别修改提示，不是检查命中的违规。未修改厂商规则或生成脚本。 |
| 内部时序 | 通过 | 409,870 setup endpoints、409,792 hold endpoints、145,695 pulse-width endpoints 均 0 failing；WNS +0.001 ns、WHS +0.010 ns、WPWS +0.071 ns。 |
| 完整 I/O 时序覆盖 | 未通过/待设计约束确认 | 7 个输入没有 input delay，9 个输出没有 output delay；内部 unconstrained endpoints 为 0 不代表这些 I/O 被约束。涉及 I²C、MIPI 输入和音频接口。 |
| 静态区/RP/Pblock | 无 RP/Pblock | routed DCP `PBLOCK_COUNT=0`；这是完整静态 XRT_FLAT bitstream，不是带已预留可重配置区的 DFX shell。 |
| 小型 AXI-Lite/PWM 物理可放置性 | 未证明，风险高 | 全局 LUT 使用率 59.44%，但 CLB site 使用 14,579/14,640（99.58%），仅余 61 个 site；URAM 已用 56/64（87.5%）。不能仅凭 LUT/DSP 剩余比例认定能放置。需把目标 RTL/IP 合入后重新实现并审阅局部拥塞、DRC 和时序。 |
| BIT/BIN 与 bundle 文件结构 | 通过格式/命名核验 | BIT 是 xck26 Vivado 2022.2 BIT 容器；bundle 的 `.bit.bin` 是 Bootgen `-process_bitstream bin` 产生的 raw BIN。DTBO `firmware-name` 精确指向该文件名；XCLBIN/HWH CU 地址相符；shell 为 `XRT_FLAT`, 1 slot。 |
| 新产物与原板 DPU/model 指纹 | **阻断** | 新 `arch.json` 为 `0x101000016010407`；原板活动 DPU 与原板 ResNet18 XMODEL 均为 `0x101000056010407`。虽然 DPU 都标为 B4096，指纹不同，不能假定模型兼容。 |
| 候选 bundle 可部署性 | **不批准** | 除上述架构指纹不匹配外，新 DTBO/BIN/XCLBIN 哈希也不同于板端原基线。独立测试卡上也应先选用与目标 model 匹配的 XMODEL/overlay 组合并做运行时验证。 |

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
| CLB site | 14,579 / 14,640 | 99.58% | 仅剩 61 个 CLB site；站点/位置比全局 LUT 百分比更直接显示实现空间很紧。 |
| LUT | 69,615 / 117,120 | 59.44% | 聚合 LUT 仍有余量，但不能反映局部拥塞、站点类型和布线可达性。 |
| FF | 131,094 / 234,240 | 55.97% | 全局尚有余量，不代表适合放置在 IP 周边。 |
| BRAM tile | 94.5 / 144 | 65.63% | 尚有余量，但需看具体列/区域及端口连接。 |
| URAM | 56 / 64 | 87.50% | 余量有限。 |
| DSP | 710 / 1,248 | 56.89% | 总量有余量，不能消除 CLB/布线问题。 |

当前工程中没有静态区与 RP 的物理分区，也没有任何可供 AXI-Lite/PWM 使用的 Pblock。故不存在可以直接指定的“可重配置区位置”。若将最小 AXI-Lite 寄存器 bank 和 PWM 加到此 flat design，只有作为整个静态设计的一部分重新跑完整实现，并检查新增 IP 的 placement、routing、DRC 和各相关时钟时序后才能判断。尤其 CLB site 已接近满载，不能从资源总表保证成功。

## 工件、板端基线与模型兼容性

本机隔离 bundle 位于 [test_bundle](evidence/deployment_review/test_bundle/)。文件核验清单见 [bundle_manifest.txt](evidence/deployment_review/bundle_manifest.txt)，运行文件 SHA-256 见下文生成的 `evidence/deployment_review/SHA256SUMS`。

| 内容 | 新参考构建候选 | 原板基线/一致性 |
|---|---|---|
| BIT | `file` 识别为 Xilinx BIT data，Vivado 2022.2，`xck26-sfvc784-2LV-c`；7,797,826 bytes | BIT 容器本身不是运行时 `.bit.bin`。 |
| raw BIN | 7,797,692 bytes；由 Bootgen `-process_bitstream bin` 从此 BIT 转换 | 正确的板端文件类型是 headerless/raw BIN。Bootgen 文档给出该处理方式；PetaLinux 文档要求 `.bin` 文件名与 DTS `firmware-name` 对应，并说明使用 `fpgautil` 加载 DTBO/BIN。[Bootgen UG1283](https://docs.amd.com/r/2022.1-English/ug1283-bootgen-user-guide/process_bitstream) · [PetaLinux UG1144](https://docs.amd.com/r/en-US/ug1144-petalinux-tools-reference-guide/DTG-Settings) |
| DTBO | 2,344 bytes；由固定源码 `firmware-reference/boards/kv260/benchmark-b4096/kv260-benchmark-b4096.dtsi` 编译 | `firmware-name = "kv260-benchmark-b4096.bit.bin"` 与 bundle BIN basename 一致；但新 DTBO 哈希不同于原板上的 DTBO。 |
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
  provenance/hardware/   # 原始 BIT、raw BIN、HWH、arch.json
  provenance/            # DTSI、XCLBIN info
  build/                 # Bootgen/DTC 输入输出及日志
```

官方 Kria 应用打包结构支持由应用目录中的 bitstream、DTBO、可选 XCLBIN 和 shell metadata 组成运行包；本目录采取同类目录布局，但尚未在目标 rootfs/`xmutil` 上执行 app install 或 load。[AMD kria-apps-firmware](https://github.com/Xilinx/kria-apps-firmware)。`firmware-name` 仅负责 device-tree 对应 BIN 文件，不会证明 XCLBIN、DPU IP 和 XMODEL 架构兼容。

**部署批准前必须先处理：**解释新旧 DPU fingerprint 差异并产出与目标 ResNet18 XMODEL 匹配的 XCLBIN/arch 组合；由接口负责人补齐或正式确认 I/O timing intent；目标用途若包含 AXI-Lite/PWM，则完成集成后的重新实现并审查资源/时序。测试必须使用独立测试卡或可整体恢复的克隆介质，不能覆盖唯一基线卡。

获批后建议按以下顺序操作（以下是后续方案，不表示本轮执行过）：

1. **锁住原基线。** 关机后读回整张原 SD 卡为镜像并计算 SHA-256；另将板端 `/lib/firmware/xilinx/kv260-benchmark-b4096/` 整目录复制到主机，记录 `sha256sum`、`xmutil listapps`、`xmutil boardid`、XRT/VART 版本、活动 XCLBIN UUID/arch fingerprint。保留用户之前的同一 ResNet18 XMODEL 与同一 Samoyed 图片，分别计算哈希。优先使用另一张测试 SD 卡；不要只备份覆盖前的单个 overlay 文件。
2. **先做静态兼容检查。** 对拟部署目录执行 `sha256sum -c SHA256SUMS`；用 `file` 确认 `.bit.bin` 是 raw BIN 而不是 `.bit` 容器或 Bootgen 完整 boot image；确认 DTBO `firmware-name` 与 BIN basename 完全一致；检查 `shell.json` 的 `XRT_FLAT`/slot 数量、XCLBIN kernel/CU 地址、HWH 地址、`arch.json` fingerprint 与目标 XMODEL fingerprint 完全匹配。任何一项不符即停止，不加载。
3. **独立测试卡加载。** 在已批准且已备份的测试卡上按该镜像自带 Kria `xmutil` app 管理流程安装/选择应用，确认应用 inactive 后再按该镜像支持的方法加载 overlay；记录命令、返回码、完整串口日志、`xmutil listapps`、`dmesg`、`xbutil examine`/相应 XRT 查询、XRT UUID 和实际 DT 状态。加载失败时立即卸载测试应用并从其基线恢复，勿在推理运行时移除 overlay。
4. **同图同模型复测。** 使用备份的同一个 `resnet18.xmodel` 和同一个 Samoyed 图片（哈希需与基线记录一致），运行原板相同的 `test_accuracy`/Vitis AI Library 命令；保存完整 stdout/stderr、Top-1 类别/分数、预热策略、线程数、FPS 测量窗口、温度/频率。单线程与双线程各重复至少 3 次并报告中位数，同时确认输出类别和分数与基线一致到预先约定容差。需要比对的是相同输入与同一模型文件，不是仅复用模型名。
5. **恢复原基线。** 关机并换回只读保管的原 SD 卡/原镜像；如果在克隆卡测试则直接撤下克隆卡。启动后核验原 `xmutil listapps`、原应用 `kv260-benchmark-b4096`、XCLBIN UUID `eedb44e9-3f77-0244-9ea9-23b953894638`、DPU fingerprint `0x101000056010407`、原运行时文件哈希，再用同一模型和图片跑一次短 smoke test。若这些基线校验失败，停止使用该卡并从整卡镜像恢复，不以复制单个新旧 overlay 文件作为回滚替代。

## 保留证据

- DRC、timing、utilization 原始报告、Vivado DCP 重开日志及对象清单均保留在 `evidence/deployment_review/`。
- 候选 bundle、BIT/raw BIN 转换输入和日志保留在 `evidence/deployment_review/test_bundle/`；其中 `bootgen_default_image.bin` 是对照用 Bootgen 默认完整输出，不是运行时 raw BIN。
- 完整 routed DCP 和既有构建产物未改写；未改 vendor DRC 规则；没有执行板端切换、固件烧录或推理。
- 证据 SHA-256 清单：`evidence/deployment_review/SHA256SUMS`。
