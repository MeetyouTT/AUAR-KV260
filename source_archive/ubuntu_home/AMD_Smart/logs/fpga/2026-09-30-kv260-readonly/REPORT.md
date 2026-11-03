# AMD KV260 本次启动只读审查报告

审查日期：Ubuntu 主机本地时间 2026-09-30（America/Los_Angeles）；证据使用主机 UTC 时间，2026-10-01。板端时间错误地停在 2021-11-19，不能用它给操作排序；使用内核单调时间和 `boot_id` 关联本次启动。

**结论：串口已连接，板卡正在运行 PetaLinux 2022.2，当前活动配置为 `kv260-benchmark-b4096`。运行状态与主机指定的 DPU 3.0 镜像中的对应文件相符，但没有足够证据证明自研运动控制和双麦方向逻辑已与 DPU 共存。当前只能列为 DPU 对照基线候选，不能列为项目镜像验收通过。**

本轮保存了 23 个经过序号、gzip CRC、长度和 SHA-256 校验的命令组输出。原始 UART 字节流、命令、主机时间、退出码和恢复后的 stdout/stderr 见 [证据索引](INDEX.md) 和 [机器可读索引](evidence-index.json)。前期存在缺字的抓取保留为不完整证据，没有据此补齐缺失内容。命令组退出码代表组内最后一个命令，组内具体错误仍以原始输出为准。

本轮未烧录 SD/QSPI、升级固件、重启、加载配置、安装软件、修改启动参数、执行推理或驱动执行器。板端 Python 收集程序只在进程内存中暂存、压缩输出；证据和报告写入 Ubuntu 项目日志目录。

## 一、已证实的事实

### 1. 连接、型号、启动与存储

| 项目 | 实际观测 | 证据 |
|---|---|---|
| 串口 | `/dev/ttyUSB1`，稳定路径的 `if01-port0`，115200 8N1；root shell 可执行查询 | 04、05、20 |
| SSH | 板端 IPv6 TCP 22 在监听；主机通过 Wi-Fi 对已知板端 IPv6 地址的 TCP 握手探测超时，未建立 SSH 登录 | 07；host-ssh-banner.json |
| Carrier | FRU：`SCK-KV-G`，part `5066-01`，revision 字段为字符串 `2` | 08 board_qspi |
| SOM | FRU：`SMK-K26-XCL2G`，part `05057-01`，revision 字段为字符串 `2`；4 GB PS DDR4，无 eMMC，无 PL DDR4 | 同上 |
| 运行设备树型号 | `ZynqMP SMK-K26 Rev1/B/A`；compatible 包含 kv260-rev1、kv260-revB、kv260 | 05 live_dt_identity |
| 主启动介质 | FRU 记载 QSPI 512 Mb；内核识别 64 MiB `mt25qu512a`，存在 17 个 MTD 分区 | 05、06、08 |
| QSPI 状态 | A、B 均 Bootable；Requested Boot Image 与 Last Booted Image 都为 A | 08 board_qspi |
| QSPI 标识 | `XilinxSom_QspiImage-k26-v2.1-06140636`；A/B Revision 都为 `K26-BootFW-01.02-06140626` | 同上 |
| SD 卡 | 内核识别 SDXC `SD128`；`/dev/mmcblk1` 为 127,865,454,592 字节，119.08 GiB | 05、06 |
| Linux | PetaLinux `2022.2_release_S10071807 (honister)`；内核 `5.15.36-xilinx-v2022.2`，aarch64，4 核 | 04；09 |
| 根文件系统 | 实际挂载 `/dev/mmcblk1p2`，ext4，约 116 GiB 可用文件系统容量，剩余约 104 GiB | 05 storage |
| 本次启动标识 | `c47f2eb3-afbe-47a5-9633-06edde63b527`，开始、中间和结束一致 | 04、17、18、19、20 |

FRU 的 revision `2` 和设备树型号中的 `Rev1/B/A` 是不同来源的字段。本报告不将它们直接换算为 PCB 丝印版本；物理 revision 的对应关系仍需硬件资料或丝印核对。

SD 分区表为 DOS/MBR，disk identifier `0x40bd38f0`：

| 分区 | 起始扇区 | 扇区数 | 类型、标识 | 当前挂载 |
|---|---:|---:|---|---|
| mmcblk1p1 | 8 | 154590 | FAT32，bootable；LABEL=boot，UUID=045C-A3DD；75.5 MiB | /boot |
| mmcblk1p2 | 154600 | 249582616 | ext4；LABEL=root，UUID=740f013d-325f-4ca0-8b7b-6f398b41e481；约119 GiB | / |

实际 bootargs 与运行设备树 chosen/bootargs 一致：

```text
earlycon console=ttyPS1,115200 clk_ignore_unused root=/dev/ram0 rw init_fatal_sh=1 cma=1536M
```

`root=/dev/ram0` 是本次传给内核的初始参数，最终根文件系统确实是 SD ext4 分区。内核记录 initramfs 启动后挂载 SD 根分区，这与两阶段根文件系统切换相符。它不能被解释为“当前整个系统都运行在 RAM”。本次保存了完整可读的 Linux `dmesg`，但没有本次上电时的 FSBL/ATF/U-Boot 串口日志；不能单凭 `/boot` 文件进一步证明每一步 U-Boot 的实际加载路径。

### 2. 本次 FPGA、overlay 与 DPU

当前加载状态由多个运行接口交叉支持：

1. `xmutil listapps` 报告 `kv260-benchmark-b4096` 活动 slot 为 `0`；`k26-starter-kits` 为 `-1`。
2. configfs 中 `kv260-benchmark-b4096_image_1/status` 为 `applied`，path 为 `kv260-benchmark-b4096.dtbo`。
3. 从运行中的 `/sys/firmware/devicetree/base` 导出设备树：`/fpga-full/firmware-name` 为 `kv260-benchmark-b4096.bit.bin`，存在 `xlnx,zocl` 节点。
4. FPGA manager `fpga0/state` 为 `operating`。
5. ZOCL `xclbinid` 为 `eedb44e9-3f77-0244-9ea9-23b953894638`，与卡上 xclbin 的 UUID 相同。
6. 直接读取 ZOCL 已注册的内存元数据 `ip_layout`，解析得到 **1 个 `DPUCZDX8G:DPUCZDX8G_1`，base address `0xa0010000`**；`kds_numcus=1`，`/proc/iomem` 中存在 `a0010000-a0013fff : CU.3.auto`。

证据：09、10、17、19、20；[实时 IP_LAYOUT 解析](live-ip-layout-decoded.json)。这些运行状态比“某个 bit/bin 文件存在”更有证据力，但仍不等于完整 PL 配置读回。

本轮没有重新执行 `xdputil query`。上轮对同一正在运行的板卡查询成功，返回如下信息；此处属于**前一轮会话工具输出摘录，非本轮重新读取的硬件寄存器**：

| 项目 | 上轮查询返回 |
|---|---|
| DPU 核数 | 1 |
| IP version | v4.1.0 |
| 架构 | DPUCZDX8G_ISA1_B4096 |
| fingerprint | 0x101000056010407 |
| DPU / XRT frequency | 300 MHz / 300 MHz |
| 地址 | 0xa0010000 |

本轮 xclbin 文件元数据还记载 300 MHz / 600 MHz 时钟配置，构建目标为 `hw`。这属于构建描述；本轮没有重新测量 PL 时钟。三份抽查模型的编译目标 fingerprint 都为 `0x101000056010407`，与上轮硬件查询一致，这只能证明抽查模型的目标匹配。

**查询边界修正：**上轮助手将 `xdputil query` 作为只读查询执行，但本次完整内核日志在约 `1082 s` 处显示 `zocl_xclbin_read_axlf ... ret: 0`，以及 context 注册/退出。板端 query.py 调用 `tools.xdputil_query()`；主机 Vitis-AI 3.0 源码显示其初始化 XRT 设备句柄，而相关路径包含 `xclLoadXclBin`。因此不能保证该命令完全不改变驱动运行状态。本轮已避开这一路径。当前 xclbin 文件只有元数据 sections，**不包含 BITSTREAM section**；该注册记录本身不能证明曾重新烧写 PL bitstream。源码、内核原始日志和会话摘录的来源已分开标明。

当前仍有两项读取限制：FPGA manager `firmware` 属性读取返回 `Permission denied`；ZOCL 的 `xclbin_full` 读取返回空内容。因此没有获得“当前完整 xclbin 内存副本”或“完整 PL bitstream 读回”的哈希，不能把空内容 SHA-256 当成已加载配置的哈希。

### 3. 软件栈与运行方式

| 组件 | 本轮实际版本依据 |
|---|---|
| Vitis AI Library | RPM `vitis-ai-library-3.0-r0.0`；库文件 `.so.3.0.0` |
| VART | RPM `vart-3.0-r0.0`；runner、DPU controller、XRT handle 库 `.so.3.0.0` |
| XIR | RPM `xir-3.0-r0.0`；`libxir.so.3.0.0`；已成功仅解析模型文件 |
| XRT | RPM `202220.2.14.0-r0.0`；`xbutil` 返回 2.14.0、2022.2 分支、commit 43926231f7183688add2dccfd391b36a1f000bea |
| ZOCL | 同一 2.14.0 软件栈；模块实际已加载，驱动为 `zocl-drm`，模块 vermagic 与当前内核一致 |
| 管理工具 | xmutil / dfx-mgr / image-update / fru-print 的 RPM 版本为 1.0-r0.0 |
| Python | 板端 3.9.9 |
| 现有模型包 | vai-model-1.0-r0.0 |
| root 中示例应用包 | 抽查文件归属 vai-sample-3.0-r0.0 |

当前采用 **XRT/ZOCL 运行方式**：存在 `/dev/dri/card1` 和 ZOCL 平台设备；没有 `/dev/dpu`；`XCL_EMULATION_MODE` 未设置；XRT 设备报告 Ready=Yes。没有创建推理 runner，也没有执行模型。仅有工具/驱动可用不能作为推理正确性或性能验收。

`dfx-mgr.service` 正在运行，启动日志确认默认固件为 B4096，并在约 `15.6 s` 应用 overlay。`dpu-auto-config.service` 已在本次启动执行完毕，其日志记录自动扩展 ext4 和配置 QoS。脚本已读取、未重新执行。SD 根分区扩展至 119 GiB 与该自动启动行为相符，**不是本轮审查改动**。

RPM 文件校验发现 `/etc/vart.conf` 的大小和摘要与包记录不同；大量其他条目只存在 mtime 差异，不能据此声称库内容都已被修改。当前 `/etc/vart.conf` 指向：

```text
firmware: /lib/firmware/xilinx/kv260-benchmark-b4096/kv260-benchmark-b4096.xclbin
```

主机镜像中对应文件原值为 `/run/media/mmcblk0p1/dpu.xclbin`，所以现卡不能称为完全未经修改的镜像。尚未确认该变化由何人、何时或哪个启动流程产生。

### 4. 外设与自研 IP 的可见性

| 项目 | 观测与边界 |
|---|---|
| 相机 | 无 `/dev/video*`、`/dev/media*`、`/dev/v4l-subdev*`；V4L2 列举没有相机；不能确认硬件是否实际插接 |
| USB | 板端仅列举 root hub 与板载 Microchip USB2734/USB5734 hub；未枚举 USB 相机或 USB 音频设备 |
| 显示 | `/dev/fb0`、DRM 节点存在；card0-DP-1 为 connected、enabled=disabled；已读 EDID 模式包括1024x768；没有执行 modeset 或显示测试 |
| 音频 | ALSA 只有 DisplayPort 两个 playback PCM；`arecord -l` 无 capture 设备；未发现可用 USB/I2S 麦克风采集接口 |
| I2C | `/dev/i2c-1`、`/dev/i2c-2` 存在；已有 EEPROM、PMIC、INA260 等内核实例；没有进行总线地址扫描 |
| GPIO/PWM | gpiochip0/1 存在；pwmchip0 来自 PS 的 ff110000.timer，npwm=3；不能将其认定为自研舵机 IP |
| UIO | uio0–3 的名称都是 axi-pmon，资源对应 PS 性能监测；没有证据支持它们是自研控制 IP |
| DMA | `/dev/dmaproxy`、dmaproxy 模块存在；未运行 DMA 测试；不能单凭它认定运动/音频自研逻辑已加载 |
| 项目自研 IP | 实时设备树、资源映射和 XRT IP_LAYOUT 中未找到可核验的运动控制、双麦方向判断接口或版本寄存器定义 |

自研逻辑可能未被设备树或 XRT 元数据描述，因此“没有找到接口”不能严格证明这些逻辑在 PL 中绝对不存在。但当前没有项目 XSA/HWH、寄存器表或安全只读版本寄存器可供核对，**不能作出共存验收结论**。未使用 `/dev/mem`，也未读可能存在 read-clear 行为的未知执行器寄存器。

### 5. 健康状态、模型与应用来源

在当前近空闲工况，AMS 三路温度为约 34.65°C、34.02°C、34.70°C；INA260 U14 的 Linux hwmon 读数为 5060 mV、1075 mA、5440000 µW，即约 **5.06 V、1.075 A、5.44 W**。这是该 SOM 供电监测点的瞬时读数，不是 12 V 电源插口或整机满载功耗测量。AMS 电压通道缺少名称标签，未把未知通道的 0 值解释为欠压。没有负载测试、外部电源纹波测量或完整 PMIC 告警寄存器读取。

板端清点的 2327 个文件包含 297 份 `.xmodel`，其中 291 份位于 `/usr/share/vitis_ai_library/models`，另有跨平台参考示例模型。完整路径和大小已保存；不能认为所有模型都适配 KV260。

抽查 densebox_320_320、resnet18、yolox_nano_pt：

- 仅调用 `xir.Graph.deserialize` 读取编译图，未导入 VART runner 或调用硬件。
- DPU 子图架构均为 `DPUCZDX8G_ISA1_B4096`，fingerprint 为 `0x101000056010407`；部分子图由 CPU runner 执行。
- 三份模型文件与主机镜像中的对应文件 SHA-256 一致；抽查 resnet50 示例二进制和 main.cc 也一致。
- 模型文件归属 vai-model 包，示例二进制归属 vai-sample 3.0 包。这提供分发来源证据，但未获得每个模型独立的训练数据、量化和编译完整 manifest。

证据见 16、18 和 [样例对照](host-model-sample-comparison.json)。现有进程和 CU 使用统计未显示正在运行项目推理/控制应用；这是采样时点的观测。

## 二、Ubuntu 主机文件与板端状态的区分

Ubuntu 主机为 20.04.4 LTS / x86_64，内核 5.15.0-139-generic；这不是板端操作系统。主机有 Vivado/Vitis 2022.2 安装目录和 PetaLinux 2022.2 的版本声明，本轮未启动构建或证明其完整可用性。

| 主机文件 | 大小、检查结果 | 能证明什么 |
|---|---|---|
| 下载/xilinx-kv260-dpu-v2022.2-v3.0.0.img.gz | 3,503,938,277字节；gzip 完整读取，CRC通过 | 本地压缩文件可完整解压 |
| 对应 .img | 9,482,799,104字节；流式解压摘要与它完全相同 | .gz 与本地 .img 内容一致 |
| starterkit v2022.2 BSP | 1,964,061,022字节；已记录文件信息 | 文件存在，不证明生成或部署了项目镜像 |
| Vitis-AI-3.0.zip | 94,706,160字节；已记录摘要和7890项目录 | 源码/示例归档存在，不等于项目的已构建硬件 |

压缩镜像 SHA-256：`a8599cc033920207953a3eb954be1b925465e77c3ca835b26ef1ccfa903441d0`；解压镜像 SHA-256：`b5de568c8f008dd251cdc3c7fcc0b3942e973e752943152628519768f845aa9c`。本轮没有取得独立的发行方校验值，**这些摘要用于本地身份和后续对照，不能独立认证下载来源**。

不挂载镜像、不使用 loop 或 chroot：通过 mtools 读取 FAT，通过只读 ext4 inode/extents 解析读取选定 rootfs 文件。结果：

- 板端 `/boot` 五个文件均与本地镜像对应文件摘要相同。
- B4096 的 bit.bin、dtbo、xclbin、shell.json 四个文件均相同。
- os-release、fstab、dpu-auto-config 脚本相同；vart.conf 不同。
- 三份模型和两份示例程序/源码样例相同。
- SD 分区标识、第一分区起点和大小相同；板端第二分区已扩展。

详见 [文件对照清单](host-board-file-comparison.json)、[镜像 rootfs 读取结果](host-image-root-files.json)、[gzip 校验](host-gzip-integrity.json)。这组结果支持“当前活动 B4096 环境与指定对照镜像相符”，并明确保留“不能证明整张 SD 原样复制、不能做 PL 字节读回认证”的限制。

在 `/home/ghmd` 的非隐藏用户目录搜索中，排除了厂商安装目录、snap、代理目录和本次证据目录，未找到项目 XSA/XPR/bit/xclbin/dtbo/HWH/BD、RTL 或 PetaLinux config.project。归档里的官方参考模型另列，不将其当作项目产物。`AMD_Smart/plan/active` 开始时为空，参考方案是 FMQL 平台的旧资料，不能替代当前 KV260 的地址表。搜索范围和原始结果已保存为 host-build-artifact-search.json，**不意味着其他挂载位置、隐藏目录或远端没有工程**。

版本组合 2022.2 / Vitis AI 3.0 与 AMD 的[官方兼容说明](https://xilinx.github.io/Vitis-AI/3.0/html/docs/reference/version_compatibility.html)一致；指定 KV260 镜像名也列于[官方 Vitis AI Library 3.0 版本说明](https://docs.amd.com/r/3.0-English/ug1354-xilinx-ai-sdk/Vitis-AI-Library-v3.0-Release-Notes)。这属于参考依据，不能代替本报告的板端实测证据。`bootfw_status` 的读取用途参考 [xmutil 官方说明](https://github.com/Xilinx/xmutil)。

## 三、发现的不匹配与异常

| 发现 | 已证实的影响和处理边界 |
|---|---|
| 没有 IPv4 和默认路由 | 网口1 Gbps物理链路正常，DHCP已配置但未取得地址；wait-online超时，dashboard因无IP退出；原因不能仅凭现有日志确定。未重启网络或设置地址 |
| 板端时间为2021年 | 日期与主机相差多年；日志绝对时间、网络时间同步和依赖时间的应用可能受影响。未改时钟 |
| /boot FAT未正常卸载 | 内核明确警告；尚未证明文件损坏，抽查五个启动文件摘要正确。未在已挂载分区执行修复或 fsck |
| fstab重复/boot项 | LABEL=boot 与 /dev/mmcblk1p1 双项，systemd generator实际报duplicate；同样重复已存在于主机镜像，不能归因为本轮改动 |
| /etc/vart.conf与镜像及RPM记录不符 | 固件路径已指向B4096包；当前路径实际存在且UUID可核对，变化来源未知 |
| QSPI版本与SD软件版本不是同一标识 | 已读得旧式BootFW-01.02标识；不能因为Linux是2022.2就宣称QSPI也已升级到2022.2。未更新固件 |
| NFS失败 | proc-fs-nfsd.mount失败，NFS服务依赖受影响；与root终端/DPU枚举成功是不同检查结果 |
| TPM self-test error 256 | 安全模块自检异常，根因和对TPM用途的影响未验证；不据此认定DPU不可用 |
| 时钟设置失败 | dpdma_ref_div1、dpll_int返回-13；SDIO时钟设置出现-16；显示输出未启用。不能直接确定均由QSPI版本引起 |
| MTD User分区被截短 | 设备树声明超出实际QSPI末端，内核截为0x1d60000；未验证User分区用途，也未写入 |
| overlay卸载内存泄漏警告、ZOCL IRQ index 8 not found | 内核有实际警告，活动overlay已应用，XRT枚举成功；未卸载overlay或做压力/中断测试 |
| FUSE模块缺失、ALSA restore失败 | 日志出现fuse模块找不到、alsactl restore退出99；未安装或调整音频配置 |
| last_reset_reason读取返回Invalid argument | 不能确认本次复位原因；不是已经证实发生供电复位 |
| 早期串口抓取缺字 | 持续接收和校验后23组输出完整；不能凭前期采集方式的问题认定板卡USB/UART硬件故障 |

本次完整内核日志未见明确 SD/MMC I/O error、EXT4 error、kernel panic、过热或掉电告警。但这仅涵盖当前可读日志和空闲传感器采样，不是存储、供电、温度或长时间负载的全面通过证明。

## 四、尚无法确认的事项

1. 上电启动阶段各固件实际的完整版本链、U-Boot执行路径和物理PCB revision与FRU字段的对应关系。
2. 当前PL配置字节与镜像bitstream的逐字节一致性；本轮没有配置读回。
3. 本轮重新读取的硬件fingerprint/时钟：保留上轮查询来源；本轮只确认活动overlay和CU元数据。
4. 自研IP是否以未描述节点的方式藏在PL内；没有项目工程、硬件manifest、寄存器表或安全版本寄存器证据。
5. DPU模型实际推理的数值正确性、延迟、吞吐、DDR竞争、与运动/双麦逻辑同时运行的稳定性。
6. 相机、麦克风的实际插接与功能；显示画面是否正常；SSH实际认证连接。
7. QSPI旧固件与现Linux组合的全部兼容性、TPM/时钟/存储警告根因、12V电源和执行器负载下供电情况。
8. 全部现有模型/应用的独立来源、精确编译版本和是否运行过；本轮只完成目录盘点、包归属和代表样例摘要/图元数据核对。

## 五、下一步最小验证步骤

| 步骤 | 目的 | 是否涉及改变板卡状态 |
|---|---|---|
| 提供当前项目XSA/HWH、block design/RTL、寄存器表和待部署模型manifest，在主机离线核对 | 确认DPU、运动控制和双麦逻辑属于同一硬件设计；核对地址、时钟/复位、AXI带宽、引脚和安全只读版本寄存器 | 主机读取即可；当前工程材料不足 |
| 核对网线拓扑和上游DHCP服务 | 查明“有物理链路、无IPv4”的原因 | 读取路由器/主机状态可继续；改IP、renew或重启网络需另行授权 |
| 选已核对fingerprint的现有模型和固定输入，执行一次短推理并与CPU参考结果比较 | 把“基线候选”升级为有数值正确性证据的DPU基线 | **会创建XRT context、分配buffer、写DPU控制寄存器，故本轮未执行**；执行前需明确授权 |
| 获得自研IP只读版本寄存器定义后，只读查询ID/版本并与manifest对照 | 在保持当前配置条件下查证共存接口；禁止以名称或文件存在替代验证 | 需先确认读取不触发read-clear/FIFO pop等副作用；当前未执行未知MMIO |
| 后续维护时离线检查FAT并复核启动日志 | 确认异常卸载的实际影响、补齐早期启动链证据 | 卸载、重启、修复、QSPI更新都超出当前授权；本轮停在读取和摘要对照 |

现有摘要对照已足以避免把“先重新烧一遍卡”当作当前盘点的必要步骤。后续项目镜像应保存一份可追溯的硬件manifest，包含同一构建产生的bit/DT/xclbin摘要、DPU fingerprint、自研IP ID与地址、VART/XRT版本，以及资源/时序报告；部署与带执行器测试属于后续独立授权阶段。
