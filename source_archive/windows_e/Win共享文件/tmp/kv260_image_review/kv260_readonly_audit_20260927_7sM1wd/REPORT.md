# KV260 开发环境只读审查报告

审查日期：2026-09-27（主机本地时间）。对象：`/home/ghmd` 中可读的 Ubuntu 主机、2022.2 工具、工程、候选系统产物，以及下载的官方镜像文件。原环境未修改；本目录仅保存静态查询和分析结果。没有连接板卡、磁盘分区或 Docker 容器。**本报告的“当前”仅指审查时主机文件，不代表板端本次实际加载状态。**

## 结论与证据等级

| 等级 | 本次判断 |
|---|---|
| 已确认损坏 | 未发现 Ubuntu 核心包、工程关键文件或官方镜像压缩流损坏的证据。`/home/ghmd/work/Vitis-AI-v3.0.zip` 为 **0 字节**，是已确认不可用的下载文件；不能据此认定旁边解压源码损坏。 |
| 已确认不完整或缺失 | 主机包记录中 `flex`、`bison` 为 `not-installed`，`socat` 未找到；Vitis AI 源码目录无 `.git`，不能提供 checkout commit；官方镜像尚无官方校验值。旧工程原始 DPU routed DCP 存在，新工程 DCP 也存在。 |
| 已确认版本、路径或产物错配 | 9 月 26 日重建 XSA/bit（bit SHA256 `d316ee9c…`）尚未进入当前 PetaLinux XSA、`images/linux/system.bit` 和 SD 候选目录（均使用 bit `6a75e223…`）。这是**最新重建成果与候选系统版本不一致**；当前候选 XSA、独立 bit 与 FIT DTB 的静态关联反而相互吻合。 |
| 有风险但尚未证实 | 历史 Vivado 安装记录有两个设备列表后置步骤失败；相关输出文件如今存在，工具和 K26 器件也可用。DPU 两路 reset 的优化后连接语义未解释。候选 `BOOT.BIN` 成员字节身份、板端实际 QSPI/SD/库状态、模型对实际 DPU 的兼容性未证实。 |
| 检查通过 | Ubuntu 20.04.4 为 2022.2 文档列出的主机版本；`dpkg --audit` 空、选定核心包 `dpkg -V` 空；Vivado v2022.2 可启动；PetaLinux 安装日志完成；官方 `.img.gz` 本地 SHA256 与给定值一致、`gzip -t` 通过；现有 XSA ZIP 成员 CRC 检查通过；当前 FIT 的内嵌 DTB、ramdisk、解压 kernel 与旁边独立文件逐字节哈希相同。 |
| 未检查或无法验证 | 官方发布哈希、主机 Docker 镜像实时 ID/摘要、许可证**当前**可用性、板端启动和推理、全部 ext4 内容校验、BOOT.BIN 内每一成员与 BIF 输入的字节等同性，以及 DPU reset 功能语义。 |

## A. Ubuntu 主机与存储

证据：[host.txt](logs/host.txt)、[package_state.txt](logs/package_state.txt)、[package_verify.txt](logs/package_verify.txt)、[host_errors.txt](logs/host_errors.txt)、[kernel_storage_oom_matches.txt](logs/kernel_storage_oom_matches.txt)、[dependency_status.txt](logs/dependency_status.txt)、[build_fail_matches.txt](logs/build_fail_matches.txt)。系统为 Ubuntu 20.04.4 LTS、x86_64、内核 `5.15.0-139-generic`；30 GiB RAM、15 GiB swap。`/home/ghmd` 位于 `/dev/nvme0n1p10` 的 ext4，约 328 GB 容量、290 GB 已用、**22 GB 可用（94%）**，inode 余量约 1963 万。`lsblk` 只用于识别设备；未触碰任何设备分区。AMD [PetaLinux 2022.2 UG1144 安装要求](https://docs.amd.com/r/2022.2-English/ug1144-petalinux-tools-reference-guide/Installation-Requirements)列 Ubuntu 20.04.4 为支持系统，并给出 100 GB 空闲磁盘要求；当前空间明显低于新建完整构建的参考要求。

**A1，已确认容量风险，影响正式重建，不妨碍验证已下载镜像。** 原始证据为 `df -hT /home/ghmd` 的 22 GB 空闲、94% 使用率。影响是新的 Vivado/PetaLinux 构建、Yocto 下载或解包可能写满盘；当前未发现 `No space left` 构建错误。下一步先选择有足够空间的新构建位置或规划容量，不能从“空间不足”推断已有文件损坏。官方镜像文件校验不需要重建空间。

**A2，系统损坏证据未发现。** `dpkg --audit` 无输出，选定 `bash/coreutils/dpkg/libc6/libstdc++6/gcc/g++/make/git/python3/zlib1g` 的 `dpkg -V` 无差异。扫描可见内核日志未找到 `I/O error`、`EXT4-fs error`、OOM kill；`EXT4-fs … re-mounted. Opts: errors=remount-ro` 是挂载选项行，并非已经发生的 ext4 错误。当前 journal 有 ACPI、蓝牙、无线接口和 fwupd 报错，见 `host_errors.txt`，未建立与 KV260 文件损坏的因果关系。检查范围限于可读 journal 和选定包，**不能保证整盘完全正常**。如今没有重装 Ubuntu 的证据基础。

**A3，主机依赖缺口，影响未来环境复核和重建，通常不妨碍官方镜像文件校验。** `dpkg-query` 显示 `flex`、`bison` 未安装，未找到 `socat`；`libtinfo5`、`libncurses5-dev`、`libssl-dev`、`zlib1g-dev` 已安装，`/bin/sh` 指向 bash。`device-tree-compiler`、`u-boot-tools` 宿主包未找到，但 Xilinx 随工具提供 `dtc`、`bootgen`，不能据此认定项目缺少 DTB/BOOT 生成能力。已有多次 PetaLinux 构建成功，说明缺少这几个宿主包未证明当时的构建失败。下一步在正式重建前以该版本 release notes 核对精确依赖清单，再补必要包；本次未安装任何软件。

## B. Vivado / Vitis 安装

证据：[vivado_version.txt](logs/vivado_version.txt)、[vitis_version.txt](logs/vitis_version.txt)、[xinstall_poststeps.txt](logs/xinstall_poststeps.txt)、[source_refs.txt](logs/source_refs.txt)、[fpga_build_excerpt.txt](logs/fpga_build_excerpt.txt)。当前 `vivado` 解析到 `/home/ghmd/Xilinx/Vivado/2022.2/bin/vivado`，版本 `v2022.2`、SW build `3671981`、IP build `3669848`，`-version` 退出 0。`vitis` 路径为 `/home/ghmd/Xilinx/Vitis/2022.2/bin/vitis`，打印 `v2022.2`、build `3671529`，该启动器的 `-version` 调用退出 255，不能把此标志调用当作 Vitis 整体功能测试。`Vitis_HLS/2022.2` 存在，未独立启动。未发现 2022.2.1/2022.2.2 补丁证据。2022.2 [Vivado OS 列表](https://docs.amd.com/r/2022.2-English/ug973-vivado-release-notes-install-license/Supported-Operating-Systems)包含 Ubuntu 20.04.4。

**B1，历史后置任务失败，当前安装完整性仍有局部不确定性。** 原安装日志 `/home/ghmd/.Xilinx/xinstall/xinstall-2026-09-18_01-11-29.log` 的筛选行记录 `GenerateDevListFileLin` 和 Model Composer 设备列表生成因 `libtinfo.so.5` 当时缺失而失败，同时最终写 `Installation completed successfully`。审查时 `libtinfo5` 已安装，`/home/ghmd/Xilinx/Vivado/2022.2/data/parts/installed_devices.txt`、`Model_Composer/2022.2/data/board_supported.csv` 已存在；K26 part 数据和 KV260 SOM 1.4 板卡文件存在。两个 IP repo 的 `component.xml` SHA 相同，新工程实现日志有 `Got license … xck26`、`write_bitstream Complete!`。因此确认**安装时发生过局部失败**，但不能宣称现有 Vivado 已损坏或必须重装。此项影响未来器件/Model Composer 枚举的可信度；下一步只读核对需要的功能列表与现有文件，正式重建时在隔离目录验证。9 月 26 日取得过 Implementation 许可不证明本次审查时许可仍有效；许可证内容未读。

`/home/ghmd/Xilinx/Downloads/Vivado_2022.2/payload` 是约 466 MB 安装下载缓存，不是 114 GB 的实际 Vivado 安装目录；不能以缓存零散文件判断安装未完成。实际 `Vivado/2022.2` 约 114 GB、`Vitis/2022.2` 约 13 GB。`.bashrc` 第 122 行加载 Vitis 2022.2 设置，因此本 shell 中 Vivado/Vitis 命令可见。PetaLinux 未进入 PATH 是未加载它的环境脚本，不等于没有安装。官方 [PetaLinux 环境问题说明](https://docs.amd.com/r/2022.2-English/ug1144-petalinux-tools-reference-guide/PetaLinux-Environment-Issues)提醒与已有 Xilinx 环境变量混用可能导致问题；现有全局 Vitis 环境是**潜在路径冲突**，本次没有构建验证冲突实际发生。

## C. PetaLinux 工具、项目和构建记录

`/home/ghmd/petalinux/2022.2/.version-history` 写 `PETALINUX_BASE_VER=2022.2`，`settings.sh` 写 `PETALINUX_VER=2022.2`，`tools/common/petalinux/bin/petalinux-build` 存在；`petalinux_installation_log` 记录 SDK、buildtools、extended buildtools 安装成功，只提示未发现 TFTP server。`/home/ghmd/work/petalinux-kv260-dpu` 当前项目配置 `CONFIG_YOCTO_MACHINE_NAME="xilinx-k26-kv"`、`CONFIG_SUBSYSTEM_ROOTFS_INITRD=y`。工程内旧的 `.before-*` 备份和多个 `sd-card-staging-*` 目录都存在，代表多个候选版本，不应交叉取文件。

**C1，当前项目的硬件来源与最新重建成果不一致，阻碍将最新重建 bit 称为已集成系统。** `project-spec/hw-description/system.xsa` 与 `/home/ghmd/work/kv260_dpu_b2304_uram/output/kv260_dpu_clockfix.xsa` 完整文件 SHA 都是 `08abccc5…`；该 XSA 内 bit 和当前 `images/linux/system.bit` 都是 `6a75e223…`。最新 `/home/ghmd/kv260_clockfix_rebuild_20260926/artifacts/kv260_dpu_clockfix_rebuilt.xsa` 为 `76e8d105…`，内嵌 bit 为 `d316ee9c…`。因此当前项目没有引用最新 XSA。对“直接用官方镜像”没有影响，对最新自定义镜像发布是阻断项。下一步明确选择哪一套硬件为基线，在新目录重建配套 PetaLinux 与镜像，并记录一次构建的输入哈希和产出清单。见 [artifact_hashes.tsv](logs/artifact_hashes.tsv)、[xsa_members.tsv](logs/xsa_members.tsv)。

**C2，现有构建曾成功，但 images/linux 不是单次构建来源证明。** `petalinux-build.log` 末尾 `Attempted 5762 … all succeeded`、`Successfully built project`；其他日志有 `Attempted 7030 … all succeeded`。`Failed to copy built images to tftp dir: /tftpboot` 出现在成功之后，属于 TFTP 拷贝阶段，不能等同内核构建失败。多个后续重新配置与 staging 目录表明文件更新过；时间戳本身不构成同源证明。好在当前 `image.ub` 的 FIT 内核解压哈希等于 `images/linux/Image`，FIT DTB 等于 `system.dtb`，FIT ramdisk 等于 `rootfs.cpio.gz`；这是对当前 FIT **三个成员**的字节级关联，不能延伸到 `BOOT.BIN` 或板端实际 SD。证据：[petalinux_build_excerpt.txt](logs/petalinux_build_excerpt.txt)、[fit_members.txt](logs/fit_members.txt)。

PetaLinux 的 Vitis AI recipes 在 `project-spec/meta-user/recipes-vitis-ai/vitis-ai-library/vitisai.inc` 指定 Git `SRCREV=c5d2bd43d951c174185d728b8e5bcda3869e0b39`；这是可追溯的**配方目标提交**，并非审查时主机解压源码的 commit，也未确认未来网络或下载缓存一定可取到它。

## D. Vitis AI、Docker 与模型

**D1，已确认一个 0 字节源码 zip 不可用；主机源码身份未证实。** `/home/ghmd/work/Vitis-AI-v3.0.zip` 为 0 字节；`/home/ghmd/work/vitis-ai-source/Vitis-AI-3.0` 有源码树，但 `git rev-parse` 返回“不是 git 仓库”，没有 tag、commit 或源归档校验值。影响自定义重建的可追溯性；不影响官方镜像文件的哈希/gzip 检查。下一步重建时从可核验的 v3.0 tag/归档或配方固定 commit 建立干净源基线，不能用零字节 zip 作来源证明。此 zip 是**源码下载对象**，绝非板端 OS 镜像。证据：[vitis_ai_source_state.txt](logs/vitis_ai_source_state.txt)。AMD [Vitis AI 3.0 发布页](https://github.com/Xilinx/Vitis-AI/releases/tag/v3.0)提供 v3.0 tag；该 tag 与本地配方 SRCREV 是否同一内容未验证。

**D2，模型只能作为候选。** 旧 `resnet50_b2304.xmodel` SHA `acf77c7f…`，9 月 26 日另一次编译的 `resnet50_b2304_verified.xmodel` SHA `330a654a…`；两份 `meta.json` 都写 `DPUCZDX8G_ISA1_B2304`，对应工程 `arch.json` 内容 `{"fingerprint":"0x101000056010405"}`、SHA `ac3853f7…`。过去编译日志显示 `Target architecture: DPUCZDX8G_ISA1_B2304` 并生成产物，但这只证明编译器按所给 arch 输入工作。没有本次板端 fingerprint、实际位流/运行库或推理功能证据，不能判定与当前板端兼容。历史 `compile_provenance.txt` 记过 Docker image ID `sha256:8b2d3517…` 和 `vai_c_xir` 命令，但本次未实时复核容器 ID/摘要。证据：[artifact_hashes.tsv](logs/artifact_hashes.tsv)、[model_compile_excerpt.txt](logs/model_compile_excerpt.txt)、[model_provenance_excerpt.txt](logs/model_provenance_excerpt.txt)。

Docker 服务状态查询返回 `Failed to connect to bus`；为遵守不启动服务或改 Docker 的边界，未向可能被 socket 激活的 daemon 请求镜像清单。量化器、编译器、主机 XIR/VART 当前安装身份因此为**未验证**；不能把过去容器镜像或主机运行库当成板端运行库。

## E. FPGA/DPU 工程、时钟和 reset

`/home/ghmd/work/kv260_dpu` 为早期工程；`/home/ghmd/work/kv260_dpu_b2304_uram` 含旧 routed DCP 和旧/中期 XSA；`/home/ghmd/kv260_clockfix_rebuild_20260926` 是隔离重建工程，含新 routed DCP、bit、XSA。三个 XPR 均为 Vivado 2022.2、器件 `xck26-sfvc784-2LV-c`、板卡 `kv260_som:part0:1.4`。XPR 的 BD、wrapper、旧工程导入 DCP 引用均存在；IP `component.xml` 的 22 个本地文件引用无缺失。新工程 IP repo 与 `/home/ghmd/work/dpu/.../DPUCZDX8G_v4_1_0` 逐文件 `diff -qr` 退出 0。两个 repo 是相同副本，当前 XPR 各自有明确路径；**目前没有证据表明发生 IP 版本覆盖**，但搬动目录时绝对工程路径及引用需要重新确认。证据：[source_refs.txt](logs/source_refs.txt)、[ip_repo_diff.txt](logs/ip_repo_diff.txt)。

原 XSA `kv260_dpu.xsa` 的 bit SHA `82166677…`，HWH 的 DPU 时钟端口约 99.999/99.999 MHz；中期 clockfix XSA 的 bit `6a75e223…`，HWH 的 `dpu_2x_clk=199998002 Hz`、`m_axi_dpu_aclk=99999001 Hz`；最新重建 XSA 的 bit `d316ee9c…`，HWH 仍为 200/100 MHz 路线。当前 DTB 的两个 fixed-clock 值为 `0x0bebba32`（199998002）和 `0x05f5dd19`（99999001），DPU 地址 `0x400000000`、中断 GIC SPI 89，与中期 XSA HWH 的地址和钟值静态一致。XSA HWH/BD 是设计描述；bit 的内部真实时钟未做板端测量。9 月 26 日新实现的时序报告写 WNS 1.462 ns、WHS 0.009 ns、`All user specified timing constraints are met`，实现日志写 `write_bitstream Complete!`；这证明完成实现，不证明板端功能。较早的 9 月 21 日 clockfix 日志 WNS 12.892 ns 属于另一套产物，不应混用。证据：[xsa_clock_ports.txt](logs/xsa_clock_ports.txt)、[new_fpga_build_excerpt.txt](logs/new_fpga_build_excerpt.txt)、`/home/ghmd/kv260_clockfix_rebuild_20260926/reports/postroute_timing_summary.rpt`。参考 AMD [PG338 4.1 时钟要求](https://docs.amd.com/r/en-US/pg338-dpu/Reference-Clock-Generation)。

**E1，reset 网表风险仍待解释，阻碍自定义 DPU 的功能验收。** 现存原始查询输出而非摘要报告显示：旧 routed DCP 两路 `dpu_2x_resetn`、`m_axi_dpu_aresetn` 的 `IS_CONNECTED=0`；新 DPU OOC DCP 顶层对应端口 `FANOUT=0`，内部 `inst/...resetn` 接 `<const0>`；新设计 synth DCP 两路在 BD 层相连，opt 和 routed DCP 的 DPU 边界两路断连。见 [prior_orig_routed_reset.txt](logs/prior_orig_routed_reset.txt)、[prior_ip_ooc_reset.txt](logs/prior_ip_ooc_reset.txt)、[prior_reset_stage_connectivity.txt](logs/prior_reset_stage_connectivity.txt)，源文件哈希在 [prior_reset_sources_sha256.txt](logs/prior_reset_sources_sha256.txt)。这些是以往 Vivado 查询留下的原始输出，来源链相同的重复引用不是独立复验。本次曾在审查目录用 Vivado 只读 `open_checkpoint` 重新查询；工具成功打开 OOC 与 synth DCP，随后在 180 秒限制内未完成全部阶段，退出 124；不能将超时视为 DCP 损坏或新复验通过。

**可解释的优化机制：** OOC 顶层两路 reset 无可见内部负载，上层综合网表先保留连接，`opt_design` 可以清除无效网和专用 reset controller；这种机制与所见 synth→opt 差异一致。**仍未知的语义：** 为何 v4.1 IP OOC 把内部 reset pin 接常量、该常量在实现后对应什么有效行为、复位时序是否满足器件要求、板端真实运行是否可靠。AMD [PG338 4.1 Reset](https://docs.amd.com/r/en-US/pg338-dpu/Reset)要求各输入时钟有同步的复位；现有证据不足以宣布“无害”或“永久复位”。下一步需要 AMD IP 实现说明或受控板端功能/复位验收；本次不加载位流或推理。

## F. Linux 镜像、驱动与运行时

**F1，当前候选 FIT 成员已静态核对，BOOT.BIN 字节来源仍有限。** `image.ub` 为 FIT/FDT，含 arm64 gzip kernel、`fdt-system-top.dtb`、ramdisk。内嵌 kernel 解压 SHA `3296e0f0…` 等于 `images/linux/Image`；DTB SHA `f8f7b874…` 等于 `system.dtb`；ramdisk SHA `43468905…` 等于 `rootfs.cpio.gz`。`bootgen -read BOOT.BIN` 读得 FSBL、PL `system.bit`、BL31、`system.dtb`、U-Boot（PMUFW 在 boot header）；`bootgen.bif` 也列这些路径。但未对 BOOT.BIN 各分区解包逐字节比对，故**不声称 BOOT.BIN 内 bit/DTB 字节与同名输入文件相等**。对正式镜像发布，这是来源追踪待补项；对官方原厂镜像独立验证无影响。证据：[fit_members.txt](logs/fit_members.txt)、[bootgen_read.txt](logs/bootgen_read.txt)、[artifact_hashes.tsv](logs/artifact_hashes.tsv)。

**F2，内核/模块有基本一致证据，ABI 仍待板端核实。** 当前 `Image` 包含 `Linux version 5.15.36-xilinx-v2022.2`；rootfs tar 中模块目录为 `/lib/modules/5.15.36-xilinx-v2022.2`，抽样及列出的 `.ko` `vermagic` 同为该版本；build `.config` 的 `CONFIG_XILINX_DPU=y` 表示 DPU 驱动内建而非一个需要匹配的 `xlnx_dpu.ko`。版本名/`vermagic` 相同不证明所有 ABI 符号完全匹配，也不说明板端当前所用内核。证据：[rootfs_runtime.txt](logs/rootfs_runtime.txt)、[rootfs_packages_excerpt.txt](logs/rootfs_packages_excerpt.txt)。

**F3，当前 rootfs 是 ramdisk 路线，运行库为自定义配方的 Vivado 集成候选。** PetaLinux 配置 `CONFIG_SUBSYSTEM_ROOTFS_INITRD=y`，FIT 内含 ramdisk；候选 SD 的 `boot.scr` 会优先找 `image.ub`，`uEnv.txt` 会从 SD 加载 `system.bit`。rootfs manifest 有 `vart/xir/unilog/target-factory/vitis-ai-library 3.0`，tar 中有 `libvart-dpu-runner.so.3.0.0`、`libxir.so.3.0.0`；当前启用的是 `vart_3.0_vivado.bb`，没有在 manifest 找到 XRT 包。按配方和包清单，这是 Vivado 集成路线的构建证据，不是板端实时库身份。运行时写到 ramdisk 的应用配置一般不会因关机保留；SD 的 `uEnv.txt` 等独立文件可保留。若应用需要持久化配置，须在下一阶段设计并验证单独存储位置。不同历史 QSPI/内核年份只能列为兼容性待核查，不据此建议直接降级固件。证据：[rootfs_packages_excerpt.txt](logs/rootfs_packages_excerpt.txt)、[boot_script_excerpt.txt](logs/boot_script_excerpt.txt)。

## G. 官方镜像文件

对象：`/home/ghmd/下载/xilinx-kv260-dpu-v2022.2-v3.0.0.img.gz`，3,503,938,277 字节。重新计算 SHA256 为 `a8599cc033920207953a3eb954be1b925465e77c3ca835b26ef1ccfa903441d0`，与用户提供的双端值一致；本次 `gzip -t` 退出 0。前 17,408 字节显示 MBR 签名 `55aa`，两个分区：LBA 8 起 154590 扇区、LBA 154600 起 18366492 扇区；第二分区 ext 超级块魔数 `53ef`。进一步静态读取前约 79 MB：第一分区 FAT BPB 标为 `FAT16`，根目录可见 `BOOT.SCR`、`IMAGE`、ramdisk、两个 DTB；MBR 分区类型字节为 `0x0c`（通常表示 FAT32 LBA），与 FAT16 BPB 标签不同。这是**元数据差异，未证明文件损坏**；原厂镜像可能有特定分区制作方式，需要以官方哈希和实际读取行为核实。第一分区没有看到 `BOOT.BIN`，不能从此推断板端无法启动，因为 KV260 还涉及板上 QSPI 启动链。没有完整解包、fsck、烧录或挂载镜像。证据：[official_image_sha256.txt](logs/official_image_sha256.txt)、[official_image_partition_header.txt](logs/official_image_partition_header.txt)、[official_image_static.txt](logs/official_image_static.txt)。

AMD [UG1354 3.0](https://docs.amd.com/r/3.0-English/ug1354-xilinx-ai-sdk/Vitis-AI-Library-v3.0-Release-Notes)明确列该文件名为 Vitis AI Library 3.0 测试镜像；[UG1414 下载说明](https://docs.amd.com/r/3.0-English/ug1414-vitis-ai/Flashing-the-OS-Image-to-the-SD-Card)给出受账户下载页。公开可访问页面没有取得该文件的官方 SHA256/MD5；**官方校验未完成**。两台电脑的相同哈希和 gzip 检查只能证明本地一致与压缩流完整，不能替代官方发布值。也没有证据表明官方镜像 DPU 与自定义 B2304/fingerprint 相同。官方镜像的文件验证独立于宿主 Vivado/PetaLinux 缺口；后续板上功能验证还需要确认实际 QSPI/SD 启动链，但本次没有执行。

## H. 板端状态

没有本次明确的板卡连接信息，也未收到允许使用的现成会话；没有扫描网络、打开串口、连接 JTAG 或读取板端。过去日志中的 QSPI 2023.2、Linux 2022.2、`initcall_blacklist=xlnx_dpu_drv_init` 仅作为历史线索，不能写成当前实测。官方镜像验证及自定义镜像正式发布前，须在获授权的既有连接中只读采集 `uname`、`/proc/cmdline`、挂载、设备树、已加载固件、驱动和运行库身份；随后另行安排功能验收。

## 重建输入、产物保留与建议顺序

FPGA 原工程与隔离 clockfix 工程的 XPR/BD/IP 本地引用完整，K26 板卡/器件文件存在，DCP、bit、XSA 可保留作为**可追溯候选与对照**。最新 bit/XSA 可保留，但因 reset 未验收、系统未配套重建，不应列为正式板端镜像。当前 `images/linux` 与 SD staging 可保留作 9 月 21–24 日历史候选，不宜和 9 月 26 日重建 bit 混装；旧 `kv260_dpu.bit`、旧 routed DCP 主要供时钟/reset 对照。Vitis AI 源码副本和 0 字节 zip 不构成完整、已认证的源码基线；模型 xmodel 也仅作候选。故现有资料**基本具备 FPGA 结构输入，但不构成完整、可验收的一键正式重建输入包**：还缺明确的唯一硬件基线、可验证源码身份、构建容量/宿主依赖复核、BOOT 成员追踪及板端验收。

建议顺序：① 先完成官方哈希来源查证与官方镜像独立验证计划；② 为自定义路线定唯一新 XSA/bit/IP/arch 和模型版本，明确 reset 风险及板端验收标准；③ 准备充足空闲空间，核对并补齐正式重建所需宿主依赖，隔离 PetaLinux 环境变量；④ 在**新目录**重建 PetaLinux、BOOT/FIT/rootfs 并记录成员哈希，随后另行授权板端测试。**没有证据支持重装 Ubuntu 作为默认方案。** 本次停在审查，不执行上述修复、重建或板端操作。

## 审查限制与官方资料

日志可能不覆盖所有历史会话；有权限不足或无法安全只读验证的对象按“未检查”处理。DCP 新查询超时、Docker bus 不可访问、官方哈希未取得均不会归类为文件损坏。压缩包只附报告、清单和必要原始输出；不包含工具、系统镜像、模型大文件、环境变量或许可证敏感内容。主要外部依据：[PetaLinux 2022.2 UG1144](https://docs.amd.com/r/2022.2-English/ug1144-petalinux-tools-reference-guide/Installation-Requirements)、[Vivado 2022.2 UG973](https://docs.amd.com/r/2022.2-English/ug973-vivado-release-notes-install-license/Supported-Operating-Systems)、[Vitis AI 3.0 UG1354](https://docs.amd.com/r/3.0-English/ug1354-xilinx-ai-sdk/Vitis-AI-Library-v3.0-Release-Notes)、[PG338 4.1 Reset](https://docs.amd.com/r/en-US/pg338-dpu/Reset)、[PG338 4.1 Clock](https://docs.amd.com/r/en-US/pg338-dpu/Reference-Clock-Generation)。
