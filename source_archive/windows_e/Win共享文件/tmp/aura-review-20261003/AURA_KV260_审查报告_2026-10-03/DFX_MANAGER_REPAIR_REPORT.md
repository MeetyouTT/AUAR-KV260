# KV260 DFX manager 重复监视项修复报告

## 结果

固定版本的修复候选已通过主机构建、回归、运行库审阅和实际 KV260 有限复验。测试结束后恢复原管理器、原 ZOCL、官方 `kv260-benchmark-b4096` slot 0 和原 VART 配置；26 份运行文件哈希一致，boot ID 未变。

**修复候选没有永久安装。当前运行的原程序仍包含原有缺陷。** 本轮完成管理器修复与有限验证，没有重建系统镜像或 FPGA，也没有烧录、重启、PWM、寄存器写入或执行器操作。

实际板端命令窗口：`2026-10-03T04:06:08.786219Z` 至 `2026-10-03T06:03:58.569205Z`。共 24 条成功命令、1 条失败就绪探针；所有输出均完整回收并核对哈希。候选传输另计，18 帧及整包哈希通过。主复验与恢复在 `2026-10-03T06:02:09.248872Z` 完成，随后追加只读挂载检查。

## 1. 已确认的原因

原配方使用 dfx-mgr commit `bc06691eb35d7f0acb7c2508b6d050d77b0264a0`。重新取得固定官方归档，其 139 个 Git blob 与此前封存的固定树逐一一致；没有改选源码版本。

源码调用关系为 `listAccelerators() → firmware_dir_walk() → acell_dir_add() → add_to_watch()`。重复扫描再次调用 `inotify_add_watch()`；内核对于同一目录可返回同一个 wd，原 `add_to_watch()` 却直接占用下一个空槽。后面的 base 去重来不及保护 watch 表。内部 `MAX_WATCH=500` 因重复登记耗尽。

主机使用真实 helper 和 inotify 确定复现：原版 130 次扫描后，内部已有 500 项，而内核仅有 5 个监视项。这与上轮板测的 44 条去重管理器错误、内核 5 个监视项相符；不能通过“内核监视项不多”排除内部耗尽。

原源码：[daemon_helper.c](https://github.com/Xilinx/dfx-mgr/blob/bc06691eb35d7f0acb7c2508b6d050d77b0264a0/src/daemon_helper.c)。本地复核见 `evidence/source_final_review.json` 和 `evidence/host_validation_summary.json`。

## 2. 实际修复范围

仅改 `src/daemon_helper.c`：

- 登记时遍历有效表项，按 wd 或完整 path 找已有项；先记住空槽，继续检查后面的已有项，避免空洞造成重复。
- 已有项更新原槽；新项才使用空槽；容量仍为 500。
- 检查无效 wd、空参数、字符串边界，完整初始化并保存元数据；保留明确的错误诊断。
- 对登记和删除的写操作加 mutex；删除时清理整项。

补丁 SHA256：

`62fd3dc5ddfc6fe789aac5dff38d03f82cf0d3240883d3e0da493546888e99d0`

最终复核确认 139 个文件中只改这一个文件，`artifacts/watch-dedup.patch` 与实际源码差异完全一致。未修改厂商时钟 Tcl、DRC 规则、PL、默认固件或既有模型。

该锁保护本轮修改的 watch 写操作，不能据此宣称整个 daemon 的所有共享数据均已具备完整并发安全性。

## 3. 构建与主机验证

复用已有 Vitis/PetaLinux 工具，没有安装或升级软件，也没有修改全局 shell 配置。

| 项目 | 实测条件或结果 |
|---|---|
| 交叉工具链 | Vitis 2022.2 内 AArch64 GCC 11.2 |
| CMake | 现有 AArch64 SDK 内 CMake 3.21.1 |
| 官方构建入口 | CMake，targets `dfx-mgrd-static`、`dfx-mgr-client-static`，并行度 4 |
| 原版、修复版 | 均成功构建，完整 configure/compile/readelf 日志保留 |
| libdfx | header 固定 `f2b7bbca9d6936141024becfb92266600eeefc2b`；链接库复用原镜像二进制 |
| 构建标志 | `-O2`、stack protector、FORTIFY、branch protection、RELRO/NOW；保留官方 `-Werror` |
| 主机编译器 | 已有 PetaLinux extended buildtools 的 GCC 11.2 |
| 运行库审阅 | 4 个 AArch64 原版/修复版 daemon/client 均通过原镜像 loader 的 QEMU `--list` |
| 修复 daemon 符号 | 84 个强引用均可按版本解析，未解析强符号为 0 |
| 可运行副本 | 已删除主机 build RPATH；原编译和 debug ELF 保留 |
| 新客户端 | 原版与修复版 `.text` 一致；板端沿用原客户端 |

`static` target 指管理器库链接方式；产物仍动态依赖 libc、pthread、libdfx 和加载器，不能理解为完全静态程序。库和此前修复 ZOCL 是输入，未列为本轮新构建成果。

| 回归项目 | 原始日志实际结果 |
|---|---|
| 原缺陷复现 | 130 次扫描，内部 500 项、内核 5 项 |
| 修复扫描 | 10,000 次扫描，内部及内核均为 5 项 |
| 目录生命周期 | 1,000 次添加/删除/重新登记，最终均为 5 项 |
| 边界 | 空洞、已有项、满表、容量溢出、非法参数及字符串边界通过 |
| 同项并发登记 | 8 线程、80,000 次调用，最终 1 项 |

这些主机测试不加载 FPGA、不启动实际板端 daemon。现有 GCC SDK 不含 libasan，最终回归没有 sanitizer 覆盖。QEMU loader 检查是 ABI 证据，实际可用性以以下板测为准。

## 4. 实际板端复验

备用卡、根分区、内核、原文件、DRM 占用与 boot ID 均逐阶段核对。板端保持 PetaLinux 2022.2 / Vitis AI 3.0，Win11 网口直连没有改变；命令通过 Ubuntu UART 执行。

反复卸载期间，临时使用此前已验证的修复 ZOCL `9BDC942A6014BCCBD1DCB78`，参数 `enable_xgq_ert=1`。候选管理器通过独立的 `/run/systemd/system/dfx-mgr.service.d/` 配置启动，原厂 unit 和原二进制没有覆盖。

| 阶段 | 结果与证据 |
|---|---|
| 原程序备份及候选传输 | 7 份基线文件备份；55,124 字节、18 帧及整包哈希通过 |
| 候选下官方同图推理 | DPU 查询、同图 Top-5 与基线一致 |
| 大量列表查询 | 专门的 1,000 次循环成功；6 个采样点均为内核 5 个监视项 |
| 真实目录事件 | 50 次自建测试目录创建/删除；发现时 6 项，删除后 5 项，测试目录最终不存在 |
| 官方应用循环 | 在修复驱动下 3 轮卸载/重载成功，随后同图推理通过 |
| M3 应用 | 一次加载成功，DPU 查询及同模型同图推理通过 |
| 原程序与驱动恢复 | 正常卸载 M3，候选 SIGINT 刷新日志后停止，移除本轮临时配置，恢复原服务和原 ZOCL |
| 恢复后复验 | 官方应用 slot 0，同图推理通过；26 文件哈希全部一致 |
| 完整候选日志 | 1,673,512 字节；板端/主机 SHA256 一致；`ERROR:` 及 watch 容量错误为 0 |

本轮所有功能查询：1 个 DPU CU、`DPUCZDX8G_ISA1_B4096`、地址 `0xa0010000`、DPU/XRT 均 300 MHz、指纹 `0x101000056010407`。官方 IP git 标识 `ce8dd1`；M3 标识 `7d32c41`。ResNet18 XMODEL、样图和可执行文件的哈希逐阶段核对；四次功能复验 Top-5 均与原对照相同：

| 类别编号 | 类别 | 分数 |
|---|---|---|
| 258 | Samoyed | 0.949879 |
| 270 | white wolf | 0.00931229 |
| 259 | Pomeranian | 0.00821807 |
| 257 | Great Pyrenees | 0.00498451 |
| 279 | Arctic fox | 0.00388194 |

主机测试可直接观察内部表项；本轮板测观测内核监视项、实际功能及完整错误日志，没有直接读取 daemon 内部表项。也没有重新运行 FPS 测试，不能将上轮 FPS 写成本轮成果。

日志 SHA256：

`e33f7362ea28b9cfc4d8243b30f7ab204dfaf7bd266c0eb162683ff9919151d3`

原始证据见 `evidence/20261003T043753Z-board-continuation/`；命令汇总见 `evidence/board_command_ledger.json`。

## 5. 失败、修正及实际保留问题

### 本轮就绪探针错误，已纠正

`06-start-candidate` 返回 1：我编写的就绪探针使用 `SOCK_STREAM`，原服务实际创建 `SOCK_SEQPACKET`。只读诊断确认候选进程、修复驱动和官方应用已经正常启动，失败是就绪误判。

保留完整失败命令及日志，没有重跑已执行的启动操作。在独立 continuation 中改为 `SOCK_SEQPACKET`，`20-ready-check` 通过后顺序完成后续测试与恢复；没有因此修改候选生产二进制。

官方 socket 入口：[dfx-mgrd.c](https://github.com/Xilinx/dfx-mgr/blob/bc06691eb35d7f0acb7c2508b6d050d77b0264a0/example/sys/linux/dfx-mgrd.c#L156)。原失败证据在 `evidence/20261003T042453Z-board-validation/`，修正来源与冻结哈希在 continuation 的 `preparation.json`。

### 构建准备阶段的失败，均保留

- 首轮 Debug/O0 配置与 FORTIFY 冲突，官方 `-Werror` 拒绝编译；在新的独立构建中加 `-O2` 后原版及修复版均通过。
- 主机 GCC 9.4 拒绝原厂匿名形参定义；改用已有 GCC 11.2 后通过，未改原厂函数来迁就旧编译器。
- 早期 loader 审阅先遇到 debugfs PATH、随后遇到抽取加载器缺少执行位；修正本地主机抽取与工具路径，最终独立 runtime review 全部通过。
- 两个下载的默认沙箱网络尝试退出 7；获准在沙箱外下载固定官方归档并核对哈希。

这些失败目录、日志与首次 runner 保留，没有替换为成功日志。

### 原 ZOCL 的退出引用错误

开始卸载原官方应用时，原驱动实际出现一次：

`[13104.964094] OF: ERROR: memory leak, expected refcount 1 instead of 2 ... /axi/zyxclmm_drm`

修复 ZOCL 后，受控循环、M3 卸载和恢复阶段未新增该目标引用错误。结束又恢复了原驱动，其已知缺陷仍存在。

### 基线挂载配置与其他警告

两次 daemon-reload 实际产生 `boot.mount` 重复生成失败。追加只读检查确认 `/etc/fstab` 同时包含：

`LABEL=boot        /boot   vfat    defaults    0   2`

`/dev/mmcblk1p1    /boot   vfat    defaults    0   0`

板端文件与此前保存的基线 rootfs 字节及哈希一致，确认本轮修复之前已存在；没有据此断言两条配置都来自厂商原始镜像。目前仅有一个实际 `/boot` 挂载，设备 `/dev/mmcblk1p1`，unit active/mounted、Result=success。本轮未改 fstab。

收集窗口按内核时间去重后，还记录了 112 条 overlay 属性警告、26 条 SysV 兼容生成提示。这些没有被隐藏或改严重级别；目标引用错误为上述一次，未见分类之外的新 ERROR/异常。统计范围是已回收的日志窗口，不等于全生命周期无泄漏证明。

详见 `evidence/kernel_diagnostics_review.json` 和 `evidence/20261003T060312Z-fstab-audit/review.json`。之前 PL 的 DRC、约束与时序限制继续以封存审阅报告为准，本轮没有消除它们。

## 6. 新成果与使用范围

| 新成果 | 位置 |
|---|---|
| 实际源代码修复 | `sources/dfx-mgr-patched/src/daemon_helper.c` |
| 精确补丁 | `artifacts/watch-dedup.patch` |
| 原版/修复版编译及 debug ELF | `artifacts/baseline/`、`artifacts/patched/` |
| 去除 RPATH 的板测候选 | `artifacts/runtime/20261003T040248.123957Z-runtime-review/patched/dfx-mgrd` |
| 整理后的候选包 | `release/kv260-dfx-watch-reviewed.tar.gz` |
| 候选包元数据 | `release/manifest.json` |
| 主机/板测/恢复汇总 | `evidence/validation_summary.json` |
| 本轮索引及核验 | `EVIDENCE.sha256`、`EVIDENCE_VERIFY.json` |

实际板测候选：117,488 字节，SHA256：

`db9c25f09f1178177884b1114c57f32c076f1e7f9cdd0d12b7a896039038a46c`

整理包：51,758 字节，SHA256：

`3153015d735bf24ceddef8b9b4b079092aaf522a6e96dc06c34a8f2b6919074a`

整理包包含同一候选、补丁、版本信息、运行库要求、说明和校验清单；二进制与已板测版本逐字节一致，压缩包成员回读哈希通过。整理包没有再次部署。

`bundle-v2` 保留历史测试输入，其中旧 guard 的就绪函数使用 SOCK_STREAM；本轮通过的是独立续跑的覆盖函数。整理包不携带该错误 guard，不提供永久安装脚本；已执行的旧控制器禁止盲目重跑。

原镜像 libdfx、镜像运行库、此前修复 ZOCL、官方/M3 FPGA 固件及模型均为本轮输入；没有新 BIT、XCLBIN 或 XSA 成果。

## 7. 当前状态与后续

当前运行 `/usr/bin/dfx-mgrd`、原 ZOCL `0991D1B457855C8987936E6`、官方应用 slot 0；候选位于独立工作目录，临时 service 配置已移除，自建 probe 目录已删除，原基线备份保留。

本轮恢复目标已完成。后续固定测试环境需要一起纳入已验证的管理器候选和此前修复 ZOCL，重新保存基线并形成新的受控启用计划，再评估是否永久使用。还需长期加载/卸载、内存增长、并发与断电恢复验收，以及单独处理 fstab 重复配置。

M3 的最小寄存器与 DPU 共存已经在上轮板测通过，本轮重新确认其 DPU 同图功能。PWM、运动控制和执行器仍未实现或验收。

原封存的驱动、M3 构建与板测证据保持原样，本轮另加新的日志与索引。
