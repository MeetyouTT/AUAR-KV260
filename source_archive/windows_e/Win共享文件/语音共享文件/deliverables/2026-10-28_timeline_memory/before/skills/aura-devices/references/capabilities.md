# 设备能力及实际入口

| 能力 | 调度入口 | 执行和数据 |
| --- | --- | --- |
| 语音唤醒、接话、插话 | VoiceFirstRecordingController → ChannelConversationJobs → 8792 | 板端单一采集者，Windows ASR/LLM/TTS；PCM 在 RAM，结果按 request/generation 绑定 |
| 即时视觉问答 | X-Aura-Visual: frame-question-v1 | 主机 transcript 请求 token；板端从 8790 的现有预览获取同一 frame/epoch/boot JPEG，回传 /v1/voice/visual/frame；8810 CPU VLM回答 |
| 定时观察 | DeviceObserver → 192.168.50.1:8812/v1/observations | 默认 15 秒，最大一项推理，图像不落盘；摘要有 boot/epoch/frame/接收时间；关闭监听同时停止观察 |
| 摘要回忆/清除 | 主机 device_client → 127.0.0.1:8812/v1/memory/recall 或 /forget | 模型上下文注入带来源的摘要；“清除画面记忆”清除本次开机记录，同时拒绝在途旧结果重新写入 |
| 人脸登记/识别 | 8792 identity exchange → 板端 VoiceEnrollment → 8790 identity 命令 | 现有注册流程、目标/帧绑定、模板/库版本、UNKNOWN/AMBIGUOUS 保护保持；不调用 VLM 猜人名 |
| 声纹登记/查询/删除 | 8792 device_client → 8812/v1/speaker/turn | 精确 ASR context+PCM摘要；ECAPA CPU 单线程池；三样本、一致性检查、最终保存确认；独立模板库，未标定不自动认人 |
| 入镜招呼 | VisualSocial → 缓存选定音色 → 原播放器 | 稳定入镜 0.6 秒“嗯？”，4 秒无发言后一次邀请，30 秒冷却；语音忙碌则让路，播放可由原回声核验插话路径打断 |

`8812/health` 明确报告声纹是否 ready/calibrated、最近视觉错误和保留时间。普通语音不会等待声纹/视觉推理；声纹指令才发送同一次已完成采集的 PCM。LLM 与新增视觉、声纹模型位于 D 盘，ASR/TTS 保持既有授权路径；摘要及声纹数据库在 Windows 用户私有 `AppData/Local/Aura/device-memory`，不打包到共享目录。

“刚才看到了什么”等历史问题读取观察摘要，不自动重拍当前画面。当前合成录音实测“汐蓝”独立唤醒通过；短促“哎/欸”仍有转写失败，专用 KWS 候选尚未接入正式服务。完整部署状态与验收限制见项目 `deliverables/2026-10-28_device_skills/README.md`。

示例：“汐蓝，你好”“这是什么颜色”“刚才看到了什么”“清除画面记忆”“登记我的声纹，我叫小林”“确认保存声纹”“你认识我的声音吗”“删除声纹小林”“确认删除声纹”。人脸登记沿用“帮我登记身份，我叫小林”及板端引导。

限制：VAD+ASR 不是专用流式 KWS；即时唤醒、自然噪声、多说话者、声画归属和现场声纹准确率须单独验收。当前同一 boot 的视觉观察是环境记忆，不属于任意个人；不据此写入个人档案。
