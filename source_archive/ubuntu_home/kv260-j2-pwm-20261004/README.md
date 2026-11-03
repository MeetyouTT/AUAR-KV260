# KV260 J2 / H12 PWM 波形测试候选

当前板测已按用户要求切换到 [持续 PWM 测试](../kv260-j2-pwm-continuous-20261005/README.md)，持续模式已启动；本目录保留一秒版本和历史证据。

用途：在舵机三线插头拔下时，验证 J2 → ADuM1201 VIB → VOB 的数字波形。
用户已说明三根线在针 1 所在排，并说明隔离模块两侧电压已测、正常。
针位及电压属于用户现场报告，尚未由本程序或助手独立测量。

这是单独的离线测试工程，不含 DPU，也不是正式 motion ABI 或最终联合平台。
加载其完整位流会替换当前 PL；加载/恢复需要先处理当前官方应用和驱动。
本工程的构建脚本不连接板卡，不部署、不写 SD/QSPI、不启动舵机。
原 M3、DPU 工程及其工件不改动。

## 候选行为

- 外部输出：`servo_pwm` → H12，LVCMOS33，4 mA，SLOW；按 B03 J2.1 对照。
- 默认和同步复位输出低；没有自动启动，也没有后台续租。
- 显式 START 后输出 50 帧：候选周期 20 ms、高电平 1500 µs，总时长约 1 s。
- 运行中的重复 START 返回 SLVERR，不能延长时长。
- STOP 或复位优先截断当前脉冲；50 帧结束直接返回低电平，没有额外窄脉冲。
- 脉宽/帧数固定于构建，不执行左右扫动，也不声称 1500 µs 就是实际机械中位。
- Vivado PS PL0 配置推导频率为 99,999,001 Hz：周期 1,999,980 ticks，脉宽 149,999 ticks。加载位流前仍须核验板端实际 PL 时钟；位流加载本身不保证 Linux 的 PS 时钟配置与 XSA 一致。
- 该核没有正式运动监督的会话/代次/标定/外部停止输入等合同，不能替代 A07—A09。

数字输出低与舵机停稳是两种结果。ADuM1201 在 VDD1 失电、VDD2 仍供电时，VOB 默认高，停机应先断舵机电池。

## 离线构建

```bash
cd /home/ghmd/kv260-j2-pwm-20261004
python3 scripts/run.py sim
python3 scripts/run.py build
python3 scripts/verify.py
```

Vivado/XSIM 2022.2 已安装。仿真器需要本机通信套接字；限制套接字的沙箱可能使 XSIM 初始化失败。
每次尝试使用新的 `evidence/<UTC>-sim|build/` 目录，保留错误及原日志。
`CURRENT_SIM.json` / `CURRENT_BUILD.json` 仅反映相应阶段实际结果；完成构建不等于板测。

## 测量和上板顺序

1. 已有电压检查按用户反馈正常。保持舵机三线插头拔下；给隔离器两侧分别供电。
2. 完成离线仿真、布局布线、时序/DRC及工件核对后，确定当前板端包的停止、卸载与恢复方式，再加载此候选。
3. 先读取 PWMT 身份、BUILD_ID、状态；默认应为禁能。正确加载前不要对未知地址执行诊断客户端。
4. 示波器探头接隔离模块 VOB、地夹接 GND2，等待一段明确触发的 50 帧波形；或使用支持 5 V 输入的逻辑分析仪测数字时序。
5. 测高电平约 1.5 ms、周期约 20 ms、50 帧后低电平；测 STOP/复位。万用表直流平均值不能验证脉宽。
6. 数字波形实测通过后，再断电接舵机、移除机械负载，从标称中位附近的小范围标定开始。

不要用普通示波器的两个共地地夹跨接 GND1/GND2。当前仅测 VOB 对 GND2。
位流只声明内部至异步输出端的 20 ns 路径预算，没有虚构外部采样时钟或导线延迟；外部传播和脉宽依靠实际仪器核验。

仪器接线与起始设置见 [MEASUREMENT_GUIDE.md](MEASUREMENT_GUIDE.md)。仪器已确认是 UNI-T UTD2102CEX+；指南不是已完成的波形实测。

## 测试 ABI

地址窗口来自本次 BD：`0x80080000–0x80080fff`，32 位、4 字节对齐。

| 偏移 | 含义 |
|---|---|
| 0x00 | IP_ID = 0x50574D54（PWMT，与原 AURA M3 区分） |
| 0x04 | ABI = 0x00010000 |
| 0x08 | BUILD_ID；完整输入哈希见 evidence/source_identity.json |
| 0x0c | bit0 busy、bit1 当前 PWM 电平、bit2 参数合法 |
| 0x10 | 只写控制：START=0x53544152，STOP=0x53544F50；必须四字节有效 |
| 0x14 / 0x18 | 周期 / 脉宽 ticks |
| 0x1c | 剩余帧数 |
| 0x20 / 0x24 / 0x28 | 控制频率 Hz / 固定帧数 / 脉宽 µs |
| 0x2c | SCRATCH，支持 WSTRB，只用于不产生动作的总线核验 |

控制错误、运行中 START、只读写入、未对齐及保留地址返回 SLVERR。
AXI AW/W 分别缓存，响应背压保持稳定；复位丢弃半写；读写 SCRATCH 同拍读旧值。
客户端 `board/probe.py` 默认只读；`--start` 明确请求一次有限测试，`--stop` 截断输出。
当前客户端调用哈希校验的 AArch64 `board/mmio32`，用已核对机器指令的 32 位读写访问寄存器；它检查指定测试卡、FPGA manager 和加载固件名，再读身份和配置。必须先加载匹配的 Linux 配置，不能在其他位流下访问测试地址。Vivado 的 `.bin` 是原始配置数据；匹配的 Linux Bootgen `.bit.bin`、DTBO 和 `PL_FLAT` 包现已离线生成并核对，见 [CURRENT_LINUX_PACKAGE.json](CURRENT_LINUX_PACKAGE.json)。

第一次启动使用旧 Python `struct.pack_into` 客户端时发生内核 SError/panic，用户报告未看到波形；旧客户端已保留并拒绝继续使用，直接故障根因仍未完全确认。2026-10-05 用户按 RESET/SW2 后 Linux 恢复，新归档已核验并重新加载；新 32 位访问器的身份/默认状态、SCRATCH 写读恢复、STOP 以及随后一次 START 控制检查均通过，boot ID 不变、最终 status=4/frames_left=0。外部 PWM 周期、脉宽和完整帧数尚未验收；用户最新报告有波形，照片未能清晰辨认重复矩形脉冲。启动控制器要求本次加载会话的 SCRATCH/STOP 已通过、boot ID 未变化，再等待用户的仪器就绪确认。当前证据及下一步见 [BOARD_BRINGUP_STATUS.md](BOARD_BRINGUP_STATUS.md)。

## 依据

- 项目 ZIP A 手册 A06：从真实时钟计算周期/脉宽，先无动力测波形。
- 项目 ZIP A 手册 A12：隔离器通道/供电和失电状态需验证，先数字再机械标定。
- [Xilinx Kria-PYNQ XDC](https://github.com/Xilinx/Kria-PYNQ/blob/main/kv260/base/vivado/constraints/base.xdc)：H12 / LVCMOS33。
- [Xilinx B03 载板原理图第17页](https://www.mikrocontroller.net/attachment/573191/038-05058-01-X-MLCC_REVB03_SKIT.pdf)：J2.1 / H12。
- [ADI ADuM1201 数据手册](https://www.analog.com/media/en/technical-documentation/data-sheets/ADuM1200_1201.pdf)：通道、供电参考地与失电行为。
