# 2026-10-04：J2 PWM 离线候选完成

结果：H12 的有限时长 PWM 候选已完成 RTL、XSIM 仿真、Vivado 2022.2 综合/布局布线、位流导出和独立文件核对。41 项核对全部通过。没有连接或编程 KV260，没有产生板端波形，也没有驱动舵机。

用户最新说明“电压测过了，没问题”，供电状态记录为用户实测正常；未收到具体读数，不再要求重复测量。接线按用户确认的针 1 所在排及照片位置采用 J2.1/H12 信号、J2.9 地、J2.11 3.3 V。远端通道和实物载板版本仍不属于助手独立测量结果。

## 实现与实际验证

新工程位于 `/home/ghmd/kv260-j2-pwm-20261004`。原 M3 工程未修改；引用的原 `aura_m3_regs.v` SHA-256 仍为 `2165e1aa17837d79a2898f1ca52113d0235a676afeede45070de87f5a6bc2810`。

- `rtl/pwm_burst.sv`：默认输出低；显式 START 后发送固定帧数；STOP/同步复位优先截断；运行中重复 START 不续时；到期返回低且不自动重启。
- `rtl/aura_pwm_probe.sv` 与 `rtl/axi_body.sv.in`：独立 PWMT 测试 ABI；AXI-Lite AW/W 分别缓存；B/R 背压保持；控制必须完整 WSTRB、正确命令和合法状态；非法访问返回 SLVERR。BUILD_ID 为 `0x03cd161b`。
- `scripts/build.tcl`、`constraints/j2.xdc`：新的独立 PS＋AXI＋PWM 工程；控制窗口 `0x80080000/4 KiB`；H12、LVCMOS33、4 mA、SLOW；异步输出使用明确的寄存器到管脚 20 ns 数据路径预算。
- `board/probe.py`：读取加载身份与配置后，显式 `--start` 才请求一次输出，并等待硬件到期；默认只读。该客户端只完成 Python 编译/帮助入口检查，尚未做板端 MMIO 验证。

XSIM 两组测试通过。脉冲组含 9 个参数用例，覆盖 99,999,001 Hz、100 MHz、缩放时钟、1/2/3 帧以及非法脉宽/频率/帧数；逐周期核对脉宽、周期、剩余帧数、到期、重复启动、停止优先级和脉冲中复位。AXI 组覆盖 16 种 WSTRB、AW/W 到达顺序、响应背压、错误访问、半写复位、同拍读写旧值和有限时长。仿真中的完整运行使用 1/2/3 帧，实际位流固定参数为 50 帧；没有把仿真当作目标板 50 帧波形实测。

| 最终布局布线项目 | 实际结果 |
|---|---|
| 器件 / Board part | xck26-sfvc784-2LV-c / kv260_som 1.4 |
| PS PL0 配置推导频率 | 99,999,001 Hz，板端真实时钟仍待核验 |
| 固定输出参数 | 50 Hz、1500 µs、50 帧，约 1 s |
| 周期 / 脉宽 | 1,999,980 / 149,999 ticks |
| Setup WNS / Hold WHS | +6.681 ns / +0.013 ns |
| 异步输出预算 / 路径延迟 / 余量 | 20.000 / 5.036 / +14.964 ns |
| 最终默认 DRC | 0 个 violation |
| no_clock / 内部未约束端点 / no_output_delay | 0 / 0 / 0 |
| CLB LUT / FF / CLB site | 608 / 749 / 135 |
| 最终日志 ERROR / CRITICAL WARNING | 0 / 0 |

独立核对还确认了当前 RTL 与通过仿真的 RTL、封装 IP 内的 RTL一致；复位极性及辅助复位常量正确；BD 地址和构建参数一致；BIT 的器件字段正确；BIN 与 BIT 配置载荷逐字节一致；XSA 内的 BIT 与导出 BIT 一致。全部输入与日志摘要见 [FINAL_VERIFICATION.json](FINAL_VERIFICATION.json)。

## 可追溯工件

通过的仿真证据：`evidence/20261005T034439.314192Z-sim/`。

通过的构建证据：`evidence/20261005T035504.065314Z-build/`。

| 工件 | SHA-256 |
|---|---|
| [aura_pwm_probe.bit](evidence/20261005T035504.065314Z-build/artifacts/aura_pwm_probe.bit) | `3c4a44876459ea7d742efebe225a0710b8d7b5e0d1acc11b8d5e808789511e2f` |
| [aura_pwm_probe.bin](evidence/20261005T035504.065314Z-build/artifacts/aura_pwm_probe.bin) | `527a95f3515d6e00f8c57fbcc4366fc689cc863e408d3abc5dd57da2ff53fabf` |
| [aura_pwm_probe.xsa](evidence/20261005T035504.065314Z-build/artifacts/aura_pwm_probe.xsa) | `3f958d747bdb336731c34a086ce7154d358010cfe088ed8cde94f57c5ce47b2f` |

Vivado `.bin` 是原始配置载荷，不能直接当成板端 Linux 已就绪的 Bootgen `.bit.bin`。本轮没有生成或安装 Linux DTBO/DFX 运行包，没有执行上板加载。

## 修正与保留证据

前期失败分别为缺少 timescale、沙箱禁止 XSIM 所需的本机通信套接字、测试台首次采样多进一个周期。补充 timescale、获准在沙箱外运行本机离线工具、修正测试台采样后，两组仿真通过；所有原日志保留。

第一次构建生成了工件，但审阅发现 `set_max_delay -datapath_only` 缺少非空 `-from`，约束被忽略；同时辅助复位传播为低有效却接了 0，会使逻辑持续复位。该批已标记 [REVIEW_REJECTED.json](evidence/20261005T034610.064175Z-build/REVIEW_REJECTED.json)，不可用于上板。修正源选择、辅助复位电平，增加复位极性和输出路径预算检查，并让构建遇到 CRITICAL WARNING 即判失败；在全新证据目录重新完整构建通过。

## 当前范围与下一步

这是独立波形测试工程，未包含 DPU 或完整 motion ABI。加载完整位流会替换现有 PL；同配置 DPU 与运动监督的正式联合平台仍需另行实现和验收。

下一步先保持舵机三线插头拔下，确认现有波形仪器；再准备与当前板端系统匹配的 Linux 加载/恢复配置并核验实际 PL0 时钟。正确候选加载后，先检查身份和默认低电平，再显式触发一次固定波形。示波器测 VOB 对 GND2，或采用支持 5 V 输入的逻辑分析仪；测周期约 20 ms、高电平约 1.5 ms、50 帧到期以及停止/复位。普通万用表不能代替数字时序测量。

波形通过后再断电接入无机械负载的舵机并做小范围标定。1500 µs 是首测脉宽，不代表已经标定的机械中位。ADuM1201 的 VDD1 失电而 VDD2 保持供电时 VOB 默认高，停止系统先断舵机电池。测量依据和完整步骤见 [README.md](README.md)。

## 2026-10-04 后续板端准备补记

本报告上文保持原离线阶段结论。此后已生成 Linux Bootgen/DTBO/`PL_FLAT` 包、经原系统 DTB 离线合并核对，并通过 USB 串口只读核验当前官方应用；归档包已传至板端独立暂存目录并按 SHA-256 验证。当前仍未加载测试位流或发送 START，外部 PWM 尚未测到。详见 [BOARD_BRINGUP_STATUS.md](BOARD_BRINGUP_STATUS.md) 与对应 `CURRENT_*` 状态文件。
