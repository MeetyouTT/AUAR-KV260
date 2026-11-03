# 视觉到舵机时序修复实测（2026-10-08）

当前结论：坐标时效与命令提交短测已通过；完整持续左右跟随尚未验收。实测12条视觉命令接受，有效PWM宽度1500..1506 µs；1.153秒后因FACE_QUALITY停止，未出现此前STALE_SOURCE/HARDWARE_LEASE_ENDED。最终独立确认flags=0/lease=0，镜像预览继续运行。机械轴运动没有编码器/本轮用户反馈，不能把宽度读回当成实测角度。

修复内容：识别线程继续直接发布带原始出队时间的RAM快照；CPU YuNet推理图从320×320改为192×192，采集/预览仍640×480，检测框和五个关键点按原图宽高映射，蓝线仍x=320。后端以单独文件纳入发布和SHA校验，原模型权重及原identity后端未修改。原320尺寸输出逐元素一致；192固定参考/镜像各1脸、空白0脸、非正方形坐标映射通过，固定图IoU与320结果0.825。CPU线程最终2；4线程与1线程的实时试验均未通过时效资格，未选用。

算法依据：[OpenCV 4.6.0 face_detect.cpp](https://github.com/opencv/opencv/blob/4.6.0/modules/objdetect/src/face_detect.cpp) 的输入尺寸与prior网格、坐标解码；仅接受64的整数倍并逐层检查输出数。192模式的远距离小脸召回率尚未用标注现场数据验收，不能宣称生产准确率或DPU检测完成。

延迟证据：原寄存器单读中位0.183ms、完整状态查询2.269ms；原发布年龄中位139.1ms、更新间隔103.6ms。192配置20秒3422个读取样本/401次检测更新，坐标年龄中位100.0ms/P95 132.6ms/最大194.1ms；超过230或250ms均为0。推理中位48.2ms、发布间隔中位50.2ms。此为当前负载的测量窗口，不承诺任意额外负载下的延迟上界。

板端有限测试：轮询等待20ms缩为5ms，舵机速度参数未变；原250ms时效、20ms提交预算、仅新源帧续租、单写入者、当前boot/epoch/platform/native hash核对仍保留。12条提交与ACK/目标/会话/代次/许可一致，提交中位3.028ms/最大3.502ms，ACK时源帧年龄最大127.0ms，请求lease最小105ms。目标和实际有效宽度均1500..1506 µs；仅观察到CENTER/COUNTERCLOCKWISE映射命令。正式PhysicalReference与三点指向标定仍未完成；1500 µs仅此前授权的测试点，范围1480..1520、步长4 µs/40 µs每秒参数未调整。

还需完成：用户稍微站远，确保整张脸在画面内，确认准备好后再做30秒左右两侧测试。保留目标失效即停止；不自动重新ARM。当前仅常驻视觉预览，输出已禁能。

证据：

- 原时序诊断：/home/ghmd/kv260-adaptation-check-20261006/evidence/20261008T144324.970207Z-visual_timing_probe
- 固定图验证：/home/ghmd/kv260-adaptation-check-20261006/evidence/20261008T145358.311392Z-fast_detector_start
- 快速预览部署：/home/ghmd/kv260-adaptation-check-20261006/evidence/20261008T145535.489482Z-timing_fast_camera_start
- 20秒时效验证：/home/ghmd/kv260-adaptation-check-20261006/evidence/20261008T145623.194004Z-visual_freshness_probe
- 有限视觉命令：/home/ghmd/kv260-adaptation-check-20261006/evidence/20261008T145728.382694Z-timing_visual_direction_start
- 独立停止核对：/home/ghmd/kv260-adaptation-check-20261006/evidence/20261008T150007.702243Z-vsrv_final
- 真实屏幕：/home/ghmd/kv260-adaptation-check-20261006/evidence/20261008T150054.405307Z-realtime_verify

真实X11截图人工检查通过：镜像画面、蓝线、绿色目标框显示，age=92ms；截图时上半张脸在画面外，需用户调整机位/距离后才能继续完整左右测试。舵机保持停止，等待已提出的整脸入镜准备确认。
