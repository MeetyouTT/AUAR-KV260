# 固定摄像头身份与拔插自动恢复

已将默认采集源从 `/dev/video0` 改为这只 HD 720P Webcam 的稳定 USB 身份链接，更新板端相机服务和开机配置。发布 `f4459770ade95f0e`，仅重启相机服务，玩偶 GUI PID1357 保持。

固定链接：`/dev/v4l/by-id/usb-HD_720P_Webcam_HD_720P_Webcam_20130901-video-index0`。每次打开前核对 VID/PID `0c45:6341`、序列号 `20130901` 及视频索引0，再解析当次实际节点；元数据节点或不同身份会被拒绝。相机不在时先退出等待，systemd 每3秒重试且不再因原90秒/3次限流永久停在failed。

主机45项、板端45项相关测试通过。板端受控 USB authorized 断开14秒后重新授权，服务自动恢复，采集5→30、检测4→24帧；新相机代次不同，旧图返回404，缺帧时界面失效，恢复后READY/可见。该测试模拟USB断开，不等于人工拔插线缆；已请求用户进行实物确认，尚待回复。整板冷启动及长期稳定性未新增验收。

后续30秒31次采样均在线、无相机/检测/预览错误，采集+380、检测+301；6个部署目标文件回读SHA与发布清单一致。最终界面截图见 [screen.jpg](/home/ghmd/kv260-display-check-20261017/evidence/20261017T111924.990828Z/screen.jpg)。

部署前后文件哈希、21份部署响应、模拟重连响应和ZIP载荷均复核，详见 [validation.json](validation.json)。板端完整备份在 `/home/root/aura-camera-hotplug-20261017/release-f4459770ade95f0e/backup/`。

项目源码改动：

- `board/vision/camera_device.py`：设备身份及视频节点校验。
- `board/vision/ui_camera_service.py`：每次启动重新定位，缺设备不加载DPU，健康接口记录实际设备，别名不绕过所有权检查。
- `config/board_camera_ui.json`：使用稳定身份链接。
- `scripts/board_camera_ui/aura-camera-ui.service`：持续重试，间隔3秒。
- `tests/framework/test_camera_device.py`：7项新增回归，覆盖编号变化、断开、错身份、元数据及占用。
- `tools/package_board_avatar.py`、`docs/BOARD_CAMERA_UI.md`：打包测试入口和操作说明。

主仓不在Git工作树中；修改前已保存主机和板端原件，没有覆盖其他任务的改动。完整运行包收集另遇到既有 `docs/BOARD_ASR.md` 缺失，本轮没有补写无关ASR文档或重建整包；当前独立修复ZIP已实际部署并核验。
