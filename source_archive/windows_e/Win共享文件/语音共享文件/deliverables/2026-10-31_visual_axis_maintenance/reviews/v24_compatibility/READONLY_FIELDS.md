# 只读健康字段与来源

本表来自本地源码，未访问设备。API存在与当前owner、相机源码闭包须主窗口新鲜核对。`null`表示未知，不得用0、false或空字符串补出“健康”。只投影固定枚举、有限数值与布尔值，原始JSON留在板端内存，不保存人名、个人ID、任意错误正文或图像。

## 来源与精确指针

| 来源 | 取值/JSON Pointer | 输出及解释 |
| --- | --- | --- |
| GUI，既有`GET 127.0.0.1:8783/api/state` | `/handsfree_dialogue/enabled`、`/handsfree_dialogue/state`、`/handsfree_dialogue/microphone_open` | bool / `PAUSED,OTHER,UNKNOWN` / bool；须保持用户暂停，不发控制命令 |
| GUI | `/manual_pan/state`、`/manual_pan/automatic_following` | 运动后端状态枚举及模式是否开启；`automatic_following=true`不证明PWM正在输出 |
| GUI | `/manual_pan/pulse_us`、`/manual_pan/readback/flags`、`/manual_pan/readback/lease_left_ms` | 当前已有状态的数值/null；FAULT/null时不为了填值加载MMIO驱动 |
| GUI | `/manual_pan/backend_pid`、`/manual_pan/panel_open` | int/null、bool/null；不能用PID存在代替lease或停止证明 |
| GUI，R2部署后才有 | `/manual_pan/face_follow/report_fresh`、`/manual_pan/face_follow/report_age_ms` | bool/null、int/null；1500ms仅为报告显示TTL，不是运动许可 |
| GUI | `/manual_pan/face_follow/heartbeat_mono_ms`、`/manual_pan/face_follow/commands_accepted`、`/manual_pan/face_follow/segments` | 同板时钟、累计提交及运动段计数；原版本不具备新增字段时保留null |
| GUI | `/board_business/visual_timeline/steps`、`/board_business/visual_timeline/errors` | 视觉时间轴worker轮数与错误；不是相机帧数、人脸测量FPS或识别准确率 |
| 相机，`GET 127.0.0.1:8790/health` | `/pid`、`/capture_frames`、`/detected_frames`、`/observation_frame_id` | 当前相机owner、采集帧及主检测帧；主检测在该配置中是YOLOX人体 |
| 相机health | `/capture_age_ms`、`/observation_age_ms`、`/last_inference_ms` | 有限数值/null；由板端同一单调时钟解释，不能在Windows用本机时钟相减 |
| 相机health | `/camera_error`、`/detector_error`、`/identity/error` | 仅输出`*_error_present` bool/null，绝不直接导出字符串 |
| 相机health | `/identity/ready`、`/identity/backend`、`/identity/processed`、`/identity/discarded` | ready/backend枚举与识别处理计数；ready是可用性，不是身份已确认 |
| 相机health | `/identity/face_targets/ready`、`/identity/face_targets/processed`、`/identity/face_targets/discarded` | 脸检测服务状态和轮数，不是FaceFlow当前像素测量计数 |
| 相机health | `/identity/face_targets/source_age_ms`、`/identity/face_targets/worker_alive`、`/identity/face_targets/worker_faults`、`/identity/face_targets/fault_latched` | 有限数值/bool/null；故障字段缺失不得按零故障处理 |
| 相机health | `/dpu_schedule/primary_calls`、`/dpu_schedule/primary_period_overruns`、`/dpu_schedule/owner_fenced` | 主DPU调用、周期overrun和fence；与GUI视觉worker错误分开报告 |
| 相机health | `/dpu_schedule/optional/yunet/overruns`、`/dpu_schedule/optional/yunet/native_failures`、`/dpu_schedule/optional/sface/overruns`、`/dpu_schedule/optional/sface/native_failures` | 四个独立计数/null；不存在可信的通用`native_error_count`字段，不自行合计成新口径 |
| 当前脸观测，`GET 127.0.0.1:8790/v1/motion/face/observation` | `/state`、`/source_frame_id`、`/source_mono_ms`、`/deadline_mono_ms`、`/face_detection_mono_ms` | `READY,NO_TARGET,UNCONFIRMED,EXPIRED,MULTIPLE_FACES,FACE_ERROR,FACE_UNAVAILABLE,INCONSISTENT_FACE_SOURCE,OTHER,UNKNOWN`及源时间数字；非READY不能授予新图像权限 |
| 当前脸观测 | `/target/track_id`、`/target/track_generation` | 匿名运动目标数值/null，不是人脸图库ID。与相机/服务epoch一并在板端比较；只导出`same_target`布尔值或匿名数值 |
| 当前脸观测 | `/face_tracking/processed`、`/face_tracking/valid_measurements`、`/face_tracking/anchor_refreshes` | FaceFlow轮数、有效当前像素测量、真实检测锚更新数；`face_measurement_count_delta`应取`valid_measurements`，不能取`/identity/processed` |
| 当前脸观测 | `/face_tracking/reason`、`/face_tracking/error`、`/detection_miss` | 原因只经下表枚举过滤；error仅输出present；miss=true仍须有效新像素及原锚有效，不可误报为零画面 |
| 相机UI，`GET 127.0.0.1:8790/v1/ui/status` | `/modules/identity/state`、`/modules/identity/source_frame_id`、`/modules/identity/source_mono_ms` | 源龄和身份目标匹配通过后的当前识别状态。原始响应含个人信息，只取状态枚举和源数值，不导出people/name/person_id/detail |
| 相机UI | `/modules/identity/face_count`、`/modules/identity/face_attention/frontal`、`/modules/identity/face_attention/yaw_ratio`、`/modules/identity/face_attention/roll_degrees` | 数值/bool/null；先核相机/服务/face_attention.target和TTL；过期view中的face_count=0不证明人离开 |
| 控制器运行报告，R1/R2候选才有 | `/result/target_lock/locked`、`/result/target_lock/track_id`、`/result/target_lock/track_generation` | 匿名会话锁，GUI当前选择性转发并未包含target_lock，不能从`/manual_pan/face_follow/target_lock`读取 |
| 控制器报告 | `/result/readback/flags`、`/result/readback/lease_left_ms`、`/result/commands_accepted`、`/result/segments`、`/result/heartbeat_mono_ms` | 固定运行路径的最新报告；检查当前进程、报告时钟与发布清单，不将旧报告当停止证明 |

控制器报告路径来源于当前face配置的`release_root/runs/.../trial.json`，由主窗口当前子进程持有的报告引用确定；不要扫描旧runs目录挑“最近成功”的收据。报告内`reason`经过静态允许枚举过滤后才导出。

## 不在这些health API中的项目

| 项目 | 精确来源和默认值 |
| --- | --- |
| 当前组件/startup/config匹配 | 主窗口现有canonical spec/mapping与实际文件SHA比较，返回布尔/null。不是health中的ready字段 |
| 相机PID birth、boot/服务/相机epoch匹配 | 主窗口现有`/proc`只读owner检查及响应上下文比较，输出整数和匹配布尔；epoch/路径不必导出 |
| 真实固件及VART | `/proc/device-tree/fpga-full/firmware-name`、`/sys/class/fpga_manager/fpga0/state`、`/etc/vart.conf`的只读比较；输出`BENCHMARK_B4096,WIDE_V1,OTHER,UNKNOWN`及operating布尔 |
| FDT/配对固件/Native库匹配 | 对既有固定清单的只读字节比较，返回布尔/null；不运行`run_face_motion.py`或新建驱动来“只读检查” |
| 人脸身份阈值0.85 | 沿当前相机argv/config的`identity.config`读取实际身份配置中的`threshold`；GUI副本`config/board_identity.json`的0.85不能代替这一步 |
| 当前实体朝向、有效停止参考、方向/随轴安装 | 本次现场记录及同boot停止证据，不能由1500寄存器复位值、IMU不存在的角度或过去用户反馈推定，未核对为UNKNOWN/null |
| 未标定声纹与个人权限 | 主窗口既有身份政策证据；视觉health不暴露可信`field_calibrated`授权字段，缺少时为null，不能因单脸或KNOWN解锁 |
| 清晰度/机械角度/端到端识别准确率 | 现有映射没有连续、已校准的blur/角度/准确率字段；保持null，不能拿相似度、frontal或人数替代 |

## 采样与枚举规则

同boot、同PID/birth、同service/camera epoch、计数不倒退才可做两样本差值。owner变化、缺字段、布尔冒充整数、NaN/Inf、倒退计数一律使差值为null。健康接口中的采集/检测Hz是进程累计均值，不是严格短窗口FPS。窗口FPS仅在源时间和源帧真正推进时由两个数值计算，并标明对应人体、脸检测或像素测量。

运动源接收时年龄在板端计算：`received_mono_ms - source_mono_ms`与`received_mono_ms - face_detection_mono_ms`；只报告数值/null。期限仍取250ms图像与500ms锚的较早值。GUI报告1500ms TTL与身份结果自己的TTL分别使用，互不替代。

FaceFlow原因只允许源码声明的静态原因集合，至少保留`WAITING,NON_NEW_IMAGE,MULTIPLE_FACES,FACE_ERROR,DETECTOR_EXPIRED,UNCONFIRMED_DETECTION,FACE_CONTINUITY_LOST,MISSING_ANCHOR_FRAME,NO_FACE_ANCHOR,FACE_ANCHOR_EXPIRED,FACE_MEASUREMENT_REJECTED,FACE_DETECTION_ANCHOR,FACE_TEMPLATE_VISIBLE_CLIP,FACE_TEMPLATE_PARTIAL_FIXED_ANCHOR,FACE_FIXED_ANCHOR_LK_AFFINE`；其他字符串投影为OTHER，缺失为UNKNOWN。不输出任意错误详情。

优先单次脸观测GET，不额外占用`face-stream`。旧相机实现对该流只允许一个消费者，活动跟随与诊断争用会得到409。`run_input_diagnostics.py`虽没有运动IO，却会打开这个流并使用独立影子参考；它不能证明真实控制器会话锁、本次实体参考或生物身份。

181点观察中的`visual steps207→747/errors0`仅证明已保存窗口的视觉时间轴worker继续工作，不能推导相机实时帧率、人脸目标稳定、识别正确或机械可跟随。
