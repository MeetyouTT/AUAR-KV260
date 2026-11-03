# J2.3/E10 固定高、固定低诊断

**2026-10-06 08:03 UTC 当前状态：固定电平诊断已STOP并卸载，当前运行独立J2.3/E10 PWM。** 本目录BUILD `3eaeabab` 曾完成用户固定低0V/固定高3.3V实测；之后STOP/restore通过。当前活动项目 `/home/ghmd/kv260-j2-pin3-pwm-e10-20261006`、BUILD `2a3aca85`，约50Hz/1.5ms，示波器波形待验收。静态测量触点未独立确认，原J2.1低幅值根因仍未知。完整过程见 `BOARD_DIAGNOSTIC_STATUS.md`；以下内容保留为诊断准备历史。

目标针脚：KV260 实体 J2.3 → HDA12 → SOM240_1 D20 → FPGA E10，Bank45、LVCMOS33、DRIVE4、SLEWSLOW。针脚依据见 `J2_PIN_MAP.json`。默认/RESET/STOP输出低；START后持续输出高，直到STOP/复位。此程序用于电压对照。

来自已冻结的 `/home/ghmd/kv260-j2-pin3-static-20261006`。旧包实际D10/J2.5与标签不符，已禁止加载；本目录重新编译E10，仿真、构建、XSA、访问器、设备树和归档全部重新产生。没有复制旧构建通过状态或板测结果。

**2026-10-06 07:03 UTC：离线准备完成，52项核验通过，BUILD `3eaeabab`。** 新仿真、最终E10布线和实体J2.3映射通过，WNS+6.836ns、WHS+0.022ns、DRC错误0；AArch64访问器、设备树生成和基线合并、加载包哈希、串口封装均通过。归档56,683字节，SHA-256 `225abede15ab10eebb1973a15276eee4718a6c69f670250b8f6f6e204cef3b7b`。没有访问板子、没有加载、没有START，电压尚未测量。

准备状态以 `PREPARATION_STATUS.json` 为准。加载前核对实体目标、当前约束、最终IO报告和约束哈希，并要求 `PHYSICAL_CONNECTION.json` 确认J2.3空载或只接测量仪表。07:03离线阶段尚未收到连接答案，普通及`-O`模式均实测在访问串口前拒绝加载；之后用户明确测量点并回答“是的”确认只接仪表，才执行加载。对应证据为 `PIN_MAPPING_REVIEW.json`、`evidence/connection-guard-review.json`。没有把默认选项或等待时间当作实际接线确认。

测量计划：万用表直流电压档，黑笔接J2.9或J2.10 GND，红笔接J2.3；固定低预期接近0V，固定高预期接近3.3V。实际电压由现场测量提供，内部寄存器状态不能代替物理电压。
