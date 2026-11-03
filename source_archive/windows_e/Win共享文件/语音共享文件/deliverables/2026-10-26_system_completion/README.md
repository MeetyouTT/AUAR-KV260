# 玩偶自动修复与验收（2026-10-26）

用户要求先完成现有玩偶功能，再安排迁移；用户目前不在现场，先完成自动测试。本轮自动测试已完成。整个项目仍有软件缺口和现场验收项，不能标为全部完成。

Windows 8791/8792/8795 已实际启动并就绪。板卡正式UI、相机、转轴进程保持，监听仍为false、麦克风关闭、音频IDLE_READY。本轮没有实物运动命令、开麦、声音播放、身份登记或个人记忆写入，没有迁移模型或业务。

## 已实施的修复

- TTS请求增加总期限、请求ID核对、取消和异常恢复。stdout半行、无响应、退出、错误代次和stdin未读取均有真实子进程故障注入；过期后释放锁，下一请求使用新进程。等待中的请求不能终止其他请求，迟到取消重新核对归属。
- Windows TTS子进程纳入本服务持有的Job Object，服务退出时由系统结束所属子进程。
- 语音通道清理取消本请求TTS，结束LLM流并有界等待；不再无限等待TTS执行器退出。
- health按依赖状态报告200/503，包含能力版本和加载源码指纹。Ollama使用有缓存的模型清单探测；该探测证明可达及模型存在，每次推理是否成功仍由业务结果确认。
- 统一启动确认8791/8792/8795全部就绪，原子记录STARTING/READY/FAILED；拒绝复用同协议但源码/能力不匹配的语音进程。失败只清理由本次启动的模型子进程。
- 首次真实冷启遇到TTS预热120秒超时，失败证据保留。启动专用预热改为240秒，业务请求仍受自身预算约束。独立预热及后续两次完整启动成功，冷启耗时仍有波动，根因尚未完全确认。

共享主源码和本机8792已采用上述语音修复。`before/`与`baseline.json`是修改前快照；其中production_changed=false仅描述取快照时的状态。

## 自动测试结果

| 范围 | 结果 | 证据及边界 |
| --- | --- | --- |
| Windows语音、取消、记忆/ACK、启动与健康回归 | 238通过，27子测试通过；2项Windows跳过 | [日志](voice_final2.log)、[XML](voice_final2.xml)；仅允许进程自有回环端口 |
| 上述2项Linux音频补测 | 2通过 | [board_audio_auto.json](board_audio_auto.json)；实际SpeexDSP数学处理、假采集进程/独立flock，禁止设备和子进程 |
| 转轴r11候选假设备回归 | 75通过 | [motion_board_fake_device.json](motion_board_fake_device.json)；已校验的ARM轨迹数学库，禁止设备/网络/子进程 |
| 独立声纹/音频门控 | 8通过；公开四段ECAPA推理成功 | [speaker_auto_tests.json](speaker_auto_tests.json)；CPU、禁网，未读个人库、未选现场阈值 |
| Windows真实模型链路与取消 | 7项检查通过 | [live_voice_acceptance.json](live_voice_acceptance.json)；公开WAV、真实ASR/27B/OmniVoice、首文字取消、锁释放和下一轮恢复；没有播放ACK |
| 板端实际客户端经网线连接Windows | 2轮PCM接收及SHA校验通过 | [board_live_voice.json](board_live_voice.json)；首音频4505.783/3915.467ms，整轮约6.724/6.203秒；只接收 |
| 对话并发CPU音频前端 | 600帧通过；P95 7.091ms，最大21.377ms | 同上；2帧超过20ms，最大调度迟到13.834ms；12秒短窗，未做长稳/真实采集积压验收 |

不同自动回归合计 **323项通过，另27个子测试通过**；Windows跳过的2项已在Linux用同一测试体补测。真实模型/网络检查另计。板端首包和RPC使用perf_counter测量；Windows早期脚本的monotonic分辨率较粗，延迟以板端数据为准。

公开声纹同人余弦约0.7295/0.6649，异人约0.0552，单次CPU推理约44–83ms。仅为两个公开说话人的模型烟测。当前8792报告explicit_anonymous_conversation和personal_identity_memory=false；Windows已有声纹独立实现保留，正式聊天的个人身份/档案挂接未由本轮证明。

## 转轴候选及未关闭项

`pan_candidate/continuous_v10r11/`基于r10独立制作，修复停止清理顺序，使filter_tau_ms和velocity_filter_tau_ms实际作用于OneEuro。默认约159.155ms对应旧实际1Hz，默认滤波序列保持；旧80/100ms报告值未实际生效。75项假设备回归通过，**未替换正式r10**。

仍需完成：

1. 真人听音、房间噪声/旁人、真实插话、持续实聊和动画负载验收。
2. 转轴候选受控部署、机械标定、连续真实人脸输入和平顺跟随；回区速度/加速度直接归零仍存在。
3. 源绝对截止到实际COMMIT之间的竞态F04；硬件独立保证需要可信时钟/期限合同和PL验证，本轮未改固件。
4. 对齐已完成的Windows声纹/个人记忆入口和最终整合版本，验证个人身份授权与跨人档案。
5. 真实画面问答/ASD、全项目发布复现的原有缺口，见[全系统审查](../../../协作任务/2026-10-26_全系统审查/README.md)。HDMI冷启排查仍按此前用户要求暂停。

## 启动、复现和交付

入口为语音项目根目录`start_voice.ps1`。成功打印三项服务READY；失败读取`deliverables/2026-10-18_board_dialogue/models_launch.json`及port日志。源码指纹不匹配需核对进程归属并受控重启；启动器不会自行终止旧监听者。

`validate_voice.py <新运行名>`使用既有语音Python执行禁外网回归，需要临时回环套接字权限。板端脚本复用既有SSH，不启动UI/运动。`board_auto_tests.py`若同摘要目录已存在会退出，复测需另选新目录。`speaker_auto_tests.py`使用D盘CPU环境和公开样本，合成临时库位于本交付目录。

`source_and_acceptance.zip`按显式清单包含修改源码、修改前备份、转轴候选和小型报告；`SOURCE_MANIFEST.json`记录SHA256。`finalize_report.py`核对运行源码指纹/三服务健康，逐项验证包内哈希。包不含模型、环境、真实录音、密钥或个人数据库。

原始失败保留：首次预热/启动超时、Windows非提升运行的回环/临时目录权限失败、初始Linux专属模块收集失败。后续按相应平台和明确测试目录重跑通过，失败不计入成功数。
