# 首次定位与有限往返测试结果

UTC2026-10-20 08:12—08:13。用户在已说明首次定位可能明显转动、需要现场观察后明确要求：“那现在就试一下”。本轮按已准备的2秒计划执行一次，不重复扩大幅度。

**硬件命令接受及关闭输出回读通过；实际机械响应待现场反馈。** 这次发出了台架测试命令，不是fixture回放，也不是摄像头闭环跟随。没有把1500µs当作已经标定的机械零点。

## 执行与验证

- 串口预检确认同一boot `3e1add36-b917-4289-91dc-699348528782`、联合固件operating、准确的联合VART路径；相机/身份正常约9.92Hz，GUI空闲。GUI已更新到avatar-performance/candidate-8049378caf0e，本轮使用实际运行版本，不覆盖旧GUI。
- 执行前一轮冻结的 `first_pulse_bench.py`，5590字节，SHA256 `919a590181e649680d91c734724892a84d5a17469bb66320efb89db804bc5d51`。boot/FDT、CID、8份程序/4份固件、活动APP及Native独占传输/ID/ABI/build门槛通过后才设置权限。
- 序列为1500→1504→1496→1500µs，各约0.5秒；配置100ms硬件租约，循环提交并核对ACK、session、epoch和目标，每段核对脉宽寄存器到达目标。共接受46条命令，最后一条记录在1979.79ms；含guard/加载的脚本总耗时3.643秒。
- finally STOP、传输关闭及随后重新打开的独立读回均确认输出许可清零：flags=0、lease_left_ms=0、active=false、armed=false。最后ACK=46、width_us=1500；ACK保留不代表仍在输出。
- 相机PID106060、GUI PID132404，前后均active且PID不变；相机检测计数30758→30805、约9.92Hz、identity_recognition=true、相机/检测无错误。没有重启服务、切位流、录音/播放，未修改身份/GUI/HDMI或语音配置。

板端结果在 `/home/root/aura-pan-follow-20261020/first-pulse-01/`。同名事务和结果用exclusive-create保护，通信异常时只读取结果，不重跑动作。原始UART留Ubuntu私有目录。

## 仍待确认

尚无外部示波器/逻辑分析仪测量，也没有收到本轮用户对转动、方向、卡滞/抖动/异响的反馈。因此仅标记为“有限测试ACK/STOP通过、机械观察待确认”。±4µs是脉宽偏移，不换算为未经测量的角度。

已询问现场观察，收到反馈后再决定是否核对中位/方向或检查信号和供电。保持输出关闭；不自动重复、扩幅或开始跟随。前一阶段的边缘目标/源超时问题仍待处理，完整实体跟随尚未验收。

## 文件

- `evidence/bench.json.gz`、`result.json.gz`：完整ACK和独立最终读回，包含两端服务状态，不含图像/姓名/特征/身份库。
- `evidence/response.json`、`status.json`、`authorization.json`：过滤摘要、串口传输校验和本轮授权范围。
- `evidence/first_pulse_bench.py`：板端回读的实际执行脚本，与上一轮冻结SHA完全一致。
- `audit/board_first_pulse_execute.py`：本轮已执行的固定事务；`board_first_pulse_export.py`只读导出。审计用途，不作为重复动作指令。
- [核验清单](verification.json)：每份工件长度/SHA。

前置平台和跟随限制见[联合平台与实况接口](../2026-10-20_pan_axis_integration/README.md)。Windows独立接收以其回执为准，本轮不代填。
