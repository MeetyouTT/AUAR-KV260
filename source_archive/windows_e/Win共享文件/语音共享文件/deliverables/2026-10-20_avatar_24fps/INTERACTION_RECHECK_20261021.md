# 实际交互复查与合成优化（2026-10-21）

## 正式修复已提交

恢复监听后的约一分钟30份被动样本：监听开关全程true、音频IDLE_READY、error空，fps范围7.983–8.023；滚动帧间隔P95范围145.05–167.60ms。全程IDLE/WAITING_PERSON、麦克风未打开，没有SPEAKING样本。这说明等待人物状态正常，不能据此宣称真实开麦/持续对话已稳定8帧或满足原P95门槛。最终实际根仍bd9e，用户进入画面后沿原视觉门控开麦。证据interaction_fix_observation.json，未干预麦克风/触发模型/生成测试台词。

实际UI根为 `/home/root/aura-speech-motion-20261021/bd9e48cc658f/runtime`，新增自身覆盖 `zzzzzz-aura-interaction-render-fix.conf`，原0e98动作/f8e送显/a3c8核验与此前覆盖全部保留。限时单实例试验COMMITTED，原监听true已恢复；PC未重载或修改。

同场暂停监听基线8.015fps、sink间隔P95中位200.86ms、UI CPU111.92%；修复后90秒8.013fps、P95中位132.03ms、CPU92.22%。缓存语音7.995fps/P95约138.23ms。此处约17.6%的CPU下降和P95下降是本次受控前后实测，不冒充已完成实聊全负载验收。证据interaction_fix_trial.json。开启监听后的被动一分钟结果另列，不与暂停结果混合。

## 复查结论

0e98正式版本可以自动聆听、提交问题并播放回答，PC原27B/OmniVoice16与首句/记忆服务健康。最近真实已完成轮次中存在`ack_nod`、at_sample=0的动作记录，说明至少一次真实语音动作接通，不仅是测试触发。普通回复动作为空仍是保守规则行为。

但开启监听/真实对话时的渲染没有达到受控测试的稳定水平。首次只读状态约7.33fps、sink间隔P95约267ms；随后24秒真实采样跨THINKING/SPEAKING/IDLE约6.45–6.87fps、P95约295–351ms。UI进程累计CPU约116%、camera约112%。此前“稳定8帧”只能用于暂停监听的短时待机/缓存语音条件，不能沿用为实聊稳定结论。

## 本轮修复

只修改两个合成文件：聆听/思考/四类反应期间不再计算不会显示的idle身体帧；真实身体序列的整帧插值复用已存在的NEON原生实现。画面采样位置、口型、眼睛、身体帧、送显调度、目标8帧、语音/回声/监听/pan/记忆与PC均保持。

40个插值采样时刻身体像素差最大0、面部矩阵完全一致。板端同场采样耗时中位21.92ms→5.67ms。176项相关回归、图像质量和pan入口检查通过。168份其他Python逐字节一致；关键回声、监听、pan、配置和固定送显worker哈希相同。候选bd9e48cc658f，正式限时验收与恢复监听后的被动负载观察结果待更新。

性能证据：interaction_recheck.json、live_interaction_detail.json、body_cost_probe.json、speaking_cost_profile.json、interaction_fix_candidate.json、interaction_fix_verification.json、interaction_fix_tests.json。cProfile包含首次39帧加载，不能把其135ms平均直接当成热态持续说话耗时。
