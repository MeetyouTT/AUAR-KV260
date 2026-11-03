# 汐蓝 GTK/GStreamer 板端播放器适配

用户在板端环境检查后问“怎么做”。已按 ZIP README/当前范围、最新板端证据及 A 负责视觉+FPGA 的安排，推进可独立进行的缓存玩偶播放器。工作目录 `/home/ghmd/aura-board-avatar-gtk-20261009`；[完整报告](/home/ghmd/aura-board-avatar-gtk-20261009/IMPLEMENTATION_REPORT.md)。

## 实现

新增 GTK3 入口和配置，复用原 FSM、原 PNG、五套口型、眨眼、选定声线四段缓存；画布/玩偶框/contain落位/底色读取原合同。独立 GStreamer 音频进程输出到 MCP01，24 kHz 单声道转换 48 kHz 双声道 S16LE，以 sink position 控制口型并处理暂停、取消、旧代次、设备失败和启动超时。兼容旧 Pillow 常量，保留 PC 默认 Qt worker。

回收中文字体、原版权/许可、源 SHA；新增缓存运行包构建器、原生无声管线检查和 10 项音频生命周期测试。说明入口 [BOARD_AVATAR_GTK.md](/home/ghmd/Win共享文件/共享文件夹/aura/docs/BOARD_AVATAR_GTK.md)，更新主仓 README/当前安排/框架状态。原 6 文件备份和指纹保存在工作目录，原图/音频/参考未改。

## 实测

- 主机 **58 项测试通过**，原 48 + 新 10；正式 **573 PNG/4 WAV/42 眨眼层** 核验通过，源码/配置/说明链接核对通过。
- Ubuntu GStreamer 1.16.3 与 KV260 1.18.5 的真实原生 **fakesink** 管线均通过格式转换、暂停/恢复、取消、旧代次和 EOS；转换后为 48 kHz 双声道，1 秒 fixture 输出 191996 字节。这是原生软件管线证据，未发声。
- 板上 GTK 可连接 `:0`，Pillow 8.3.2 常量/变换通过；板上 10 项音频生命周期测试通过，未创建玩偶窗口或打开播放设备。
- 审阅的小包18 KB写入 `/home/root/aura-avatar-gtk-stage/native-probe-c9a53bcb97d3acda`；9 载荷核对、31 UART 命令输出 SHA/长度核对通过，控制台回显恢复。[板端记录](/home/ghmd/aura-board-avatar-gtk-20261009/board_native_validation.json)。
- 完整缓存包 `aura-board-avatar-gtk-runtime-20261009T112752Z-57fc8c.zip` 已生成：217023529 字节，**871 载荷＋清单回读通过**，SHA `1a8677ce385516b406344f5e22acfed72e1fd9ab1ffe79aa745760e1137917de`，位于主仓 artifacts/releases。该包范围是玩偶子系统，没有 GPU 模型/固件；不表示真实 UI/声音通过。

## 限制与下一步

完整包尚未送到板端；最新网络证据为 eth0 DOWN / IP 未知，异步询问接网线的能力尚未收到回复。等待不是授权或已连接事实。下一步经可用有线网络或拷贝介质部署独立目录，资源/库预检，再验收窗口、中文、音频/口型、暂停/打断和实屏；随后与 A 视觉/FPGA并行测CPU/内存/帧间隔/响应。

本轮没有安装镜像依赖、改网络/系统显示/音量、访问相机、停止其他程序、改写 FPGA 或驱动舵机。机构继续等待 3D 模型。33 ms 调度和三序列缓存是配置；总内存、帧率和声学同步仍待实际测量。
