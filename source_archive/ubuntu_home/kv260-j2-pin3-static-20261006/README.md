# 固定电平对照：针脚标注错误，禁止部署

**2026-10-06 审查更正：J2.3 对应 E10；已有 BUILD `0bad79ac` 约束到 D10，实际对应 J2.5。** 此包没有访问板子、加载或 START，不能解释此前 J2.1/H12 的低幅度。先前把逻辑数组 `pmod[2]` 当成实体针脚 3，导致本页下方历史说明、XDC 首行注释、命令帮助与归档中的标签错误。原 XDC/RTL/位流/归档保持原件用于追溯；文件名中的 `pin3` 也不能作为实际针脚依据。

已将 `PREPARATION_STATUS.json.ready_for_upload=false`，并在 `uart_load.py` 加入加载前核对：实体目标 → 官方针脚表 → 当前 XDC → 最终 IO 报告。当前目标 J2.3/E10 与构建 D10/J2.5 不匹配，脚本在导入串口传输前拒绝加载；仅确认外接状态不能解除此错误。51 项原核验只覆盖数字实现与工件身份，没有核验实体排针映射，因此不构成整包通过。

官方交叉依据见 `J2_PIN_MAP.json`；详细审查见 `PIN_MAPPING_REVIEW.json`。后续需重新构建 E10/J2.3，或完整重新发布标为 J2.5 的 D10 包，再确认对应针脚的外接状态。

以下保留原准备记录，**其中 J2.3/D10 对应关系已撤回，不能照此接线或部署**。

**准备已完成（UTC 2026-10-06 06:29）：** 最终仿真和构建通过，51 项离线核验通过，BUILD_ID `0bad79ac`；WNS +6.728ns、WHS +0.020ns、DRC错误0，D10/LVCMOS33落实到最终实现。AArch64访问器、从新XSA生成的设备树、基线合并与加载包哈希均通过。归档56,266字节，SHA-256 `b8f8878b4b5656036c816c73eb838e663e107b8d0ae22a0a127b7026092ab35d`。见 `PREPARATION_STATUS.json`。尚未上板，等待 J2.3 外接状态；没有新的电压实测结果。

该目录用于定位 J2.1/H12 低幅度输出的原因，复用已有固定电平诊断逻辑，只把输出约束改到 J2.3/D10（Bank45、LVCMOS33、4mA、SLOW）。默认/复位/STOP 为低，START 后固定高；不是舵机控制波形。

来源 `/home/ghmd/kv260-j2-static-high-20261005`；历史测量和板端状态没有复制。独立应用名 `aura-pin3-static`，固件名 `aura_pin3_static.bit.bin`；BUILD_ID 对源文件、引脚约束和构建脚本取哈希。离线验证和板端状态以本目录新产生的证据为准。

部署前须确认 J2.3 空载或只接测量仪表。板端尚未部署；原 J2.1 连续 PWM 的最近控制回读为 2026-10-06 05:47 UTC，同 boot `3b572120-4f45-48ec-99ce-90e377e91036`，内部连续运行。

测量：万用表直流 V 档，黑笔接 J2 GND，红笔接 J2.3。START 预期约3.3V，STOP预期约0V，实际数值由用户测量。内部状态不能代替电压实测。

定位意义：J2.3 正常而 J2.1 异常，范围缩小到 H12 独有电气通路；两路都异常，优先核对实际接点、测量链路和共用 I/O 供电。任何一个结果都不能单独认定 FPGA 芯片损坏。

已确认空载后，操作顺序是：用原连续 PWM 的受控脚本 STOP/restore，再运行本目录 `uart_stage.py`、`uart_load.py`、`uart_burst.py scratch`、`uart_burst.py stop`、`uart_burst.py start`、`uart_burst.py inspect`。新加载脚本读取 `PHYSICAL_CONNECTION.json`，当前未确认，不会开始加载。固定高测量完成后，再由受控 STOP 切换低电平并测量。

针位依据：[Xilinx 官方 KV260 约束](https://raw.githubusercontent.com/Xilinx/Kria-PYNQ/main/kv260/base/vivado/constraints/base.xdc)及 KV260 载板 RevB03 原理图第17页。实板版本/方向仍须现场核实。
