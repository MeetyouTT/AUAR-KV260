# 1470→1450µs有限修正

1470µs试步后用户反馈“还是朝右”，继续既有居中调试，将测试点小幅降至1450µs，保持2秒后STOP。实际46条连续ACK、阶段端点及独立停止读回通过；终态flags0/lease0/width1450/reference1470/target1450/epoch7/ACK46，输出许可关闭。是否已经正前方、动作是否改善右偏仍等待现场反馈。

同boot/FDT/CID/联合APP及程序固件SHA、Native独占、ID/ABI/build保护保持；初态要求epoch6/ACK46/width1470/reference1490/target1470且flags0/lease0。新epoch7以1470作临时测试参考，100ms租约及硬件限速保持，不建立正式PhysicalReference、不改镜像跟随极性、不启动自动跟随。

先从已冻结的前一步启动器派生并校验新脚本，准备阶段没有硬件输出，发出开始提示后短启动器仅执行一次。主机语法、默认计划、1450/2秒/100ms、缺确认和非板端拒绝通过。生产源码、服务、位流、HDMI和语音配置保持。

相机PID106060和GUI162389前后active/PID不变，相机约9.93Hz、identity_recognition=true、无camera/detector错误；GUI IDLE/STOPPED，本步读取身份状态KNOWN。这里只记录服务和状态字段，不作为真人身份准确率验收。

- [现场反馈输入](field-input.json)、[计划](plan.json)、[主机检查](host-checks.json)、[台架源码](midpoint_step_bench.py)
- [实板摘要](evidence/results/response.json)、[完整ACK记录](evidence/results/bench.json.gz)、[独立终态与服务证据](evidence/results/result.json.gz)
- [冻结文件清单](verification.json)

此前结果：[放大往返](../2026-10-20_pan_visible_direction_wide/README.md)、[1470µs试步](../2026-10-20_pan_midpoint_step04/README.md)。物理居中/停稳模式、图像控制符号及完整跟随尚未验收；原始UART、图像及身份库不共享。
