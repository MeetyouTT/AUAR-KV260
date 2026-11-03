# 摄像头与HDMI检查

用户说明连接HDMI屏幕，要求查看摄像头识别。UART实查同boot 2a95bf6d-fea6-46e7-88aa-12f92eb40551：显示DP-1 connected、桌面active、1024×768/60Hz、link Good，但初始息屏Off；唤醒当前X会话成功，复查On。没有1024×600模式或EDID，未强制旧原生模式。物理画面待用户观察。

摄像头未枚举：/dev/video*为空、video4linux为空、lsusb仅root hub，v4l2-ctl没有video0。OpenCV4.5.2可导入，GStreamer和v4l2工具存在；没有实际采集或识别。PL仍aura-pin3-sweep，未加载DPU/换固件/START舵机。下一步用户将摄像头接KV260 USB Host后再检查。

报告与证据：/home/ghmd/kv260-camera-check-20261006/CAMERA_DISPLAY_REPORT.md、CURRENT_INVENTORY.json、CURRENT_DISPLAY.json及evidence。

## USB 摄像头复查

用户确认摄像头为 USB 类型。再次 UART 实查仍没有 video_devices，lsusb -t 仅两个 xHCI root hub。uvcvideo 的 modinfo 成功，filename 为 builtin；内核已注册该驱动。dmesg 显示启动时曾枚举 Microchip USB2734/USB5734 集线器，而启动后约 3169 秒出现两个集线器的 USB disconnect；当前没有其下的摄像头枚举。不能将此归因于摄像头驱动缺失，也不能仅凭日志确定断开原因。需要用户重新插接 KV260 的 USB Host 端口后复查连接事件。未重置 USB、未重启板子、未启动舵机、未运行图像识别。

诊断证据：`/home/ghmd/kv260-camera-check-20261006/evidence/20261006T121002Z/result.json`，UART rc=0，控制台回显恢复成功。

用户回复重新插入已完成后再次检查：仍无 video 设备，USB 树仍仅 root hub。新的内核日志检查没有插入事件，末尾仍为启动后 3169 秒的两个 hub 断开记录；相机采集无法进行。证据：`/home/ghmd/kv260-camera-check-20261006/evidence/20261006T121336Z/result.json`。待确认摄像头连接在 KV260 的 USB-A Host 接口及供电指示；USB hub 断开根因未验证，不认定摄像头损坏。

## 集线器恢复与摄像头实际采集

用户授权继续排查。检查确认 xHCI 驱动、USB5744 平台及 I2C 控制驱动存在。仅对 `/sys/bus/i2c/drivers/usb5744` 的 `1-002d` 执行 unbind/bind，未操作 FPGA 或舵机。集线器恢复枚举，Realtek/RYS USB Camera `0bda:9143` 出现，video0/video1 正常；恢复证据 `evidence/20261006T122339Z`。故障时集线器未完成 USB 枚举，重新初始化可恢复；最初失联原因尚未确定。

随后串口捕获新启动日志，boot_id 变为 `5134c246-b23b-48a1-9365-0bb36426d79f`，不是本次脚本发起重启。新启动当前 PL 为 `kv260-benchmark-b4096`，sweep 非 active，不能沿用旧 boot 的运动状态。用户换摄像头期间曾采到 5 帧后设备断开；旧预览因此失败。采集脚本最初截断了 JSON 输出，已修正为保留完整结果并解析最后一行。

最终换上的摄像头是 HD 720P Webcam / Microdia `0c45:6341`。在 `evidence/20261006T123407Z` 实际采到 30 帧 640×480 BGR 图像，耗时约 2.94 秒，保存本地 `frame.jpg`；此测量不代表 30fps 通过。GStreamer YUY2 640×480/30fps + ximagesink 预览进程 PID 1877 在启动后 3 秒仍运行，日志进入 PLAYING。HDMI屏幕用户肉眼确认和长期稳定性尚未验证；没有执行目标识别或视觉驱动舵机。

脚本：`hub_diagnostic.py`、`recover_hub.py`、`camera_preview.py`，均在 `/home/ghmd/kv260-camera-check-20261006/`；最新状态 `CURRENT_PREVIEW.json`。

## 全屏预览修复与换摄像头

用户反馈屏幕没有画面。先前仅证明预览进程存活，不能据此断言用户屏幕可见。新增 `display_diagnostic.py` 使用 X11 获取实际桌面截图，确认旧 gst 窗口存在。截图最初按 24 位像素解码，与实际 XImage 颜色掩码不一致，已修正，不把旧截图的假色当作摄像头故障。

新增 `fullscreen_worker.py` 与 `start_fullscreen.py`，部署到板端 `/home/root/aura-camera-check-20261006/fullscreen_preview.py`。只停止本次创建且命令行经校验的预览进程，创建 override_redirect 置顶窗口，缩放到实际 1024×768，记录经 identity 的帧数和错误；状态文件改用原子替换避免读到半写入 JSON。MJPEG 曾对 Microdia 摄像头验证持续帧，后用户换摄像头，最新枚举一度为 Realtek 0bda:9143，MJPEG 出现 Buffer pool activation failed。改用 640×480 YUYV/MMAP，最终启动 PID 2804，无错误，两秒内计数从 14 到 39。证据 `evidence/20261006T124813Z-fullscreen`。

最终桌面截图 `evidence/20261006T124912Z/desktop.jpg`；用户实际屏幕可见性仍待确认。没有启动识别或舵机。新改动均在 camera-check 目录，未改系统镜像或 FPGA 固件。

## 用户确认实屏画面

用户随后明确回复“是的，现在好了”，确认本次屏幕上的摄像头画面正常。结合上述连续帧计数和实际桌面截图，将实屏预览记为用户观察确认通过；人体检测、跟踪、身份、ASD 和视觉驱动舵机仍未验收。此补记未访问板卡或发出任何控制命令，不将旧 PID/设备型号当当前实时查询结果。
