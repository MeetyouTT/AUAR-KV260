# 汐蓝部署连接复查与网线用途

用户要求“看看什么情况”，随后询问“等一下，网线有什么用”。本轮只读复查连接、显示、音频、进程、网口链路和拷贝介质；解释网线用于当前大素材传输及后续 Windows 模型服务通信，缓存播放器本身部署后可离线运行，亦可用 U 盘拷贝，不要求连接互联网。

## 当前实测

UTC 2026-10-09 11:39–11:40：主机侧 Xilinx 串口链接存在，ttyUSB1 无其他进程占用；UART root shell 成功，boot ID 仍为 `c2753755-e758-4ab6-a4b6-2929271aa723`。Xorg :0 / 1024×600 / 59.85 Hz，DP-1 connected/enabled/DPMS On；MCP01 仍被 ALSA 识别。视觉 PID 16981 的 realtime_vision.py 仍在运行，这只是进程证据，不表示算法或并行性能已验收。

板端 eth0 的 ip flags 为 `<NO-CARRIER,BROADCAST,MULTICAST,UP>`，`carrier=0`，ethtool 明确 `Link detected: no`：接口在管理层已启用，但当前没有有效物理链路，无板端 IP。不能把 DOWN 简单解释为没有执行启用命令；本轮没有修改接口/DHCP配置。链路断开时 ethtool 显示的 10 Mb/s/Half 不能当作已协商成功的速度。

板端 `/home/root/aura-avatar-gtk-stage/` 仅看到 `native-probe-c9a53bcb97d3acda` 小包子目录；未观察到 board_avatar_gtk.py 运行进程。块设备清单未见 USB 磁盘，`/media`、`/mnt`、`/run/media` 为空。完整缓存运行包仍准备在 Ubuntu 共享目录，未在本轮传输或启动。

## 记录与验证

新增探针 `network_link_and_media` 于 [只读诊断脚本](/home/ghmd/aura-board-avatar-baseline-20261009/read_board_environment.py)，补充 ethtool/ip/sysfs 和介质清单读取；本地探针语法/行长核验通过。两次 UART 会话共 **5 份响应** 的长度/SHA256/JSON 回读一致，会话完整且回显恢复。[本次核验](/home/ghmd/aura-board-avatar-gtk-20261009/connection_recheck_20261009T1140.json)。

证据目录：`aura-board-avatar-baseline-20261009/evidence/20261009T113917.278957Z-board-environment/` 和 `20261009T114010.625920Z-board-environment/`。

## 下一步与边界

当前网线用于快速传输约 207 MiB 的完整玩偶运行资源；USB 串口现已能执行控制/诊断，但大包传输慢。部署可选通畅的有线局域网或 U 盘。后续接 Windows ASR/VLM/TTS 等模型服务时，需要板卡与主机可通信的局域网；当前四段缓存播放不依赖该服务。

若采用网络，先检查网线两端连接与对端路由器/交换机是否通电，确认物理链路后再核对 IP 和可达性。用户目前在了解用途，未收到接线方式的新选择；不把询问当作选择已完成。本轮没有部署文件、播放音频、创建窗口、改显示/网络/音量、访问相机或操作 FPGA/舵机。
