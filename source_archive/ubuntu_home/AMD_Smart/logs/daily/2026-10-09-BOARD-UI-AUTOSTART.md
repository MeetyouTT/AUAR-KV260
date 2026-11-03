# 汐蓝界面开机服务与真实快速重启检查

日期：2026-10-09（America/Los_Angeles），主机 UTC 证据为 2026-10-10。用户“接下来怎么办”后，接续已完成的基础触控，补齐启动流程。按 ZIP README 及 C 执行手册 C12/16.4 的日常启动要求，针对已有 GTK 缓存入口实现；不把计划中的整机服务全部标记完成。

## 实际结果

- 新增并启用 `aura-avatar-ui.service`。板端 systemd 249.7 实际加载为 Type=notify、NotifyAccess=main、Restart=on-failure、KillMode=mixed，LoadError 为空。
- 脚本核验 GUI/模块 SHA、内核和屏幕 EDID，等待现有 X 显示、恢复 1024×600 / 59.85 Hz、映射微雪控制器，再启动原 GUI。等待真实 GTK API 就绪后报告 READY。
- 界面按原设置恢复为 **18%、非静音、全屏、普通动画**。原 GUI 源码、素材与缓存声线没有更改。
- 修正版实际启动通过，随后一次立即的 `systemctl restart` 通过。最终服务为 active/running、Result=success、NRestarts=0；监督进程 PID **26881**、GUI PID **26893**、唯一音频 worker PID **26927**。新旧运行证据目录不同，没有重复 GUI 或遗留音频 worker。
- 显示会话（xinit 1059 / Xorg 1142）和 DFX manager 1073 的 PID/start_ticks 保持一致；三个保护配置 SHA 未变。当前没有 `realtime_vision.py`，未启动/停止 A 的视觉、未重载 PL 或操作舵机。
- 本轮 boot ID 始终为 `0ecc7063-1b99-4bca-9e9c-d9f8026732f5`。**没有执行整板重启或冷启动验收**；已询问用户是否可正常重启，目前仍以未验收记录。

## 文件、版本与备份

服务：`/etc/systemd/system/aura-avatar-ui.service`；启用链接：`/etc/systemd/system/graphical.target.wants/aura-avatar-ui.service`。

当前启动版本：`/home/root/aura-ui-startup-20261009/releases/75cf50fce4bc4d86/`。

| 载荷 | 大小 | SHA256 |
| --- | ---: | --- |
| `launcher.py` | 10234 | `fd95022f93dab2dea1792b9969a1c436f97115b178f7e655a754c929ff252c5d` |
| `config.json` | 823 | `d8963fa695e32de5c6a7ec1b155a38791bc0af7c8d9dc647eb16595e574ef193` |
| `aura-avatar-ui.service` | 869 | `cb63edc9c50adbe93c9ee6f9ff572ff3ff8ed79238db8b0f72645d9f4ebcfed0` |

初始版本 `db8b47700c1d8a34/backup/` 保留安装前 `launch.json`、`stage.log`、用户设置、保护 SHA/PID 基线及最后手动 GUI 日志；修正版 `75cf50fce4bc4d86/backup/` 保留本轮旧服务和替换前状态。每次运行独立保存至原运行目录的 `managed-runs/<boot-id>-<monotonic-ns>/`，`launch.json` 和日志链接指向当前实例，历史运行目录保留。

工作目录：[aura-board-ui-autostart-20261009](/home/ghmd/aura-board-ui-autostart-20261009)。新增 `launcher.py`、`config.json`、服务模板/实际服务、`manage_startup.py`、两项回归 `test_launcher.py`、证据核验 `verify_startup.py`、版本/发布清单与核验 JSON。另在触屏工具中增加只读 `autostart-inspect`，未改原 GUI。

项目同步：`scripts/board_ui_startup/` 六个源/配置快照及 README、`docs/BOARD_UI_STARTUP.md`，并更新 README、设置说明、GTK 说明、当前安排、框架状态与 `PROJECT_BOOK_INDEX.md`。独立启动 ZIP 5092 字节，三个载荷回读通过，SHA256 `966ce0f89f0ca990d01893669e1cd868cfbd8be15e26d7907bd103db74989f9b`；它配套已有缓存安装，不包含素材或模块，也没有替换此前约 217 MB 的运行 ZIP。

## 验证

1. 正常监听端口必须拒绝、关闭 HTTP 式连接后的 TIME_WAIT 允许立即重启：两项真实 loopback 回归通过。沙箱内最初因禁止创建套接字报 PermissionError，随后授权的沙箱外运行通过，不能把前者当作实现失败。
2. 主机 systemd 245 语法检查返回 0，存在主机无关运行单元/Varlink 告警，未将其计作完整板级验证；板端通过 `systemctl show` 验证实际解析属性和空 LoadError，并完成真实服务 READY。
3. 目标板快速重启后 PID/证据目录改变，保存设置一致，界面/音响/触屏可用；单个 GUI 与其 worker，无原 worker 遗留，显示/DFX 进程和保护文件不变。
4. `python3 -B .../verify_startup.py`：**32 份响应**（29 份启动记录及三份重启后的设置页/报告/截图记录，包括保留的失败响应）的大小/SHA/JSON 核验及上述启动、重启检查通过。实际 GUI 源 SHA 与原版本一致，设置页截图已回读查看。详见 [核验](/home/ghmd/aura-board-ui-autostart-20261009/startup_validation.json)。新启动包 CRC、清单和三载荷 SHA 回读通过。

关键原件：

- 初始启动配置读取：`aura-waveshare-touch-20261009/evidence/20261010T005544.365367Z-autostart-inspect/`。
- 安装与启用：`evidence/20261010T012051.859711Z-install/`、`20261010T012122.619935Z-enable/`。
- 初始手动 GUI 交接：`20261010T012134.967676Z-activate/`。
- 首版失败及原因：`20261010T012232.738833Z-status/`，日志含 EADDRINUSE、NRestarts=5；端口释放后重试 `20261010T024145.996762Z-retry/`，随后旧版就绪记录保留。
- 修正版传输与替换：`20261010T050627.858719Z-stage/`、`20261010T050703.874195Z-replace/`。
- 修正版 READY：`20261010T050822.295325Z-status/`。
- 快速重启和最终状态：`20261010T050834.986465Z-restart/`、`20261010T050928.325158Z-status/`。
- 重启后设置报告与截图：`aura-waveshare-touch-20261009/evidence/20261010T051731.743946Z-report/`、`20261010T051738.175561Z-window/board-window.jpg`。

## 问题处理和边界

板端精简镜像没有 `systemd-analyze`，首次安装在写入系统服务前停止；改为主机语法检查与板端真实解析/启动核验。UART 外层封装长度在主机发送前检查，过长阶段拆分后通过，没有截断执行任务命令。

首次交接后，自写端口探针没有使用地址复用，将刚关闭连接的 TIME_WAIT 判为占用，服务因此五次重试后限流。原 GUI 的保存记录和设置保留。已在 loopback 重现旧探针问题，设置 SO_REUSEADDR 后同时验证“真实占用仍拒绝”和“已关闭端口可重启”；修正版随后在 KV260 的立即服务重启通过。失败证据未删除，也未将首版失败计为成功。

服务当前正常，下一步为获准后进行整板正常重启，核验开机自动显示、模块、触摸及设置恢复。前次手指滑块/页签已实测；本轮重启后的完整手指、边缘/多指、运行中崩溃恢复、动画流畅度、视觉并行和整机长测仍未完成。上述步骤完成后建议推进 MCP01 麦克风录音/停止/回放，再接 Windows 真实语音模型。

依据：[systemd v249 服务说明](https://github.com/systemd/systemd/blob/v249/man/systemd.service.xml)、[停止策略](https://github.com/systemd/systemd/blob/v249/man/systemd.kill.xml) 及目标板实际文件/进程/READY/响应证据。
