# YuNet受限自动恢复候选与快速验证

状态：代码候选已实现，默认关闭；尚未切入正式相机服务。2026-10-23本轮实板检查前后相机198117/unit af337bce…保持，YuNet仍为CPU_YUNET_FALLBACK_AFTER_DPU_OVERRUN，YOLO业务保持原运行。本轮实际DPU新作业数0，不把合成检查当真实推理验收。

用户要求缩短验证等待。本轮改为快速故障注入、已有集成回归、KV260隔离逻辑/成本检查；后续每轮真实业务试跑约1～3分钟，长期证据随正式候选正常运行积累，不将两小时长测作为后续开发前置。

改动：新增dpu_recovery_policy.py，修改dpu_vision_schedule.py、dpu_yunet.py和ui_camera_service.py。启用方式是在隔离候选相机配置中新增`"yunet_dpu_recovery": true`，不是用单字段片段覆盖完整生产配置。未设置时保持原超限后停用规则；显式非bool拒绝。父版三个源码通过UART回读与当前已接受release manifest逐字节核对，parent-manifest.json记录版本。

恢复规则：原30ms硬占用和5ms guard不变；仅native明确完成/status0、无body异常且仅hardcap超的事件可冷却10秒。需要上次故障后新的正常YOLO完成且最近不超过0.5秒，无新增主周期超限，仍按原单owner/primary优先/截止时间原子准入。10分钟最多2个恢复探测周期、连续3次native正常完成后退出观察期。确认成功发生在PinnedRunner.wait返回0且slot尚未释放时；异常/取消不产生旧成功证明。

冷却、拒绝和CPU fallback均不持有DPU槽，也不等待睡眠占槽；恢复不清除原overruns/maximum/last_overrun。原生失败、guard越界、主任务异常或预算耗尽保持停用；探测期间YOLO超周期亦立即停止探测。服务关闭/过期源等明确未提交的撤回不误判成native失败。SFace保护不使用此YuNet恢复机制。

验证：offline Docker沿用既有89项时效/重试/runtime软件回归，新增24项策略/adapter故障检查和4项实际PinnedRunner包装层合成集成，共117项通过（执行约0.104秒，不含容器启动）。初次运行发现bootstrap路径缺失，修正测试装载后通过，原错误日志本机保留。

KV260 Python3.9.9/aarch64同源隔离检查24项通过，约0.0597秒；无VART/XIR/numpy/cv2/gi加载，无真实DPU推理和服务切换。500个空合成槽/模式的额外每调用线程CPU均值0.02738ms，低于0.5ms前置门槛；这仅是该段微基准，不是整板降耗或真实调用尾延迟收益。

可复现的本机检查：`python3 -B -m unittest discover -s tests -v`（完整包装层4项在本机未装旧harness时跳过）；完整117项使用`python3 run_regressions.py`，依赖脚本中已存在的本机离线镜像和冻结源目录。板端隔离封包由build_board_preflight.py生成；board-preflight-manifest.json固定helper、payload及6份源SHA。生产部署需基于当前活动版本构造受保护的短试跑，旧写死84116d8f基线的helper不能复用。

本候选解决的是一次允许恢复的故障后长期只用CPU的问题，尚未证明31ms等待长尾本身消除。当前正式服务未启用新选项；新配置的真实推理、恢复耗时、UI/音频共存和整板CPU收益仍待短试跑。后续原生对照/独立执行路径继续按证据推进，语音/身份旧库/运动/位流保持原范围。
