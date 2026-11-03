<!-- aura-architecture-generated -->
# 单轴供电 / 限位 / 3D 机构与标定

模块：M5 / `servo`；负责人：A / B；目标位置：物理装置。

当前证据层级：**等待机构**。

输入：PWM / 动力 / 实际机构。
输出：方向、范围、位置与真实随动。

现有源码/证据来源：

- `config/servo_calibration.json`
- `/home/ghmd/AMD_Smart/logs/daily/2026-10-08-SERVO-VISIBLE-TEST.md`

待补：既有带电有限动作记录；机构、角度和机械停止验收等 3D 模型。

关联内部验收：T07、T10、T11、T28。

这里是按总框图建立的交付位置和接口说明；本次没有把占位包装为已实现功能。最终工程包必须放入实际使用的源码、输入和实测，而不能仅交本说明。

<!-- aura-structure-details -->
## 复核后的目录职责

主责：A/B；运行/使用位置：3D 模型到位后的实物。

内容：轴向、角度/PWM、限位、供电与停止输入标定记录。

边界：当前 WAIT；图像归一化偏差不当作已标定角度。

依据：P3、C11，见 report/structure_detail.md 的依据登记。

现有来源：

- `config/servo_calibration.json`

目标目录已建立；本轮没有将实际源文件迁移到此处。
