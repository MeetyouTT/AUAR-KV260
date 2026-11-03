# 视觉边界切页同步修复

日期：主机UTC2026-10-29（洛杉矶当地10月28日晚）。用户反馈视觉追踪转玩偶交流后两条边界滞留。

已查阅ZIP项目README、方案/分工入口、项目索引、最新宽版实板记录及Win共享入口。以boot55152f95的500..2500µs宽版及device-skills为基线。

完成：确认边界为独立GTK进程每0.5秒轮询页面，错误路径保留旧active；新增Unix datagram导航通知、GTK隐藏/显示服务器同步后ACK、页面序号/GUI代次和旧刷新屏蔽。改 `board_avatar_gtk.py`、`face_zone_editor.py`，新增 `boundary_visibility.py`。编辑器settings与当前控制器对齐，几何逐项比对相同。

实测：本机16项回归通过；实板4轮vision/main检查两个边界均在命令返回时unmapped，0.65秒后仍隐藏；另快速往返两轮通过。四轮隐藏ACK10.012..32.577ms。v1的60ms等待有一次未获回执，失败保留；v2增加耗时诊断和200ms有界等待，上述实板验收通过。最后一次ACK12.611ms，服务应用2.871ms/无ACK错误。

当前：boot55152f95，GUI supervisor114923/GTK114988，editor115144，相机21824未重启。GUI目录 `gui-page-sync-v2`、编辑器 `editor-page-sync-v2`，均在板端 `/home/root/aura-boundary-nav-20261029/`；配置SHA `12af11467b3ca0c0a1e6b57ac203e887d658a9799a159e39dfa90dbff60037d4`。279组件，原宽版277项不变。新增systemd drop-in生效并核对SHA；原unit/运行目录保留。任务state最终为VERIFIED。

范围：舵机500..2500µs、READY/flags0保持，宽度1576/target2500/ref1336/epoch65/ACK16保持；本次0运动测试指令，FPGA/模型/运动参数未改。结束恢复main。无新实体角度/语音延迟/HDMI验收。

证据：[共享交付](/home/ghmd/Win共享文件/协作任务/2026-10-29_边界切页同步/README.md)，包含最终源码、补丁、指纹、16项测试输出、原生窗口映射及部署状态；本地私有原始证据 `/home/ghmd/aura-boundary-nav-20261029/` 和 `aura-post-power-20261022/transfer-boundary-nav-*-20261029/` 保留。未共享UART原文/图像/音频/数据库/模型权重，未代写Windows回执。

未验证：肉眼切页效果/光学同步、断电重启后验证、Windows同步接收。板卡壁钟为2021且未同步；本轮记录采用主机UTC，不把板卡时间误当验收日期。
