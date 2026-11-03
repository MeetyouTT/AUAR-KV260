---
name: command-guard-validation
description: 核对 FPGA 执行器命令轨迹中的重复序号、目标越界、STOP、QUIESCE 与租约到期，或用已冻结的 KV260 wide RTL 复跑保护逻辑仿真。
---

在本技能目录执行 python3 -B scripts/run_checks.py。它顺序验证合同指纹和正常、违规、证据不足三类轨迹。审核新日志时，用 scripts/validate_trace.py 传入 --trace 和 --profile，按一次开机的单调时钟对齐。记录缺少提交决策或主动停止回读时保留 UNKNOWN。

需要 RTL 时序证据时，按[复跑说明](readme.md)的“四套 RTL 仿真”运行 scripts/run_rtl.py，保留每个测试台的成功标志与具体参数。将结果区分为提交轨迹、仿真脉冲和物理引脚读数。报告机构是否真正停止，需要现场观测覆盖相同时间段。
