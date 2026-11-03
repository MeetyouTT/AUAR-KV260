# 2026-10-07 HDMI 蓝线反馈

UTC 07:00，用户反馈屏幕有一根蓝线。按资料包 README 和前日实时视觉日志接续排查，未更改摄像头程序、分辨率、FPGA 或舵机状态。

只读核验通过：当前 PID 56983 独占 video0，采集帧 16939→16976，检测/最终显示计数持续增加、error=null、stopped=false、Monitor is On。串口回显恢复。证据 [核验 JSON](../../../kv260-adaptation-check-20261006/evidence/20261007T070004.867617Z-realtime_verify/verification.json)。

实际 [X11 截图](../../../kv260-adaptation-check-20261006/evidence/20261007T070004.867617Z-realtime_verify/desktop.jpg) 有顶部 AURA 字样及中央蓝色竖线，源码明确绘制该中心参考线。摄像头视野大部分被近处物体占据，右上可见房间；不把暗/遮挡画面当作相机完全无图像。

已询问物理蓝线的位置、方向与顶部文字，并让用户清空镜头前方、朝向明亮房间。用户能看到蓝线不等于完整画面和识别已验收，待现场反馈。完整状态见 [报告](../../../kv260-realtime-vision-20261007/REALTIME_REPORT.md)。

## UTC 09:30 用户要求重新显示

旧 boot 的重启动作在 boot 检查处退出，未修改板端；新只读清单确认 boot `4365d744-ddef-4325-a264-e7bb57cc9bb8`，此前预览不在运行，摄像头/显示服务正常、相机空闲、五项发布源码 SHA 一致、官方 B4096 仍活动。

较长恢复脚本被 UART 行长上限在发送前拒绝，改用短的新 boot 恢复脚本后启动成功，PID 2138。启动中采集 13→51、检测 5→36、显示入口 9→47；独立核验继续出帧、error=null、Monitor On，唯一采集 PID 正确。实际 [屏幕截图](../../../kv260-adaptation-check-20261006/evidence/20261007T093021.603280Z-realtime_verify/desktop.jpg) 有桌面物品/手部、AURA 文字和中央参考线。物理屏幕仍需用户查看确认。

新增 `scripts/restart_inventory.py`、`scripts/realtime_restart.py`、`scripts/preview_restore_newboot.py`；三者语法及 UART 封装长度检查通过，分别 2482/3778/3654 字节。恢复脚本和只读清单实际执行通过，同 boot 重启脚本只验证本地，未再打断画面。失败原件保留。最新指针 [CURRENT_RUNTIME.json](../../../kv260-realtime-vision-20261007/CURRENT_RUNTIME.json)，详细报告同步。未修改预览算法、分辨率、FPGA、舵机状态或开机自启。

UTC 09:37 用户反馈“好了，接下来怎么做”，记录为本轮显示恢复的现场确认，报告同步。下一步让单人正脸进入镜头，检查确认框/目标编号，缓慢左右移动检查方向及编号，离开检查 LOST/目标消失；尚未收到这些测试结果。保持舵机暂停，视觉方向仅预览。之后推进正式运动接口与受保护联调，不能从预览确认直接跳到机械闭环验收。本轮只更新记录，没有重新启动程序或改变硬件。

## UTC 09:49 正脸确认与跟踪只读采样

用户在“先做正脸绿色框检查”后回复“可以看到，没问题”，记录为单人正脸检测的现场确认；未扩大为左右跟踪、丢失、身份识别或舵机闭环通过。已请用户缓慢左右移动并离开两秒，检查框是否跟随及 LOST；反馈尚未收到。

新增只读 `scripts/face_tracking_probe.py`，实际板端执行 rc=0，串口回显恢复。同一 boot/PID 2138，16 次每秒采样中采集 25342→25531、检测 11683→11847、显示入口 15797→15986，全部 error=null、stopped=false、motion_command_emitted=false。近期推理中位数 93.57 ms、观察完成帧龄 P95 172.28 ms，仅表示近期软件采样性能。此次采样均 LOST，历史事件包含 TRACKING→LOST；现场位置/动作时间未同步，既不据此判定故障，也不作为移动稳定性与离开验收通过。完整 [采样证据](../../../kv260-adaptation-check-20261006/evidence/20261007T094904.525679Z-face_tracking_probe/result.txt)，报告同步。未打开第二路相机、重启预览、更换 PL 或启动舵机。
