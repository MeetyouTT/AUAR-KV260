<!-- aura-architecture-generated -->
# 既有 VSRV：相对租约 / PWM / STOP

模块：M5 / `vsrv`；负责人：A；目标位置：KV260 PL。

当前证据层级：**已有有限板测**。

输入：影子字段 / COMMIT / STOP。
输出：有限许可 / 受限 PWM / 状态。

现有源码/证据来源：

- `hardware/rtl/visual_servo.sv`
- `board/motion/vsrv_driver.py`
- `/home/ghmd/kv260-visual-servo-20261007/BOARD_TEST_REPORT.md`

待补：有限板测已有；不是新的绝对源期限监督，数字引脚波形仍需测。

关联内部验收：T02、T10、T11、T12。

这里是按总框图建立的交付位置和接口说明；本次没有把占位包装为已实现功能。最终工程包必须放入实际使用的源码、输入和实测，而不能仅交本说明。
