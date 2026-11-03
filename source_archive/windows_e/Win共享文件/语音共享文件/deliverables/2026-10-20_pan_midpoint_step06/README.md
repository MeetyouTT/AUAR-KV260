# 1450→1430µs有限修正

用户反馈1450µs后“还有点偏右”，继续既有定位调试，执行一次1430µs、2秒试步。46条连续ACK、阶段脉宽端点和独立停止读回通过；终态flags0、lease0、width/target1430、reference1450、epoch8、ACK46，输出许可关闭。1430是否已正前方仍待现场反馈。

保留同boot/FDT/CID、联合APP及程序固件SHA、Native独占和ID/ABI/build守卫。初态精确要求epoch7/ACK46/width1450/reference1470/target1450且flags0/lease0；新epoch8以1450作临时测试参考，100ms租约、硬件斜坡、finally STOP及关闭后独立读回保持。未建立正式机械参考、修改跟随极性或启动自动跟随。

主机语法、默认仅计划、单目标1430/2秒/100ms、缺确认及非板端拒绝检查通过。先传送准备并校验SHA，没有动作；发出开始提示后短启动器执行一次。实际源码与回传脚本逐字节一致。原1450等冻结工件保持，最新现场反馈单独记入本目录。

相机106060和当前GUI165304前后active/PID不变，约9.93Hz、identity_recognition=true、无相机/检测错误；GUI IDLE/STOPPED、身份字段UNKNOWN。没有修改或重启生产服务、切固件或改HDMI/语音配置，不将身份状态字段当准确率结论。

- [现场反馈](field-input.json)、[计划](plan.json)、[主机检查](host-checks.json)、[台架源码](midpoint_step_bench.py)
- [实板摘要](evidence/results/response.json)、[完整ACK记录](evidence/results/bench.json.gz)、[独立终态与服务状态](evidence/results/result.json.gz)
- [冻结文件清单](verification.json)、[前一次1450试步](../2026-10-20_pan_midpoint_step05/README.md)

固定脉宽停稳模式、机械中位、图像控制符号及完整跟随仍未验收。仅共享过滤后的状态和自有脚本，不包含原始UART、图像或身份库。
