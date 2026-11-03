# 1490→1470µs有限修正

用户确认前一次大幅往返“看清了”，但1490µs仍略向右，要求再转一下。结合此前增脉宽加重右偏的现场反馈，执行一次1470µs、2秒有限试步；用户随后回答“还是朝右”，因此本点没有被确认为正前方，进一步1450µs试步另存[第五次定位记录](../2026-10-20_pan_midpoint_step05/README.md)。

精确boot/FDT/CID/联合固件及程序SHA、Native独占、ID/ABI/build、初态epoch5/ACK208/width/reference/target1490守卫保持。新epoch6，初始化测试参考1490；100ms租约、硬件斜坡、finally STOP和独立终态读回保持。46条连续ACK通过，最后事件1993.32ms，目标1470；独立终态flags0/lease0/width1470/reference1490/target1470/epoch6/ACK46，输出许可关闭。没有建立正式机械参考或启动自动跟随。

相机106060和GUI162389前后均active/PID不变，相机约9.93Hz、identity_recognition=true、无相机/检测错误。此次GUI已IDLE/STOPPED，前一次GUI启动问题不在本任务中修复或重启；不把服务恢复归因于转轴试步。身份状态接口所读字段UNKNOWN仍单独记录。

主机语法、默认计划、单目标1470/2秒/100ms、缺确认及非板端拒绝通过；先传送并校验脚本、没有硬件输出，发出开始提示后短启动器只运行一次。初次误用短脚本传输器因长度超限在主机退出，未连接板卡；改用已有分片传输工具准备成功，没有重复执行动作。未改生产代码/服务/位流/HDMI/语音配置。

- [现场原话](field-input.json)、[计划](plan.json)、[主机检查](host-checks.json)、[台架源码](midpoint_step_bench.py)
- [实板摘要](evidence/results/response.json)、[完整ACK记录](evidence/results/bench.json.gz)、[独立终态与服务状态](evidence/results/result.json.gz)
- [冻结清单](verification.json)

物理中位、固定脉宽停稳模式、图像跟随极性和外部波形仍未验证。仅共享过滤证据和自有脚本，不含原始UART、图像或身份库。
