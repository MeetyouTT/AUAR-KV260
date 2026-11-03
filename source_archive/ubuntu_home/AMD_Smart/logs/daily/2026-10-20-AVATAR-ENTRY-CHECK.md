# 玩偶程序入口只读核查

用户询问玩偶界面在哪里、一般如何打开、板卡桌面是否有玩偶App。按项目资料及最新启动记录，完成两次板端只读检查；证据UTC2026-10-21 05:09/05:10，本地20日。

实读新boot33d0dc5b…，`aura-avatar-ui.service` enabled/active/running、NRestarts0，监督1056、GUI1455，日志READY。API IDLE/devices/error空；X属性确认“汐蓝”全屏窗口存在并Normal，另有Matchbox Desktop/Panel。本次GUI自启已发生；没有物理观察/切窗，不宣称实屏前台已确认。

检查`/usr/share/applications`、`/usr/local/share/applications`、`/home/root/.local/share/applications`、`/home/root/Desktop`与中文桌面目录，没有AURA/avatar/汐蓝/玩偶匹配的.desktop快捷入口。程序已安装，启动方式为systemd自启；没有桌面可点App图标。若在设备状态页面，按现有界面底部“返回”进入演示层，再选“玩偶交流”。确实未运行时root终端可`systemctl start aura-avatar-ui.service`，已运行时该命令不负责切前台。

本轮未新增快捷方式、改板端文件、重启服务、切页/切窗或发显示/运动命令。后续可新增只启动/激活现有实例的桌面入口；这是建议，尚未实现。发现新boot但没有核对HDMI初始模式/EDID/重置阶段或物理花屏，不视为上一修复冷启动验收通过。

共享[说明和过滤证据](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-20_avatar_entry_check/README.md)已写入；Ubuntu回执/共享入口更新，Windows回执未代填，原始UART仅保留私有工作区。

## 用户报告布局变化：UTC21日05:51～05:52只读核查

当前API debug/connection，私有X截图为“服务连接”页，顶部声音测试/设备状态/服务连接/设置；此前截图为演示层的玩偶交流/视觉追踪，左侧聊天。GUI/wrapper/截图模块及布局/主题/GUI配置共7个文件SHA、启动配置SHA均与修HDMI前实板基线相同，1024×600/全屏、GUI1455/监督1056/NRestarts0保持。已确认切换界面层/页面造成导航和左侧内容变化，没有证据显示本次HDMI修复替换布局；用户尚未回执具体指哪处变化，不能排除其指更早版本。右下角返回文字截图有截断，入口不清楚；本轮未自动发布修复或切回页面。

附带新启动软件证据：Xorg16.899秒实际初始1024×600，新启动器OFF/等待/恢复/完成均true、无错；模式时序修复与分阶段记录已经运行，但没有物理冷启动/花屏消除回执。第一次探针在可选xrdb命令缺失处退出，修正为报告不可用后重读通过，无运行配置修改。没有切页/切窗、服务重启、显示控制或运动命令，截图仅私有保留。详见[核查与过滤证据](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-20_avatar_layout_check/README.md)。

## 用户报告四角发黑：UTC21日05:56～05:57

暂按整屏四角理解并询问具体区域，尚待回执。私有X截图为设置页，四个外角RGB均[255,255,246]，各角8/32/80平方区域无所有通道低于32的像素，未复现大块黑角。输出1024×600/59.85、单位Transform、DRM源/目标同尺寸同原点、RG16/pitch2048/CRTC active；GUI全屏、Monitor On。Matchbox工作区留顶部34像素，但截图实际全屏，不能由此认定黑角原因。EDID仍0，不能排除识别/物理同步问题，尚不能定因。需手机完整实屏照片（含四角边框）及区域确认，未擅自修改时序/布局或控制显示。共享[过滤证据及限制](/home/ghmd/Win共享文件/语音共享文件/deliverables/2026-10-20_screen_corner_check/README.md)，图片/原始UART不共享；Windows回执不代填。
