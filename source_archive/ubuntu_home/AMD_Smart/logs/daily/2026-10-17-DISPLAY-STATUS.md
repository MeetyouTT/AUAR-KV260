# 2026-10-17 板卡屏幕状态只读检查

用户要求检查板卡屏幕是否开启。通过主机 Xilinx UART 读取当前 KV260，检查时间为 UTC 2026-10-17 10:20（本地 03:20）。

实际结果：

- `card0-DP-1/status=connected`，但 `enabled=disabled`、`dpms=Off`。
- `xset q` 返回 `Monitor is Off`，DPMS 已启用，Standby/Suspend/Off 均设置为 600 秒；该配置与当前休眠状态相符，未追溯实际休眠触发事件。
- `xrandr --current` 仍保留 `1024x600` / `59.85Hz` 模式；模式存在不能证明物理屏已点亮。
- `aura-avatar-ui.service` 与 `xserver-nodm.service` 均为 active/running；X11 缓冲抓图为 1024×600 的 AURA 视觉追踪页，显示等待相机连接。截图说明 GUI 仍存在，不作为物理面板亮屏证据。
- UI 同时返回 MCP01 声卡不可用，本轮未排查该项。

结论：检查时系统将显示输出置于关闭/省电状态；接口仍检测到屏幕，GUI 仍运行。未直接观察面板电源或背光，因此不判断物理电源开关位置。

验证：三项 UART 命令均 exit_code=0，传输长度/SHA256 通过既有 UART 校验，JPEG 长度/SHA256 核对通过并查看图像；串口回显已恢复。没有修改板端显示设置、唤醒屏幕或重启服务。

证据目录：`/home/ghmd/kv260-display-check-20261017/evidence/20261017T102021.637633Z/`。当前 boot ID 为 `e109cf65-d3c7-4396-9cf6-4bdc7a253929`。新增主机检查脚本：`/home/ghmd/kv260-display-check-20261017/check_display.py`。

沙箱内首次运行因串口节点不可见而停止，未发送板端任务命令；主机权限运行完成检查。首次失败记录保留在同一 evidence 父目录。

## 用户授权后唤醒

用户随后要求点亮屏幕。UTC 10:23 通过同一 UART 执行 `DISPLAY=:0 xset s reset` 与 `DISPLAY=:0 xset dpms force on`，两条命令均成功。等待 2 秒核验 `Monitor is On`，DRM 为 `connected/enabled/On`；后续独立显示与电源查询仍为开启，分辨率 1024×600。GUI/Xserver PID1048/1047 保持 active/running。

本轮四项响应均退出 0，传输完整性通过，截图 JPEG 长度/SHA256 通过，串口回显已恢复。没有改变 600 秒自动息屏设置，因此后续空闲仍可能再次息屏。未直接观察物理面板背光。

唤醒证据：`/home/ghmd/kv260-display-check-20261017/evidence/20261017T102351.947469Z/`；主机检查脚本新增显式 `--wake` 参数，默认仍只读。

## 用户反馈黑屏：纠正状态结论并排查

用户随后明确反馈物理屏幕仍黑。此前回复中的“已唤醒屏幕”只得到软件 DPMS 状态支持，不能作为物理亮屏结论；以用户现场黑屏反馈为准，亮屏目标尚未完成。

UTC 10:30 深入只读检查：

- Xrandr 亮度 1.0、Gamma 1:1:1、link-status Good；DRM CRTC active/enabled，Xorg framebuffer 为 1024×600。X11 缓冲仍有 AURA 界面。
- 屏幕 EDID 为 0 字节，Xrandr 无 EDID 属性、物理尺寸 0×0，内核提供回退模式。当前 1024×600 是已存在的手动模式，不能据此判断当前面板身份。
- USB 总线仅有两个 root hub，原微雪触摸控制器、MCP01、摄像头以及下游 hub 均不在当前枚举中；没有可由 sysfs 控制的 backlight 设备。
- 内核日志在 uptime 32732 秒起出现 USB port2 reset/disable 错误 `-71`，随后 MCP01、摄像头与 hub 断开。日志中的 `Maybe the USB cable is bad?` 是内核提示，不作为线缆损坏的确诊。

UTC 10:31 按既有亮屏授权重建显示链路：`xrandr --output DP-1 --off` 后恢复同一 `1024x600/59.85Hz` 模式，重置屏保并 `dpms force on`，四条命令全部成功；EDID 仍为 0 字节，USB 设备仍缺失。没有从该软件状态再次宣称物理亮屏已恢复。

供电、线缆、USB hub 状态是待排查方向，不能凭本次证据区分断电、拔线或控制器/硬件故障。已询问用户屏幕是完全不亮、背光亮但全黑还是显示无信号，需要现场状态继续定位。

新增脚本参数 `--deep` / `--retrain`，默认检查行为保留。两轮证据分别为 `evidence/20261017T103036.555686Z/`（6响应）和 `evidence/20261017T103133.625238Z/`（7响应）；命令返回 0、响应输出 SHA256 独立核对通过，串口回显恢复。未重启整板、Xorg 或 GUI，未改持久配置、FPGA 或运动服务。

## UTC 10:43 再次复查

用户询问“现在呢”。实时深查仍为 EDID 0 字节、仅两个 USB root hub，未见触摸屏/MCP01/摄像头重新枚举；显示已再次进入 DPMS Off。沿用此前亮屏授权，于 UTC 10:44 执行同样的屏保重置与 DPMS 唤醒，返回 `Monitor is On`、`connected/enabled/On`。这只证明软件输出恢复，物理屏幕亮起仍未得到确认。

深查证据 `evidence/20261017T104328.604737Z/`（6响应）、再次唤醒 `evidence/20261017T104405.742168Z/`（4响应），全部退出 0、传输完整性校验通过且回显恢复。保持 600 秒息屏策略，未更改脚本或板端持久配置。

## UTC 10:46 HDMI 专项检查

用户要求查看 HDMI。检查既有 HDMI 对应的 `card0-DP-1` 链路，连续三轮 Xrandr 属性探测后读取 sysfs：三次均 `connected/enabled/On`，EDID 均为 0 字节。当前 1024×600 / 59.85Hz 模式保留，视频像素时钟实测 48999993Hz、DPDMA 参考时钟 444444440Hz，相关 enable/prepare 计数为 1。

板端未暴露 `/dev/drm_dp_aux*`，本轮无法通过字符设备读取接收端 DPCD/训练状态；不能将 AUX 列表为空报告成 AUX 物理故障。当前 dmesg 可见内容没有匹配到显示专用日志，同样不作为硬件链路正常的证明。

结论：可以确认板端显示输出及对应时钟开启，但连续读取仍不能取得屏幕识别信息，尚不能确认 HDMI 实物链路已恢复或判定线缆损坏。屏幕供电、输入选择、HDMI 连接及中间转换链路仍需现场核对。

新增检查脚本显式 `--hdmi` 参数，本轮未修改板端状态。证据 `evidence/20261017T104635.419221Z/`，4响应退出 0、输出 SHA256 独立核验通过，串口回显恢复。
