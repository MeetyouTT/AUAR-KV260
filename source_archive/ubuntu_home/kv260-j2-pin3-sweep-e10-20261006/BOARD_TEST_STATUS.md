# J2.3 持续小幅摆动候选

最新11:42 UTC：用户明确反馈舵机已左右摆动、目前没问题。本次变脉宽实物动作按用户观察验证通过，证据 `evidence/20261006T114234Z-user-servo-motion.json`。维持此前用户要求的暂停状态，本轮未访问板卡或发送START。隔离后电平、精确角度及长期稳定性尚未测量。以下为历史过程记录。

最新09:57 UTC：新候选 `aura-pin3-sweep`（BUILD `53fd5a67`）已加载并通过板端身份/寄存器核验，START 后由用户要求暂停，现已 STOP 回到低电平空闲（status4）。PWM 参数为50Hz、1.4/1.6ms各保持50帧交替。用户报告VIB接J2.3；实际隔离后波形、舵机动作仍未验证。证据：加载 `evidence/20261006T094513.906432Z-uart-load-idle`、START `evidence/20261006T094926.687288Z-uart-start`、暂停STOP `evidence/20261006T095708.091511Z-uart-stop`。旧固定应用被候选替换；回退文件哈希已在加载前核验并保留。

本轮加载脚本首次运行因错误要求官方基准应用作为唯一当前活动应用而安全拒绝；只读检查确认板上实际为先前验证的 `aura-pin3-pwm`，未卸载或改变PL。随后将装载/回退基线修正为旧PWM并校验其三个安装文件SHA，重新执行后 prepare/extract/install/unload/load 全部通过。Scratch 和 STOP 自检均通过，START 为status7、持续模式；用户随后要求暂停，STOP返回status4。当前candidate仍加载但不输出PWM，servo_actuation_verified=false。

以下带时间段落保留过程事实。

UART上传 `evidence/20261006T092753.795080Z-uart-stage`：58611字节、49帧及最终SHA核验通过，目标 `/home/root/aura-pin3-sweep-stage/20261006T092753.795080Z/aura-pin3-sweep-stage.tar.gz`，console_echo_restored=true。上传仅新增暂存文件，未切换PL。

随后原项目只读inspect `/home/ghmd/kv260-j2-pin3-pwm-e10-20261006/evidence/20261006T093044.336586Z-uart-inspect` rc0、status5、同boot `2a95bf6d-fea6-46e7-88aa-12f92eb40551`/BUILD `2a3aca85`，PL0实际99999999Hz、period1999980/pulse149999/RUN_FRAMES0/PULSE_US1500，仍在运行，回显恢复。它是原固定程序的回读，不冒充新摆动候选的板测通过。新候选BUILD仍为 `53fd5a67`，固件为 `aura_pin3_sweep.bit.bin`。

最新准备结果 `evidence/20261006T093149Z-sweep-ready-staged-not-started.json`，同步PREPARATION_STATUS/CURRENT_BENCH。下一步在VIB实物针脚确认后受控停止/恢复原程序，加载新候选默认低、核对新BUILD/ABI/参数、SCRATCH/STOP后START；这是待执行步骤。还需观察舵机实际往返和隔离后波形，不将离线仿真视为实物动作验收。

09:28 UTC最新：构建与48项离线工件核验全部通过，Linux包和加载归档完成，串口上传进行中。尚未加载/START；VIB实际连接针脚仍待用户确认。以下09:13段落保留当时状态。

构建 `evidence/20261006T091347.464129Z-build`：WNS+6.869ns、WHS+0.030ns、DRC错误0，E10/LVCMOS33/Bank45/DRIVE4/SLOW，20 ns输出预算、slack15.002ns；位流、BIN载荷和XSA内嵌位流一致，构建/仿真精确RTL和参数一致。最终核验记录 `FINAL_VERIFICATION.json`，48项全部通过。一次核验调用早于XSA/结果导出完成，因build_result.json不存在退出；待完整构建退出后重验通过，并给核验入口加未完成快速拒绝，未冒充提前通过。

设备树由本候选XSA独立生成，官方2022.2仓库commit `24d29888d0048f26e4f3d6e0b7cd655aede94f31`。沙箱内生成因Xvfb显示环境失败，原尝试保留在 `evidence/linux-overlay-generated-sandbox-attempt-20261006T092347Z`；沙箱外重跑成功，生成的pl.dtsi与新XSA身份记录在 `evidence/linux-overlay-generated/generation.json`。

Linux包 `evidence/20261006T092557.549706Z-linux-package`：新APP `aura-pin3-sweep`、固件 `aura_pin3_sweep.bit.bin`，clock99999001、AFI14=a00/15=0、reg80080000/1000及与基线合并检查通过。加载归档 `evidence/20261006T092714.791754Z-pwm-board-stage/aura-pin3-sweep-stage.tar.gz`，58611字节，SHA256 `120ce61a6bfe7091a0c97ef18a81044e39be8389bbaae0405ca19046e319c045`，8条目与7文件内容核对通过。

已实际运行本地加载器验证前置检查：VIB实体针脚未确认时，入口报 `The intended connector pin has not been confirmed`，在打开UART前退出。没有通过修改确认事实绕过保护。旧固定程序CURRENT_BENCH的complete保留true，表示既有板端控制核验完成，不表示舵机动作通过；动作状态另记servo_actuation_verified=false。

2026-10-06 09:13 UTC：完成代码和仿真，Vivado构建进行中。新程序默认禁用，START后输出50 Hz PWM：1.4 ms保持50帧，再1.6 ms保持50帧，反复交替。STOP/reset立即输出低，重新START从1.4 ms段首开始。脉宽只在帧边界切换。

独立目录 `/home/ghmd/kv260-j2-pin3-sweep-e10-20261006`，BUILD `53fd5a67`、ABI `0x20000`。尚未上传、加载、START或取得舵机动作证据。原固定PWM仍引用最近08:40板测状态，不将旧板测通过状态继承给新候选。

## 已完成验证

- `evidence/20261006T091046.196476Z-sim`：11组参数与波形检查通过，包括一秒保持、每帧切换、99.999001 MHz计数、无效范围拒绝、重复START、STOP与reset。
- AXI仿真通过16种WSTRB、AW/W先后及同时到达、响应背压、错误命令、复位清除半事务、脉宽寄存器只读；总线活动期间PWM仍按完整帧交替。
- 新AArch64访问器编译与反汇编检查通过，32位ldr/str及dsb sy，主机架构拒绝。START检查busy位，允许瞬时低相位，不要求每次读取都处于高电平。
- 串口封装长度检查通过，最大3791≤3800；板卡CID、boot/固件/归档哈希、时钟和全部静态参数核验保留。
- 原项目复用源文件哈希未变；没有复制旧生成RTL/位流/板测结果。

初次沙箱内xsim编译与elaboration通过，但启动发生Tcl工具异常，未作为仿真通过。经授权沙箱外重新运行得到上述完整通过结果。串口初版封装3855字节超限，在硬件操作前拒绝；压缩重复参数检查与冗余遥测后通过，未删除身份保护条件。

## 未完成与上板条件

Vivado最终引脚E10、时序、DRC、位流/XSA身份、Linux设备树/归档核验待构建结束后执行。

用户已经授权写持续动作程序；缺的是实物接线信息。用户明确通过隔离模块接舵机，共享图仍为旧J2.1，但新旧两个当前候选的实际PWM均选J2.3/E10。VIB实际输入针脚待用户回复，不把文档差异当作已证实接错。本候选加载器接受已确认的隔离接法，但在 VIB→J2.3 与独立适当供电确认缺失时明确拒绝部署。实际供电电压、VOB和舵机S/G波形、实物动作仍未验证。

接线与测量详见 [隔离链路审查](/home/ghmd/kv260-j2-pin3-pwm-e10-20261006/ISOLATOR_WIRING_REVIEW.md)。GND1/GND2按隔离方案各用本侧参考地；不得把旧直接共地解释套在这里。

这是位置来回变化测试，不能使普通DS3230连续单向转圈。实物角度尚未校准，不保证某个精确角度；停止PWM也不等于舵机动力电源断开。
