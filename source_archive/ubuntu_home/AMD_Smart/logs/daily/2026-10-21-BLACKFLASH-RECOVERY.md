# 整屏黑闪：一次显示输出重初始化

2026-10-21 UTC12:09后检：用户确认“刚才插拔hdmi，画面已经正常”。同boot EDID由0恢复128字节/SHA727d3e18…，8秒复核稳定，1024×600/59.85Hz、三服务PID及配置SHA保持。物理插拔本次有效；软件OFF/ON此前无效。未改启动参数或继续重启，永久冷启动修复仍未验证。[实屏恢复及证据](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-21_physical_hdmi_recovery/README.md)。

2026-10-21 UTC12:01后续：用户明确软件重初始化后仍整屏黑闪，实屏未修复。只读确认EDID仍0、无AUX字符设备，但存在DRM debugfs临时EDID覆盖接口（未写入）；16位色深已满足。未改U-Boot/1080p/分配器寄存器或重复关开。物理HDMI单次拔插结果、屏幕供电接法待回执。[官方建议核查与后续分支](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-21_blackflash_followup/README.md)。

2026-10-21 UTC11:54～11:58。用户“那怎么办”后继续处理。实际boot8817dc71…/speech-motion922dab49a74f。

先两次时序守卫拒绝（空白精确匹配、垂直height遗漏），均在显示动作前退出；已纠正初步“时序变化”判断。最终7项有效/负例解析检查通过。实际只执行一次xrandr关闭（保持framebuffer1024×600），读回CRTC inactive，等待2.002秒，再恢复原49MHz/59.85Hz，读回active。15秒独立恢复定时器建立后才关闭，正常恢复后已停止，后检inactive/not-found。

三服务PID1057/988/1048、active/NRestarts0保持，8秒帧10306→10370/UI IDLE/error空；启动器cd168022…/Xorg164afc02…/配置1815ddb8…未改。EDID仍0，实屏结果已询问，未收到回执，不能称修复或冷启动验收。

仅新增隔离助手与恢复脚本/结果，未部署永久补丁、重启业务/板卡、运动或CPU优化。最终UART/后检退出0、SHA/回显恢复通过。[交付与证据](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-21_blackflash_recovery/README.md)。Windows同步未确认。

