# 玩偶界面在哪里、如何打开

2026-10-20本地 / UTC21日05:09～05:10只读实测：玩偶程序名称为“汐蓝”，是板端独立GTK程序，由`aura-avatar-ui.service`开机自动启动。当前没有找到单独的桌面/App菜单快捷入口；检查范围见[入口证据](entry.json)，不代表全文件系统没有其他历史启动文件。

本次已是新boot `33d0dc5b-27f4-4060-ae25-d2e8e8ddabc3`。服务enabled/active/running、NRestarts0，监督PID1056、GUI PID1455，日志READY，API为IDLE/devices/error空。[窗口证据](windows.json)确认“汐蓝”窗口正常存在、为全屏，另有Matchbox Desktop和Panel；未执行切窗或物理观察，不据此保证用户当前肉眼所见。

日常开机应等待界面自动打开。若看见“设备状态/服务连接/设置”等按钮，已经在汐蓝调试层，可点底部“返回”再点“玩偶交流”。若看到Linux桌面，它与汐蓝窗口是不同界面。目前没有桌面图标可供点击；适合后续补充“汐蓝玩偶”快捷入口，点击时启动或切回已有窗口，避免重复启动实例。本轮只核查，没有擅自新增入口。

程序确实未运行时，可在板端root终端执行`systemctl start aura-avatar-ui.service`；这条命令不会把已经运行的窗口自动切到前台，不应通过反复手动运行Python启动第二份GUI。

实际ExecStart仍指向render24-budget/e06409743174启动器。发现新boot，只证明此次GUI自启成功；本轮未核对HDMI初始时序/重置分阶段或物理花屏，尚不能作为显示修复验收。没有修改板端文件、重启服务、切页/切窗或发送显示/运动命令。Windows同步和现场视图尚未确认，原始UART未共享。[操作来源](provenance.json)。
