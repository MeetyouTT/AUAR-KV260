# 摄像头准备完成后的联合 PWM 复核

2026-10-08 08:35 UTC。用户在“放稳摄像头、保留舵机当前位置”的操作要求后回复“好了”。先读取 ZIP README、B 执行手册相关章节、当前预览/机械基准记录和最新日志，然后推进候选加载前的复核。

## 完成与验证

- 新增 audit_joint.py / audit_joint.tcl：独立重新打开最终 routed DCP，核对 pad/寄存器初值/时钟/MMCM/DPU/VCU，生成时序、DRC、路由与 bus skew 报告，记录输入/输出 SHA，保持 deployable=false。
- 完整重跑通过，rc=0、offline_checkpoint_passed=true；J2.3/E10 唯一寄存器 PWM 驱动，初始化低，100 MHz 约束/MMCM 一致；WNS +0.001 ns、WHS 0、WPWS +0.071 ns，失败端点均 0；路由错误 0，bus skew 最差 +2.782 ns。原 DRC 警告、实现 Critical Warning 和外部时序缺口均披露。
- 新增 audit_metadata.py：检查源链已有 BD/HWH 与旧 M3 DT/主机合并树，保存原件和 SHA；原描述没有 servo_pwm，仍有旧音频模块，metadata_matched=false。继承地址信息与新板端地址实测明确分开；没有复制旧 HWH 冒充新发布。
- 新增 CALIBRATION_PENDING.json，记录用户准备反馈，实测脉宽/极性/三锚点保留 null、confirmed=false。新增电路复核报告及平台差异说明，同步 README、CONTROL_REFERENCE、SERVO_REFERENCE 和 NEXT_INTEGRATION。
- 本地新 Python 脚本语法、记录 JSON、实测缺值不能启用的标记、报告证据 SHA/链接检查通过。未修改运行控制算法或 RTL，因此未重复既有 35 项控制测试或 HDL 仿真。

首轮复核脚本错误使用 VCU 的短层级名 vcu_0，被检查拒绝；读取原 HWH/BD 确认为 vcu/vcu_0，修正并完整重跑通过。失败与成功证据分别保存，没有将脚本失败写成电路失败。无板端访问、PL 加载、PWM 写入或真实机械动作。

## 当前限制与下一交付

仅候选电路离线复核通过，真实随动尚未开启。下一项是匹配源平台 BD/XSA/HWH、加载所需 DT/XCLBIN 及访问 transport；随后做无动力联合板测和轻载标定。软件电路通过不代表 FPGA 电气故障已排除，也不代表舵机位置已测得。用户之前授权真实随动仍有效，无需重复获取动作授权。

详细原件：

- [电路复核报告](../../../kv260-visual-servo-20261007/FINAL_AUDIT_REPORT.md)
- [成功证据](../../../kv260-visual-servo-20261007/evidence/20261008T082835.411084Z-final-audit/status.json)
- [失败证据](../../../kv260-visual-servo-20261007/evidence/20261008T082307.745250Z-final-audit/status.json)
- [元数据差异](../../../kv260-visual-servo-20261007/evidence/20261008T082948.204026Z-metadata-audit/result.json)
- [待标定记录](../../../kv260-visual-servo-20261007/CALIBRATION_PENDING.json)
