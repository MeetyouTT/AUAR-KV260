# 命令与只读状态记录

记录范围：本次 KV260 完整镜像栈审计的关键读取、检查器调用、输出文件和退出状态。所有重定向/解包输出只写入 `/home/ghmd/kv260_full_image_audit_20260926_codex`。输入工程、模型、PetaLinux 文件均未写入。前一轮已经完成的重建命令另见 `/home/ghmd/kv260_clockfix_rebuild_20260926/BUILD_COMMANDS.md`；那是用户在隔离重建目录中完成的构建，不是本次只读审计重新执行。

以下逐项列出会读取/解析项目证据的主要命令。行号核对期间另外调用的 `rg -n`、`sed -n`、`nl -ba`、`head`、`wc -l`、`find` 均为只读文本/目录查看，退出状态为 0（缺失模式或路径的例外列在后文），输出仅显示在交互终端，未单独写日志。报告编辑和哈希清单生成只写本诊断目录；没有命令写回任何输入目录。文件清单字段包括 `file` 给出的文件类型、大小、SHA256 和绝对路径；archive 成员与内部版本字段另见专门报告，无法解出/确认的字段保持未确认。

| 检查 | 实际命令/方式 | 状态 | 结果位置 / 限制 |
|---|---|---:|---|
| 枚举/类型识别/哈希本机目标文件 | `python3 build_artifact_inventory.py`；对每个匹配文件调用只读 `file --brief <path>` 并计算 SHA256 | 0 | `reports/artifact_inventory.tsv`，136 个文件行；包含 group、file type、bytes、SHA256、absolute path；不表示整个磁盘的完整取证 |
| FIT 容器与成员 hash | `python3 parse_fit_readonly.py /home/ghmd/work/petalinux-kv260-dpu/images/linux/image.ub` | 0 | `reports/image_ub_fit_members.txt`；只在诊断目录解析/记录，内嵌 DTB/rootfs SHA 与对应独立文件一致 |
| PetaLinux BOOT.BIN 分区头 | `/home/ghmd/Xilinx/Vivado/2022.2/bin/bootgen -read /home/ghmd/work/petalinux-kv260-dpu/images/linux/BOOT.BIN` | 0 | `reports/bootbin_headers_readonly.txt`；读取分区/头信息，不等价于从 FPGA 或板端启动链读回哈希 |
| 两个 XSA 的 archive 成员哈希 | 只读列出/解包本机旧 PetaLinux XSA、新独立重建 XSA 到本审计 `extracted/xsa/` 并 SHA256 | 0 | `reports/xsa_member_hashes.txt`；与两份源 XSA 对照，不覆盖源 |
| FIT DTB 文本化 | `/home/ghmd/Xilinx/Vitis/2022.2/bin/dtc -I dtb -O dts -o reports/system_dtb_readonly.dts <PetaLinux system.dtb>` | 0 | DTS 写在本审计 `reports/`；DTC 诊断在 `reports/system_dtb_dtc_warnings.txt`。未改设备树源文件 |
| 新重建阶段连通性 | `/home/ghmd/Xilinx/Vivado/2022.2/bin/vivado -mode batch -source query_existing_dcp_stages.tcl`；Tcl 只对现有 DCP 执行 `open_checkpoint` 和 pin/cell/net 查询 | 0（最终修订版） | `reports/reset_stage_connectivity.txt`、`reports/vivado_stage_query_final.log/.jou/.stdout`。确认 synth→opt 之间 reset 连接消失 |
| DPU OOC checkpoint ports | Vivado batch + `query_dpu_ooc_ports.tcl`，仅 `open_checkpoint` 并查询端口方向/名称 | 0 | `reports/dpu_ooc_port_query.txt` 以及日志/journal/stdout；DPU OOC 中 reset 输入端口存在 |
| 既有深层 DPU OOC/reset 证据复核 | 只读查看此前保存的 `ip_ooc_and_new_routed_reset_topology.txt`、旧 routed 查询、仿真 netlist 摘录、实现 opt 关键行及对应 Tcl；逐份比对源文件和本目录副本 SHA256 | 成功 | 原始文件列表及哈希在 `reports/prior_audit_reference_sha256.txt`；副本在 `references_prior_audit/`。这不是本次重新打开旧 DCP 的结果，也不采纳先前摘要对“是否安全”的推断；本报告另与 AMD PG338 v4.1 reset 规定核对 |
| 本机 ELF build IDs / SONAME | `readelf -d -n` 检视从现存 PetaLinux rootfs archive 只读抽取到诊断目录的五个 `.so` | 0 | 五个 ELF 位于 `extracted/rootfs_usr_lib/`；哈希纳入 inventory。只代表当前本地 rootfs 包，不代表板端当前库 |
| AMD 本机 image/checksum 查找 | 对 `/home/ghmd` 目标文件集合按 `*.img`、`*.img.gz`、`*.wic`、`*kv260*dpu*`、`*.sha256`、`sha256sum*` 过滤枚举；随后只读检查 Installer 元数据 | 0 | 未找到官方 KV260 board image/校验和；文件清单保存在 `reports/artifact_inventory.tsv`，没有打开/执行下载器 |
| 当前介质/串口可见性 | `lsblk -o NAME,TRAN,TYPE,SIZE,MODEL,MOUNTPOINT`；`findmnt /media/ghmd/boot`；`ls /dev/ttyUSB* /dev/ttyACM*` | `lsblk` 0；`findmnt` 1（无挂载）；串口枚举 2（无匹配设备） | 原始输出及每条退出码保存在 `reports/host_device_visibility.txt`；没有板卡 SD/USB block device 或串口，所以未访问板端 |
| 既有启动日志 SHA | `stat -c '%n %s bytes' .../serial-boot-raw.log .../report.txt`；`sha256sum` 两个既有文件 | 0 | 原始启动日志 SHA256 `153aa69bba57792298f659e4cfdc7f248f3e78cc74aab22b1e6d9949679d46b`；仅读取既有日志，日志记录的是历史启动，不代表本轮最新 run |
| 官方资料 | 只读打开/查找 AMD Docs 的 UG1354 3.0、UG1414 3.0、PG338 v4.1 页面；网页查询只取得文本，没有下载二进制 | 成功 | URL 见 `REPORT.md` 官方参考资料；核对 UG1354 发布日期 2023-01-12、官方 image 名称及 KV260 1.0 支持，PG338 reset/port/tool/IP facts 内容；没有下载或安装 |
| 本轮报告复核 | `rg -n`、`sed -n`、`nl -ba`、`head`、`wc -l`、`find` 对本报告、诊断输出和来源文件做行号/路径核对 | 0 | 只读交互输出；除上述失败记录外，没有另行保存日志 |
| 生成并核对交付哈希清单 | `find . -type f ! -name SHA256SUMS.txt -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS.txt`；`sha256sum -c SHA256SUMS.txt > /dev/null` | 均为 0 | 清单覆盖本诊断目录中除其自身外的所有文件；核对通过；清单自身 SHA256 在本次最终回复单独报告 |

## 失败/停止的只读查询尝试

- 第一次 Vivado 阶段查询因为目标诊断 `reports/` 子目录尚未建立，启动失败，退出状态 1；没有打开/保存 checkpoint。部分日志在 `reports/vivado_stage_query_attempt1_partial.*`。
- 第二次 Tcl 使用错误的 Vivado 对象定位方式，退出状态 1；无工程写操作。记录在 `reports/vivado_stage_query_attempt2.*`。
- 第三次 net 查询展开了过大的 DPU 时钟网负载，手动中止，退出状态 130。保留部分输出 `reports/reset_stage_connectivity_attempt3_partial.txt` 与 partial logs。之后将查询范围限制在指定 DPU pin、reset controller 和关键端点，最终阶段报告退出状态 0。
- 额外对不存在的 `project-spec/meta-user/.../pl.dtsi` 路径做过一次只读查找，返回无文件；按已存在的 PetaLinux 生成文件路径改用 `/home/ghmd/work/petalinux-kv260-dpu/components/plnx_workspace/device-tree/device-tree/pl.dtsi`。未发生源文件改动。
- 曾在库存表中运行一条括号未闭合的只读筛选表达式，`rg` 返回语法状态 2；随后用逐项字符串筛选成功获取关键路径和 hash。无输入/工程变化。
- `rg --files` 对 PetaLinux 项目内部寻找 `pl.dtsi` 的一次搜索未包含生成组件树路径，退出状态 1；已使用实际 `components/plnx_workspace/device-tree/device-tree/pl.dtsi` 作为后续证据。无文件写操作。

## 禁止事项确认

本审计没有烧写、加载 bitstream、重启、复位、读写硬件寄存器、切换时钟/电源、卸载/加载模块、运行模型推理、重编译模型或硬件、重新打包 PetaLinux 镜像、安装软件或下载官方 image。所有本轮新建文件都在本目录。
