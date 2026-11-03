# KV260 简易图形操作与设置界面已部署

日期：2026-10-09；证据目录时间为 UTC。用户要求基于现有 UI 完成简易但完整的操作界面，能改音量等必要设置并支持触控。已实现并部署软件功能；物理触屏当前未被板卡识别，手指操作与坐标映射仍未验收。

## 实际结果

沿用原汐蓝、缓存声线和 1024×600 画布，右侧显示玩偶，左侧分“互动”和“设置”。当前板端停在“设置”页，音量 100%、非静音、全屏、省电动画关闭。设置已实际保存到安装目录的 `avatar_user_settings.json`。

| 页面 | 已实现操作 |
| --- | --- |
| 互动 | 四段缓存台词、暂停/继续、打断、重新开始、保存画面 |
| 设置 | 0–100% 音量滑块、10% 加减、静音/取消静音、全屏切换、省电动画、恢复默认 |
| 状态 | 实际音量回读、调整与失败反馈、音响连接和触摸设备检测 |

主操作按钮高 56–64px，页签 48px，按钮字体 19px。GTK 原生激活处理鼠标与触摸，触摸事件只观察记录，避免同一手势再次调用动作；同按钮短时间重复激活合并。声音设置使用有界后台队列，连续滑动合并待处理值，ALSA 操作不在 GTK 主线程执行。只写 MCP01 `PCM` 播放控制，回读确认后才保存；麦克风不变。全屏与省电偏好同样保存，重启播放器时恢复。

新增启动置前逻辑只提升自身窗口及其外框，解决现有视觉预览遮挡。最后只读检查确认原视觉 PID 16981、设置界面 PID 48503、音频工作进程、Xorg 与 dfx-mgrd 同时存在；板卡 boot ID 仍为 `c2753755-e758-4ab6-a4b6-2929271aa723`。

## 改动文件

以下相对路径基于 `/home/ghmd/Win共享文件/共享文件夹/aura`：

- `tools/board_avatar_gtk.py`：双页操作界面、反馈、设置入口、触摸观察与启动置前。
- `tools/board_ui_settings.py`：配置保存/恢复、MCP01 异步控制与回读、触摸设备检测。
- `tools/x11_foreground.py`：只将本窗口及其所属外框置前。
- `tools/realtime_bridge.py`：允许板端实例额外注册页面/设置命令，默认客户端命令范围保持原约定。
- `tools/package_board_avatar.py`：完整运行包包含新模块、说明和测试。
- `tests/framework/test_board_ui_settings.py`：12 项配置与后台控制契约测试。
- `docs/BOARD_UI_SETTINGS.md`：操作、实现、部署和验证边界；同步 `README.md`、`docs/BOARD_AVATAR_GTK.md`、`docs/FRAMEWORK_STATUS.md`、`docs/CURRENT_ASSIGNMENT_AND_BOARD_UI.md` 的当前状态。
- 前序兼容性改动 `board/interaction/avatar_player.py` 见 [部署日志](2026-10-09-BOARD-AVATAR-USB-DEPLOY.md)。

## 验证

1. Ubuntu `python3 -B -m unittest discover -s tests/framework -v`：70 项通过，0 失败、0 错误。新增 12 项覆盖持久化与恢复、错误配置保留、参数验证、ALSA 输出解析、回读不符、设备错误、后台运行和滑动请求合并。
2. KV260 Python 3.9.9 实际运行同一 12 项设置测试：全部通过；运行资源检查通过。
3. KV260 真窗口 XTest 指针检查：进入设置、音量减/加、静音/恢复、滑块拖到 49%、省电切换、退出全屏、恢复默认和配置文件回读通过；结束恢复 100%/非静音/全屏/普通动画，麦克风控制保持原值。
4. KV260 真窗口互动检查：播放、暂停、继续、打断通过，暂停期间播放位置增量 0；最终返回设置页并保存画面。
5. [最终截图](/home/ghmd/aura-board-avatar-gtk-20261009/evidence/20261009T133208.806715Z-usb-runtime-fetch-window/board-window.jpg) 1024×600，61062 字节，SHA256 `67ca66dfa94b7b68d869966fb1b410744a553eaccd9be95128fa470864dcf11b`，已目视确认控件完整且没有裁切。
6. 独立核验脚本回读更新包/当前源文件、27 份部署命令响应、8 份关键阶段 UART 响应、最新环境探测、截图和完整运行 ZIP。大小和 SHA 全部一致；报告 [validation_final.json](/home/ghmd/aura-board-avatar-touch-20261009/validation_final.json)。该核验脚本初次用了主机 Python 不支持的 `removeprefix`，只影响本地审计；已改为兼容写法并重跑通过。

上述窗口检查使用 XTest 指针事件，**不能代替物理触摸验证**。板端 `touch_devices` 为空，输入枚举为鼠标、摄像头/音频按键和 GPIO，未见触摸控制器。

## 部署与包

板端安装目录：`/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009`。

设置更新包位于 [工作目录](/home/ghmd/aura-board-avatar-touch-20261009)，16256 字节，SHA256 `ddd4944081890e22e76d1bd105106059ae3cea09636fe6f97c2093868a09b661`。包含五个载荷，部署前逐项验证旧 SHA，备份后写入并回读；只停止和重启原独立播放器 PID 46865，没有停止视觉。备份位于板端 `touch-update-ddd4944081890e22/backup/`。当前 UI 源 SHA256 `dbf55275035374221db1303bcf7549b54a6e0821dfa352fda41bb63df7cd7e7e`。

另外生成最终可迁移完整运行包 [ZIP](/home/ghmd/Win共享文件/共享文件夹/aura/artifacts/releases/aura-board-avatar-gtk-runtime-20261009T132845Z-c742c0.zip)：217036400 字节，SHA256 `ff45dc1a157b88d1cb3ffea41908d7cac4a7ab95b4c80762aaa6ae0cbaf182bd`；875 个载荷和清单回读核验通过。该新 ZIP 未整包再次部署；板端实际为已验证原运行包加兼容性和设置更新，不能混为同一个部署工件。

原始证据入口：`aura-board-avatar-touch-20261009/evidence/20261009T131910.962991Z-deploy/`；窗口设置检查为 `aura-board-avatar-gtk-20261009/evidence/20261009T132550.101267Z-usb-runtime-ui-settings-check/`；窗口播放检查为 `20261009T132700.781496Z-usb-runtime-ui-pointer-playback/`。最新环境证据为 `aura-board-avatar-baseline-20261009/evidence/20261009T133349.670700Z-board-environment/`。

## 未验证与下一步

- 软件已适配触摸，但须屏幕本身支持触摸并将触摸数据 USB 接至 KV260；显示连接本身不证明触摸数据已连接。设备识别后仍要验证手指点击、拖动、边缘坐标及单次激活。
- 现有视觉并行下最近记录的渲染间隔 p95 约 473ms，不能称为 30fps；动画流畅度仍需优化。省电模式是 250ms 调度目标，不是实测帧率承诺。
- 当前为缓存播放与本地设置；实时模型联调、精确声学/声画同步及整机长测未完成。
- 设置会保存，界面在当前会话运行；没有新增开机自启服务。机构继续等待 3D 模型，A 的视觉/FPGA 分工不变。
