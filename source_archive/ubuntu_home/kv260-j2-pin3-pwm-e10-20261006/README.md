# J2.3/E10 连续 PWM

09:31 UTC更新：新[小幅持续摆动候选](/home/ghmd/kv260-j2-pin3-sweep-e10-20261006/README.md)已构建、核验并上传暂存，尚未加载/START。本固定程序最新只读inspect `evidence/20261006T093044.336586Z-uart-inspect` rc0、status5、同boot/BUILD，仍为50 Hz/1.5 ms持续运行。隔离模块VIB实物接脚待确认；不要把新候选已上传当作已经切换输出。

08:56 UTC最新：用户报告舵机完全不动，补充信号经过隔离模块。共享资料确认DS3230、5 V方案、ADuM1201 VIB→VOB→SVPDB-8S信号1；旧共享图仍选J2.1，而当前PWM在J2.3，VIB实际输入针脚待核对。当前1.5 ms是固定位置指令，无动作不等于器件损坏；隔离后输出及舵机端供电尚未测。本轮没有新的硬件动作。此前直接共地的解释被隔离方案取代，各侧使用本侧参考地，不跨接GND1/GND2。见 [隔离链路核对](ISOLATOR_WIRING_REVIEW.md)。以下时间段为历史记录。

2026-10-06 08:03 UTC：已加载并START，当前J2.3/E10持续PWM运行。新BUILD `2a3aca85`，同boot `2a95bf6d-fea6-46e7-88aa-12f92eb40551`，SCRATCH/STOP/START/inspect均通过；START status7、inspect status5均表示正在运行，不把瞬时低相位误读为停止。实际板端时钟99999999Hz，计算周期19.9998002ms、高脉宽1499.990015us，约50Hz/1.5ms。示波器电平/周期/脉宽仍待用户测量。52项离线核验通过，WNS+6.864ns、WHS+0.022ns、DRC错误0。完整状态及改动清单见 `BOARD_TEST_STATUS.md`。

本程序复用已核验PWM内核，输出改为已测得固定低0V/固定高3.3V的J2.3/E10。独立重建位流、XSA、访问器和Linux包，没有复用固定高程序的通过状态。

08:10 UTC更新：用户图片已看到符合预期的脉冲结构，平均值231mV；按网格估计高低平台约3.3V/0V、周期20ms、高脉宽1.5ms。图片含边沿过冲，数值高值/低值/周期/正向脉宽及短地线复测待完成，见 `BOARD_TEST_STATUS.md`。下文“尚未完成”指完整数值验收，不表示没有收到图片。

目标：50Hz、20ms周期、1.5ms高脉宽、7.5%占空比；START后持续输出，STOP/reset低。实际引脚J2.3→HDA12→SOM240_1 D20→E10，LVCMOS33/Bank45/DRIVE4/SLOW。电平预期0–3.3V；万用表直流平均约0.25V。PWM示波器测量尚未完成，原J2.1低电压根因未定位。

08:40 UTC最新：用户已确认信号J2.3、适当独立电源和共地；实际触点未独立核验，型号和数值供电电压未单独报告。已执行STOP→START并再次只读inspect，三次rc0、同boot/BUILD，原50Hz/1.5ms PWM持续运行。未改源码/位流/脉宽，舵机实际动作等待用户观察，不能仅凭寄存器宣称动作成功。当前接线记录见PHYSICAL_CONNECTION.json，重启结果见 `evidence/20261006T084052Z-servo-pwm-restart-result.json`。
