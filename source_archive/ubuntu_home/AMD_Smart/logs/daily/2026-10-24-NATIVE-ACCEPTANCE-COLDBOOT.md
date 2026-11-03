# 现场身份、真实断电与未闭环问题更新

root按用户单终端限制执行；未创建新代理。生产r4模型/阈值/库未变。新证据[现场检查与真实冷启交付](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-24_native_acceptance/README.md)。

本人首轮106判定92KNOWN/14UNKNOWN=86.79%，未过预设90%；用户随后确认中途转头，原报告保留并标为混合姿态。按用户要求明确指示、收到“已就位”才重启正脸60s：106/106判定认对、61/61界面点正确，无过期结果。未登记者明确开始后60s：107UNKNOWN/0KNOWN，61/61界面点拒绝。两人并排20s：21双脸点/0单身份绑定/0新增匹配。均YOLO约9.93–9.95Hz、新primary/optional超限/gap0，配置398ece…/库ee22b…保持；不将单人单场景结果外推总体准确率/FAR。

用户明确可配合真实断电。cold_policy6项纯检查通过，sealed helper c6b338dc…先验证normal stop/checkpoint/旧PID退出/锁空闲再OS poweroff。串口停止响应后用户按指示重新接通；上电后读取持久关机报告确认safe_to_disconnect_power/poweroff_scheduled均true、无failure，精确checkpoint和archive全量/哈希匹配。

**必须更新长尾结论：** 上一原生期源PID2174关机前primary98191/overs2，YuNet34373准入/34365完成/8未提交，超限4、attempt4/recover4/phaseRUNNING；SFace1862准入/1850完成/12未提交，超限0。不能继续说原生期累计0超限或已根治。计数与恢复已保留，但没有4次逐事件trace，不能定唯一等待原因，也不能用新kernel零值抹除。

新boot b7871498-884a-4190-8ba1-6876a63a3f6c，相机1294/GUI1295/X1076自动恢复，GUI从activating到active，无手动服务重启。60.071522s启动后YOLO9.9548Hz、SFace新10、0新primary/optional超限gap，source/dest boot与previous_kernel_counters精确对应。**实体显示冷启失败**：用户报告闪屏并明确这次已拔插HDMI恢复正常。软件启动setup有live EDID128/727d3e18…、1024×600、startup_output_retrained=true/off2s，动作时刻未精确采集，不据此推定初始EDID始终正确。此轮只能判业务恢复通过/整机显示未通过。

用户屏幕微雪、USB接KV260兼供电触摸、无独立电源Hub，具体型号未确认。已核查官方C系列与Microchip供电/数据原理，未套用未知型号端口或寄存器。用户最新说准备更换USB供电；已暂停板端操作，要求HDMI和板卡主电源先不动、5V输出，普通充电器触摸数据暂不可用；当前已手工HDMI恢复，换供电后正常不单独证明冷启解决，USB重新供电也会重置屏幕。

后续恢复此任务先核对新boot/PID，不可再用旧a692固定脚本操作。尚需显示供电/握手对照、原生fault事件持久留证与调度归因、严格同输入CPU/DPU收益、实际旧码回退和更广角度/人群验收。未改Windows回执、未保存人脸/向量、未主动开麦/播放或重置显示芯片。
