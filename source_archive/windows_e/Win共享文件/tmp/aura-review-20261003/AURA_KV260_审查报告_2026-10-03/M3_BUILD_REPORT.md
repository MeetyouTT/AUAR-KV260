# M3：DPU 与最小 AXI-Lite 寄存器联合构建

日期：2026-10-02。范围：Ubuntu 主机上的独立硬件构建与审阅。

## 当前结论

主机端联合构建与核心审阅已完成：新平台、自研寄存器 IP、DPU 联合实现及 11 项工件已生成并通过 SHA-256 核验。最终 setup / hold / pulse-width 余量分别为 +0.009 / +0.009 / +0.071 ns，失败端点均为 0；内部未约束端点和布线错误均为 0。

原参考平台仍有 7 个输入、9 个输出缺少 I/O 延迟约束，完整外部接口约束覆盖未通过。板端寄存器读写、同配置下的 DPU 推理与 AXI 协议专项仿真均未执行。

这次生成的是 FPGA 硬件配置。已有备用卡的 PetaLinux 2022.2 / Vitis AI 3.0 镜像继续复用；本流程没有调用 `petalinux-build`。新增模块需要重新综合、布局、布线，才能与 DPU 一起出现在同一份完整位流中。

## 1. 工程与配置

- 独立目录：`/home/ghmd/kv260-m3-axilite-20261002`。
- 官方参考源码固定 commit：`a3a83f179503792226adf83082aee7c05de620b4`，来源 `xlnx_rel_v2022.2`。
- 派生起点：此前已在备用卡验证的独立 DPU 4.1 工程 `/home/ghmd/kv260-dpu41-control-20261001`。
- 继承的四项 DPU 兼容性改动保留于 `evidence/inherited_dpu41_changes.patch`；五项 DPU 输入与该起点逐项 SHA-256 相同，见 `evidence/source_manifest.json`。
- DPU 保持 B4096、1 CU、300/600 MHz、`SAVE_ARGMAX_ENABLE` 和原内存连接；控制地址保留 `0xa0010000`。最终架构核验以后续生成的 `arch.json` 为准。
- 工具实际日志：Vivado 2022.2，SW Build 3671981、IP Build 3669848，安装环境 `/home/ghmd/Xilinx_2022.2/Vitis/2022.2/settings64.sh`。
- synthesis / implementation / make 任务并行参数均为 4；工具内部线程数另由工具控制，位流写入及报告时序更新日志显示 8 线程。物理优化期间实测总内存 30 GiB、可用约 19 GiB、swap 使用 0；根分区可用约 158 GiB。

这里是新增自研模块后的派生工程，原样官方参考构建和旧板端对照均保留。

## 2. 新模块与接入

| 项目 | 配置 |
|---|---|
| 自研模块 | `aura.local:user:aura_m3_regs:1.0` |
| 地址窗口 | `0x80080000–0x80080fff`，4 KiB |
| 接入 | `PS_0/M_AXI_HPM0_LPD → axi_ic_ctrl_100/M06_AXI → aura_m3_regs_0/S_AXI` |
| 时钟 | 参考 `clk_wiz_0/clk_100M`，BD 实际 99.999 MHz |
| 复位 | `proc_sys_reset_100MHz/peripheral_aresetn` |
| IP_ID / ABI_VERSION | `0x41555241` / `0x00010000` |
| BUILD_ID | `0xa5078450` |
| SCRATCH | 偏移 `0x0c`，32 位读写，复位为 0，支持 WSTRB |

完整寄存器行为见 [M3_REGISTER_CONTRACT.md](docs/M3_REGISTER_CONTRACT.md)。模块只有三个身份寄存器和一个 SCRATCH，没有 PWM、外部输出和中断。

BUILD_ID 为记录的 11 项源码/配置摘要的前 32 位，完整摘要为 `a5078450b0777a556c6c349af6599310413535d84fe4e2767e7a7a80f3bd95be`。它不是整个 BIT 的 SHA-256。构建期间已再次核对 11 项输入，均与 `evidence/build_identity.json` 一致。

只在独立参考平台的 `scripts/main.tcl` 中增加本地 IP 仓库和 `scripts/integrate_m3.tcl` 入口。原 `config_bd.tcl` 与厂商规则保持原内容。控制互连从 6 个输出扩为 7 个。

XCLBIN 的 IP_LAYOUT 预期保留一个 DPU CU。M3 通过独立 AXI-Lite 控制窗口访问，其存在和地址由 HWH、routed 层级和后续板端寄存器读写核验。

## 3. 实际执行与已修复问题

| 阶段 | 返回码 | 结论与证据 |
|---|---:|---|
| `ip_01` | 0 | 后续 XML 审阅发现自动 `reg0` 与新增 `Reg` 重叠；不能以工具返回 0 判为有效封装 |
| `ip_02` | 0 | 修复为单一地址块；频率属性仍不匹配参考源 |
| `platform_01` | 2 | BD 检查拒绝 100 MHz 与 99.999 MHz 声明不匹配 |
| `ip_03` | 0 | 最终单地址块、四个寄存器；OOC 综合 54 LUT、118 FF、0 BRAM/URAM/DSP |
| `platform_02` | -15 | HLS 本地端口被沙箱拒绝；受控终止本次构建进程树，保留已完成的 54 个综合 run |
| `platform_resume_01` | 0 | 获准沙箱外恢复，仅重置 framebuffer 和等待中的顶层综合；XSA 验证与 XPFM 生成完成 |
| `overlay_01` | 2 | Vivado/Vitis 实际完成联合实现、位流和 XCLBIN；入口脚本在构建结束后出现语法错误，旧返回码保留 |
| `overlay_02` | 0 | 固定入口快照后复核；复用本轮生成的硬件工件，仅执行 Make 的打包复制 |
| `review_01` | 1 | routed DCP 报告与 XCLBIN 段提取完成；汇总时历史 MEM_TOPOLOGY JSON 不存在 |
| `review-finalize_01` | 0 | 从已验证父工程的 XCLBIN 补提内存拓扑到本轮目录，汇总通过，生成新 PL BIN，11 项哈希通过 |

每阶段完整日志和起止 UTC、命令、真实返回码保留于 `logs/<phase>_<attempt>/console.log` 和 `result.json`。

### 重复地址块

复用 IP packager 自动生成的唯一 `reg0`，将四个寄存器加入其中；连接脚本指向 `aura_m3_regs_0/S_AXI/reg0`。首轮封装、DCP、日志保留于 `evidence/ip_attempt01/`，第二轮于 `evidence/ip_attempt02/`。

### 时钟属性不匹配

原始错误为 `[BD 41-237]` 与 `[BD 41-238]`，分别出现在自研 AXI 接口与时钟引脚。删除自研模块不正确的固定 `FREQ_HZ=100000000` 封装属性，让参考时钟实际值传播。没有修改官方 Clocking Wizard、速度模型或厂商 Tcl。失败平台保留于 `evidence/platform_attempt01/`。

### HLS 沙箱本地端口

原始错误为 `ERROR: exception getting local port: open: Operation not permitted`。该错误来自开发主机 HLS 的本地通信，和板卡网线无关。获准沙箱外执行后，保留已完成 IP 缓存，重新生成受影响的 framebuffer 和顶层综合，随后实际导出并验证 XSA。

停止的本次构建进程记录于 `logs/platform_resume_01/result.json`。原 sandbox 错误及恢复日志快照保留于 `evidence/sandbox_hls_preserved/`；部分恢复日志会回放旧错误，结论依据实际恢复结果和返回码。已有的 `too many nested evaluations` 提示也出现在原参考成功日志中，未将其当作 M3 新失败根因。

### 长时构建入口的在线修改

`overlay_01` 从 UTC 11:55:04 运行至 14:10:50。Vitis 日志在 07:10:38 当地时间记录 `Run completed`，随后完成 BITSTREAM 去除与 HWH/arch/BIT/XCLBIN 打包复制；包装脚本最后报 `行 44: 未预期的符号“do”附近有语法错误`，整体返回码为 2。

这期间我修改过正在执行的 Bash 入口以补充审阅步骤。当前文件的 `bash -n` 返回 0，旧错误行位置也与当前内容不一致，最可能是长时运行的 Bash 后续读取受到文件改动影响。启动时没有保存该入口的精确快照，不能逐字还原当时的读取位置。

实际修复：每次阶段启动时，把入口复制到该阶段日志目录，记录 SHA-256，执行该快照，通过子进程环境 `AURA_M3_PROJECT_ROOT` 固定工程根目录。`overlay_02` 真实返回 0，日志只有已有工件的打包复制，没有重新进行综合和布局布线。保留 `overlay_01` 的失败记录。

### 汇总脚本的历史 JSON 路径

`review_01` 的 Vivado 已输出 `AURA_M3_ROUTED_REVIEW_COMPLETE` 并正常退出，错误发生在 Python 汇总阶段：假定的父目录 `evidence/xclbin_MEM_TOPOLOGY.json` 不存在。修复为从父工程已验证 bundle 中的 `kv260-benchmark-b4096-dpu41.xclbin` 提取到本轮 `evidence/validated_parent_MEM_TOPOLOGY.json`。原目录未添加或改写文件；`review-finalize_01` 复用已经完整生成的 routed 报告，实际返回 0。

## 4. 最终硬件审阅

数据均来自本轮最终 `kv260_ispMipiRx_vcu_DP_wrapper_routed.dcp`，报告保留于 `evidence/postroute/`，机器可读汇总为 `evidence/host_review_summary.json`。

### 时序与约束

| 检查 | 最差余量 | 总违规余量 | 失败 / 总端点 |
|---|---:|---:|---:|
| setup | +0.009 ns | 0 | 0 / 414172 |
| hold | +0.009 ns | 0 | 0 / 414094 |
| pulse-width | +0.071 ns | 0 | 0 / 147911 |

`no_clock=0`、`unconstrained_internal_endpoints=0`。211280 条需布线的网均已完整布线，布线错误 0。

缺输入延迟的 7 个端口：`iic_scl_io`、`iic_sda_io`、`mipi_phy_if_data_p[0..3]`、`sdata_rx`。缺输出延迟的 9 个端口：`iic_scl_io`、`iic_sda_io`、`lrclk_rx`、`lrclk_tx`、`mclk_out_rx`、`mclk_out_tx`、`sclk_rx`、`sclk_tx`、`sdata_tx`。这些缺口在旧参考工程中也存在，本轮保持并明确标记；全外部接口约束覆盖未通过。

### DRC

621 个实际 violation 对象均为 Warning，Error / Fatal / Critical Warning 实际违规为 0，实际 HDPR-5 为 0。

| 检查编号 | 实际违规数量 | 严重级别 | 主要受影响对象 |
|---|---:|---|---|
| AVAL-318 | 62 | Warning | DPU ALU 的 DSP48E2 |
| DPIP-2 | 43 | Warning | DPU DSP 输入流水级 |
| DPOP-3 | 1 | Warning | DPU DDR reader 的 `u_mult_hp0` DSP |
| DPOP-4 | 1 | Warning | DPU save fetch 的 `mul_c_reg` DSP |
| REQP-1731 | 512 | Warning | DPU convolution 的 DSP48E2 |
| REQP-1934 | 1 | Warning | 音频 I2S TX 的 FIFO BRAM |
| RTSTAT-10 | 1 | Warning | 音频 formatter 的 34 条无可布线负载网 |
| HDPR-5 | 0 | — | 无实际触发对象 |

相比旧 DPU 工程，AVAL-318 从 64 降为 62，DPIP-2 从 20 增为 43，总数从 600 增为 621。其余各编号数量相同。621 条描述中没有出现 M3 模块；完整关联 cells/nets/ports/pins 和原始描述保留在 `drc_objects.tsv`。

原日志的 `[Vivado 12-4430]` 提示由 Vitis 自动生成的 `src/kv260/overlays/examples/benchmark/binary_container_1/link/vivado/vpl/scripts/_vpl_pre_place.tcl:17` 设置 HDPR-5 严重级别为 Warning 引起。此提示本身不计为 HDPR-5 violation。本轮未修改该生成规则。

### 资源与放置

| 资源 | 新联合工程使用 / 总量 | 使用率 | 已验证 DPU 父工程使用 |
|---|---:|---:|---:|
| LUT | 70545 / 117120 | 60.23% | 70110 |
| FF | 132810 / 234240 | 56.70% | 131725 |
| 已占用 CLB site | 14559 / 14640 | 99.45% | 14567 |
| BRAM tile | 94.5 / 144 | 65.63% | 94.5 |
| URAM | 56 / 64 | 87.50% | 56 |
| DSP | 710 / 1248 | 56.89% | 710 |

M3 层级在最终设计中使用 **50 LUT、118 FF、0 BRAM/URAM/DSP**，实际涉及 22 个 SLICE site，坐标边界 X6–X12 / Y124–Y133。逐 primitive 的 LOC/BEL 保留于 `m3_placement.tsv`；OOC 的 54 LUT 与最终报告的 50 LUT 分别保留各自阶段含义。

整机差异包含互连扩展和全设计物理优化/打包变化：LUT +435、FF +1085、已占用 CLB site -8。仅剩 81 个完全未占用 CLB site，已占用 site 中还有未用 LUT/FF。Pblock 数为 0，可重配置 cell 数为 0，全部处于静态设计中；M3 上述位置是本次布局结果，不是为 PWM 预留的区域。后续 PWM 接在同一 100 MHz 控制路径的可行性须经下一次联合实现验证，时序余量也只有约 9 ps。

### 元数据一致性

- HWH 中 M3 窗口为 `0x80080000–0x80080fff`，DPU 窗口为 `0xa0010000–0xa0010fff`。
- DPU 的全部 91 个 HWH 参数与已验证父工程一致，版本 `0x41`、ARGMAX 为 1；`arch.json` 指纹为 `0x101000056010407`。
- XCLBIN 保留 1 个 DPU CU，IP_LAYOUT 地址为 `0xa0010000`；CONNECTIVITY 与 MEM_TOPOLOGY 与父工程一致。
- XCLBIN UUID 为 `c5255f48-d8da-4df0-e36e-a7c7d21b9dd8`，不含 BITSTREAM section，作为运行时元数据配合独立 PL BIN 加载。
- routed 实际引脚分别连接 `clk_300M`、`clk_600M`、`clk_100M`。XCLBIN 将其标记为 FIXED，频率为 299.997 / 599.994 / 99.999 MHz，继承参考时钟的取整；没有 scalable clock 数据。
- 编译使用的 BUILD_ID 头与当前源码头相同，固定 commit 与 11 项源码配置摘要再次核验通过。
- 实际 PART 为 `xck26-sfvc784-2LV-c`。打开 DCP 时关于临时项目 K24 与 KV260 board part 匹配的工具警告保留；随后实际加载 K26，资源与最终 PART 均按 K26 报告，没有执行 IP 升级。

DRC 关联对象通过 `get_* -of_objects` 从实际 violation 对象提取，保留 cells、nets、ports、pins 四列，不将不可用的属性误写成“没有受影响对象”。该查询方式依据 [AMD 2022.2 UG835](https://docs.amd.com/r/2022.2-English/ug835-vivado-tcl-commands/create_drc_violation)。

## 5. 工件

新平台生成于 `src/kv260/platforms/xilinx_kv260_ispMipiRx_vcu_DP_202220_1/`，包含 XPFM、`hw/*.xsa` 和 `sw/*.spfm`。完整路径、字节数与 SHA-256 见 [artifacts.json](evidence/artifacts.json)；[ARTIFACTS.sha256](evidence/ARTIFACTS.sha256) 的 11 项实际核验全部通过。

| 工件 | 字节数 | SHA-256 前 16 位 |
|---|---:|---|
| 平台 XPFM | 610 | `49392319bbb65c19` |
| 平台 XSA | 78951482 | `8c6bc4a66d915fb0` |
| 平台 SPFM | 2281 | `2bc8a9b3570c94d5` |
| DPU XO | 1412553 | `8bb096dc1a79e34d` |
| 联合 link XSA | 5901812 | `5211b3e320923a0d` |
| 元数据 XCLBIN | 39145 | `875ca912d87b2c99` |
| 完整 BIT | 7797826 | `cfb3faba6e27ce9f` |
| 新 HWH | 1317917 | `088cca44b02e2b49` |
| arch.json | 36 | `6feb79ba36f1f030` |
| routed DCP | 132753480 | `4a564eb334121245` |
| 完整 PL BIN | 7807932 | `a48a25265d280f26` |

BIN 位于 `artifacts/kv260-benchmark-b4096-m3.bit.bin`，由本轮新 BIT 通过 `bootgen -arch zynqmp` 和 `[destination_device = pl]` 生成，Bootgen 2022.2.0 返回 0。BIN 前 64 字节与已上板验证父工程的相同格式 BIN 一致，仅说明格式一致，尚未验证这份新 BIN 的板端加载。

这是完整 PL 配置，未来须以 full / XRT_FLAT 路线加载，DTBO 的 partial 标志应为 0；不是可单独替换 M3 的局部位流，也不是含 Linux 的 SD/QSPI 系统镜像。DTBO、`shell.json`、`firmware-name` 对应关系和运行 bundle 尚待下一阶段冻结。本轮未制作该 M3 运行 bundle。

不将旧成果或 staging 的预编译固件列为新构建产物。

## 6. 下一步与未验收范围

1. 主机联合构建和 routed 审阅通过后，单独准备 M3 测试 bundle，冻结 BIN、DTBO、XCLBIN、`shell.json` 与 `firmware-name` 对应关系。
2. 在备用卡先保存官方活动应用、运行时、原 firmware 与同模型同图片的对照；核对实际 `/dev/mem` 或 UIO 支持，再选择寄存器访问工具。
3. 获准加载候选后，核对 IP_ID、ABI_VERSION、BUILD_ID，受控读写 SCRATCH 并恢复原值；这一步验证实际 ARM→AXI→自研模块访问。
4. 在同一份已加载 PL 配置中复跑同一 ResNet18 XMODEL、同一图片，保存 DPU 指纹、CU 地址、分类与性能证据，再恢复官方应用并复查。
5. 共存验证通过后再增加真实 PWM 模块及其约束，重新做联合实现与审阅。

本轮未执行板端加载、重启、SD/QSPI 烧录或执行器连接。专门的 AXI 协议仿真未执行，综合通过不能替代协议验收。

旧板端曾出现设备树 overlay 卸载引用计数错误，官方应用恢复并不等于该内核问题已解决；长期反复热切换仍未验收。旧 DPU 的分类分数与 FPS 仅作为对照，不能冒充这份 M3 位流的板端结果。

复测固定输入：旧 ResNet18 XMODEL SHA-256 `4d4d669c84b6d5aa6f731b389ebcf0f51fb1449752cf5fa4a4beddd496c3c0ef`；JPEG SHA-256 `f3f87bb8ab3c26c7ecfd3ac60421d7f32b0503d1d6c5baf8bac42ed93d86351a`。分类先核对旧对照 Top-1 `Samoyed / 0.949879`，性能按旧程序与相同计时口径执行单线程、双线程各三轮 60 秒，记录完整输出与中位数；这些均是下一阶段操作方案。

旧 15 项工件与 104 项板端证据索引再次实际核验通过，记录于 `evidence/input_integrity_audit.json`，原基线及其测试证据保留。
