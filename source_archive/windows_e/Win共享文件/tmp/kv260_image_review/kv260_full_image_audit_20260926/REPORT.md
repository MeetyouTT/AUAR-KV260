# KV260 ResNet50 推理系统全栈只读来源与版本审计报告

> **本报告由 DeepSeek 完成**（AI 审计：在 Cline 环境中由 DeepSeek 规划并执行只读命令与 Vivado 只读对象查询，随后由 DeepSeek 汇总、判定与撰写）。
> 报告版本：v1.0 ｜ 完成时间：2026-09-26 22:20（本机本地时间）
> 署名：**DeepSeek** ｜ 无人工修改的原始命令与日志见 `COMMANDS.txt`、`logs/`、`extract/`、`reports/`。

- 审计日期：2026-09-26 / 2026-09-27（本机本地时间与 UTC 混用，均已在文件内标注）
- 审计目录（本报告唯一写入位置）：`/home/ghmd/kv260_full_image_audit_20260926/`
- 操作边界：全程只读。未修改源工程、BD、XPR、Tcl、模型、输入、设备树、驱动、镜像、板卡配置；未烧写、未加载 bitstream、未复位、未写寄存器、未加载/卸载模块、未切换时钟、未改变电源状态；未重新导出/量化/编译/打包；未安装软件、未下载镜像或二进制、未覆盖已有文件；报告、提取文件、哈希清单全部写入本诊断目录。
- 板卡操作：仅一次串口**被动**采样（`timeout 5 cat /dev/ttyUSBx`，未向串口写入任何字节，结果 0 字节）。未向板卡发送任何命令。

---

## 0. 摘要

### 0.1 已确认事实（均有路径+SHA/行号，见后文）

| 编号 | 结论 | 关键证据 |
|---|---|---|
| F1 | 本机**不存在**任何 AMD 官方 KV260 板级镜像文件（无 `*.img` / `*.img.xz` / `*.wic`）。只有 Vitis AI 3.0 源码副本（无 `.git` 元数据）、Vivado/Vitis 2022.2、`Downloads/AMD_KV260_2022.2/01_unified_installer` | `logs/evidence_official_images.txt`、`logs/evidence_official_source_2.txt` |
| F2 | 因此**无法完成**"当前系统 vs AMD 官方配套镜像"的逐文件/逐字节比对；本报告只能给出官方版本号与 URL，以及所需最少官方文件 | 同上 + `logs/evidence_vitisai_source_git.txt` |
| F3 | 官方 KV260 配套镜像名称确认为 **`xilinx-kv260-dpu-v2022.2-v3.0.0.img.gz`**（Vitis AI 3.0 官方 `board_setup/mpsoc/board_setup_mpsoc.rst:41`；官方注：KV260 板级镜像版本须 ≥ 2022.2） | `logs/evidence_vitisai_source_git.txt:24-25` |
| F4 | 本机 DPU IP 版本为 **DPUCZDX8G v4.1**（changelog：`2022.2 / Version 4.1 / Vitis AI v3.0`），IP 参数 `SYS_IP_VER=0x41`、`GIT_COMMIT_ID=0x07d32c41`、`GIT_COMMIT_TIME=2023022121`；核心 RTL 为 IEEE-1735 加密 | `extract/ip_changelog_and_bdtcl.txt`、`extract/ip_hdl_encryption_check.txt`、`extract/ip_sv_inst_block.txt` |
| F5 | 新 clockfix 离线产物（2026-09-26）：bit `d316ee9c…385c`、XSA `76e8d105…363b`、routed DCP `23d16616…9fbd`、synth DCP `87e79b44…6dc4`、HWH `0fed493c…4c63`、arch.json `ac3853f7…7bdd`（`{"fingerprint":"0x101000056010405"}`）；XSA 内嵌 bit 与 `impl_1` bit 同 SHA，XSA 内嵌 HWH 与生成的 HWH 同 SHA | `kv260_clockfix_rebuild_20260926/reports/SHA256SUMS.txt`、`reports/export_provenance.txt` |
| F6 | 新 post-route 时序已建立 200/100 MHz 关系（`clk_dsp_…` 5.000 ns、`dpu_clk_wiz_clk_dpu` 10.000 ns），WNS 1.462 ns / 3.284 ns，无 setup/hold 违例；DRC 0 error / 0 critical / 342 warning | `reports/postroute_clocks.rpt`、`extract/timing_clk_groups.txt`、`kv260_clockfix_rebuild_20260926/reports/postroute_drc.rpt` |
| F7 | **IP 交付物内部不使用 `dpu_2x_resetn` / `m_axi_dpu_aresetn` 这两个输入**：新、旧两代 IP OOC DCP 中 IP 顶层这两个端口 FANOUT=0；`inst/dpu_2x_resetn`、`inst/m_axi_dpu_aresetn` 都被绑到内部常量网 `<const0>`；`s_axi_aresetn`/两路时钟正常连接 | `reports/ip_ooc_and_new_routed_reset_topology.txt:1-18`（NEW）与 `:44-61`（ORIG） |
| F8 | **旧实现（2026-09-19，即板上曾运行硬件的来源）与新实现行为完全一致**：两代 routed DCP 中 `dpu_0/dpu_2x_resetn`、`m_axi_dpu_aresetn` 均 `IS_CONNECTED=0`，`dpu_2x_clk`/`m_axi_dpu_aclk`/`s_axi_aresetn` 均 `IS_CONNECTED=1` | `reports/orig_routed_reset_query.txt:4-11`；`kv260_clockfix_rebuild_20260926/reports/final_routed_reset_gate.txt` |
| F9 | BD 生成 HDL 与 top 综合网表中连接是存在的（`kv260_dpu_bd.v:689/691`；synth DCP 中 `dpu_0/dpu_2x_resetn` IS_CONNECTED=1），但同一次综合的 IP 实例内部已是 `<const0>`；实现 `opt_design` 的常量传播/Sweep 阶段随后移除无负载逻辑（1575 + 1246 cells），routed DCP 中 `rst_dpu_dsp` cell/net 不再存在 | `kv260_dpu.gen/.../synth/kv260_dpu_bd.v:689,691,819-832`；`reports/synth_dpu_reset_connectivity.txt`；`logs/impl_opt_keywords.txt:124,132,139` |
| F10 | 新 bit/XSA **尚未进入启动链**：`petalinux images/linux/system.bit` 仍是旧 bit `6a75e223…4aba5`（= 旧 routed checkpoint 写出物），`BOOT.BIN` = `335fd6ec…044d` | `reports/SHA256SUMS_local_artifacts.txt` |
| F11 | 板端（既有日志）存在**明确的版本混搭**：QSPI 固件为 2023.2（FSBL/PMUFW 2023.2、BL31 v2.8 2023.2、U-Boot 2023.01），SD 上的 `image.ub`（122,901,532 字节）对应内核 **5.15.36-xilinx-v2022.2**；默认流程停在 `ZynqMP>` 提示符（`Loading Environment from nowhere`）；另一次带 `initcall_blacklist=xlnx_dpu_drv_init` 的启动成功但**屏蔽了 DPU 驱动** | `extract/boot_serial_key_lines.txt:2-20,31,49-58`；`/home/ghmd/work/kv260-boot-audit-live/report.txt` |
| F12 | rootfs 中 `vart` / `xir` / `vitis-ai-library` / `unilog` 标称版本均为 **3.0**；工程 `petalinuxbsp.conf` 亦为 `PREFERRED_VERSION_* = "3.0"` | `logs/evidence_boot_artifacts.txt:1-4`、`logs/evidence_official_source_3.txt` |
| F13 | 新 `/home/ghmd/work/models/resnet50-b2304/compiled/resnet50_b2304.xmodel` 的 SHA256 为 `acf77c7f…4def7c`，与提示词中"旧硬件最终模型"的 SHA256 相同；固定猫图/输入未变 | `reports/model_and_input_hashes.txt` |

### 0.2 优先级最高的那项差异（DPU reset）——本轮已可解释

提示词要求优先核实"routed DCP 中 DPU reset pin `IS_CONNECTED=0` 而 HWH 仍称已连接"。本轮结论：

1. **不是本次重建引入的回归**：新（9/26）与旧（9/19）两代 IP OOC DCP、两代 top routed DCP 在这一点上**逐项一致**（F7、F8）。
2. **不是"实现阶段丢失连接"**：在 IP 单独综合（OOC）阶段，IP 顶层 `dpu_2x_resetn` 端口就已是 FANOUT=0，其内部实例输入被绑到 `<const0>`。即"IP 内部没有使用这两个输入"是**原因**，"顶层 reset 网无负载 → 被 opt_design 清理"是**结果**。
3. **HWH 与 DCP 的差异属抽象层差异**：HWH/BD 描述逻辑连接意图（BD 中确实连到 reset controller），routed DCP 描述优化后的实现网表。因此不能把 HWH 连线当作 routed connectivity（该谨慎点成立），但也不能据此判定"实现断线事故"。
4. 两代实现的悬空输入集合都是"IP 在当前配置下未使用的端口"（未启用的 DPU1/2/3 核 AXI、未使用的 AXI 可选/响应 ID 信号、`dpu0_m_axi_data2/3_*`、两路未使用的 reset），而不是功能主通道被切断：`dpu_0` 边界 606 个输入中 196 个悬空，`inst` 层 3021 个输入中 2611 个悬空（`logs/new_routed_dangling_summary.txt:86-88`）。

### 0.3 不能证明的部分（必须保留为未确认）

- **U1（关键）**：IP 加密核内部为何**不使用**这两路 reset（其内部 2× 域/AXI 域复位究竟由谁驱动）。公开可见只有 IP 顶层 wrapper（`.sv` 中 `.dpu_2x_resetn(dpu_2x_resetn)`、`.m_axi_dpu_aresetn(m_axi_dpu_aresetn)`）；核心 `DPUCZDX8G_v4_1_0_vl_top.sv` / `arch_para.vh` 为 IEEE-1735 密文。**未确认**，需 AMD 官方 IP 文档/官方参考设计或 IP 变更说明对照。
- **U2**：这两路输入在实际 bitstream 中的 tie 值与被裁剪后的等效连接。**未确认**（未从 bit 逆向、未回读）。
- **U3**：板上**实际加载**的 bit/镜像身份。既有日志只记录"所选文件路径"，没有编程前哈希、没有 FPGA 配置回读；本轮串口被动采样 0 字节。**未确认**。
- **U4**：板上识别错误与重复输出波动的根因。现有证据只支持"排除若干候选"，不支持指认单一根因。
- **U5**：342 条 post-route DRC warning（REQP-1731×288、AVAL-318×48、PDCN-1569×3、DPOP-3/4、RTSTAT-10）均未 waiver，语义正确性**未验证**。
- **U6**：`build_logs/rebuild_impl_retry.log` 中 `WARNING::74 Unsupported FPGA device name 'xck26-sfvc784-2LV-c'` 的触发来源**未确认**（bitgen 仍成功）。

### 0.4 对当前 bit/XSA 可上板性的判定

- 本轮**未发现**新的硬件实现缺陷；reset 差异已定位为 IP 固有 + 工具优化结果，且新旧一致，**不再构成阻止上板的独有理由**。
- 但 U1/U2/U3/U5 仍属未确认，且本轮未做任何板端功能验收，因此正式判定为：**不可确认可上板（保守结论：不可上板）**。要转为"可上板"，需先完成第 8 节最少只读补证，并另起目录做一次受控上板验收（本轮未做）。
- 另需注意 F10：即便判定通过，新 bit 也尚未进入 PetaLinux 启动链（当前 `system.bit`/`BOOT.BIN` 仍是旧的 100 MHz 产物）。

---

## 1. 审计过程、命令与只读性

完整命令清单与退出状态见 `COMMANDS.txt`，Vivado 原始日志见 `logs/`，证据摘录见 `extract/`。

| # | 命令（要点） | 只读性 | 结果 |
|---|---|---|---|
| 1 | `ls` / `find` / `grep` / `head` / `tail` / `sed` / `diff` / `wc` / `sha256sum` 于本机工程、镜像、模型、日志目录 | 只读 | 全部成功 |
| 2 | `sha256sum` 启动链组件、SD 暂存、SD 备份、模型、输入 | 只读 | `reports/SHA256SUMS_local_artifacts.txt`、`reports/model_and_input_hashes.txt` |
| 3 | `vivado -mode batch -source query_orig_routed_dcp.tcl`（open_checkpoint 旧 routed DCP） | 只读（仅查询对象属性） | 退出 22:00:36，`reports/orig_routed_reset_query.txt` |
| 4 | `vivado -mode batch -source query_ip_ooc_and_new_routed.tcl`（新/旧 IP OOC DCP + 新 routed DCP） | 只读 | 退出 22:03:47，`reports/ip_ooc_and_new_routed_reset_topology.txt` |
| 5 | `vivado -mode batch -source query_opt_and_orig_dangling.tcl`（opt.dcp 阶段定位 + 旧 routed 悬空对照） | 只读 | `reports/opt_stage_and_orig_dangling.txt` |
| 6 | `timeout 5 cat /dev/ttyUSB0`、`/dev/ttyUSB1` | 被动只读（**未写入任何字节**） | 0 字节，`extract/serial_passive_*.raw` |
| 7 | 官方资料查询：Vitis AI 3.0 文档 / 官方 GitHub tag `v3.0` / Ubuntu for AMD-Xilinx / cdimage 目录 | 仅网页读取，未下载二进制 | 版本号与 URL 见第 3 节 |

**未执行**（按提示词边界）：任何写操作；未向原工程目录写 `write_*`/`report_*`；未 `stty`/串口写；未 `xsdb`/JTAG 动作；未 `xmutil`/`fpgautil`；未加载模块、未访问寄存器；未重编译模型、未重打包镜像。

---

## 2. A 节：本机现存文件与来源清单

容器内成员哈希与"来源链"判定均在表后说明。所有路径为绝对路径；下面 SHA256 均为本机 `sha256sum` 实测值（完整值见 `reports/*.txt`）。

### 2.1 启动链与 PetaLinux 产物（`/home/ghmd/work/petalinux-kv260-dpu/`）

| 文件 | 大小(byte) | SHA256(前缀) | 内部版本/身份 | 来源判定 |
|---|---:|---|---|---|
| `images/linux/BOOT.BIN` | 9,526,664 | `335fd6ec019ccbbc…` | 由 `images/linux/bootgen.bif` 指定组成 | 已确认=本工程 bootgen 产物（BIF 内引用 FSBL/PMUFW/`system.bit`/BL31/system.dtb/U-Boot） |
| `images/linux/image.ub` | 130,879,552 | `3a452b9d3790f097…` | FIT：kernel+DTB+rootfs(ramdisk) | 已确认=本工程 9/24 重新生成的 FIT；**与板上曾加载的 122,901,532 字节版本不同** |
| `images/linux/system.bit` | 7,797,816 | `6a75e223ba4f901b…` | 旧 100 MHz routed checkpoint 写出物 | 已确认=旧实现 bit（SHA 与 `kv260_hw_timing_audit_20260926/ARTIFACT_SHA256SUMS` 一致） |
| `images/linux/system.dtb` | 45,086 | `f8f7b8749f943f28…` | 由 `system.xsa` HWH 生成 | 已确认 |
| `images/linux/boot.scr` | 2,777 | `9ada4d88212468c1…` | U-Boot script | 已确认 |
| `images/linux/zynqmp_fsbl.elf` | 356,448 | `bfd58941bc3bcb40…` | 2022.2 工程构建 | 已确认（与板上 QSPI 的 2023.2 FSBL 不同，见第 6 节） |
| `images/linux/pmufw.elf` | 506,364 | `50076f2a9e070260…` | 2022.2 | 已确认 |
| `images/linux/bl31.elf` | 152,504 | `43fced005e38795a…` | ATF 2022.2 | 已确认 |
| `images/linux/u-boot.elf` | 9,421,424 | `0a2e076983944633…` | U-Boot（2022.2 构建） | 已确认 |
| `images/linux/Image` | 21,930,496 | `3296e0f0470e3e2f…` | 5.15.36-xilinx-v2022.2 | 已确认（日志行 129/`extract/boot_serial_key_lines.txt:73`） |
| `images/linux/rootfs.manifest` | 28,633 | `49a8124d77782098…` | 547 行，含 `vart/xir/vitis-ai-library/unilog 3.0` | 已确认 |
| `images/linux/bootgen.bif` | 605 | `2915a5b49f8412f9…` | 6 个条目（含 `[destination_device=pl] system.bit`） | 已确认 |
| `images/linux/rootfs.ext4` / `rootfs.cpio` / `vmlinux` | 476,282,880 / 332,469,248 / 313,747,696 | 未计算 | rootfs 与内核镜像 | 未确认（本轮未哈希大文件以控制只读开销） |
| `sd-card-staging-dpu-clock-fixed/{BOOT.BIN,boot.scr,image.ub,system.dtb,uEnv.txt}` | — | `335fd6ec…` / `9ada4d88…` / `9634ab4cca4b4ccf…` / `f23b895257354f93…` / `724e78d98ef8e63f…` | 9/21 SD 暂存集 | 已确认；其 `image.ub`(122,901,872) **既不等于**工程当前 `image.ub`，**也不等于**启动日志中的 122,901,532 → 三份不同版本 |
| `/home/ghmd/kv260-sd-backup-20260924.9ZTIEc/image.ub.old` | 130,751,948 | `1dd3245ca72d8127…` | 覆盖前旧 image.ub | 已确认存在 |

### 2.2 硬件产物（原工程 / 新重建 / 旧 XSA）

| 文件 | 大小(byte) | SHA256(前缀) | 身份/内部字段 | 来源判定 |
|---|---:|---|---|---|
| `/home/ghmd/work/kv260_dpu_b2304_uram/kv260_dpu.xpr` | — | `1ac27f046f08b47c…` | 原工程 | 已确认未改动（构建前后同哈希） |
| `…/kv260_dpu_bd.bd` | — | `daffe6dd01a409f3…` | 原 BD（clockfix 版） | 已确认未改动 |
| `…/output/kv260_dpu_clockfix.xsa`（= `petalinux…/hw-description/system.xsa`） | — | `08abccc5df51ebce…` | 内含 `kv260_dpu_clockfix.bit`=`6a75e223…`（旧 bit）+ `kv260_dpu_bd.hwh`=`ea48b3a0…` | 已确认：**HWH 与 bit 不同源**（旧审计结论，本轮复核一致） |
| `…/output/kv260_dpu.bit` | — | `8216667789ea0261…` | 另一 bit | 未确认用途（不与启动链 SHA 相同） |
| `…/kv260_dpu.runs/impl_1/kv260_dpu_bd_wrapper_routed.dcp` | 73,480,348 | `c04bc88110b232e7…` | 旧（100 MHz）routed | 已确认（本轮只读打开查询） |
| `/home/ghmd/kv260_clockfix_rebuild_20260926/kv260_dpu.srcs/sources_1/bd/kv260_dpu_bd/kv260_dpu_bd.bd` | — | `e03dcc93f21a8c78…` | 副本 BD（`generate_target` 后默认参数传播） | 已确认（与原 BD 不同哈希，原 BD 未改） |
| `…/kv260_clockfix_rebuild_20260926/kv260_dpu.runs/synth_1/kv260_dpu_bd_wrapper.dcp` | — | `87e79b44cec2d000…` | 新 synth（2022.2 全新建） | 已确认 |
| `…/kv260_clockfix_rebuild_20260926/kv260_dpu.runs/impl_1/kv260_dpu_bd_wrapper_opt.dcp` | 42,787,552 | 未计算 | 新 opt_design 阶段 | 已确认存在（本轮只读查询） |
| `…/impl_1/kv260_dpu_bd_wrapper_physopt.dcp` / `_placed.dcp` | 63,914,548 / 63,910,547 | 未计算 | physopt / placed | 已确认存在 |
| `…/impl_1/kv260_dpu_bd_wrapper_routed.dcp` | 73,503,245 | `23d166161b9efc33…` | 新 routed | 已确认 |
| `…/impl_1/kv260_dpu_bd_wrapper.bit` = `artifacts/kv260_dpu_clockfix_rebuilt.bit` | 7,797,816 | `d316ee9c33bae954…` | 新 clockfix bit | 已确认同源（同一次 impl_1） |
| `…/artifacts/kv260_dpu_clockfix_rebuilt.xsa` | 4,470,034 | `76e8d1056949999e…` | 内嵌 bit=`d316ee9c…`、HWH=`0fed493c…` | 已确认：**XSA 内嵌 bit/HWH 与 impl_1、生成的 HWH 完全同源**（与 2.2 上表的旧 XSA 形成对照） |
| `…/kv260_dpu.gen/…/hw_handoff/kv260_dpu_bd.hwh` | — | `0fed493cc519aa38…` | BD 逻辑视图 | 已确认 |
| `…/kv260_dpu.gen/…/ip/kv260_dpu_bd_dpu_0_0/arch.json`（新/旧同哈希） | 36 | `ac3853f7a1c3d8a1…` | `{"fingerprint":"0x101000056010405"}` | 已确认（B2304 arch） |
| `…/ip_repo/DPUCZDX8G_ip_repo_VAI_v3.0/…`（19 文件） | — | 源/副本清单同哈希 | DPUCZDX8G v4.1；changelog=`2022.2 / v4.1 / Vitis AI v3.0` | 已确认与本机 `/home/ghmd/work/dpu/DPUCZDX8G_ip_repo_VAI_v3.0` 一致；**官方发布物比对未确认**（见第 3 节） |

### 2.3 模型与输入（未修改）

| 文件 | 大小(byte) | SHA256 |
|---|---:|---|
| `/home/ghmd/work/models/resnet50-b2304/compiled/resnet50_b2304.xmodel` | 26,843,134 | `acf77c7fdb91ed87…4def7c` |
| `…/compiled/meta.json` | 203 | `eaf69a834b9ee854…c98a5` |
| `/home/ghmd/kv260_float_check_offline_run/kv260_float_check/cat2.jpg` | 1,323,314 | `03259f0b2dbd34ca…da182` |
| `…/kv260_float_check/input.bin` | 150,528 | `46c4aacdc41072ec…61c00` |

### 2.4 来源链结论

- **可证实的来源链（新重建）**：副本 XPR → `generate_target all`（IP repo 本地化）→ `synth_1` → `impl_1`（opt→place→route→bitgen）→ `impl_1/*.bit` == `artifacts/*.bit` == XSA 内嵌 bit；BD HWH == XSA 内嵌 HWH。链条完整、无断裂。
- **可证实的来源链（旧 clockfix 交付物）**：`output/kv260_dpu_clockfix.xsa` 内嵌 bit = 旧 routed checkpoint 写出物 = `images/linux/system.bit`；但其内嵌 HWH 描述的是含 `dpu_clk_wiz` 的 BD。→ 该 XSA/镜像链在 **bit 与 HWH 之间断裂**（旧审计结论，本轮以 SHA 复核确认）。
- **断裂/未确认**：① 板上启动日志中的 `image.ub`(122,901,532) 在本机已无同尺寸文件可对应（现存为 130,879,552 / 122,901,872 / 130,751,948）→ 那次启动的 rootfs/内核版本无法用现有文件复现；② 本机 Vitis-AI 3.0 源码副本无 `.git`，其 tag/commit **未确认**；③ IP repo 与官方发布包的逐文件哈希比对 **未做**（未下载官方包）。

---

## 3. B 节：版本正确的 AMD 官方配套镜像

### 3.1 本机查找结果（只读）

| 查找位置 | 结果 |
|---|---|
| `/home/ghmd` 全盘（深度 ≤4）查找 `*.img` / `*.img.xz` / `*.wic*` / `*ubuntu*kv260*` / `*vitis-ai*3.0*` | **未找到任何官方板级镜像**；仅命中 `Vitis-AI-3.0.zip`（源码包）、`work/vitis-ai-source/Vitis-AI-3.0`（解包源码）、`work/Vitis-AI-v3.0.zip`（**0 字节**） |
| `/home/ghmd/Downloads/AMD_KV260_2022.2/` | 只有 `01_unified_installer/`（Vivado/Vitis 安装器），非板级镜像 |
| `/home/ghmd/kv260-sd-backup-20260924.9ZTIEc/` | 只有 `image.ub.old`、`system.dtb.old`（本工程产物备份） |
| `work/vitis-ai-source/Vitis-AI-3.0` | 官方源码副本，但**不是 git 仓库**（无 `.git`），文件日期 2023-01-13；tag/commit 无法验证 |

**结论**：本机**没有可验证的 AMD 官方 KV260 配套镜像**，因此第 4 节的"官方配套产物"列只能填"未获取（无本机可比对物）"。按提示词要求，本报告不下载镜像，只列出所需最少官方文件与官方 URL。

### 3.2 官方版本与 URL（仅列版本与链接，未下载）

| 项目 | 官方版本/名称 | 官方来源 |
|---|---|---|
| Vitis AI 版本 | **3.0**（文档 Last updated 2023-07-19） | https://xilinx.github.io/Vitis-AI/3.0/html/docs/quickstart/mpsoc.html |
| Vitis AI 3.0 支持目标 | ZCU102 / ZCU104 / **Kria KV260** | 同上（"Applicable Targets"） |
| KV260 官方配套板级镜像 | **`xilinx-kv260-dpu-v2022.2-v3.0.0.img.gz`** | Vitis AI 3.0 源码 `board_setup/mpsoc/board_setup_mpsoc.rst:41`（本机副本）；官方下载入口 `https://www.xilinx.com/member/forms/download/design-license-xef.html?filename=xilinx-kv260-dpu-v2022.2-v3.0.0.img.gz` |
| 官方镜像版本约束 | "For ZCU102/ZCU104/KV260, the version of the board image should be **2022.2 or above**" | `board_setup_mpsoc.rst:43`（本机副本） |
| 官方配套模型包 | `resnet50-zcu102_zcu104_kv260-r3.0.0.tar.gz` | `board_setup_mpsoc.rst:99`（本机副本） |
| DPU IP 版本 | **DPUCZDX8G v4.1**（`2022.2: Version 4.1 / Vitis AI v3.0`） | `ip_repo/…/doc/DPUCZDX8G_v4_1_0_changelog.txt`（本机） |
| 官方 GitHub tag | **`v3.0`**（含 `board_setup`、`dpu`、`docker`、`docs`、`docker_run.sh`） | https://github.com/Xilinx/Vitis-AI/tree/v3.0 |
| Kria 官方文档门户 | 存在（重定向到 home page） | https://xilinx.github.io/kria-apps-docs/ |
| Kria K26/KV260 的 Ubuntu 官方镜像 | 官方页面提供 Kria SOM 的 Ubuntu（22.04/24.04 LTS 等）；**本轮未取到 K26 的确切镜像文件名与校验值** | https://ubuntu.com/download/amd-xilinx |
| Ubuntu 22.04 官方 cdimage 目录 | 仅见 `inteliot/`、`nvidia-tegra/` 等，**未见 Kria/K26 镜像** | https://cdimage.ubuntu.com/releases/22.04/release/ |

### 3.3 兼容性判断（版本号层面 vs 文件层面）

- **版本号层面（已确认匹配）**：本机 DPU IP `v4.1` + `B2304` + fingerprint `0x101000056010405` + Vitis AI runtime 3.0（`vart/xir/vitis-ai-library/unilog = 3.0`）+ Vivado 2022.2，与 Vitis AI 3.0 官方发布线（2022.2 / IP v4.1 / Vitis AI v3.0）**一致**。
- **文件层面（未确认）**：因本机无官方镜像/官方 IP 包，未做逐文件哈希、未做官方 HWH/bit 与 本机 HWH/bit 的结构比对。**不得**用"版本号相同"替代官方文件比对（提示词第 9 条要求）。
- **必要的区分**：本机 `Vitis-AI-3.0.zip`/`vitis-ai-source` 是**开发侧源码**；`Downloads/input-leap-*` 等是无关第三方；未见任何"板端 rootfs 镜像"。因此本报告不会把开发容器/源码包当作 KV260 板端系统镜像。

### 3.4 完成"官方配套镜像比对"所需的最少官方文件

1. `xilinx-kv260-dpu-v2022.2-v3.0.0.img.gz`（或官方发布的镜像副本）+ 官方 `SHA256SUMS`/发布说明中的校验值。
2. 该官方镜像内的：`BOOT.BIN`、`image.ub`/`Image`、`system.dtb`、`system.bit`、`rootfs` 清单（用于与本机第 2 节逐项对照）。
3. AMD 官方 DPU 参考设计的 `XSA`（含 `HWH` 与 `bit`），用于与本机 HWH/bit 做结构与 `SYS_IP_VER`/fingerprint/时钟复位连接对照。
4. Vitis AI 3.0 官方 `vart`/`xir`/`dpu_task` 的 ELF `build-id`/`SONAME`/源码 commit 清单，用于 ABI 级比对。
5. 官方 DPUCZDX8G v4.1 的 IP 用户指南（UG）中关于 `dpu_2x_resetn`/`m_axi_dpu_aresetn` 连接要求的条目（用于回答 U1）。

补充：本机存在官方**开发侧容器** `xilinx/vitis-ai-pytorch-cpu:ubuntu2004-3.0.0.106`（`docker images` 只读输出，9.88 GB，约 3 年前创建）。它属于主机开发环境（模型量化/编译），**不是** KV260 板端系统镜像；本轮未启动容器、未读取其内部文件（避免任何状态变更）。

---

## 4. C 节：当前系统与官方配套镜像逐项对比

> 说明：由于本机无官方配套镜像（第 3.1 节），"官方配套产物"列均为"未获取"。本节的判定主要以"**本机内部一致性**"与"**板端既有只读证据**"为对象，并明确区分"已确认/推测/未确认"。

### 4.1 对比总表

| 项 | 本机当前产物 | 官方配套产物 | 板端实际加载值 | 证据 | 判定 |
|---|---|---|---|---|---|
| 1. Boot chain（FSBL/PMUFW/ATF/U-Boot/BIF） | FSBL `bfd58941…`、PMUFW `50076f2a…`、BL31 `43fced00…`、U-Boot `0a2e0769…`、BIF `2915a5b4…`（均 2022.2 工程构建）；BOOT.BIN `335fd6ec…` | `xilinx-kv260-dpu-v2022.2-v3.0.0.img.gz`（未获取） | QSPI：**2023.2**（FSBL/PMUFW 2023.2、BL31 v2.8 2023.2、U-Boot 2023.01）；未使用 SD/BIF 启动链；`Loading Environment from nowhere`，默认停在 `ZynqMP>` | `reports/SHA256SUMS_local_artifacts.txt`；`extract/boot_serial_key_lines.txt:2-20,31,49-50` | **已确认不匹配**：板上运行的是 QSPI 2023.2 官方固件 + SD `image.ub`（2022.2 内核）的混搭链，与本机 2022.2 BOOT.BIN 链不是同一交付路径 |
| 2. FPGA/DPU（bit/XSA/HWH/IP/fingerprint） | 新：bit `d316ee9c…`、XSA `76e8d105…`（内嵌 bit/HWH 同源）、HWH `0fed493c…`；旧：`system.bit` `6a75e223…`、XSA `08abccc5…`（内嵌 bit 旧 + HWH `ea48b3a0…` 新）；IP `v4.1`/`B2304`/`0x101000056010405` | 未获取 | 日志只记录 `fpga`/启动路径为 `images/linux/system.bit`（=旧 bit `6a75e223…`）；无编程前哈希、无配置回读 | 第 2.2 节；`kv260_hw_timing_audit_20260926/REPORT.md:28-30` | 本机"新产物内部同源"=**已确认**；"旧 XSA 的 bit 与 HWH 不同源"=**已确认**；"板上实际配置内容"=**未确认** |
| 3. PetaLinux/Linux（kernel/DTB/bootargs/模块） | `Image` `3296e0f0…`（5.15.36-xilinx-v2022.2）、`system.dtb` `f8f7b874…`、`image.ub` `3a452b9d…` | 未获取 | 内核 `5.15.36-xilinx-v2022.2`（与工程同型号）；rootfs 从 ramdisk 启动（`root=/dev/ram0`）；bootargs 由手工 `setenv`（含 `clk_ignore_unused`、`initcall_blacklist=xlnx_dpu_drv_init`）；模块 vermagic 未取证 | `extract/boot_serial_key_lines.txt:55-58,73` | 内核型号一致=**已确认**；"板上那次启动所用 image.ub"=**未确认**（现存三份候选均不匹配 122,901,532 字节） |
| 4. Vitis AI runtime（VART/XIR/dpu_task） | rootfs manifest：`vart/xir/vitis-ai-library/unilog = 3.0`；工程 `PREFERRED_VERSION_*=3.0`；主机容器 `vitis-ai-pytorch-cpu:ubuntu2004-3.0.0.106` | 未获取（无官方 runtime 清单） | 提示词既有信息：板端 `libvart-runner`/`libxir` 构建日期 2026-09-20、`dpu_task` 2023-01-13，均标称 3.0；本轮未做 ELF `build-id`/`SONAME`/commit 比对 | `logs/evidence_boot_artifacts.txt:1-4`、`logs/evidence_docker_and_zips.txt` | 标称版本一致=**已确认**；ABI/源码级一致性=**未确认**（提示词要求"找具体 ABI/源码/补丁差异"这一点本轮**未能完成**，因为缺少板端只读 ELF 取证） |
| 5. DMA/内存（地址宽度/CMA/IOMMU/coherency） | DPU AXI 地址 40 位（`araddr[39:0]`/`awaddr[39:0]`）；XSA 未含 SMMU 相关证据 | 未获取 | 内核日志：`cma: Reserved 256 MiB at 0x62000000`；DMA32/Normal 分区；soft IO TLB 64 MB；未见 IOMMU fault | `extract/ip_sv_inst_block.txt`（地址宽度）、`extract/boot_serial_key_lines.txt:79-101` | CMA 256 MiB=**已确认**；SMMU/coherency/DMA mask 配置=**未确认**（未取证设备树与内核 config） |
| 6. DPU 时钟/复位 | 新实现：`clk_dsp` 5.000 ns（200 MHz，PLL CLKOUT0 ×2）、`dpu_clk_wiz_clk_dpu` 10.000 ns（÷2），WNS 1.462/3.284 ns；旧实现：两路都落在 `clk_pl_0`(100 MHz) | 未获取 | 板端 `clk_summary` 报告 199,998,002 / 99,999,001 Hz，但与 DTB 静态 `fixed-clock` 声明相同 → 非硬件测量 | `reports/postroute_clocks.rpt`；`kv260_hw_timing_audit_20260926/REPORT.md:52`；`routed_checkpoint_topology_summary.txt` | 新 bit 的时钟关系=**已确认**；板上实际频率/PLL lock=**未确认**；复位见第 5 节 |
| 7. 设备树与镜像（频率/clock-names/resets/ranges/reg/中断） | `system.dtb` 由 `hw-description/system.xsa`(`08abccc5…`，HWH=`ea48b3a0…`，含 clock wizard 的 BD) 生成 | 未获取 | 板端 `pl.dtsi` 的两个 `fixed-clock` 频率值与 `clk_summary` 一致 | `kv260_hw_timing_audit_20260926/REPORT.md:52` | **已确认**：DTB 基于"新 HWH"生成，而同一交付链中的 bit 是旧实现 → **DTB↔bit 不同源**（镜像内部不一致） |
| 8. 应用/模型（xmodel/输入/labels/preprocess） | `resnet50_b2304.xmodel` `acf77c7f…`、`meta.json` `eaf69a83…`、`cat2.jpg` `03259f0b…`、`input.bin` `46c4aacd…` | 官方 `resnet50-zcu102_zcu104_kv260-r3.0.0.tar.gz`（未获取） | 提示词既有信息：板端运行新模型 SHA `330a654a…`（与本机 `acf77c7f…` **不同**）；权重/指令/输入回读一致 | `reports/model_and_input_hashes.txt` | 本机文件哈希=**已确认**；板上所用模型身份=**未确认**（无板端只读取回） |

---

## 5. D 节（优先项）：DPU reset 网表差异的完整定性与阶段定位

### 5.1 分阶段证据链

| # | 阶段 | 证据文件（行号/对象） | 观测 | 判定 |
|---|---|---|---|---|
| 1 | IP 明文 wrapper RTL | `kv260_dpu.gen/…/ip/kv260_dpu_bd_dpu_0_0/synth/kv260_dpu_bd_dpu_0_0.sv:703,705` | `.dpu_2x_resetn(dpu_2x_resetn)`、`.m_axi_dpu_aresetn(m_axi_dpu_aresetn)`（同一实例的 `dpu1/2/3_2x_clk` 为 `1'B0`，属未启用核） | IP 顶层封装**意图上**传递这两路 reset |
| 2 | IP 核心 RTL | `hdl/DPUCZDX8G_v4_1_0_vl_top.sv`、`inc/arch_para.vh` | IEEE-1735 密文（`grep -c dpu_2x_resetn` = 0） | **无法读**（U1 的来源） |
| 3 | BD 生成 HDL | `kv260_dpu.gen/…/synth/kv260_dpu_bd.v:689,691,819-832` | `dpu_0.dpu_2x_resetn←rst_dpu_dsp_peripheral_aresetn`；`m_axi_dpu_aresetn←rst_dpu_clk_peripheral_aresetn`；两个 `proc_sys_reset` 实例存在 | BD 层连接**存在且正确** |
| 4 | BD HWH | `…/hw_handoff/kv260_dpu_bd.hwh`（`0fed493c…`） | 仍描述两路 reset 连到 DPU（重建报告 2631-2643 / 4328-4353 / 5250-5261 行） | HWH 反映 BD 逻辑视图 |
| 5 | **IP OOC DCP（新 9/26）** | `reports/ip_ooc_and_new_routed_reset_topology.txt:1-18` | IP 顶层 `dpu_2x_resetn`：`NETS=`(空) `FANOUT=0`；`m_axi_dpu_aresetn` 同；`inst/dpu_2x_resetn` 与 `inst/m_axi_dpu_aresetn` → `NETS=<const0>`；`s_axi_aresetn`、两路时钟正常；`RESET_PIN_TOTAL=44 CONNECTED=44 CONST_TIED=2` | **根因**：IP 内部不使用这两路输入 |
| 6 | **IP OOC DCP（旧 9/19）** | 同上 `:44-61` | 与 #5 **逐字段相同** | 非本次重建引入 |
| 7 | IP OOC 综合日志（新/旧） | `…/kv260_dpu_bd_dpu_0_0_synth_1/runme.log`；`logs/evidence_ip_synth_reset_port.txt` | `grep dpu_2x_resetn/m_axi_dpu_aresetn` = **0 行**；`8-7129` 共 103/104 条，全部与本 DPU reset 无关（`regs4.prof_value`） | 无"漏连/未驱动"告警 → 属"顶层输入未被内部使用"的正常处理 |
| 8 | top 综合（BD 包装层） | 综合日志 `:51-57` 与 `:69-79` | `Synth 8-7071` 列出 `dpu_0` 的悬空端口**不含**这两路 reset（只含 `s_axi_bid/rid`、`*_awuser`、`*_wid` 等） | 外部连接**确实进入**了综合 |
| 9 | top synth DCP | `reports/synth_dpu_reset_connectivity.txt`；`reports/reset_interface_comparison.txt:9-14` | `dpu_0/dpu_2x_resetn` `IS_CONNECTED=1`（net=`rst_dpu_dsp_peripheral_aresetn`）但 `inst/dpu_2x_resetn` 已是 `<const0>`；`rst_dpu_dsp` cell/reset net 存在 | 综合阶段"外连→内部常量"已同时成立 |
| 10 | **impl opt_design** | `kv260_dpu.runs/impl_1/runme.log:124,132,139,154,219` | Constant propagation 移除 1575 cells；Sweep 移除 1246 cells；`Opt 31-32 Removing redundant IBUF…`；`opt_design completed successfully` | **无负载 reset 树在此被清理** |
| 11 | routed DCP | `reports/final_routed_reset_gate.txt`、`reports/ip_ooc_and_new_routed_reset_topology.txt:87-*` | 两路 reset `IS_CONNECTED=0`、`NETS=`；`RST_DPU_DSP_CELL_COUNT=0`；`rst_dpu_clk_peripheral_aresetn` fanout=2（仅 reset controller 输出 + `axi_mem_intercon_2/S00_ARESETN`） | 已完成清理的实现态 |
| 12 | bit / XSA | `reports/export_provenance.txt`、`kv260_clockfix_rebuild_20260926/reports/SHA256SUMS.txt` | bit=`d316ee9c…`、XSA 内嵌 bit 同 SHA、HWH 同 SHA | 产物来源一致 |
| 13 | 旧实现对照（routed + sim_netlist） | `reports/orig_routed_reset_query.txt:4-11`；`extract/old_sim_netlist_context.txt` | 旧 routed：两路 reset `IS_CONNECTED=0`（时钟与 `s_axi_aresetn` = 1）；旧 IP sim_netlist 第 2242/2244 行同样 `1'b0` | **新旧一致**（F8） |

### 5.2 阶段定位结论

"`IS_CONNECTED` 由 1 变 0"的精确定位是**两段**，而不是单一实现步骤：

1. **根因发生在 IP OOC 综合阶段**：IP 顶层封装把这两路 reset 传给内部实例，但 IP 加密核不使用它们，于是 IP OOC 网表中该输入成为"无内部负载"，被绑到 `<const0>`，IP 顶层端口 `FANOUT=0`。
2. **表现（pin 变为无连接）发生在 top-level `opt_design`**：由于该 reset 网在 IP 侧没有真实负载，`opt_design` 的常量传播与 Sweep 清除了整条网及其驱动 `proc_sys_reset` 实例；`place`/`route` 只是沿用该结果（`opt.dcp` 实测见 `reports/opt_stage_and_orig_dangling.txt`）。

因此，把它描述为"新实现丢掉了 reset 连接"或"某一步实现操作弄断了 reset"都**不成立**；它是"IP 该输入未使用 → 无负载网被优化"的必然结果，且**旧实现完全相同**。

**opt.dcp 实测（本轮新增，`reports/opt_stage_and_orig_dangling.txt`）**：

| 检查点 | 观测 | 含义 |
|---|---|---|
| 新 `impl_1/*_opt.dcp` | `dpu_2x_resetn` `IS_CONNECTED=0` `NETS=`；`m_axi_dpu_aresetn` 同；`dpu_2x_clk`/`m_axi_dpu_aclk` =1；`OPT_RST_DPU_DSP_CELL_COUNT=0`、`OPT_RST_DPU_DSP_NET_COUNT=0` | **在 `opt_design` 完成后 reset 树已被移除** → 与 synth DCP 的 `IS_CONNECTED=1` 形成边界，阶段精确锁定为 `opt_design` |
| 旧 routed DCP 顶层悬空输入 | `ORIG_DPU_BOUNDARY_DANGLING_INPUT_COUNT=196` | 与新实现同口径 |
| 集合级比对（`logs/dangling_set_compare2.txt`） | 新（196）与旧（196）**`IDENTICAL_SET`：逐名完全相同**，且集合中包含 `dpu_2x_resetn`、`m_axi_dpu_aresetn` | 两路 reset 属于"该 IP 未使用端口集合"的同一类，**不是**单独被破坏的功能通道 |

> 注：`inst/` 层还有 1713 个悬空输入（新实现统计 `new_dangling_names.txt` 1909 行 - 顶层 196 行），这些是 IP 内部未启用子模块（DPU1/2/3 核、未使用 AXI 通道等）的端口；顶层与 `inst` 层的口径差异在 `logs/dangling_set_compare.txt` 中已标注，避免把"口径不同"误读为"新旧差异"。

### 5.3 这段差异对功能与上板判定的影响（严格边界）

- **可以确定的**：这不是本次重建引入的回归；不是 HWH/bit 打包错配（新 XSA 内 bit 与 HWH 各自同源）；`s_axi_aresetn` 与两路时钟在 routed DCP 中连接正常（`s_axi_aresetn` 由 `rst_ps8_0_99M_peripheral_aresetn` 驱动）。
- **不能确定的**：这些输入在器件中的最终电平与功能语义（U2）；IP 内部 2×/AXI 域复位的真实来源（U1）。**禁止**把 HWH 连线等同于 routed connectivity，也**禁止**把 `IS_CONNECTED=0` 等同于"器件内未复位/被永久复位"。
- **对提示词结论的修正建议**：原重建报告把该差异列为"阻断验收"的独立理由并据此判定不可上板。本轮证据显示该差异应降级为"**已解释的既有现象**"；不可上板的判定应主要依赖 U1/U2/U3/U5 与缺少板端验收，而不再依赖"reset 断连"本身。

---

## 6. E 节：板卡只读取证（本轮做了什么）

### 6.1 本轮实际执行（全部只读）

| 动作 | 命令 | 结果 |
|---|---|---|
| 串口设备与占用检查 | `ls -la /dev/ttyUSB*`、`ps -ef \| grep -E 'screen\|minicom\|picocom'` | 设备存在（ttyUSB0-3，19:00 创建）；**未发现**任何 screen/minicom/picocom 占用 |
| 被动串口采样 | `timeout 5 cat /dev/ttyUSB0`、`timeout 5 cat /dev/ttyUSB1` | 各 5 秒，**0 字节**；原始文件 `extract/serial_passive_ttyUSB{0,1}_*.raw`（0 字节）；**未向串口写入任何字节** |
| 主机 Docker 镜像枚举 | `docker images` | 见第 3 节补充 |

**本轮没有从板端取得任何"当前运行时"信息**（串口无输出）。因此关于板卡现状的一切陈述都只能引用既有日志，且必须标注为"既有证据、非本轮实测"。

### 6.2 既有板端只读证据（引用，来源与哈希已知）

| 证据 | 路径 / SHA256 | 关键内容 |
|---|---|---|
| 串口启动原始日志 | `/home/ghmd/work/kv260-boot-audit-live/serial-boot-raw.log` = `153aa69bbba57792298f659e4cfdc7f248f3e78cc74aab22b1e6d9949679d46b`（680 行 / 43,689 字节） | `QSPI 32 bit Boot Mode`；FSBL `Release 2023.2 Mar 18 2024`；PMU FW 2023.2；`BL31 v2.8 … 2023.2_ksb_aug`；`U-Boot 2023.01 (May 10 2024)`；`Detected name: zynqmp-smk-k26-xcl2g-rev2-sck-kv-g-rev2`；`Loading Environment from nowhere... OK`；`Hit any key to stop autoboot` → `ZynqMP>`（**默认未自动引导**）；手工 `mmc dev 1` → `fatload mmc 1:1 0x10000000 image.ub`（122,901,532 B）→ `setenv bootargs`（含 `clk_ignore_unused initcall_blacklist=xlnx_dpu_drv_init`）→ `bootm`；内核 `5.15.36-xilinx-v2022.2`；`cma: Reserved 256 MiB at 0x62000000`；到 `Multi-User System` 并 root 登录；唯一功能失败为 NFS |
| 该次启动的分析报告 | `/home/ghmd/work/kv260-boot-audit-live/report.txt` | 明确声明：该日志**屏蔽了 DPU 驱动**（`initcall_blacklist=xlnx_dpu_drv_init`），因此**不能**回答 DPU probe/推理问题；默认流程停在 U-Boot 提示符 |
| 更早的续采日志 | `/home/ghmd/work/kv260-boot-audit-current/serial-boot.log` = `3f9b37089af1c7b4fe8a634fab763f1bc59dd60231f1f39208c0a5f5fe975131` | 同上系列 |

### 6.3 结论（E 节）

- 已确认（既有证据）：板上启动链是"**QSPI 2023.2 官方固件 + SD 上的 2022.2 内核 FIT**"的混搭；默认 U-Boot 环境为空、不自动引导；DPU 驱动在唯一一次成功进入系统的记录中被显式屏蔽。
- 未确认（U3）：板上**当前**加载的 bit/镜像/内核/模块身份 —— 无 `fpga_manager` 状态、无配置回读、无编程前哈希；本轮串口采样 0 字节。
- **人工审阅项**（本轮未执行，需有人在场并按需受控执行；均为只读或近只读）：`cat /sys/class/fpga_manager/fpga0/state`、`ls -l /dev/dpu`、`dmesg | grep -iE 'dpu|fpga|deferred|iommu|dma'`、`/usr/bin/vart_version`、`sha256sum` 板上 bit/模型/输入、`strings /usr/lib/libvart-runner.so*`（或 `readelf -n`）、`lsmod`/`modinfo xlnx_dpu`（看 `vermagic`）、`cat /proc/cmdline`。任何会触发 FPGA 配置、复位或写寄存器的动作（如 `fpgautil -b`、`xmutil loadapp`）**不得**作为"验证"手段使用。

---

## 7. 根因候选（按现有证据强度排序）

| 排序 | 候选 | 证据强度 | 状态 |
|---|---|---|---|
| 1 | **交付链内部不一致**：板上运行/打包的是旧（无 clock wizard、100 MHz）bit（`6a75e223…`），而同一 XSA 内的 HWH、以及据此生成的 `system.dtb` 描述的是含 clock wizard 的新 BD；`pl.dtsi` 的两个 `fixed-clock`（199,998,002 / 99,999,001 Hz）与真实硬件是否符合未验证 | **强（已确认的哈希级不一致）** | 已确认事实；但其与"识别错误/波动"的因果关系仍属**推测** |
| 2 | 板上实际运行的组合（固件 2023.2 QSPI + SD 2022.2 内核 + 未知 bit）与本机工程/模型假设不一致 | 中（既有日志已确认版本混搭） | 已确认部分；具体影响**未确认** |
| 3 | runtime/驱动 ABI 与源码级不一致（标称 3.0，但 `libvart-runner`/`libxir` 构建时间 2026-09-20 与 `dpu_task` 2023-01-13 不同源、out-of-tree 模块） | 弱（提示词既有信息，本轮**未能**取得板端 ELF 证据） | **未确认** |
| 4 | 模型编译与 DPU 配置（fingerprint `0x101000056010405`）不匹配，或 xmodel 与 IP 不是同一次发布 | 弱（`arch.json` 与 IP 同源已确认；xmodel 元数据未解析） | **未确认**；不可用"运行成功/`VART wait=0`"当反证 |
| 5 | DMA/内存/IOMMU/cache 一致性 | 弱（既有日志**无** IOMMU fault/timeout；未取证 SMMU/DT/内核 config） | **未确认** |
| 6 | DPU reset 输入在 IP 内部未使用（第 5 节） | 强（已确认机制）但与故障相关性**弱** | 机制**已确认**；因果**未确认** |
| 7 | 采样/量化/后处理/标签等应用层问题 | 无本轮证据 | **未确认** |

> 注意：候选 1 是"构建/交付缺陷"，可以解释"为什么板上行为与工程意图不符"，但它**不能**单独解释"同一输入重复输出波动"这类随机性现象；随机性更可能来自运行路径（DMA/内存/并发/时钟），而这些路径本轮均**未取证**。

---

## 8. 继续定位所需的最少只读证据

1. **板端只读一次**（需有人在场；不动 FPGA 配置）：`fpga_manager` 状态、`/dev/dpu`、`dmesg` DPU/IOMMU 行、`vart_version`、`lsmod`+`modinfo`（`vermagic`）、板上 bit/模型/输入 `sha256sum`、`libvart*`/`libxir*` 的 `SONAME` 与 `build-id`。
2. **一次"不带 blacklist 且使用本工程 BOOT.BIN"的启动**串口全量记录（含 `dmesg`），用于确认 DPU probe、时钟、fingerprint 读取路径；需明确这是**有状态操作**，应由用户决定并在受控条件下进行（本轮不做）。
3. **官方文件**（第 3.4 节 5 项），特别是 `xilinx-kv260-dpu-v2022.2-v3.0.0.img.gz` 及其校验值，用于完成第 4 节缺失的"官方配套产物"列。
4. **AMD 官方 DPUCZDX8G v4.1 文档**中 `dpu_2x_resetn`/`m_axi_dpu_aresetn` 的连接语义（回答 U1）。
5. **本机 Vitis AI 3.0 源码的真实 tag/commit**：重新以 `git clone --branch v3.0`（会写入新目录）或核对官方 tarball 校验值；本轮不执行下载。
6. **xmodel 元数据解析**（只读）：确认 xmodel 的 DPU arch/fingerprint 与 `0x101000056010405` 一致（需要 Vitis AI 3.0 容器内的 `xir` 工具，本轮未在容器中执行任何操作）。

---

## 9. 最终结论

1. **reset 差异已解释，且不是本次重建的回归**：新/旧两代 IP OOC DCP、top synth DCP、routed DCP、sim_netlist 在 `dpu_2x_resetn`/`m_axi_dpu_aresetn` 上逐一致；根因是"IP 交付物内部不使用这两路输入"，表现是 `opt_design` 清理无负载网。HWH 与 routed DCP 的差异属抽象层差异，不能证明器件内断线，也不能反证连接有效。
2. **本次重建在离线硬件验收上是"技术成功"**：全新综合/实现/bitgen 成功、200/100 MHz 时钟关系建立、时序无违例、bit 与 XSA 内嵌 bit 同源、HWH 与生成 HWH 同源（优于旧 XSA 的 bit/HWH 错配）。
3. **但当前 bit/XSA 仍不应上板**（保守判定，理由与 reset 无关）：① U1（IP 内部 reset 语义）、U2（器件内 tie 值）未确认；② U3（板上实际加载值、无回读）未确认；③ 342 条 DRC warning 未 waiver；④ 本轮无任何板端功能验收；⑤ 交付链本身存在"bit vs HWH/DTB"的既存错配，未修复前不存在"可信的配套镜像"。
4. **必须强调的操作边界**：本报告没有、也不建议在本轮产出上直接尝试烧写；任何上板动作都应在完成第 8 节补证、并明确"这是有状态操作"后，由用户决策并在受控条件下执行。

---

## 10. 附录

- `COMMANDS.txt`：本轮运行过的命令（含只读性标注）。
- `logs/`：Vivado 原始日志与 shell 采证输出。
- `extract/`：证据摘录文件（含 0 字节串口采样原始文件）。
- `reports/`：结构化查询结果与哈希清单。
- `SHA256SUMS.txt`：本诊断目录全部文件的 SHA256。

---

> **报告结束。** 本报告（`REPORT.md`）及其摘要（`SUMMARY_DEEPSEEK.md`）由 **DeepSeek** 完成，全部结论可依据 `COMMANDS.txt` 中的只读命令重放，并用 `SHA256SUMS.txt` 校验证据文件。

