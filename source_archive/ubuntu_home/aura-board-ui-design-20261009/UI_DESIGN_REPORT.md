# KV260 触屏、相机接入与卡顿修复实测

更新：2026-10-11。任务从 10 月 10 日持续完成；下列时间以证据目录的 UTC 时间为准。资料入口为 `/home/ghmd/下载/项目.zip` 的 `项目/README.md`、无声源定位完整实施方案、C04/C08 与 §6.7/§6.8、10 月 8 日框架和最新板端记录；现行分工仍为 A 负责视觉与 FPGA。

已部署五页触屏界面、真实相机预览及主要卡顿修复。当前预览两次短测约 **12.6～15.9 fps**，原界面约 **3.94 fps**。独立验收核对通过，当前保持互动页、全屏、非静音、音量 18%。这份结果覆盖 UI、CPU 相机预览和现有缓存播放；真实语音模型、项目 DPU/身份及机构没有因此完成。

## 实际测量

| 测量口径 | 原 JPEG/GTK 路径 | 修复版完整功能验收 | 最终启动器更新后复查 |
| --- | --- | --- | --- |
| 测量时长 / API 样本 | 7.84s / 35 | 11.29s / 120 | 10.32s / 120 |
| 视频入口计数 / 秒 | 原 GUI 发布约 3.94 | 15.88 | 12.59 |
| API 已发布画面帧龄中位数 / P95 | 450 / 600ms | 235 / 338ms | 210.5 / 305ms |
| 采集出队至原生视频入口帧龄中位数 / P95 | 原路径未设此测点 | 98.33 / 142.87ms | 76.39 / 114.94ms |
| 采样时画面不可用 | 见原记录 | 0 / 120 | 0 / 120 |

原路径的 GUI 发布计数代表该路径的画面更新；新路径使用视频入口计数，视频已不依赖 GUI 状态发布频率。同口径延迟比较使用 API 已发布帧龄，不能直接拿原 450ms 与新视频入口 76ms 计算加速比。时间戳从 appsink 出队开始，不包括相机曝光、USB/V4L2 内部缓冲和物理面板扫描；**未测量玻璃到玻璃端到端延迟**。不同场景、CPU 负载和启动会话的短测不能保证固定帧率，也没有证明已经达到原直接显示的延迟。

完整验收时实际采集约 18.87Hz、检测约 9.30Hz；640×480 YUY2 / 30fps 和检测 10Hz 是配置上限。CPU 占用按一个核心为 100% 计算，GUI 约 167.6%、相机约 152.9%；仍需长期并行预算，不能宣称低负载或恒定 30fps。

最后复查实际采集约 12.60Hz、显示入口约 12.59Hz、检测约 9.50Hz，视频入口计数已接近当时采集计数。采集率变化的具体原因未作隔离实验，不能仅凭这两次短测归因于曝光或 CPU。

原始依据：

- [原路径剖析](evidence/20261010T142957.476905Z-preview-profile/preview-profile.json)。
- [修复版完整功能验收](evidence/20261011T064917.508404Z-final-checks/result.json)、[性能](evidence/20261011T064917.508404Z-final-checks/8-preview-profile.json)。
- [最终启动器复查](evidence/20261011T082413.055693Z-post-startup/result.json)、[最新性能](evidence/20261011T082413.055693Z-post-startup/2-preview-profile.json)。
- [最终互动页](evidence/20261011T082413.055693Z-post-startup/screen.jpg)、[放大画面](evidence/20261011T064917.508404Z-final-checks/0-camera-test-screen.jpg)。截图属于真实相机画面，仅用于本地验收。

## 修复及源码

| 文件 | 本轮行为 |
| --- | --- |
| [board_avatar_gtk.py](/home/ghmd/Win共享文件/共享文件夹/aura/tools/board_avatar_gtk.py) | 互动/演示/设备/连接/设置五页，原人物几何不变；能力不足时禁用操作；诊断在单一后台任务保存 |
| [board_avatar_worker.py](/home/ghmd/Win共享文件/共享文件夹/aura/tools/board_avatar_worker.py) | 单一线程持有原控制器和音频时钟，后台合成/缩放/编码，只发布最新人物帧 |
| [ui_camera_service.py](/home/ghmd/Win共享文件/共享文件夹/aura/board/vision/ui_camera_service.py) | 唯一相机采集者；最新帧、预览和检测分别推进，预览不等推理 |
| [local_preview.py](/home/ghmd/Win共享文件/共享文件夹/aura/board/vision/local_preview.py) | 私有 RAM 最新 BGR 帧，绑定启动/服务/相机代次及绝对源时间，拒绝异常和过期数据 |
| [board_camera_preview.py](/home/ghmd/Win共享文件/共享文件夹/aura/tools/board_camera_preview.py) | 独立原生视频管线，有限缓冲、丢旧帧、过期推黑帧；重置后重新绑定指定窗口 XID |
| [ui_services.py](/home/ghmd/Win共享文件/共享文件夹/aura/board/interaction/ui_services.py) | 后台状态/命令、有界回执、取消与迟到丢弃；JPEG 状态和匹配画面原子提交，避免闪空 |
| [board_screen_capture.py](/home/ghmd/Win共享文件/共享文件夹/aura/tools/board_screen_capture.py) | 独立子进程读取真实 X11 屏幕，支持板上 RGB565，避免原 Cairo 截图崩溃 |
| [启动器](/home/ghmd/Win共享文件/共享文件夹/aura/scripts/board_ui_startup/launcher.py) | 固定 UI/组件 SHA；严格的本屏时序回退；正常退出有界等待后台诊断提交 |

原新增 JPEG 后台方案仍只有约 5.2fps，曾在 120 次采样中出现 26 次空状态；该结果保留为失败的中间方案。原生视频第一次短测达到 15.66fps，但后续截图发现管线重置丢失嵌入窗口，诊断也因主线程写盘超过 3s 而两次返回 503。最终版本修复这两项后，才通过真实嵌入窗口的放大/返回、重复诊断和完整页面验收。中间测量不冒充最终验收。

本机接口为 `aura-ui-1`；详细合同、时效、能力和交接见 [触屏设计](/home/ghmd/Win共享文件/共享文件夹/aura/docs/BOARD_TOUCH_UI_DESIGN.md) 与 [相机说明](/home/ghmd/Win共享文件/共享文件夹/aura/docs/BOARD_CAMERA_UI.md)。当前真实能力为 CPU YuNet 人脸检测、IoU 基础关联与目标选择；这不是人体计数、ByteTrack 或身份识别。框只来自小于 250ms 的有效观测，并非与每个预览帧同步推理。

## 验证与最终安装

已完成 118 项主机框架测试、2 项异步诊断测试、4 项真实 loopback HTTP 测试、5 项模拟 EDID 回退测试及异步退出等待检查。主机 GTK 五页几何和实际像素检查通过；合成视频在 GTK 暂停 400ms 时仍出帧，移位窗口/相机换代后仍正确嵌入，源冻结后清黑。这些主机结果与板测分开记录。

板上 60 项软件测试、573 PNG / 4 WAV / 42 眨眼层资源检查、相机源及模型预检通过。真实相机采集/检测增长、源时效、放大/返回、五次诊断无重启、五页原生指针操作及布局通过。缓存音频实际播放、暂停时音频时钟不前进、继续与取消回到 IDLE、期间视频持续刷新通过；操作回执为 88.19～140.73ms。指针测试不能替代完整手指和多指验收，实际发声也不代表已测声学延迟。

最后一次仅更新启动器，19 个运行载荷与完整功能验收时完全相同；更新后重新核对真实相机、互动页、性能、设置、运行源 SHA 与服务状态。最终当前 GUI PID `235915`，相机 PID `992` 为唯一 `/dev/video0` 采集者；两项服务 active/running/enabled 且 NRestarts=0。更新过程中相机、Xorg、DFX manager 及四项保护文件保持一致，没有整板重启、PL 重新加载或舵机动作。

发布状态：

- 运行代码更新：`49e441bea05c3d3f`；最新启动版本：`5c0364f24f0b6b16`。
- 最终配套包：[aura-board-ui-update-aae0d9db5911b5e5.zip](aura-board-ui-update-aae0d9db5911b5e5.zip)，77456 字节、27 载荷、19 运行文件，SHA256 `3f15335a41c7b24fd5f0aefb2207c72c00e21cc1d00f3cb2d22a76554d809691`。
- [清单](manifest.json)、[包回读](package_validation.json)、[独立核验](validation_final.json) 与 [核验脚本](verify_evidence.py)。375 份 UART 响应长度/SHA 回读通过；历史六次失败及三次负向 503 探针原样保留。
- 同包已复制到主仓 `artifacts/releases/`。现有完整素材包继续使用；没有重建原 217MB 包，也不声称旧包已包含本轮服务。源包收集入口已加入新依赖，当前收集清单核对见 [source_package_validation.json](source_package_validation.json)。

期间板卡出现新的启动会话 `9223af18-5113-4486-822f-29ec94d03d3e`，无法从现有证据确定触发者和具体上电方式。DP connected 但 EDID 曾为 0 字节，系统回退 1024×768，旧启动器反复等待；EDID 后来恢复。新增回退仅允许此前实测的 49MHz、1024/1072/1168/1312、600/603/613/624 时序，并要求相同微雪触屏和 connected；实际部署走 `live_edid`，**真实缺 EDID 回退未板测**。

## 尚未验证

物理屏幕端到端延迟、全部新页面手指/边缘/多指操作、最新版本冷启动、真实缺 EDID 回退、长时间并行性能尚未通过。本次没有实现或验收真实麦克风录音、ASR/VLM/TTS、身份、项目 DPU 模型、机械跟随。下一项先接 MCP01 录音/停止/本地回放，再按现有媒体合同接 Windows 模型；A 的统一视觉服务接管前交接相机唯一所有权与 8790 端口。
