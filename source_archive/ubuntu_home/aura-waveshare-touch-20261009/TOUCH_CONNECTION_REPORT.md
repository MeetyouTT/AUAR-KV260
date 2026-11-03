# 微雪触屏连接结果

已识别 `WaveShare WS170120`（`0eef:0005`），正确绑定 `hid-multitouch`，恢复 1024×600 的 GTK 操作界面。

本轮已记录真实手指输入：25 秒内 3348 个 evdev 事件，GTK 收到音量滑块触摸及“互动／设置”页签点击。音量改变后，界面、ALSA 与保存配置一致，最终为 18%、非静音。实际窗口已查看，显示“触摸已连接”。

驱动安装至当前内核的 `extra/aura/`，新增 `/etc/modules-load.d/aura-touch.conf`，模块回读和加载路径检查通过。**新配置尚未经过重启验收**；GUI 自启、全屏边缘精度、多指压力与动画流畅度仍待验证。

- [改动、备份、问题处理及实际验证日志](/home/ghmd/AMD_Smart/logs/daily/2026-10-09-WAVESHARE-TOUCH-CONNECTED.md)
- [八份关键响应与真实输入核验](touch_connection_validation.json)
- [回读截图](evidence/20261010T005024.206584Z-window/board-window.jpg)
- [本轮恢复与复查脚本](touch_runtime.py)
- [离线证据核验脚本](verify_touch_connection.py)

本次 boot ID 为 `0ecc7063-1b99-4bca-9e9c-d9f8026732f5`。先前的 `TOUCH_REPAIR_REPORT.md` 与 `validation_final.json` 是接线前、另一启动会话的历史记录。

本轮文件包括 `touch_runtime.py`、`verify_touch_connection.py`、`touch_connection_validation.json`、本报告，以及诊断/加载工具的恢复支持；项目同步更新 `README.md`、`docs/BOARD_UI_SETTINGS.md`、`docs/BOARD_AVATAR_GTK.md`、`docs/FRAMEWORK_STATUS.md`、`docs/CURRENT_ASSIGNMENT_AND_BOARD_UI.md`、`AMD_Smart/PROJECT_BOOK_INDEX.md` 和本轮实测日志。GUI 运行源码没有改变。
