# 说话、身体素材与语义动作连接（2026-10-21）

正式板端根：`/home/root/aura-speech-motion-20261021/0e98f7830e27/runtime`。
启动覆盖：`zzzzz-aura-speech-motion-trial.conf`，保留f8e的固定送显8帧覆盖、a3c8回声核验以及此前全部覆盖。
最终读取：IDLE、IDLE_READY、监听true、error空，实际计数约7.99fps。PC8792已加载动作发送代码，原27B/IQ4_XS、OmniVoice16、首句优化和记忆规则保持。

## 生效行为

- 新板端通过`X-Aura-Motion: speech-v1`请求动作能力，旧客户端仍保留旧通道行为。模型的低延迟三字段/紧凑语法不变，不增加模型调用或等待动作元数据。
- PC按实际合成的语句生成有界控制包，在该段PCM之前发送，使用答案的样本时钟调度。明确动作字段优先；当前空动作语法由保守的开头语义规则补充。“好的”等确认点头，“抱歉/不能”等否定摇头，“哇/太棒了”等惊讶，“没听清/不确定”等困惑。引语、假设与普通说明不强加动作。
- 每轮最多两种不同反应，相隔至少4秒音频；板端再次检查次数/间隔。缓冲、反馈语音、暂停不会触发答案动作；取消或旧代次的控制被丢弃。点头/摇头/惊讶使用完整单次素材，困惑限制可见时间后回到说话。
- 修复实时说话只使用静态身体配口型的路径。复用已有`IdleBodyTrack`、原始身体帧、面部位置与局部嘴部合成，保留原身体像素和眼睛位置。用兼容板端旧Pillow的枚举；小型仿射逆变换避免额外线程库调用。
- 连续播报的口型仍按实际音频包络采样；四类反应使用原生动作帧，没有为反应素材制造未经校准的口型追踪。不是音素级唇同步，也不把规则匹配称为完整语义动作规划。

## 验证与资源代价

| 项目 | 结果 |
|---|---|
| 相关板端回归、图像核验、pan预检 | 176项通过；原RGB565/插值质量门槛保持 |
| 主机/首句/记忆/HTTP回归 | 73项及4子用例通过 |
| 真实素材/FSM/PCM发包/身体像素测试 | 20项通过 |
| 隐藏GTK | 启动、原生送显、null音频、无录音、无界面错误通过；双实例数据不作为稳定性能结论 |
| 动作版单实例90秒 | 7.994fps；送显间隔P95中位146.06ms |
| 同缓存语音 | 7.891fps；P95约155.07ms，接近156.25ms门槛，余量不大 |
| UI进程CPU | 同场91.22%→99.92%；允许真实身体合成最多增加25%，实际约9.5%，仍低于原未限帧约148% |
| 正式模型通道 | 既有归档输入经过真实ASR/27B/TTS，speech_motion=v1，控制先于PCM，完整样本/摘要校验通过；无播放/新录音/ACK/持久会话提交 |

正式模型这一条普通回复的动作字段为空，符合保守规则，不能把它称为四类反应真人播放通过。四类动作对应素材、播放推进、收尾和取消由20项专项覆盖。最后读回监听true/IDLE_READY。持续真人实聊、主观丰富程度与长稳尚未验收；此前a3c8的真人语音验收保留为历史，不自动给新组合填通过。

稳定目标保持8fps，不再追24。固定送显最多暂存一张新帧，最多从采样开始有意等85ms，不重复旧帧凑数。新增身体合成仍有开销，不能保证任何系统阻塞期间零掉帧。

## 保留与回退

161份非动作Python逐字节保持；`barge_verify.py`、`barge_in_capture.py`、`barge_in_recording.py`、`handsfree_recording.py`、pan、GUI配置与固定送显worker单独核对哈希不变。摄像头PID与单元在单实例试验保持。PC只更新`common/speech_motion.py`、`common/voice_channel.py`、`tools/voice_channel_source.py`，模型/延迟/存储配置SHA保持；旧源码备份位置见`pc_action_deployment.json`。没有复制模型、虚拟环境、私钥、身份库或新增用户录音。

动作板端回退：自然空闲并按当前用户选择保护监听后，只移除自身`zzzzz-aura-speech-motion-trial.conf`并重启UI，会回到已验收f8e。不要移除稳定8帧、回声核验、聆听或pan等旧覆盖。PC若同时回退，按部署JSON中的备份恢复三个指定源码，再仅重载8792；保留所有业务配置和持久记忆数据。旧客户端能力协商未改变，PC恢复旧发送端后新版板端仍兼容旧空动作控制。

证据：`action_candidate.json`、`action_verification.json`、`action_connection_tests.json`、`action_host_regression.txt`、`action_smoke.json`、`action_trial.json`、`pc_action_manifest.json`、`pc_action_deployment.json`、`pc_motion_live.json`、`pc_action_monitor_restored.json`、`action_final_state.json`。
