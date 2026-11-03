# KV260 2022.2 官方参考平台核验与构建记录

记录日期：2026-09-30 至 2026-10-01。工作区：`/home/ghmd/kv260-reference-2022.2-20260930`。未修改全局 shell 配置、固定源码或板端固件；按用户授权，仅向现有 Vivado 2022.2 安装增补了 MPSoC 器件支持。

## 结果

**最终状态：官方 KV260 2022.2 参考 platform 与 B4096 benchmark overlay 均已原样构建成功。** 安装器记录显示原环境有 Kria SOM 支持、缺少通用 Zynq UltraScale+ MPSoC 器件模块；只增补该模块后，原先失败的同一 K26 Clocking Wizard 探针通过，Clocking Wizard 输出产品与最小综合通过，随后 platform 和 overlay 阶段均成功。固定源码 commit 未变，厂商 Tcl、速度参数和官方时钟模块未修改。实现时序满足约束；完整日志、产物、关键报告与 SHA-256 清单见 [REPAIR_REPORT.md](REPAIR_REPORT.md) 和 `evidence/final_build/`。本轮没有向板卡部署或烧录。

## 主机与工具实测

| 项目 | 实测值 |
| --- | --- |
| 系统 | Ubuntu 20.04.4 LTS，x86_64，Intel Core Ultra 5 125H，18 个可用逻辑 CPU |
| 内存 | 30 GiB RAM，15 GiB swap；核验时约 23–25 GiB available |
| 文件系统 | `/home/ghmd` 位于 ext4；本轮完成后可用 169 GiB、可用约 2071 万 inode；工作区约 29 GiB |
| Vivado | `/home/ghmd/Xilinx_2022.2/Vivado/2022.2/settings64.sh`；v2022.2，SW 3671981，IP 3669848 |
| Vitis | `/home/ghmd/Xilinx_2022.2/Vitis/2022.2/settings64.sh`；`v++` v2022.2，SW 3671529；包含 `xsct`、`bootgen`、`dtc`、`cmake` |
| PetaLinux | `/home/ghmd/petalinux/2022.2/settings.sh`；`PETALINUX_BASE_VER=2022.2`；环境检查通过，仅提示未找到 TFTP server |
| 板卡/器件 | Vivado 能列出 `xilinx.com:kv260_som:part0:1.4`、`xck26-sfvc784-2LV-c`、`xck26-sfvc784-2LVI-i` |
| 增补组件 | Vivado ML Standard 配置只选择 `Zynq UltraScale+ MPSoC`；安装记录键为 `Zynq_MPSoC_WP`，并保留 `Xilinx_Kria_Som` |
| 系统依赖 | `build-essential`、`flex`、`bison`、`libssl-dev`、`git`、`python3` 已安装；系统 PATH 无 `dtc`/`cmake`，Vitis 环境中有 |

硬件构建只在当前进程加载 Vitis `settings64.sh`。PetaLinux 核验在另一个 shell 加载其 `settings.sh`；不要在同一进程叠加两套设置。无 PetaLinux 工程，故未运行 OS 镜像构建。`xsct` 需使用 `-nodisp` 避免本机无 DISPLAY 时的图形启动问题。`vivado -version`、`v++ --version`、PetaLinux 环境脚本和器件枚举成功并不等于综合、实现或许可验收。

## 官方源码与构建入口

| 来源 | 固定点 |
| --- | --- |
| `Xilinx/kria-vitis-platforms`，`xlnx_rel_v2022.2` | `a3a83f179503792226adf83082aee7c05de620b4` |
| 子模块 `kv260/overlays/Vitis_Libraries` | `a60e1df95fa43e715cc9223f470587456463be8b` |
| `Xilinx/kria-apps-firmware`，`xlnx_rel_v2022.2`，仅作部署格式对照 | `1592956c9119ebf77222d3050a22c326a3adbfc2` |

官方入口是 `make -C src/kv260 platform PFM=kv260_ispMipiRx_vcu_DP JOBS=4`，成功后再执行 `make -C src/kv260 overlay OVERLAY=benchmark JOBS=4`。本机用 `run_reference_build.sh` 只负责加载 Vitis 环境、传入上述参数及 `XSCT=".../xsct -nodisp"`；未改官方 Makefile。`JOBS=4` 是针对 30 GiB RAM 的保守并行度。

`OVERLAY=benchmark` 在官方顶层 Makefile 中固定到 `kv260_ispMipiRx_vcu_DP` 平台。DPU 来自仓库 `kv260/overlays/dpu_ip/DPUCZDX8G_v4_0_0`（IP 元数据版本 4.0）；`benchmark/dpu_conf.vh` 启用 B4096 和 URAM，`prj_conf/prj_config_1dpu` 指定一个 `DPUCZDX8G_1`、300/600 MHz 时钟，以及 HPC1/HP1/HP3 内存连接。overlay 的 Makefile 用 Vivado 封装 DPU XO，再由 `v++ --link` 生成 `binary_container_1/dpu.xclbin`；成功时 `package` 把 `.hwh`、`arch.json`、`.bit`、`.xclbin` 复制到 `binary_container_1/sd_card`。这些步骤本轮均已完成，产物路径和大小列在下文。

## 首次核验与排障证据（修复前）

1. `git clone --depth 1 --branch xlnx_rel_v2022.2` 和 `git submodule update --init --depth 1` 成功；源码无受跟踪文件修改。
2. Vivado 器件和 IP 枚举成功，见 `logs/vivado_check_v2.log`。其他未安装器件的板卡定义产生 `Board 49-26` 警告，KV260 板卡可用。
3. 原样平台构建命令 `bash run_reference_build.sh platform > logs/platform.log 2>&1` 返回 2；受限环境外相同命令返回 2，见 `logs/platform_outside_sandbox.log` 和 `logs/platform_vivado.log`。
4. 第一处致命报错：`expected floating-point number but got "Unable to get value from speedsfile for keyword MM"`；随后 `IP_Flow 19-3476`、`BD 5-7` 指向 `clk_wiz_audio` 的 `create_bd_cell`。失败发生于 XSA 生成之前。
5. `evidence/probe_clk_wiz.tcl` 独立创建 K26 `clk_wiz` 也失败；仅加载 Vivado、C locale、干净进程环境均重现，见对应 `logs/probe_clk_wiz*.log`。目前只能定位到该 Vivado 安装/运行环境下的时钟 IP 速度模型查询异常，尚不能断言具体文件损坏或许可原因。
6. 官方固件参考仓库的预编译 BIT 使用 `bootgen` 转为 BIN，DTSI 使用 `dtc` 编译为 DTBO，`make ... install DESTDIR=...` 本地暂存成功，见 `logs/official_firmware_packaging.log`、`logs/official_firmware_staging.log`。这并非本轮 DPU 重新综合的结果。

## 对照固件的重要差异

官方 2022.2 *固件参考仓库* 中的 `kv260-benchmark-b4096.xclbin` 经 `xclbinutil --info` 显示：`v++ 2022.1`、Vivado 2022.1 平台、一个 `DPUCZDX8G_1` CU，基址 `0xa0010000`，XCLBIN UUID `58e67848-75ea-02f9-bbb1-a7904fffe459`。这与本轮 2022.2 源码和用户所述板端 Vitis AI 3.0 镜像都不能直接证明同源；仅 CU 地址相同不足以判定位流相同。

官方固件参考仓库的 Makefile 生成并暂存 `kv260-benchmark-b4096.bin`，但对应 DTSI 中 `firmware-name` 是 `kv260-benchmark-b4096.bit.bin`。本地暂存包保持上游原样，因此**不能直接据此判定可加载**；后续制作测试卡时必须使设备树中的固件名与实际文件名一致，并确认 XCLBIN、BIT、DTBO 对应同一设计。

本轮生成了新的 XSA/XPFM/XO/XCLBIN/BIT、HWH、`arch.json`、路由后资源占用和时序报告；它们均来自这次固定 commit 的构建，不包括 `staging` 中的预编译固件。最终交付物 SHA-256 在 `evidence/final_build/ARTIFACTS.sha256`。安装器原始日志保留在 `evidence/installer/`；交付目录中的匹配副本已遮盖邮件地址。

## 构建与当前限制

安装记录原先没有 `Zynq UltraScale+ MPSoC` 器件模块，而 K26/KV260 能枚举并不足以证明 Clocking Wizard 的速度模型数据可用。使用 AMD 2022.2 安装器生成 Vivado ML Standard 配置，仅选择 `Zynq UltraScale+ MPSoC`，对现有 `/home/ghmd/Xilinx_2022.2` 执行 Add 后，安装记录新增 `Zynq_MPSoC_WP`。同一独立 `clk_wiz` 探针随后成功，新增器件支持是这次故障的已验证修复。详情、前后日志及安装器官方依据见 [REPAIR_REPORT.md](REPAIR_REPORT.md)。

`platform` 和 `overlay` 在受限运行中分别遇到本机 HLS/Vitis 工具申请本地端口被系统拒绝；两次完整重跑在沙箱外成功完成。这是执行环境权限差异，不是构建设计错误。安装仍是 Vivado ML Standard：K26/KV260 所需的当前构建已验证；ZCU102 的通用器件定义仍未枚举，本轮不以 ZCU102 为构建目标。版图、时序和警告情况见 [REPAIR_REPORT.md](REPAIR_REPORT.md)。

## 独立测试卡部署与复跑方案

1. 在原官方卡上只读记录当前 `/lib/firmware/xilinx/kv260-benchmark-b4096/` 各文件 SHA-256、`xmutil listapps`、`xdputil query`、模型 XMODEL 与萨摩耶原图 SHA-256、Vitis AI/XRT 运行时版本，并保留原推理命令、预处理参数、线程数与完整输出。用户此前报告的对照值为 Top-1 0.949879、1 线程 214.381 FPS、2 线程 238.479 FPS；本次主机核验未独立复测。
2. 以相同 PetaLinux 2022.2 系统镜像制作另一张 SD 卡，并确认其 XRT/ZOCL、dfx-mgr、Vitis AI 运行时与模型可用。原卡保留。
3. 修复工具并重建成功后，从同一次新构建取得 BIT 与 XCLBIN，按官方 `bootgen` 方法转 PL 二进制；按新 XSA/实际硬件连接核对或生成 DTBO。使用 `XRT_FLAT` 的 `shell.json`，给测试应用设置独立目录和一致的 BIT/DTBO/XCLBIN 基名，核对 DTSI `firmware-name`。测试前比较 XCLBIN 架构、时钟、CU 数和地址与模型要求，不能混用参考仓库预编译文件。
4. 只在测试卡系统上安装新 bundle 并通过 `xmutil` 切换；确认 `xdputil query` 显示一个预期 CU，再使用**完全相同**的 ResNet18 XMODEL、图片、预处理和单/双线程命令复跑。记录 Top-1、分数、FPS、日志与加载固件哈希，并与原卡数据逐项比较。若有差异，先核对 XMODEL/DPU 架构指纹和运行时版本，再分析硬件性能。
5. 测试结束可换回原卡恢复基线；本轮没有执行烧录、重启或板端部署。

## 官方资料

- [AMD PetaLinux 2022.2 安装要求](https://docs.amd.com/r/2022.2-English/ug1144-petalinux-tools-reference-guide/Installation-Requirements)
- [Kria Vitis platforms 固定提交](https://github.com/Xilinx/kria-vitis-platforms/tree/a3a83f179503792226adf83082aee7c05de620b4/kv260)
- [Kria apps firmware 固定提交](https://github.com/Xilinx/kria-apps-firmware/tree/1592956c9119ebf77222d3050a22c326a3adbfc2/boards/kv260/benchmark-b4096)
- [AMD Kria 运行时固件格式和 xmutil 说明](https://xilinx.github.io/kria-apps-docs/creating_applications/2022.1/build/html/docs/target.html)（文档标注 2022.1；实际 2022.2 仓库内容已逐文件核对）
