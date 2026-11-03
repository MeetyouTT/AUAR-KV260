# 1420～1580µs放大固定往返实测

用户要求“动作再大一点”，完成一次1580→1420→1490µs固定往返，每段3秒，共9秒。实际208条连续ACK、三个阶段端点及独立停止读回通过；最终flags0、lease0、width/reference/target1490、epoch5、ACK208，输出许可关闭。保留硬件每20ms最大4µs斜坡和100ms租约，没有开启自动跟随或修改跟随默认范围。

用户随后反馈“看清了，现在还有点向右偏转，再转一下”：本轮动作已可见，1490µs仍有右偏，因此不是已确认的机械正前方。下一次1470µs有限修正另存[第四次定位试步](../2026-10-20_pan_midpoint_step04/README.md)。前两段具体方向、固定脉宽到位后停稳还是持续转动、图像坐标极性仍未确认。

准备阶段没有硬件输出。第一次启动因GUI的8783端口拒绝连接，在创建动作事务和ARM之前退出；独立只读复核确认事务不存在。仅将台架启动器的GUI状态读取改为尽力记录，保留身份非ENROLLING/SAMPLING、相机健康及全部硬件守卫；重新准备、提示开始后实际执行一次。原始启动器、修正启动器、两次准备和失败/未执行复核证据均保留。

相机PID106060前后active，约9.93Hz，identity_recognition=true，无camera/detector错误。GUI前后均activating、PID161498，HTTP状态不可用；不记为GUI健康通过，本轮没有修改或重启它。身份模块状态读取为UNKNOWN，不等于身份业务全部验收。未改生产源码、服务、位流、HDMI启动配置或语音参数。

- [计划](plan.json)、[主机保护检查](host-checks.json)、[现场反馈](field-input.json)
- [台架源码](wide_sweep_bench.py)，默认仅输出计划，真实运行有精确boot/初态和独占事务门槛
- [实板摘要](evidence/results/response.json)、[完整ACK记录](evidence/results/bench.json.gz)、[独立终态与服务记录](evidence/results/result.json.gz)
- [文件校验清单](verification.json)

证据使用主机UTC时间。仅共享过滤后的状态和自有脚本，不共享原始UART、相机图像或身份库。该记录是有限台架测试与现场反馈，不代表完整机械跟随已完成。
