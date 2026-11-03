# 舵机方向确认与有限视觉测试（2026-10-08）

用户报告脉宽增加时逆时针转动；方向映射 polarity=-1，镜像画面人脸中心在蓝线左侧对应增大脉宽/逆时针，右侧对应减小/顺时针。尚未实现头部 yaw 输入。速度调配按用户要求留到 3D 打印机构完成后，本次不调整速度/增益。

验证结果：方向映射、静止目标不累积偏移、过期/目标丢失/切换停止共4项单元测试通过。此前4秒板级方向测试92条接受命令，1500→1520→1500 µs，结束STOP；用户确认逆时针。随后重复测试的检查时刻过早导致断言退出，实际宽度1516 µs，finally STOP通过；检查窗口已修正，但没有再宣称完成长保持测试。

首次视觉联动仅接受1条1500 µs命令，0.881秒后STALE_SOURCE停止。5秒坐标读取探测中位243.1ms/最大341.8ms，237样本中103超过250ms。随后识别线程直接发布RAM坐标，显示状态恢复1Hz，原250ms新鲜度保护保持。部署后5秒探测中位194.0ms/最大303.5ms，240样本中15超过250ms，检测更新最大间隔125.6ms。

修复后有限联动仍只接受1条1500 µs命令，0.792秒后HARDWARE_LEASE_ENDED停止；没有实际左右方向命令变化。命令来源允许的剩余时效不足以稳定跨越下一次检测更新，不能报告连续视觉联动通过。最终独立核对 flags=0、lease=0，预览采集/检测/显示持续增长、单摄像头拥有者PID21340。当前常驻状态仅镜像视觉预览，舵机输出已停止。

1500 µs仍是授权测试点，不是用户机械零点；PhysicalReference和三点指向标定均未完成。下一步应优化识别时延/发布间隔及命令提交调度，再做小范围联动；不能用放宽过期保护、续租过期坐标或调舵机速度掩盖问题。

证据：

- 直接发布部署：/home/ghmd/kv260-adaptation-check-20261006/evidence/20261008T143152.812792Z-direct_observation_start
- 坐标时效：/home/ghmd/kv260-adaptation-check-20261006/evidence/20261008T143524.539898Z-direct_coordinate_age_probe
- 有限联动：/home/ghmd/kv260-adaptation-check-20261006/evidence/20261008T143554.295630Z-direct_visual_direction_start
- 最终停止：/home/ghmd/kv260-adaptation-check-20261006/evidence/20261008T143622.919711Z-vsrv_final
- 预览：/home/ghmd/kv260-adaptation-check-20261006/evidence/20261008T143640.200556Z-realtime_verify


## 用户要求再次测试

2026-10-08T14:40:33.135802+00:00：核对同一boot、camera epoch、单摄像头owner与舵机STOP后，运行相同最大30秒/1480..1520 µs有限视觉测试。实际提前退出，rc=1：COMMIT接受检查发现flags=32、reason=2、ACK=1、lease=0、bound/referenced/armed/active均false。RTL的reason=2表示COMMIT校验拒绝，不能仅凭此码断言专门的超时原因；结合前次短剩余lease证据，更新/提交时效不足仍是最可能原因。本次没有额外时序采样，具体竞态未证实，不作硬件损坏结论。finally STOP后再独立核对flags=0/lease=0/ACK=1/width=1500；预览计数继续增长。持续左右联动未通过；未修改代码/速度/新鲜度阈值。

测试证据：/home/ghmd/kv260-adaptation-check-20261006/evidence/20261008T143919.931577Z-direct_visual_direction_start
最终停止证据：/home/ghmd/kv260-adaptation-check-20261006/evidence/20261008T143948.952391Z-vsrv_final


## 视觉时序修复最新结果

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
