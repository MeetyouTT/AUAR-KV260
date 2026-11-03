# KV260 真人跟踪与目标选择验收

2026-10-11 本地日期，最终证据 UTC 2026-10-12。已验证真实相机人体框、原生界面点选、有效服务回执和短窗口选中保持；随后观察到旧目标消失、新轨迹出现时选择保持为空。近距离仰拍和移动仍有明显失跟，多人交叉、受控遮挡及长期稳定性没有验收。

开始时按 ZIP README、视觉手册、最新实施方案和项目日志检查。前轮“天花板、无人、未执行选择分支”属于首次接入状态，本次有实际真人画面。

- [真人框图](evidence/20261012T034838.549624Z-target/real-track.jpg)：实际 `#34`、分数 0.70。旧助手虽然报告 PASS，但没有新的选择回执，不能作为手动选择通过证据；[独立核验](evidence/20261012T034838.549624Z-target/validation.json)明确标记未验证。
- [真实选人弹窗](evidence/20261012T035903.740754Z-choice/target-chooser.jpg)：实际 1024×600 界面，弹窗 502×387，显示 `人体 #82`。分步检查时目标或界面变化，未产生有效选择回执。
- [连续点选记录](evidence/20261012T040519.523918Z-live/live.json)：GTK/XTest 点选当前 `#97`，代次 2，相机 epoch `7134c8a136ab47aeb50e9b0205061105`；服务回执 `accepted=true`，command_id `f02dc649ed4f4f3887507815f38db0e4`。40/40 个新鲜采样保持同一选中键，源时间跨度 6029ms、检测计数增加 60。[对应相机图](evidence/20261012T040519.523918Z-live/after-selection.jpg)已查看。
- [后续只读观测](evidence/20261012T042358.939612Z-watch/watch.json)：45.118 秒、193 样本，133 次有当前轨迹、60 次无轨迹，全部 `selected=null`；新轨迹包含 #202～#209，未继承旧手动选择。[最终相机图](evidence/20261012T042358.939612Z-watch/after-return.jpg)为房间内景，无人体。
- [最终界面](evidence/20261012T055810.942138Z-screen/current-screen.jpg)：960×550 放大画面仍可见，实际黄色框 `#281`、0.76，当前选择为空；同一界面客户端保留原有效回执，连接 READY、画面可见，无界面错误，音量58%等设置一致。

旧目标在只读窗口第一个采样之前已经消失。因此实际证据是“已选中 → 后续旧键失效且新可见键不自动选中”，没有连续捕获用户按指令离开、返回的完整物理过程，也没有身份识别证据。近距离仰拍窗口产生多个新编号，不能宣称持续稳定跟踪或多人 MOT 精度通过。下一项先固定摄像头、让上半身完整入镜，再做受控出入画、遮挡和双人交叉测试；暂不根据这段不规范视角调低阈值。

45 秒窗口实际采集生产率 21.54Hz、JPEG 预览生产率 21.41fps、检测 9.91Hz，按计数增量/窗口时长计算。这里的预览生产率不是物理屏幕显示帧率或面板端到端延迟。最终打开大画面的原生入口指标快照 `update_hz=12.29`，与JPEG生产率不同，本轮没有重新进行放大前后性能对照。相机、检测和预览错误均为空，NPU READY。

本次跨授权等待发现外部启动变化：boot 从前轮 `9223af18-5113-4486-822f-29ec94d03d3e` 变成 `0e0c24cf-0a5b-4212-91af-a50e6c008aa5`。最终相机 PID 988、service epoch `10e586f2b5134d0da8733b4a5b782790` 在点选及后续观测中保持一致。只能确认新启动下服务可用，没有观察关机、上电过程，不能替代冷启动验收。设置保持音量 58%、非静音、全屏、非省电。

本轮只修改验收助手和状态资料，暂存辅助脚本于独立 `live-acceptance-*` 目录；业务运行代码、模型和 FPGA 配置没有通过本轮命令更改。当前 GUI 已打开放大实时画面。未重新运行前轮 131 主机/80 板端软件测试；已有 7 项语音 API 回归错误仍见 [首次接入报告](TRACKING_REPORT.md)。

修复了验收过程的三项问题：单条串口脚本过长改为分段传输并在打开串口前检查长度；过滤无标题的 GTK 提示气泡，避免误判为弹窗；通过新的受理回执及实际选中键核验选择，不再以自动选择或关闭弹窗作为通过依据。前期失败原始记录保留。

[独立核验](continuation_validation.json)通过：35 份 UART 响应逐一从原始串口帧解码，长度/SHA 与保存内容一致；9 个相机/界面工件解码及 SHA 一致；上传辅助脚本 SHA 已核对；真实回执、40 个选中样本和 193 个后续样本交叉核对；最终放大界面、连接、回执及设置核对通过。[文档核验](continuation_document_validation.json)记录9份助手源码语法和本地链接检查。记录包括两次界面状态断言失败；另一次串口长度预检失败没有发送任务命令。对应核验脚本本身的解析错误已修正，不能把这些助手错误解释为相机故障。

本轮改动文件：

- [manage_tracking.py](manage_tracking.py)：增加现场验收阶段、分段传输、发送前编译/长度检查。
- [board_target.py](board_target.py)、[board_choice.py](board_choice.py)、[board_select.py](board_select.py)、[board_screen.py](board_screen.py)：真实画面、弹窗、状态和分步检查助手。
- [board_live.py](board_live.py)、[board_watch.py](board_watch.py)：本次连续点选、失跟后绑定观测。包含本次实例的 epoch/键/几何信息，是记录本次操作的脚本；换启动或目标后应重新读取状态，不能直接沿用。
- [verify_target_evidence.py](verify_target_evidence.py)、[verify_acceptance_continuation.py](verify_acceptance_continuation.py)：独立响应、图像、回执和生命周期核验。
- [跟踪操作说明](/home/ghmd/Win共享文件/共享文件夹/aura/docs/BOARD_TRACKING.md)、[框架状态](/home/ghmd/Win共享文件/共享文件夹/aura/docs/FRAMEWORK_STATUS.md)、[仓库入口](/home/ghmd/Win共享文件/共享文件夹/aura/README.md)。
- 本报告、[首次接入报告](TRACKING_REPORT.md)的后续链接、[资料导航](/home/ghmd/AMD_Smart/PROJECT_BOOK_INDEX.md)、[当日日志](/home/ghmd/AMD_Smart/logs/daily/2026-10-11-BOARD-TRACKING-ACCEPTANCE.md)及首次接入日志的后续链接。
