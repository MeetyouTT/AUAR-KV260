# 转轴启停与旧点击修复候选

用户要求继续处理“点击左右时卡住，随后转轴大幅来回”。本轮完成驱动、界面输入和RTL候选集成及离线验证，保留板端运动隔离；**没有把修复加载到板卡，没有发转动或停止指令，也没有解除保护锁。**

中位姿态已按用户确认保存，关联1420µs，见[中位记录](center_observation.json)。它不代替实际PWM和机构验证。现场大摆的最终物理原因仍未确认，前轮[故障机制复现](../2026-10-20_pan_stall_waveform/README.md)保持有效。

## 本轮实现

- [正常结束路径](runtime/aura/board/motion/manual.py)改为调用完整脉冲结束；[VSRV驱动](runtime/aura/board/motion/vsrv_driver.py)发送QUIESCE，最多等待25ms，核对上下文不变且flags/lease均关闭后才回READY。超时、许可失效或上下文改变会回退立即STOP并锁定FAULT，保留失败记录。用户停止、取消、异常和进程退出仍保留立即STOP。
- [RTL](rtl/visual_servo.sv)延续完整高脉冲结束和新周期租约余量检查，100ms手动租约、1400～1600µs范围、50Hz周期和每帧4µs斜坡保持。新测试复现前轮候选的边界遗漏：QUIESCE恰与新周期重合时会多发一帧；现同周期识别QUIESCE并阻止起脉冲。
- [输入校验](runtime/aura/board/motion/input_freshness.py)与[GTK扩展](runtime/aura/tools/pan_controls.py)读取原始GDK事件时间，并向同一X Server取当前时间，避免假设X时间戳与Python时钟同源。事件超过250ms、GUI心跳中断超过200ms、恢复后250ms窗口或取时往返超过100ms时拒绝点动。原始时间继续传给[独立进程](runtime/aura/board/motion/manual_process.py)，在IPC接收及身份采样预检后再次检查，不重新生成“新点击”。
- 点动必须来自按钮当前的原生释放事件和一次性内部凭据。程序直接调用clicked、JSON/HTTP伪造点动不能绕过；停止不受这一输入门槛限制。X11不可取时时拒绝点动。没有启用自动跟随。
- [Native协议](native/vsrv_protocol.h)及[C传输](native/vsrv_mmio.c)配对ABI2/build `0x778d2512`，增加QUIESCE白名单。旧ABI1/build14da0e60或旧v1固件不兼容，保持卡号/boot/固件、先flock后MMIO、32位访问和屏障检查。该build是候选身份，不能表示已经发布。
- [板端适配器](runtime/aura/board/motion/manual_vsrv.py)默认不放行：[配置模板](config/pan_manual.template.json)为disabled，且必须有字节固定、通过外部波形/实体反应/DPU共存验证的独立发布清单，才能打开Native。当前没有这种合格清单，不能靠复制文件启动运动。

## 实际验证

| 检查 | 结果与证据 | 边界 |
| --- | --- | --- |
| 新增故障/输入/IPC/发布门槛 | [28项通过](evidence/safe-completion-tests.log) | 假硬件，无MMIO |
| 原有点动/独立进程回归 | [23项通过](evidence/manual-regression.log) | 假硬件，含父进程GIL停顿 |
| 真实GTK与X Server事件 | [6项检查通过](evidence/gtk-input.json) | Xvfb/XTest，未使用实际相机或舵机 |
| PWM完整脉冲与边界 | [9场景日志](evidence/pwm-nine-scenarios.log) | 100MHz/50Hz数字仿真，非引脚实测 |
| 原AXI/协议及正常PWM | [协议](evidence/hdl-protocol.log)、[正常波形](evidence/hdl-nominal.log)通过 | 两个原HDL测试台 |
| Native | [主机协议测试与AArch64编译通过](evidence/native-build.json) | 未执行AArch64库；零build负例按预期编译失败 |
| 控制核独立综合 | [综合日志](evidence/ooc-console.log)、[利用率](evidence/ooc-utilization.rpt)、[DRC](evidence/ooc-drc.rpt) | 595 LUT、457寄存器、0 DSP/BRAM，DRC零违规；未做联合布局布线 |

九个PWM场景包括：高电平正常结束、1ms/2ms许可拒绝、真实100ms续期到期完整末脉冲、低电平正常结束、QUIESCE撞新周期不多发一帧、3ms最小许可下完整1600µs脉冲、帧边界余量最小时完整1600µs脉冲，以及立即STOP仍能截断。立即STOP的500.02µs截断是保留的紧急语义，不是候选已经消除全部机械风险。独立供电DS3230的断信号和紧急停止反应仍须实测。

边界竞态修复前的[RTL](evidence/boundary-before-rtl.sv)、[测试台](evidence/boundary-before-test.sv)、[输入哈希](evidence/boundary-before-inputs.json)、[预期失败日志](evidence/boundary-before-fix.log)单独保留；最终通过日志使用修正后的RTL。该失败是离线测试主动复现，没有板端动作。[综合时序估计](evidence/ooc-timing_estimate.rpt)不是联合平台布线后时序验收。

## 板端只读复查

UTC12:42的[隔离检查](evidence/board-readonly.json)确认同boot、保护进程256477存活且不打开/dev/mem，独立flock仍被拒绝。中心记录保持1420µs。相机仍106060，采集12.49Hz/检测9.92Hz，无错误；GUI为IDLE、error空。

UTC12:44按实际argv取得[活动版本](evidence/board-runtime.json)：已另切`aura-listening-timing-20261020/candidate-5a0cab12671b/runtime/aura`，其五个运动组件SHA与本候选修改前基线一致，GTK更新。新运动子进程276693的FAULT/EAGAIN表示连接被保护锁挡住；不是本轮驱动已部署，也不能据此删除锁。此语音/GUI更新非本轮发起，发布者与现场卡顿时序尚未确认。

候选只放在本目录，不覆盖活动业务源码、较新GTK/语音版本或旧冻结交付。Windows回执不代填。本机工件通过不表示Windows同步或实板业务验收通过。

## 复现与后续

在本目录执行软件测试：

```sh
PYTHONPATH=runtime/aura:runtime/aura/tests/framework python3 -B -m unittest discover -s tests -p test_safe_completion.py -v
PYTHONPATH=runtime/aura:runtime/aura/tests/framework python3 -B -m unittest discover -s runtime/aura/tests/framework -p 'test_manual_pan*.py' -v
PYTHONPATH=runtime/aura:runtime/aura/tests/framework xvfb-run -a -s '-screen 0 1024x600x24' python3 -B tests/check_gtk_input.py /tmp/aura-pan-gtk-result.json
```

[Native构建脚本](scripts/build_native.py)接收`--cross-cc`与`--out`，输出目录放本机项目外；不加载库或访问板卡。RTL用Vivado2022.2的xvlog/xelab/xsim运行`tests/tb_pulse_guard.sv`、`tb_servo.sv`、`tb_nominal.sv`，各自单独工作目录；独立综合入口见[synth_ooc.tcl](scripts/synth_ooc.tcl)。源码与证据SHA见[验证清单](verification.json)。

恢复运动前仍需完成联合DPU固件实现/时序、准确DTBO/XCLBIN及发布清单配对，先断开舵机测J2.3波形，再确认供电/断信号和实体反应，最后按本次用户中位记录完成机构标定。当前没有生成或加载新bitstream，没有电气/机械放行证据；保护锁继续保持。解除时须核对guard的boot/PID/命令和原因后结束保护进程，禁止删除`/run/aura-vsrv.lock`、自动解锁或重放旧动作。
