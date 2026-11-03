# KV260 板卡镜像栈只读审计

审计时间：2026-09-26（America/Los_Angeles）  
审计目录：`/home/ghmd/kv260_full_image_audit_20260926_codex`  
边界：只读检查本机已有文件、checkpoint、日志和官方资料；未访问板端控制接口，未改工程/镜像/模型/输入，未运行构建、推理、烧写或硬件操作。

## 摘要

**当前离线证据确认两套硬件产物各有发布阻断项。** 现存 PetaLinux `system.bit` 的 SHA256 与旧 100/100 MHz routed bit 相同，但同一 `system.xsa` 内的 HWH 描述 200/100 MHz 时钟；当前 `image.ub` 内设备树也声明 200/100 MHz。该 bit/XSA/DT 组合来源不一致。无法只凭这些主机文件证明它就是板上当前加载的 PL 配置。

**新 clockfix 独立重建仍不可上板。** 本次阶段查询确认综合 DCP 里 BD 层的两个 DPU reset pin 都连通；到 `opt.dcp` 时两个 pin 已变成 `IS_CONNECTED=0`，`rst_dpu_dsp` cell 消失；placed、physopt、routed 均保持此状态，DPU 两路 clock pin 始终连通。另核对此前保存的独立审计输出发现，新旧两代 DPU IP OOC DCP 都显示：DPU IP 顶层 reset ports 无负载（fanout=0），而 IP 实例内部对应 reset pins 接到 `<const0>`；旧 routed DCP 也有相同的两个 reset boundary pins 断连。因此，顶层连接在 opt 阶段被清理的**网表机制**有较强证据：reset 信号在 OOC DCP 中没有可见负载，opt 把上层无负载连接裁掉。现有日志只给出 Constant propagation/Sweep 的总体 cell 统计，不能证明具体是哪一个子阶段删了这些对象。

这**还没有解决 reset 是否符合 DPU 功能要求**：AMD PG338 v4.1 明确将 `dpu_2x_resetn` 和 `m_axi_dpu_aresetn` 定义为 active-low reset，并要求每个 clock 都有对应且同步的 reset。OOC `<const0>` 与 routed pin 断连和该官方接口说明存在语义冲突；DPU 核 RTL 加密，现有只读材料不能证明这些常量是安全的实现约定还是 DPU IP/网表错误。故不能把差异降格为“只是假告警”或据此批准上板。

AMD 官方资料将 Vitis AI 3.0 的 KV260 配套镜像列为 `xilinx-kv260-dpu-v2022.2-v3.0.0.img.gz`，并说明该系列面向 Vitis AI 3.0、Vivado/Vitis 2022.2；本机没有该板卡镜像或它的官方校验和。因此只完成发布系列层的核对，**没有证据证明官方镜像中的 DPU 参数/fingerprint 与本机 B2304、`0x101000056010405` 完全一致**。

板卡没有通过本次主机审计环境连接；主机没有发现可挂载的 SD 卡或串口设备。用户提供的最近推理观察（识别错误、重复波动、猫图与全零输入未明显分离，以及读回字节相等）作为用户报告记录，未取得该次原始日志/文件哈希清单来独立复核。`VART wait=0`、参数/输入读回一致和 DDR/VART 输出一致都不能证明 DPU 运算正确。

用户特别确认：本次重建没有降低 `dpu_2x_clk` 或 `m_axi_dpu_aclk` 频率，也没有向原工程、板卡或镜像添加 clock/reset connection；操作在隔离重建目录中进行。报告中的 200/100 MHz 是该副本现有设计与实现报告呈现的目标关系，不应误述为本次改频或新加复位线。

**结论：当前已有 PetaLinux 镜像栈有确认的 bit/HWH/DT 来源不一致；新生成 BIT/XSA 因 routed reset 差异不可确认、不可上板。** 这两项是具体交付问题，但目前不能断言哪一项单独导致了随机输出或分类错误。

## 证据状态与核心产物

文件类型、路径、大小和 SHA256 见 [artifact_inventory.tsv](/home/ghmd/kv260_full_image_audit_20260926_codex/reports/artifact_inventory.tsv)。清单有 136 个文件记录，覆盖本机发现的 PetaLinux 启动产物、Vivado checkpoints/IP、模型与源代码元数据、输入、SD 备份、此前保存的审计证据及本地 AMD 安装器元数据；未发现官方 KV260 `.img`/`.img.gz` 文件。它是按审计目标筛选的清单，不表示整个磁盘都已做文件系统取证。Archive 成员哈希在 FIT/XSA 专项报告中；版本字段来自 FIT 描述、rootfs manifest、Bootgen 头、HWH 和对应历史启动日志，不能从不含版本字段的二进制推定版本。

| 项目 | 本机当前产物 | 官方配套 | 板端实际加载值 | 证据及判定 |
|---|---|---|---|---|
| `BOOT.BIN` / boot chain | PetaLinux 自定义产物，SHA256 `335fd6ec019ccbbc9d08ac518f1f02bfb67e64c60e0f6c5435556dfe6c05044d`。BIF 指向 FSBL、PMUFW、`system.bit`、BL31、DTB、U-Boot | 没有对应官方镜像二进制，无法比较各分区 SHA/版本 | **最新状态未确认**。既有串口原始日志 SHA256 `153aa69b…967d46b` 记录过 QSPI FSBL/PMUFW 2023.2、BL31 v2.8 2023.2、U-Boot 2023.01；之后手工从 SD 读入一个 122,901,532-byte `image.ub`，bootargs 带 `initcall_blacklist=xlnx_dpu_drv_init`。它与本地主机当前 130,879,552-byte `image.ub` 不同，且该历史启动禁用了 DPU initcall | BIF 行 1–9；历史日志摘录 [boot_serial_key_lines.txt](/home/ghmd/kv260_full_image_audit_20260926_codex/references_prior_audit/boot_serial_key_lines.txt:2)–[69]，原始日志路径 `/home/ghmd/work/kv260-boot-audit-live/serial-boot-raw.log`。该历史启动不能当作用户最新推理 run 的启动身份 |
| PetaLinux FPGA/XSA | `system.bit` SHA256 `6a75e223ba4f901b4f82eef7ccee185f5e8269dcffe92903680c74e3f0d4aba5`；`system.xsa` SHA256 `08abccc5df51ebcecdf09c52782e4d3ae96260a1625aa1fca9e16cd28637bdd0`。XSA 内 bit 与本地 `system.bit` 相同 | 官方 Vitis AI 3.0 KV260 image 名称已确认，二进制及官方 SHA256 **未找到** | **未确认**，没有 FPGA 配置哈希回读 | 成员 SHA 见 [xsa_member_hashes.txt](/home/ghmd/kv260_full_image_audit_20260926_codex/reports/xsa_member_hashes.txt:3)–[6]；旧时序审计 [REPORT.md](/home/ghmd/kv260_hw_timing_audit_20260926/REPORT.md:8)–[12] 说明此 bit 来自 100/100 MHz 旧 routed 设计 |
| PetaLinux HWH 与 DT | XSA 内 HWH SHA256 `ea48b3a03c558eb1f99a47b4d0ffba9e3e9a83e3e4d390034c17708b73c64514`，描述 200/100 MHz 与两路 reset 连接；DT DPU 节点 compatible `xlnx,dpuczdx8g-4.1`、三路 clocks、reg `0x400000000/0x1000000`、IRQ 89；clock 固定声明为约 200/100 MHz | 未取得官方镜像中的匹配 HWH/DT 作字节级比较 | 用户报告板端显示约 199,998,002/99,999,001 Hz；**未独立确认它是测量值**，且静态 DT 数值不是频率实测 | HWH [petalinux_system_xsa_embedded.hwh](/home/ghmd/kv260_full_image_audit_20260926_codex/extracted/xsa/petalinux_system_xsa_embedded.hwh:2631)–[2644]、[4326]–[4353]；DT [system_dtb_readonly.dts](/home/ghmd/kv260_full_image_audit_20260926_codex/reports/system_dtb_readonly.dts:1732)–[1741]；生成时钟源 [pl.dtsi](/home/ghmd/work/petalinux-kv260-dpu/components/plnx_workspace/device-tree/device-tree/pl.dtsi:14)–[32] |
| 新 clockfix BIT/XSA | BIT SHA256 `d316ee9c33bae9547424b8820d188af1b3db2710a9a87586542a84dd7e3b385c`；XSA SHA256 `76e8d1056949999ef517cfc13912f41ade39a40c9304f3779ff69f545f92363b`；XSA 内 bit 与此 BIT 完全相同 | 官方工具版本层面 Vivado 2022.2 符合 PG338 4.1 推荐范围；官方 image 与本机 bit 没有可比文件 | 用户说没有把此 bit/XSA 烧到板卡；本次没有上板操作 | 新构建报告行 7–10、100–116；嵌入成员哈希见 `xsa_member_hashes.txt` 行 1–2、6 |
| 镜像/内核/runtime | PetaLinux `image.ub` SHA256 `3a452b9d3790f09710b017a82f9522cc48ed19ea601967aed966c735d05b8bb0`；FIT 内 kernel 为 5.15.36 `19984dd147`；rootfs manifest 的 VART/XIR/Vitis AI Library/target-factory/unilog 均标称 3.0 | 未取得官方板端 rootfs 作 ELF/build-id/包文件逐字节比较；本机 Unified Installer `.digests` 不是官方板卡镜像校验和 | 最新 run 的启动参数/镜像**未确认**；历史串口记录中的 `image.ub` 是 122,901,532 bytes，和本机当前 `image.ub` 大小/hash 不符，且那次 bootargs 屏蔽 DPU driver initcall | FIT 成员/哈希在 [image_ub_fit_members.txt](/home/ghmd/kv260_full_image_audit_20260926_codex/reports/image_ub_fit_members.txt) 行 1–12；manifest 行 164、521、530、539、541、546。历史 boot 摘录及原始日志 SHA 见上。本机 rootfs ELF SONAME/build-id 见 [local_runtime_elf_provenance.txt](/home/ghmd/kv260_full_image_audit_20260926_codex/reports/local_runtime_elf_provenance.txt)，不代表板端运行库 |
| ResNet50 模型/输入 | 新编译 XMODEL SHA256 `330a654a6c54db486b9fa8f82a1e84c298b66829b7939eabb3635d88007434da`，编译指纹 `0x101000056010405`；旧模型 SHA256 `acf77c7fdb91ed875999c7d0e455aecb8f76d26e108f53ceb9cdf063ce4def7c`，二者不是同一文件 | 官方通用镜像不证明本项目模型/预处理正确 | 用户报告最近运行载入新 XMODEL；没有原始板端哈希回读材料供本次复核 | 新模型 `/home/ghmd/kv260_resnet50_verified_rebuild_20260926/compiled/resnet50_b2304_verified.xmodel` 在 [artifact_inventory.tsv](/home/ghmd/kv260_full_image_audit_20260926_codex/reports/artifact_inventory.tsv:68)；编译来源见 [compile_provenance.txt](/home/ghmd/kv260_resnet50_verified_rebuild_20260926/compile_provenance.txt:11)–[35]；PG338 [IP Facts](https://docs.amd.com/r/en-US/pg338-dpu/IP-Facts) 要求 architecture/AXI width 改变后按更新 `arch.json` 重新生成相关 `.xmodel` |

## A. 本机文件来源清单与关联

1. `BOOT.BIN` SHA256 为 `335fd6ec019ccbbc9d08ac518f1f02bfb67e64c60e0f6c5435556dfe6c05044d`。BIF [bootgen.bif](/home/ghmd/work/petalinux-kv260-dpu/images/linux/bootgen.bif:1)–[9] 列出 FSBL、PMUFW、PL `system.bit`、BL31、`system.dtb` 和 U-Boot ELF；只读 `bootgen -read` 输出显示 Bootgen v2022.2.0，保存在 [bootbin_headers_readonly.txt](/home/ghmd/kv260_full_image_audit_20260926_codex/reports/bootbin_headers_readonly.txt:1)–[8]。这建立了**当前主机这套 BOOT.BIN 的分区名称和 BIF 输入关系**；没有从容器逐分区提取 payload SHA，因此不能证明 BOOT.BIN 内的每个成员字节都等于当前同名源文件，也未读回板卡实际启动分区或运行映像身份。
2. `image.ub` FIT 内 kernel、DTB 和 cpio rootfs 的计算 SHA256 与 FIT 声明值一致。FIT 的 `fdt-system-top.dtb` 计算哈希 `f8f7b874…d068467f`，等于 PetaLinux 独立 `system.dtb`；FIT cpio rootfs 哈希 `43468905…c18f31` 对应 `/images/linux/rootfs.cpio.gz`。见 [image_ub_fit_members.txt](/home/ghmd/kv260_full_image_audit_20260926_codex/reports/image_ub_fit_members.txt:1)–[12]。说明 image.ub 容器成员彼此一致，不代表它与 `BOOT.BIN` 中 PL bit 匹配。
3. PetaLinux `system.xsa` 内 bit 的哈希等于 `images/linux/system.bit`，但其 bit SHA 与旧 routed DCP 产出的 `system.bit` 相同；旧 DCP 查询只见 100 MHz PS clocks，没有目标 200/100 clock wizard。与此同时 XSA HWH 声明新 200/100 MHz 拓扑。该文件组合确认为旧 bit 与新 HWH 描述同包，属于**当前本地镜像栈真实不一致**，不是对板端加载状态的证明。见旧审计 [REPORT.md](/home/ghmd/kv260_hw_timing_audit_20260926/REPORT.md:8)–[12]、[22]–[30]、[38]–[42]；成员哈希见本报告目录 `reports/xsa_member_hashes.txt`。
4. 新 clockfix XSA 与新 BIT 的成员哈希一致，嵌入 HWH 与本次生成 HWH 哈希一致；但相同 HWH 与最终 routed DCP 的 reset 连通性意见冲突。字节完整性相符不等于 HWH 对物理实现语义正确。
5. `system.dtb` 中 DPU node 没有 `resets` 属性；本审计没有取得与当前 kernel/driver 配套且版本匹配的绑定约束，故将“DT reset 属性缺失是否构成错误”列为**未确认**，不单凭缺失断言故障。DT 明确声明的 reg/IRQ/clocks 已记录，不足以完成 DMA 地址宽度、IOMMU、cache sync 或 reserved-memory 与板端 driver 的端到端核验。

## B. AMD 官方版本匹配

AMD [Vitis AI Library 3.0 Release Notes](https://docs.amd.com/r/3.0-English/ug1354-xilinx-ai-sdk/Vitis-AI-Library-v3.0-Release-Notes) 的兼容性列表列出 `xilinx-kv260-dpu-v2022.2-v3.0.0.img.gz`，并列 KV260 1.0 支持（UG1354 3.0 文档日期 2023-01-12）；AMD [Vitis AI 3.0 OS 镜像说明](https://docs.amd.com/r/3.0-English/ug1414-vitis-ai/Flashing-the-OS-Image-to-the-SD-Card) 链接到 KV260 预构建镜像（UG1414 3.0 文档日期 2023-02-24）。这些是文档发布日期，不是镜像二进制构建日期。AMD [PG338 DPUCZDX8G v4.1 工具章节](https://docs.amd.com/r/en-US/pg338-dpu/Development-Tools) 推荐 Vivado 2022.2 或更高版本；PG338 [IP Facts](https://docs.amd.com/r/en-US/pg338-dpu/IP-Facts) 支持 Zynq UltraScale+、说明 PetaLinux 驱动供应方式，并指出改变 DPU architecture/AXI width 后需按更新的 `arch.json` 重新生成模型。PG338 还说明该 IP 使用加密 RTL，不提供 test bench/simulation model，因此仅凭现有仿真材料不足以推定 reset 语义。

本机在 `/home/ghmd` 文件枚举中未找到 KV260 `.img`、`.img.gz` 或 `.wic` 镜像；匹配到的 `.img` 是 QEMU 仿真器系统文件。`/home/ghmd/Downloads/AMD_KV260_2022.2/01_unified_installer` 仅找到官方 AMD/Xilinx Unified Installer 的 `.digests` 和下载 manifest，而非板卡镜像；Installer 二进制本身也不在本机。元数据及 SHA 在 `artifact_inventory.tsv` 前几行。未下载任何东西。**官方镜像的确切 SHA256、BOOT/BIT/XSA/rootfs 成员、B2304 参数和 fingerprint 未确认。** 官方发布说明给出的 compatibility 是 release/image 层面的测试关联，不等同于其 stock DPU 与自定义 B2304 build fingerprint 相同。

官方资料可支持的最小判断：Vitis AI 3.0 + KV260 + 2022.2 是正确的发布系列组合；Vivado 2022.2 符合 PG338 4.1 推荐范围。不能据此确认本机 custom PetaLinux boot chain、DPU 参数、Linux patch/module ABI 或当前板端 runtime 与 stock 镜像二进制兼容。Host CPU Docker `xilinx/vitis-ai-pytorch-cpu:ubuntu2004-3.0.0.106` 是模型编译环境，不能当作板端镜像。

## C. 当前本地栈逐层对照

| 层 | 已确认事实 | 推测 / 未确认 |
|---|---|---|
| Boot chain | 主机 `BOOT.BIN` 的 BIF 组成见上；当前 PetaLinux 输出还有 `boot.scr`、`image.ub`、DTB、rootfs 和 firmware 文件，清单记录各自 SHA | 没有官方镜像二进制，无法比较 FSBL/PMUFW/TF-A/U-Boot build ID、bootgen 版本或 patch。也无法证明板卡启动时用了此 BOOT.BIN 或 SD 上文件仍保持这些 SHA |
| FPGA/DPU | PetaLinux bit 与旧 100 MHz route 来源匹配，XSA HWH 却写 clockfix 新时钟；新 clockfix BIT XSA 内部 hash 一致，DPU IP v4.1.0/B2304，arch fingerprint `0x101000056010405`。新设计时序报告过关，但 reset 网表验收失败 | 旧栈若正在板上运行，固定 DT 200/100 与实际 100/100 的不一致可能影响 DPU；无法证明该不一致单独造成当前错误。新 route 的 reset 输入实际最终值未知 |
| PetaLinux/Linux | 本地 `image.ub` FIT 说明 Linux 5.15.36 `xilinx-k26-kv`，内核提交短标识 `19984dd147`；DTB 与 FIT 内 DTB 哈希相同；rootfs manifest VART/XIR/library 是 3.0 | 无官方对照 image/rootfs；无当前板端 `/proc/version`、`uname -a`、模块 SHA/vermagic、配置、补丁清单与运行 DTB 哈希。过往 9/25 板端记录为 `5.15.36-xilinx-v2022.2`，只是历史快照 |
| Runtime/ABI | rootfs manifest package labels 统一为 3.0。本地 rootfs 中五个 ELF 的 SHA256、SONAME（均为 `.so.3`）和 Build ID 见 [local_runtime_elf_provenance.txt](/home/ghmd/kv260_full_image_audit_20260926_codex/reports/local_runtime_elf_provenance.txt:1)–[24]；这些值只代表本机 image，不代表板端 | 用户指出板端 `libvart-runner`/`libxir` 构建日期为 2026-09-20、`dpu_task` 为 2023-01-13；没有板端 ELF 原文件/build-id、源码 commit、补丁或 ABI diff。日期差异本身不构成错配事实，不能认定为根因 |
| DMA/内存 | DT DPU reg/interrupt/clocks 已解包；用户报告输入/参数读回及输出字节相同，但未提供可核验原始材料 | AXI master address width、SMMU stream ID/IOMMU domain、DMA mask、CMA/reserved memory、cacheable/coherent 属性、实际物理地址和 VART sync 调用路径尚未形成同一 run 证据链；不能判定 DMA/cache 正常或异常 |
| 时钟/复位 | 当前旧镜像 XSA/HWH/DT 与本地旧 bit 不一致；新旧两代 OOC DCP 的 reset top ports 都无负载，内部 DPU reset pins 在 OOC 对象模型中连到 `<const0>`；新旧 routed DCP 的两个 DPU reset boundary pins 都断连。新 DCP 的断连从 opt 阶段开始 | AMD PG338 v4.1 仍要求三时钟各自有同步 reset，且两路 pin 是 active-low reset。是否为合法 IP 内部实现约定或功能错误**未确认**；板端 200/100 值也不是独立时钟测量 |
| 模型/输入/应用 | 新 XMODEL SHA 与编译来源记录吻合；架构 fingerprint 和编译记录一致；本机浮点/QAT CPU 检查曾在猫图上识别为 cat | 最新板端载入文件身份、preprocess/labels/app binary SHA 和输出 raw trace 未独立复核。CPU 成功只排除部分模型/输入问题，不证明板端 DPU 的量化执行、时序、buffer cache 同步正确 |

## D. 新 routed DCP reset 差异专项

Vivado 2022.2 只读 Tcl 逐个 `open_checkpoint` 现有 synth、opt、placed、physopt、routed DCP；没有写入工程或 checkpoint。结果完整保存在 [reset_stage_connectivity.txt](/home/ghmd/kv260_full_image_audit_20260926_codex/reports/reset_stage_connectivity.txt)，Vivado 最终日志/journal/stdout 也在同目录 `reports/`。

| 阶段 | `dpu_2x_resetn` | `m_axi_dpu_aresetn` | reset controller | DPU clocks |
|---|---|---|---|---|
| synth | `IS_CONNECTED=1`，连 `rst_dpu_dsp_peripheral_aresetn` | `IS_CONNECTED=1`，连 `rst_dpu_clk_peripheral_aresetn` | `rst_dpu_dsp` 存在；reset net fanout 包含 DPU 与 controller | 两 pin 均连接 |
| opt | `IS_CONNECTED=0`，无 net | `IS_CONNECTED=0`，无 net | `rst_dpu_dsp` 消失；1x reset net 只留 controller 与 AXI interconnect | 两 pin 均连接 |
| placed / physopt / routed | 一直 `IS_CONNECTED=0` | 一直 `IS_CONNECTED=0` | `rst_dpu_dsp` 仍不存在 | 两 pin 均连接 |

`reset_stage_connectivity.txt` 行 1–27 为 synth，28–42 为 opt，43–72 为 placed/physopt，73–87 为 routed。**首个观测到 BD 层断连差异的阶段是 opt DCP。** 这次审计后来发现已有独立审计保存了更早一层的只读证据：

- 新、旧 DPU IP OOC DCP 的顶层 `dpu_2x_resetn`、`m_axi_dpu_aresetn` ports 都是 fanout 0；`inst/dpu_2x_resetn` 与 `inst/m_axi_dpu_aresetn` 显示接到 `<const0>`，而 clocks 和 `s_axi_aresetn` 有负载。完整摘录在 [ip_ooc_and_new_routed_reset_topology.txt](/home/ghmd/kv260_full_image_audit_20260926_codex/references_prior_audit/ip_ooc_and_new_routed_reset_topology.txt:1)–[18]，旧/新 OOC 段落逐项相同；文件 SHA256 `81ea7864223269050e2b8019f5acf2feed4326ef8d081f4d31127dc5cfaddada`。此前 DeepSeek 审计报告（`/home/ghmd/Downloads/kv260_audit_deepseek_20260926/REPORT.md`，SHA256 `fc5e6f0f499503b26a915473328d24db8a78567bac7ea728d0118b81ae7896df`）对该现象作了“无害”解释，但那是摘要结论，不是原始对象证据。本审计不沿用该安全判定，依据原始 Vivado 查询结果和 PG338 要求保留为未解决风险。
- 旧 DPU IP routed DCP 对应 reset pins 也断连；证据 [orig_routed_reset_query.txt](/home/ghmd/kv260_full_image_audit_20260926_codex/references_prior_audit/orig_routed_reset_query.txt)，SHA256 `c31302ff45d418eb6334a40a867cc7b414483166d4e2d5ebc077367ab69106eb`。这表示不是 9/26 clockfix rebuild 独有的优化回归。
- 明文 IP wrapper 的实例化连接仍把 reset 端口传给 IP（[ip_sv_inst_block.txt](/home/ghmd/kv260_full_image_audit_20260926_codex/references_prior_audit/ip_sv_inst_block.txt)，SHA256 `b8e287b8d83a55d937859fcc6b4441d2fe4af9cbf692b9a0f7a4d1bdd00befd3`）；已有仿真 netlist 摘录却将这两端口连 `1'b0`（[new_sim_netlist_inst_context.txt](/home/ghmd/kv260_full_image_audit_20260926_codex/references_prior_audit/new_sim_netlist_inst_context.txt)，SHA256 `eeb04e2d33f38cb4c907051cfa9f078474d079e30a6a664453166dabeef300e5`）。仿真 netlist 不是 BIT 语义或电平的证明，只是又一处应由 AMD 资料解释的差异。
- 新实现 `opt_design` 日志只有全局优化统计：Constant propagation 删除 1,575 cells，Sweep 删除 1,246 cells；Tcl 注释要求 `-debug_log` 才能看到更细节。筛选输出 [impl_opt_keywords.txt](/home/ghmd/kv260_full_image_audit_20260926_codex/references_prior_audit/impl_opt_keywords.txt) 的 SHA256 是 `b1d9fa17cf3cbf0e1c5e3fb6ad9e2265ebe7a65c5319ad06ebec5d6ceb6be03f`。现有证据支持“无可见 OOC 负载 → opt 清理上层网”这个机制，但**不证明为什么 IP OOC reset 无负载，也不证明这种 tied-low 语义安全**。

DPU OOC DCP 的本次简化 port query 显示 reset 和 clocks 都作为 top input port 存在，见 [dpu_ooc_port_query.txt](/home/ghmd/kv260_full_image_audit_20260926_codex/reports/dpu_ooc_port_query.txt:1)–[8]；但它并未检查 input port 是否有内部负载。已有独立审计的深层对象查询显示前述 reset input ports fanout=0。生成 BD HDL 在新构建报告行 83–87 显示 reset 连接；新 XSA HWH [fresh_rebuild_xsa_embedded.hwh](/home/ghmd/kv260_full_image_audit_20260926_codex/extracted/xsa/fresh_rebuild_xsa_embedded.hwh:2631)–[2644]、[4326]–[4353]、[5259]–[5262] 仍描述 reset 连接。BD/HWH 记录连接意图，OOC/routed DCP 记录综合对象模型；结合 AMD 对 reset 的要求，目前语义冲突未解决。

还未验证 OOC checkpoint 链接/封装产生 tied-low 的原因、Vivado synthesis 与 IP 加密 RTL 之间的约定、以及 `<const0>` 在实际硬件的有效状态。AMD PG338 v4.1 的 [Reset 章节](https://docs.amd.com/r/en-US/pg338-dpu/Reset) 说每个输入 clock 都有对应 reset，各 reset 必须与对应 clock 同步，未同步不能保证 DPU 正常工作，并推荐 Processor System Reset IP；[Port Descriptions](https://docs.amd.com/r/en-US/pg338-dpu/Port-Descriptions) 将 `dpu_2x_resetn` 定义为 DSP block active-low reset，将 `m_axi_dpu_aresetn` 定义为 DPU general logic active-low reset。于是 DCP 内部 tied-low/无负载值得视为**高优先级未解决问题**，而不是安全通过证据。即使 STA 约束路径通过、DRC 0 errors、bitgen 成功，也不能覆盖 reset 语义冲突。新构建报告 [REPORT.md](/home/ghmd/kv260_clockfix_rebuild_20260926/REPORT.md:7)–[10]、[57]–[79] 和 [81]–[96] 给出完整签核上下文：WNS +1.462 ns、WHS +0.009 ns、0 failing endpoints，但有 342 warnings。

## E. 板端与模型证据

- 主机 `lsblk` 只看到 NVMe 与 loop devices，没有 SD/USB 块设备；`findmnt /media/ghmd/boot` 未找到该挂载点。主机 `/dev/ttyUSB*`、`ttyACM*` 当前也没有板端串口可读。**没有本次板端运行时证据**，不能核验正在执行的 kernel、DTB、模块、VART/XIR ELF、boot source 或 PL bitstream SHA。
- 既有 9/26 启动日志（原文件 `/home/ghmd/work/kv260-boot-audit-live/serial-boot-raw.log`，SHA256 `153aa69bba57792298f659e4cfdc7f248f3e78cc74aab22b1e6d9949679d46b`）记录：QSPI FSBL/PMUFW 为 2023.2、BL31 v2.8 2023.2、U-Boot 2023.01；该次手工从 SD 载入 122,901,532-byte `image.ub`，设置的 bootargs 含 `initcall_blacklist=xlnx_dpu_drv_init`，明确屏蔽 DPU driver initcall。该文件长度不等于本机现有 130,879,552-byte `image.ub`。这是先前一次启动的历史证据，不能据此推断用户本轮更新的推理 run 使用了相同启动参数；需要对那次最新 run 单独采集。
- 2026-09-25 历史日记记载当时板端 `5.15.36-xilinx-v2022.2`、DPUCZDX8G B2304 IP v4.1.0、`xdputil query` 时 DPU/XRT 显示 100 MHz、Vitis AI 3.0，且该次未推理，见 `/home/ghmd/AMD_Smart/logs/daily/2026-09-25.md:5`–[7]。这只是历史快照，不应覆盖用户所述的更新运行。
- 用户本轮补充：最新 run 的模型 SHA 是 `330a654a…7434da`；权重/指令/输入读取字节与文件相同，DDR 输出和 VART 返回值逐字节相同；分类仍错、重复结果波动，猫图与全零输入的差异不明显超过波动；CPU float/QAT 能识别猫图；未见明确 DPU timeout/DMA/IOMMU fault。**以上属于用户提供事实，本次没有原始日志、读回文件或 board 运行时来复验。** 其中字节传输相等只能说明指定数据副本相同，不能证明执行器件产生数学正确输出。
- fingerprint `0x101000056010405` 与新 XMODEL 编译 provenance 对齐；PG338 要求 architecture/AXI width 改变后按新 `arch.json` 重新编译模型。该匹配只排除“新模型编译时完全没用目标 arch.json”的一种问题，不证明板上加载的 bit 与模型对应，也不证明模型计算正确。

## 候选根因排序

1. **确认的交付错配，因果关系仍待验证：** PetaLinux current bit 为旧 100/100 MHz 实现，XSA HWH/DT 表达新 200/100 MHz 设计。若这正是最近 run 实际启动/加载的组合，则驱动/软件认识的时钟拓扑与 PL 真实拓扑不一致，是较强的系统级候选。当前实际加载身份无法只读核验，不能宣称它已解释输出随机性。
2. **确认的 reset 语义冲突，根因和板端因果仍未确认：** 新/旧两代 DPU OOC DCP 都没有两个 reset top port 的可见负载，并把 IP instance reset pins 映射到 `<const0>`；旧/新 routed DCP 的 reset boundary pins 均断连，opt 的清理路径因此有较强机制证据。AMD PG338 又明确要求对应同步 reset 且为 active-low。若 `<const0>` 作用于这些功能 reset 输入，可能导致 DPU logic 处于 reset；但 encrypted RTL、DCP 对象和器件配置尚不能证明它在实物中的最终效应。新 BIT/XSA 在语义问题解决前必须阻断上板。
3. **特定历史启动曾禁用 DPU driver：** 既有串口 log 的 bootargs 含 `initcall_blacklist=xlnx_dpu_drv_init`，且当次 SD `image.ub` 大小与本机现有文件不同。这对那次启动是已确认事实；是否为用户最新推理使用的启动状态未确认，不能混为最新 run 根因。
4. **未确认的 runtime/ABI 差异：** 板端 VART/XIR/dpu_task 构建日期不同；缺少 ELF 哈希、SONAME、build-id、源码 commit、patch 和 `vermagic` 对比。仅版本字符串 3.0 或日期不能判因果。
5. **未确认的 DMA/cache/设备树/driver 兼容性：** 物理地址范围、coherency、SMMU、DMA mask、VART cache sync 与 kernel driver 需同次 run 追踪。没有明确 fault 日志降低了“已观察到硬错误”的证据，但不能排除静默错误。
6. **未确认的模型或输入后处理问题：** 本机 CPU float/QAT 通过是有用对照，但板端输入预处理、layout/quantization、labels 和实际执行 XMODEL 来源未闭环；用户的逐字节复制核对也不能证明算术正确。

## 继续定位所需的最少只读取证

1. 从出现问题的那次板端导出原始文本/文件哈希：`uname -a`、`/proc/version`、`cat /proc/cmdline`、运行 DTB 的 SHA256（先取得其文件路径）、`cat /sys/kernel/debug/clk/clk_summary`（仅普通只读文本节点；不得向 debugfs 控制文件写入）、`dmesg`、`lsmod`、`modinfo`/模块文件 SHA256、DPU driver/sysfs 可见的版本信息，以及运行中的 `libvart-runner`、`libxir`、`libvitis_ai_library-dpu_task` ELF 的 SHA256/SONAME/Build ID。保存输出与采集时间，不触发推理或重载。
2. 对实际 boot SD 只读记录分区布局、BOOT.BIN/image.ub/boot.scr/system.dtb/system.bit SHA256；如正在使用 JTAG，保留精确编程命令、被选文件 SHA 和启动时间。只读文件哈希无法证明 PL 配置寄存器内容，若设备不提供无副作用配置身份回读，则将 bit 身份继续标未确认。
3. 对 reset 语义补齐 AMD 官方依据：PG338 v4.1 中 tied-low/未使用 reset pin 是否为合法生成 IP 特例的说明或 AMD 支持答复；以及 Vivado implementation DCP 内可见的 reset endpoint/driver 证据，解释 OOC `<const0>` 如何与 PG338 active-low synchronous reset 要求共存。现有日志可定位 opt 阶段的删网，但不能证明其子步骤。即使找到 netlist 机制，实际 BIT 内有效复位值仍需与 HWH 分开的证据。
4. 做官方镜像对照所需最少资料：由用户/AMD 官方下载流程提供官方文件 `xilinx-kv260-dpu-v2022.2-v3.0.0.img.gz` 和 AMD 官方校验和/签名元数据（本轮不下载），以及镜像版本发布说明；再在独立只读目录对 BOOT/FIT/rootfs/bit/HWH 成员抽取、计算 SHA 与 build-id。还需官方或原始导出来源明确 B2304 参数和 fingerprint；仅镜像名不能证明。
5. 对 runtime ABI/DMA，需要板端运行中**原样现存**驱动模块与运行库、对应 kernel config/源码 commit/补丁、设备树、VART/DPU buffer 类型和同步路径日志；只读地址/属性记录应脱敏，避免暴露业务数据或凭据。

## 官方参考资料

- AMD Vitis AI Library v3.0 release notes：KV260 镜像名与受支持 EVB 清单，见 Compatibility / Device Support：<https://docs.amd.com/r/3.0-English/ug1354-xilinx-ai-sdk/Vitis-AI-Library-v3.0-Release-Notes>
- AMD Vitis AI 3.0 UG1414 镜像下载说明（KV260 预构建 image 链接）：<https://docs.amd.com/r/3.0-English/ug1414-vitis-ai/Flashing-the-OS-Image-to-the-SD-Card>
- AMD PG338 v4.1 Development Tools：Vivado 2022.2 或更高版本推荐：<https://docs.amd.com/r/en-US/pg338-dpu/Development-Tools>
- AMD PG338 v4.1 IP Facts：Zynq UltraScale+ 支持、驱动说明、模型重新生成要求：<https://docs.amd.com/r/en-US/pg338-dpu/IP-Facts>
- AMD PG338 v4.1 Reset：对应时钟同步 reset 的要求：<https://docs.amd.com/r/en-US/pg338-dpu/Reset>
- AMD PG338 v4.1 Port Descriptions：两路 reset 为 active-low input：<https://docs.amd.com/r/en-US/pg338-dpu/Port-Descriptions>
- AMD/Xilinx Vitis AI v3.0 官方发布说明：DPUCZDX8G 更新适配 2022.2：<https://github.com/Xilinx/Vitis-AI/releases/tag/v3.0>

## 本报告附件

- [命令和只读状态清单](/home/ghmd/kv260_full_image_audit_20260926_codex/COMMANDS.md)
- [全量 SHA256 清单](/home/ghmd/kv260_full_image_audit_20260926_codex/SHA256SUMS.txt)
- [文件清单](/home/ghmd/kv260_full_image_audit_20260926_codex/reports/artifact_inventory.tsv)
- [实现阶段 reset 查询结果](/home/ghmd/kv260_full_image_audit_20260926_codex/reports/reset_stage_connectivity.txt)
