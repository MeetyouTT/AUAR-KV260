# KV260 简易图形操作与设置界面

2026-10-11 更新：板端界面已经扩展为“互动、演示、设备、连接、设置”五页，设置沿用本文件的异步音量与持久化逻辑，当前保存音量 18%。相机、触屏布局、接口和最新实测见 [触屏设计](BOARD_TOUCH_UI_DESIGN.md)、[相机说明](BOARD_CAMERA_UI.md) 与 [本轮报告](/home/ghmd/aura-board-ui-design-20261009/UI_DESIGN_REPORT.md)。下文两页描述为原基础设置版的记录。

更新：2026-10-09。入口为 `tools/board_avatar_gtk.py`，右侧保留原汐蓝，左侧分为“互动”和“设置”。沿用 1024×600 画布与原素材、声线，不启动新的模型。

## 当前功能

| 页面 | 可用操作 |
| --- | --- |
| 互动 | 四段缓存台词、播放、暂停/继续、打断、重新开始、保存画面 |
| 设置／声音 | 0–100% 音量滑块、每次 10% 的加减按钮、静音/取消静音、实际音量回读 |
| 设置／界面 | 全屏切换、省电动画、恢复默认 |
| 设置／状态 | 音响连接状态、触摸设备检测、调整中/失败反馈 |

主操作按钮高 56–64 像素，页签高 48 像素，使用 19px 按钮字体和按下反馈。GTK 原生手势负责激活按钮；触摸事件仅作观察记录，不再额外触发一次点击。同一按钮的短时间重复激活会合并。

音量只操作 `MCP01` 的 `PCM` 播放控制。后台执行 ALSA 命令并回读，滑块连续调整只保留最近待处理值，界面不等待外部命令。麦克风音量不随播放设置改变。设置错误会显示，硬件未确认的音量不会保存为已生效值。

设置保存于运行目录的 `avatar_user_settings.json`，包含音量、静音、全屏与省电动画。默认值为用户选定的音量 100%、非静音、全屏、普通动画；后台回读成功后保存声音设置，后续启动恢复已保存值。配置损坏会保留原文件并记录错误。可用 `--settings-file` 指定独立配置路径。

省电动画将调度间隔改为 250ms，普通模式为配置的 33ms；调度间隔不是实测帧率。原始素材解码、图像变换和并行视觉仍限制实际流畅度。

## 显示与触摸边界

启动后将本界面的窗口及其所属外框置前，解决视觉预览 `override_redirect` 遮挡问题。前次部署时与视觉同时运行；本轮外部重启后未发现 `realtime_vision.py`，没有沿用旧 PID 或重新启动 A 的视觉。

2026-10-09 接好 TOUCH USB 后，已识别微雪 `WaveShare WS170120`（`0eef:0005`），加载匹配内核的 `hid-multitouch`，实际输入为 `event5`、`INPUT_PROP_DIRECT`；XInput 枚举 direct 与五触点能力。恢复本次显示至 1024×600 并映射至 `DP-1`。

**真实手指拖动音量与“互动／设置”页签切换已通过**：25 秒只读记录 3348 个实际 evdev 事件，GTK 有 touch-begin/end 与页签 activation，音量实际回读及保存文件一致，最后为 18%。当前手指记录未覆盖加减按钮；边缘精度、多指压力、长测仍待验证。鼠标/XTest 与实际手指证据分别记录。

模块安装至 `/lib/modules/5.15.36-xilinx-v2022.2/extra/aura/hid-multitouch.ko`，自启配置为 `/etc/modules-load.d/aura-touch.conf`。模块 SHA、解析路径与配置回读通过。现已增加 [界面开机服务](BOARD_UI_STARTUP.md)，启动时恢复显示和触摸映射；实际服务启动与快速重启通过，**整板正常重启后的自动恢复尚未验收**。触摸原件见 [实测日志](/home/ghmd/AMD_Smart/logs/daily/2026-10-09-WAVESHARE-TOUCH-CONNECTED.md) 和 [独立核验](/home/ghmd/aura-waveshare-touch-20261009/touch_connection_validation.json)。

## 验证与证据

- 主机 70 项框架测试通过，其中新增 12 项设置测试覆盖配置、类型限制、真实 ALSA 文本解析、回读失败、异步合并、设备失败与重载恢复。
- 同一 12 项设置测试在 KV260 Python 3.9.9 实际执行通过；资源检查通过。
- KV260 真实窗口经 XTest 指针操作通过：设置页切换、音量减/加、静音/恢复、滑块拖到 49%、省电切换、退出全屏、恢复默认与设置文件回读。结束恢复 100%、非静音、全屏、普通动画，麦克风控制保持原值。
- 上项为前次自动化结束状态。本轮启动恢复用户后存的 64%；真实触摸后最后保存为 18%、非静音，全屏与普通动画保持一致。八份关键响应的 SHA/大小、真实输入、GTK 事件、ALSA 与配置回读检查通过。
- 原缓存播放器已完成四段 MCP01 播放、EOS、暂停位置冻结、恢复、打断与旧代次不恢复；用户确认声音可听并要求音量调满。精确声学延迟、长测和最终整机验收仍未完成。

工作目录：`/home/ghmd/aura-board-avatar-touch-20261009`。更新包 `touch_settings_update.zip` SHA256 为 `ddd4944081890e22e76d1bd105106059ae3cea09636fe6f97c2093868a09b661`，包含五个载荷。部署先逐项验证旧源 SHA，保存备份，再更新独立播放器目录；实际记录见 `evidence/20261009T131910.962991Z-deploy/`。

板端安装目录：`/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009`。旧播放器和证据保存在该目录的 `touch-update-ddd4944081890e22/backup/`。设置页自动化检查原件在 Ubuntu 的 `aura-board-avatar-gtk-20261009/evidence/20261009T132550.101267Z-usb-runtime-ui-settings-check/`。

实现依据：[GTK 按钮激活](https://docs.gtk.org/gtk3/signal.Button.clicked.html)、[GDK 触摸事件掩码](https://docs.gtk.org/gdk3/flags.EventMask.html)、[GTK 触摸事件](https://docs.gtk.org/gtk3/signal.Widget.touch-event.html)。最终触摸驱动与坐标正确性仍以目标屏幕实测为准。
