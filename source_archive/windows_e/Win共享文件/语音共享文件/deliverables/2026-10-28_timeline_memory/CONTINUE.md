# 时间轴 v1 接续

先读本目录 README.md、PROGRESS.json、release_verification.json。Windows 已提交为 `voice-timeline-20261028-r1` / `device-timeline-v1`；下方旧目录“r6 最新”或“时间轴只设计”属于历史。整个记忆方案尚未全部完成。

1. 每次接续重新读取实际 boot、systemd 入口、源码和空闲状态。本轮最后 boot `55152f95-ea3a-4c6c-82e6-51bd553d96fd`；板端仍为原 0cd7…/runtime，277 项启动校验。不要按旧 boot/PID 放宽机械保护；保护并行机械更新。
2. 用户已有停止跟随后部署授权；实际停止走原 UI 入口并确认无运动。不要自行开启麦克风或运动。最后监听/跟随均关闭，IDLE_READY，音量 70；机械 FAULT/位置 null 保持。
3. 不直接重跑 deploy_windows.py：它绑定当时源码/boot；deployment.json 已 COMMITTED，脚本会拒绝再次执行。代码回退也保留最新权威库，不能恢复旧库使已遗忘信息回来。不能从旧 runtime 覆盖板卡。
4. 私有设备库必须按**独立 WMI 后台文件视图**检查/备份，直接从当前工具进程读取同名 AppData 路径可能是影子副本。inspect_service_databases.py 以 WMI 运行会保存 physical_database_check.json；`--backup` 才在真实私有目录生成一致快照。早期 verification_before_private_view_fix.json 和 agent 视图视觉库快照不是当前生产证据。
5. 当前记忆权威仍在 Windows。ARM 测试目录只是合成库兼容验证，不是真实迁库；未来按单写入者、一致快照、授权范围/版本和最新数据可回退的步骤移交 PS。
6. 配置时区 America/Los_Angeles，接收端 UTC 作日期锚点；不信任板卡墙钟。30 天/10000 视觉事件是上限，先达到者清理；不延长旧短期记录、不补造历史图像。仅保存文字观察。
7. 保留对话播放 ACK、memory_revision、视觉持久版本和派生回复来源失效；身份未确认/未标定不自动开放个人档案。不能只删视觉表而让旧回复在对话召回中复活。
8. 其他模型不卸载；LLM/Ollama 权重和下载数据继续 D 盘，禁止放入共享树或建立权重目录联接。私有数据库/备份、真实帧、录音不进源码包。

优先后续：后台情节/日摘要及有效来源关联；事实变化时间与更丰富的时间段检索；对话主题/日期删除；PS 权威存储接管；最终跨天真人验收。既有短唤醒词、说话长帧、声画归属和机械问题仍开放。

核验工具：inspect_current.py 只读核对板卡与当前服务，写 runtime_current.json；verify_deployment.py 使用这个严格复核的基线并校对实际状态。板卡重启后先复核，不直接改断言。live_persistence.py 会提交一帧观察并重启 CPU 设备服务，不是只读工具，不应例行重复运行。

没有创建自动任务或新聊天。当前代码和测试见 verified_source.zip / source_manifest.json；按新代码变更再决定必要的测试范围，不重复累加旧用例数量。
