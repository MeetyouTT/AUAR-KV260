# 板端界面启动文件

2026-10-20最新：用户明确要求回退到约三小时前。已撤回下面05:02的HDMI启动补丁，板端启动器恢复`cd168022…`、Xorg恢复`164afc02…`，共享启动器恢复修改前SHA`61d852c0…`，新误报回归已归档撤回。原17项显示fixture通过，板端实际预检/界面/相机通过，恢复玩偶交流页。GUI业务源码及241项配置与回退目标相同，保留语音/身份/相机功能和数据；免点击对话当前暂停。实屏闪烁是否消失仍待回执。见[回退依据、实际结果及备份](../../../deliverables/2026-10-20_ui_time_rollback/README.md)。下条为已撤回的历史修复记录。

2026-10-20显示启动修复已合入源码：OFF失败/超时不再算完整重置，分别记录关闭、等待、恢复；同boot仍只尝试一次，保留2秒关闭设置。37项显示fixture及2项真实端口测试通过。实际render24-budget/e06409743174的启动器和Xorg专用1024×600时序已安装、下次启动载入；候选42项Ubuntu/KV260软件测试通过，物理冷启动未验收。详见[完整交付、验证边界及回退](../../../deliverables/2026-10-20_display_startup_fix/README.md)。本目录历史config/release清单不代表新发布，禁止覆盖当前241项组件/较新GUI和音频。

2026-10-18最新实际配置：当前开机入口为 `aura-automatic-conversation-20261018/candidate-b1b08f8b0b2b/startup`，已将每boot输出关闭时间由1秒改为2秒，普通重启/断电开机均重新初始化，17项逻辑测试及板端预检通过；下次实际冷启动/物理花屏仍待验证。活动配置、备份和证据见[每次开机HDMI重置](../../../deliverables/2026-10-18_hdmi_boot_reset/README.md)。下方本目录旧config/release清单为历史快照，不应覆盖新版连续对话入口。

2026-10-17 当前源码与部署清单更新为 `d2e45eb7fee4fa08`：显示冷启动等待/稳定和每 boot 一次输出重建补丁。配置从实板 `190bbd429af06931` 回读，保留当前 GUI/ASR/相机修复的54项组件哈希。已安装为下次启动入口，本轮保持当前进程，不作为冷启动/物理花屏已修复的证据。见 [实测与限制](../../report/display_coldboot_20261017/REPORT.md)；下文是历史快照。

当前源码/清单为 `abd3df01b6d50a3b`，包含固定 ByteTrack 适配组件；实际运行更新 `33fd4bc855871500`，配套验收修正版 `ea926df36eb116cd`。见 [跟踪说明](../../docs/BOARD_TRACKING.md)。下文 `40f5d358d1c0d7ba` 为前一 YOLO 基线。

此目录保存当前启动版本 `40f5d358d1c0d7ba` 的源码、配置和 SHA 清单，配套 YOLO 更新包 `0da0dc7f7289d5b7`。界面入口仍为 `tools/board_avatar_gtk.py`；本目录监督启动和退出，并固定 UI、预览、YOLO 桥接和参考图的组件哈希。实际安装与验收状态见 [YOLO 说明](../../docs/BOARD_YOLO.md) 及下方启动说明。

操作、当前路径、回退及验收边界见 [启动说明](../../docs/BOARD_UI_STARTUP.md)。配置含本次实际内核、模块、GUI 和屏幕的 SHA；更换目标环境时先验证并更新，不能照搬到其他板卡。

主机回归检查：`python3 -B scripts/board_ui_startup/test_launcher.py`。测试需要本机 loopback 套接字权限；两项只测试端口生命周期，不启动界面或访问硬件。

`python3 -B scripts/board_ui_startup/test_display_fallback.py` 检查五种显示保护条件；它是模拟命令输出的测试。EDID 为空时仅允许已实测的本屏时序，须同时读到 connected 和指定微雪触摸设备；不覆盖不同的非空 EDID。真实缺 EDID 恢复及最新冷启动仍待验收。

在本目录执行 `python3 -B -m unittest test_display_fallback test_display_startup -v`，共17项：包括原保护条件在新配置下复测，以及 EDID 迟到、宽限/稳定等待、同 boot 不重复、新 boot 换代、恢复失败、取消后恢复和失败重试不再次关闭输出。所有显示命令均为 fixture，不切换主机或板端的真实显示。

部署原始记录和 UART 操作工具保存在 `/home/ghmd/aura-board-ui-autostart-20261009/`。此前完整缓存 ZIP 不含本次启动服务；当前由独立启动包配套安装，统一发布包仍需后续整合。
