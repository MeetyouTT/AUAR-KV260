# J2.3/E10 连续PWM板测状态

09:31 UTC最新：原固定PWM只读inspect `evidence/20261006T093044.336586Z-uart-inspect` rc0、status5、同boot/BUILD `2a3aca85`、PL0实际99999999Hz，period1999980/pulse149999/RUN_FRAMES0/PULSE_US1500，仍在运行，回显恢复；无START/STOP或固件切换。新 [持续摆动候选](/home/ghmd/kv260-j2-pin3-sweep-e10-20261006/BOARD_TEST_STATUS.md)完成仿真/构建/48项核验及暂存上传，但未加载/START，VIB实际J2.3连接待用户确认；两份候选的通过状态不混用。servo_actuation_verified仍为false。

最新状态08:56 UTC：用户已报告“完全不动”，并明确经过信号隔离模块。只读共享资料与源码发现旧图J2.1/H12与当前J2.3/E10输出存在差异，VIB实际针脚未确认；不能据文档直接判实物接错。共享资料为DS3230、5 V、ADuM1201 VIB→VOB→SVPDB-8S信号1。当前程序仅固定1.5 ms，可START/STOP而不能运行时改脉宽；同目标重启可能无可见动作。隔离后的PWM及舵机插口供电/信号尚无实测，servo_actuation_verified=false。本轮无新UART动作、固件或脉宽变更，最新硬件证据仍为08:40 inspect。此前直接共地解释不适用于新明确的隔离拓扑；模块两侧各用本侧参考地，不跨接GND1/GND2。现阶段与接线核对见 [ISOLATOR_WIRING_REVIEW.md](ISOLATOR_WIRING_REVIEW.md)，证据 `evidence/20261006T085633Z-servo-isolator-review.json`；共享原件未改。以下旧段落保留当时状态。

最新状态08:40 UTC：用户已确认J2.3信号、独立动力供电与共地；按其要求完成STOP→START，并在随后只读inspect核对同boot/BUILD，固定50Hz/1.5ms PWM持续运行。舵机实际动作等待用户观察，尚未验收。以下早期段落保留当时状态与测量证据。

08:33 UTC用户要求重新启动测试。新只读 `evidence/20261006T083323.328600Z-uart-inspect` rc0、status5、同boot/BUILD，50Hz/1.5ms持续输出不变；当前加载会话SCRATCH/STOP前置记录通过。未收到供电与共地接法回复，尚未执行新的STOP/START。准备记录 `evidence/20261006T083348Z-servo-restart-preparation.json`；这是一份待执行计划，不能作为重启动作完成的证据。

2026-10-06 08:03 UTC：已加载并START，当前持续输出程序运行。实体输出J2.3/HDA12/SOM240_1 D20/E10，Bank45/LVCMOS33/DRIVE4/SLOW。新应用 `aura-pin3-pwm`、固件 `aura_pin3_pwm.bit.bin`，BUILD `2a3aca85`，boot `2a95bf6d-fea6-46e7-88aa-12f92eb40551`。用户此前确认该脚仅接仪表，固定低测0V、固定高测3.3V。08:10 UTC收到新PWM示波器图片，脉冲形态符合目标；数值电平和周期/脉宽尚未全部验收。没有连接/驱动舵机的记录。

## 完成及实际证据

- 新仿真 `evidence/20261006T073937.942630Z-sim`：15参数/波形组、AXI16选通、连续输出/STOP/reset通过。
- 新构建 `evidence/20261006T074155.943586Z-build`：52项离线工件/实体映射检查通过，WNS+6.864ns、WHS+0.022ns、DRC错误0，输出预算20ns/slack14.907ns。最终E10输出和当前XDC/构建身份一致。一次提前核验因导出文件未产生退出，构建完全结束后重新核验52项通过。
- 访问器AArch64/32位ldr、str/dsb sy/程序身份/主机架构拒绝检查通过。初始串口封装3803字节超限，在硬件访问前拒绝；去掉可选耗时遥测后最长3723<=3800，保护条件保留，见 `evidence/transport-size-adjustment.json`。
- 新XSA生成设备树，官方2022.2仓库commit `24d29888d0048f26e4f3d6e0b7cd655aede94f31`；Linux包 `evidence/20261006T075113.263364Z-linux-package`，位流/DTBO/基线合并、clock99999001、AFI14=a00/15=0、reg80080000/1000通过。
- 加载归档 `evidence/20261006T075158.053688Z-pwm-board-stage/aura-pin3-pwm-stage.tar.gz`：56295字节，SHA `37ca4c0d33620c7e7d20c1180744c361f9116e8bd5d736148dd04ec87a428a03`。串口上传 `evidence/20261006T075259.561359Z-uart-stage`，47帧且最终哈希一致。
- 固定高程序先STOP，再restore：`/home/ghmd/kv260-j2-pin3-static-e10-20261006/evidence/20261006T075814.719275Z-uart-stop`、`20261006T075839.409366Z-uart-restore`，确认原诊断不活动、基线恢复，才加载新PWM。
- 新PWM加载 `evidence/20261006T075854.728345Z-uart-load-idle`：五步全部通过，默认status4、未START。
- SCRATCH `evidence/20261006T080126.694177Z-uart-scratch`、STOP `evidence/20261006T080144.974183Z-uart-stop`：同boot/BUILD、status4、rc0。
- START `evidence/20261006T080237.141490Z-uart-start`：同boot/BUILD、status7、rc0；只读inspect `evidence/20261006T080343.313054Z-uart-inspect`：status5、continuous_running=true，PL0实际99999999Hz，period1999980/pulse149999、RUN_FRAMES0、PULSE_US1500。控制台回显恢复，无再次复位的证据。

## 参数与待测事项

按实际时钟及计数计算周期19.9998002ms、高脉宽1499.990015us、频率约50.0005Hz，占空比约7.5%。这仍是程序参数/板端回读，不等于示波器实测。

物理高低电平预期约3.3V/0V；在前一个固定电平位流中用户报告0V/3.3V，证据见 `/home/ghmd/kv260-j2-pin3-static-e10-20261006/evidence/20261006T073420Z-fixed-low-user-measurement.json`、`20261006T073633Z-fixed-high-user-measurement.json`。不将两种不同BUILD的测量混作当前PWM的电平验收。原J2.1低幅值根因仍未定位，不能据此宣布原引脚或整片FPGA损坏。

测量接法：探头尖J2.3，地夹J2.9/J2.10 GND；探头和示波器均10×，CH1直流，1V/div，5ms/div，CH1上升沿触发约1.6V，Run/Stop处于运行。预期每20ms一枚宽1.5ms、高约3.3V的脉冲。万用表直流通常读平均值约0.25V，不能把该读数当作高电平幅度。

## 08:10 UTC：用户示波器图片

收到 `/home/ghmd/图片/5554545455457777.jpg`，示波器CH1为1V/div、5ms/div、Trig'd。图上两个脉冲的高平台视觉估计约3.3V、低平台约0V、相邻上升沿约20ms、高平台宽约1.5ms。这些是按网格估计，不冒充仪器数值测量。图片接触位置沿用此前J2.3接法确认，照片未独立展示触点。

屏幕显示平均231mV、峰峰值4.44V、最大值4.04V、最小值-408mV，周期均方根812mV、均方根980mV。约0.25V的预期平均与231mV接近；最大/最小包含边沿过冲，不能代替高值/低值平台。原先J2.1数百mV的小幅脉冲没有在这张J2.3图片中重现，但原引脚根因依然未知。

待测：CH1“高值”“低值”“周期”“正向脉宽”，目标约3.3V、0V、20ms、1.5ms；用短且直接的探头接地复查尖峰。长接地线可引入测量振铃，参考 [Tektronix 探头说明](https://www.tek.com/en/documents/whitepaper/abcs-probes-primer)，本次尖峰究竟来自接法还是实际输出仍未确定。仅标记external_waveform_observed，不将external_waveform_verified/电平全部通过置真。图片观察证据见 `evidence/20261006T081045Z-scope-image-observation.json`。

## 改动文件

08:40 UTC重启实测完成：用户回复“确认”，对应证据 `evidence/20261006T083722Z-servo-connection-confirmation.json`，确认信号J2.3、适当独立电源、共地；没有单独报告型号和数值供电电压，没有独立触点检查。STOP `20261006T083823.901163Z-uart-stop` status4、START `20261006T083904.102058Z-uart-start` status7、inspect `20261006T084027.522182Z-uart-inspect` status5，三次rc0、同boot/BUILD，时钟与period/pulse/RUN_FRAMES/PULSE_US保持原值，回显恢复。没有重载固件、重启板子或改脉宽。

实际重启汇总见 `evidence/20261006T084052Z-servo-pwm-restart-result.json`；前一份08:33准备记录保留未执行状态，不能与这次已执行结果混淆。当前servo_restart_complete=true、continuous_running=true、servo_actuation_verified=false。输出为固定位置指令，原已处于目标位置时可能没有明显位移；下一步由用户报告转动后停住/完全不动/抖动等现象，再决定后续测试。PHYSICAL_CONNECTION、PREPARATION_STATUS、CURRENT_BENCH、CONTINUOUS_VERIFICATION、README、本报告、项目日志和本轮证据已更新，RTL/约束/访问器/位流保持不变。

08:26 UTC更新：用户报告舵机已连接。通过 `evidence/20261006T082550.189998Z-uart-inspect` 只读复核，rc0、status5，同boot/BUILD，PL0实际99999999Hz、period1999980/pulse149999、RUN_FRAMES0、PULSE_US1500，当前固定连续PWM仍运行。未再次START、STOP、重启、加载或改脉宽。软件回读不能证明舵机已收到有效信号或已动作。

新接线取代此前仅接仪表的确认；PHYSICAL_CONNECTION记录“舵机连接已报告、细节待确认”，当前external_connection_confirmed=false，历史0V/3.3V与示波器观察仍保留。正在确认型号、J2.3信号接法、外部电源/实际电压、共地；舵机动作结果待用户观察。进一步动作命令须在接线信息齐全后执行。J2的3.3V电源只有100mA供电能力，参见 [AMD UG1089供电预算](https://docs.amd.com/r/en-US/ug1089-kv260-starter-kit/Powering-the-Starter-Kit-and-Power-Budgets)；项目舵机使用额定范围内的独立动力供电并共地。

新工作目录下创建 `constraints/j2.xdc`、`rtl/pwm_burst.sv`、`rtl/axi_body.sv.in`、`rtl/aura_pwm_probe.sv`、`tests/tb_burst.sv`、`tests/tb_axi.sv`、`board/probe.py`、`board/mmio32.c`、`board/bench_config.h`、`board/mmio32`、`J2_PIN_MAP.json`、`PHYSICAL_CONNECTION.json`、`PREPARATION_STATUS.json`、`README.md`、`BOARD_TEST_STATUS.md`、`CONTINUOUS_VERIFICATION.json`。

本目录scripts：`prepare.py`、`build.tcl`、`run.py`、`verify.py`、`connector_mapping.py`、`compile_accessor.py`、`review_transport.py`、`generate_overlay.py`、`gen_device_tree.tcl`、`package_linux.py`、`make_stage.py`、`uart_stage.py`、`uart_restage.py`、`uart_load.py`、`uart_burst.py`、`uart_state.py`。工具生成CURRENT_SIM/BUILD/LINUX_PACKAGE/STAGE/BOARD_STAGE/BENCH/SCRATCH/STOP/START/INSPECT等状态、验收报告与对应evidence，均来自此次实际执行。

先前固定电平目录更新PHYSICAL_CONNECTION/PREPARATION_STATUS/CURRENT_BENCH/README/BOARD_DIAGNOSTIC_STATUS和两项用户测量证据；原J2.1连续PWM目录更新CURRENT_BENCH/CONTINUOUS_VERIFICATION的当前应用指针。日志：`/home/ghmd/AMD_Smart/logs/daily/2026-10-06-J2-PIN3-PWM.md`、`2026-10-06-J2-PIN3-E10.md`。没有改动原M3源码或受保护基线应用固件。
