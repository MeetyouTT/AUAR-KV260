# 持续联动 r7：已重新运行，等待左右实体验证

UTC2026-10-26 04:39：用户问“现在怎么办”。只读复核r6运行105.152s，已有208次左侧/84次右侧READY包，但只有4ACK/2次目标变化、宽度1447..1448、20段，不能视为连续跟随有效。随后取得15次真实只读face observation：13 READY/2 EXPIRED，HTTP13.95..81.3ms，READY检测锚龄290..492ms，输入时效压力仍存在；相机/DPU调度的完整根因尚未证实。

本轮修正continuous_face_control.py：先验证新到的帧、上下文、来源顺序和检测锚；合法新源可替换旧的已过期感知源，避免在MONITORING阶段因旧源截止无谓清掉确认历史。相同源不能刷新截止；失效包、真实丢脸、换上下文仍停止；已过期硬件lease绝不被新图“复活”，必须停止重新确认。

run_face_motion.py将运行确认从3张调整为2张新图，检测器原有确认/质量和多脸保护保持。保留r6连续模式、左脸框/右中心、polarity=-1、10us/s/4us每新源/1400..1600软件范围、250ms图像/500ms锚/20ms余量及10秒运动段上限。未扩大速度或自动回中。

61项软件回归通过，新增“合法新锚替换旧过期锚”和“新锚不能救回已失效硬件lease”检查。将记录中的512条时序/位置重建为FakeDevice软件回放：r6为1次目标变化、r7为7次，均无fatal；重建不包含全部原始包字段，并非实体延迟或机械效果证据。初次回放因浮点重建使贴边box超过640发生INVALID_BOX，已仅在回放重建中钳制到实际画幅后重跑；真实输入未因此改写。

正常通过GUI pan_stop结束r6，STOP/lease0/READY后交接r7；17源闭包及258GUI pins通过。真实consumer/GUI再次运行，camera13537、GUI与editor未重启，故障primary2/optional0、0保持。启动后8.716秒242 READY均在线内、3 EXPIRED，0ARM/ACK、1447us保持、fatal=false，符合区内不动；新版本左右机械跟随与平顺性尚待用户观察。当前保持运行，停止按钮可结束。

改动快照：[continuous_v10r7](continuous_v10r7/)，证据：[CONTINUOUS_R7_VERIFICATION.json](CONTINUOUS_R7_VERIFICATION.json)，重建软件回放：[R6_R7_RECONSTRUCTED_TIMING_REPLAY.json](R6_R7_RECONSTRUCTED_TIMING_REPLAY.json)。25源文件指纹核对，未共享人脸图像/身份库/模型/原始UART，Windows回执未代填。
