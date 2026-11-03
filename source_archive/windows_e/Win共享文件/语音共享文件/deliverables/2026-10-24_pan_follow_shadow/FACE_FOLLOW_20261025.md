# 人脸持续随动、速度反馈与中值滤波

版本 `AURA-FACE-FOLLOW-20261025-r2`，更新2026-10-25。当前boot `463c9307-5e47-49b0-b22f-5fd3fc21451c`。本报告更新此前FACE_EDGE_REPORT中的历史状态；各次快照、时间和原始数值以[最终验证记录](FINAL_VERIFICATION.json)为准。板卡壁钟不准，证据采用主机UTC及板卡boot/monotonic时间。

已完成本轮代码与板端接入：身份服务恢复、实际视频画布修复、仅人脸持续跟随、按人脸图像移动速度反馈、三点中值滤波，以及手动/跟随软件范围对齐。结束时输出关闭，界面停在视觉追踪页，可直接点击“开始人脸跟随”。真人姓名准确率、新版双向越线及机械平滑度等待用户返场确认。

## 当前行为

- 只用实际人脸框/中心及其新图像时间。不使用人体框、头部yaw或姓名匹配来驱动转轴；多脸、丢脸或不确定测量先停止，重新取得稳定的新帧后再确认。硬件/协议故障停止本次跟随。
- 右边界保留用户选定的屏幕线：x≈414.589，实际画面宽度80.6472%。widget含留黑，原保存比例0.71582536不能直接当相机比例使用。实际图像区域为 `(92,112,400,300)`，原始帧640×480。
- 右侧按人脸中心越线触发；左侧按脸框触及实际画面左缘2像素触发。完整可见人脸的中心无法到达0，因此左侧使用脸框触边。左触边实物效果尚待验收。
- 边界内不发运动指令；越界后跟随，真实脸位置回区立即finish/STOP。保持区内位置，不强制追到画面正中。
- 监测进程持续运行，每个运动段最多10秒，达到本次软件行程边界后停止。断流/过期包不续旧lease，重复包不产生新指令。250ms运动源期限与20ms提交余量保持。
- 右线和滑块都能调整；调整时停止随动。百分比按实际视频内容显示，边界限制在图像内，保存后可重新开启。

## 速度反馈与平滑

三点中值先抑制位置毛刺，再进行80ms位置平滑；以实际新图像的位移/时间估计人脸图像速度，并做100ms速度平滑。向外快移增加响应，向内回区减速；不预测未来位置，也不在边界内继续积分。这个速度包含相机自身纠正运动，不是经过机械标定的人的角速度。

基础速度24µs/s，反馈后的范围8～60µs/s，加速度变化限制120µs/s²，单新源指令步长≤4µs。手动与自动软件范围均为1425～1505µs。没有扩大到固件全部1400～1600范围，也没有将80µs软件范围写成实测机械限位。

跨ARM只继承已确认的人脸测量/滤波历史，脉宽参考、执行速度和源时间重新建立。ARM之前的帧不能产生PWM或续lease，保留移动速度反馈的同时减少重复确认带来的延迟。

板端纯软件回放结果（合成坐标，不访问实际执行器）：

| 场景 | 请求脉宽变化速度 |
| --- | ---: |
| 静止脸，处于同一最终位置 | 25.45µs/s |
| 向外移动到该位置 | 33.60µs/s |
| 向内接近边界 | 14.40µs/s |
| 单帧毛刺，未使用中值 | 60.00µs/s |
| 相同毛刺，使用三点中值 | 24.00µs/s |

回放中，真实测量回区立即停、区内不改变脉宽、输出步长/速度/软件行程约束均通过。表内数值不能替代实体角速度或机械平滑度验收。

## 身份服务恢复

故障原因是原生执行超时后的恢复预算锁定，不能据此判定为理发或姓名匹配失败。新增显式恢复API：旧两次恢复尝试均自然超过600秒、当前主检测连续健康30秒且真实推进至少200次、无active/pending/fence时，才重新进入10秒冷却及三次有效探针验证。旧故障、尝试、恢复累计及旧时间戳保留，30ms hardcap和5ms guard不变。

SFace通过3个明确标记的合成零输入健康作业及有效ACK恢复，每次约7.6～7.8ms；没有发布匹配身份或写入身份库。YuNet使用当前自然相机帧恢复。最终两个可选模型RUNNING，identity.ready=true/error空。旧超限累计SFace3、YuNet7保持；实际新增恢复后尝试/恢复累计为3/3与7/7。可选C调用期间仅当前线程采用FIFO10，退出后恢复原调度。

相机66241正常停止、精确PID/birth/boot的fresh quiescent checkpoint和ZOCL0核验后，同boot启用153151，GUI当时保持。新启动主检测超限18→19新增1已保留；之后通过原生健康窗口才接受显式请求。原断电跨boot的4→1计数断档仍保留，不称已补齐。

现役native unit为`7cf7eaee…`，库SHA `704f561a…`；旧unit为`29786434…`。启动先验证前代checkpoint，再显式做ABI兼容迁移，未修改seed冒充原样恢复。当前保存的前代checkpoint来自66241，已消费；新owner下一次正常停止将导出新unit的checkpoint。回退须正常stop、核验fresh新checkpoint，再用`native_entry_rollback.py`兼容回旧库，不能直接删除24z覆盖后启动旧入口。详细记录见[身份恢复证据](IDENTITY_OPERATOR_VERIFICATION.json)。

## 界面与手动控制

边界设置窗口曾被桌面自动最大化并缺少中文字体，已改为POPUP、默认收起及复用主界面字体。持续跟随的开始/停止按钮放在主窗口内，不创建新的TOPLEVEL。

另一次实际截图发现“frame_visible正常、画布仍是占位文字”。已修正原生X11画布与GTK缓冲/重画配合：关闭该画布双缓冲，绘制后重画当前视频，重画前检查同一输出及真实源年龄<250ms。卸载、已clear和过期输出不重画。参考[GTK3绘制模型](https://docs.gtk.org/gtk3/drawing-model.html)及[GstVideoOverlay expose](https://gstreamer.freedesktop.org/documentation/video/gstvideooverlay.html)。

最终冷启动后的12次实际X11屏幕取样均与相机内容匹配、12帧哈希不同，相关系数最低0.99645，像素绝对差均值最高5.517/255。该检查限于当时静态房间场景，是实际软件屏幕像素证据；未测物理HDMI扫描输出。

旧手动范围1425～1445会使1476µs停点的左右按钮同时受限，现已对齐到1425～1505。使用独立`USER_BOUNDED_MANUAL_VSRV2`发布范围，仍限定每次5/20µs点动、最长2秒、直接点击新鲜度校验及独占运动owner。原20µs人眼观察证明继续按原20µs范围核验，未改成80µs实测；新范围的physical_range_verified、外部波形与机械标定均为false。相机、原驱动/传输库、位流及身份库未因此更换。

## 验证结果

- 17项算法/会话专项在Ubuntu与板端PS均通过；板端使用合成帧和FakeDevice，不将它称作实体运动验收。
- 4项手动范围/原证明继承检查通过；实板平台、文件pins和新范围预检通过，无MMIO写入。
- 3项最新GUI运动所有权检查及原生画布当前/过期/清除/卸载/未映射检查通过。
- 原生恢复20组既有策略、5组C ABI、8组新守卫（含ASAN/UBSAN）和7项Python调度/迁移检查通过；板端链接/ABI检查未创建context或执行模型，恢复阶段才执行实际探针。
- 最后60秒墙钟无人检查，控制子进程实际运行58.637秒，179/179预览采样可见，均NO_TARGET，0个运动段/0ARM/0COMMIT。停止后manual READY，flags0/lease0，1476µs、epoch11/ack16保持；主/可选新增超限0。
- 最终相机153151、GUI supervisor265320、编辑器238044运行，257/257源码pins通过，无render/editor错误。相机约9.91Hz，身份READY；最后2秒USB错误窗口新增0，读日志未清历史。

## 主要改动与当前入口

| 文件 | 用途 |
| --- | --- |
| [continuous_face_control.py](source/continuous_v2r2/continuous_face_control.py) | 仅脸边界、三点中值、位置/速度平滑与反馈、脉宽约束 |
| [continuous_session.py](source/continuous_v2r2/continuous_session.py) | 持续监测、有限运动段、源期限、失目标重确认及故障停止 |
| [run_face_motion.py](source/continuous_v2r2/run_face_motion.py) | 实际板卡/固件上下文、源流、启停与停止证据 |
| [face_pan_controls.py](source/continuous_gui_v2/face_pan_controls.py) | GUI开始/停止、独占子进程交接、实际视频画布 |
| [identity_recovery.py](source/native_operator_v1/identity_recovery.py)及同目录C++源 | 显式受限恢复、兼容迁移、健康探针与本线程调度 |
| [manual_release.py](source/manual_bounds_v1/manual_release.py)、[manual_vsrv.py](source/manual_bounds_v1/manual_vsrv.py) | 明确用户软件范围，保留旧观察证明及平台/负载校验 |
| [face_zone_editor.py](source/zone_editor_v4/face_zone_editor.py) | 用户右线、真实画面坐标、调整即停与小窗口 |

consumer：`OPS/pan-face-edge-v5/continuous-v2r2`，manifest SHA `251ec5808b2b028ec09835561df817523d6c8969562c74e4160fe9ba29375027`。`OPS=/home/root/aura-native-live-20261024/ops/be72669aa53de735`。

GUI：`/home/root/aura-pan-current-20261024/463c9307/gui-face-edge-v5`。实际模型/相机入口由24z `aura-identity-operator-v1.conf`包装既有face-v5入口；原meta、原Python闭包及更早GUI保留。此交付包含精确运行依赖及[GUI组件指纹](GUI_COMPONENT_SHA256.json)，源文件校验见[FINAL_SOURCE_SHA256.json](FINAL_SOURCE_SHA256.json)。不直接覆盖Windows/共享业务主目录的较新源码。

## 返场确认

用户回来后，在当前视觉页点击“开始人脸跟随”，查看只动身体时转轴保持、脸越右线及左触边时转动、回区停止；再确认姓名和实体平滑度。当前输出已关闭。

机械零点、机械限位、角度映射、外部电测、新版真人双向动作与冷启动组合尚未验收。当前许可绑定本次boot，断电重启后须重新核对实际平台及转轴参考。仅完成Ubuntu共享文件落盘，不代填Windows接收、同步版本确认或业务验收。原始画面、身份内容和UART日志不放共享目录。
