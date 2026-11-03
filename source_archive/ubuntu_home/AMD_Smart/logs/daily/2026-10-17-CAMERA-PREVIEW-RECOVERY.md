# 2026-10-17 玩偶界面的真实摄像头预览恢复

用户先要求调出玩偶，随后明确反馈“我的玩偶界面的摄像头看不到”。本轮完成当前界面操作、摄像头服务诊断和恢复，以 UTC 主机时间记录，不沿用板端未校准的 2021 年日志日期。

## 新启动与设备状态

UTC 10:51 实查发现 boot ID 已从 `e109cf65-d3c7-4396-9cf6-4bdc7a253929` 变为 `25c4401f-471d-4383-8159-03b8bcaf480b`。本轮脚本没有发起整板重启，也没有观察此次启动过程，不能据此追加冷启动验收。

USB2734/USB5734 两个四口集线器重新枚举；下游拓扑为 port1 MCP01、port2 `HD 720P Webcam / 0c45:6341`、port3 WaveShare WS170120，port4 没有枚举设备。摄像头恢复 `/dev/video0`（Video Capture）和 `/dev/video1`（Metadata Capture），UVC 已绑定。未对空闲的第四个物理插座进行插拔测试。

显示恢复原生 1024×600/59.85Hz，Xrandr 报告 150×90mm，MCP01 音量控制可用、58%非静音。没有在本轮另外读取原始 EDID 字节或直接观察屏幕背光。

## 界面及相机恢复

“调出玩偶”的 API 切页返回成功，短时 `ui_page=main/ui_layer=presentation`，玩偶渲染 sequence 110→117。稍后状态回到 vision，切回来源未确定，不能把首个 API 成功当作最终停留在玩偶页。用户随后澄清当前问题是应用内的相机画面，本轮最终保留视觉追踪页供检查。

摄像头设备已在线，但 `aura-camera-ui.service` 仍 failed/MainPID=0，启动日志有 `CAMERA_FAILED: Cannot start camera`，连续失败后触发启动限流。8790 健康接口拒绝连接，界面为 OFFLINE、frame_visible=false。未能从旧日志确诊最初采集启动失败的底层原因。

先确认 `/dev/video0` 为已识别的 HD 720P Webcam、没有其他占用进程，并确认安装的 unit 与当前运行包中的 unit 完全相同；随后只对现有相机服务执行 `systemctl reset-failed` 和 `systemctl --no-block start`。服务恢复 active/running，PID1974。没有复位 USB hub、加载 FPGA 位流、操作运动、重启 GUI 或修改启动配置。

## 实际验证

- 同一相机 PID/代次，约2秒观测采集 64→91 帧，检测 45→66 帧，camera/detector/preview error 均为空；这只证明该短时窗口持续工作。
- 界面 `link=READY`、`frame_visible=true`，快照 `source_kind=actual`，原生预览 displayed_frames=82、约12.32Hz；帧入口延迟统计不代表物理屏端到端延迟。
- 实际 X11 界面截图已回读并查看，视觉追踪页包含真实人物画面、检测框和当前目标#1。服务报告检测1人，仅作为这次场景的运行证据，不作为多人精度验收。
- 最终 GUI/Xserver 服务 active/running，显示 connected/enabled/On，音量58%。没有播放音频或运行录音测试。

## 工件与验证完整性

工作目录 `/home/ghmd/kv260-display-check-20261017/` 的 `check_display.py` 增加 `--avatar` 和限定同目录探针的 `--source`；新增 `camera_gui_diagnose.py`、`recover_camera_service.py`、`verify_camera_preview.py`。仅这些主机操作助手和日志发生文件修改，未改板端应用源码或持久系统配置。

关键证据目录：

- `evidence/20261017T105100.530757Z/`：切页、唤醒、新 boot 状态；后续截图仍为等待相机的视觉页。
- `evidence/20261017T105137.711950Z/`：新启动 USB、摄像头枚举。
- `evidence/20261017T105316.217739Z/`：实际服务启动失败日志及 GUI 状态。
- `evidence/20261017T105403.244458Z/`：相机服务恢复动作。
- `evidence/20261017T105413.471584Z/`：真实连续采集、检测和 UI 预览核验。
- `evidence/20261017T105442.530128Z/screen.jpg`：恢复后的实际界面截图。

7轮15份 UART 响应的输出 SHA256 已独立复核，所有会话回显恢复。其中 `20261017T105301.337295Z` 首次诊断因板端缺少 `xwininfo` 退出1，未改变板端；诊断助手补充工具缺失处理后复查成功。保留该失败响应，其余14份响应退出0。实际截图的传输长度/SHA256通过并已查看。

最初相机启动失败原因、下次启动能否自动恢复、USB/HDMI长期稳定性仍未验证。本轮不将手动恢复写作开机问题根因已修复。
