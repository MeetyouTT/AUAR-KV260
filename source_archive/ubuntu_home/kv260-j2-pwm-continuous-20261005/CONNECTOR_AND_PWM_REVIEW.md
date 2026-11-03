# J2 针脚、PWM 软件与低幅度审查

审查时间：2026-10-06 06:42 UTC（项目所在时区 2026-10-05）。

**后续修正，2026-10-06 07:03 UTC：** 用户问下一步后，独立重建 `/home/ghmd/kv260-j2-pin3-static-e10-20261006`，正确E10/J2.3、BUILD `3eaeabab`，新仿真、构建与52项核验通过，匹配加载包准备完成。旧D10包仍冻结并禁止加载。新包尚未上板，正在等待实际J2.3接线描述；详细状态见新目录 `README.md` 和项目日志 `2026-10-06-J2-PIN3-E10.md`。下文保留本次审查发现与原证据。

结论：发现新固定电平对照包的实体针脚映射错误，已经禁止加载；原连续 PWM 的 J2.1/H12 映射与数字实现核验通过。另修正只读脚本的一处内部低电平状态显示错误。两处软件问题都不能解释此前 J2.1 的低幅度；实体电气根因尚未确定，没有证明 FPGA 损坏。

## 已确认的针脚对应

| KV260 实体针脚 | 载板信号 | SOM240_1 | FPGA 管脚 |
|---|---|---|---|
| J2.1 | HDA11 | A17 | H12 |
| J2.3 | HDA12 | D20 | E10 |
| J2.5 | HDA13 | D21 | D10 |
| J2.7 | HDA14 | D22 | C11 |

J2.9、J2.10 是 GND；J2.11、J2.12 是 3.3V。按用户之前白板上“11 在左、1 在右”的方向：

```text
11(3.3V)  9(GND)  7  5  3  1(原PWM)
12(3.3V) 10(GND)  8  6  4  2
                       ↑J2.3
```

J2.3 是 J2.1 同一排、向 GND 方向相邻的下一个信号脚。图中的左右依据用户白板，不替代现场一脚标记与板卡方向确认。

本次重新下载并查看厂家载板图第17页，PDF SHA-256 为 `f152a6f8fa8a909106837605404de110fd69aeb20b03bbbf41503583217c8640`。结合官方 BIST XDC 明确列出的 HDA11～HDA18 与 FPGA 管脚顺序，确认 `pmod[2]`/`PMOD_GPIO_tri_io[2]` 是第三个逻辑信号，不是实体 J2.3。实板载板 revision 尚未独立确认。

依据：[Xilinx 官方 KV260 BIST XDC](https://raw.githubusercontent.com/Xilinx/kria-vitis-platforms/main/kv260/platforms/kv260_bist/xdc/pin.xdc)、[Xilinx 载板原理图 Rev B03，第17页](https://hacksterio.s3.amazonaws.com/uploads/attachments/1429052/038-05058-01-x-mlcc_revb03_skit_TqvbkQ3RNn.pdf)、[AMD DS987 SOM240_1 表](https://docs.amd.com/r/en-US/ds987-k26-som/SOM240_1-Connector-Pinout)。

## 错误的范围与处理

新目录 `/home/ghmd/kv260-j2-pin3-static-20261006` 的约束和最终 IO 报告都使用 D10，实际输出在 J2.5；此前 README、XDC 首行注释、帮助文本和元数据写成 J2.3/D10，确有错误。该包 BUILD `0bad79ac` 没有上板、加载或 START。此错误影响新换脚诊断的接线说明与目标选择，不影响已加载的 H12 程序。

原51项核验只检查 RTL、仿真证据、构建、D10配置和工件身份，缺少“实体目标针脚是否与 FPGA 管脚相符”的独立检查。故51项通过不能证明 J2.3 对应关系正确。新增 `connector_mapping.py` 依据明确的 J2 表同时检查当前 XDC、最终 IO 报告及约束哈希。本包的新映射检查返回失败：目标 J2.3 要求 E10，构建 D10 实际为 J2.5；`ready_for_upload=false`，加载脚本在导入串口传输前拒绝，普通和 `-O` 模式均实测拒绝。

原约束、RTL、位流和归档保留作审计原件，没有用文案更改伪装成新构建。归档 SHA-256 仍为 `b8f8878b4b5656036c816c73eb838e663e107b8d0ae22a0a127b7026092ab35d`。旧注释/帮助有错，已在 README 置顶撤回。本包须重建为 E10/J2.3，或完整重新发布为 D10/J2.5，然后确认实际测点外接状态，才可进入部署；本次审查没有执行这些硬件操作。

原连续 PWM 的 `uart_burst.py` 另有一处记录错误：`output_register_low` 曾根据 `not running` 判断，因此运行中的低相位 status=5 被误标为 false。已改为读取 status 的 PWM 位（bit1），status4/5 对应低，status7 对应高。此改动只修正回读的 JSON 标记，没有改变 FPGA 配置或 PWM 参数；也不是物理引脚电压反馈。

末尾记录一致性检查还发现，`CURRENT_INSPECT.json` 已更新，而 `CURRENT_BENCH.json` 的两个最新inspect指针仍停留在05:47。已补齐inspect分支的证据指针与运行状态更新，并把当前汇总对齐到06:42实际回读。首次一致性断言因此失败，修正后重新验证；该记录错误也不改变引脚电气行为。

## 原连续 PWM 的复核结果

- 重新执行43项工件核验，全部通过，BUILD `f0206bda`。
- 复查原 RTL：硬件计数器输出，RESET/STOP 优先，连续运行 `RUN_FRAMES=0`；内部状态来自 PWM 节点，不能测量实体电压。
- 原最终 routed DCP 审计证据仍为 `evidence/20261005T203451.360132Z-output-path-audit/`：H12、Bank45、LVCMOS33、DRIVE4、SLEWSLOW，FDRE.Q → 普通 OBUF → 输出，无用户三态缓冲；原实现 DRC0、时序通过。本次读审计原件，没有重新打开 DCP 或重新运行完整仿真。
- 两次本轮只读板端检查 `20261006T063931.216719Z-uart-inspect` 与 `20261006T064224.066415Z-uart-inspect` 均 rc=0，同 boot `3b572120-4f45-48ec-99ce-90e377e91036`、BUILD `f0206bda`，status5/busy1，串口回显恢复。后一条的 `output_register_low=true` 已正确反映内部低相位。未发送 START/STOP、未加载新配置。
- 回读 period1999980、pulse149999，PL0实际99,999,999Hz，计算周期19.9998002ms、脉宽1499.990015µs、占空比约7.5%。这些是内部参数计算，不是示波器时序验收。

## 对电压的判断

正常目标是相对 J2 GND 的低平台接近0V、高平台接近3.3V；此50Hz/1.5ms波形的占空比约7.5%，若高平台3.36V、低平台0V，直流平均值约0.252V。因此万用表0.33～0.36V读数本身不能证明高平台只有这个电压，也不能据此认定 PWM 失败。

用户曾报告同一探头测电源平均3.36V、信号高值680mV/低值280mV/平均341mV；若确实是高低平台，则幅度不符合目标。断电重启后的720mV/最小200mV/平均330mV中，720mV具体测量项未确认，不能直接等同高平台。各读数来自不同采集，不合并成一个同时测量的数据集。未配置的第二排信号脚可能没有确定的输出状态，1.64V不能充当已验证的正常输出对照。

原理图显示 H12/HDA11 经 SOM240_1 A17、R276(0Ω) 到 J2.1；R274(20Ω)+C370(33pF) 是串联 RC 接地支路，不是直流分压器。尚无证据把低幅度归因于这个支路、DRIVE4设置或 FPGA 输出晶体管损坏。HDA/Bank45 的实际 VCCO 由载板经 SOM 连接器供给，J2 电源脚3.36V不能独立证明连接器之后的 I/O 供电正常。见 [AMD HDIO 供电说明](https://docs.amd.com/r/en-US/ds987-k26-som/HDIO-HDA-HDB-and-HDC-Banks)。

下一步仍需在针位准确、确认空载的条件下做固定低/固定高实体测量，再用另一条准确映射的同Bank信号通路对照。电气通路检查包括实际触点、局部 I/O 供电、SOM/载板连接和输出级；当前不能确定其中哪一项是根因。

## 本次文件改动与验证

- 新包：新增 `J2_PIN_MAP.json`、`scripts/connector_mapping.py`、`PIN_MAPPING_REVIEW.json`；修改 `scripts/uart_load.py`、`PREPARATION_STATUS.json`、`CURRENT_BENCH.json`、`README.md`，设置禁止部署并说明原件标签错误。
- 原 PWM：修改 `scripts/uart_burst.py` 的内部电平标记；更新 `BOARD_BRINGUP_STATUS.md`、`CONTINUOUS_VERIFICATION.json` 和只读检查产生的当前状态记录；新增本审查报告。
- 更新项目日志 `2026-10-05-J2-PIN3-STATIC.md`、`2026-10-05-J2-PWM-CONTINUOUS.md`。
- 验证：原43项、对照包数字工件51项通过；新增实体映射检查失败并正确阻止加载；普通/优化Python加载拒绝检查通过；脚本语法通过；原归档哈希不变；最新只读状态标记正确。
- 实板电压、稳定外部时序和舵机动作仍未验收。
