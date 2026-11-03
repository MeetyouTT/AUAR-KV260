# 状态快照与分阶段性能记录优化

## 最终上线与实测

正式根 `/home/root/aura-speech-motion-20261021/922dab49a74f/runtime`，新增独立 `zzzzzzz-aura-snapshot-budget.conf`，原bd9e合成/动作/固定送显/回声/聆听/pan覆盖全部保留。限时试验COMMITTED，看门狗已停止，原监听true已恢复；PC未修改或重启。

| 条件 | 平均fps | sink间隔P95中位 | UI CPU（单核100%） |
|---|---:|---:|---:|
| 切换前暂停监听基线 | 8.007 | 186.33ms | 107.20% |
| 新版90秒暂停监听 | 8.012 | 135.21ms | 92.75% |
| 新版缓存语音短测 | 8.333 | 134.65ms | 不单列 |

缓存语音统计来自短SPEAKING采样区间，边界可造成高于8的估计，不能当持续8.33fps能力。受控前后测还包含重启后进程历史清空，不能把整机全部差异归因于代码；同一真实状态的复制微测26.51→8.97ms才是相同输入的独立证据。录音缓存失效、服务单次读取等收益由专项行为测试确认，后续仍需积累真实等负载数据。

正式阶段日志已写25条，覆盖IDLE/SPEAKING/VOICE_PREPARING/VOICE_STARTING，0丢失/0错误。最终读回IDLE/IDLE_READY、monitor=true、error空，约7.999fps/P95 150.89ms，日志增至30条。此最终快照为恢复监听后当时状态，不能代替持续真人对话验收。用户已接受的真人对话属于bd9e，不能自动标新组合真人通过。

证据snapshot_fix_candidate.json、snapshot_fix_verification.json、snapshot_fix_tests.json、snapshot_fix_smoke.json、snapshot_fix_trial.json、snapshot_fix_final_state.json。实际日志路径由API avatar_renderer.presentation.performance_log.path给出，位于当前managed-runs/.../evidence/render_performance.jsonl。小样本5秒P95只适合看阶段波动，不应将各窗口P95平均成整个对话的P95。

回退时在自然空闲并保护用户监听选择后，仅移除自身zzzzzzz-aura-snapshot-budget.conf，重启UI即回到bd9e；保留所有旧覆盖、PC配置和持久记忆。日志轮转保留约4MB加单条记录边界开销，写入失败只上报诊断错误、不取消语音。

用户在bd9e真人对话通过后授权继续优化。本轮不更换模型、语音、动作素材或渲染画质，重点减少状态快照对送显deadline的挤占，并补上原本缺失的阶段性能日志。

## 候选修改

- 快照的JSON树使用专门的隔离复制，避免deepcopy对每个不可变标量的分派；嵌套字典/列表/元组仍独立，非JSON对象沿用deepcopy兜底。
- RecordingController.public同份快照只读取一次播放状态及转写服务状态，不改变实际控制路径的检查。CapturedAudio与AudioRef为frozen，PCM为bytes时仅缓存当前一份元数据，替换录音即失效；返回的format字典依然隔离。非标准/可变输入保持原即时计算。
- 在实际native push完成后，按phase和FSM状态聚合5秒帧间隔、处理耗时、快照耗时及>187.5ms次数，跨阶段的间隔不强算到下一阶段。不写音频、图像或聊天正文。
- 文件由独立后台线程写入，有界4条队列，满队列丢诊断而不等待I/O；约2MB轮转到一份备份。正常关闭尝试刷新最后窗口。日志属于软件提交时刻，不等同物理屏幕扫描；不同5秒窗口的P95不能直接合并成全轮P95。

候选922dab49a74f基于正式bd9e，167份非改动Python一致；回声核验、监听、身体/口型、动作、PC首句/记忆和pan/config保留。变更为board_avatar_worker、board_recording、GUI传入诊断路径及新增render_performance模块。

## 已完成验证

176项相关回归、10种图像质量、pan预检及4项专项测试通过。专项覆盖嵌套快照修改隔离、一次状态读取、录音元数据失效与返回字典隔离、实际阶段间隔归属及后台落盘。板端当前真实状态的100次复制微测中位deepcopy26.51ms→snapshot_copy8.97ms；该数值是隔离复制微测，不直接当作整机实时收益。

完整隐藏GTK通过，日志已写5条、0丢失/0错误；双UI负载约7.93fps仅功能检查，不作为稳定8帧结论。随后单实例原门槛验收通过，详见上方最终结果。
