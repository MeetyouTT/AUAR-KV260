# 自动轮流对话实现与验收（2026-10-18）

已通过真实自动接话、结束后重新开始仍记得绿色、用户听音和结束停止验收；原27B已验证颜色偏好超出四轮仍可召回。

## 实际行为

点击一次“开始对话”，直接说话；检测到至少180ms有效语音后，停顿约700ms自动提交。保留200ms前导声音，闲置监听使用有界缓冲，不持续积累整段PCM。每段最长约20秒；录音、网络、播放或记忆确认出错时停止对话并显示错误，需手动重新开始。

ASR、原27B/IQ4_XS和OmniVoice16仍在电脑端。生成及播放期间关闭麦克风；完整播放并收到本轮匹配的记忆提交ACK后，等待500ms尾音保护，再自动聆听下一轮。按“结束对话”或取消会关闭监听、取消当前请求和播放；过期完成事件不能重新开启会话。

## 现场发现并修复的记忆缺口

第一轮连续聊天已正确记住绿色，但用户随后确认“停止对话，第二轮就不记得我喜欢绿色”。实际记录显示已经聊了七轮，后续仍带8条历史消息，原因是原来只保留最近四轮，颜色那轮被挤出，并非结束按钮清空历史。失败证据保留为memory_failure_state.json及listening.json，最初轮转证据保留为live_automatic_initial.json，不能用初次绿色成功掩盖后续失败。

现增加一个有界的、同boot/session的颜色偏好锚点：只从明确的第一人称颜色陈述中提取，并在匹配完整播放ACK后保存对应原始问答。被取消、未播完、错误ACK、疑问、引述、第三人称、假设或任意附加指令均不写成偏好。新颜色覆盖旧颜色，明确不再喜欢该颜色或要求忘记颜色偏好时移除锚点；不同会话隔离，32个会话淘汰时同步清理。

保留原四轮短期历史；旧颜色信息被窗口挤出时，在原2048上下文预算内额外带入原始确认问答（2条），27B自由生成回复。没有新增模型调用、固定颜色答案、扩大上下文或修改系统人设提示；预算不足则不额外注入，记录context_budget。当前只覆盖明确颜色偏好，不宣称任意事实、人名或长期记忆均已完成。结束/开始保留同一会话，但电脑8792服务重启、板端UI重建会话或boot改变均会清空；没有将偏好落盘。

这版是自动轮流交谈。尚不支持播放时凭声音打断、双向同时说话或回声消除。700ms停顿适合当前第一版，尚未覆盖口音、长犹豫、远场、电视声及噪声的系统测试。

## 验证及时间口径

- 电脑端主批次65项通过，1项Linux生命周期检查跳过、1项POSIX权限检查排除，26个子用例通过；后续worker批次7项通过，与主批次有重叠，不能相加当成独立测试数量。
- KV260 Linux最终53项全部通过，包含真实文件锁/子进程录音生命周期、POSIX权限、静音端点、有界缓冲、短噪声、保留首音、等待播放ACK、取消和过期结果保护。GTK/GStreamer资源检查通过。
- 记忆修复电脑端70项及26子用例通过（与前面协议测试有重叠）。原27B实际文字探针：重放7轮已确认问答后仍答对绿色；偏好改蓝色并再插入5轮后仍答对蓝色；带“你好啊请记住”的现场真实转写再插入5轮后仍答对绿色。该探针使用受控播放ACK重放、实际27B自由生成，不计作新话筒录音/板端听音。
- 当前真实观测状态：`PASS_ONE_AUTOMATIC_ROUND_AND_USER_STOP`；此文件属于修复后观测。最新用户反馈及修复后复测是否通过以listening.json和verification_summary.json为准。
- 最后一次带“你好啊请记住”的真实转写及匹配完整播放ACK已记录；健康接口parser_revision=2、独立偏好会话计数=1。用户确认“已说完并结束，回答清楚自然”；结束复核状态=STOPPED，助手是否发送收尾取消命令=False。重新开始后绿色召回及自然听音另保留在live_memory_first_retest.json和listening.json。
- 本轮被完整观测、匹配播放ACK的样本，从自动录音提交到正式回答软件播放启动记录为：3.693秒、3.653秒。这不包括说话时间和700ms端点判定，亦非外部麦克风测得的声学起音；不是稳定3秒保证。
- 原27B、量化、生成设置、五个延迟开关、OmniVoice16和视觉YOLOX/DPU配置保持，板端源码指纹匹配。部署切换当时相机PID一致，随后另观测到相机服务停止/启动，PID变为199373，来源未确认；当前模型SHA与DPU arch不变且健康，boot未变，不能宣称相机进程全程未变。之后也观测到UI服务另一次停止/启动，路径未换，详情ui_external_restart.json；这种服务重建会更换会话、清空进程内记忆，不能与点击结束/开始等同。
- 额外自由聊天中仍出现专有名词误听及“打错字”式回复，泛化ASR和语音语境表达仍需完善；本轮自动轮转验收不代表这些问题已解决。原界面底部的远端“语音主机待接入”与本地已连接语音通道尚有显示口径不一致，也列为后续界面完善项。

## 运行与回退

活动板端目录：`/home/root/aura-automatic-conversation-20261018/candidate-b1b08f8b0b2b/runtime`。

旧运行目录：`/home/root/aura-stream-playback-20261018/candidate-ec77f48a63de/runtime`。

部署前的systemd unit与启动配置：`/home/root/aura-automatic-conversation-20261018/candidate-b1b08f8b0b2b/activation-backup-bf55f17ce2`。只切换aura-avatar-ui.service，未改相机服务、DPU或FPGA。

如需恢复之前手动开始/停止录音的正式版本，在板端先结束会话，再执行：

```sh
systemctl stop aura-avatar-ui.service
cp /home/root/aura-automatic-conversation-20261018/candidate-b1b08f8b0b2b/activation-backup-bf55f17ce2/aura-avatar-ui.service /etc/systemd/system/aura-avatar-ui.service
systemctl daemon-reload
systemctl start aura-avatar-ui.service
```

原目录、资源和历史证据均保留，不删除模型。回退后应检查8783/api/state的IDLE_READY和相机8790/health。正常启动仍使用现有aura-avatar-ui.service；重启后默认停止，不自行开启麦克风。只设置源码automatic_turns=false并不等于已更新板端，后续发布必须同步启动器源码指纹。

颜色记忆修复仅在电脑端加载，不需要重启KV260。电脑端回退需在结束会话后恢复本目录before/aura/tools下的board_model_host.py、voice_channel_source.py，再精准停止8792服务及其OmniVoice子进程，使用原start_background_models.ps1重新启动；不要停止ASR8791、项目Ollama11435或全局Ollama11434。新增session_memory.py无入口时可保留，不做删除。memory_reload_before.json、memory_reload_ready.json记录了本次重载范围及实际加载版本。重启会清空进程内历史与颜色偏好。

## 证据与交付

- `candidate.json`、`tests_board.log`：最终隔离候选、53项Linux测试和资源检查。
- `tests_pc.log`、`tests_pc.xml`、`tests_worker_pc.log`：电脑端测试。
- `deployment.json`、`current_state.json`、`live_screen.png`：实际部署、服务健康、界面与源码指纹。
- `live_playback.json`、`listening.json`、`verification_summary.json`：新录音、多轮状态转换、匹配ACK、听音和停止结果。
- `memory_failure_state.json`、`live_automatic_initial.json`：修复前缺口和初次轮转证据。`tests_memory.log`、`preference_27b_probe.json`：修复回归与原27B文字验证。
- `before/`：改前源码。`verified_source.zip`：本版生产变更与相关测试，带独立SHA256清单；不含模型、虚拟环境或SSH私钥。
- 首次导入/Windows权限/ARM状态发布时序失败日志保留，最终结论只依据最终通过日志。测试修复将worker结果与随后状态发布分别等待，避免假设两者原子发布。

大语言模型数据仍在D:/AIModels；本目录只存代码、设计、配置和运行证据。候选CosyVoice声线本轮没有切入正式服务。
