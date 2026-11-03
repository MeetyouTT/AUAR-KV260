# 当前交付接续（2026-10-27）

本轮Windows CPU画面部署已完成，正式目标16fps，实际UI断线回退8fps/恢复、静音真实PCM与口型、设置页布局均有证据。先读README、PROGRESS、final_verification和最新适用AGENTS。正式根 `/home/root/aura-windows-portrait-20261027/layout-4fca8de03dc84c989f84d7814a984bd3`；不得再从历史8fps入口直接覆盖。

1. 用户已授权停止跟随，本轮通过既有入口退出；最终保持跟随、监听、麦克风关闭。没有自动恢复运动。两分钟等待心跳automation已通过工具删除，不重复创建。
2. 先运行check_wait.py只读确认当前boot、入口、空闲、IDLE_READY、跟随/活动运动和监听状态，再核对当前源码/配置，保护之后的并行机械更新。持续跟随duration_s=0没有固定结束时间，SOURCE_HORIZON_ENDED不是整个跟随已退出。
3. 不要重跑deploy_ui.py/prepare_layout.py/step_fps.py来“补做”本轮。它们是历史验收脚本，门槛/入口均固定。16fps已经持久化，24fps因P95/P99未通过而未采用。
4. Windows只管理本任务持有的8796 CPU画面服务。start_portrait.ps1可独立启动，start_voice.ps1接原语音服务，-WithoutPortrait跳过；未设系统自启。不可终止其他模型；LLM数据继续D盘，无共享目录权重或入口。
5. rollback_ui.py默认只读检查；--apply为完整UI回退，仅移除本任务32z覆盖并核对旧源码/机械绑定、空闲、监听和跟随关闭。旧覆盖保留。不要用历史脉宽/PID覆盖当前现场状态，HDMI排查继续暂停。
6. 后续重点：用户在场听音/插话/选档、持续实聊帧间隔与延迟、声纹/声画归属、视觉问答和机械现场验收。本轮静音PCM功能通过，但SPEAKING P95约99.57ms，不能宣称严格稳定16fps。不开麦或自动运动来代替待确认的现场验收。
7. 旧性能日志target_fps固定8，远端模式使用API/config目标及native提交计数；待后续有新性能改动时再单独修正该元数据并回归。

本机解释器：C:\Users\35870\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe。SSH复用相邻2026-10-18_board_dialogue/board_ssh.py；禁止输出或打包私钥。最终包显式排除模型、素材字节、虚拟环境、音频和数据库。
