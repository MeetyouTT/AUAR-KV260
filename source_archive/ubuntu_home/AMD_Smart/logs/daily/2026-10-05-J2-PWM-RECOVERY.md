# 2026-10-05：J2 PWM 板卡恢复与电脑端调试权限

承接 2026-10-04 J2 PWM 日志、项目 ZIP README/A06/A12 和当前板测状态。用户以“好了”确认电脑与板卡间 USB 串口线已重插；随后固定串口只读检查仍未返回 root 提示符，原始日志 0 字节、目标任务命令 0 条，证据为 `kv260-j2-pwm-20261004/evidence/20261005T065751.089181Z-pwm-uart-readonly/`。此项发生于 2026-10-04 23:57 PDT，本日志承接跨日的后续诊断，不把 USB 重插当作系统已恢复。

新增 `scripts/jtag_readonly.py` 和 `scripts/jtag_readonly.tcl`：仅通过本机临时硬件服务器枚举处理器/JTAG 目标，服务器监听 `127.0.0.1:3127`、关闭 GDB 监听，结束时关闭自己创建的进程；没有选择、暂停、复位处理器、内存访问或 FPGA 下载。Python 语法检查通过。第一份 Tcl 漏了 `puts`，结果没有显示返回列表，不能据此判断目标不存在；修正为 `puts [targets]` 和 `puts [jtag targets]` 后重复检查。

修正后的证据在 `evidence/20261005T070141.075170Z-jtag-readonly/`。目标列表为空，同时实际发现电脑端 Xilinx USB 总线设备 `/dev/bus/usb/003/006` 为 root:root、模式 0664，ghmd 用户不具有读写访问权限；电脑端没有安装配套 Xilinx FTDI udev 规则。现有串口节点权限和 USB 总线设备权限不同，因此该权限问题阻止 JTAG 进一步诊断，但不能用它解释此前 UART 无返回的直接原因。尝试 `sudo -n python3 -B .../scripts/jtag_readonly.py` 被系统拒绝，输出 `sudo: 需要密码`，管理员检查未执行。没有修改 udev、权限或驱动配置。

当前需用户在 Ubuntu 电脑终端执行 `sudo python3 -B /home/ghmd/kv260-j2-pwm-20261004/scripts/jtag_readonly.py`，在本地终端完成管理员认证。此项用于获得可用的只读调试证据，不自动复位、登录、刷新 SD/QSPI 或运行 PWM。当前 Linux 恢复、新 C 访问器上板、外部 PWM 波形均未通过；旧客户端仍阻止继续启动。

厂家参考：[XSCT 目标连接与查询](https://docs.amd.com/r/2024.1-English/ug1209-embedded-design-tutorial/Setting-Up-the-Target)、[KV260 官方 Linux 串口设置](https://github.com/Xilinx/Xilinx_Kria_KV260_Workshop/blob/main/Linux%20set-up.md)。本机工具的 `52-xilinx-ftdi-usb.rules` 说明 USB 总线读写权限要求；未安装该规则。

## 用户执行管理员检查后的实际结果与临时权限方案

用户回复“执行完了”，新证据 `evidence/20261005T070509.654725Z-jtag-readonly/` 确认管理员运行时 USB 读写权限为 true，但 XSCT 返回 `ftdidb_lock failed: FTDMGR wasnt properly initialized`，退出码 1；尚未获取处理器或 JTAG 列表。不能把完成用户命令当作板卡检查通过。该初始化失败的直接原因未证实，未删除共享文件。

增加只读主机诊断及 `strace`、硬件服务器 discovery/jtag 日志；改为随机 localhost 端口，避免上一轮连接遗留状态使固定端口预检查误报占用；临时服务器使用自己的进程组并在结束时关闭。Python 语法通过。一次固定端口检查失败证据保留于 `evidence/20261005T070724.002804Z-jtag-readonly/`；改为随机端口后证据为 `evidence/20261005T070837.424027Z-jtag-readonly/`。

普通 ghmd 用户下，系统调用日志显示 `/dev/shm/digilent-adept2-mtx-ftdmgr` 与 `/tmp/digilent-adept2-shm-ftdmgr` 打开成功，实际打开 `/dev/bus/usb/003/006` 返回 `EACCES`；目标列表为空。已定位普通用户 JTAG 检查的电脑端 USB 权限阻塞，但仍未解释 UART 无返回。准备的最小修正是 `sudo /usr/bin/setfacl -m u:ghmd:rw /dev/bus/usb/003/006`：只给当前插着的一个 KV260 USB 总线设备添加 ghmd 读写 ACL，不修改永久 udev/驱动、共享文件或板卡配置。已尝试非交互执行，仍被 `sudo: 需要密码` 阻止，ACL **未应用**。需用户在本机终端完成这条命令，之后助手以普通用户重新查询目标；不再要求以 root 运行调试库。

本轮改动文件：`scripts/jtag_readonly.py`、`scripts/jtag_readonly.tcl`、`BOARD_BRINGUP_STATUS.md`、`CURRENT_BENCH.json` 与本日志。Linux 恢复、新访问器 MMIO 和外部波形仍未验证。

## 临时 USB 权限生效与实际板卡识别

用户以“好了”确认执行临时 ACL 命令。普通 ghmd 用户运行调试查询实际确认 USB 读写权限 true，列出 `Xilinx X-MLCC-01 XFL1EMEBC1R5A`、`xck26` IDCODE `04724093`、`arm_dap` IDCODE `5ba00477`，四个 Cortex-A53 显示 Running；证据 `evidence/20261005T072111.603534Z-jtag-readonly/`。电脑端 JTAG 访问已通过，不把 Running 当作 Linux 已恢复。随后 UART 检查仍为 0 字节、无 root 提示符，目标任务命令 0 条（`evidence/20261005T072153.126640Z-pwm-uart-readonly/`）。

为只读诊断增加 `--uart-registers`，核对实际既往启动记录中 `ttyPS1` 映射 `0xff010000`，对照 Vitis 2022.2 自带 Xilinx `uartps_v3_11/src/xuartps_hw.h`。仅在期望电缆/K26 出现后选择 PSU 目标，通过调试口读取 UART1 CR/MR/IMR/BAUDGEN/SR/BAUDDIV；不读取有消耗数据副作用的 FIFO，不写任何寄存器，不暂停或复位核心。证据 `evidence/20261005T072418.377668Z-jtag-readonly/`：CR=`0x114`，MR=`0x20`，IMR=`0x2161`，BAUDGEN=`0x7c`，SR=`0x8`，BAUDDIV=`0x6`；CR 的 TX_EN/RX_EN 均置位，SR 的 TXEMPTY 置位、RXEMPTY 未置位。可确认串口已启用且接收缓冲有数据，但不能仅凭这些读值确定内核停在哪条指令，也不能认定之前物理断电确已恢复了系统。

下一步开启 UART 启动监听，由用户按 KV260 板上 RESET/SW2 进行一次复位并等待启动。复位是待执行现场步骤，助手未通过 JTAG 复位、刷新 SD/QSPI、切换 PL 或发送 PWM。新 MMIO 访问器和外部波形仍未验证。

## RESET/SW2 后 Linux 实际恢复

用户明确反馈“已按复位并等待”。本次 UART 在监听期间捕获 FSBL、U-Boot、Linux 至 root 提示符，FSBL 显示 `Reset Mode: System Reset`，U-Boot 显示 `Reset reason: SOFT`；不是已确认断电的冷启动。证据 `evidence/20261005T072733.549866Z-pwm-uart-readonly/`，原始记录 58,044 字节。只读三阶段命令均返回 0、帧 SHA 校验通过，控制台回显恢复。

目标仍为原 SD CID，Linux `5.15.36-xilinx-v2022.2`；新 boot ID `50909139-fa62-4afc-9243-a2438d57293f`，初读 uptime 29.08 秒，确认是新启动且 Linux 可响应。官方 `kv260-benchmark-b4096` 自动活动，FPGA manager operating，dfx-mgr active/PID 1014；四份官方工件哈希与之前保护值一致，`/etc/vart.conf` 仍为官方 xclbin 路径。目标 `glibc 2.34` 和 AArch64 ELF 加载器存在，满足新访问器所需版本。官方配置下 PL0/UART1 实际读回均为 99,999,999 Hz；不是候选加载后测值。

新归档本机 SHA 复核通过，六阶段远端源语法及实际串口线长核验通过（最长 LOAD 3593 字节，EXTRACT 3564 字节，均小于 3800）。已开始将 57,417 字节修正包传到新暂存目录；上传、重新加载及新 C 写访问尚未宣称完成。旧 START 的直接故障根因仍未最终确认。外部 PWM 波形尚未验证。

## 修正客户端无 PWM 板测通过

57,417 字节修正归档共 48 帧 UART 上传完成，板端整体 SHA 与本机一致，终端回显恢复；新暂存路径 `/home/root/aura-pwm-probe-stage/20261005T073059.065037Z/aura-pwm-probe-stage.tar.gz`。准备/解包/复用校验安装/卸载官方/加载候选五阶段均通过（`evidence/20261005T073342.186703Z-uart-load-idle/`），新 AArch64 ELF 无参数入口先返回用法/退出码 2，确认目标运行库可执行且此入口无 MMIO。新程序只读身份、BUILD_ID、固定参数、status=4/frames=0 和 PL0 实际 99,999,999 Hz 均通过。当前 PL 为 `aura-pwm-probe`，官方 DPU 临时卸载，尚未恢复。

SCRATCH 完整 32 位模式 `0x12345678`、`0xa55a3cc3` 写读及原值恢复通过，控制状态保持禁能（`evidence/20261005T073601.448435Z-uart-scratch/`）。随后 STOP 完整 32 位写控制寄存器及读回通过（`evidence/20261005T073647.959523Z-uart-stop/`），最终 status=4/frames_left=0，Linux 和串口保持响应，均未发送 START。新客户端的字写访问已有实际板测支持，但这不等于第一次故障原因已最终证明，或 PWM 已实测合格。

修改 `scripts/uart_burst.py`，要求 START 前本次加载会话的 SCRATCH/STOP 状态均通过、归档与加载证据一致；每次普通操作还校验启动 boot ID 与加载前一致、原官方工件哈希不变。控制动作失败时阻止后续直接续测。Python 及远端源语法检查通过，实际动作串口命令长度 3623 字节，小于 3800。未改变 RTL、位流或归档客户端内容。更新 README、测量指南、板测状态和日志，将历史故障与当前实测区分。

现场下一步：舵机保持拔下，恢复供电板和隔离模块两侧供电，让 UNI-T CH1（VOB/GND2）在 5 ms/div、2 V/div、上升沿、2.48 V 单次等待。已请求用户明确就绪反馈，尚未收到本轮确认，未发送 START；不能以先前等待或默认选项代替确认。验收波形后再恢复原官方配置。

## 修正访问器首次 START 与外部波形待确认

用户随后回复“已等待”，执行一次有限 START。`evidence/20261005T074247.954619Z-uart-start/` 记录退出码 0、客户端耗时 1.303537207 秒、boot ID 仍为 `50909139-fa62-4afc-9243-a2438d57293f`、最终 status=4/frames_left=0、输出寄存器为低，控制台回显恢复。程序启动控制与结束检查通过，没有记录新的内核崩溃；程序耗时不等于外部脉冲持续时间，未据此验收 50 帧。

用户提供 `/home/ghmd/图片/65BDDB30782456C8B88E484B04A644CF.jpg`（SHA-256 `a5add7f6f148db5033b67c4fb9514de3043aed6c04d56d46d3f5a197ddaf46ac`），可见 STOP、5 ms/div、2 V/div、10×、CH1 单次上升沿触发 2.48 V 和接近水平的蓝色轨迹。照片未能清晰辨认重复矩形脉冲。用户纠正“有波形”，已修正助手“没有波形”的过强表述，询问现场所见形态；保留外部验证为 false，不把轨迹存在当作目标周期/脉宽通过，也不据照片判定无信号或隔离器故障。暂不移动探头或重新 START，舵机保持拔下。

修正 host 控制器成功 START 后未同步 `CURRENT_BENCH.start_sent` 的状态遗漏；当前总状态更新为 true，加载时 `loaded_idle.start_sent=false` 保留历史事实。同步更新 README、板测状态和测量指南。RTL、位流、板端归档及冻结的离线身份文件未修改。候选仍占用 PL，原官方应用尚未恢复。

## 隔离器输入端第二次有限 START

用户要求继续处理，指导其先取下 CH1 探头尖和地夹，再改接 VIB/GND1，避免跨接两侧地；舵机保持拔下，改为 1 V/div、5 ms/div、约 1.6 V、CH1 单次上升沿触发。用户回复“输入端已等待”，这是现场就绪报告，不是助手独立核实接点或电压。

运行 `scripts/uart_burst.py start` 完成，证据 `evidence/20261005T081349.970765Z-uart-start/`，退出码 0，结果 SHA-256 `7ed8062406dfee7d85ec52f578a2a705e8559b73978cb6918852ce199f9df718`；boot ID 不变，客户端耗时 1.303362466 秒，最终 status=4/frames_left=0、输出寄存器为低、回显恢复。更新当前物理状态报告和板测状态；未改位流/RTL/板端归档。外部输入端照片尚待提供，周期、脉宽及帧数仍未验收，未继续自动发脉冲或连接舵机。下一步读取本次冻结画面，再定位输入/输出链路。

用户随后报告“我看不到什么也没有”，输入端仍未取得可验收波形，没有本轮截图。复核 CURRENT_START 仅确认程序成功与结束读回，未重复发送 START 或改变板端配置。查阅 UNI-T 官方 UTD2000 系列手册功能检查/探头补偿：CH1 探头接自身 PROBE COMP 输出与地、倍率匹配 10×，按 AUTO 应显示约 3 Vpp 的重复方波，默认 1 kHz（频率可配置）。已将此检查作为下一步现场步骤写入测量指南和状态，检查本身尚未执行/验收。应先取下项目电路上的探头尖及地夹，舵机保持拔下；不据用户无波形报告认定 FPGA 或隔离器故障。

## 用户要求重新设置并再次启动

用户要求暂缓并重新选择示波器选项，按当前输入端 VIB/GND1 给出 CH1 DC 1 MΩ、全带宽、粗调、本体及软件 10×、1 V/div、5 ms/div、CH1 边沿/DC/单次/上升、约 1.6 V 触发设置。随后用户明确要求“你重新给一个波形”，执行第三次有限 START；本轮重新设置后是否已进入单次等待尚未明确报告，已提示 STOP 时需先按 RUN/STOP。

证据 `evidence/20261005T082114.174627Z-uart-start/`，退出码 0、结果 SHA-256 `db643aa50c2a6a15b0f27d0460c627889c3b81c311a6d4fd010434e8b1332b0b`，boot ID 不变、客户端耗时 1.301878421 秒，最终 status=4/frames_left=0、输出寄存器低、回显恢复。外部是否捕获与时序仍待本轮照片，未恢复官方应用或连接舵机；PROBE COMP 检查仍未执行。
