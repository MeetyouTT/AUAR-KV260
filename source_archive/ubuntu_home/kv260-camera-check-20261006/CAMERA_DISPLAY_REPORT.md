# 摄像头与HDMI检查

2026-10-06，通过既有UART读取同一KV260，boot ID为2a95bf6d-fea6-46e7-88aa-12f92eb40551。

- HDMI显示在Linux中为DP-1 connected，X桌面服务active，当前1024×768/60Hz，link-status Good。
- 初次DPMS为Off；已执行当前会话xset dpms force on，返回0，复查Monitor is On。没有公布1024×600模式或EDID，本轮未强制设置旧屏幕模式；物理屏幕是否显示仍需用户观察。
- /sys/class/video4linux没有设备，/dev/video*不存在；lsusb仅有两个root hub，v4l2-ctl报Cannot open device /dev/video0。这次启动下尚未枚举USB摄像头，不能输出摄像头画面或识别框。
- OpenCV 4.5.2可导入，v4l2-ctl及GStreamer工具存在；模型目录存在，但尚未验证检测模型工件与硬件适配，更未实际推理。
- 当前PL活动应用仍为aura-pin3-sweep，DPU基准应用未活动。本轮没有换PL、访问运动寄存器或START舵机。

证据指针：CURRENT_INVENTORY.json与CURRENT_DISPLAY.json；对应evidence子目录保存远端探针、完整输出和UART原始记录。

下一步：将USB摄像头接到KV260的USB Host并确认相机供电后，重新枚举、查询格式、获取真实帧，再启动屏幕预览与适配检测程序。HDMI只传显示输出，不能代替摄像头输入。
