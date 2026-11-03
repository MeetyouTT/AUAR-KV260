<!-- subtitle-current-20261101 -->
字幕一源修复已发布并完成一轮真人完整播放回执，最终PAUSED/mic=false/无播放、main页面，原跟随关闭、转轴输出关闭。字幕两栏用户反馈状态：both_visible。

当前startup `22317f7933447b28a2ca535a47246de8b3869989cc0d964a13cd169cd2289311`，manifest `5b741bff8039a4f71110b06cce88ff40bea32a27ace718a263f6879f79deaa2b`，spec `62b99e24560229c78a3be000fed5752b6a50c4fb16ab6bc2c88e987561831177`，源de04；380项闭包实读匹配，唯一改动production_memory_presentation，另379项/原相机430894/原25控制器/当前四配置/wide固件保持。supervisor689460、GTK689464；完整birth/命令指纹见[最新实板状态](E:/Win共享文件/语音共享文件/deliverables/2026-10-31_visual_axis_maintenance/reviews/joint_performance_20261101/CURRENT_SUBTITLE_RELEASE.json)。

原71c28的UI性能对照与全部失败/重做证据保留；字幕新版未重复性能采样。用户已报告多轮记忆正常，非超过五分钟摘要检索验收。后续操作先新鲜核对，不沿用下方旧startup/PID。
<!-- /subtitle-current-20261101 -->

<!-- single-projection-current-20261101 -->
现役已完成一源状态投影优化及同方法60秒后测；真人对话测量尚未开始。startup `71c28c2d4a15585a0370790c9be62ab5c1d975d0ac70626613429d355e83bb87`、manifest `e35ec0e32bb5b4d5c17ce11396753bcb36ad13eb651c9d1c3f57d1d745786020`、380组件；唯一替换production_memory_presentation，当前四项相机/转轴配置、原相机430894、wide固件与v24记忆/人格/动画保留。GUI新owner为supervisor648043、GTK648047，完整birth/命令指纹见[实际发布与后测](E:/Win共享文件/语音共享文件/deliverables/2026-10-31_visual_axis_maintenance/reviews/joint_performance_20261101/CURRENT_PUBLICATION.json)。

后测保持main/角色可见/16fps、PAUSED/mic=false、follow=false及输出关闭。发布耗时和GTK CPU中位下降；原生绘制一次101.20ms长尾及视觉源龄波动完整保留，不宣称所有性能均改善。此前段落的startup/PID仅适用于各自保存时点；之后真人恢复聆听已获用户授权，须以新鲜状态回执为准。
<!-- /single-projection-current-20261101 -->

<!-- visual-axis-current-20261101 -->
原板端人脸随动已恢复，按用户反馈将方向修正为+1；短测后用户反馈“差不多额”。当前保存观测为READY/follow=false、输出关闭、1632µs，视觉页可再开启原跟随。语音仍PAUSED/mic=false。相机430894、supervisor496785、GTK496789；旧PID与FAULT/null状态已由本次读回替代。

startup `226b5a20f0089f5c534b1d540dd3605d805c17f7f1bd371a6ab5b3a4b287ad15`，manifest `8ff79452570385921e06c098b5d42c2ea1ef5dfb84d81dfa7f53a9295373d0e8`，GUI配置 `a695d620ddad3216de2d0447ec91d0e983a67343c2282179adece8014fccc063`，380项实读匹配。仅4项运行配置更新，原控制器25文件和全部Python/Native源码保持；v24记忆与人格/动画保持，R2未选作生产。

[最新实板交接](E:/Win共享文件/语音共享文件/deliverables/2026-10-31_visual_axis_maintenance/reviews/live_follow_test_20261101/HANDOFF.md)。按用户安排，本窗口本轮操作已结束，设备串行权暂留本窗口、主窗口只读。下次先新鲜核对完整指纹；以下旧轮次的PID、startup、FAULT和未实测声明属于历史，原证据不迁作本轮验收。
<!-- /visual-axis-current-20261101 -->

<!-- board-business-live-20261030 -->
- v24 现役保持，本次跟踪的记忆积压已清空
- 运行根 /home/root/aura-board-business-20261030/production-5259eab11e42af13。startup SHA 888faff24fef9d85ad75bbe19bc34d63956820ccd3e6dd3f674cfe4525ed0863，manifest SHA 6d9b0ee5c311288e07335841c3c9e42278e8564f8be860f68412f7c2c537d8a2，config SHA e0762cbfb88fd77238b5b1b3562fd00005bc505395867e96cfc8b1b6651fb135，380份组件。
- 现役为v24的d6e摘要提示单源修订。supervisor 330179、GTK 330183、原A相机 229296。最终观察前后380组件及同owner核验通过，后续操作先现读。
- 用户选择暂时保持暂停。现役READY和保存偏好为enabled=false、PAUSED、mic=false，界面可见。ASR 2线程、GTCRN 1线程与原8帧队列、GTK每5秒保活继续使用。自动迎宾关闭，机械FAULT/null和跟随关闭边界保持。
- 三次独立只读计数中，待处理用户原文38→13→0、待处理已播助手原文20→12→0、仍带待处理原文的失败摘要任务33→14→0，已提交摘要2807→2826→2879。2879属于单独清空计数的时点，最终90秒窗口仅记录进程计数。
- 历史181样本中的negation_missing拒绝和原文保留均真实保留。后续4分钟观察，待处理失败任务3→0，记录6次同批重试，间隔约10–54秒，LLM已接受请求累计1001→1010。随后已有积压经原校验继续处理完成。
- 最后90.029秒共46点，失败待处理0→0、LLM已接受计数1010→1010，推理active=false/pending=0全窗。worker completed 78→80、discarded 68→68，failure_streak=0、memory error=false，未新增拒绝。完成计数增加不等同模型调用增加。
- 最后窗口GUI运行故障0，头像控件可见投影首末为true，约2–12秒的6点投影未确认可见；false投影包含字段缺失、None或其它类型，原始值无法由该投影还原；视觉steps 5184→5440、errors=0。worker故障字段仍未提供，早期缺失默认0的值不能证明无异常。声纹尚未标定，新真人对话、扬声器首声和多小时稳定性继续待验。
- 用户确认此前切换过视觉页。已核固定源码show_page在视觉页隐藏portrait头像控件；这一解释合理，逐样点归因未确认。新31点主页面观察60.016秒，avatar_visible字段全程存在且为bool true，presentation_state=visible，nativeframes43388→44338，运行故障0，XSSstate=0、DPMSlevel=0，保持原600秒策略。结论为主页面软件状态正常，物理面板未观测。
- 显示维护已恢复原600秒策略和DPMS启用。此前同v24的31点被动观察有6次idle下降，最大4857ms，观察器复位0次。外部输入未排除，物理面板未观测。历史v21的635.886秒观察独立保留。JPEG对照存在场景与吞吐混杂，继续使用原A。
- 公开15样例经真实模型和两名assistant语义复核通过，最终R2有16次模型调用、0取消，原human_semantic_review仍为PENDING，容量301字节。v25冷却重试方案仅离线27项通过，未部署，gate=false且无APPROVED/实际spec。600秒冷却可能延后失败批次压缩，当前保持已清空积压的v24。
- v20功能与92项公开ARM证据按历史版本保留。两个旧测试模块依赖缺口、11个公共临时目录约10.3MB清理被自动审批拒绝的记录保留。
- 最终接续入口 E:\Win共享文件\语音共享文件\deliverables\2026-10-30_board_owner\integration\dialogue_repair\current_observation_v24_final_display_review.json。本次12入口改前原字节与证据在 E:\Win共享文件\语音共享文件\deliverables\2026-10-30_board_owner\integration\dialogue_repair\docs_state_v24_final_display_review，原docs_state_v24、docs_state_v24_final及全部中途失败记录保留。
<!-- /board-business-live-20261030 -->

<!-- archived-board-business-live-20261030-pre-v17-d74dc0f6b100 -->
以下旧段完整原字节保留为历史，仅适用于其原startup。
<!-- board-business-live-20261030 -->
- v16 当前接续：Paraformer Small 已生产接入并 READY，保留用户手动 PAUSED。
- 运行根 /home/root/aura-board-business-20261030/production-5259eab11e42af13；startup SHA bf6cdd70768ea5fac4e5be874a387f444c0834d67db5e7a2a744671d9019d63c；manifest SHA e488f45660e78904d04ba57fe4210e2bcf9eeffa6282219096e9d7b6115df718；378 份组件；config SHA 8c35161e766c53728c75c592a074845e35e01502e8438aaf649b4a8e078a6101。
- 保存观测 mono56590.97092797：IDLE/no playing，enabled=false、PAUSED、mic=false，GUI 故障0；supervisor1053004/GTK1053122，camera260102/birth784437，同boot 8100a7fd-0c6a-46c4-82b8-f874988a1521。下次必须现读，不能写已恢复自动监听。
- Small/3线程已选中；8个公开合成WAV各2轮的16次decode均值 old5.789s→Small2.057s 是背景有变化的筛选，非真人首声、准确率gold或端到端提速验收。用户接受同音字，姓名字形仍有限制；v16真人等待尚未重新验收。
- Windows保持现有27B/2048/120和OmniVoice16，LLM权重仍D:/AIModels；板端业务、存储、显示和统一五分钟时间轴不改。combined前端1线程/capture nice-10/原8帧保留；每包新鲜权限检查与完整ACK保留。
- 新进程armed/speech/submitted=0且capture snapshot不可用，不能证明v15采集故障已修复；v15连续采集/控制通过仅属旧startup，不能移作v16验收。
- 早期mono56240.522488149 memory completed11/discarded10、streak5、48s退避、脱敏error other；后续mono56590.97092797已完成29/丢弃18、error清空、streak0、clock safe_compaction=true。只证明后续恢复推进，未直接观测原错误枚举，原因和全库健康仍未确认；丢弃任务不等于删除源正文。
- frontend allocation候选A1通过、B1在原8帧队列pcm_input_queue_overflow，B2/A2停止，未部署且无收益结论；phasehold未部署。视觉/声纹路由后续修订不纳入本回执。
- 接续入口 current_observation_v16.json、paraformer_small_validation/v16_evidence 和 docs_state_v16/HANDOFF.json。本次接续文档修订只读封存metadata，未访问设备/模型/私库，未修改生产或候选代码；root此前实机发布与公开试验记录保留。
<!-- /board-business-live-20261030 -->
<!-- /archived-board-business-live-20261030-pre-v17-d74dc0f6b100 -->

<!-- archived-board-business-live-20261030-pre-v16-09c715c6d33f -->
以下旧段完整原字节保留为历史，仅适用于原startup。
<!-- board-business-live-20261030 -->
- 现役v15：/home/root/aura-board-business-20261030/production-5259eab11e42af13；startup SHA 67d03ca40d709d22d761706bfca51a55e352adf86763ced7fb5eb5a688123a55，378份组件；manifest SHA 8312169b6747d6f0e1c2c8a73c20ecee6cd7b949083f977871412a96390c2e73；config SHA faa5bead11f6c212412cf295db7d11c092c51848a5b08b49d78449ed613ba6d7未改。
- 恢复回执mono51155.430627971：IDLE/no playing、自动WAITING_SPEECH/enabled=true/mic=true，无唤醒词、半双工，GUI故障0；supervisor970372/GTK970411/frontend970467、camera260102/birth784437，同boot 8100a7fd-0c6a-46c4-82b8-f874988a1521。均是保存时点，下次必须现读。
- v15连续采集、优先级作用域、磁盘暂停false→恢复true、取消rearm、arecord释放及worker复用均通过；不代替冷启动/暂停重启/多小时长稳。
- 用户最新确认声音连续，仍认为等待过长：audio_continuity_user_confirmed=true、waiting_improvement=false；该次真人反馈的精确轮次耗时未取得可靠关联，不把后续THINKING的ASR数或旧ACK硬挂该反馈。扬声器首声尚未声学测量，不能宣布完整对话验收。
- 两段约8秒监听观察CPU83.98%→82.33%，仅-1.65个百分点；native完成计数速率3.37→6.27次/秒，不是屏幕物理FPS且未达16目标，不构成严格A/B或等待提速证明。
- 正式保持原Paraformer3线程、combined前端1线程/capture nice-10、原8帧；板端业务/存储/雪妃显示，Windows仅现有27B与OmniVoice16，权重仍D:/AIModels。两种新流式ASR未上线；合成意图107字对照差异3/7/12不是人工gold，CTC另有1秒credit失败。
- 最终恢复时本进程memory completed74/discarded1/streak0无error、capture failures0；不得与v14累计493等直接相减。跟随false、机械FAULT/null、身份与每包权限/完整ACK边界保留。
- 接续按语音项目根目录相对路径deliverables/2026-10-30_board_owner/integration/dialogue_repair/current_observation_v15.json及idle_cpu_integration/v15_current_note.txt读取；旧v14正文及文档原字节归档于docs_state_v15/before。
<!-- /board-business-live-20261030 -->

[后文历史归档省略；来源SHA针对完整原文件。]
