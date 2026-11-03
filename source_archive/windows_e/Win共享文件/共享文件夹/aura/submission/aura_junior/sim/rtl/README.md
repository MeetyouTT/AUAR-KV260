<!-- aura-architecture-generated -->
# RTL 正反例 / AXI / PWM / 到期仿真

模块：M8 / `rtl_verify`；负责人：A；目标位置：Ubuntu 仿真。

当前证据层级：**接口或部分实现**。

输入：冻结合同 / 时钟 / 正反例。
输出：波形 / 自检查结果。

现有源码/证据来源：

- `/home/ghmd/kv260-visual-servo-20261007/tests/tb_servo.sv`
- `/home/ghmd/kv260-visual-servo-20261007/scripts/run_sim.py`

待补：参考仿真代码已有；新绝对期限与完整边界仿真待做。

关联内部验收：T10、T11、T12。

这里是按总框图建立的交付位置和接口说明；本次没有把占位包装为已实现功能。最终工程包必须放入实际使用的源码、输入和实测，而不能仅交本说明。

<!-- aura-structure-details -->
## 复核后的目录职责

主责：A；运行/使用位置：RTL 仿真。

内容：AXI/COMMIT、到期/停止、重放、复位、恢复的自检查用例。

边界：对新源期限核新增用例；既有相对租约 testbench 仅验证旧核。

依据：P2、P3，见 report/structure_detail.md 的依据登记。

现有来源：

- `/home/ghmd/kv260-visual-servo-20261007/tests/tb_servo.sv`

目标目录已建立；本轮没有将实际源文件迁移到此处。
