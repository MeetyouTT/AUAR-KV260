# 中位校准第一步：1504µs有限保持

UTC2026-10-20 08:26。用户确认首次测试“转动了”，随后说明停下后的镜头“偏右”。因此1500µs记录为用户报告的右偏测试点，尚不是机械正前方。

继续既有转轴调试，在此前已测试的1496～1504µs范围内，将测试点微调到1504µs并保持约2秒后关闭输出。此次用于比较姿态，不预设脉宽增大必定向左，不建立PhysicalReference、不启动自动跟随。

**1504µs命令/阶段脉宽读回及停止复核通过；是否更靠近正前方仍待现场反馈。** 本轮46条连续ACK，所有目标均1504µs，最后事件1993.23ms；含guard/加载的脚本耗时3.443秒。100ms租约、finally STOP和Native关闭保护保持；随后独立打开传输读回flags0/lease0/active=false/armed=false、width/target/reference=1504、ACK46，输出许可已关闭。1504寄存器值不是已完成机械标定的结论。

执行脚本从上一轮已测有限台架流程派生，仅改变测试点/标签并增加“初态必须ACK46、width/reference/target=1500、未解锁、租约0”的门槛。精确boot/FDT、CID、程序/固件、活动联合APP及Native独占/ID/ABI/build门槛继续核对。语法、默认仅计划、单目标1504/2秒/100ms、无确认拒绝、非板端拒绝以及finally STOP源检查通过；随后实际板端执行通过。实际脚本SHA256为 `2706fac7aa4aad8935c1b7e4407cafcf408bf06c8e57de387b5fb5e331a633c4`。

前后相机PID106060、GUI PID141059均active/PID不变。相机仍是handsfree/0c0a8ab46ec2，GUI现场已更新为handsfree/resume-049c88498ae0，本轮使用实际版本，没有恢复旧GUI。检测计数38712→38758、约9.92Hz、身份ready、无相机/检测错误；本轮未重启服务、切固件或修改身份/相机/GUI/HDMI/语音配置。

板端事务 `/home/root/aura-pan-follow-20261020/midpoint-step-01` exclusive-create防重跑，确认后仅执行一次。已询问本步相比原1500µs是更接近正前方、右偏更明显还是几乎无变化。反馈到达前保持输出关闭，不连续自动寻中或扩大范围。此前卡滞/明显抖动/异响未获明确答复，仍记未知。

用户原话和本步目的见 `field-input.json`，计划/主机保护检查分别在 `plan.json`、`host-checks.json`；原始硬件结果/独立停止复核为 `evidence/bench.json.gz`、`result.json.gz`，过滤状态及传输核验也在evidence；本轮执行/只读导出工具保存在audit供审计。原始UART、图像和身份库不共享。每份工件见[长度/SHA清单](verification.json)，此前13份首次测试、5份现场补记和28份联合接入工件保持冻结。
