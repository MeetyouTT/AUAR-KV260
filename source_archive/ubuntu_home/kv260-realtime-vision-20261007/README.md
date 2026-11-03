# KV260 实时人脸预览

最新（2026-10-08）：上电后 30 秒双向视觉命令测试通过（374 条）；放大动作的固定往返两轮已完成（1400～1600 µs、616 条），最终 STOP、预览继续。实际方向和角度尚未标定，常驻预览仍不启用动作。见 [最新实测记录](/home/ghmd/AMD_Smart/logs/daily/2026-10-08-SERVO-VISIBLE-TEST.md)，下方保留历史。

后续 30 秒测试：中心位置真实命令连续提交通过；左右补测因新帧未取得有效人脸观察提前停止。当前仍为镜像预览、舵机输出禁能。见 [最新实测](../kv260-visual-servo-20261007/CONTINUITY_30S_REPORT.md)，不能将中心测试记作左右机械随动验收。

2026-10-08 晚间最新状态：重启后已恢复原镜像/192 检测/2 CPU 线程预览；三轮受控视觉命令测试结束，输出禁能，当前常驻为预览。左右命令、失跟停止和重现不自动恢复已有本次证据，30 秒持续验收与机械标定仍未完成。见 [复测报告](../kv260-visual-servo-20261007/FOLLOW_RETEST_REPORT.md) 与 [实际运行记录](CURRENT_RUNTIME.json)。下方模拟部署状态为历史记录。

本阶段实现 USB 摄像头采集、CPU YuNet 人脸检测、基础 IoU 轨迹关联、目标保持以及 HDMI 叠加显示。默认只预览；`--motion-sim` 增加模拟接受回读的控制服务。程序没有真实舵机驱动、寄存器写入或 FPGA 加载入口。

2026-10-07 UTC 10:55 的最新部署、测试及边界见 [模拟运动报告](MOTION_SIMULATION_REPORT.md)。板端当前为模拟模式，真实舵机继续暂停；源帧丢失后模拟服务也停止，目标重现不会自动重新 ARM。

它不是完整的人体 YOLO / ByteTrack、SFace 身份库或已验收的视觉机械闭环。前序两项适配的结果见 [适配报告](../kv260-adaptation-check-20261006/ADAPTATION_REPORT.md)。

## 实现与运行

- [realtime_vision.py](realtime_vision.py)：唯一摄像头采集者、只保留最新帧的推理线程、实时显示、运行状态和有限事件日志。
- [vision_core.py](vision_core.py)：两次观察确认、短时保持当前目标、丢失与陈旧检查、按真实时间间隔计算的滤波及方向预览。
- [x11_window.py](x11_window.py)：独立全屏窗口，运行中每 30 秒重置屏幕休眠计时；不修改系统休眠设置。
- [board_launch.py](board_launch.py)：先检查依赖，再替换本项目原预览；启动失败恢复原程序。
- [deploy_vision.py](deploy_vision.py)：通过已知 UART 传送 SHA-256 校验的不可变源码包并执行板端检查。
- [test_vision_core.py](test_vision_core.py)：轨迹、丢失、冻帧、顺序、裁剪、时间间隔及禁止动作的 5 项测试。
- [motion_service.py](motion_service.py)：实际观察间隔下的滤波/P 控制、限速限幅、源帧检查、模拟提交及接受回读。
- [motion_replay.py](motion_replay.py) 与 [test_motion_service.py](test_motion_service.py)：确定性回放及 20 项控制测试。
- [deploy_motion_sim.py](deploy_motion_sim.py) 与 [board_motion_launch.py](board_motion_launch.py)：先校验平台、源码及板端测试，再替换归属明确的旧预览；模拟模式不加载 PL。

板端发布目录 `/home/root/aura-realtime-vision-20261007/releases/`；运行目录由板端 `current.json` 指向，保留每次启动证据。板端日期不准确，实际先后顺序采用电脑 UTC 证据目录与板端 monotonic 时间、boot_id、epoch；不把板端墙钟当作真实日期。

已有模型和兼容后端保持在 `/home/root/aura-adaptation-20261006/identity/`。程序按原验证 SHA 检查后端和固定 YuNet 权重，不安装或升级 OpenCV。

## 验证与边界

本地参考图检测和 5 项逻辑测试通过；实际部署、屏幕输出及现场人脸结果见 [本阶段报告](REALTIME_REPORT.md)。`display_frames` 是推送帧数，`rendered_frames` 是经过最终显示入口的帧数；不能只用推送帧数判断画面正常。实际 X11 framebuffer 截图用于独立核验。

采集请求 30 fps，不宣称真实达到 30 fps。采集、推理及显示分开计数；帧池和推理候选只保存最新帧，显示源最多等待一帧，后续显示队列丢弃旧帧。帧时间是驱动交付时间，不是传感器曝光时间。观察超过 250 ms 后显示 STALE，目标不存在时显示 LOST，过期观察不会产生运动许可。

人脸框的轨迹 ID 是本次运行的关联编号，不是人物身份；尚未验证多人交叉、严重遮挡、镜头转动或长时间重返。每两秒更新一张当前预览 JPEG，不保存连续录像；事件日志达到 1 MiB 时轮换，保留一份历史。

## 恢复原预览

主机使用已建立的串口入口：

```sh
cd /home/ghmd/kv260-adaptation-check-20261006
python3 scripts/board_exec.py scripts/realtime_rollback.py 40
```

恢复脚本仅停止本项目且本次 boot 的识别进程，确认相机无其他占用后恢复原预览。该命令尚未作为人工恢复执行；启动失败时的自动回退已在本次调试中实际发生并验证。原程序恢复后仍采用原屏幕休眠行为。

新程序没有设置开机自启，关机后不能认为仍在运行。部署入口保留 board boot、SD CID、进程归属及活动官方 B4096 检查；换 boot 时先核验当前状态，不跳过保护。

本地检查：`python3 -m unittest test_vision_core test_motion_service`。模拟参考 0°、1500 μs 和 ±5° 范围只用于软件测试，不是实物标定。租约到期依赖软件轮询，不证明 FPGA 独立看门狗有效。同 boot 的恢复辅助脚本已适配模拟模式并静态检查，新增分支未实际重启验证；跨 boot 需要重新核验。
