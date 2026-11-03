# KV260 图形界面启动与恢复

2026-10-17 显示冷启动补丁：用户报告断电后再次开机花屏、重新插拔 HDMI 恢复。新启动器 `d2e45eb7fee4fa08` 已安装并写入服务，**下次服务启动/开机生效**；本轮未重启当前 GUI、相机或整板。新增 EDID 最多15秒宽限、显示身份稳定3秒、每 boot 最多一次输出关闭1秒后恢复，并保留原本已验证的固定时序回退及屏幕/触摸校验。主机17项、板端17项启动逻辑测试和实际组件预检通过；测试中的显示命令为 fixture，**真实断电冷启和物理花屏是否消失尚未验证**。本次读板发现启动记录为 EDID 缺失回退，不能据此确诊供电或 HDMI 硬件根因。详见 [报告](../report/display_coldboot_20261017/REPORT.md)。当前 GUI 仍使用原 `190bbd429af06931` 进程，下面各旧版本记录保留追溯。

2026-10-16 最新：双层界面已替换默认运行/开机入口，更新 `c2ce862bbed8ecb2`，启动器 `dc3fb02b00f4783b`。新增控制端口最多70秒等待释放，响应停止、不终止其他进程；本轮实际从STARTING到READY，最后服务enabled/active、NRestarts=0、音量58%。原五页文件与单元备份保留；本轮未整板重启，不视为冷启动通过。详见 [上板报告](/home/ghmd/aura-ui-layers-board-20261016/REPORT.md)。下方为历史版本记录。

2026-10-11 跟踪更新：实际运行 `33fd4bc855871500`、启动器 `abd3df01b6d50a3b`；验收助手修正版配套包 `ea926df36eb116cd` 与当前 37 个运行文件一致。80 项板端软件测试、服务/放大返回/设置保留通过，音量仍为 58%。[跟踪说明](BOARD_TRACKING.md)、[完整报告](/home/ghmd/aura-board-tracking-20261011/TRACKING_REPORT.md)。本版本冷启动未验；下文 `0da0dc7f7289d5b7`/`40f5d358d1c0d7ba` 是更新前 YOLO 基线。

更新：2026-10-11。五页触屏界面与真实相机由独立服务管理，均开机启用。最新 [YOLO 人体检测](BOARD_YOLO.md) 配套更新包 `0da0dc7f7289d5b7`，启动版本 `40f5d358d1c0d7ba`，实际结果见 [接入报告](/home/ghmd/aura-board-yolo-20261011/YOLO_INTEGRATION_REPORT.md)。此前外部重启后 EDID 曾为空，旧启动器反复等待；EDID 后来恢复，当前 1024×600 通过真实服务启动恢复。**本版本整板冷启动及真实缺 EDID 回退尚未验收**，不能把服务启用等同于冷启动通过。

## 启动流程

1. 沿用现有 `xserver-nodm.service` 图形桌面和 `systemd-modules-load.service` 触摸模块加载。
2. 核验 GUI、全部配置组件、触摸模块与内核；等待 EDID，连续稳定后恢复 `DP-1` 的 1024×600 / 59.85 Hz，并映射微雪 `WaveShare WS170120`。若 EDID 为空，先等待15秒，仅在输出 connected 且该触摸设备存在时允许使用此前本屏实测的固定时序；不同的非空 EDID 或冲突时序拒绝回退。每次开机最多关闭/恢复该输出一次，关闭前将尝试标记保存到 `/run/aura-display-startup.json`；即使服务失败重试也不反复闪屏。关闭后会在 finally 中尝试恢复，软件回读通过后再记完成。该标记不代表物理屏幕已通过验收。
3. 用独立目录启动原 GTK 界面，读取原 `avatar_user_settings.json`。仅当界面 API 真实返回 GTK 缓存模式状态后，才向 systemd 报告 READY。
4. 监督本界面子进程，异常退出按服务配置有限频率重试。触屏重新枚举时按名称重新映射，不写死 event 编号。正常停止时先取消本地播放，请求后台保存诊断并有界等待报告提交，再结束自身子进程。

启动不依赖 Windows 模型或网络就绪。相机由单独的 `aura-camera-ui.service` 拥有；UI 服务不负责 DFX/PL 或运动。YOLO 更新备份并重启自身的相机/UI 服务，Xorg、DFX manager 和保护文件保持一致。当前相机使用固定模型及实时匹配指纹的 DPU YOLOX-Nano，并复用 A 的 IoU 基线；ByteTrack、身份和统一视觉主服务仍需单独接入。

## 文件与已安装路径

源码快照：[scripts/board_ui_startup](../scripts/board_ui_startup/README.md)。

| 文件 | 用途 |
| --- | --- |
| `launcher.py` | 等待显示、映射触摸、单实例和子进程监督 |
| `config.json` | 当前目标板的路径、内核、EDID 与源 SHA 固定值 |
| `aura-avatar-ui.service.in` | 服务模板 |
| `aura-avatar-ui.service` | 本次实际安装的服务内容 |
| `release_manifest.json` | 三个板端载荷的大小、SHA 与安装位置 |
| `test_launcher.py` | 活跃监听端口与 TIME_WAIT 两项真实本机回归 |
| `test_display_fallback.py` | 五项主机模拟测试，验证显示回退保护条件 |

当前启动版本 `40f5d358d1c0d7ba`，板端脚本与配置路径为 `/home/root/aura-ui-startup-20261009/releases/40f5d358d1c0d7ba/`；服务位于 `/etc/systemd/system/aura-avatar-ui.service`，通过 `graphical.target.wants/` 开机启用。原素材与用户设置继续使用。

每次启动在原运行目录的 `managed-runs/<boot-id>-<monotonic-ns>/` 写独立日志与证据；`launch.json` 指向当前界面/监督进程，`stage.log` 为当前日志链接。停止和重启不会复用此前的证据目录，也不会覆盖原截图/报告。

当前配套包：[aura-yolo-update-0da0dc7f7289d5b7.zip](../artifacts/releases/aura-yolo-update-0da0dc7f7289d5b7.zip)，128039 字节，SHA256 `14417489c66bd8aa1a66c819b4ee6e8eff3bc14c14691f0e97df5167d85a21b1`。32 个载荷包含 26 个运行文件、启动器及部署辅助程序；依赖已有素材、触摸模块、Vitis AI 库、A 的关联源码及 [固定板上模型](BOARD_YOLO.md)。旧 `aae0d9db5911b5e5` 包作为更新前基线保留，不能直接覆盖当前固定 SHA 的启动器。

## 板端操作

```bash
systemctl status aura-avatar-ui.service --no-pager
journalctl -u aura-avatar-ui.service -n 30 --no-pager
systemctl restart aura-avatar-ui.service
```

重启上项仅影响汐蓝界面和其音频子进程。要改 GUI 源码、内核、屏幕或安装路径，先取得新的实际参数并更新配置/版本；固定 SHA 或版本不匹配会停止启动并记录具体错误。

恢复手动入口时，先执行 `systemctl disable --now aura-avatar-ui.service`；然后用原 `tools/board_avatar_gtk.py` 手动启动。原运行目录、素材、设置和历史证据均保留；不要同时开两个使用 8783 端口的入口。

## 验证与限制

本次 YOLO 更新：126 项主机、68 项板端软件测试、固定参考图/空白图、实时相机/DPU增长和放大/返回通过；最终真实入镜检出 1 人，同源图与实际快照核对通过。两个服务均 active/running/enabled、NRestarts=0；音量保持 18%。没有重新做整板启动或手指触控验收。以下为 YOLO 接入之前的预览/启动记录。

2026-10-11：当前 UI 的 60 项板端软件测试、真实相机和缓存音频、放大/返回、五次诊断及五页原生指针操作已通过。原生视频两次短测约 12.6～15.9 fps、入口帧龄中位数 76～98ms；主机五项 EDID 回退模拟和异步诊断停止等待检查通过。真实缺 EDID 故障曾发生，但部署时 EDID 已恢复，因此当前实际启动走 `live_edid`，不能声称真实回退路径已板测。以下为原启动基线记录。

已完成板端实际加载、READY、快速重启、单个 GUI/音频 worker、设置恢复、显示/触屏枚举、保护文件/进程与 32 份响应完整性检查；本轮最终音量 18%、非静音、全屏、普通动画。[重启后实际设置页](/home/ghmd/aura-waveshare-touch-20261009/evidence/20261010T051738.175561Z-window/board-window.jpg) 已回读查看。原错误探针将关闭后的 TIME_WAIT 当成端口占用，已修正；两个真实套接字回归测试和目标板快速重启通过。

详见 [实测日志](/home/ghmd/AMD_Smart/logs/daily/2026-10-09-BOARD-UI-AUTOSTART.md)、[核验](/home/ghmd/aura-board-ui-autostart-20261009/startup_validation.json)。前次真实手指滑块/页签操作证据保留于 [设置说明](BOARD_UI_SETTINGS.md)；本轮重启后复查了设备和 API，未重新完整测试手指按钮/边缘/多指。整板开机、断电冷启动、运行中崩溃恢复、动画流畅度及视觉并行仍不能据此宣称通过。

依据：目标板 systemd 249.7 的实际加载结果，以及 [systemd v249 服务类型/重启说明](https://github.com/systemd/systemd/blob/v249/man/systemd.service.xml)、[停止进程说明](https://github.com/systemd/systemd/blob/v249/man/systemd.kill.xml)。
