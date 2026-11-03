# 转轴 VSRV/2：联合固件离线构建完成，实板待验

**2026-10-24已完成DPU＋VSRV/2源工程联合实现、位流/XSA、独立路由检查点复核、驱动配对及封包。** 本任务没有连接板卡、切固件、重启业务或发运动指令；实体转轴是否改善尚未验证。

[完整候选ZIP](aura-vsrv2-joint-778d2512-offline.zip) · [候选清单及SHA](firmware/candidate-manifest.json) · [机器状态](PROGRESS.json) · [接板与回退安排](OPERATIONS.md)

ZIP为9,055,885字节，SHA256 `395b499385d0539c16be32e1e76213467ed70a502461467f0b8033d7f97f15ee`。复制、ZIP CRC和逐文件SHA核对通过；Windows接收未确认。状态仍为`OFFLINE_VSRV2_BUNDLE_PENDING_BOARD`、`deployable=false`，不伪造正式QUALIFIED放行。

## 已完成的验证

| 项目 | 实际结果 |
|---|---|
| 源工程/驱动身份 | VSRV/2、build `0x778d2512`、ID `0x56535256`、AXI `0x80080000/0x1000`；Native为AArch64，仅编译未加载 |
| 布线 | 200,476条可布连线全部布通、布线错误0 |
| 最终时序 | WNS0.001ns、WHS0.000ns（报告精度）；setup/hold/pulse失败端点均0，脉宽余量0.071ns |
| 总线偏斜 | 最差余量2.782ns |
| DRC | Error/Critical Warning均0；保留663条原平台Warning，不称零告警 |
| 独立复核 | 新Vivado进程重新打开最终DCP；器件K26、E10/LVCMOS33/DRIVE8/SLOW、寄存器输出INIT0、100MHz控制时钟及DPU/VCU结构通过；正式时序/布线报告与实现结果一致 |
| 源码/软件 | 原51项回归、13项HWH/BD/连接检查、8项报告接受/拒绝检查、14项新只读/ID-STOP/有限步进工具检查通过 |
| 输入/PWM | 真实GTK/X Server六项（假硬件）及3套RTL台架通过，含9个100MHz/50Hz完整脉冲/边界场景 |
| 工件配对 | XSA内HWH与本轮生成HWH逐字节相同；位流配置数据7,797,692字节逐字节相同，6项格式/拒绝检查通过 |

静态资源为LUT66,969/57.18%、寄存器124,189/53.02%、BRAM93.5/64.93%、URAM56/87.50%、DSP710/56.89%。这不是运行忙时或模型加速倍数。报告仍有6个输入/2个输出缺外部delay约束，沿用平台限制，不能当完整外部电气验收。

源码在`candidate/`，构建/审计/台架工具在`scripts/`，报告在`evidence/implementation/`及`evidence/independent-audit/`。本机完整工程和DCP保留于`/home/ghmd/aura-pan-joint-20261023`；脚本依赖本机既有2022.2工具和源工程，未做另一台电脑从零复现。

## 配对方式与历史失败

`write_hw_platform -include_bit`重新生成位流，头部时间由06:09:46变为06:12:25；设计、器件及实际配置数据完全相同。保留原件，封包采用XSA内的确切位流，经bootgen生成`.bit.bin`；比较证据见[evidence/bitstream-pairing-verified.json](evidence/bitstream-pairing-verified.json)。没有只改哈希放行不同配置。

10月23日08:43开发电脑关机导致首次路由中断，旧“运行中”状态与过滤关机记录保留。10月24日从固定SHA的布局DCP继续，由独立低优先级用户服务完成全部步骤；服务已正常退出、ExecMainStatus0。早期XSim沙箱启动异常和错误`-mt 1`参数日志保留，改为`-mt off`后取得真实PASS。报告解析器的重复计数覆盖缺陷由反例发现并修正。

## 下一步与另一终端的边界

当前统筹仍由另一终端管理板卡。本任务交付完整候选，未抢占串口或修改其业务。接板时先读取最新boot/FDT、活动固件、相机/GUI根及原生r4的持久故障记录；保留当前r4及身份库，不能重放旧GUI/相机整包或只改boot字段解除保护。

先核对当前DT并准备成套恢复，再安装/切换候选、做ID/STOP和真实DPU共存；随后按用户“无测量设备也可试一下”的授权，现场观察2秒、最大5µs的小步台架。初始脉宽须根据本次姿态选定，复位1500和历史1420均不能自动视作当前姿态。外部波形继续未测，真实反应和停止须另取反馈，暂不启用自动跟随或开机ARM。

后续板测另建新日期交付，保留本轮已封存候选与证据，不覆盖成套ZIP或把这里的离线结果改写为实板通过。
