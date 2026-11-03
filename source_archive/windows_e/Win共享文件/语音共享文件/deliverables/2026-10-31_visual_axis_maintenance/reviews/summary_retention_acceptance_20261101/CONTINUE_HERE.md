# 扩展记忆测试接续

现役未变：startup 22317f7933447b28a2ca535a47246de8b3869989cc0d964a13cd169cd2289311，源 de04，380 项闭包。设备当前暂停、麦克风关闭、无播放、跟随关闭、转轴输出关闭。设备操作权仍由本窗口串行持有，主窗口只做本地准备。

本轮仅“自然压缩与原文删除”已通过。“同会话摘要回忆”未通过，不能以压缩完成或新播放 ACK 代替。

- 有效种子 8db2358adf1cd749e621baaee14ec65a8b87ba50a042b8419a8dfa32c1e86f34，公开句为“你好，我把杯子放在桌子左边了。”，用户确认意思正确、回答完整。
- 压缩前：可信关闭年龄 115.800794 秒，saved scope 与种子一致，用户／助手正文各 1 条。baseline 文件 target_probe_r3_baseline_1793539124765536800.json，SHA edf8640513238d30c2cb2d06b4e8e971b2572c51ab84292928015dd44369a824。
- 自然等待后：333.442281 秒，同范围两正文各 0，直接关联同一有效摘要，committed task 各 1。post 文件 target_probe_r3_after_natural_300s_1793539342593344500.json，SHA 307496a52a80319c69674c08f4e36e0b098c714ef2e1316cdb6f016f0c7a59a6。
- R1 手动追问确实 LOCAL RECORDING READY，但观察器共享命名空间被 SOURCE 覆盖，仅留 1 样点，第二次控制轮询 AttributeError、最终 guard TypeError。无取消／暂停命令，后续独立全量 guard 确认暂停。失败 trial 为 evidence/manual_trial_1793539577193045500，原冻结 d3cb 全部保留。
- 用户确认追问 ASR 意思正确，但位置回答不正确／说不记得。不能用观察错误解释掉此反馈。
- 独立一次 API 恢复到新正式 ACK 5aab489e9e8cd2e322991fbba446b0be951a33c3c87e4cac4fd52533594da692，committed=true；ACK 内没有 generation。当前 UI generation=27 与 route generation=53 分属不同字段，不混同。
- 精确 pair 原 cbe235 查询按规则拒绝：两个请求均匹配，但 same_scope=false，seed scope=4c1f3c8f5a6bcad0f6e8e3f4e2ba0b60b45424e3a7d0ee4c90b8f9c98896b81b，answer scope=bdc53733a748c6c1ce6fe91a2494e82d3bfaebb1b06281ec08e5bf042f1aceeb，saved 与 seed 不符。没有事件、依赖或正文检查。证据 target_probe_r3_manual_r1_pair_diagnostic_1793540141614839200.json，SHA 901a7befbee77a8a95638640e5255e5765146f60126f2e2811644f77540d6c1f。
- 另一次获准 API 四字段读回：同 ACK 5aab，route generation=53 / transcript_characters=13 / board_owned=true / history_requested=true。history 路由曾请求，不代表最终 prompt 包含原摘要。证据 manual_r1_route_metadata_1793540317130804700.json，SHA ce8bb41f39ee16fc3a08d234840a77d4116a42859562392e373b3fbd1b814b31。

R2 将 common、control、observer 的执行字典隔离。15 项公开本地检查通过，含真实 SOURCE 三轮、首 accepted token、完整 ACK、自然收尾及最终 guard；旧两类错误都被明确复现。冻结 manual_driver_r2/FROZEN_MANIFEST.json SHA 1410475ff46df0e86426544c10586933cfab99fa11c939972503c8dacde4dec4，组合源 a5de834918e84cb53d391a48b6365c285aef08fd0af230ffe0bc00bf558373fc。未实机运行，当前安排不再开临时 manual。

用户已再次明确确认手动追问期间“点过暂停、继续或开始聆听”；确切按钮与时序未知。这与已知原继续入口新开匿名会话的行为一致，不把范围变化归为隐藏 record_start 缺陷或 memory 本体故障。主窗口正准备用户选择的“暂停再继续接回当前对话”单源 voice_first 候选。当前不得发布／重启／改 selection；等精确冻结包后再由本窗口做具体发布准备。发布必须核启动 saved/bootstrap 路径；当前 saved 已不对应旧 seed，不能强行切回旧范围。若正常修复后仍新 scope，须用新的合法公开种子重新自然等待五分钟。

旧 57ec 语义无效、旧 3611 已 scope mismatch，均不再读取。原失败证据、用户反馈和所有源／旧冻结文件保留。模型权重及缓存不在共享目录。完整索引见 LATEST.json；主窗口维护统一分析与自身报告，不在此覆盖。
