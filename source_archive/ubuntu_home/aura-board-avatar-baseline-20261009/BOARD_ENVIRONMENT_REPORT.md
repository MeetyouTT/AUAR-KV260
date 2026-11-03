# 汐蓝板端环境实测

2026-10-09，UTC 10:28–10:34。任务为确认当前连接、板端图形和音频条件，未启动玩偶程序。

## 结论

**KV260 已通过 USB 串口连接；当前 Qt 缓存播放入口为 NOT_READY。** 屏幕输出和 MCP01 已被系统识别，但缺少 PySide6，板端 Pillow 8.3.2 也不提供原复用代码使用的 `Image.Resampling` / `Image.Transform`。不应把 PC 软件测试通过视为板端程序可以直接运行。

当前镜像已有 GTK3、GdkPixbuf、GStreamer 与 NumPy，可作为后续适配路径。这里只验证了库加载、内存中的小图像操作及插件清单，没有验收 GTK 窗口、Python 音频管线或真实扬声器。

## 连接及实际系统

- 主机侧 `lsusb` 识别 FT4232H/Xilinx 调试接口；4 个 `usb-Xilinx_ML_Carrier_Card_XFL1EMEBC1R5-if0*-port0` 串口链接存在，控制台为 if01 / ttyUSB1，115200。
- 主机侧 `fuser -v /dev/ttyUSB1` 无占用输出；随后成功确认既有 root 控制台。此前沙箱内未显示设备，不能据此断言主机未连接板卡。本轮设备判断以沙箱外主机检查和实际串口响应为准。
- 系统为 aarch64 / K26，PetaLinux 2022.2，内核 `5.15.36-xilinx-v2022.2`，Python 3.9.9。
- 本次 boot ID 为 `c2753755-e758-4ab6-a4b6-2929271aa723`；采样时 uptime 44781 秒。可用内存约 3.50 GiB、根分区可用约 20.2 GiB，只是环境快照，不代表运行时性能验收。
- `eth0` 为 DOWN，没有可用于远程部署的板端 IPv4 地址；本次检查依赖 UART。

## 图形、资源与库

| 项目 | 实测 | 对当前入口的影响 |
| --- | --- | --- |
| 显示 | Xorg `:0`；DP-1 connected/enabled、DPMS On；xrandr 1024×600 / 59.85 Hz | 输出配置符合目标尺寸；本轮没有实屏照片或程序绘制验收 |
| PySide6 / PyQt5 | 模块不存在 | 当前 `tools/realtime_stage.py` 直接导入 PySide6，会在启动前失败 |
| Pillow | 8.3.2；小图像创建成功；两个新版枚举不存在 | 原口型/眨眼复用代码需要兼容旧版常量 |
| NumPy | 1.21.2；小数组运算成功 | 基础数组依赖可用 |
| Tk | `tkinter` 源码存在，但 `_tkinter` 扩展缺失；ImageTk 同样失败 | 不能仅凭模块路径改用 Tk 播放器 |
| GTK3 / GdkPixbuf | GTK 3.24.30 导入成功；Pixbuf 2×2 内存图像成功 | 是后续图形适配候选，未创建窗口 |
| GStreamer | `wavparse` / `alsasink` / `pulsesink` / `playbin` 插件查询成功 | 具备音频适配候选；尚未创建播放管线 |
| Gst Python 查询 | GI 类型加载后，未初始化时查询版本被 `NotInitialized` 拒绝 | 不是播放通过；Python 管线须在实现时初始化并实测 |
| 中文字体 | `fc-list :lang=zh file family` 返回 0 条 | 部署需携带可用中文字体，不能依赖当前系统字体清单 |
| 常用部署位置 | `/home/root/aura`、`/home/root/deliverables`、`/home/ubuntu/aura`、`/home/ubuntu/deliverables`、`/opt/aura` 不存在 | 这些位置尚无本次源码与相邻资源；未声称全盘不存在其他副本 |

## MCP01 音频

- ALSA card 2 为 Lenovo MCP01，播放与录音设备均被识别。
- 设备 USB 播放格式为 **48 kHz / 双声道 / S16_LE**；录音为 16 kHz / 单声道 / S16_LE。本轮两者状态均 Stop。
- 原演示缓存为 **24 kHz / 单声道 / 16 bit**。后续播放器需要采样率和声道转换，或选择经过实测的转换设备；直接向固定硬件格式写入原缓存不可作为方案。
- MCP01 播放 PCM 开关 on，读到音量 29%；没有调整音量或播放测试音。
- ALSA 默认输出指向 PulseAudio，不能据此保证默认声音会进入 MCP01。适配时应明确输出设备并检查真实音频进度。

## 正在运行的项目

视觉进程 PID 16981 正在运行，其脚本为：

```text
/home/root/aura-realtime-vision-20261007/releases/mirror-0c1d48dd418e922d/realtime_vision.py
```

另有 dfx-mgrd 和 Xorg。本轮未停止或重启任何项目进程，没有访问相机、加载 FPGA、写运动寄存器或操作舵机。仅凭进程存在不能判断视觉模型、跟踪或 DPU 的完成度。

## 验证与证据

只读检查脚本：[read_board_environment.py](/home/ghmd/aura-board-avatar-baseline-20261009/read_board_environment.py)。复用已审阅 UART 传输，保存原始串口记录、明确命令、输出与 SHA256；临时关闭控制台回显并在三次会话结束后确认恢复。

证据目录：

- `evidence/20261009T102828.291518Z-board-environment/`：系统、依赖发现、显示、音频、现有进程/目录/网络。
- `evidence/20261009T103226.217463Z-board-environment/`：库加载、音频格式/音量/插件、字体与部署路径。第一版库探针将 ImageTk 的错误合并到 Pillow 项中。
- `evidence/20261009T103415.348614Z-board-environment/`：拆分 Pillow 与 ImageTk 后的准确库结果；Pillow 本身可用，Tk 扩展不可用。以该记录更新库判断，不把前一结果解释为 Pillow 缺失。

[证据回读核验](/home/ghmd/aura-board-avatar-baseline-20261009/board_environment_verification.json)：**9 份命令响应的字节数、SHA256 与 JSON 内容一致；三次会话完整，控制台回显恢复。** 这是诊断证据完整性通过，板端 Qt 入口仍为 NOT_READY，声音/绘制/并行性能未验证。

## 下一步

1. 在当前工程中实现 GTK3/GStreamer 的板端缓存播放器适配，保留原素材、选定声线与缓存身份校验；兼容 Pillow 8.3.2，明确 MCP01 输出及格式转换。
2. 准备独立板端部署包、相邻资源和中文字体，保持当前视觉/FPGA 工程。当前板端无网络地址，大素材部署还需可用网络或拷贝介质。
3. 验收 1024×600 显示、待机/眨眼/口型、真实声音、暂停恢复和打断；再与现有视觉程序并行测性能。机构继续等待 3D 模型。

本轮只新增 Ubuntu 诊断与记录，没有安装板端依赖或部署新播放器。此前 48 项 PC 软件测试和补丁包保持原有状态；未改动补丁包的 10 个载荷文件。
