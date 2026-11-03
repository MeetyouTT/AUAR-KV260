# 2026-10-17 四口 USB 与摄像头只读检查

用户要求检查板子四个 USB 口，以及摄像头能否识别。接续当前显示排查记录，并查阅 2026-10-06 同类集线器故障及恢复原件后，于 UTC 10:48 通过既有 UART 实查。

## 实际结果

- `lsusb` 和 `lsusb -t` 当前只有 USB2/USB3 两个 xHCI root hub；原板载下游 USB 集线器及摄像头、触摸屏、MCP01 均未枚举。
- I2C 控制设备 `1-002d/name=usb5744`，仍绑定 `/sys/bus/i2c/drivers/usb5744`；xHCI 平台驱动仍绑定 `xhci-hcd.1.auto`。控制驱动存在不代表集线器已在 USB 总线上工作。
- `/dev/video*` 与 `/sys/class/video4linux/video*` 均为空；`v4l2-ctl --list-devices` 返回 1，明确提示无法打开 `/dev/video0`。
- UVC 驱动已注册，`modinfo uvcvideo` 返回 builtin。当前不能归因为缺少 UVC 驱动。
- `aura-camera-ui.service` 为 failed，MainPID=0、NRestarts=7，8790/health 拒绝连接。没有实际相机采集或人物识别结果。
- 当前日志保留先前 `HD 720P Webcam / 0c45:6341` 枚举，以及 uptime 32732 秒起 USB reset 错误 `-71` 和随后摄像头、hub 断开的记录。这些历史识别记录不能代替当前设备在线。

## 判断与限制

当前摄像头未被识别，故障范围先落在板载 USB hub/上游链路层，而非相机应用是否识别人脸。尚不能区分集线器异常、供电或物理连接原因；root hub 的 runtime suspended 也可能只是没有下游设备的结果，不认定为根因。

本轮没有把同一摄像头实际轮流插入四个插座，因此不能单独给四个物理插座作好坏结论，也不能宣布四口损坏。

2026-10-06 的相似状态曾仅通过重新绑定 USB5744 I2C 控制设备恢复集线器和相机，具体见当天摄像头日志与 `kv260-camera-check-20261006/recover_hub.py`。这是可供后续恢复参考的历史证据，本轮未执行该恢复，也没有重启相机服务、复位 USB、重启板卡或操作运动。

## 文件与验证

主机脚本 `/home/ghmd/kv260-display-check-20261017/check_display.py` 新增 `--usb` 专项只读检查。实际证据在 `evidence/20261017T104842.015838Z/`：USB 拓扑、hub 控制、相机枚举三份响应均完整，输出 SHA256 独立复核通过，串口回显恢复。三份包装响应退出 0 不代表内部设备探针全部成功；v4l2 的退出 1 和相机健康接口失败按原样保留。

当前 boot ID 为 `e109cf65-d3c7-4396-9cf6-4bdc7a253929`。

## 后续状态更新

UTC 10:51 检测到外部新启动 `25c4401f-471d-4383-8159-03b8bcaf480b`，两个四口 hub、摄像头、MCP01和触摸屏重新枚举；随后恢复已失败的相机服务，实际连续采集、检测和界面预览通过。上文“未识别”仅表示 UTC10:48 的旧启动检查状态；详见 [新启动与预览恢复记录](2026-10-17-CAMERA-PREVIEW-RECOVERY.md)。本轮未发起整板重启。
