# 汐蓝板端连接及播放前置检查

用户回复“你看看”后，通过主机侧检查及 UART 实际连接确认当前板卡环境。开始时已读 ZIP README、最新基线准备记录、项目索引和本目录 AGENTS。当前 A 负责视觉与 FPGA，机构继续等待 3D 模型。

## 实测结果

- 沙箱内不可见的 Xilinx FT4232H 接口在主机侧可见，控制台为 if01 / ttyUSB1；无其他进程占用。通过 115200 UART 成功确认 root shell。修正此前仅依据沙箱设备列表判断连接状态的局限。
- 板端为 aarch64、PetaLinux 2022.2、Python 3.9.9，boot ID `c2753755-e758-4ab6-a4b6-2929271aa723`。Xorg `:0`、DP-1 1024×600 / 59.85 Hz，连接/启用/DPMS On。
- MCP01 被 ALSA 识别，固定 USB 播放格式为 48 kHz 双声道 S16_LE，PCM 开关 on / 音量 29%；现有缓存为 24 kHz 单声道，播放器须转换并明确设备。未播放或录音。
- Pillow 8.3.2 和 NumPy 1.21.2 实际基础操作通过；缺 PySide6/PyQt5，Pillow 缺原代码采用的 Resampling/Transform 枚举，Tk 缺 `_tkinter`。因此当前 Qt 入口 **NOT_READY**。
- GTK3/GdkPixbuf 导入及小图像成功，GStreamer WAV/ALSA/Pulse/playbin 插件存在，可作为适配路径；未测窗口或播放管线。Gst 未初始化的版本查询被拒绝，不当作运行通过。
- 中文字体查询 0 条，五个常用源码/资源部署目录不存在，eth0 DOWN / 无可用网络地址；这些结果不能等同全盘资源搜索。
- 视觉 PID 16981 仍在运行，脚本来自 `aura-realtime-vision-20261007/releases/mirror-0c1d48dd418e922d/`。不凭进程名判断算法完成度，没有干扰该进程或 FPGA。

## 新增与验证

新增 [只读诊断脚本](/home/ghmd/aura-board-avatar-baseline-20261009/read_board_environment.py)、三份 UART 会话证据、[完整报告](/home/ghmd/aura-board-avatar-baseline-20261009/BOARD_ENVIRONMENT_REPORT.md)、[证据核验](/home/ghmd/aura-board-avatar-baseline-20261009/board_environment_verification.json)，更新项目索引。

本地探针语法/串口行长验证通过；主机回读的 **9 份命令响应** 字节数/SHA256/JSON 一致，三次会话完整并恢复控制台回显。库探针第一版将 ImageTk 错误归到 Pillow，已拆分复验，最新记录确认 Pillow 可用、Tk 扩展缺失。没有重复运行与本次诊断无关的 48 项框架测试，原补丁包载荷未改动。

## 计划与未验证

下一步为 GTK3/GStreamer 播放适配、旧 Pillow 兼容、MCP01 音频转换及独立资源/字体部署，然后真实显示/发声/暂停/打断验收，最后与视觉并行测性能。当前只是板端环境诊断；没有安装依赖、部署、绘制、播放、录音、改显示模式、驱动舵机或改写 FPGA。
