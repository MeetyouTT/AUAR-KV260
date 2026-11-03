# 实机玩偶动画审查（2026-10-20）

结论：卡顿已实测复现；计划动作素材存在于板端，但正常流式聊天的动作链路被置空。此次只读审查，不修改正式源码、不重启服务、不触发录音或播放。

## 现场性能

活动UI：`/home/root/aura-long-conversation-20261019/candidate-9a5bcf476bf8/runtime`，systemd MainPID现场41716。45次约200ms间隔HTTP采样期间均为IDLE。

- 渲染发布序列对视觉时间：约3.108帧/秒。此为渲染发布吞吐，非屏幕扫描/呈现帧率。
- HTTP采样所见单帧耗时中位297.25ms、最大797.64ms；重复采到同一帧，故不是逐帧总体分布。
- 配置tick_ms=33（目标约30Hz），不能证明实际达到30Hz。
- 板端UI进程ps累计CPU约152%，同时还有视觉等任务。累计CPU不能据此单独确认瞬时资源竞争为主因。

独立无声16帧IDLE+面部合成剖析耗时4.764秒，其中Pillow transform累计4.239秒（约89%），底层transform2自身3.777秒。整体offset变换累计2.948秒，眨眼warp 6次累计1.293秒。剖析与现场服务并行，仅定位热点，不当无负载基准；未包含GTK、最终缩放和JPEG。

活动播放层在frame_at执行offset，面部BlinkLayer.apply还执行offset，存在重复整体变换路径。全画布仿射与旧版眼层warp是优先优化对象。每帧还有缩放与JPEG，属于额外开销，当前证据未证明其为主因。

## 动作素材与触发链路

板端实际PNG数量：idle_normal/idle_listening/idle_thinking/emo_puzzled各39；ack_nod/deny_shake/emo_surprised各22。素材并未整体丢失。

已核对：

1. 电脑当前本地dialogue_host_ollama.py的快速提示明确avatar_action为空，schema只允许空字符串。
2. 已取回板端活动voice_channel_source.py，其control帧也固定action=''。该文件为部署快照，不能直接当电脑8792已加载文件的证明。
3. 板端活动streaming_controller.py与本地SHA一致：开口apply_response固定emotion='neutral'、avatar_action=''；control只改core.emotion，未重新路由FSM情绪状态，也未消费action。

因此正常聊天无法通过这条通道触发点头/摇头/惊讶/困惑动作；情绪三档路由也不完整。倾听/思考仍有事件映射，不能概括为所有状态素材均未使用。本轮未发起新对话，不声称已完成各状态真人验收。

## 版本偏差

活动board_avatar_worker.py和voice_channel_source.py哈希与本地不同；worker可见核心渲染逻辑相同，哈希不同不等于每项都有行为差异。活动preview_script.py和facial_layers.py从剖析可见为较早实现：活动frame_at未走本地IdleBodyTrack路径；活动warp也不是本地已缩小ROI的版本。故本地10月9日说话沿用待机身体及眼层优化报告不能直接证明实机已部署。

## 修复顺序

1. 以取回的活动版本建立候选，收拢预览播放器、面部层及依赖，保留当前长对话、身份和音频功能。
2. 消除重复整体变换，眼层改局部ROI；在板端验证像素配准、轮廓和口型，再评估预计算/缓存及JPEG降频，不能仅调tick_ms。
3. 端到端恢复动作白名单、传输和消费；明确音频同步策略，一次性动作完整播放且不反复触发，保留取消代次保护。情绪需真正驱动状态路由。
4. 分别测待机、倾听、思考、说话及动作切换，报告逐帧P50/P95/最大间隔、渲染/显示序列和超时；最后真人对话验收。保持既有“说话沿用待机身体”的用户选择，若需改视觉方案另行讨论。

原始证据：board_idle_probe.json、board_profile.json、active_sources.json。未下载/复制任何模型，未改变模型存储。
