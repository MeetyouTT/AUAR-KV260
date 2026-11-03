# KV260 2022.2 参考平台构建阻塞 — 第二轮诊断报告

日期：2026-09-30（主机本地时区）。工作区：`/home/ghmd/kv260-reference-2022.2-20260930`。
本轮**未修改**厂商 Tcl、未伪造速度参数、未删除官方时钟模块、未改动现有安装 / 工程 / 板端固件、未烧录。
本报告是继 `REPORT.md`、`REPAIR_REPORT.md` 之后的**补充诊断**，不替换它们。

---

## 1. 结论摘要

1. **报错可 100% 复现，且与工程无关**：在仅含 `create_project -part xck26-sfvc784-2LV-c` + `create_ip -name clk_wiz` 的最小工程中同样失败。
2. **本轮新增的裁决性证据**：Vivado 自身打印
   `WARNING: [Device 21-8777] ML based speedfiles are not available for the part. Loading regular speedfile`
   随后仍然报 `expected floating-point number but got "Unable to get value from speedsfile for keyword MM"`。
   → Vivado 先尝试 **ML speedfile**，确认**该器件没有**，回退到 **regular speedfile** 后**仍然取不到** MMCM 类关键字的值。
3. **影响范围为"所有已安装的 Kria 器件"**：`xck26-sfvc784-2LV-c`、`xck26-sfvc784-2LVI-i`、
   `xck24-ubva530-2LV-c`、`xck24-ubva530-2LVI-i` **全部** `create_ip clk_wiz` 失败；
   同一工程下对照 IP `axi_gpio` **全部成功**。
4. **因此这不是 IP 仓库损坏、不是 locale/沙箱问题、不是器件无法枚举问题，而是"该安装中 Kria（Zynq UltraScale+）
   器件缺少 Clocking Wizard 所需要的速度模型值数据（PASPD / speedfile 内容）"。**
5. **本机不存在第二套可启动的 Vivado 2022.2 安装**（本轮重新全盘核实，见 §3.1），因此"优先用另一套安装验证"这一条**无法满足**；
   修复只能走"向现有安装增补/修复器件数据"。
6. **本轮未执行任何安装变更**：增补需要有效的 AMD 认证令牌或官方离线安装介质，按规则先列明缺失组件、修复范围与恢复方法，等待确认（§6）。
7. 由于最小探针仍未通过，**`platform` / `overlay` 未运行**，本轮**没有**任何新构建的 XSA / XPFM / XO / XCLBIN / BIT / HWH / arch.json（§8）。

---

## 2. 最早错误与 Tcl 调用位置（证据）

| 项 | 内容 | 证据文件 |
|---|---|---|
| 最早非正常输出 | `expected floating-point number but got "Unable to get value from speedsfile for keyword MM"` | `logs/platform_vivado_first.log:123` |
| 紧随其后的命名错误 | `ERROR: [IP_Flow 19-3476] Tcl error in create_gui procedure for BD Cell 'clk_wiz_audio'` | 同上 :124 |
| 触发点 | `create_bd_cell -vlnv xilinx.com:ip:clk_wiz:6.0`（`create_hier_cell_audio_ss_0` → `scripts/config_bd.tcl:884`） | `REPORT.md` §已执行与失败证据 |
| 独立最小复现 | `create_ip -name clk_wiz -vendor xilinx.com -library ip` 即失败 | `logs/probe_clk_wiz*.log`、本轮 `logs/diag2/3/4/5.*` |
| 厂商侧调用链 | `clk_wiz_v6_0_utils.tcl` → `get_speedsfile_key_value` → `GetClkwizProperty $PartName $ComponentName "SpdKeyValue" $keyword` | `Vivado/2022.2/data/ip/xilinx/clk_wiz_v6_0/xgui/clk_wiz_v6_0_utils.tcl` |
| 查询的具体关键字 | `MMCM_CLKIN_FREQ_MIN/MAX`、`MMCM_VCOCLK_FREQ_MIN/MAX`、`MMCM_CLKOUT_FREQ_MIN/MAX`、`MMCM_CLKPFD_FREQ_MIN/MAX`、`M_MIN/M_MAX`、`D_MIN/D_MAX`、`O_MIN/O_MAX`、`MMCM_REF_CLK_JITTER_MAX`、`FMAX_BUFGCE_DIV`、`PLL*`、`PLLE2*` | 同文件 `get_speedsfile_data`（190–300 行） |
| 错误串与实现所在库 | `lib/lnx64.o/librdi_iptasks.so` 内含字符串 `Unable to get value from speedsfile for keyword %s`、`SpdKeyValue`，以及符号 `Ip_Clocking::clocking_utils::getSpeedFileProperty` | `strings` 取证 |

> 说明：错误文本中的 `MM` 是厂商接口返回值中的失败片段，**不能**当作完整缺失键名或数值使用；本轮未改动该 Tcl 与任何参数默认值。


---

## 3. 安装记录、已安装组件与器件数据核查

### 3.1 是否存在"另一套完整的 Vivado 2022.2 安装"——**否**

| 检查 | 命令/位置 | 结果 |
|---|---|---|
| 已知安装路径 | `/home/ghmd/Xilinx_2022.2/Vivado/2022.2` | 存在，v2022.2（SW 3671981），26 GB |
| 旧路径 | `/home/ghmd/Xilinx/Vivado/2022.2`、`/home/ghmd/Xilinx/Vitis/2022.2` | **不存在** |
| `/home/ghmd/Xilinx` 全部内容 | `find /home/ghmd/Xilinx -maxdepth 2` | 仅 `.xinstall/` 与 `Downloads/`（466 MB 安装器 payload 缓存），**无主程序** |
| 全盘搜索 `*/Vivado/*/settings64.sh` | `find / -xdev ... -name settings64.sh -path '*Vivado*'`（排除已知安装与备份） | **无其它结果** |
| 其它常见位置 | `/tools/Xilinx`、`/opt/Xilinx`、`/mnt`、`/media`、`/srv` | 无 Vivado |
| 备份副本 | `installation_backup/Vivado_2022.2_before_add` | 26 GB / 137,939 文件，与当前安装**同源同数量**，不是独立第二套 |

### 3.2 已安装组件（安装记录）

`Xilinx_2022.2/.xinstall/Vitis_2022.2/data/instRecord.dat`：
`Common_Links`、`Scout_Product`、`Vitis_HLS`、`Vivado_for_Scout`、`XiC_MODULE`、**`Xilinx_Kria_Som`**；
`installedPackage = Scout_Edition`。

- **没有 `Zynq_MPSoC_Devices`（"Zynq UltraScale+ MPSoC" 器件模块）。**
- `~/.Xilinx/install_config.txt` 中所有器件模块项均为 `0`，与"只装了 Kria SOM 器件"一致。
- `~/.Xilinx/registry/installedSW.xml`：`2022.2_1014_8888`，两处安装记录。

### 3.3 器件支持：区分"能枚举"与"能生成"

| 检查 | 结果 | 判读 |
|---|---|---|
| `get_parts xck26*` | `xck26-sfvc784-2LV-c`、`xck26-sfvc784-2LVI-i` | **可枚举** |
| `get_parts xck24*` | `xck24-ubva530-2LV-c`、`xck24-ubva530-2LVI-i` | **可枚举** |
| `get_parts xczu*`（通用 MPSoC） | **空** | 通用 MPSoC 器件数据未安装 |
| `get_board_parts xilinx.com:kv260_som:part0:1.4` | 可用 | 板卡定义正常 |
| `create_ip clk_wiz`（依赖速度模型值） | **4/4 失败** | **不能生成** |
| `create_ip axi_gpio`（不依赖速度模型值） | **4/4 成功** | IP 框架正常 |

> 这就是"能枚举器件 ≠ 时钟 IP 能实际生成"的直接证据。

### 3.4 时钟 IP 依赖的速度模型数据

| 检查项 | 实测 | 判读 |
|---|---|---|
| `data/parts/xilinx/zynquplus/` 总大小 | 889 MB | 有数据，但只覆盖 Kria 器件 |
| `.../devint/zynquplus/xck26/` | 8.7 MB：`xck26.xgd/.rtd/.xng/.preplace/.cfg/.frameData/.bramTileSites` + `sfvc784/Package.xml`、`fbvb900/` | 器件**物理/布局**数据存在 |
| `.../devint/zynquplus/timing/prod_ver1/`、`prod_eval/` | 各含 `delay_0..3.dst`、`routes.dst`、`zynquplus.lib`、`zynquplus.belTimingModels`、`netTimingSet`、`zynquplus_pt.lib` 等（合计约 360 MB） | 家族**时序**数据存在 |
| `*.paspd` / `*.padr`（PASPD = speed model values file） | 全安装仅 4 个：`timing/{prod_ver1,prod_eval}/zynquplus.nonlib.paspd` 与 `zynquplus.padr` | **只有 `nonlib`（非库）部分** |
| `<family>.paspd`（tag `<paspd>` = "Paspd speedfile"） | **未找到** | **疑似缺失的关键数据** |
| `data/parts/xilinx/` 其它家族 | `kintexuplus` 344 KB、`virtexuplus` 148 KB …… **无 versal 家族目录** | 无对照器件可用 |
| `data/parts/arch.xml`、`DeviceParts.xml`、`PartStats.xml` | 为**二进制/编码**格式（非明文 XML），故字符串检索不能证明"数据缺失" | 需运行时证据（见 §4） |

`librdi_device.so` 中的官方字符串（一手依据）：
```
device.loadMLSpeedfile  ->  "Switch that enables to load ML Speedfile (if exists) for any
                             part that does not have timing information"
device.evalarch.paspdFile       -> "PASPD file location"
device.evalarch.nonlibPaspdFile -> "nonlib PASPD file (vorpal)"
"<paspd>" / "Paspd speedfile";   "<nonlib.paspd>" / "nonlib.paspd"
"Unable to read Paspd speedfile"
"DEBUG: PASPD, speed model values file, is compiled." / "... is text format."
"Opened default parameter speedfile";  "from paspd file - skipping"
"@21-8777@"（本轮观测到的 ML speedfile 警告编号）
```

---

## 4. 本轮裁决性实验（全部为运行时只读/可逆操作，不改任何文件）

| # | 实验 | 脚本 / 日志 | 结果 |
|---|---|---|---|
| E1 | 最小复现：K26 上 `create_ip clk_wiz` | `diag/diag_clkwiz_paths.tcl` → `logs/diag2.*` | 失败，与原始错误一致 |
| E2 | 枚举与速度相关命令 | 同上 | 仅 `get_speed_models`、`set_speed_grade`（`get_speed_models` 属设计内速度模型查询，需打开的 design） |
| E3 | 设置 `device.loadMLSpeedfile true` 后重试 | `diag/diag_clkwiz_paths3.tcl` → `logs/diag3.*` | **`WARNING: [Device 21-8777] ML based speedfiles are not available for the part. Loading regular speedfile`**，随后仍失败 |
| E4 | 设置 `device.loadMLSpeedfile false` 后重试 | 同上 | 直接失败（同样错误） |
| E5 | 打开 device debug 参数（`debugGetDeviceLoadPath`、`debugPartLoader`、`dumpSpeedModelStackTrace` 等）后复现 | `diag/diag_clkwiz_paths4.tcl` → `logs/diag4.*` | 参数可被接受，但该级别 debug 未在日志中输出具体 speedfile 路径（**未获得路径级证据**） |
| E6 | 影响范围：4 个已安装 Kria 器件分别建时钟 IP + 对照 `axi_gpio` | `diag/diag_clkwiz_scope5.tcl` → `logs/diag5.*` | `clk_wiz` **4/4 失败**；`axi_gpio` **4/4 成功** |
| E7 | 用 `strace` 做系统调用级取证 | `diag/strace_clkwiz_paths.log` → `logs/diag_stdout.txt`（即 `diag/diag_stdout.txt`） | **不可用**：Vivado 在 ptrace 下 `Segmentation fault (core dumped)`（139）。这是工具兼容性问题，与时钟 IP 缺陷无关 |

> 说明：E3/E4 是**运行时参数**实验（不写入任何文件、不修改厂商 Tcl、不伪造速度数值），用于判定"是数据缺失还是开关问题"。
> 结论是**开关无法补救**——因为数据本身对该器件不可用。

---

## 5. 根因判定与仍不确定的部分

### 已确认（有直接证据）
1. 失败点固定在 `clk_wiz` IP 的 `create_gui` 阶段，由 `GetClkwizProperty ... "SpdKeyValue"` 无法取到速度模型值引起。
2. Vivado 明确告知：该器件**没有 ML based speedfile**；回退到 regular speedfile 后**仍取不到值**（E3）。
3. 影响范围是**该安装内的全部 Kria 器件**，而同一安装中**不依赖速度模型的 IP 正常**（E6）。
4. 本机**只有一套** Vivado 2022.2，且安装记录**不含** Zynq UltraScale+ MPSoC 器件模块；`get_parts xczu*` 为空。
5. 器件数据中**只有 `zynquplus.nonlib.paspd`**，全安装找不到库侧 `<family>.paspd`（"Paspd speedfile"）。

### 尚不能 100% 断言的（诚实标注）
1. **"缺 `Zynq UltraScale+ MPSoC` 模块"能否一定修复**：尚无本轮实测，因为增补需要有效令牌/离线介质。逻辑与证据高度支持，但**未验证**。
2. **"Kria SOM 模块本身是否应包含速度模型值文件"**：AMD 官方文档只说该模块安装 Kria SOM/Starter Kit 的器件支持，未给出文件级清单；
   本机**原始 9-27 安装日志已被 9-30 的失败 Add 覆盖**（`xinstall.log` 中只有该次 Add 的记录），无法回溯下载/校验是否完整。
   因此"模块边界问题"与"该模块文件下载不完整"两种可能**都还不能排除**，但两者的修复动作相同（补齐器件数据）。
3. **是否与 `-2LV` 低电压速度等级强相关**：4 个 Kria 器件（2LV / 2LVI）全部失败，数据不足以单独区分速度等级因素。
4. 未获得 speedfile 的"路径级"证据（E5/E7 均未给出），因此**不能**指出"某个具体文件不存在"作为唯一根因。

---

## 6. 修复方案（**尚未执行**，等待确认）

### 6.1 缺失组件与修复范围

| 项目 | 内容 |
|---|---|
| 缺失/可疑组件 | ① **`Zynq UltraScale+ MPSoC` 器件模块（`Zynq_MPSoC_Devices`）**：安装记录中不存在，`get_parts xczu*` 为空；② Kria 器件数据中 Clocking Wizard 所需的速度模型值文件（PASPD/"Paspd speedfile"）不可用 |
| 修复范围 | **只向现有 `/home/ghmd/Xilinx_2022.2` 增补器件数据**；不改安装路径、不升级版本（仍为 2022.2）、不动 Vitis/PetaLinux、不动 `kria-vitis-platforms` 源码、不动任何工程与板端固件 |
| 禁止事项（保持） | 不修改厂商 Tcl、不伪造速度参数、不删除/替换官方时钟模块、不删除现有构建日志 |
| 预期下载量 | 中等（仅器件数据，通常 8–20 GB 量级；具体以安装器显示为准） |

### 6.2 方案对比（请任选其一）

| 方案 | 操作 | 依据 | 影响 | 前提 |
|---|---|---|---|---|
| **A（推荐，在线增补）** | 由你本人执行 `xsetup -b AuthTokenGen` 刷新令牌（**不要把密码/token 给我**），确认后可运行已备好的 `-b Add -c evidence/installer/install_config_add_mpsoc.txt`（仅 `Zynq UltraScale+ MPSoC=1`，目标为现有安装路径） | AMD UG973 2022.2《Adding Additional Tools and Devices》《Running the Installer》；安装器原生支持"向现有安装增补工具/器件" | 新增器件数据，可能覆盖/补齐 `data/parts/xilinx/zynquplus/`；不动版本与工程 | 有效 AMD 账号令牌 + 网络 |
| **B（离线增补）** | 提供 **2022.2 完整离线安装镜像（SFD，约 89.4 GB）** 的本地路径，用同一配置文件做离线 `-b Add` | 同上 | 同 A，且不受网络/令牌影响 | 你有该镜像文件 |
| **C（跨机复制，最快但有约束）** | 若你另有**同版本（2022.2，build 1014_8888）**完整安装，复制其 `Vivado/2022.2/data/parts/xilinx/zynquplus/`（并核对文件清单与 SHA-256）到本机对应目录 | 等价数据替换 | **仅替换器件数据目录**；必须先备份现状、逐文件校验，风险高于 A/B | 存在同版本完整安装 |
| D（不采用） | 修改厂商 Tcl / 设参数绕过 / 用旧 bitstream 与不明来源 arch.json | — | 会产生不可信结果，且与你的要求冲突；本轮已实测**参数开关无效** | — |

### 6.3 恢复方法（回滚，已就绪）

`installation_backup/` 内容与本轮核实结果：
- `Vivado_2022.2_before_add/`：**26 GB / 137,939 普通文件**，与当前 `Vivado/2022.2` 同源同数量。
- `Vitis_2022.2_installer_before_add/`：安装器目录 + 安装日志。
- `installedSW_before_add.xml`、`instRecord_before_add.dat`：安装注册表快照。

回滚顺序（仅在修复出现问题时执行）：
1. 退出所有 Vivado / 安装器进程；
2. 将出问题的 `/home/ghmd/Xilinx_2022.2/Vivado/2022.2` **改名保留**（不删除），
3. 从 `installation_backup/Vivado_2022.2_before_add` 复制回原路径；
4. 从 `installation_backup/Vitis_2022.2_installer_before_add` 复制回 `/home/ghmd/Xilinx_2022.2/.xinstall/Vitis_2022.2`；
5. 从 `installedSW_before_add.xml` 恢复 `~/.Xilinx/registry/installedSW.xml`；
6. 重跑 `diag/diag_clkwiz_paths.tcl`，确认回到"当前状态"（即仍失败但行为一致）。

> 当前**未开始任何修复**，因此回滚**尚未需要**。

---

## 7. 官方资料与一手同报错记录

| 类别 | 来源 | 用途/结论 |
|---|---|---|
| 官方安装 | [UG973 2022.2 Adding Additional Tools and Devices](https://docs.amd.com/r/2022.2-English/ug973-vivado-release-notes-install-license/Adding-Additional-Tools-and-Devices) | 官方支持后装增补工具/器件（方案 A/B 依据） |
| 官方安装 | [UG973 2022.2 Running the Installer](https://docs.amd.com/r/2022.2-English/ug973-vivado-release-notes-install-license/Running-the-Installer) | 安装器命令行与 Add 用法 |
| 官方流程 | [UG896 2022.2 Using IP Tcl Commands in Design Flows](https://docs.amd.com/r/2022.2-English/ug896-vivado-ip/Using-IP-Tcl-Commands-In-Design-Flows) | 时钟 IP 输出产品与独立综合（§9 的第 2 步依据） |
| 一手同报错 | [Xilinx/open-nic-shell discussion #46](https://github.com/Xilinx/open-nic-shell/discussions/46) | **完全相同**的 `Unable to get value from speedsfile for keyword MM`：发生在 Vivado 2022.1 + **ML Standard 版**、目标器件未完整安装（U50/U55C）时；维护者回复未给出该错误的已验证修复，仅建议换版本/不升级特定 IP。**仅作症状对照，不作为修复依据** |
| 本轮实测 | `librdi_device.so` / `librdi_iptasks.so` 内的官方字符串与参数说明 | 证明速度模型值（PASPD/speedfile）是时钟 IP 定制的必要数据 |

> 说明：公开检索未找到 AMD 官方针对"Kria SOM 器件模块 + Clocking Wizard speedsfile"的专门 AR/答复；因此本报告不把任何第三方"解法"当作已验证修复。

---

## 8. 本轮实际结果：产物与未执行项（严格区分）

### 8.1 本轮**实际生成**的产物
| 类型 | 路径 | 说明 |
|---|---|---|
| 诊断脚本 | `diag/diag_clkwiz_paths.tcl`、`diag_clkwiz_paths2.tcl`、`diag_clkwiz_paths3.tcl`、`diag_clkwiz_paths4.tcl`、`diag_clkwiz_scope5.tcl` | 全部为只读/可逆探针 |
| 诊断日志 | `logs/diag2.*`、`logs/diag3.*`、`logs/diag4.*`、`logs/diag5.*`、`diag/diag_stdout.txt`、`diag/strace_clkwiz_paths.log` | 原始输出（含 §4 全部实验） |
| 报告 | 本文件 `RUN2_DIAGNOSIS_REPORT.md` | 中文诊断报告 |
| 临时工程 | `diag/diag_proj*`、`diag/diag_p5_*`、`evidence/clk_wiz_probe` | 仅为探针创建的 Vivado 工程，未参与任何交付 |

### 8.2 本轮**未生成**（必须明确）
| 类型 | 状态 | 原因 |
|---|---|---|
| XSA / XPFM | **未生成** | `run_reference_build.sh platform` 未运行（探针未通过） |
| DPU XO / XCLBIN / BIT / HWH / arch.json | **未生成** | overlay 未运行 |
| 实现后资源/时序报告（`*.rpt`） | **未生成** | 同上 |
| 任何安装变更 | **未执行** | 等待 §6 授权 |
| 板端部署/烧录 | **未执行** | 本轮不涉及；`staging/` 中的预编译固件**不是**本轮成果 |

> **明确声明**：`staging/` 与 `firmware-reference/` 中的固件来自官方预编译仓库，**不得**计作本轮构建产物。

---

## 9. 修复通过后的后续步骤（已准备，尚未执行）

| 步骤 | 输入 | 产物 | 验收条件 |
|---|---|---|---|
| S1 最小探针 | `evidence/probe_clk_wiz.tcl`（或 `diag/diag_clkwiz_paths.tcl`） | 控制台 `PROBE_CLK_WIZ_CREATED` | 4 个 Kria 器件上 `create_ip clk_wiz` 不再报 `speedsfile`，且无 `IP_Flow 19-3476` |
| S2 器件数据复核 | Vivado batch | `get_parts xczu*` 输出、`instRecord.dat` 复查 | `Zynq_MPSoC_Devices` 出现在安装记录；通用 MPSoC 器件可枚举 |
| S3 时钟 IP 输出产品 + 最小综合 | `evidence/installer/verify_clk_wiz_after_repair.tcl`（含 `generate_target` + 该 IP 的 OOC 综合） | `.xci`、`*_sim_netlist`/`.dcp`、综合日志、`utilization/timing` 报告 | 综合 0 error；时钟频率参数与预期一致；输出 `*.dcp` 与报告落盘 |
| S4 平台构建 | `run_reference_build.sh platform`（`PFM=kv260_ispMipiRx_vcu_DP JOBS=4`） | **XSA、XPFM** | 命令返回 0；XSA/XPFM 生成；日志无致命错误 |
| S5 overlay 构建 | `run_reference_build.sh overlay`（`OVERLAY=benchmark`） | **XO、XCLBIN、BIT、HWH、arch.json**（`binary_container_1/sd_card/`） | `v++ --link` 成功；DPU CU 数/基址符合 `prj_config_1dpu`（1×`DPUCZDX8G_1`，300/600 MHz，HPC1/HP1/HP3） |
| S6 证据归档 | 上述全部产物 | `*.rpt`、`*.dcp`、XSA/XPFM/XO/XCLBIN/BIT/HWH/arch.json 的 **SHA-256 与版本信息** | 哈希清单写入 `evidence/SHA256SUMS`；版本号与 Vivado/Vitis 2022.2 一致 |

**重要约束（保持）**：这些步骤成功后，仍**不进行板端部署或烧录**；新构建产物与 `staging/` 中的官方预编译固件必须分开记录、分开校验。
