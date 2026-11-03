# 本地开源音频前端接入（2026-10-21）

用户已选择本地开源。GTCRN＋Silero v5 已正式接入，当前板端根 `/home/root/aura-audio-frontend-20261021/candidate-fe6f5c7b1b56/runtime`，电脑独立 CPU 服务为 `192.168.50.1:8795`。本版实机听音与现场噪声尚待用户验收，不能沿用此前回声/打断真人结果。

板端继续负责收音、SpeexDSP 回声消除、20ms切帧、单捕获归属和取消；成熟官方 sherpa-onnx SDK 在电脑CPU运行降噪和VAD，只返回逐帧语音判断。ASR继续使用原始音频（打断路径为既有AEC输出），不使用降噪后音频替换识别输入。保留原700ms静音端点与180/240ms起点，前导改500ms补算法缓冲；前导计入既有20秒总预算。未训练、重写任何降噪/VAD/声纹网络。

每个捕获实例独立UUID、严格序号和样本进度，一次仅一包；电脑预热两条独立流，忙时拒绝，队列不积压。网络超时、错归属、取消后的回包不能变成语音事件，也不会回退为纯能量打断。保留取消前ASR核验、完整PCM提交、ACK交接、记忆、首句优化、922dab渲染/动作/pan/状态缓存和阶段性能日志。

## 验证与边界

- 最终板端313项回归、预检、隐藏GTK配置检查通过。隐藏检查关闭第二个native显示通道和麦克风；正式服务仍启用原native显示。
- 35段公开/合成输入中，30段语音均收尾，5段非人声0次起点；ASR输入是原音频精确切片。裁切与强噪声仍有4项公开转写差异，不能说识别完全无损或达到现场准确率。
- 最终协议公开PCM实际板端→PC→板端，180/240ms两种起点共622帧，P95约4.38/4.29ms，最大13.83ms，0帧超过20ms；此值不包括算法起点、说完判定、ASR、LLM和TTS的完整等待。
- 独立300秒回退守护下切换并提交，监听保持 `True`，最终 `IDLE/IDLE_READY`。切换期间相机PID/epoch、身份库指纹保持，未重启8792模型服务；本版尚无现场录音/听音验收。
- 初次隔离隐藏UI/传输测试期间观察到板卡重启，原因未确认、上次日志未持久化；不归因于某组件。正式922dab自动恢复。后续隐藏检查关闭重复原生显示，单独传输及正式切换通过。诊断见 integration_reboot_diagnostic.json。
- VAD/降噪主要防非人声误触发，不拒绝所有电视或旁人人声。既有SpeechBrain ECAPA仍只通过公开素材隔离复测，未接入正式聊天、未读取个人声纹库、未改阈值。下一阶段才做说话者验证、短句策略及多人的真实标定；视觉正脸不是声画归属证明。

补充被动观察：12次采样看到实际开麦及前端602帧，未出现UI/录音/打断错误。单帧往返最大约107.32ms，高于公开节拍测试，不能把公开样本的0超20ms当作真实运行保证。也不能据此认定现场噪声、延迟或打断体验验收通过。

## 启停与回退

电脑运行 `start_frontend.ps1` 可启动经过模型/源码指纹检查的独立服务，隐藏窗口并脱离终端；模型在 `D:/AIModels/audio-frontend-eval-20261021`，未进入共享目录。没有配置Windows登录自动启动；电脑重启后须重启此独立服务，服务不可用时音频捕获报错而不会误打断。

本次两层覆盖分别为 `zzzzzzzz-aura-audio-frontend-20261021.conf` 和 `zzzzzzzzz-aura-audio-frontend-budget-20261021.conf`，旧覆盖全部保留。仅撤销最终budget层会回到初次前端；完整回退应在自然空闲、保存当前监听选择后停止UI，核对并撤销这两份本次覆盖、daemon-reload、启动原922dab，再核对音频/监听状态。不得删除旧候选、模型或身份库。备份位置 `/home/root/aura-audio-frontend-20261021/candidate-fe6f5c7b1b56/deployment-4d9ad187`，原922dab配置在 initial_integration/integration_board_baseline.json。

## 证据

verification_summary.json、integration_candidate.json、integration_tests_log.log、integration_preflight_log.log、integration_smoke.json、integration_validation.json、integration_lan_validation.json、integration_deployment.json、pc_service/manifest.json。此前隔离结论保留在 isolated_verification_summary.json；finalize.py为旧阶段脚本，不能用其覆盖当前摘要。
