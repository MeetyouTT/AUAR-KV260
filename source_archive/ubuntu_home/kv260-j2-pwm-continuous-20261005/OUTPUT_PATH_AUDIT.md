# J2.1 PWM 输出通路核查（2026-10-05）

结论：当前未发现 PWM 时序逻辑、输出方向、H12 约束或最终布线连接错误。用户报告的高值 0.680 V、低值 0.280 V 不符合目标 0～3.3 V 输出；应继续检查 I/O 输出级、VCCO 供电、SOM/载板连接和实际测点。现有证据不足以确定 FPGA 芯片内部损坏，也不足以宣布板级 PWM 验收通过。

## 本轮实际检查

- 查阅资料包 README、FPGA 相关资料和最新项目记录；较新的实际记录覆盖历史状态。
- 阅读 `rtl/pwm_burst.sv`、`rtl/aura_pwm_probe.sv`、`constraints/j2.xdc`、`scripts/build.tcl`、`board/mmio32.c`。连续模式由硬件计数器产生，寄存器输出未定义高阻态；状态寄存器读取的是内部 `servo_pwm`，不是引脚电压反馈。
- 重新运行 `scripts/verify.py`，43 项既有工件核验通过，BUILD_ID=f0206bda。此项复核仿真/构建证据及工件身份，没有重新执行完整仿真。
- 新增 `scripts/audit_output_path.tcl`，用 Vivado 2022.2 打开原最终 routed DCP。端口 H12、OUT、LVCMOS33、DRIVE=4、SLEW=SLOW 均符合断言；普通 OBUF 的唯一输入驱动是 `pwm_bench_i/probe/inst/burst/pwm_reg/Q`（FDRE）。未发现 OBUFT/IOBUF 或用户 STARTUP 实例。
- 本轮离线审计退出码 0，证据：`evidence/20261005T203451.360132Z-output-path-audit/`。原实现报告 Bank=45、布线错误 0、WNS +6.919 ns、WHS +0.012 ns。原输出路径只经过一个 OBUF。
- 本轮没有访问或修改板端。最近一次实际板端读取仍为 `evidence/20261005T202543.199585Z-uart-inspect/`：同 boot/BUILD、status=5、busy=1、PL0=99,999,999 Hz。内部控制通过不能证明物理输出合格。

## FPGA 到排针的实体路径

依据 Xilinx KV260 载板原理图 038-05058-01 Rev B03（2021-03-26），第 6、17 页：

`PWM 寄存器 → OBUF → FPGA H12 / HDA11 → SOM240_1 A17 → R276（0Ω）→ PMOD_HDA11 → J2.1`

信号节点还接有 R274（20Ω）和 C370（33 pF）组成的串联 RC 接地支路；这不是直流电阻分压器。该支路未发现信号电平转换器。U42 是 PMOD 电源开关，不是这一路 PWM 的信号转换器。现场载板版本尚未独立确认，因此元件号须先与实板版本对应，不能据此盲目探测。

H12 属于 HDA / Bank 45。AMD DS987 说明其 VCCO_HDA 由载板供电，SOM240_1 B13、B14 为该供电脚。载板 PL_3V3 同时供给这一供电通路和 PMOD 电源开关的输入。J2 电源测得 3.36 V 是有用证据，但不能代替对连接器之后实际 I/O 供电的验证。DRIVE=4 表示驱动强度配置，不能解释为输出电压 0.4 V。

资料：

- [AMD DS987：HDIO banks](https://docs.amd.com/r/en-US/ds987-k26-som/HDIO-HDA-HDB-and-HDC-Banks)
- [AMD DS987：SOM240_1 引脚](https://docs.amd.com/r/en-US/ds987-k26-som/SOM240_1-Connector-Pinout)
- [Xilinx 官方 Kria-PYNQ KV260 引脚约束](https://raw.githubusercontent.com/Xilinx/Kria-PYNQ/main/kv260/base/vivado/constraints/base.xdc)
- [Xilinx 载板原理图 Rev B03 镜像](https://hacksterio.s3.amazonaws.com/uploads/attachments/1429052/038-05058-01-x-mlcc_revb03_skit_TqvbkQ3RNn.pdf)，PDF SHA-256：`f152a6f8fa8a909106837605404de110fd69aeb20b03bbbf41503583217c8640`。

## 对现有测量的解释与边界

最新测量见 `evidence/scope-levels-680mv-280mv-user-report.json`。同一探头在电源脚测到平均 3.36 V，在信号脚测到高值 0.680 V、低值 0.280 V、平均约 0.341 V；万用表信号对地约 0.36 V。此前“整体相差十倍”的推断已撤回。各读数来自不同采集，不能混为同时测得的数据集。

平均电压较低本身可能来自低占空比，但高平台只有 0.680 V 的报告不能仅用平均值解释。此前固定高约 0.622 V、固定低约 0.282 V 的报告也支持继续检查电气通路，不能据此确定损坏位置。0.68 V 接近某些结压降并不构成“钳位二极管损坏”的证据。

HDL/布线核查不能检验实体 I/O 晶体管、局部供电、连接器接触、R276 焊接与走线，也不能独立确认探头实际触点。未发现用户三态缓冲不等于已经实测排除所有器件全局配置或供电状态问题。

## 下一步区分试验（尚未执行）

1. 核对实际 J2.1/GND 接点、实板版本，并用同一探头测同一点；保留目前空载条件。
2. 用相同逻辑驱动另一个确认空载且针位已核实的 J2 信号脚，做固定低/固定高对照。另一路正常会把范围缩小到 H12 独有通路，但仍不能单独判定芯片损坏；多路都异常应先查共用供电和测量链路。
3. 在已确认实板版本和元件位置后，由熟悉板级测量的人检查 R276 两端及实际 VCCO_HDA 供电。连接器侧正常而 J2 侧异常，优先查电阻/焊接/载板；连接器侧也低，继续查供电、SOM 通路与输出级。不要直接探测细间距 BGA 或带电拆装 SOM。

板级电压/时序验收仍为未通过；根因尚未确证。
