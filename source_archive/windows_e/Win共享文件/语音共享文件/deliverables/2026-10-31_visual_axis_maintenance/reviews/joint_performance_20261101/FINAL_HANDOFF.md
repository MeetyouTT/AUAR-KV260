# 本轮实测与修复收尾（2026-11-01）

已完成原板端人脸随动恢复与方向修正、UI状态投影优化、字幕单文件修复和真人复验。最后一轮已收到匹配的完整播放回执，用户确认“两栏字幕都显示，声音完整”。设备最终保持主页面、语音PAUSED/enabled=false/mic=false、无播放、跟随关闭、转轴输出关闭；当前没有在途设备命令。

用户本轮还确认：原版跟随效果大致合适；自我介绍声音连续、等待可接受；视觉人数正确且声音完整；主动多轮测试后仍记得温水偏好。记忆结论属于用户当前会话体验，不扩展为超过五分钟的摘要检索验收。

| 同方法约60秒UI对照 | 改前 | 投影优化后 |
|---|---:|---:|
| publish耗时中位 ms | 9.59 | 4.57 |
| 完整UI回调CPU中位 ms | 25.55 | 20.68 |
| GTK CPU中位，100%=单核 | 51.98% | 47.93% |
| 整板4核CPU忙碌中位 | 56.63% | 54.85% |
| 原生呈现计数/秒 | 15.75 | 15.86 |

该对照属于startup71c28版本，采样脚本正文、2秒间隔、PSS与/proc遍历保持，观察器有可见CPU开销；场景与GUI重启的影响未完全排除。一次绘制101.20ms长尾、视觉源龄P95从176→194ms等限制完整保留。字幕de04版本保留投影热路径，本轮按安排没有再做性能采样。

字幕修复只增加本次有效提交owner/epoch的一次性显示许可，原请求TTL、后续失效、锁顺序和控制API正文清理保持。公开ARM R2在板端Python3.9.9上实际通过19项行为、10项投影与500个嵌套等价案例。最终真人68点记录中，caption.showing的true/false均出现，API两处正文空标志全为true，无缺字段；用户在播放中确认两栏显示。GUI与渲染worker故障均0，本轮音频欠载0。暂停后字幕可按设计清空。

当前生产根仍为`/home/root/aura-board-business-20261030/production-5259eab11e42af13`；startup `22317f7933447b28a2ca535a47246de8b3869989cc0d964a13cd169cd2289311`，manifest `5b741bff8039a4f71110b06cce88ff40bea32a27ace718a263f6879f79deaa2b`，spec `62b99e24560229c78a3be000fed5752b6a50c4fb16ab6bc2c88e987561831177`，配置SHA `a695d620ddad3216de2d0447ec91d0e983a67343c2282179adece8014fccc063`。380项闭包全部实读匹配。最后仅更新production_memory_presentation源码，另外379项、原25文件跟随控制器、当前相机/转轴配置、原相机430894、wide固件与VART保持；跟随极性+1。

最终owner为supervisor689460/birth5191021、GTK689464/birth5191136、camera430894/birth4011213，同boot `bebd3e7d-e984-4517-8cbb-211df7f1c6dc`；完整命令指纹见[结构化最终交接](FINAL_HANDOFF.json)。脉宽读回1400µs只是控制读回，不是机械角度或中点标定。最后配对request hash `3322de4ccdf81ee195eb6d8b8cefe8d7768b40264e7d8c958acc90a0d69408e6`；[原始脱敏窗口](E:/Win共享文件/语音共享文件/deliverables/2026-10-31_visual_axis_maintenance/reviews/joint_performance_20261101/evidence/live_trial_1793536566480481000/metadata.jsonl)、[完整播放结果](E:/Win共享文件/语音共享文件/deliverables/2026-10-31_visual_axis_maintenance/reviews/joint_performance_20261101/evidence/live_trial_1793536566480481000/RESULT.json)、[最终暂停读回](E:/Win共享文件/语音共享文件/deliverables/2026-10-31_visual_axis_maintenance/reviews/joint_performance_20261101/evidence/live_trial_1793536566480481000/FINAL_PAUSED.json)均保留。软件首音频入队约9.185秒，不当作声学首声。

首次公开包的Python注解兼容失败、第三轮中断、用户说明问题未说好的无效追问、旧观察器漏关联ACK，以及字幕首窗到时错误取消在途生成的记录均按历史保留。临时观察器随后增加首个已接纳请求门槛，超时只停采样，生成/播放期间不再发送cancel；空闲、生成、播放及一直忙的公开门槛检查通过。先前被取消窗不覆盖为本轮成功，字幕与完整声音的成功只对应最后一轮。

项目spec/ready、AGENTS/README、视觉任务最新指针和协调文件已接入本回执，改前原字节归档保留。后续操作从[最新指针](LATEST.json)读取并新鲜核对设备状态；设备串行分工仍沿用用户安排，本窗口当前空闲。机械零点/角度、声学首声与长期稳定性不属于本轮完成声明。
