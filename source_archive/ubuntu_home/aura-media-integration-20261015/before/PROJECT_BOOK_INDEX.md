# AURA / KV260 竞赛项目资料包导航

2026-10-11 真人跟踪现场验收（证据 UTC 10 月 12 日）：真实原生界面点选 #97/代次2、新的服务受理回执与40/40短时保持通过；随后45秒193样本中旧绑定已失效，新可见轨迹未自动接替。35份UART响应及9个图像工件独立核验通过，最终放大界面/连接/设置核对通过。近距离仰拍仍有失跟，物理出入画全过程、受控遮挡、多人精度和长稳未验。音量58%保持，发现外部新boot后服务可用，但未观察冷启动过程。详见[最新日志](logs/daily/2026-10-11-BOARD-TRACKING-ACCEPTANCE.md)、[现场报告](/home/ghmd/aura-board-tracking-20261011/REAL_TRACKING_ACCEPTANCE_REPORT.md)、[核验](/home/ghmd/aura-board-tracking-20261011/continuation_validation.json)。下段为首次接入记录。

2026-10-11 最新跟踪：[ByteTrack 作者版本 NumPy 适配](/home/ghmd/Win共享文件/共享文件夹/aura/docs/BOARD_TRACKING.md) 已在真实 YOLO 相机服务上板，含代次/失跟与单人、手动目标策略。12 新增跟踪测试、131 主机相关测试、80 板端软件测试通过，短测预览 19.46fps、检测 9.91Hz，原生放大/返回和设置保留通过。真人选人/多人精度未验；全量回归另有 7 项旧语音接口错误。实际运行 `33fd4bc855871500`、启动器 `abd3df01b6d50a3b`，验收助手修正版包 `ea926df36eb116cd` 与37运行文件一致；68响应回读通过且保留已解决助手失败，音量58%。详见 [当天日志](logs/daily/2026-10-11-BOARD-BYTETRACK.md)、[报告](/home/ghmd/aura-board-tracking-20261011/TRACKING_REPORT.md)、[核验](/home/ghmd/aura-board-tracking-20261011/validation_final.json)。下方尚未接跟踪为此前状态。

2026-10-11 最新 YOLO：[YOLOX-Nano 人体检测](/home/ghmd/Win共享文件/共享文件夹/aura/docs/BOARD_YOLO.md) 已接入 KV260 B4096 DPU、真实相机和 GTK 界面；真人入镜检出 1 人，同源图与实际快照核对通过。126 项主机、68 项板端软件测试通过，同轮预览约 12.34→12.66fps、检测约 9.98Hz，无空画面；20 秒真实人员观测 154 个新鲜样本无相机/检测/预览错误，检测调用中位 10.66ms。96 份响应完整性、32 包载荷、26 运行文件与启动源码 SHA 核验通过，其中保留 1 份已解决的链接失败。当前更新 `0da0dc7f7289d5b7`、启动器 `40f5d358d1c0d7ba`，音量仍 18%。多人精度、ByteTrack/身份、统一主服务、冷启动和整机待验收；旧素材包未重建。详见 [当天日志](logs/daily/2026-10-11-BOARD-YOLO.md)、[报告](/home/ghmd/aura-board-yolo-20261011/YOLO_INTEGRATION_REPORT.md)、[核验](/home/ghmd/aura-board-yolo-20261011/validation_final.json)。下方同日 CPU 相机与待接项目 DPU 描述属于接入前记录。

2026-10-11 最新触屏与相机：[五页 UI 及接口](/home/ghmd/Win共享文件/共享文件夹/aura/docs/BOARD_TOUCH_UI_DESIGN.md)、[真实相机说明](/home/ghmd/Win共享文件/共享文件夹/aura/docs/BOARD_CAMERA_UI.md) 已上板。独立视频、人物渲染和后台诊断修复主要卡顿，两次短测预览约 12.6～15.9fps，API 帧龄中位数 450→210.5～235ms；不是物理面板端到端延迟。118 项主机框架、2 项诊断及 60 项板端软件测试、原生五页/放大/缓存音频操作通过；375 份响应回读通过。最终配套包 aae0d9db5911b5e5、启动器 5c0364f24f0b6b16，保留音量 18%。最新冷启动、实物全部新页触控、真实语音模型、身份/项目 DPU 与整机仍待验收；EDID 缺失曾发生，当前走 live_edid，实际回退未板测。详见 [当天日志](logs/daily/2026-10-11-BOARD-UI-CAMERA.md)、[报告](/home/ghmd/aura-board-ui-design-20261009/UI_DESIGN_REPORT.md)、[核验](/home/ghmd/aura-board-ui-design-20261009/validation_final.json)。下方 10 月 9 日的两页及待接相机描述保留历史。

2026-10-10 构建复现要求核查：[脚本实施清单与 42 工作包映射](/home/ghmd/Win共享文件/共享文件夹/aura/docs/reproducible_build_plan.md)、[当天记录](logs/daily/2026-10-10-REPRODUCIBLE-BUILD-REVIEW.md)。官方允许其他工具版本在报告说明并保证复现；本机实测 Vivado/v++ 2022.2，新工具版本检查入口通过。旧硬件脚本仍依赖本机路径/cache/增量参考，完整构建、真实项目模型和整机复现未完成；本轮没有板测或固件变更。

2026-10-09 最新启动闭环（UTC 2026-10-10）：独立 `aura-avatar-ui.service` 已启用，等待显示后恢复 1024×600、微雪触屏映射和保存设置；修正版实际启动及一次立即服务重启通过，音量仍为 18%，无重复 GUI/音频 worker。32 份响应完整性、两个端口回归和三个发布载荷回读通过，显示/DFX 进程及保护配置未变。**整板正常重启与断电冷启动尚未验收**，已询问用户是否可正常重启；手指边缘/多指、流畅度及视觉并行继续单列。详见 [启动实测日志](logs/daily/2026-10-09-BOARD-UI-AUTOSTART.md)、[操作说明](/home/ghmd/Win共享文件/共享文件夹/aura/docs/BOARD_UI_STARTUP.md)、[核验](/home/ghmd/aura-board-ui-autostart-20261009/startup_validation.json)。下方“GUI 自启/分辨率未配置”属于此前历史状态；当前改由开机服务恢复显示参数。

2026-10-09 最新触屏实测（UTC 2026-10-10）：接线后已识别微雪 `WaveShare WS170120 / 0eef:0005`，重新加载匹配模块并自动绑定 `hid-multitouch`。外部重启后已恢复 1024×600 与 GTK 界面；**真实手指拖动音量、互动/设置页签切换通过**，25 秒记录 3348 个实际输入事件，最终音量与保存值为 18%。模块已安装并配置开机加载，八份关键响应回读核验通过；新配置重启验收、GUI 自启、边缘精度/多指与流畅度仍待完成。本次未发现视觉进程，不能延用重启前 PID 的并行结论。详见 [最新实测日志](logs/daily/2026-10-09-WAVESHARE-TOUCH-CONNECTED.md)、[核验](/home/ghmd/aura-waveshare-touch-20261009/touch_connection_validation.json)、[截图](/home/ghmd/aura-waveshare-touch-20261009/evidence/20261010T005024.206584Z-window/board-window.jpg)。下方未枚举、未固化与音量 100% 为此前历史状态。

2026-10-09 微雪电容触屏排查：实测内核未启用 HID_MULTITOUCH，已用匹配源码/配置/GCC 单独构建 34944 字节驱动，在当前会话正常加载并注册；模块回读、版本、实际加载和 UI/视觉并行复查通过。**USB 仍未枚举触摸控制器，型号/接线与实物触摸待确认**，没有固化自启或修改启动镜像。最新只读 UI 为互动页、音量 64%，本轮没有改音量。四 USB 口均占用，可拔已卸载 U 盘腾口接屏幕 TOUCH 数据线。详见 [驱动处理日志](logs/daily/2026-10-09-WAVESHARE-TOUCH-DRIVER.md)、[核验](/home/ghmd/aura-waveshare-touch-20261009/validation_final.json)。

2026-10-09 最新图形操作界面已上板：现有汐蓝 UI 增加“互动 / 设置”两页，支持缓存播放、暂停/继续、打断、音量滑块/加减、静音、全屏、省电动画、恢复默认与设置保存。当前板端设置页可见，MCP01 音量 100%、非静音；70 项主机测试、12 项板端设置测试、真实窗口 XTest 按钮/滑块及播放控制检查通过。**未检测到触摸硬件，手指触控尚未验证**；动画与原视觉并行仍偏慢。A 的视觉 PID 16981 继续运行。详见 [设置界面日志](logs/daily/2026-10-09-BOARD-UI-SETTINGS.md)、[操作说明](/home/ghmd/Win共享文件/共享文件夹/aura/docs/BOARD_UI_SETTINGS.md)、[最终截图](/home/ghmd/aura-board-avatar-gtk-20261009/evidence/20261009T133208.806715Z-usb-runtime-fetch-window/board-window.jpg)、[独立核验](/home/ghmd/aura-board-avatar-touch-20261009/validation_final.json)。

2026-10-09 完整运行包已从 U 盘部署至 KV260 独立目录，871 载荷回读、573 PNG/4 WAV/42 眨眼层预检通过；旧 Pillow 兼容与视觉窗口遮挡已处理，MCP01 真实缓存播放、EOS、暂停/继续、打断通过。用户反馈声音可听并要求最大，音量已从 29% 调为 100%，麦克风不变；U 盘已在板端安全卸载，运行不依赖 U 盘。详见 [实际部署日志](logs/daily/2026-10-09-BOARD-AVATAR-USB-DEPLOY.md)。下方“待移插/待部署”等文字是此前历史状态，由这两条新实测更新。

2026-10-09 U 盘拷贝完成：Ubuntu 已识别用户的 64 GB U 盘；四个准备文件写入新目录 `AURA_AVATAR_20261009_1a8677ce`，217023529 字节运行包及三辅助文件全部 fsync/大小/SHA 回读通过，并成功安全卸载 `/dev/sda1`。现在待用户将 U 盘移插 KV260，完整播放器尚未上板或启动。沙箱内 ro 是环境可见限制，主机实际 rw；没有修复/格式化 U 盘。详见 [拷贝日志](logs/daily/2026-10-09-BOARD-AVATAR-USB-COPY.md)、[核验](/home/ghmd/aura-board-avatar-gtk-20261009/usb_copy_validation.json)、[拷贝脚本](/home/ghmd/aura-board-avatar-gtk-20261009/copy_usb_bundle.py)。

2026-10-09 完整运行包拷贝准备：主机侧未见 U 盘/有线网卡；已准备 [可直接拷贝的目录](/home/ghmd/aura-board-avatar-gtk-20261009/USB_READY_AURA_AVATAR)，内含原完整 ZIP、SHA256SUMS、包核验和 U 盘部署步骤。217023529 字节包重新读回 SHA 与原记录一致，未改程序或包字节。优先建议先插 U 盘到 Ubuntu；用户实际传输方式仍待回复，尚未拷入外部存储或部署完整播放器。详见 [准备日志](logs/daily/2026-10-09-BOARD-AVATAR-USB-HANDOFF.md)、[拷贝准备核验](/home/ghmd/aura-board-avatar-gtk-20261009/usb_handoff_validation.json)。

2026-10-09 UTC 11:40 部署连接复查：板卡串口、1024×600 显示会话、MCP01 和既有视觉进程仍在；eth0 管理层已启用但 **NO-CARRIER / Link detected: no**，没有板端 IP；未见 USB 磁盘，独立目录仍只有原生测试小包，玩偶程序未运行。5 份新 UART 响应完整性核验通过；[复查日志](logs/daily/2026-10-09-BOARD-AVATAR-CONNECTION-RECHECK.md)、[证据核验](/home/ghmd/aura-board-avatar-gtk-20261009/connection_recheck_20261009T1140.json)。网线用于当前大包传输及后续 Windows 模型服务局域网通信；缓存版部署后可离线运行，也可用 U 盘传包，不要求互联网。本轮只读复查，无部署或配置修改。

2026-10-09 最新汐蓝 GTK/GStreamer 适配：[板端入口与部署步骤](/home/ghmd/Win共享文件/共享文件夹/aura/docs/BOARD_AVATAR_GTK.md)、[本轮交付报告](/home/ghmd/aura-board-avatar-gtk-20261009/IMPLEMENTATION_REPORT.md)。已复用原素材/声线和 FSM，完成旧 Pillow、中文字体、独立音频进程、MCP01 格式转换及暂停/取消。58 项软件测试、573 帧/4 WAV/42 眨眼层通过；小包实际上板，GTK 显示连接/Pillow 兼容、GStreamer 1.18.5 **不发声**原生管线及 10 生命周期测试通过，31 UART 响应完整性通过。完整玩偶子系统包 871 载荷/约207 MiB 已回读核验；尚未部署完整素材或验收真实窗口/MCP01声音/口型/与视觉并行性能。当前无可用板端网络地址，接线询问待回复。详见 [适配日志](logs/daily/2026-10-09-BOARD-AVATAR-GTK-ADAPTER.md) 和 [板端原生记录](/home/ghmd/aura-board-avatar-gtk-20261009/board_native_validation.json)。下方环境检查的 NOT_READY 指原 Qt 入口，当前采用新 GTK3 适配。

2026-10-09 最新汐蓝板端实测：[环境报告](/home/ghmd/aura-board-avatar-baseline-20261009/BOARD_ENVIRONMENT_REPORT.md)。主机侧发现 Xilinx 串口并成功连接 KV260；此前沙箱设备列表不能代表主机连接状态。板端 PetaLinux 2022.2 / Python 3.9.9，显示 1024×600，MCP01 已识别；当前 Qt 入口缺 PySide6，旧 Pillow 也需兼容，**NOT_READY**。GTK3/GdkPixbuf 与 GStreamer 插件已核对，可作为适配候选；缓存 24 kHz 单声道须适配 MCP01 48 kHz 双声道，另需字体与部署资源。视觉进程仍在运行，没有操作 FPGA/舵机或播放。9 份 UART 响应完整性回读通过，详见 [最新日志](logs/daily/2026-10-09-BOARD-AVATAR-ENVIRONMENT-CHECK.md) 和 [核验](/home/ghmd/aura-board-avatar-baseline-20261009/board_environment_verification.json)。真实播放与并行性能尚未验收。

2026-10-09 此前汐蓝板端缓存基线准备：[入口与执行说明](/home/ghmd/Win共享文件/共享文件夹/aura/docs/BOARD_AVATAR_BASELINE.md)。显式缓存模式关闭新语音生成/对话并独立记录日志；音频包按需加载，保留原 36 个公开名称。48 项标准库测试、16 套/573 帧、4 段演示音频及 42 张眨眼层核验通过。准备时 Ubuntu 缺 NumPy/PySide6，沙箱内未检测板卡串口且 IP 未知；该连接局限和当前板端状态由上方新实测更新。尚未执行板端播放或并行性能验收。详见 [准备日志](logs/daily/2026-10-09-BOARD-AVATAR-BASELINE-PREP.md) 与 [软件验证](/home/ghmd/aura-board-avatar-baseline-20261009/unittest_validation.json)。

2026-10-09 用户更新当前安排：**A 负责视觉与 FPGA，玩偶界面部署在 KV260 PS/Linux**。后续分工以 [当前分工与玩偶板端部署](/home/ghmd/Win共享文件/共享文件夹/aura/docs/CURRENT_ASSIGNMENT_AND_BOARD_UI.md) 为准；原总包/图册人员标签与工作包编号保留来源追溯，不代表最新个人指派。首版模型在 Windows，板端负责真实播放与显示。代码核对发现 PC 演示入口耦合本机语音合成，需分开播放器与主机模型适配；没有执行板测。详见 [澄清日志](logs/daily/2026-10-09-ASSIGNMENT-AND-BOARD-UI.md)。

2026-10-09 结构细化与依据复核入口：[目录细分页面](/home/ghmd/Win共享文件/共享文件夹/aura/report/architecture/structure_detail.html)、[完整说明](/home/ghmd/Win共享文件/共享文件夹/aura/report/architecture/structure_detail.md)、[提交目录](/home/ghmd/Win共享文件/共享文件夹/aura/submission/aura_junior/README.md)。保留七类交付与 M1–M8，细化 59 项目录职责、共享层、运行位置、10 类资源所有者和原 I01–I07；171 份 Python 源码及 420 条本地静态导入核对通过。修正 PS 客户端/Windows TTS/运行时模拟后端/DPU 集成的归属，并明确实际包导入和资源路径迁移门槛。新框架包 309 个载荷核验通过；源码未搬迁，静态核验不代替运行或板测。详见 [本轮日志](logs/daily/2026-10-09-PROJECT-STRUCTURE-REVIEW.md) 与 [独立核验](/home/ghmd/aura-structure-review-20261009/validation_final.json)。下方同日框图搭建记录为细化前初版，保留作追溯。

2026-10-09 完整参赛框图与提交框架入口：[八张框图及状态页](/home/ghmd/Win共享文件/共享文件夹/aura/report/architecture/index.html)、[八页 PDF](/home/ghmd/Win共享文件/共享文件夹/aura/report/architecture/framework_diagrams.pdf)、[七类提交目录](/home/ghmd/Win共享文件/共享文件夹/aura/submission/aura_junior/README.md)。按初级组自主选题整个作品建立 M1–M8、64 个模块，包含未实现部分，挂接 42 工作包、T01–T30 和 r01–r17；源码与既有实测分六种证据层级。图册、来源、原文矩阵、目录、203 个本地链接与 255 个框架包载荷核验通过。该成果是完整设计/提交框架，不代表最终模型、媒体、PL 或整机完成。详见 [搭建日志](logs/daily/2026-10-09-JUNIOR-ARCHITECTURE-FRAMEWORK.md) 与 [独立核验](/home/ghmd/aura-submission-framework-20261009/validation_final.json)。

2026-10-09 项目统一框架已落地于 [aura 主仓](/home/ghmd/Win共享文件/共享文件夹/aura/README.md)，入口和 A/B/C 接入顺序见 [项目框架说明](/home/ghmd/Win共享文件/共享文件夹/aura/docs/PROJECT_FRAMEWORK.md)，软件验证/限制见 [框架状态](/home/ghmd/Win共享文件/共享文件夹/aura/docs/FRAMEWORK_STATUS.md)。新增 41 项框架测试通过，固定/可变模拟场景和媒体 fixture 管线通过，121 文件源包完整性与迁移启动检查通过；这些是 PC 软件证据。真实项目 DPU、ByteTrack 板测、MCP01/媒体模型、PL 绝对源期限及机构仍待接入/验证。工作与实际工件见 [搭建日志](logs/daily/2026-10-09-PROJECT-FRAMEWORK-BUILD.md)。默认启动不连接硬件，机构继续等待 3D 模型。

2026-10-08 最新整体计划入口：[AURA·汐蓝初级组项目框架](/home/ghmd/Win共享文件/方案/aura_junior_project_framework_20261008.md)。配套方法见 [10 月 7 日单一创新方向](/home/ghmd/Win共享文件/output/aura_single_innovation_direction_20261007.md)，技能交付见 [10 月 7 日技能包方案](/home/ghmd/Win共享文件/方案/aura_skill_package_plan_and_delivery_20261007.md)。ZIP 仍先读作为基础资料；研究主线和关卡需结合这三份更新。它们是计划，实际进度以 Ubuntu/板端最新可核验证据为准。用户目前明确机构等待 3D 模型，模型/跟踪/时效记录与数字验证继续推进。对齐记录见 [最新计划复核](logs/daily/2026-10-08-LATEST-PLAN-ALIGNMENT.md)。

2026-10-08 论文入口：[论文方法与项目实现对照](/home/ghmd/aura-shared-review-20261008/PAPER_PROJECT_MAPPING.md)，包括研究主线四类文献、跟踪/身份/说话人方法、六项硬件优化候选及待做实验。共享原件为 [第一份核查](/home/ghmd/Win共享文件/output/AURA_论文方法_GitHub_FPGA实现核查_2026-10-04.md)、[第二份核查](/home/ghmd/Win共享文件/output/AURA_第二份论文报告_GitHub_FPGA实现核查_2026-10-04.md)、[实施建议](/home/ghmd/Win共享文件/output/AURA_论文方法加入项目的实施建议_2026-10-04.md)。近期原始调研附件尚未在当前可访问共享文件中定位到；同名 `Docs/deep-research-report (1).md` 是历史方案。阅读范围和实际检查见 [论文对齐日志](logs/daily/2026-10-08-PAPER-PROJECT-ALIGNMENT.md)。

2026-10-04 最新显示检查：[HDMI 接入日志](logs/daily/2026-10-04-HDMI-DISPLAY-CHECK.md)。读取屏幕 EDID 后，将本次 X 会话从 1024×768 回退模式/自动休眠调整为 1024×600、约 59.85 Hz、On。Xorg、DRM 和实际设备 modetest 确认输出 enabled/active、链路 Good；64 项证据检查通过。用户随后提供实屏照片，确认 Linux Applications 桌面页面已显示，基础 HDMI 静态桌面显示通过；闪烁、精确裁剪和输入操作未验证。没有持久化显示设置，600 秒息屏保留，显示时钟 -13 未修复。详见 [完整报告](/home/ghmd/kv260-hdmi-display-check-20261004/DISPLAY_CHECK_REPORT.md)。

完整资料包：`/home/ghmd/下载/项目.zip`（435 个条目，压缩包约 42.5 MB，解压内容约 92 MB）。资料包覆盖 AMD FPGA 赛题、AURA 方案、A/B/C 分工、FPGA 框架、板端基线、源码和历史工作记录。开工时先看 ZIP 内 `项目/README.md`，再按本页定位任务资料。

## 项目总体与当前方案

- `项目/README.md`：资料包入口，指出当前执行手册和被保留作追溯的旧方案。
- `项目/方案/AURA_KV260_完整实施方案_无声源定位版_2026-09-30.md`：当前产品范围和完整实施方案；当前范围采用 MCP01 USB 音频、视觉说话人判断、单轴运动，不含双 I2S 麦克风声源定位。
- `项目/方案/AURA_当前现状三人分工_2026-10-02.md`：基于当时进度的 A/B/C 起点、责任和交接。
- `项目/方案/AURA_三人执行总包_2026-10-02/00_总负责人_系统集成与交付总包.md`：集成、排期、风险和发布流程。
- 同目录的 `01_...`、`02_...`、`03_...`：A（FPGA/硬件）、B（视觉/身份/运动服务）、C（视听交互/主机模型/UI）的个人执行手册。
- `项目/方案/AURA_KV260_共同板端部署与联调速查表_2026-10-02.md`：现场部署与联调速查。

## 依任务查阅

- **赛题与交付要求：**官方指南 PDF 的第 3.3 节是“自主选题赛道”，包含初级组/高级组规则；AURA FPGA 框架按初级组编写。任务涉及报名或正式交付时，核对官方指南及后续发布的正式评分细则。再查 `项目/aura_fpga/docs/submission_matrix.csv` 和 `项目/方案/reference_round4_20260926/` 中的需求追溯资料。
- `项目/方案/amd_kv260_full_work_requirements_v3.md`：较早的完整需求汇总，适合作为追溯材料；其中历史双麦需求等与 2026-09-30 当前方案冲突时，以当前方案删除双麦后的范围为准。
- **FPGA/平台：**`项目/aura_fpga/readme.md`、`项目/aura_fpga/docs/fpga_framework.md`、`项目/aura_fpga/docs/first_steps.md`、`项目/aura_fpga/contracts/platform_manifest.json`。
- **硬件和外设：**`项目/方案/AURA_KV260_外设控制与采购规格_2026-09-26.md`、个人 A 执行手册和对应技术记录。
- **视觉与身份：**个人 B 执行手册、`项目/方案/aura_plan_b_vision_identity_30days.md`。
- **音频、问答与 UI：**个人 C 执行手册、`项目/方案/AURA_方案1_USB一体音频与视觉说话人定位_实施步骤_2026-09-29.md`。
- **平台镜像与工具：**`项目/方案/KV260_镜像问题综合判断与重建验收方案_2026-09-27.md`、`项目/方案/AURA_KV260_软件下载与实现可行性核对_2026-09-27.md`。

## 状态和冲突处理

资料包中的计划说明目标和当时判断，不自动证明已经完成。ZIP 更新到 2026-10-02 左右；当前工作区还有更新的 `logs/daily/` 和各任务目录报告。开始工作时查看最新记录和证据，涉及板卡、构建、推理或修复状态时以可核验实测为准。历史方案和 `项目/tmp/` 内容只用于追溯；遇到冲突时先看 `项目/README.md` 标出的当前入口，再核对日期与实测依据。

2026-10-04 最新运行时证据：见 [DFX 状态修复板测日志](logs/daily/2026-10-04-DFX-STATE-BOARD-VALIDATION.md) 和 [板端报告](/home/ghmd/kv260-dfx-state-boardtest-20261004/BOARD_REPAIR_REPORT.md)。新 manager 的实际板测、持久化和一次用户确认的断电冷启动通过；ZOCL 先加载，新 manager 与官方 B4096 自动启动，原图推理和原文件哈希一致。主机回读核验 5223 文件、23 次分类。NFS/TPM/overlay 等遗留告警仍存在；DPU 与自研运动 IP 共存及三人整机尚待验收。

同日后续 [遗留告警诊断](logs/daily/2026-10-04-PLATFORM-WARNING-DIAGNOSIS.md) 补充：NFS 已确认是未启用服务端内核功能却启用开机服务；TPM 首次未初始化提示已由内核恢复，本轮能力查询成功。overlay 属性生命周期和显示时钟权限仍需处理，当前 DP 接口 connected。见 [具体修复方案](/home/ghmd/kv260-platform-warnings-20261004/WARNING_REPAIR_PLAN.md)；本轮没有修改这些板端配置。

同日最新 [NFS 开机配置修复](logs/daily/2026-10-04-NFS-STARTUP-REPAIR.md)：用户授权后已停用 server/mountd 并新增当前内核的 nfsd 挂载条件。运行中复验后，用户确认断电启动，本次新 boot ID `20353da8-9e81-4b1b-9b15-cac06ac7923f`；NFS 开机自动跳过挂载且无原失败，失败单元为 0，ZOCL/manager/官方应用自动启动，原图推理、DPU、原 26 项哈希和客户端检查通过。新启动证据主机回读核验 194 文件、446 项检查。物理断电由用户确认，本轮没有从关机/上电起的 UART 观察。见 [实际修复报告](/home/ghmd/kv260-platform-warnings-20261004/NFS_REPAIR_REPORT.md) 和 [验收依据](/home/ghmd/kv260-platform-warnings-20261004/NFS_COLD_BOOT_VERIFICATION.json)。overlay/显示时钟问题仍待修复。

2026-10-04 后续 [FPGA 环境实际核验](logs/daily/2026-10-04-FPGA-ENVIRONMENT-REVIEW.md)：Vivado/v++/HLS 2022.2、K26/KV260 板卡支持、Clocking Wizard 输出产品、M3 当前综合与授权、XSCT 读取 XSA、PetaLinux 环境检查通过；原 11 项工件/11 项输入和四个设置脚本保持一致，独立回读 64 项通过。核心开发环境已就绪，完整 PWM/运动监督和最终平台仍需实现；下一项是运动 ABI 与实际输出/停止引脚/XDC。见 [核验报告](/home/ghmd/kv260-fpga-environment-review-20261004/FPGA_ENVIRONMENT_REPORT.md)。本轮未连接板卡或完整重建。

用以下命令查找和读取 ZIP 内原件：

```sh
unzip -Z1 /home/ghmd/下载/项目.zip
unzip -p /home/ghmd/下载/项目.zip '项目/README.md'
unzip -p /home/ghmd/下载/项目.zip '项目/方案/相对路径.md'
```
