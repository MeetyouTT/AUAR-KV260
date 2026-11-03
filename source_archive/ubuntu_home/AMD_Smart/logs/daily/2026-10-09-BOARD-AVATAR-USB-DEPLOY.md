# 汐蓝运行包上板、显示与真实音频验证

日期：2026-10-09；串口证据使用 UTC 时间。用户将 U 盘移插 KV260 后回复“好了”，后续确认声音偏小并明确要求“调到最大”。本记录更新此前仅完成 Ubuntu 拷贝的状态。

## 实际完成

从板端 `/run/media/sda1/AURA_AVATAR_20261009_1a8677ce` 读取完整运行包，保存并展开到新独立目录 `/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009`，保留 `aura/` 与 `deliverables/` 相邻。原 ZIP 为 217023529 字节，SHA256 `1a8677ce385516b406344f5e22acfed72e1fd9ab1ffe79aa745760e1137917de`；871 个载荷的大小、SHA 和写后回读通过。16 套正式资源、573 PNG、4 WAV、42 张眨眼层预检通过。

板端 Pillow 8.3.2 缺新枚举，初次播放出现 `Image.Transform` 错误。修改 `board/interaction/avatar_player.py`，通过兼容枚举回退解决；原文件与旧日志保存在 `patch-backup-pillow/`。GTK 定时回调改用空闲优先级，避免持续渲染占住正常重绘；原件保存在 `patch-backup-refresh/`。

窗口遮挡另有独立原因：现有视觉预览使用 `override_redirect` 并置顶，普通 GTK 窗口在其下方。只提升本界面及其所属窗口外框后，真实截图显示中文按钮和汐蓝。没有停止原视觉 PID 16981。后续设置版将该提升动作加入启动流程，详见 [设置界面日志](2026-10-09-BOARD-UI-SETTINGS.md)。不能把定时优先级改动单独表述为遮挡问题的原因或完整解决方案。

MCP01 以 `hw:CARD=MCP01,DEV=0` 实际输出 48 kHz 双声道音频；四段缓存台词已实际播放。问候 5.04 秒，开心 4.88 秒，轻声 5.6800416667 秒，长句 12.24 秒。后面三段 EOS 到达，暂停时播放位置增量为 0，继续和打断通过，旧代次没有晚到重启；同时观察到 ALSA PCM `RUNNING`。用户反馈“音响声音太小了”证明现场可听，不能替代声学质量、精确同步和整机验收。

按用户要求，将 MCP01 `PCM` 从 29% 调到 100%，读回 `Playback 151 [100%] [-0.06dB] [on]`；麦克风控制保持原值。音量 100% 后问候播放检查通过。

U 盘已在 KV260 安全卸载 `/dev/sda1`；运行包和资源在板端存储上仍在，当前播放不依赖 U 盘。没有重新格式化或修复文件系统。

## 可核验证据

工作目录：[GTK 部署与证据](/home/ghmd/aura-board-avatar-gtk-20261009)。关键原件位于其 `evidence/`：

- `20261009T124242.018512Z-usb-runtime-deploy/`：871 载荷回读。
- `20261009T124616.240587Z-usb-runtime-check/`：资源预检。
- `20261009T124920.505680Z-usb-runtime-repair-pillow/`、`20261009T125622.879229Z-usb-runtime-repair-refresh/`：兼容性修改及备份。
- `20261009T125936.206314Z-usb-runtime-audio-controls/`：真实 PCM、EOS、暂停/继续、打断。
- `20261009T130202.527837Z-usb-runtime-fetch-window/board-window.jpg`：首个已目视确认的完整窗口。
- `20261009T130428.921412Z-usb-runtime-unmount-usb/`：板端安全卸载。
- `20261009T130615.739435Z-usb-runtime-volume-max/`：100% 回读且麦克风不变。
- `20261009T130637.025960Z-usb-runtime-greeting/`：100% 音量播放。

最终设置版的独立证据审计同时重新核对本轮部署、音频、卸载、音量四份响应的大小及 SHA，见 [最终核验](/home/ghmd/aura-board-avatar-touch-20261009/validation_final.json)。

## 当前边界

缓存播放与窗口已实际上板，当前状态由后续设置版更新。仍未接通实时 ASR/VLM/TTS、验收最终声画同步或进行长时间整机性能测试。视觉与玩偶并行时动画明显慢于设定的 33ms 调度间隔。原视觉、FPGA 和舵机未被本次播放器部署修改。
