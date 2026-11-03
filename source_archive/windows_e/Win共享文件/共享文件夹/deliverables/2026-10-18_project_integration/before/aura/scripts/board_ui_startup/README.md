# 板端界面启动文件

当前源码/清单为 `abd3df01b6d50a3b`，包含固定 ByteTrack 适配组件；实际运行更新 `33fd4bc855871500`，配套验收修正版 `ea926df36eb116cd`。见 [跟踪说明](../../docs/BOARD_TRACKING.md)。下文 `40f5d358d1c0d7ba` 为前一 YOLO 基线。

此目录保存当前启动版本 `40f5d358d1c0d7ba` 的源码、配置和 SHA 清单，配套 YOLO 更新包 `0da0dc7f7289d5b7`。界面入口仍为 `tools/board_avatar_gtk.py`；本目录监督启动和退出，并固定 UI、预览、YOLO 桥接和参考图的组件哈希。实际安装与验收状态见 [YOLO 说明](../../docs/BOARD_YOLO.md) 及下方启动说明。

操作、当前路径、回退及验收边界见 [启动说明](../../docs/BOARD_UI_STARTUP.md)。配置含本次实际内核、模块、GUI 和屏幕的 SHA；更换目标环境时先验证并更新，不能照搬到其他板卡。

主机回归检查：`python3 -B scripts/board_ui_startup/test_launcher.py`。测试需要本机 loopback 套接字权限；两项只测试端口生命周期，不启动界面或访问硬件。

`python3 -B scripts/board_ui_startup/test_display_fallback.py` 检查五种显示保护条件；它是模拟命令输出的测试。EDID 为空时仅允许已实测的本屏时序，须同时读到 connected 和指定微雪触摸设备；不覆盖不同的非空 EDID。真实缺 EDID 恢复及最新冷启动仍待验收。

部署原始记录和 UART 操作工具保存在 `/home/ghmd/aura-board-ui-autostart-20261009/`。此前完整缓存 ZIP 不含本次启动服务；当前由独立启动包配套安装，统一发布包仍需后续整合。
