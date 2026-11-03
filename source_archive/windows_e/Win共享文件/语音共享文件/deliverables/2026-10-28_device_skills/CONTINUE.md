# 接续规则

先读 README.md / PROGRESS.json。正式板端 `/home/root/aura-device-skills-20261028/0cd7c3445a84475098b938d5b97175e0/runtime`，Windows `voice-device-skills-20261028-r6`。本轮已部署，整机最终验收未完成。

**用户重新连接后已复核：有线直连恢复 1Gbps；板卡重启为 boot `50b4fef1-9748-43c7-92bf-3040db8c994e`，自动进入原已提交入口。277 项源码校验、相机/MCP01、Windows 语音与设备服务通过，待机送显快照约 15.99fps。监听/麦克风/跟随仍关闭，机械保护保持。** [重连核验](reconnect_status.json)、[网络证据](final_connectivity.json)。此前断线记录保留在 [历史证据](connectivity_before_reconnect.json)。



1. 不按旧历史入口或旧 boot 执行操作。重新核对实际 systemd 入口、当前 boot、源 SHA、监听/播放/机械状态；当前相机 PID 1350 仅为本次证据，后续必须动态读取。
2. 用户已授权停止跟随后部署，无需再次询问同一授权。实际停止必须走已有 UI 入口并确认无活动运动；部署仍要求监听关闭、IDLE/IDLE_READY。不要主动开启跟随、麦克风或放宽机械精确绑定。
3. 其他模型保留；LLM/Ollama 只在 D 盘，严禁复制权重、缓存分段或权重目录联接到共享树。身份数据库/原始现场录音不入源码包。
4. 本轮下一步是现场样本与短呼唤词方案、说话长帧诊断及一次集中真人验收。KWS 候选有漏检和“西兰花”误报，禁止直接启用或仅降低阈值。不能把离线文本测试当实际唤醒成功。
5. 不直接重跑本目录 prepare/deploy/restart 旧脚本：它们绑定旧入口或 r4/r5 前置条件。部署脚本保留为证据和可参考流程。回退也只处理自己新增的覆盖，不能删除其他 systemd drop-in 或覆盖并行机械更新。
6. 若声纹现场校准，保存模型指纹、同人/异人/噪声数据的评价证据，再决定阈值；未校准不自动访问个人记忆。人脸与声音不能仅凭同屏关联。

核验工具：windows_health.py / read_board_state.py / reconnect_check.py 为只读检查。verify_release.py 保留原部署时的 boot、相机 PID 与既定状态，重启后不要盲改断言填通过；reconnect_check.py 按实际入口核对原部署源码/配置并记录新 boot，不更新机械绑定。原部署证据 release_verification.json 保留。

已删除的旧等待心跳无需重建。本轮没有创建自动任务。
