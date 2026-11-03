# 摄像头镜像显示修正（2026-10-08）

结果：KV260 镜像预览已经运行；显示、识别、跟踪和控制预览共用一次水平翻转后的图像。蓝线仍为 640 像素画面中的 x=320。用户实际向左/向右的动作对应关系仍需现场确认。

原程序未进行镜像；用户希望照镜子式的自视图，本次启用 --mirror-horizontal。仅在捕获帧发布之前调用 orient_frame；先翻转，再检测和绘制识别框，叠加文字保持正向。默认 CLI 行为仍为非镜像，当前板端启动参数已明确启用镜像。

验证：
- 主机 OpenCV 4.6.0 下 7 项测试通过，包含非对称像素、源图不变、默认关闭、两次翻转恢复，以及识别坐标与蓝线两侧方向一致。
- 板端 OpenCV 4.5.2 固定原图/镜像图均检测到一个人脸；空白图和跟踪失效检查通过。
- 精确校验运行中的原 release 全部文件，仅更改 realtime_vision.py；在新目录运行，保留旧版本和 previous-state/staged 备份。
- 摄像头唯一所有者 PID 19794；capture/detected/display/rendered 计数持续增长；error=null，stopped=false。
- 实际 X11 屏幕截图已检查：画面、识别框和蓝线可见，顶部 MIRROR 标识可见。
- 本次检查采集 23.8 Hz，CPU 人脸检测 9.0 Hz；此短时数据不代表竞赛性能验收。

运行证据：
- Release: /home/root/aura-realtime-vision-20261007/releases/mirror-81f321f9aea59728
- Run: /home/root/aura-realtime-vision-20261007/runs/mirror-preview-41b68a7f6cb74099b4eb34628b06920f
- Boot: f7a3ff07-fc20-4804-af12-c314a7a1847a
- 新 camera epoch: 4a34688a223445969d193f5cb2bcbe28
- 启动证据: /home/ghmd/kv260-adaptation-check-20261006/evidence/20261008T140323.120758Z-camera_mirror_launch
- 验证证据: /home/ghmd/kv260-adaptation-check-20261006/evidence/20261008T140352.293598Z-realtime_verify
- 截图: /home/ghmd/kv260-adaptation-check-20261006/evidence/20261008T140352.293598Z-realtime_verify/screen.jpg

边界：本次没有写 PWM 或重载 FPGA，实际运动未启用；运行界面为 MOTION OFF。坐标方向改变后，舵机物理极性及映射仍待标定，CALIBRATION_PENDING 继续 confirmed=false。没有宣称机械随动或现场左右动作通过，也没有新增自动开机服务。

改动文件：realtime_vision.py、test_orientation.py、CAMERA_MIRROR_CHANGE.json、CURRENT_RUNTIME.json；适配目录 scripts/camera_mirror_20261008.py、camera_mirror_transfer.json、camera_mirror_launch.py；CALIBRATION_PENDING.json；本报告和项目日志。
