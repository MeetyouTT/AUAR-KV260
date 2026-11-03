<!-- board-business-live-20261030 -->
- v23 记忆摘要修订已发布，真实数据仍有校验拒绝
- 运行根 /home/root/aura-board-business-20261030/production-5259eab11e42af13。startup SHA d848dc90cf9a890fb8bc66b2c494b78c2ae39a7e22a4743fe0ab917ca3edbae8，manifest SHA 8e4d3a90f20520c518f28fa12cbf9093f17405f4d9ed2bb9edf2ac46890d496a，config SHA e0762cbfb88fd77238b5b1b3562fd00005bc505395867e96cfc8b1b6651fb135，380份组件。
- 本次更新两份记忆源码，378份其他组件与界面配置保持。supervisor 277913、GTK 277918、原A相机 229296。操作前现读owner。
- 用户选择暂时保持暂停，enabled=false、PAUSED、mic=false，界面可见。ASR 2线程、GTCRN 1线程与原8帧队列、GTK每5秒保活继续使用。
- 同一组11个公开样例经真实模型处理，机械通过由3项增至11项。第四版共12次调用，长记录分两片处理，摘要保留反复提问并消除了局部次数的范围误导。两名assistant逐条语义复核通过，原human_semantic_review仍为PENDING。容量301字节与原默认预算保持。
- 生产61样本观察至mono30560.689，完成4→7、discarded计数5→9，最终连续失败2次、退避6.0秒。真实数据仍在full_source_validation出现['negation_missing']，修复继续进行。计数属于本进程，完成批数不能推作模型调用次数。
- 失败批次原文在成功校验压缩前保留。61样本内GUI运行故障0、视觉steps189→369且errors0。worker故障字段未提供，早期缺失默认0的值不能证明无异常。声纹尚未标定，新真人对话和扬声器首声继续待验。
- 显示维护临时设置已恢复为原600秒策略和DPMS启用。当前31点被动观察有6次idle下降，最大5012ms，观察器复位0次。外部输入未排除，物理面板未观测。历史v21的635.886秒观察独立保留。JPEG对照有人数和吞吐混杂，当前继续使用原A相机，自动迎宾保持关闭。
- v20功能与92项公开ARM证据作为历史保留。两个旧测试模块的依赖缺口、11个公共临时目录约10.3MB清理被自动审批拒绝的记录保留。前三版摘要候选及首次验证程序失败回执完整保留。
- 接续入口 E:\Win共享文件\语音共享文件\deliverables\2026-10-30_board_owner\integration\dialogue_repair\current_observation_v23.json。本次12入口的原字节与证据在 E:\Win共享文件\语音共享文件\deliverables\2026-10-30_board_owner\integration\dialogue_repair\docs_state_v23，历史快照独立保留。
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
<!-- /archived-board-business-live-20261030-pre-v16-09c715c6d33f -->

<!-- archived-board-business-live-20261030-v14-53a84aea006e -->
以下旧v14当前段原文逐字保留为历史；仅适用于其原startup。

- 现役v14：/home/root/aura-board-business-20261030/production-5259eab11e42af13；startup SHA 39b102a4a505db491cf06b90e3a5232bfb656c79cb0a3c221551d76d414a9a0a，378份组件；manifest SHA a2545970650f60b95cdc6e4f0a31c234f37adb5f0662c9f04ded791352f53353；config SHA faa5bead11f6c212412cf295db7d11c092c51848a5b08b49d78449ed613ba6d7。
- 最终恢复回执mono47956.819：自动聆听enabled=true、WAITING_SPEECH、mic=true，IDLE、无播放、GUI故障0；supervisor887170/GTK887178，同boot8100a7fd-0c6a-46c4-82b8-f874988a1521。相机health metadata核对PID260102/birth784437。以上均为保存时点，不代替下次现读。
- v14实际暂停磁盘false→true、取消本轮rearm、麦克风/arecord释放及worker复用已通过；优先级作用域通过。continuous_capture_passed=false：采样期间有实际语音/轮次，不能冒填全quiet通过。冷启动/暂停重启、扬声器首声、真人等待满意度和多小时长稳仍未验收。
- 正式仍板端业务/存储/雪妃显示，Windows仅27B/2048/120与OmniVoice16推理；权重在D:/AIModels。无唤醒词、半双工；combined前端1线程/capture nice-10、原ASR3线程保持，未上线新ASR。跟随false、机械FAULT/null安全边界保留。
- 真人仍反馈等待太久，短回合首音频入队8.4–9.4秒不等于扬声器首声；小样本名字ABBA约19%仅模型调用局部结果。最终runtime累计采集失败1、memory完成252/丢弃23/streak0；361摘要/927积压是较早详细库快照，不能当最终全库计数或健康通过。
- root已完成本轮公开实机ASR对照与隔离流式候选测试；候选未上线，简记见docs_state_v14/current_note.txt。本次接续文档修订仅处理已保存metadata，未再操作设备/模型/私库或改生产/候选代码。当前证据固化于docs_state_v14/evidence_final，完整关联见current_observation_v14.json，旧文档原字节归档保留。

<!-- /archived-board-business-live-20261030-v14-53a84aea006e -->

<!-- archived-board-business-live-20261030-v10-dcb972fff97a -->
以下旧现役段逐字保留为历史，仅适用于其原startup；以上v14当前观测不继承旧验收。

- 板端正式业务当前入口：/home/root/aura-board-business-20261030/production-5259eab11e42af13；startup SHA 1129a2a7af2b401537710d1a67651c79961c1b10198f5625ae6802e7ac99fd77，375份组件，source manifest SHA c575f5fc8eb55536e4ea1a8b926d5843e54f2068337691bba7bab61c8a3f01a5。
- 本次实读supervisor 811772、GTK 811885、相机 260102、boot 8100a7fd-0c6a-46c4-82b8-f874988a1521；PID仅为本次观测，下次先现读。
- 已取消唤醒词门槛，就绪后自动聆听、直接说话即可，无需称呼或开始按钮；连续采集与优先级作用域两门槛均有真实通过回执。当前采用半双工：生成/播放期间不启插话采集，完整播放ACK后自动恢复聆听。实际暂停/恢复后的磁盘偏好false→true往返已核验；实际取消本轮后自动rearm已核验。未新增实际冷启动/重启验收声明。
- 采用的前端配置仅按最终installed回执记录：{"asr_threads": 3, "capture_priority_nice": -10, "frontend_capture_process": true, "frontend_optimization": "baseline", "frontend_process": true, "frontend_threads": 1}；不将此前候选或静态hash当作已上线。
- physical_microphone_opened=true；physical_audio_acceptance_passed=false。真人ASR、实际播放/听感/口型和长稳仍未验收；采集通过不等于整机语音闭环通过。跟随false、机械FAULT/null，真实业务库及身份权限保留。
- Windows继续仅模型推理，固定27B/OmniVoice16与其他模型保护不变；不恢复旧Windows业务写者。
- 生产诊断只保存白名单metadata，不归档正文/PCM/窗口截图。来源：integration/listening_entry_fix/actual_automatic-listening-v10-null-status-fix.json SHA 06eac613790ceb4bccd5b9c55ec5d0aa60fe5e06464326ac777fe29e1ec7a43e；integration/production_business_acceptance/actual_ready.json SHA 1299ddd9d42f886ea909faf6a3b30ea287acb8392eedf1373a7a06662fc21628；integration/listening_entry_fix/actual_live_listening.json SHA bc933c67f52c7d86997311254b3861eb4f08e76cb7be5fd0d0142f033ba72299；integration/listening_entry_fix/actual_control_semantics.json SHA 85d6ae8f83879f00f271be8874e04a000150b286369ab9ca310c99899bacdcb3。
- v10显示空值修复及语音保活的最终接续见deliverables/2026-10-30_board_owner/integration/dialogue_repair/STATUS.json和板端性能分配与优化计划.txt。用户已确认v7连接复用的一轮声音连续完整（239次检查平均7.43ms、1个欠载包、完整ACK），不扩展为v10新听音验收；v10实际274.383秒同一采集流无GUI故障/重开/新增采集失败，8帧队列峰值5。启动初期第1代另有1次队列溢出已恢复，必须保留这个待优化项。直接语音监听开启或播放时每5秒保活显示；暂停且不播放时沿用原600秒熄屏，10分钟无人操作尚未专门验收。

<!-- /archived-board-business-live-20261030-v10-dcb972fff97a -->

<!-- archived-board-business-live-1129a2a7af2b4015-50573f976fea -->
以下为本次更新前的历史现役段，已由上方新回执替代：
- 板端正式业务当前入口：/home/root/aura-board-business-20261030/production-5259eab11e42af13；startup SHA 8149545f55e940c771115554e2253d71f69bc5fd89443cd9290918289d90c276，375份组件，source manifest SHA 01de85c4eb7eb27e9f7398b4ee5daa9bf75633adc124b2aeb682bfbd91506893。
- 本次实读supervisor 804062、GTK 804172、相机 260102、boot 8100a7fd-0c6a-46c4-82b8-f874988a1521；PID仅为本次观测，下次先现读。
- 已取消唤醒词门槛，就绪后自动聆听、直接说话即可，无需称呼或开始按钮；连续采集与优先级作用域两门槛均有真实通过回执。当前采用半双工：生成/播放期间不启插话采集，完整播放ACK后自动恢复聆听。实际暂停/恢复后的磁盘偏好false→true往返已核验；实际取消本轮后自动rearm已核验。未新增实际冷启动/重启验收声明。
- 采用的前端配置仅按最终installed回执记录：{"asr_threads": 3, "capture_priority_nice": -10, "frontend_capture_process": true, "frontend_optimization": "baseline", "frontend_process": true, "frontend_threads": 1}；不将此前候选或静态hash当作已上线。
- physical_microphone_opened=true；physical_audio_acceptance_passed=false。真人ASR、实际播放/听感/口型和长稳仍未验收；采集通过不等于整机语音闭环通过。跟随false、机械FAULT/null，真实业务库及身份权限保留。
- Windows继续仅模型推理，固定27B/OmniVoice16与其他模型保护不变；不恢复旧Windows业务写者。
- 生产诊断只保存白名单metadata，不归档正文/PCM/窗口截图。来源：integration/listening_entry_fix/actual_automatic-listening-v9-ui-fault-diagnostics.json SHA 3549f181bdc3318f76e5a06c96662fe1e52ae502fef6e9a35133b78b62ffe5f4；integration/production_business_acceptance/actual_ready.json SHA 7bbd56a4752b232a81091de9c866610699f2b6ed6b60cb6e8a36e72867370f9e；integration/listening_entry_fix/actual_live_listening.json SHA 337331c58bcb12bb74f048cbe4f65da5164be0187c8ccbd9faa79d79e6110c03；integration/listening_entry_fix/actual_control_semantics.json SHA 8630c4e6d68c6b8d73bdf03f93c32a5d29746b9e6ce88fb74ddde72a5cf46ca4。
<!-- /archived-board-business-live-1129a2a7af2b4015-50573f976fea -->


<!-- archived-board-business-live-8149545f55e940c7-8ef275a9ccb2 -->
以下为本次更新前的历史现役段，已由上方新回执替代：
- 板端正式业务当前入口：/home/root/aura-board-business-20261030/production-5259eab11e42af13；startup SHA e9fca749489d1333e20c3df0fb0285086b1aaf938b2b7ffe8ee54e915928466d，375份组件，source manifest SHA b7972ae6770e48929439dfca4830dad596532c587dac9bc2c8e832105d64581d。
- 本次实读supervisor 781536、GTK 781635、相机 260102、boot 8100a7fd-0c6a-46c4-82b8-f874988a1521；PID仅为本次观测，下次先现读。
- 已取消唤醒词门槛，就绪后自动聆听、直接说话即可，无需称呼或开始按钮；连续采集与优先级作用域两门槛均有真实通过回执。当前采用半双工：生成/播放期间不启插话采集，完整播放ACK后自动恢复聆听。实际暂停/恢复后的磁盘偏好false→true往返已核验；实际取消本轮后自动rearm已核验。未新增实际冷启动/重启验收声明。
- 采用的前端配置仅按最终installed回执记录：{"asr_threads": 3, "capture_priority_nice": -10, "frontend_capture_process": true, "frontend_optimization": "baseline", "frontend_process": true, "frontend_threads": 1}；不将此前候选或静态hash当作已上线。
- physical_microphone_opened=true；physical_audio_acceptance_passed=false。真人ASR、实际播放/听感/口型和长稳仍未验收；采集通过不等于整机语音闭环通过。跟随false、机械FAULT/null，真实业务库及身份权限保留。
- Windows继续仅模型推理，固定27B/OmniVoice16与其他模型保护不变；不恢复旧Windows业务写者。
- 生产诊断只保存白名单metadata，不归档正文/PCM/窗口截图。来源：integration/listening_entry_fix/actual_automatic-listening-v8-ui-budget.json SHA 6852cb8e34c9dfb2ef85d0b5063910d5ff654ee176d3866492b39e5a35755876；integration/production_business_acceptance/actual_ready.json SHA d7f3fc3b96fd75a383d16ba49d43833f0f76c08c3cb24aed9d2a3ef7a0d32173；integration/listening_entry_fix/actual_live_listening.json SHA 5f5d646eb1d817bd05ddd9bbe4c4b7abe295901262f941c23cb802392860b986；integration/listening_entry_fix/actual_control_semantics.json SHA ac61f9f471db7a78383b21fac86942690f0b288ca6ea9943ddc3f9cd6ea888f4。
<!-- /archived-board-business-live-8149545f55e940c7-8ef275a9ccb2 -->


<!-- archived-board-business-live-e9fca749489d1333-1c7fbc366118 -->
以下为本次更新前的历史现役段，已由上方新回执替代：
- 板端正式业务当前入口：/home/root/aura-board-business-20261030/production-5259eab11e42af13；startup SHA 6301d969e2e0bef9c5337f0e36ea7545cd46c59c4b2e8d9d8ce729797ebc2edf，375份组件，source manifest SHA d4367967d525ede969d1d0f3697adb712ce4c07cd62a0ef75edde4f498481523。
- 本次实读supervisor 771802、GTK 771806、相机 260102、boot 8100a7fd-0c6a-46c4-82b8-f874988a1521；PID仅为本次观测，下次先现读。
- 已取消唤醒词门槛，就绪后自动聆听、直接说话即可，无需称呼或开始按钮；连续采集与优先级作用域两门槛均有真实通过回执。当前采用半双工：生成/播放期间不启插话采集，完整播放ACK后自动恢复聆听。实际暂停/恢复后的磁盘偏好false→true往返已核验；实际取消本轮后自动rearm已核验。未新增实际冷启动/重启验收声明。
- 采用的前端配置仅按最终installed回执记录：{"asr_threads": 3, "capture_priority_nice": -10, "frontend_capture_process": true, "frontend_optimization": "baseline", "frontend_process": true, "frontend_threads": 1}；不将此前候选或静态hash当作已上线。
- physical_microphone_opened=true；physical_audio_acceptance_passed=false。真人ASR、实际播放/听感/口型和长稳仍未验收；采集通过不等于整机语音闭环通过。跟随false、机械FAULT/null，真实业务库及身份权限保留。
- Windows继续仅模型推理，固定27B/OmniVoice16与其他模型保护不变；不恢复旧Windows业务写者。
- 生产诊断只保存白名单metadata，不归档正文/PCM/窗口截图。来源：integration/listening_entry_fix/actual_automatic-listening-v7-scoped-audio-check.json SHA ca348912d85c05beb27f655a87675f451a0c136e0dba99f3b22f426178080cff；integration/production_business_acceptance/actual_ready.json SHA 6ae249c79a3edae847ff8120c8604c2af2ba6488e6884c9ea2b37daa1318efe0；integration/listening_entry_fix/actual_live_listening.json SHA 799f445ebd9cb3d822747ed27090aa627bc4deee3f53f55d99ca4443c83c852b；integration/listening_entry_fix/actual_control_semantics.json SHA a525cec2976e5dea37fe04817ce202c7b5b12eff623e95ed0c7ab8ebc802af4a。
<!-- /archived-board-business-live-e9fca749489d1333-1c7fbc366118 -->


<!-- archived-board-business-live-6301d969e2e0bef9-4c8057a805ab -->
以下为本次更新前的历史现役段，已由上方新回执替代：
- 板端正式业务当前入口：/home/root/aura-board-business-20261030/production-5259eab11e42af13；startup SHA 698b757a8ede34d52ea1d6ec9894e80ac0ccf793109efb3dc0b06e94800a7f7b，375份组件，source manifest SHA b5379bebf67db5d1edac7ef3546f1031c777c8765fc5b5ad9bc4b35ef8f51635。
- 本次实读supervisor 756359、GTK 756438、相机 260102、boot 8100a7fd-0c6a-46c4-82b8-f874988a1521；PID仅为本次观测，下次先现读。
- 已取消唤醒词门槛，就绪后自动聆听、直接说话即可，无需称呼或开始按钮；连续采集与优先级作用域两门槛均有真实通过回执。当前采用半双工：生成/播放期间不启插话采集，完整播放ACK后自动恢复聆听。实际暂停/恢复后的磁盘偏好false→true往返已核验；实际取消本轮后自动rearm已核验。未新增实际冷启动/重启验收声明。
- 采用的前端配置仅按最终installed回执记录：{"asr_threads": 3, "capture_priority_nice": -10, "frontend_capture_process": true, "frontend_optimization": "baseline", "frontend_process": true, "frontend_threads": 1}；不将此前候选或静态hash当作已上线。
- physical_microphone_opened=true；physical_audio_acceptance_passed=false。真人ASR、实际播放/听感/口型和长稳仍未验收；采集通过不等于整机语音闭环通过。跟随false、机械FAULT/null，真实业务库及身份权限保留。
- Windows继续仅模型推理，固定27B/OmniVoice16与其他模型保护不变；不恢复旧Windows业务写者。
- 生产诊断只保存白名单metadata，不归档正文/PCM/窗口截图。来源：integration/listening_entry_fix/actual_automatic-listening-v6-prepared-guard.json SHA 524ca1e84dc555d053889604c93cdc4f19cc6aa5d5f01b107bfbb0a21b016f84；integration/production_business_acceptance/actual_ready.json SHA 3d81bec4ee4f294bd9f407a4dac1c04b53b3348e8d0e7bebf41916e18fd22eea；integration/listening_entry_fix/actual_live_listening.json SHA f4e9f59aa539bae142ccbebb448533c8b5e0cc98a9e6362ee92d64bc2ca7dd91；integration/listening_entry_fix/actual_control_semantics.json SHA e794b847258dcbd7fe048012614d432f451c8d4a016b6ad86f17fbf2e70d5c96。
<!-- /archived-board-business-live-6301d969e2e0bef9-4c8057a805ab -->


<!-- archived-board-business-live-698b757a8ede34d5-1c5b37f59e8f -->
以下为本次更新前的历史现役段，已由上方新回执替代：
- 板端正式业务当前入口：/home/root/aura-board-business-20261030/production-5259eab11e42af13；startup SHA 192861de11e3431736f306168230e63b087b81f05c5d20122d37f72d70698d48，375份组件，source manifest SHA bf0942f29fd051bb981ce770a67492c8ed45f6b1348b7b5ce73057eaea186588。
- 本次实读supervisor 743208、GTK 743212、相机 260102、boot 8100a7fd-0c6a-46c4-82b8-f874988a1521；PID仅为本次观测，下次先现读。
- 已取消唤醒词门槛，就绪后自动聆听、直接说话即可，无需称呼或开始按钮；连续采集与优先级作用域两门槛均有真实通过回执。当前采用半双工：生成/播放期间不启插话采集，完整播放ACK后自动恢复聆听。实际暂停/恢复后的磁盘偏好false→true往返已核验；实际取消本轮后自动rearm已核验。未新增实际冷启动/重启验收声明。
- 采用的前端配置仅按最终installed回执记录：{"asr_threads": 3, "capture_priority_nice": -10, "frontend_capture_process": true, "frontend_optimization": "baseline", "frontend_process": true, "frontend_threads": 1}；不将此前候选或静态hash当作已上线。
- physical_microphone_opened=true；physical_audio_acceptance_passed=false。真人ASR、实际播放/听感/口型和长稳仍未验收；采集通过不等于整机语音闭环通过。跟随false、机械FAULT/null，真实业务库及身份权限保留。
- Windows继续仅模型推理，固定27B/OmniVoice16与其他模型保护不变；不恢复旧Windows业务写者。
- 生产诊断只保存白名单metadata，不归档正文/PCM/窗口截图。来源：integration/listening_entry_fix/actual_automatic-listening-v5-half-duplex.json SHA c3c8cf0dcbdd452cbba0b756dd69fc3aa3bb2d65d1cc07a50221eb23b8f79675；integration/production_business_acceptance/actual_ready.json SHA 765770164fc3a39c4ab5fb5db0cc9d37337ae3f3095433e829b370fa10a9787a；integration/listening_entry_fix/actual_live_listening.json SHA d9708078589b49a36b1b8c2b352b698361e3b990f5bfeaab35fde79d57f8c1ea；integration/listening_entry_fix/actual_control_semantics.json SHA 400b14dd4141930696cca57d25bd3ac2df73331d93beadac280e2a39013a1981。
<!-- /archived-board-business-live-698b757a8ede34d5-1c5b37f59e8f -->


<!-- archived-board-business-live-192861de11e34317-319c442f5bad -->
以下为本次更新前的历史现役段，已由上方新回执替代：
- 板端正式业务当前入口：/home/root/aura-board-business-20261030/production-5259eab11e42af13；startup SHA 9e1f2b1cdc619766f5c3ba4fe82cf8849d147956416974d7011f4ccb5ecc7d46，375份组件，source manifest SHA af43ae6667d27b9a76a2f89778f26695c8222a7e1d483afb44febcbbabcd7034。
- 本次实读supervisor 726380、GTK 726384、相机 260102、boot 8100a7fd-0c6a-46c4-82b8-f874988a1521；PID仅为本次观测，下次先现读。
- 已取消唤醒词门槛，就绪后自动聆听、直接说话即可，无需称呼或开始按钮；连续采集与优先级作用域两门槛均有真实通过回执。实际暂停/恢复后的磁盘偏好false→true往返已核验；实际取消本轮后自动rearm已核验。未新增实际冷启动/重启验收声明。
- 采用的前端配置仅按最终installed回执记录：{"asr_threads": 3, "capture_priority_nice": -10, "frontend_capture_process": true, "frontend_optimization": "baseline", "frontend_process": true, "frontend_threads": 1}；不将此前候选或静态hash当作已上线。
- physical_microphone_opened=true；physical_audio_acceptance_passed=false。真人ASR、实际播放/听感/口型和长稳仍未验收；采集通过不等于整机语音闭环通过。跟随false、机械FAULT/null，真实业务库及身份权限保留。
- Windows继续仅模型推理，固定27B/OmniVoice16与其他模型保护不变；不恢复旧Windows业务写者。
- 生产诊断只保存白名单metadata，不归档正文/PCM/窗口截图。来源：integration/listening_entry_fix/actual_automatic-listening-v4-direct-speech.json SHA ebee9688ff02f0aea13c3d23c186b9e348189bcdec64c8a2727273a786ae22d0；integration/production_business_acceptance/actual_ready.json SHA 74d474f8dc22e7d353645a9f4516753d2078d40119de0266c0010609eb5b0b87；integration/listening_entry_fix/actual_live_listening.json SHA 469e2fd7c2a304f8a2c8f3a4657e77d2ecf6edf98409dae5b9872b3a93cc1cbb；integration/listening_entry_fix/actual_control_semantics.json SHA cc69a9502e7740be38ed9024bb3dcdedee368b742a01663e9be97b1b46af2819。
- 用户已要求取消唤醒词：正式入口为direct_speech，wake_word_required=false，wake_words为空。开机就绪后直接说话，首句仍检查有效音频、ASR及当前会话归属；角色称呼不再作为进入条件。身份权限、播放完整回执和防自收音保持；前轮ASR3线程、逐句TTS及模型常驻保留。实机自动聆听、暂停/恢复/取消和12秒连续采集通过，真人首句对话尚待现场验证。来源：integration/direct_speech_entry/STATUS.json。
<!-- /archived-board-business-live-192861de11e34317-319c442f5bad -->


<!-- archived-board-business-live-9e1f2b1cdc619766-36b73fbbb338 -->
以下为本次更新前的历史现役段，已由上方新回执替代：
- 板端正式业务当前入口：/home/root/aura-board-business-20261030/production-5259eab11e42af13；startup SHA 77f411c2365d2e0b07e827f508ad5e1c5f3f06ae64dd64f4af9885f79f830029，375份组件，source manifest SHA 815e996ae98156382d4794c2ba0140b886de0d1f2ffda43613ee3805bf3dc35c。
- 本次实读supervisor 710649、GTK 710653、相机 260102、boot 8100a7fd-0c6a-46c4-82b8-f874988a1521；PID仅为本次观测，下次先现读。
- 就绪后自动打开麦克风并聆听唤醒词，无需开始按钮；连续采集与优先级作用域两门槛均有真实通过回执。实际暂停/恢复后的磁盘偏好false→true往返已核验；实际取消本轮后自动rearm已核验。未新增实际冷启动/重启验收声明。
- 采用的前端配置仅按最终installed回执记录：{"asr_threads": 3, "capture_priority_nice": -10, "frontend_capture_process": true, "frontend_optimization": "baseline", "frontend_process": true, "frontend_threads": 1}；不将此前候选或静态hash当作已上线。
- physical_microphone_opened=true；physical_audio_acceptance_passed=false。真人ASR、实际播放/听感/口型和长稳仍未验收；采集通过不等于整机语音闭环通过。跟随false、机械FAULT/null，真实业务库及身份权限保留。
- Windows继续仅模型推理，固定27B/OmniVoice16与其他模型保护不变；不恢复旧Windows业务写者。
- 生产诊断只保存白名单metadata，不归档正文/PCM/窗口截图。来源：integration/listening_entry_fix/actual_response-latency-v2-capture-control-ack.json SHA e5c46839f58ccb6d4abf465c74cf7255610be17fac217b6b9b13923615664e06；integration/production_business_acceptance/actual_ready.json SHA f7b3b94fc98d6cbb50dc1546c7bff82728144bcb3a55a640d0d996d1e8b3cf1a；integration/listening_entry_fix/actual_live_listening.json SHA 20c011e4a86357c738626c37ac2b67ccbb29fbb0a1046035bfc75fb6599723a6；integration/listening_entry_fix/actual_control_semantics.json SHA 643943d883cc6cefa91f950b42fa041578b55136ec789c5cc0db3da2903428f0。
- 响应优化已部署：ASR显式3线程、普通回答逐句TTS交付、27B keep_alive=-1、失败摘要3→6→12→24→48→60秒退避；模型/权重/阈值/原8帧队列/完整播放ACK不变。公开5.614625秒录音在GUI关闭时2线程4700/4718ms、3线程3741/4283ms；三句同文本真实TTS首段可交付2037→676ms，非扬声器首音或整机通过。计时入口board_business.dialogue.latency；现场ASR/听感、长稳仍待验。Windows当前host 25836/TTS 8232/固定11435 daemon 26036（下次现读）；详见integration/response_latency/STATUS.json。
<!-- /archived-board-business-live-9e1f2b1cdc619766-36b73fbbb338 -->


<!-- archived-board-business-live-77f411c2365d2e0b-3ae2d011904d -->
以下为本次更新前的历史现役段，已由上方新回执替代：
- 板端正式业务当前入口：/home/root/aura-board-business-20261030/production-5259eab11e42af13；startup SHA ac9be342ffbf933a7e044e99f74ce6ddc45b947970f04741e3534744644bc1f7，374份组件，source manifest SHA 2d1218d2be4c5295d6f5d96380a369778949ccb0aa36e2a0179274579053f544。
- 本次实读supervisor 677377、GTK 677385、相机 260102、boot 8100a7fd-0c6a-46c4-82b8-f874988a1521；PID仅为本次观测，下次先现读。
- 就绪后自动打开麦克风并聆听唤醒词，无需开始按钮；连续采集与优先级作用域两门槛均有真实通过回执。实际暂停/恢复后的磁盘偏好false→true往返已核验；实际取消本轮后自动rearm已核验。未新增实际冷启动/重启验收声明。
- 采用的前端配置仅按最终installed回执记录：{"capture_priority_nice": -10, "frontend_capture_process": true, "frontend_optimization": "baseline", "frontend_process": true, "frontend_threads": 1}；不将此前候选或静态hash当作已上线。
- physical_microphone_opened=true；physical_audio_acceptance_passed=false。真人ASR、实际播放/听感/口型和长稳仍未验收；采集通过不等于整机语音闭环通过。跟随false、机械FAULT/null，真实业务库及身份权限保留。
- Windows继续仅模型推理，固定27B/OmniVoice16与其他模型保护不变；不恢复旧Windows业务写者。
- 生产诊断只保存白名单metadata，不归档正文/PCM/窗口截图。来源：integration/listening_entry_fix/actual_automatic-listening-v3-complete-capture.json SHA c0f609aed5632814d874fcb2f74832f5120c1f083ad31291fe1b67cc549f6fdc；integration/production_business_acceptance/actual_ready.json SHA 9b220da402abda01dda64d852d2e08f869b82f3a5873782d96bdb7d387a9f691；integration/listening_entry_fix/actual_live_listening.json SHA 97d3d500d655091fb0b5894a979b727b59bd206ce2993758fa57b5c9ce59e307；integration/listening_entry_fix/actual_control_semantics.json SHA 3b3da66fa9b148fe6d46b9dd7577769e0db73c221bcf4b8774b0621421e3057a。
<!-- /archived-board-business-live-77f411c2365d2e0b-3ae2d011904d -->


<!-- archived-board-business-live-ac9be342ffbf933a-863ec603a48d -->
以下为本次更新前的历史现役段，已由上方新回执替代：
- 当前最高优先状态：板端正式业务与真实记忆已接管，retention=true，真人音频尚未验收。先读deliverables/2026-10-30_board_owner/integration/PRODUCTION_BUSINESS_LIVE.json及板端业务正式接管与实测接续_20261030.txt。当前root=/home/root/aura-board-business-20261030/production-5259eab11e42af13，startup e34590df7ecd4f74046671c9458edd48ede45d1474b5fbeba63481edd4cb8759、368pins、manifest cd1844eff9681979f5be65e8b87a8cd376432c07fa91f5638c2987ec7d5e83e1；最后UI622241/GTK622245/camera260102（操作须现读）。下方4c788/304与f94角色单独上线均为历史，不再作为当前业务入口。

- 私有root=/home/root/.local/share/aura-board-business；真实311turns/239旧视觉、原3speaker库和key已导入，receipt8933586747fa9283e36e596ca8084fdc0572228fe87c54e02eaa6e0cc36ebf2c。唯一writer、正常新写入后receipt、关闭重开及真实后台摘要提交已核验；生产先摘要核验落盘再清正文，失败留队列，不得重新导入旧snapshot覆盖新数据。本轮C/board临时7文件snapshot均清除；既有原库/历史备份原地保留停写，不顺带删除。

- Windows正式8797无TTL，host16492/TTS26444/项目11435 daemon26036（须现读），固定27B/OmniVoice16；启动模型服务.cmd/start_inference.ps1；start_voice已转model-only，旧background/device启动入口受owner=board阻断。11434及其他模型保护保持，LLM存储继续D盘。看板能识别正式模型进程。不要恢复旧8791/8792/8795或Windows业务写者。

- 形象腰部构图/奶白藏蓝酒红/lib887546/978B人格保持。生产UI保存诊断/close仅private metadata、不截屏/归档原文；字幕300秒截止及更正/遗忘/压缩失效已接。实际麦克风/播放尚未开启，跟随false、机械FAULT/null；下一步用户按实机音频测试剧本前4句输入，不能把RAM PCM通过冒充真人听音/整机通过。

- boot当前8100a7fd-0c6a-46c4-82b8-f874988a1521。新boot需现读相机并通过integration/resume_camera_pin/rebuild_face_readback_pin.py重建私有readback、更新configpath/SHA/启动pins；原8c0/260102 pin不跨boot，不放宽模板/权限。receipt跨boot保留、时钟每boot新可信锚。原r3四settings/公共stage及xuefei-static-cues仍是依赖，旧目录不得按名称直接清理。
<!-- /archived-board-business-live-ac9be342ffbf933a-863ec603a48d -->




<!-- character-formal-selection-authorized-20261030 -->

- 最新外观已更新并实图检查：腰部以上近景、完整423×516角色区，奶白/藏蓝/酒红主题。当前同root的startup SHA改为4c78824ba9c1c04bb95389a49b64215a7f624a323becae637bc8d4e7c4db4d7e、仍304pins，完整manifest c575e94292cb605fb11db9f13d91b360d950908e2fe6c713dfe426f71b545891；原生库887546c09eb1897845c8d7f55a9e3f9b9c761448c7410f2b599259ae0b51efd2，仅3行projection变更，接口/依赖/模型纹理/人格不变。最后UI560251/GTK560316，camera260102（后续现读）。下文91dbe/539628是首次切换历史，后续发布必须合入appearance增量，不能再发初始26文件包或原788库。见构图配色调整_20261030.txt及integration/APPEARANCE_UPDATE.json；本轮无benchmark。

- 正式切换现已完成：当前板端root=/home/root/aura-character-xuefei-20261030/f94fca2c94288acb，startup SHA91dbe7229cf0e11afdcfa6ca5aca657dd7f95a2adfa9b3764a0df0d793f050e2、304pins；最后UI539628/GTK539632、camera260102（后续必须现读）。持久ExecStart已生效、enabled、native EGL出帧/visible/雪妃pair READY production_selected=true，临时guard移除；旧c413/286 root和下文‘未正式替换’均为历史，不再作为当前入口。回执deliverables/2026-10-30_board_owner/integration/formal_character_switch/actual_completed.json。

- 发布只换renderer/persona，现役legacy业务及原真实HOME/四settings/原stage路径保留，未启board_business候选空库、未迁真实库、未清正文。旧8792本轮仍未启动；Win默认future8792已选同978B人格r13，8797保持caller-owned消息。麦克风/监听/播放/跟随关闭、FAULT/null。依赖旧r3 runtime四settings和公共stage、candidate父目录下xuefei-static-cues-8222c2a0ff30471a均已成为正式依赖，不得随‘清理旧/候选目录’删除。

- 基础overlay f94fca2c...6cdc在启动时补了漏带的纯常量common/device_policy.py（SHA10abf675...e616），实际完整manifest bfdc28c7...fe7a0，以最终304pins为准，不能仅照原26文件ZIP重发。内部profile id沿用xuefei-yuki-board-v1-candidate，正式选择状态为true；本轮按用户要求未追加benchmark。更多见形象人格正式切换记录_20261030.txt。

- 用户最新明确授权：时间不足不再追加性能测试；依据已确认的新形象减负潜力，直接正式切换雪妃形象与配套人格，便于后续调试收尾。本条取代下文“仅规划/待用户决定是否切换”的历史限制。主控执行持久启动配置更新和必要启动/画面/人设检查，不开展新benchmark。

- 本次范围为形象/人格/称呼/唤醒/提示音成套切换；保留现役业务路径、真实HOME、记忆与身份权限，不将synthetic候选空库误作真实迁移，不启用生产正文清理。Windows模型only服务维持caller-owned messages，不为通用模型接口强加人格；旧8792业务人格入口同步配置供之后启动使用。

<!-- /character-formal-selection-authorized-20261030 -->



<!-- character-persona-candidate-20261030 -->

- 最新完整候选试验与恢复：阅读deliverables/2026-10-30_board_owner/character_persona_candidate/替换评审_20261031.txt。新r3 synthetic GUI实际EGL/形象人格配对/板端业务READY；两次nice0、原8frame队列、相机100ms公开管线通过（peak2/3，无溢出），人物计数0→1和0→0，非持续有人验收。空闲native swap15.83fps、额外公开音频探针下14.21fps，未过严格16fps，不正式替换。GUI组PSS含新业务，不能当纯渲染PSS比较。

- 两轮UI试验都已收尾，最终候选正常WM_DELETE退出，原c413/286pins恢复；最后UI487238/GTK487470、相机260102（后续现读），本轮自己的guard已移除、原unit属性恢复。原启动超过辅助工具90秒等待后已核验健康并单独完成guard收尾，无强杀/重复restart。当前生产仍原r3-ubuntu；真实库迁移/生产正文清理保持false。实际回执integration/resume_ui_trial_round2/actual_restore_finalized.json。

- Windows有界模型候选已正常关闭旧1df987...并启动新c684d464149148dfbf3f89c452db2ba3（8797、2小时寿命）；现状以integration/resume_live/latest_cycle.json与对应status.json为准，非永久生产服务。默认11434/项目11435及旧portrait8796保持；看板PID21456为本轮观测值。雪妃978B人格三组实际27B/OmniVoice16公开生成通过，未实际播放、未接真实库。

- Qwen 视觉旧模型实际清理完成：板端 fresh286pins 与上传停用证明通过后，仅删除 D:/AIModels/qwen3-vl-2b-interaction 内原 manifest/mmproj/GGUF 三份常规文件，共1552463811B；没有复制/归档权重，共享目录无新增入口。回执 deliverables/2026-10-30_visual_simplification/model_removal.json；下文“尚未删除”仅为历史，其他模型保持。

- 用户最新允许：确认新形象存在实际减负潜力后可以规划替换，且人格须同步调整。正式A/B已有renderer CPU约-20.05%/PSS约-189.24MiB、Mali约+32.58MiB，整板CPU收益仍不一致；现在可以推进成套候选与综合验收，不代表已授权静默正式替换。人物方案在deliverables/2026-10-30_yuki_native_validation/native_integration/replacement_planning/，板端完整人格候选在deliverables/2026-10-30_board_owner/character_persona_candidate/。

- 目标角色为御笠雪妃/YUKI MIKASA，中文短称雪妃；内向、努力表达取官方已核对资料，温和简短属项目适配。人格候选完整prompt978B（原1032B），原SPEECH_INPUT_HINT/MODEL_HINT/三字段及四emotion合同保持；新称呼、唤醒、UI文案与渲染同版本激活/回退，不改历史原话/用户姓名/身份key/既有音色参考。

- 相机100→200ms短测已完成并安全继承新checkpoint恢复原r17，当前观测PID260102（后续现读）；64z临时runtime drop-in已移除、原服务参数恢复，无强杀/旧seed回放。有人出镜时同权重FFT组合+仅自身nice-10两次公开采集/端点/ASR通过；正常nice0仍失败，显示帧率下降，不能当整机稳定通过。实测状态入口integration/resume_camera_budget/20261031T001356-finalize.json，旧1334和候选240801仅为历史。

- Windows看板已正常打开，源码/27项检查/实际LLM活动和GPU采样见deliverables/2026-10-30_runtime_dashboard/。主控仍持BUSINESS_ACCEPTANCE_EXCLUSIVE；子代理仅本地准备Yuki+板端业务GUI集成和新PID私有readback，禁止并发硬件压测/新模型。

<!-- /character-persona-candidate-20261030 -->



<!-- board-owner-resume-20261030 -->

- 本轮重启后已重新核对热点、aura-ubuntu SSH及板端boot8100a7fd-0c6a-46c4-82b8-f874988a1521；Ubuntu原Verysync用户服务已恢复并启用。生产仍r3-ubuntu，UI1296/相机1334（后续操作仍须现读PID，不把本条当实时绑定），未迁真实库、未启正文清理、未开麦/播音/运动。

- 复验入口deliverables/2026-10-30_board_owner/integration/RESUME_VERIFICATION.json。父合并回归538通过1个Windows/POSIX条件跳过；实际ARM可信HTTP Date、自然经过五分钟后真实27B摘要提交再删公开夹具正文、摘要检索与遗忘、实际27B→OmniVoice RAM链路均通过。真实用户数据库不在这些测试中，不能声称生产迁移已完成。

- 有人出镜时板端GTCRN/Silero的原8帧有界采集队列仍溢出，音频容量为当前硬门槛；加线程或仅提高自身优先级未解决。正在独立目录串行验证同权重缓冲优化、官方ORT1.19.2/NumPy1.26.4及既有face_source检测周期候选，不改系统包、不改模型或身份阈值、不扩大队列掩盖失败。五分钟清理仅公开夹具已验证，不针对生产库执行。

- 人物另一对话12轮正式资源A/B已结束并归还窗口；新人物内存降低明确、整板CPU改善不一致，未满足用户决定性条件，形象继续保留。旧人物本地16fps源码路径存在，但实际全业务负载验收未过，禁止静默退到8fps或替换人物。

- 用户新增要求Win后台模型运行演示界面，独立子代理windows_runtime_dashboard实现真实任务/进程资源看板；不启动推理或改模型服务。Windows候选模型端口8797为有界寿命测试实例，状态以resume_live/.../status.json实时记录为准；默认11434/其他模型不动。旧8791/8792/8795业务栈本轮尚未恢复，不能把端口8797验收当旧UI可直接对话。

<!-- /board-owner-resume-20261030 -->



<!-- board-owner-implementation-20261030 -->

- 本轮断电收尾完成，优先读deliverables/2026-10-30_board_owner/SHUTDOWN_HANDOFF.json。父合并回归271通过、1个Windows/POSIX条件跳过，最终30份源码/回归SHA见integration/final_source_manifest.json；此前各子代理“待跑”状态保留为历史，以父合并回执为准。五个现有生产库独立隐藏WMI只读quick_check均通过，未新增原文备份或迁库。

- KV260已正常停止项目服务、sync并收到Power down，UART echo已恢复；Ubuntu随后由用户确认正常关机。本机Windows由用户自行关机，代理没有创建或修改关机计划。人物临时fixture已退出，形象未替换。下一轮正常开机后重新核对热点IPv4、aura-ubuntu SSH、共享挂载和板端新boot/实际入口，不自动迁库、启正文清理或恢复未完成A/B。

- 用户已确认SSH/应用接入后要求直接执行最新梳理，并明确允许子代理并行加速；本轮已从只读规划进入候选实现与隔离验收。当前工作与证据入口为deliverables/2026-10-30_board_owner/IMPLEMENTATION_STATE.json。现役生产未切换、真实库未迁移；不能把候选实测冒作整机或实际听音通过。

- 最新板端已是r3-ubuntu（不是下文旧两次失败回退）：/home/root/aura-board-vision-20261030/06391079cfddb734-r3-ubuntu。新记忆/协议/ASR/声纹/FFT均在独立候选目录验证，按fresh实际入口及哈希合入，不覆盖其他对话修改。

- 用户明确人物形象替换的决定性条件：新形象需在同板、同分辨率/帧率/动作与业务负载的配对A/B中切实降低板端性能开销，再由用户确认是否替换。候选自身24fps稳定不等于资源收益；不自动替换、覆盖旧素材或切生产。与“分析冬之吻 Live2D 动画”对话协调，文件范围、性能窗口和单一发布者见本轮coordination/下的JSON；人物A/B期间不并跑其他板端压力测试。

- 板端wall clock被观测为2021年而证据主机为2026年，真实时间轴迁移前必须核验并使用显式可信的UTC/单调时钟策略；不得用旧系统日期清理生产正文。原麦克风/播放/跟随关闭及FAULT/null、身份跨机授权和其他模型保护保持。

- 候选收尾：history现新增search与精确topic分区分离，clear按授权scope原子清理并保留当前操作turn；个人范围收到“本次对话”限定时先拒绝，避免扩大范围。Worker默认max_events=2适配2048预算，单个过长turn仍不截断、未提交不得删。jobs必须注入timeline.event_time，记忆idle同时检查jobs.idle/controller.idle/可信时钟。以上最新search/clear/idle改动待人物独占窗口结束后统一回归，不能照旧通过数发布。

- 时钟源码传输曾被自动审批因仅元数据借窗范围拒绝，该借窗已归还且未开UART/传源码。本轮工具权限随后已更新，SSH再次通过；后续按当时的实际工具权限和明确的测试窗口执行。人物窗口现已进入pilot/A-B独占准备，实际旧系统日期、现役入口和真实库仍未改变。

<!-- /board-owner-implementation-20261030 -->



<!-- board-business-owner-20261030 -->

- 用户最新硬边界：所有业务信息处理、管理和持久存储在板端；Windows仅通过网线接收模型请求，运行现有27B与OmniVoice并返回输出。板端归属包括ASR、降噪/VAD、YOLO/跟踪/人脸/声纹、身份权限、上下文、五分钟详细记忆/长期摘要及检索、更正遗忘、压缩调度与清理、播放和动画合成。下文旧“保留Windows权威库、ASR/迁库后置”安排已被本条替代，不能当作最终方案。

- 后台记忆管理者运行在板端，空闲时请求Windows大模型生成摘要候选，再由板端校验、存储和清理原文。普通模型回复先回板端处理，再由板端请求OmniVoice。Windows不查询或持久保存业务记忆，不保留身份/声纹/视觉业务；仅模型资源、必要配置和请求内临时缓存属于模型运行范围。LLM权重/Ollama仍按既有约定留D盘，不能复制共享树。

- 主方案为../语言模型分析/统一时间轴记忆与稳定性优先_20261030.md，Ubuntu接续提示词已同步。当前实际仍有Windows业务模块和数据库，迁移没有完成；本次仅修订架构与交接，没有执行迁库、原文清理或新部署。分步验收不改变板端最终归属；保持单写者、安全移交、原较新记忆、相机/机械保护与既有授权边界。

<!-- /board-business-owner-20261030 -->



<!-- five-minute-summary-only-20261030 -->

- 用户最新明确：最近对话用压缩上下文保持连续；记忆用于追溯过去的行为和事件。近5分钟保留详细时间轴，5分钟前闭合内容由空闲后台任务标准化压缩，核验和保存成功后删除逐字原文；长期只留摘要和必要索引，不新增原文归档。方案入口仍为../语言模型分析/统一时间轴记忆与稳定性优先_20261030.md，Ubuntu接续提示词已更新。

- 管理者优先采用现有进程内低优先级后台任务，需要语义压缩时空闲复用现有27B，不新增常驻大模型、独立服务或Codex自动任务。对话优先，忙时超时原文只临时排队，未成功保存摘要不得先删。摘要清理后是长期历史记录，不再只是依赖原文的可重建缓存。

- 现有DigestWorker无模型摘录缓存及300秒情节分组不等于该5分钟机制。先解决长期摘要生命周期、正文与事件元数据分离、现有事实/来源引用及遗忘失效，不能直接按时间DELETE旧turns。本轮仅更新设计和交接，未清理生产原文、归档或备份，未部署新记忆机制；迁库、ASR迁移和视觉扩展仍后置。

<!-- /five-minute-summary-only-20261030 -->



<!-- timeline-stability-priority-20261030 -->

- 用户最新明确：重点把记忆统一进时间轴，当前梳理以简化、确保效果稳定优先。方案入口为../语言模型分析/统一时间轴记忆与稳定性优先_20261030.md；Ubuntu接续提示词已更新。近期复用现有记忆模块和Windows权威库，统一来源、写入/查询入口、当前事实视图及更正/遗忘/删除失效规则；不另复制全量记录，不新增记忆服务或检索模型，不跨端双写。

- 先解决遗留图片上传器停用及启动路径，再稳定原有对话/事实/播放状态的时间轴。核心稳定后仅接最小必要的结构化视觉事件；板端迁库、ASR迁移、视觉类别扩展和新模型后置。身份模板独立管理，既有授权与设备保护保持。

- 本次只更新方案和交接范围，没有新部署、迁库或设备操作；运行状态仍以deliverables/2026-10-30_visual_simplification/handoff_state.json及重新核验为准，不把方案更新当作上线完成。

<!-- /timeline-stability-priority-20261030 -->



<!-- board-vision-handoff-20261030 -->

- 用户决定移除Qwen视觉模型，改用板端YOLO/ByteTrack/人脸链；最新接续为deliverables/2026-10-30_visual_simplification/README.md、handoff_state.json、Ubuntu接续提示词.md。Windows现役voice-board-vision-20261030-r12已READY，8810关闭，旧图片接口410；下方r11是本次以前的历史，不按旧清单覆盖新源码。

- 160项当前源码回归、真实公开WAV的ASR/27B/TTS和原对话/视觉历史/声纹来源比较通过。旧视觉历史保留，但不作为当前画面注入普通聊天；声纹/身份关联、其他模型与端口保持。

- 板端停用图片上传器的两次候选发布均因stage.log仍指向旧运行根而自动回退；排除managed-runs后仍失败。最终原r11板端入口、286绑定、相机、机械FAULT/null及设置保持，监听/麦克风/跟随关闭，没有进行中的发布事务。用户明确要求Ubuntu接续；操作前重新核对实际入口，不重跑旧部署脚本，不放宽路径检查。

- D:/AIModels/qwen3-vl-2b-interaction权重尚未删除；remove_model.ps1未执行。结构化视觉事件统一落库、ASR和记忆迁板端均未部署。真实人脸摘要跨机验收的原待授权边界保持。本轮没有新自动任务或心跳。

<!-- /board-vision-handoff-20261030 -->



<!-- identity-gpu-r11-20261030 -->

- 最新身份/GPU交付：deliverables/2026-10-29_parallel_interaction/README.md、CONTINUE.md、PROGRESS.json；父代理已集成四份冻结子代理交付。Windows `voice-identity-gpu-20261030-r11`，指纹 `38544d0413af52c73c5d030271834b352bf3e1e25fc258be04b456989760368d`；46份源码通过。下方voice r9/r10及279pins为历史，不按旧恢复脚本覆盖。

- 当前板根 `/home/root/aura-identity-bridge-20261030/063ae6c47d2048d5a8e78111fc9484a9/runtime`，startup/config.json、286pins；相机1333/epoch保持，UI最后525685。实际操作仍须读/proc/MainPID与pending入口，不能按旧PID行动；保护并行启动器及机械FAULT/null/boot/FDT/固件/VART，不开麦、不播放、不运动。

- 637合并回归、三组真实非缓存语音、ARM公开PCM通道、真实库逐表严格相等通过，153会话/311轮保持。共享目录只放哈希/报告，真实备份留AppData；不恢复旧库。

- **实际人脸摘要网络验收自动审批拒绝，缺少载荷/目的地明确授权。用户批准板卡身份ID/模板指纹送Windows192.168.50.1:8792前，不运行verify_arm_bridge.py或用间接路径发送同类真实数据，也不启动会自动提交该数据的真人验收。** 公开PCM替代不含这些数据，已通过但不代表跨模态身份通过。详见approval_pending.json。

- aN临时声音/明确记住本人/原face+voice回执关联已部署，speaker_calibrated=false，候选不等于已确认身份或个人记忆权限。自动相机来源重绑定未实现，重启后失败关闭，禁止放宽来源检查。

- GPU adaptive/enforcing，固定项目11435子进程fit-target4096，最终最低观测1656MiB；非物理隔离/永不OOM或整体提速保证。默认11434及其他模型保留，D盘LLM存储不变；冷启动原300秒/只读容量/唯一实例锁，不能自动卸载其他模型。详细实测及失败历史见交付。

- 无新自动任务；后续真人声纹标定、真实身份链路授权验收、听音长稳及严格说话16fps仍待验。

<!-- /identity-gpu-r11-20261030 -->



<!-- audio-animation-polish-20261029 -->

- 最新音频/动作交付：deliverables/2026-10-29_audio_animation_polish/README.md、CONTINUE.md、PROGRESS.json；已部署并过自动验证，真人听音待集中复测。原同步GLib stdout阻塞改为有界非阻塞IPC，受控ARM供音199.98→24.57ms且PCM完全相同；真实UI静音长句18.28ms/0欠载/0重排。不能冒作用户原现场声学A/B或整机完成，自打断按用户反馈已不再发生，未调整识别阈值。

- 恢复四套既有身体、同语义短轮素材选择及对应39帧眼嘴几何，点头/摇头/惊讶/疑惑保持。58音频+1平台跳过、15素材、41画面协议分组通过，不与历史总数累加。说话约15.445fps/P95~80/P99~158ms仍未过严格16fps长帧门槛；断线实际7.934fps本地回退并恢复16fps。

- 现役板端/home/root/aura-audio-animation-20261029/2a62bf25b0994029a1ff0f23f0b9720e/runtime，startup/config.json布局、279绑定；Windows画面revision 763d0b05a67a79ff6f8a6d9d5e2a67cc9cc060181499cef7a416bccdf7315bac，正常入口start_portrait.ps1及aura/config/portrait_host.local.json。旧81fd/2026-10-27启动与服务恢复脚本为历史，禁止直接覆盖新入口；voice r9/5a4fa28e8679ffd24b61e940455e7dd2341c02c8ae70e8997aa5682c157471f3保持。

- UI监督器218804，相机1333/epoch保持，并行startup-speed启动器字节/参数及所有旧覆盖保持。仍须每次读/proc实际入口及pending unit、双确认空闲，禁止按旧目录或旧PID切换。机械benchmark/wide不匹配FAULT/null保护保持，不改boot/FDT/固件/VART或MMIO、不恢复旧1604µs。

- 独立WMI逐表原始来源严格相等，153会话/311轮及视觉/声纹保持（仅本轮时点，后续重新备份），没有回滚私有库；其他模型与非8796服务PID保持，LLM仍D盘。监听/麦克风/跟随关闭、音量70/未静音；不自动开麦/有声播放/运动。迁移后置，无新心跳或代理。

<!-- /audio-animation-polish-20261029 -->



<!-- windows-services-recovered-20261029 -->

- 最新运行恢复与重启后核对：deliverables/2026-10-29_service_recovery/README.md、CONTINUE.md、PROGRESS.json。Windows七类服务已恢复现有r9，源码指纹5a4fa28e8679ffd24b61e940455e7dd2341c02c8ae70e8997aa5682c157471f3不变；两轮实际ARM语音请求通过，无开麦/实体播放/成功ACK。原模型进程及D盘LLM存储保持，未新建自启/计划任务/心跳。

- 当前board boot 605eaf50-c66a-4559-bfc9-5ae177e0f305，UI1296/相机1333。实际运行仍/home/root/aura-boundary-nav-20261029/gui-page-sync-v2/startup/config.json，运行根/home/root/aura-boundary-nav-20261029/gui-page-sync-v2/runtime、279组件匹配；并行任务改了下次启动配置/home/root/aura-avatar-startup-speed-20261029/config.json，已保留。必须同时读/proc/MainPID/cmdline与systemd，不能仅把daemon-reload的新unit当实际运行入口，不能回退并行更新。

- 板卡重启后为benchmark FPGA/VART，实际驱动要求aura-visual-servo-b4096-wide-v1，boot/FDT/固件/VART四项不匹配，转轴FAULT保护停用/脉宽null，无MMIO。下方旧READY1604/旧boot已是历史，不能照抄恢复；本轮只核对，不改绑定、不切固件、不运动。监听/麦克风/跟随关闭。

- 当前144会话/276轮、183视觉历史及声纹源表SHA保持。实时缓存188→187为原24小时策略自动移除1条过期记录，其余行完全相同；严格相等初次失败及独立过期证明均保留。不可称所有表未变，也不能恢复旧77/73或143/273。真实私有库仍用隐藏WMI，备份留AppData。

- 本轮服务恢复和核对完成，机械未复机，整机仍未最终验收；用户先完善Windows对话/记忆、迁移后置的方向保持。后续机械须协调DPU与并行任务并成套核对wide固件/VART/发布与实体位置，禁止只改boot放宽保护。

<!-- /windows-services-recovered-20261029 -->



<!-- chat-memory-r9-20261029 -->

- 现役Windows voice-chat-memory-20261029-r9，指纹5a4fa28e8679ffd24b61e940455e7dd2341c02c8ae70e8997aa5682c157471f3。最新接续deliverables/2026-10-29_chat_latency/README.md、CONTINUE.md、PROGRESS.json。下方r6/r4等为保留功能的历史，禁止按旧指纹覆盖；r7格式提示未提速已撤回，r8中间版已升级。

- 普通“今天有点累”不误触时间轴，明确历史查询保留；日期API/删除/个人权限/记忆容量/来源保护与r6取消交接不变。新增完整请求摘要及格式计数，不记录原文。TTS完成后归还空闲CUDA缓存，首次就绪观测约2.71GiB，活动张量/模型、音色/16步/原超时保持；不能直接称整体提速。

- 355相关回归、最终14步实际记忆、5项ARM取消接话/唤醒及8次最终语音测量通过。首轮r9模型驻留变化导致性能失败的8次保留不计入最终统计；缓存/未缓存及长会话单列。普通聊天稳定延迟和长尾仍未验收。

- 精确公开测试CID已清理，原144会话/276轮、77观察/73视觉事件及声纹来源逐表SHA保持；独立隐藏WMI真实私有库视图约定继续。只重载8792/TTS，其他模型/端口、板端代码/279绑定/UI114923/相机21824/READY1604µs保持，迁移暂缓，LLM数据留D盘。

- 本轮经原UI暂停监听，最终监听/麦克风/跟随关闭；不要按下方旧“监听已开启”自动开麦。实体听音/说话长帧、短词即时唤醒、声画归属/现场声纹、跨天长稳和整机仍待验，无新自动任务。

<!-- /chat-memory-r9-20261029 -->



<!-- voice-handoff-fixed-20261029 -->

- 现役Windows已更新为voice-turn-handoff-20261029-r6，指纹b991e72050af52d86e947594303fc30e5a5675aa2a95140ff7910ba8a0d582a8。最新故障交付入口deliverables/2026-10-29_listening_bounce/README.md、CONTINUE.md、PROGRESS.json；下方r4是此前记忆交付历史，r4功能完整保留，不能按其旧指纹/脚本覆盖r6。

- 用户报告识别后回聆听：查到取消清理期间503立即拒绝。r6受原请求预算约束，最多等待5秒交接；已开始的OmniVoice合成在原时限内完成后丢弃旧结果，保留暖态进程。不要重新提前退出TTS等待而触发所属进程退役，也不放宽TTS时限。r5首次实机失败与恢复助手uuid遗漏均已保留，最终r6通过285项回归（含旧267）、板端3种取消接新问及2项唤醒协议检查。

- 初次暂停时原143会话/273轮、77观察/73视觉事件及声纹来源逐表哈希保持；保留用户此前现场新增数据，不能恢复旧141/269或6/2快照。私有WMI文件视图与备份约定保持，公开PCM仅RAM接收、无CID/成功ACK，不需清理用户记录。

- 只重载8792/TTS，其他6个模型所属进程与其他端口、compact_grammar=false/其余五项true保持。板端代码/279绑定/界面/相机不改不重启；READY/1604µs、跟随关闭。监听已通过原UI暂停，交付时仍关闭；不自动开麦/播放/运动。用户手动开启后用完整“汐蓝，你好”复测；单独叫名回聆听是正常唤醒，未命中唤醒也会回聆听，不能将所有情况都算503。

- 实测下一轮首PCM4.842/8.085/4.690秒，未证明聊天提速。真人原话复测、短词唤醒、说话长帧、声画归属/声纹标定与整机长稳仍待验。Windows对话/记忆优先、迁移后置，LLM数据留D盘。没有新自动任务。

- 用户随后明确“没问题额”，确认本次退聆听故障复测正常，仅限该问题；记录见deliverables/2026-10-29_listening_bounce/human_feedback.json及overall_status_after_user_confirm.json。当前监听已由用户开启，短采样WAITING_WAKE/麦克风true，最近现场回答完整播放ACK成功。其余整体待验项保持，不能扩大为整机通过。

<!-- /voice-handoff-fixed-20261029 -->



<!-- memory-first-user-direction-20261029 -->

- 用户最新明确：先不要将这些功能迁到板卡，继续完善Windows对话和记忆并验证效果。迁移暂缓；保留当前板端部署、人脸DPU/机械及其他模型，不能自行接管PS数据或重启板端。

- 当前交付入口：deliverables/2026-10-29_dialogue_memory_polish/README.md、CONTINUE.md、PROGRESS.json。Windows r4已部署：自然当前事实直答、中文/数字1—32条历史完整浏览、旧写入/导入来源自动保守保护；267项Windows相关回归（含旧210）、12步实际记忆、7项普通语音功能、板端已有ARM客户端两轮网线请求通过。无ARM pytest、开麦/实体播放/成功ACK；整机未完成。

- 保留并行compact_grammar=false与其他五项true，当前voice-dialogue-memory-20261029-r4指纹1ed519dc5d287a344019beca4212f588aa9d41dcafebabf867466232346b3de2。只重启8792及TTS，其他模型/端口、板端279绑定及READY/1604µs保持。人脸主链仍板卡DPU。原141会话/269轮、6观察/2视觉事件和声纹来源逐表哈希保持，公开测试行清理完毕；独立WMI读取真实私有库。

- 同录音/同会话同明确事实，重复查询首PCM中位数2.656→0.110秒（改后3次TTS缓存命中）；首次双方未命中缓存的单次4.641→1.453秒。仅证明当前事实路径收益，不能称27B或普通聊天提速。普通聊天对照改前4.640/3.109、改后5.593/6.625秒，原因未确认；前端1/330帧>20ms，严格门槛未通过。

- 版本历史为录入时间，非实际生效时间；默认语音列最近两条摘录，索引读取完整存储值。删除默认当前会话，个人范围须授权，预览60秒确认及原上限保持；不删除视觉/备份。r4完整来源标记包含空上下文，缺标记且无边的旧/导入/回退写入回复自动保守停用相关召回，不再仅依赖legacy_cutoff；这替代r3需人工重建旧截止的要求，不能给未知旧行伪造来源。

- 整个记忆路线与整机真人验收尚未完成。普通聊天长尾、实际生效日期、跨天真人体验、短词唤醒、说话长帧、声画归属和现场声纹标定待后续，迁移继续暂缓。r3历史证据仍在deliverables/2026-10-29_memory_controls，不重跑其部署脚本。

<!-- /memory-first-user-direction-20261029 -->



<!-- runtime-ownership-audit-20261029 -->

- 最新实际功能归属核对：deliverables/2026-10-29_runtime_ownership/ownership_catalog.json及runtime_inventory.json，16类功能、7个Windows服务入口。检查只读，无重启/模型加载卸载/开麦播放/运动或身份内容读取。

- 重要更正：当前相机独立启动覆盖的人脸主链为板端DPU_SFACE_INT8，ready且有实际处理计数；Windows8792的SFace CPU服务虽ready，当前进程processed=0，不应写成现有人脸主链仍在Windows。两端model_id不同，不直接互换模板。GUI默认board_identity配置不能代替实际相机覆盖。

- Windows仍负责GTCRN+Silero、人声转文字、27B/OmniVoice、语义视觉、对话/权限/上下文与权威记忆/情节日摘要、声纹ECAPA及模板管理、CPU动画合成。板卡负责采集/交互/播放/显示/人脸与转轴。8791和8792内部各加载Paraformer，后续评估精简前保留所有调用者。实际机械脉宽后来为1604，本任务未改；不要恢复旧1576基线。

<!-- /runtime-ownership-audit-20261029 -->



<!-- timeline-summaries-deployed-20261028 -->

- 最新接续：deliverables/2026-10-28_timeline_summaries/README.md、CONTINUE.md、PROGRESS.json。用户最新明确“可以实际部署了”；r2 / device-timeline-v2 已提交，169 Windows / 64 ARM相关回归、4项实机摘要和7项语音检查通过，互有重叠不累加。下方“候选未部署/等待测试结束”属于历史。

- 实际画面进入日摘要、板卡历史语音请求、单探针删除、迟到ACK拒绝与普通语音取消恢复通过；无开麦/声音播放。Windows权威库原始来源逐表哈希保持，私有备份使用独立WMI生产文件视图。对话280/视觉2条持久摘要，后台无模型推理；PS权威库迁移、事实时间变化、日期主题删除和跨天真人验收未完成。

- 本次保护并行任务的新入口 /home/root/aura-boundary-nav-20261029/gui-page-sync-v2/runtime，279项绑定，boot55152f95-ea3a-4c6c-82e6-51bd553d96fd，UI114923/相机21824不重启。机械READY/1576µs、跟随/监听/麦克风关闭、IDLE_READY、音量70保持；下方旧0cd7/277/FAULT不能沿用。下次必须动态重查，禁止用本次boot/PID覆盖后续更新。

- 首次冷启动300秒超时回退，第二次约144秒就绪，期限未放宽；冷启动波动仍待观察。当前voice进程使用本交付diagnostic_voice_entry.py，就绪后调用栈计时已取消，保留入口文件。其他5个模型所属进程及D盘LLM/Ollama保持。整机短词唤醒、说话长帧、声画归属和现场声纹/听音/长稳仍待验；不得称整机全部完成，无新心跳。

<!-- /timeline-summaries-deployed-20261028 -->



<!-- timeline-memory-deployed-20261028 -->

- 最新时间轴交付：deliverables/2026-10-28_timeline_memory/README.md、CONTINUE.md、PROGRESS.json。Windows voice-timeline-20261028-r1 / device-timeline-v1 已提交，语音和视觉按时间/主题检索，派生回复遗忘、实际重启保留通过；144 Windows/39 ARM互有重叠，不能累加。

- 新视觉事件最多30天/10000条，旧实时缓存仍24小时同boot；只存文字，采用Windows接收UTC/配置America/Los_Angeles。个人历史仍须原档案授权。后台日摘要/事实时间变化及权威库迁PS尚未完成；不得称整个记忆方案或整机已完成。

- 板端代码/入口未改，仍0cd7…/runtime及277校验。期间另观测板卡重启，最后严格复核boot55152f95-ea3a-4c6c-82e6-51bd553d96fd、相机PID1332/epoch42b41d1e45794b64bd2b7b16b2b28dca；每次必须动态重查，不能更新机械绑定来适配旧boot。

- 最后监听/麦克风/跟随关闭，IDLE_READY、音量70/未静音，机械FAULT/位置null保持。原短词唤醒、说话长帧、声画归属和现场长稳仍待验。其他模型及D盘LLM/Ollama存储保持。

- 私有设备库的真实文件视图须使用与服务一样的WMI独立进程检查；当前工具直接读取同名AppData路径可能是影子副本。实际表、升级后私有快照及重启同事件已核验；不要把早期影子视觉库快照当真实升级前备份。真实库/模板/图像不进源码包。

<!-- /timeline-memory-deployed-20261028 -->



<!-- device-skills-deployed-20261028 -->

- 最新部署与接续：deliverables/2026-10-28_device_skills/README.md、CONTINUE.md、PROGRESS.json。板端正式根 `/home/root/aura-device-skills-20261028/0cd7c3445a84475098b938d5b97175e0/runtime`；Windows `voice-device-skills-20261028-r6`，下方“候选未部署”等均为历史。

- 最后连接状态：板端与Windows已只读核验。

- 语音独立于视觉；汐蓝实测唤醒通过。15秒观察摘要、实时视觉问答、历史回忆、原人脸确认入口、三段声纹确认/取消以及入镜招呼已接通。220 Windows/71 ARM 回归互有重叠不能累加；真实ASR/LLM/TTS与取消恢复通过。哎/欸合成输入失败，独立KWS也漏检/误报，未启用；即时唤醒未最终验收。

- 待机约15.93fps门槛通过；说话15.85fps/P95 113.69ms/P99 168.91ms仍未过严格门槛。声纹未现场标定、无自动个人记忆解锁；真人听音/插话/入镜社交、声画归属和长稳待验，不能称整机全部完成。

- 当前boot `50b4fef1-9748-43c7-92bf-3040db8c994e`，相机PID 1350、epoch `2820a3f83216460ab65342a73f363d06`；原部署boot/PID保留在历史证据。监听/麦克风/跟随关闭、IDLE_READY、音量70；机械FAULT/位置null保持。用户已有停止跟随后部署授权；后续须重新读实际状态并保护并行机械更新，禁止只改boot放宽绑定。

- 其他模型和D盘LLM/Ollama存储保持。外设数据库位于用户私有目录；源码包不含模型/密钥/身份库或现场影像。没有创建新心跳；旧等待心跳已删除。

<!-- /device-skills-deployed-20261028 -->



<!-- voice-first-candidate-20261028 -->

- 用户最新明确：语音独立于视觉；不入镜也能由“汐蓝/欸/哎”唤醒、连续接话和插话，视觉仅作补充。候选及接续见 deliverables/2026-10-28_interaction_completion/README.md、PROGRESS.json。159 回归通过、2 原生依赖跳过；VAD+ASR 唤醒尚非已验收的即时 KWS。入镜“嗯？”/4 秒主动招呼仅事件策略完成，未接声音；Windows/板端正式程序未部署这些候选，不能称整个交互完成。

- 最新只读 boot eeee0494-077b-43d5-9b31-f78aa1d30451，实际根 /home/root/aura-system-pan-20261028/gui-continuity-v1/runtime，跟随 false、机械 FAULT/位置 null、监听设置 true/麦克风 false、IDLE_READY、显示约 8fps。下文旧正式根、旧 boot 和位置不能沿用。再次部署需核对实时入口/源哈希/静止空闲，保护并行机械更新；不恢复运动、不放宽精确绑定。用户已有停止跟随后部署授权。



<!-- consolidated-interaction-20261027 -->

- 最新正式根/home/root/aura-windows-portrait-20261027/handoff-31b0c262c5b74d52966c00b978dfef3f。报告deliverables/2026-10-27_final_interaction/README.md：恢复Windows服务，远端RGB先送显后UI快照、按实际fps记录性能；50 Windows/69 ARM专项互有重叠，实际待机16fps、静音PCM/暂停恢复取消/新轮与公开录音真实链路通过。SPEAKING严格门槛：False，不能当长期真人验收。

- 当前boot 230ae5f0-997b-432b-a738-0065c0cb5238，机械FAULT为精确board/boot/firmware/VART不匹配，no MMIO，位置null；禁止按旧boot或旧1400/1422更新绑定、恢复运动。跟随/麦克风关闭、访客、音量70恢复，其他模型与D盘存储保持。用户要求最后集中验收，全部项目尚未完成；现场听音插话/机械/声画归属/视觉问答与长稳仍待处理。



<!-- interaction-polish-final-20261027 -->

- 最新交互GUI：/home/root/aura-windows-portrait-20261027/interaction-12c755dad3b04d78a4d5e70a66a9872a，报告deliverables/2026-10-27_interaction_polish/README.md。只改状态/麦克风引导/实际送显帧率/独立语音配置显示，隐藏GTK与原16fps门槛通过，核心和机械配置保持。不能按下方旧入口覆盖。

- 用户本轮再次授权停止跟随后已通过UI退出，当前位置1400保持；跟随/监听/麦克风关闭、访客、音频就绪。相机/检测就绪但无确认目标。其他模型及D盘存储保持，整个玩偶未全部完成，持续实聊和新版真人验收仍待进行。



<!-- windows-portrait-final-20261027 -->

- 本轮Windows CPU画面已正式部署为16fps，最新根`/home/root/aura-windows-portrait-20261027/layout-4fca8de03dc84c989f84d7814a984bd3`；详见deliverables/2026-10-27_windows_portrait/README.md与CONTINUE.md。12/16通过，24的P95/P99未通过，保持16；实际UI断线本地8fps及恢复通过。设置页布局修复已独立隐藏GTK/截图/实际16fps验证。核心旧回归48/67与362互有重叠不得相加。

- 用户明确授权停止跟随后已安全退出，最终跟随/监听/麦克风关闭，访客，IDLE_READY，音量70恢复；当前脉宽1422仅本次证据，不可覆盖后续更新。automation心跳已工具删除。下文“正式8fps/等待跟随/未部署”均为历史记录，以上述交付为准。

- 静音真实PCM/口型通过，SPEAKING约15.525fps/P95约99.57ms仍不满足严格16fps间隔，真人听音/插话和持续实聊待验；全部玩偶任务未完成。其他模型保持，LLM数据仍D盘，HDMI排查暂停。



<!-- windows-portrait-resume-20261027 -->

- 用户最新明确回答“允许停止跟随并继续部署”。已通过现有UI pan_stop安全停止持续跟随并确认退出，脉宽1422保持，跟随关闭/READY/IDLE_READY/监听false。旧等待约束由本次明确授权更新；停止已执行，不要重复开启或恢复运动。等待心跳automation已删除，当前主动执行单sink画面部署。



<!-- windows-portrait-implementation-20261027 -->

- Windows CPU画面实现与证据：`deliverables/2026-10-27_windows_portrait/README.md`，接续必读`CONTINUE.md`。单请求/最新帧、PCM归属/取消/150ms期限、单native sink、断网本地8fps回退和可切换入口已实现；Windows最终48、ARM初次完整362过1跳过、最终专项67过，互有重叠不能相加。隐藏GTK和实际主机进程断线/恢复通过，均不代表实际高帧显示验收。

- 原生候选首次因额外本地等待导致帧过期已回退，修复与专项通过；后续未切换，因为用户明确“保留跟随，等待当前测试结束”。禁止pan_stop、pause_follow.py、杀跟随或跟随开启时重启UI。duration_s=0持续模式，SOURCE_HORIZON_ENDED不是整个跟随已结束。两分钟当前聊天心跳只读等待，结束后重新核对源/入口/boot再做12→16/24实屏验收。新候选尚未COMMITTED，正式仍8fps；下方d6d相机PID54394等为历史。

- 实际正式根以最新follow_wait_state.json为准，目前`/home/root/aura-pan-current-20261024/da36c36a/gui-reference-bound-v2`，音频就绪、监听false；不要恢复历史pan脉宽或覆盖并行机械更新。所有其他模型保持运行，LLM权重及Ollama继续D盘，无模型/图像复制。Windows start_voice.ps1已接画面服务，可用-WithoutPortrait跳过，未设系统登录自启。

<!-- /windows-portrait-implementation-20261027 -->



<!-- animation-dialogue-auto-20261026 -->

- 最新接续证据 `deliverables/2026-10-26_animation_dialogue/README.md`：板端正式UI已COMMITTED至 `/home/root/aura-animation-dialogue-20261026/d6d1617467724213b3d9fd3d11530a47`，30z独立覆盖，原入口/旧覆盖保留；加入个人记忆按钮及纯情绪等待可听回答，默认访客，监听false/无开麦保持。Windows已恢复并核对r3、8791/8792 HTTP及8795帧协议；原27B/OmniVoice16和D盘存储保持。303项Windows/27子测试；ARM首次326过1冷cv2超时1跳过，原工作线程7项按GUI预载cv2后重测全过，327不同用例解决，不能累加为334。

- 最终boot da36c36a-ef4d-4122-8ad6-cfae3931303e，相机PID54394在切换前后保持；178份未改Python一致，继承原manual_release及pan配置SHA。当前视觉未就绪、manual_pan FAULT，精确环境不匹配时拒绝MMIO，不能仅更新boot或越过保护。短时待机8.078fps/P95中位137.49ms不代表实聊长稳；本轮无实际播放/开麦/机械命令。

- 用户明确“保持其他模型运行”，没有卸载maibot或停止其进程；最后只读11434无驻留模型是环境观察，非卸载对照。真实公开WAV最新首PCM6.48秒，旧冷28秒/热12.87秒保留，不能主张稳定或真人接受。新版组合仍待真人选档、听音、插话、噪声和长稳；视觉/转轴及声纹/ASD等未全部完成。

- 用户提出Windows合成提帧，独立CPU真实素材6类预热P95约3.74–5.93ms；423x438 RGB网线12/16/24fps每类64帧CRC通过，24fps RTT P95约14.03ms。仅计算/传输初测，正式仍8fps，没有第二native sink或高帧显示上线；下一步是有界最新帧、PCM时钟/代次/取消、断网回退和单sink实际送显分级验收。实验隔离加载板端模块，不覆盖共享演示开发版的factory/FSM/player差异。见fps_probe/README.md。

<!-- /animation-dialogue-auto-20261026 -->



<!-- system-completion-auto-20261026 -->

- 个人记忆接续最新：`deliverables/2026-10-26_profile_memory/README.md`。Windows8792已加载r2个人档案后端并经公开WAV验证；303项回归/27子测试通过。默认访客，只有本机密钥授权的设备/session短期令牌可访问个人跨会话明确事实；更正/遗忘跨所属会话排除旧来源、拒绝旧生成/ACK。主机配置只存SHA256校验摘要，原密钥在用户私有目录，不能复制进共享树或源码包。原匿名库已一致备份并增量加表，没有创建真实个人档案。声纹未现场标定，保持不自动解锁。板端新增选档按钮和客户端源码以实际137253活动UI为基线最小合并，3项独立客户端/隐藏GTK检查通过，候选路径及SHA见board_candidate_verification.json，**正式UI未切换**，监听false/相机/转轴保持。后续需受控合并正式UI与真人选档/听音验收。下条323项为前一轮范围，不能与本轮简单相加。

- 2026-10-26最新：用户要求先完成现有玩偶任务再迁移，现不在现场，先自动测试。语音stdin/stdout总期限、请求归属/取消、Windows Job生命周期、依赖health/源码能力、8791/8792/8795统一就绪已修复并加载。238项Windows+2项Linux补测+75项转轴假设备+8项声纹=323通过，另27子测试；公开PCM的Windows取消恢复、板端网线2轮接收及并发600帧前端通过，无开麦/播放/运动命令。正式板卡源未动，handsfree=false/麦克风关闭/IDLE_READY保持，实际活动根见deliverables/2026-10-26_system_completion/board_baseline_readonly.json；后文“最新”多为历史。r11停止顺序/滤波修复仅独立候选，未替换r10。整个项目未完成：源期限COMMIT缺口、回区轨迹归零、机械/真人平顺、声纹与个人记忆最终入口对齐、画面问答/ASD及现场长稳待处理。证据/源码包见该交付README。迁移后置，HDMI排查继续暂停，LLM仍D盘且禁止复制进共享树。

<!-- /system-completion-auto-20261026 -->



<!-- motion-binding-followup-20261021 -->

- 最新正式UI `/home/root/aura-speech-motion-20261021/de989bf024a9/runtime`，新增10z `zzzzzzzzzz-aura-motion-binding.conf`，以fe6f为基线只改streaming_controller并新增motion_queue。上一反应未结束时保留合法动作最多至对应音频滞后1.5秒，过期不补播；实际启动样本计4秒间隔、每轮最多两类/去重/暂停反馈不消费/取消清空；新增有限motion_events与state.speech_motion说明apply或skip原因，困惑收尾计时防残留。173其他Python及音频前端/500ms前导计入20秒/回声/监听/快照/perf/身体/pan/config保持，PC8792/8795和固件未动。

- 254项板端回归/真实素材/前端及预检、15本地专项通过；首次1异步HTTP完成标记失败及PATH缺modprobe保留证据，正确PATH原批完整复测通过。UI-only限时试验COMMITTED，旧8.044fps/P95中位134.18ms/CPU97.11%，新60秒8.018/P95 144.52ms/CPU94.38%，只证明原门槛通过，不主张渲染提升。最终IDLE/IDLE_READY/error空、8.009fps/P95 135.61ms/P99 183.50ms；**监听切换前为false，保持false，不要按旧true恢复**。本轮未主动播放/开麦，无新版真人动作/现场噪声通过。相机实际PID1017在本轮保持，旧PID1002亦不可当当前。全部旧覆盖保留，独立守护提交/停止，回退仅移除自身10z覆盖回fe6f。证据 `deliverables/2026-10-21_motion_binding/README.md`，下文fe6f“最新”为历史。

<!-- /motion-binding-followup-20261021 -->



<!-- mechanical-user-state-20261021 -->

- 用户补充实物“能手动转动，但机构或限位还没标定”。按手动恢复/有限点动标定路线，不自动启用随动或填写verified。既有联合固件和驱动已只读盘点存在，当前VART亦指向benchmark，恢复必须成套核对固件/DTBO/xclbin/VART及相机，不能单改pan boot字段。详情与指纹见identity_motion_followup/README.md及joint_firmware_inventory.json。



<!-- identity-motion-followup-20261021 -->

- 用户要求继续人脸、声纹和机电。本轮只读核对实际板卡，并新增本地live.py健康原因诊断/纠正UNKNOWN提示、speaker_attribution离线归属候选、check_motion_readiness只读预检。候选未替换正式相机/UI或接正式声纹。现机电manual_pan FAULT/Boot mismatch，旧boot及FDT均不匹配，实际加载kv260-benchmark-b4096.bit.bin而非驱动要求的aura-visual-servo-b4096-v1.bit.bin；不可仅更新boot或绕过校验、不可将“保留pan入口”当当前可用。正式模型/阈值/身份库/监听/固件保持，无寄存器IO。公开ECAPA同人跨句0.729495、异人0.055171，仅公开冒烟，0.80为未标定协议夹具并拒绝该同人；生产默认拒绝未标定结果，不绑定个人记忆。证据deliverables/2026-10-21_identity_motion_followup/README.md及board_candidate_verification.json。真实机构状态等待用户说明，现场重返/跨天与陌生人声纹/实体随动未验收。



<!-- local-open-source-production-20261021 -->

- 用户明确选择本地开源；GTCRN+Silero v5 经官方sherpa-onnx SDK已接入，最新正式UI `/home/root/aura-audio-frontend-20261021/candidate-fe6f5c7b1b56/runtime`（基于922dab，保留渲染/动作/pan/缓存/perf和回声核验），PC独立CPU8795、模型D盘，无8792模型服务重载。313回归/预检/隐藏配置检查及公开PCM622帧LAN通过，P95约4.4/4.3ms、0超20ms，非整轮延迟。35公开/生成输入30语音收尾/5非人声0起点，原PCM切片精确但4转写差异。500ms前导已计入20秒上限；网络失效/错序/取消不作语音或能量回退。监听true/IDLE_READY，相机及身份库在切换期间保持。新版现场噪声、听音/打断/长稳未验收；ECAPA尚未正式接聊天或读取个人库，电视/旁人不能称过滤通过。初次隔离时板端曾重启原因未明，后续隐藏检查禁第二native sink并通过，不能声称全程无重启。Windows未设自启动，独立服务缺失运行start_frontend.ps1；资料/回退见deliverables/2026-10-21_environment_frontend/INTEGRATION.md与当前verification_summary.json，下方“未选择/未部署/922dab最新”为历史。



<!-- environment-front-end-evaluation-20261021 -->

- 用户“继续”后已完成成熟前端隔离验证，尚未部署：GTCRN+Silero v5，35公开/生成场景/19降噪对照；4类生成噪声起点从原能量4→0，12中文变体组合均单段收尾，但强噪声仍词差，不能写真实环境/电视拒绝通过。板端官方SDK组合RTF约1.26–1.51不实时，选择电脑CPU方向；337个20ms公开帧板端→PC→板端往返P95 3.71ms/最大6.29ms/0包超20ms，仅处理与传输非算法/说完判断/回答延迟。117相关回归通过/1跳过，10新边界；共享silero_gate及vad/automatic_capture分类器注入默认未启用。实际922dab入口与6文件哈希保持、监听true/IDLE_READY，PC/板端生产无重启/无新常驻服务。板端原ORT Python包独立导入abort；官方ORT1.17.3/sherpa1.13.8只解包到/home/root/aura-environment-eval-20261021隔离目录，勿误称系统包已替换。模型/包在D:/AIModels/audio-frontend-eval-20261021；现有ECAPA禁网公开双人复测，未读个人库或调阈值。下一步先做流式归属/取消/有界队列及延迟前导对齐，再真实负载，不把临时TCP实验直接常驻。用户问三路线区别，尚未选择商业授权/购买硬件。证据deliverables/2026-10-21_environment_frontend/README.md、verification_summary.json。



<!-- snapshot-budget-20261021 -->

- 用户授权继续优化后最新正式根 `/home/root/aura-speech-motion-20261021/922dab49a74f/runtime`，新增 `zzzzzzz-aura-snapshot-budget.conf`，旧bd9e及全部覆盖保留。worker专用JSON树快照隔离复制、RecordingController.public单次播放/转写读取及frozen CapturedAudio不可变PCM元数据缓存；实际控制路径不变，167份非改动Python与回声核验/监听/身体/动作/pan/config保持，PC未改/重启。176回归/图像/pan、4快照隔离/缓存失效/阶段日志专项和隐藏GTK通过；同一真实状态复制微测26.51→8.97ms。

- 限时试验COMMITTED：暂停基线8.007fps/P95中位186.33ms/CPU107.20%，新版90秒8.012/P95 135.21ms/CPU92.75%，缓存语音短测8.333/P95 134.65ms（短阶段边界不能当持续8.33能力）。重启会清空进程历史，整机前后不是等历史A/B，不能把全部差异归因代码。已恢复原监听true；最终IDLE/IDLE_READY/error空、7.999fps/P95 150.89ms。bd9e真人通过不自动沿用新组合，持续真实负载/严格8帧仍需观察。

- 新render_performance模块在实际native push完成后按phase/FSM聚合5秒帧间隔/整帧/public耗时和长帧；跨阶段间隔不归新阶段。后台有界队列写约2MB轮转1份备份，不写正文/录音/图像，不堵渲染。日志在当前managed-runs/.../evidence/render_performance.jsonl，API avatar_renderer.presentation.performance_log给路径/错误/丢记录；正式已覆盖SPEAKING/IDLE等25记录，最终30，0丢失/错误。非物理扫描，5秒窗口P95不能合并成全轮P95。入口/回退/完整证据 `deliverables/2026-10-20_avatar_24fps/SNAPSHOT_OPTIMIZATION_20261021.md`，下文旧“最新”根为历史。

<!-- /snapshot-budget-20261021 -->



<!-- human-dialogue-render-check-20261021 -->

- 用户最新明确“真实对话现在通过”，bd9e组合本轮真人对话验收通过，证据avatar_24fps/human_dialogue_acceptance.json；画面稳定性不随之通过。只读日志含16轮流式audio_complete及一次ack_nod，当前IDLE/IDLE_READY/monitor=true/error空；近约30秒滚动sink7.901fps/P95 191.13ms/P99 245.85ms，平均接近8但仍有长帧。worker近240帧整帧P95 142.02ms，public快照P95 48.75ms可作为后续分析点（含调度等待不等纯CPU）。无正式落盘阶段渲染历史，turn不保存fps，不能还原整轮SPEAKING/LISTENING/打断的帧稳定性。详见 `deliverables/2026-10-20_avatar_24fps/HUMAN_DIALOGUE_RENDER_CHECK_20261021.md`。本轮未重启/暂停/改配置或额外播放录音；下文“真人待确认”由本用户反馈覆盖，严格8帧/长稳仍未通过。

<!-- /human-dialogue-render-check-20261021 -->



<!-- interaction-render-fix-20261021 -->

- 最终补记：bd9e恢复监听后被动约一分钟30样本，全程monitor=true/IDLE_READY/error空；7.983–8.023fps，滚动P95 145.05–167.60ms，但全为IDLE/WAITING_PERSON且未开麦，无SPEAKING。不能宣称重测了真实开麦负载或通过原P95门槛；等待用户入画后实际对话。独立试验watchdog已停止，正式入口保留bd9e。

- 用户要求复查实际交互继续完善。最新正式UI为 `/home/root/aura-speech-motion-20261021/bd9e48cc658f/runtime`，新增独立 `zzzzzz-aura-interaction-render-fix.conf`，保留0e98动作/f8e固定送显/a3c8回声保护与所有旧覆盖。只改realtime_facials及idle_body_compositor：不显示待机身体时跳过采样，身体帧插值复用已有NEON原生实现；其余168份Python一致，PC未修改/重启，监听/语音/记忆/pan/配置保持。40时刻身体像素差最大0，采样中位21.92→5.67ms，176回归/图像/pan通过。自然空闲限时试验COMMITTED；暂停监听同场基线P95中位200.86ms/CPU111.92%，新90秒8.013fps/P95 132.03ms/CPU92.22%；缓存语音7.995fps/P95 138.23ms。已恢复原监听true，正在分开记录开启监听后被动观察。

- 此次0e98旧正式实聊采样6.45–6.87fps/P95 295–351ms，首次约7.33fps/P95267ms，真实负载不能沿用此前暂停测试“稳定8帧”结论。最近实际完成轮次存在ack_nod at_sample0，动作链路确有真实触发，其他普通回答为空不强加动作。修复后持续真人负载结论以本轮观察为准，不自动沿用旧短测。记录 `deliverables/2026-10-20_avatar_24fps/INTERACTION_RECHECK_20261021.md`；下文0e98“最新”为历史。

<!-- /interaction-render-fix-20261021 -->



<!-- speech-motion-connected-20261021 -->

- 最新正式UI已进到 `/home/root/aura-speech-motion-20261021/0e98f7830e27/runtime`，独立 `zzzzz-aura-speech-motion-trial.conf`，保留f8e固定8帧及a3c8回声核验和原全部覆盖。说话使用既有真实身体帧+跟踪口型/眼睑，PC经能力协商发送与PCM样本对齐的点头/摇头/惊讶/困惑，最多每轮两类/间隔4秒，打断清空旧代次，动作完整收尾回说话。模型快通道语法仍空动作，语义动作由实际说话开头保守规则补充，不称模型已全语义规划。

- 176板端回归、73项PC及4子用例、20项真实素材/发包/身体像素测试、隐藏GTK通过。动作版90秒7.994fps/P95中位146.06ms，缓存语音7.891fps/P95 155.07ms，余量接近门槛；UI CPU约99.92%（同场91.22%），仍低于原未限帧148%。161份非动作源码与回声三文件/监听/pan/配置/8帧worker哈希保持。PC只更新三个动作源码并备份，首句/27B/OmniVoice16/记忆配置SHA保持；真实ASR→27B→TTS确认v1控制先于PCM，该普通回复没有强加反应，不称四类真人播放验收。未新录音/播放/ACK或提交持久测试会话。最终IDLE/IDLE_READY、monitor=true、error空、计数约7.99fps。持续真人观感/实聊长稳尚待验收；原a3c8语音真人验收不自动沿用。入口与证据 `deliverables/2026-10-20_avatar_24fps/ACTION_CONNECTION_20261021.md`。下文f8e“最新”是动作上线前的稳定渲染基线。

<!-- /speech-motion-connected-20261021 -->



<!-- stable-avatar-fps-20261021 -->

- 用户允许24帧不稳定时计算合适稳定值后实施，并要求接通说话与丰富动作。最新正式UI根为 `/home/root/aura-render24-budget-20261020/f8e48486023d/runtime`，新增独立 `zzzz-aura-stable-fps-trial.conf`，保留a3c8回声核验及原全部覆盖。10帧da631、无固定送显8帧30f3均触发门槛回退；固定deadline单帧送显8帧f8e正式验收COMMITTED：90秒7.991fps，sink间隔P95中位130.62ms、最大滚动P99 158.85ms；缓存语音8.176fps/P95 130.01ms；UI CPU147.70%→88.06%（单核100%）。176相关回归、4分频/节奏/取消与隐藏GTK通过，164份非渲染Python一致，回声三文件/pan/config哈希保持。最终状态已读回IDLE/IDLE_READY、监听true、error空。证据 `deliverables/2026-10-20_avatar_24fps/stable_fps_trial.json`、`stable_fps_final_state.json`；下文a3c8“当前”入口为历史，原语音真人验收不能自动填新组合通过。固定送显最多一张新帧、采样开始最多有意等85ms，控制不等待，无重复帧补数；非硬实时和实聊长稳保证。

- 动作候选目前仅隔离开发：`/home/root/aura-speech-motion-20261021/c7980449a5fa/runtime`，从已验收f8e叠加；PC未改。动作字段原本在模型、PC控制包与板端三处断开，现候选按PCM时钟将实际说出口的话映射点头/摇头/惊讶/困惑；每轮最多两类、间隔4秒，取消失效。增加新板端请求头协商，旧客户端保留旧行为。73项PC链路/首句/记忆回归及19项板端真实动作/发包测试通过；持续说话身体帧+跟踪口型合成候选正验，尚未作为正式效果或真人验收。后续必须保留f8e送显、a3c8核验、PC首句/记忆/身份与pan。

<!-- /stable-avatar-fps-20261021 -->



<!-- environment-speaker-research-20261021 -->

- 用户要求环境干扰/声纹等优先成熟方案，尽可能避免自行实现算法。调研结果在 `../语言模型分析/环境干扰与声纹_成熟方案调研_20261021.md`：复用已有ECAPA，普通噪声优先现成NS/Silero VAD；旁人/电视需另测现成主说话人隔离SDK。Quail Voice Focus不是固定身份锁且自助授权需联网；Krisp去旁人人声模型约30cm近场限制，远场模型不去人声；NVIDIA Speaker Focus仍Early Access。不能将VAD/降噪/声纹/ASD混为一体，不能由单通道推定硬件单麦或已具备DoA，不能让短句等待3秒声纹门槛。此轮仅官方资料与本地源码调研，未装模型/改服务/开麦，候选没有实机验收，不覆盖当前动画与语音实际根。



<!-- latency-human-accepted-20261021 -->

- 最新明确反馈：“明显快了，等待可以接受”，当前首句优化+回声核验组合的主观延迟验收通过，证据deliverables/2026-10-21_response_latency/human_latency_acceptance.json。此前安静播放和真人插话亦已通过。保持当前运行方案及免点击选择；不为继续压数值主动切换模型或中断服务。下方“延迟待反馈”仅为历史。噪声/多人、重复自身台词、个人长期记忆及持续实聊长稳仍不能填通过。



<!-- echo-human-accepted-20261021 -->

- 用户已明确反馈“安静时正常播放，插话后停下并回答新问题”：a3c8当前版一次受控回声/真人打断验收通过，依据human_acceptance.json，不把计数当意图证明。旧部署快照/下方待复测为历史；当前summary以此真人反馈更新。首句延迟、噪声/多人及长稳仍未验收，保留当前监听选择；后续渲染继续从a3c8合并并保留取消前核验，PC首句/记忆规则保持。



<!-- echo-barge-verify-20261021 -->

- 用户反馈自身播音被误当插话，已优先部署取消前ASR核验。当前有效UI根 `/home/root/aura-echo-verify-20261021/candidate-a3c8e50c2797/runtime`，新增独立 `zzzz-aura-echo-verify-20261021.conf`，原4个drop-in保留。以后渲染/动作候选必须从新根合并，保留新增 `board/runtime/audio/barge_verify.py` 及修改的 `tools/barge_in_capture.py`、`tools/barge_in_recording.py`，不能用e064旧候选覆盖。疑似语音先积累约600ms有界窗口，最多一个异步转写/1.5秒，匹配自身正文或不明确/失败则保留回答；不同新话才取消并沿原完整PCM提交。ACK交接不得将未核验候选直接提交；保留聆听时序/身份归属/记忆/原渲染/pan。代价是几百毫秒确认时间，重复台词可能被保守忽略，非声纹/完整双讲识别。

- 104项PC通过/1跳过、304项板端/预检/完整隐藏GTK通过；实际CPU ASR自身0.8/1.6秒片段判echo，另一问题判new_speech。用户再次明确安静立即测试后，实放9.21秒、0确认插话、461参考帧/0断流，但checks=0，不能写实际触发ASR否决或真人验收通过。原probe actual_cpu_asr_used静态标记错误已在清单/README解释，原始证据不改。正式已恢复免点击true，PC首句配置/记忆保持；未重启PC/相机，camera PID987/epoch d457a35735144f038b08b933c0033c9e及身份库SHA保持。真人安静播放+插话与延迟仍待本版本复测。动画任务已获授权同步，避开用户开口窗口，旧10帧候选需合入新保护。证据 `deliverables/2026-10-21_echo_barge_in/README.md`、`deployment.json`、`verification_summary.json`。未保存额外麦克风音频/复制模型；大语言模型仍D盘。

<!-- /echo-barge-verify-20261021 -->



<!-- response-latency-20261021 -->

- 用户反馈检测基本可用但回答延迟仍长，明确改为优先降延迟。30分钟观察已结束391有效样本/单服务段/无采样或语音错误，但多为等待人物，不填持续实聊或整机长稳通过。本轮发现重启后PC项目服务未运行、UI e064/PID2680且监听false；已恢复原D盘27B/IQ4_XS/2048与ASR/OmniVoice16。电脑首句优化已上线：voice_channel_source新增first_sentence_chat，普通chat首个>=12有效字符的完整句先合成，余下合并，短句仍一次；不按逗号切，思考/记忆命令/身份控制不切。155回归/1跳过/26子用例，原模型双路预热、无TTS缓存、同自由生成文字ABBA，多句首PCM中位5.347→3.362秒，短句2.686→2.615不主张改善，后半段无软件预测断流；首次全单句波动不计优化收益。只重载PC8792，UI/camera unit/相机PID与epoch保持，记忆规则/原开关/声线步数/人物身份/pan不改。用户最新明确“恢复监听并测试新版”，已API恢复true，early_listen/声音打断true；正式HTTP两次3.259/2.291秒不同台词不当AB对比，未播放/ACK。真人延迟与连续性尚待反馈。证据deliverables/2026-10-21_response_latency/README.md、deployment.json、listening_restored.json、verification_summary.json；后续UI任务保留PC新开关和既有记忆，不用旧源码覆盖。模型仍D盘，未复制权重。

<!-- /response-latency-20261021 -->

<!-- long-dialogue-started-20261020 -->

- 用户在此前暂缓后现明确“现在试试”，已从只读确认的e064/PID326059、监听/early_listen/打断true开始30分钟真人实聊观察。5秒一次状态元数据，无额外录音/聊天文本导出/测试音/服务切换，观察进程不操作监听；运行入口与PID见deliverables/2026-10-20_listening_timing/long_dialogue_latest_run.json，增量progress.json及samples.jsonl在其output路径。这轮等待用户实际体验反馈，不以观察计时到期自动填通过。动画任务已通知保留当前版本和窗口。历史“稍后”安排由本条覆盖。

<!-- /long-dialogue-started-20261020 -->

<!-- long-dialogue-deferred-20261020 -->

- 用户明确“稍后再做长聊”，30分钟真人长稳暂缓，未启动观察或计时，不关闭免点击监听。e064两轮接话真人通过保留；长稳仍未验收。证据listening_timing/long_dialogue_readiness.json。

<!-- /long-dialogue-deferred-20261020 -->

<!-- integrated-listening-human-20261020 -->

- 2026-10-20最新真人反馈：渲染试验回退并交还e064后，用户确认“两轮都有声音，开头完整，无需重复”。当前e064受控两轮接话验收通过，见human_integrated_acceptance.json；原5a0记录保留。30分钟实聊待用户准备反馈，尚未开始，声音打断旧版单次通过不等于本版重新验收。后续合并仍以有效e064根为基线，免点击保持true。

<!-- /integrated-listening-human-20261020 -->

<!-- listening-render-handoff-20261020 -->

- 最新渲染接续：动画任务受控试验COMMITTED后交还设备，当前有效根为`/home/root/aura-render24-budget-20261020/e06409743174/runtime`，基于已验收5a0保留聆听时机、声音打断、记忆和pan；原zz-listening/99/80覆盖均保留，新增zz-aura-render-budget-trial.conf生效。已核对交付final_state：enabled=true、listening_timing.enabled=true、voice_barge_in=true、音频IDLE_READY、界面无错误。此前两轮真人通过属于5a0；新组合真人接话与30—60分钟长稳尚未验收。见render_handoff.json及动画交付listening_budget_trial/final_state，后续从e064有效根合并。

<!-- /listening-render-handoff-20261020 -->

<!-- listening-timing-20261020 -->

- 用户在明确确认声音插话成功、记忆“更正正确，遗忘后不再记得”后，要求先完善开始聆听时机。新实际UI根`/home/root/aura-listening-timing-20261020/candidate-5a0cab12671b/runtime`，通过独立zz-aura-listening-timing-20261020.conf覆盖，原99-RGB565/80-pan及其业务逐份保持。early_listen=true：首份有效新鲜正脸先准备PCM，仍两新帧跨度600ms+同目标语音证明后才ASR；实际首PCM到达才提示可听；普通160ms buffer/20ms period，插话原80ms buffer保持。短视觉缺口对当前语句隔离保留、额外最多1.5秒等待新鲜同目标再提交，不扩大旧帧授权；换人/多人/换源/过期硬关闭；同人在场静音不每30秒重开有界环。回答结束的AEC段跨完整ACK/500ms尾音保留下一句，条件齐全才同段交接，不提前提交/不撤销旧ACK/不丢前导。修复closed capture残留speech_active公开状态，未合入CapturedAudio摘要缓存性能优化。225项PC/2跳过、最终289板端/预检、完整屏幕外pan+RGB565+新时序GTK通过；null音频、暂停监听/电机替身，不当真人。GUI相邻补丁合并保护首轮中止、pan测试导入路径首轮失败均保留并正确复测。UI已加载并恢复监听true，相机106060/epoch/单元/配置/身份库SHA及0.50、PC8792记忆版保持。原单次真人插话及六句记忆验收通过已保存，用户已明确反馈新时机“两句都接住，开头完整，无需重复”，单次受控两轮真人验收通过，见human_acceptance.json；30—60分钟长稳、噪声/多人仍未验收。模型仍D盘，无新录音保存。后续动画从5a0实际根合并，不用旧887/667启动器覆盖新zz。证据deliverables/2026-10-20_listening_timing/README.md、deployment.json、verification_summary.json。

<!-- /listening-timing-20261020 -->

<!-- memory-controls-20261020 -->

- 最新现场：用户明确“旧回答停下，并听到新问题的回答”，887 RGB565/pan+PC记忆组合单次声音插话通过；观察2次插话计数、完整ACK，71ms仅检测到取消软件计时。噪声/多人/远近/长时未验收。六句记忆真人测试亦收到“更正正确，遗忘后不再记得”，单次更正/遗忘通过，见memory_controls/human_acceptance.json。见voice_barge_in/human_barge_in_acceptance.json，监听保持用户最新true选择。



- 用户要求按步骤继续完善对话。当前会话明确记忆查看/设置/更正/遗忘/清空已实现并正式重载PC8792，范围仅explicit_anonymous_conversation；最多12条/键16值64，普通聊天不自动抽取，姓名不变成人脸认证。新common/memory_commands.py，conversation_store/context与board_model_host/voice_channel_source共5生产源，交付source_manifest固定。206项相关PC回归/2平台跳过；另HTTP六指令路由夹具在31项记忆模块测试内通过，与前者不相加。原27B独立合成会话11步5实际问答（召回/更正/遗忘/清空）通过，每步重开库；ACK为模拟，非真人。正式两次ASR/27B/OmniVoice HTTP证实事实1→0及旧ACK400，只有新合成会话，未开麦/播放。用户操作提交即落库，不依赖TTS；助手仍完整ACK才召回。记忆命令/播报不当事实；更正/遗忘抑制相关旧整轮，清空抑制当前会话全部旧轮，原档案保留；memory_revision阻止迟到生成/ACK回写，排除标记无删值。非抽象摘要/任意语义遗忘/个人档案/TTL；旧轮混其他话题会整轮退出召回。迁移备份在原model_host/backups，不入源码ZIP；已实际遗忘后不可回退忽略排除表的旧实现或旧库。板端实际新RGB565/pan根887c4b6b2b5d，99覆盖启动/80仍保留，PC加载前后单元哈希/相机106060及epoch保持，模型参数/0.50/身份库未改。用户最新明确恢复免点击，enabled=true；初次无反应0人脸/armed0，随后“现在有了”，真人打断与记忆更正/遗忘已分别通过；最新聆听时机及实际活动根以上方listening-timing块为准。禁止用旧667/049启动器覆盖新RGB565/pan。证据deliverables/2026-10-20_memory_controls/README.md、verification_summary.json、host-reload-3047266652/after.json、http_summary.json。

<!-- /memory-controls-20261020 -->

<!-- voice-barge-in-20261020 -->

- 声音打断667b70d586ca已在原生45f9上三方合并并上线，实际活动根`/home/root/aura-voice-barge-in-20261020/candidate-667b70d586ca/runtime`。保留NativePixels/NativeVideo、JPEG线程、sink计时、双线程/100ms及219项保留组件，板端217项/预检/完整屏幕外GTK和真实原生sink通过，PC101项/2跳过。用户再次明确安静立即开始后，预热ready触发0ms、9.22秒播放、0误触发、1267参考帧/0外层断流，实机本次安静播放检查通过；原生5条discarded-first-frame警告保留，不代表所有时序/回声环境已验证。旧失败与等待超时历史不抹除。活动源码与相机/身份哈希核对通过，免点击enabled=true、声音打断true，原选择已恢复。已请用户实际问小故事并在播放期间问名字，真人插话/新回答听音尚待反馈，不能提前填通过。实现240ms持续活动、Speex播放前参考、同一MCP01锁、同会话接话、前导保留、旧结果/回调隔离、未播完不ACK、原PCM/ASR门槛及参考失效不回退原能量。相机PID106060、0.50、身份库及PC未改，未保存新录音，LLM仍D盘。正式GUI/config在交付merged_sources，不能旧GUI或旧45f9单独覆盖；动画任务已获知当前新根并等待真人测试。证据deliverables/2026-10-20_voice_barge_in/README.md、deployment.json、active_verification.json、controlled_acoustic_pass.log。

<!-- /voice-barge-in-20261020 -->

<!-- avatar-native24-20261020 -->

- 稳定帧率增量：PC延迟任务明确允许null音频隔离回归后，重启后e064/PID2680基线构建c6bd11e52dd1；143原回归+3新增控制分频测试/原画质/pan预检/完整隐藏GTK通过，正式UI/用户暂停开关未动、没用PC模型/GPU或真实音频。双UI负载8.93fps/P95约174/P99约245ms，不称稳定10通过。trial_stable_fps.py已准备新目标门槛实际9.5–10.2fps/P95<=125/P99<=200、声音缓存约10、CPU不增5%，自然空闲/独立watchdog/原选择恢复保护；用户明确改目标，不能拿原“平均fps更高”门槛验新低稳定率。**未正式执行或部署**，等待PC延迟真实对照结束/正式交还。旧通用candidate字段preserved_except_gui=false因预期改worker+Realtime+Streaming，允许范围为4文件，后续需正式逐份核对。见STABLE_FPS_PLAN_20261021.md/stable_fps_*证据，当前无候选负载。下条是前阶段。

- 2026-10-21用户改为若24不稳则计算合理稳定帧率并实施。现有整帧P95待机约69–79ms、缓存说话约95.6ms，12fps预算83.3ms不足；选**10fps作为首个板端验证目标，非已确认稳定值**，8fps为备选。真实对话旧样本P95约205ms不能抹去，降帧是否消除长帧需实测。30分钟391样本不含渲染字段，不能从它计算帧P95。本地stable_fps_sources基于实际e064，将约24Hz控制与10fps像素分频（非视觉tick仍处理音频结束/流式控制、无旧图填充），3项针对性测试通过，prepare_stable_fps.py仅准备未运行；**未上板回归/未部署，生产未动**。对话任务发现设备重启、PC服务不可用/监听暂停，正在恢复并做回答延迟优先测试，本任务已协调等待窗口，不按旧true假设擅自恢复。见avatar_24fps/STABLE_FPS_PLAN_20261021.md及test_stable_fps.py，需最新实际配置/选择再候选回归、10fps间隔和控制响应验收，未通过可回退/评估8fps。动作后置。下条为历史。

- 最新快照/重复标签候选9bc229c3c472-retry-1637376277740812905已受控试验但**ROLLED_BACK**，实际仍e064/原4个drop-in。用户明确先做渲染、可临时暂停监听约5分钟；自然空闲暂停后，前后同缓存PCM/待机比较，结束恢复true。候选将worker.read深拷贝移锁外、23处重复文字跳过GTK；首版隐藏GUI因TextBuffer接口错误失败/超时，已修复补测，143回归/画质/pan预检/完整隐藏GTK通过。实际待机20.690→21.610fps、p95 78.045→70.447ms、CPU150.886→142.121%，收益4.4%/9.7%/5.8%均未达到原5%fps或10%p95或10%CPU任一保留标准，自动撤销本次zzz-snapshot覆盖，不降低阈值。候选说话后测未执行，旧e064缓存5秒22.13fps不等于ASR完整对话。snapshot_trial.json/snapshot_rollback_verified.json确认回e064、音频IDLE_READY/监听true/early和barge true、无UI错误/候选override/看门狗timer。已交还对话任务真人窗口并停止负载，正式源码未覆盖。24仍未通过，动作后置；本轮失败/部分打包目录保留。下条为历史。

- 当前最新e06409743174已基于真人两句通过的5a0上线COMMITTED：有效根`/home/root/aura-render24-budget-20261020/e06409743174/runtime`，同级startup启动器通过zz-aura-render-budget-trial.conf生效，原zz-listening/99-RGB565/80-pan保持。业务Python与5a0逐字节保持，GUI唯一差异native tick有界可配置、选200ms，native线程3；原RGB565/CUBIC库同SHA，未采用失败的AREA/LINEAR。143相关回归/10图显示画质/pan预检/完整隐藏GTK通过。协调自然空闲后临时暂停监听对比，独立360秒看门狗覆盖恢复；30秒原基线17.240fps/p95 99.681ms/CPU149.26%，新60秒21.123fps/p95 72.637ms/148.43%，+22.5%fps/-27.1%长帧指标/CPU基本平，无回退。结束API恢复监听最新true，early_listen/声音打断true保持，相机106060/单元保持、PC未动，watchdog已停。证据avatar_24fps/listening_budget_candidate.json、listening_budget_verification.json、listening_budget_smoke.json、listening_budget_trial.json、listening_budget_final_state.json。**21.1为暂停监听短时待机，非稳定24/真实说话/长稳**，旧887真实说话10–12fps仍有效失败证据，本轮未重测。已交还对话任务窗口，后续以e064合并勿旧5a0覆盖；渲染尚需状态快照/线程争用优化，动作接通后置，主源码未覆盖其他任务。下条是历史。

- 用户明确先渲染后动作接通。本轮AREA/LINEAR缩放替代10状态×4时刻P99最高14>原10，拒绝未采用；原CUBIC保留。ca9c0f534752候选仅3线程+200ms诊断，原RGB565库同SHA/其余业务Python保持，143回归/画质/pan预检/完整隐藏GTK通过，但正式试验在切换前遇基线<15及idle保护拒绝，实际正有真人记忆对话，不当新性能退化。**未切换**，仍887根/99和80，没创建zz调度override或启动新看门狗，监听最新true保持。只读真实SPEAKING→IDLE样本约10.5–11.7fps，public阶段P95约51–55ms/max200–294ms，包含调度/锁等待；以前19.4是待机，不能代表真实对话。证据budget_probe.json/budget_candidate.json/budget_verification.json/budget_smoke.json/monitor_10s.json/budget_handoff_state.json。已明确交还声音时序任务窗口，等待其新稳定根再合并渲染，不覆盖聆听修复；冻结CapturedAudio.metadata重复PCM SHA仅提出缓存建议未改源码，动作尚未接。下条保留前阶段。

- 最新用户明确“做”后RGB565候选887c4b6b2b5d已受控对比COMMITTED，当前实际根`/home/root/aura-render24-rgb565-20261020/887c4b6b2b5d/runtime`，同级startup/launcher.py/config.json经新增99-aura-rgb565-trial.conf生效；原80-pan drop-in保留，入口仍board_avatar_pan.py。667声音所有Python逐字节保持，仅NEON RGB565显示库变更；原色深16位，量化与旧GStreamer均值1.34–1.38/P99最大9通过10图阈值，143项回归/pan预检通过。基线30秒15.393fps/p95 102.025ms/UI CPU184.10%，新60秒19.434fps/p95 81.846ms/149.38%，实际帧率+26%/CPU-19%；仍未稳定24，不当十分钟或真人多场景验收。独立360秒看门狗+帧率>=max15/基线95%且p95不恶化10%/功能保持/须明确收益保护，本次获准执行，无回退且timer已停，不是绕过此前被拒绝三线程。免按键原false/PAUSED、声音打断true、相机106060和单元保持，未重启PC或操作云台。证据avatar_24fps/rgb16_candidate.json/rgb16_verification.json/rgb16_trial.json/rgb16_final_state.json及README首段。已向声音/记忆任务交还时段并停止负载，其可安排PC8792记忆重载；不要用旧667/45f9启动器覆盖新活动库/有效drop-in。主源码未回写覆盖其他任务。以下保留历史。

- 本轮继续后最新：已由声音任务明确交还，基于049c部署原生双线程45f9f5cd2aaa，实际稳定根`/home/root/aura-render24-20261020/candidate-45f9f5cd2aaa/runtime`，文字/诊断100ms。画质/125项回归/完整隐藏GTK/预检通过，相机106060、身份配置库SHA/0.50、PC与免按键enabled=true保持；单实例30秒约17–18fps（原6–7），sink间隔p95约83–93ms，未达稳定24fps。真实缓存PCM5.04秒播放后IDLE_READY无错误，非真人听音/完整ASR对话/10分钟验收。e660三线程+200ms诊断候选通过画质/125项/隐藏GTK，但正式切换被自动审批拒绝（并发烟测11.65fps被判可能降级且无性能阈值回退），命令未执行，不绕过，仍45f9。本任务已向声音任务明确交还板卡并停止负载/切换；其从实际45f9重新合并声音修复。共享主源码仍声音候选，本任务未覆盖。当前candidate.json指未部署e660；实际活动证据看candidate_two_thread.json/deployment_two_thread.json/monitor_30s.json/scenario.json。原生2.5倍改善但24目标与动作字段接入尚未完成，后续正式性能对比需具体回退条件和所需批准。下条保留首轮历史。

- 2026-10-20用户明确继续24fps优化。原生候选d310443d4f30以049c为基线，未正式部署；画质50组均值最高0.0522/P99最高1/最大2，125项板端回归及隐藏GTK原生sink通过。双UI并发实测仅9.09fps，不通过24fps，不当单实例或屏幕物理帧率。隔离原生全帧1线程p50/p95=37.77/47.85ms，2线程27.14/37.04，3线程21.41/39.61；只能证明计算余量，不宣称已稳定24。试切换前8783不可用，脚本在任何写入前退出；只读确认另一聊天正在声音打断实机测试。用户明确允许发消息协调，双方已约定此任务停止板端并发负载/切换，等待声音任务README“可交接界面测试”及最终稳定根，再重取基线合并，不能覆盖其新GUI或使用旧049c回退。当前源码草案增加可配置线程和XID后同步，尚未打包复测；candidate.json仍指向测试过的单线程d310。测试/状态/后续验收见deliverables/2026-10-20_avatar_24fps/README.md；动作素材字段接入仍未修。主源码未同步草案，模型权重仍D盘，无新照片/环境/密钥复制。

<!-- /avatar-native24-20261020 -->

<!-- avatar-performance-20261020 -->

- 2026-10-20用户要求板端开销分析后优化，已上线29e469动画性能版；当前已由免点击任务合并到`/home/root/aura-handsfree-dialogue-20261020/resume-049c88498ae0/runtime`，6份动画生产源码SHA及GUI性能块只读核对保留，handsfree enabled/WAITING_PERSON。后续以实际活动版为基线，不再用旧UI覆盖/回退当前恢复版，不回写旧GUI到主树。CPU原UI145%/视觉120%/Xorg32%/音频14%，可用内存约3.09GiB。移除重复变换、局部眼嘴合成、跳过被覆盖的嘴部绘制、OpenCV单线程最终变换/缩放、文字10Hz、滚动分项与GTK提交计数。113项回归、眼层/75组嘴部像素一致、背景/缩放误差与真实隐藏GTK检查通过，原相机PID本轮106060/epoch不变、身份0.50及库哈希保持，PC未重启。发布短测3.92→6.38–6.90fps、GTK约5.9–6.0fps，UI CPU145→120–129%；并行工作可能干扰采样，卡顿未彻底解决、未达24/30fps，合并后未做独占/真人听音性能验收。更激进c892435b4974组合缩放P99画质13>10拒绝未部署，rejected_candidate_sources_v5保留；目前candidate_sources是29e469确切性能源码，不能代替最新合并GUI；build_candidate.py为历史生成脚本。动作字段置空/动作接入仍未修。已停止后续UI切换与并发负载以配合免点击恢复，后续先统一安排测试。报告deliverables/2026-10-20_avatar_audit/PERFORMANCE_REPORT.md及handoff_verification.json。没有新个人照片/模型/环境/密钥复制，LLM仍D盘。

<!-- /avatar-performance-20261020 -->

<!-- handsfree-dialogue-20261020 -->

- 用户选择正对汐蓝开口免点击、无需叫名，声纹占麦暂停后已明确继续。最新UI为`/home/root/aura-handsfree-dialogue-20261020/resume-049c88498ae0/runtime`，在动画任务29e469性能版上合并，151份其余Python源逐份保持。板端176项、隐藏GTK完整初始化、真实X11唤醒及活动源核对通过；最终PC对话101项通过/1项Linux专属跳过，合并后的7项动画线程测试因Windows语音环境缺cv2不可运行，原失败日志保留，这7项已在板端完整通过，不伪填PC108。首次两份新鲜正脸帧跨度600ms；之后同轨轻微转头继续，0脸宽限不超过最后真实源帧1秒。录音/提交阶段多人/换轨/失效停止；已提交的问题先完成当前生成和播放，完整ACK及500ms尾音后重新核对目标，失效不开下一轮。交谈绑定/手动连续对话/播放期间每5秒重置显示空闲并按需唤醒，保持原600秒空闲策略。监听设置用UI实际HOME的`/root/.local/share/aura/handsfree_dialogue.json`；旧工具误恢复/home/root副本的问题已修正，本次按用户明确继续恢复enabled=true，主动暂停仍持久保留，正常关闭不改用户选择，坏设置保持暂停。原“开口没回答”及本轮“有文字但慢卡后黑屏”均保留失败；本轮确认界面未崩溃、DPMS OFF，唤醒后用户确认“已恢复显示”，恢复版用户明确反馈“两轮都能听到回答”，本轮免点击入口和连续两轮听音通过，同场另观察2份完整ACK；更长时间稳定性及声音打断未验收。自动入口新建匿名会话，不恢复上一人记忆；声音打断/全双工/说话者绑定/电视拒绝未完成。相机仍board_camera_motion.py，单元/PID本次106060、配置、身份库哈希及0.50保持，未重启PC。用户已授权与“排查玩偶动画卡顿与素材”协调，对方已停止后续切换/负载测试；共享主源码同步已验证的合并GUI及动画依赖，不取未部署c892候选。不得运行旧handsfree目录rollback.py覆盖相机/运动配置。首次候选模块软链接失败及自动回退记录保留。证据`deliverables/2026-10-19_handsfree_dialogue/resume-20261020/README.md`及verification_summary.json；LLM数据仍D盘。

<!-- /handsfree-dialogue-20261020 -->



<!-- threshold-050-active -->

- 用户明确要求“现在那就调成0.5”，已将板卡活动及本地board_identity门槛0.80→0.50，threshold_origin为user_authorized_experimental_cosine_0.50_not_field_calibrated，覆盖下方旧0.80/0.85保留要求。实时识别、登记验证、原始锚点同用该门槛，0.1分差和原模型/质量/单模板/采样/确认保持；只重载相机，UI和PC未重启。实际匹配器隔离库0.4999拒绝、0.50/0.5001通过和歧义/登记门槛检查通过，161份相机源/模型/人体DPU保持，UI READY重连。正式库仍1身份/1模板/rev15且SHA不变，25图保持，无重登/新图/模板导出。活动相机仍enrollment-photos候选6f1，PID本轮93153仅快照；UI已是长对话版，PID41716保持，不恢复旧UI。当前一次未确认人员姿态观测1脸/UNKNOWN，不能当本人受控失败，也不能声称0.50已经修好或完成误认标定。证据deliverables/2026-10-19_threshold_050/README.md、activation.json、current_verification.json；无需为阈值更改要求重新登记。LLM数据D盘。

<!-- /threshold-050-active -->



<!-- character-identity-20261019 -->

- 2026-10-19用户明确移除“DeepSeek鲸鱼娘”，正式自我身份为“名字叫汐蓝的桌面玩偶助手”。仅修改aura/board/runtime/character.py的CHARACTER_DESCRIPTION，8792空闲重载已生效；名字/默认问候/演示台词/性格/48字策略保持。63项相关回归与原27B四项真实文字身份问答通过；非真人听音。配置、记忆策略和库、原27B/ASR/OmniVoice16、板端UI和相机保持；不改历史归档或声线参考转写。详见deliverables/2026-10-19_character_identity/README.md及verification_summary.json。LLM数据仍D盘。

<!-- /character-identity-20261019 -->



<!-- long-conversation-20261019 -->

- 2026-10-19用户要求对话优先、降低延迟后置。已部署持久匿名会话与有界原话检索上下文第一版，UI活动`/home/root/aura-long-conversation-20261019/candidate-9a5bcf476bf8/runtime`；开始可继续上次/新对话，boot/session仍用于运行代次，不是长期会话主键。PC SQLite位于`deliverables/2026-10-18_board_dialogue/model_host/conversations.sqlite3`，板端仅保存`/home/root/.local/share/aura/conversation_selection.json`随机ID；不自动开麦。用户输入独立提交；助手仅匹配完整播放ACK后可召回，未播完不猜播放前缀。Windows152项/Linux155项，原27B实际50轮文字五项指定召回通过（受控模拟ACK、非真人听音）；历史录音真实ASR/27B/OmniVoice及8792实际重启接续通过。模型/声线/2048及配置保持，原相机PID本轮2004、身份库1/1/rev15哈希保持；PID以后动态读取。当前是最多2000条归档中的原话检索/摘录+近期轮次，不是抽象摘要、个人长期档案或通用遗忘；触摸打断接话、声音插话/全双工仍未实现。真人长对话与听音待本轮listening.json反馈，不能伪填通过。详见`deliverables/2026-10-19_long_conversation/README.md`、verification_summary.json和统一分析`长对话第一版_持久会话与上下文_20261019.md`。保留旧库/归档，源码包排除用户数据，LLM仍D盘。

<!-- /long-conversation-20261019 -->



<!-- identity-failure-audit-20261019 -->

- 2026-10-19用户要求详细审查身份失败，已完成只读审查与措施提案，生产代码/模型/0.80/0.1/身份库均未改。当前库1身份/1模板/修订15；25图原CPU重算复现选图，selected对库1.0；5组对齐与官方公式逐像素一致，3实际PNG板端OpenCV对电脑ORT余弦1.0，不能再把颜色/后端/对齐公式错误当已确认主因。直接拒认因本人新正脸0.620695～0.643428低于未标定0.80；25图实际只存单模板，同会话验证跨度4.415秒，不等于跨会话通过。0.60仅离线6份分数可放行，负样本0，不能直接部署或称误认已校准。人脸实测2.26Hz/特征1.768Hz（人体DPU帧率无关），推理后200ms额外等待；后续被动稳定1脸仍UNKNOWN，检测不是唯一原因。具体光照/反光/关键点导致低分尚无失败图证据。措施顺序：原因码及失败人脸证据→独立正负会话标定→少量多样模板并重标定→调度与同目标短窗共识→完整验收。审查入口deliverables/2026-10-19_identity_failure_audit/REPORT.md、review_summary.json；不自动重登记/改阈值/换模型。LLM数据D盘。

<!-- /identity-failure-audit-20261019 -->



<!-- controlled-frontal-failure-20261019 -->

- 2026-10-19用户“开始检查”后本人正脸10.09秒实测未通过：6份实际模型输入0达0.80，0.620695～0.643428/中位0.637173；52次状态全UNKNOWN，9次新鲜输入、1次无新输入、9次目标未确认、33次非单张脸条件（未细分0/多人，勿推断），目标键含None共3种。源龄429～774ms/无特征请求错；库修订15哈希不变，没存新图。彼此0.705348～0.950372，前3份相邻0.936632/0.950372，勿概括全程稳定。照片/模板一致性和登记成功仍有效，但本人正脸识别失败；检测及裁脸对齐待进一步定位，未确认新源码缺陷、不归因眼镜或用户姿态。未调0.80/0.1、未改模板/模型，不继续要求重登/转头/重返。最新证据deliverables/2026-10-19_identity_capture_snapshot/controlled_front_check_review.md及controlled_front_check.json。

<!-- /controlled-frontal-failure-20261019 -->



<!-- post-enrollment-replay-20261019 -->

- 2026-10-19本轮25张存图只读回放：selected对库模板余弦1.0，最终5验证重算0.813952～0.897079全部>=0.80，库修订15哈希未变；13采集10达标、7质量拒绝均未达标。随后12秒21当前帧0.167645～0.405261/0达标，但用户未声明当时人员/姿态，不能当本人受控测试或据此归因眼镜。已请求刚登记的本人正对同距离准备10秒检查，待用户“开始检查”；不重登/改阈值。证据deliverables/2026-10-19_identity_capture_snapshot/after_enrollment_review.md及after_enrollment_scores.json。

<!-- /post-enrollment-replay-20261019 -->



<!-- actual-enrollment-photos-20261019 -->

- 2026-10-19存图版+入口快照修复已取得真人登记证据：用户“已经完成登记”，COMMITTED/registered完整播放，库1身份/1模板修订14→15；25张实际112×112采样图+selected副本已保存在板端及电脑`身份登记照片/c6c3fa6ebd4449ae93bd9ec316344d51/`，13采集/7质量拒绝/5最终验证，SHA/解码/板端0700/0600通过。UI28f2候选、相机6f1候选，0.80/0.1及原模型保持。照片已可展示，勿再说本轮没有照片或待采样；不能补造历史照片。后续第6代“我是谁”查询仍identity_unknown/完整播放，离场重返与识别稳定性未通过，不将登记成功当识别修复完成。最新证据`deliverables/2026-10-19_identity_capture_snapshot/photo_review.json`及verification_summary.json，实际照片不打包入源码ZIP；未来登记继续留存仅人脸，失败/取消留档。LLM数据D盘。

<!-- /actual-enrollment-photos-20261019 -->



<!-- identity-capture-snapshot-20261019 -->

- 2026-10-19用户存图版登记仍无法开始：实际generation18/face_unavailable、capture_snapshot_valid=false，0照片。已确认UI缓存READY/新鲜却含取消字幕展示字段interaction_suppressed，严格相机协议拒绝。新增UiServiceClient.identity_snapshot读取原始新鲜缓存并严格校验，GUI录音改绑定该方法，显示遮罩/取消授权/同人来源和原阈值保持。Windows182+24子用例、Linux222及当前相机只读预检通过；UI已加载`/home/root/aura-identity-capture-snapshot-20261019/candidate-28f2ad776b08/runtime`，存图相机仍6f1候选/PID动态，库1/1/rev14哈希保持，电脑8792未重启。后续明确登记后保存实际112×112脸，失败也留；新真人采样和图片展示待完成，不当人脸准确度验收。最新证据`deliverables/2026-10-19_identity_capture_snapshot/README.md`及verification_summary.json；照片功能已启用，旧连接阻塞已恢复。LLM数据D盘。

<!-- /identity-capture-snapshot-20261019 -->



<!-- enrollment-photo-archive-20261019 -->

- 2026-10-19用户明确授权后续身份登记时保留人脸照片供查看；覆盖旧“不默认保存登记照片”约定。状态：已加载、真实新登记照片待采集。板卡目录`/home/root/.local/share/aura/enrollment_photos`，每会话最多192张实际112×112对齐脸+selected原图副本/manifest，最终5张独立验证单独标注；失败/取消/中断留档，普通识别不持续存图。电脑按请求由export_latest.py校验复制到`身份登记照片/<sid>/`，生成离线总览。Windows152/Linux215、原公开模型临时27图及GUI/合成导出预检通过，不能当真人照片或真人识别已通过。候选`/home/root/aura-enrollment-photos-20261019/candidate-6f1aa1842d53/runtime`；未激活时正式仍front-template旧相机，不误写活动路径。保存特性不改0.80/0.1、单模板/5独立验证/明确更新及DPU/语音。最后库1/1/rev14，连接失败期间实时值未知；不补造历史照片。详见`deliverables/2026-10-19_enrollment_photo_archive/README.md`和verification_summary.json。LLM权重仍D盘，源码包不含私有照片/向量/库。

<!-- /enrollment-photo-archive-20261019 -->



<!-- front-template-selection-20261019 -->

- 2026-10-19用户已完成静止正脸检查，5帧彼此0.896496～0.969408、对现模板0.705980～0.754973，均低于0.80；当前特征稳定，旧模板姿态未知，不能断言旧模板是侧脸。已修复自然视频模板选择忽略姿态及验证允许较大转头的源码缺口：24RAM池保护正脸，abs(yaw五点比例)<=0.22/roll<=15，至少3份正脸、最正面最多5份中选一份实际medoid，后5份独立新正脸逐份0.80/0.1；正脸不足用原验证语音自动补采，选择帧不算验证。原15秒/10份、单模板、固定原始锚点恢复/同服务相机轨迹/库修订与明确更新确认保持。Windows145/Linux207及原真实公开模型/临时库/UI预检通过；相机运行 `/home/root/aura-front-template-20261019/candidate-0003a760d43e/runtime`、PID动态读取，UI仍fa8e候选且PID保持，PC8792未重启，原DPU/ByteTrack/语音模型和参数保持。库1身份/1模板/修订14哈希不变，未自动更新旧模板。新版需用户按原称呼发起并明确确认更新，再验收我是谁及离场重返；不能把新策略加载称真人修复通过。最新证据 `deliverables/2026-10-19_front_template_selection/README.md`、verification_summary.json。LLM数据D盘，照片/模板/姓名不默认导出。

<!-- /front-template-selection-20261019 -->



<!-- identity-query-routing-20261019 -->

- 2026-10-19上一查询版真人反馈失败（仍普通聊天），随后用户说明“夕蓝”称呼识别有问题；实际当轮完整ASR未取回，不能断言具体误听字。已复现并修复“夕蓝我是谁/西兰我叫什么名字啊”无标点称呼、语气词与省略吗的直接身份问句入口，PC8792 intent_revision2、UI `/home/root/aura-spoken-identity-routing-20261019/candidate-fa8e1697c110/runtime` 已加载。只复用已知别名，不改ASR/通用姓名解释/登记/普通聊天，不宽泛子串路由。板端last_voice_route只保留单条RAM字数/路由/录音起点人脸数量与状态/回复码，不留正文、姓名、图片。Windows129项（2项Linux依赖用例移板端）、Linux202项及受控转写HTTP/原公开模型和UI预检通过；不能当真人声学称呼或识别验收。相机仍原8ad候选且PID保持，库1身份/1模板/修订14哈希不变，0.80/0.1和原语音模型/参数保持。最新真人第4轮ASR“我是谁呀”与用户确认原话一致，已进入board_identity_workflow/identity_unknown，同代次完整播放，真人问句转写/路由已通过；仍未识别人脸，称呼声学与听音未单独验收。上一版真人查询失败保留。12帧当前脸分0.437618～0.624089/0帧达0.80，路由修复未解决人脸准确度，不取最近登记姓名冒充识别。最新证据 `deliverables/2026-10-19_identity_query_routing/README.md`、verification_summary.json 优先；LLM数据D盘。

<!-- /identity-query-routing-20261019 -->



<!-- spoken-identity-query-20261019 -->

- 2026-10-19用户0.80真人登记已成功，板端确认COMMITTED，当前1身份/1模板/修订14，不能再称空库或登记待验证；用户“我是谁”不知道，根因为普通聊天没有接摄像头结果。已部署只读直接问句查询：UI `/home/root/aura-spoken-identity-query-20261019/candidate-1dc26c86d318/runtime`，相机仍 `/home/root/aura-windows-face-features-20261019/candidate-8ad60843f9d1/runtime`/PID动态读取，PC8792 query_version1，客户端另声明current-face-v1，旧客户端/普通聊天原路由。查询核对录音开始/当前真实服务、单张同人脸轨迹、库修订及3秒内KNOWN源，库中ID和称呼一致才报“镜头前识别到的是名字”；UNKNOWN/多人/失脸/过期/变代/取消不取旧名，不发数据库动作，不把姓名进入普通聊天历史，未实现说话者绑定或个人长期记忆。初始10次相机均UNKNOWN，路由修复不证明识别稳定性。PC107、新查询13复测、Linux199、公开真实模型临时库查询/失脸及真实ASR/TTS合成查询回复通过，25份UI源哈希和相机/DPU/音频保留核对，库1/14哈希不变。真人新问句/听音/重返仍待验证。最新证据 `deliverables/2026-10-19_spoken_identity_query/README.md`、`verification_summary.json` 优先于旧空库/查询未实现表述；0.80/0.1及原语音模型保持，LLM数据D盘。

<!-- /spoken-identity-query-20261019 -->



<!-- threshold-080-active-20261019 -->

- 2026-10-19用户已同意“下一轮先试0.80”并要求继续，活动及本地board_identity阈值0.85→0.80，0.1间隔/15秒选样/最多24RAM/单实际代表模板/连续5独立新帧/固定原始锚点及授权不变。此新授权覆盖下方旧保留0.85/0.80未部署表述。真实匹配器边界/分差及公开Lena临时库完整自动登记识别失脸预检通过；22份活动源码及DPU/ByteTrack/音频模型配置保持，库当前0身份/0模板/修订13。活动runtime仍 `/home/root/aura-windows-face-features-20261019/candidate-8ad60843f9d1/runtime`，当前相机PID 987但后续应动态读取。设备随后重启已复核0.80持久生效；原PC8791/8792按原启动器恢复，空闲重载UI以重新取得反馈提示，开始对话可用。真人0.80登记/听音/重返及不同人误认尚待验证，不能当已校准。最新证据 `deliverables/2026-10-19_threshold_calibration/THRESHOLD_080.md`、`threshold_080_verification_summary.json` 优先于旧0.85快照。回退仅恢复本次配置备份并加载相机，不恢复已删身份；LLM数据D盘。

<!-- /threshold-080-active-20261019 -->



<!-- empty-identity-library-threshold-20261019 -->

- 2026-10-19用户回答旧5条身份归属“不确定，你全部删除”，已通过正式identity_delete逐项COMMITTED清空全部5身份及5模板，库修订8→13，实时people空/UNKNOWN、采样idle，缓存和在途结果通过删除接口/库修订失效，无数据库备份/模板导出/重启。当前活动库0条/修订13，下方5条/修订8为历史快照，禁止当当前值或自动恢复旧记录。用户“那你看看”授权阈值对比；失败会话最后24份分数、保持0.1间隔：0.85通过3/24最长1，0.84通过9/24最长3，0.83通过14/24最长6，0.80及0.363均24/24最长24。只重放分数门槛，不能当完整77帧/模型/登记成功或误认校准。旧库人员归属未知、缺可靠不同人样本，误认率未测；0.80仅候选试验值尚未部署，正式仍0.85/0.1，不能默认为用户已授权改阈值。最新证据 `deliverables/2026-10-19_threshold_calibration/README.md`、`delete_all_receipt.json`、`threshold_comparison.json` 优先。新登记须新会话及原明确姓名确认。原模型/语音/DPU/跟踪保持，LLM数据D盘。

<!-- /empty-identity-library-threshold-20261019 -->



<!-- actual-score-failure-20261019 -->

- 2026-10-19 CPU提速/验证提示版 `candidate-8ad60843f9d1` 真人验证再次失败：77尝试、16通过、61低于0.85，最佳连续3/所需5，最终90秒超时；质量跳帧10、恢复拒绝0、间隔拒绝1可重叠，最后24帧0.810381–0.863107/中位0.8305325。候选仍单个代表特征，未保留其姿态，不能断言是侧脸或用户动作原因；提速和语音提示没有解决匹配稳定性。库5条/修订8保持，本轮只读，无重启/改阈值/写库。最新真人状态false而非待验证；证据 `deliverables/2026-10-19_validation_score_failure/README.md`、`actual_failure.json` 优先于旧预检结论。后续保持0.85，先核对候选选择与裁脸/对齐稳定性，不得将放宽验证或更多最大值匹配当作已验证修复。

<!-- /actual-score-failure-20261019 -->



<!-- windows-face-features-20261019 -->

- 2026-10-19当前活动UI/相机 `/home/root/aura-windows-face-features-20261019/candidate-8ad60843f9d1/runtime`，PC8792同一SFace/ORT CPU特征就绪，板卡只发送瞬时112×112对齐脸，不保存/传全幅或导出模板。原0.85/0.1、单实际代表模板/后5份独立验证、固定锚点/源帧和授权约束保持，网络650ms超时或上下文错配拒用。Windows74/Linux188、公开真实模型临时库、语音CPU共存、22份活动源及配置校验通过，库5条/修订8哈希未变；公开往返中位18ms，不当真人精度证明。用户上一版简化登记明确验证失败，collect10/validate0后超时，并确认“一直在慢慢转头”；新版本补回一次自动sample_validate提示看向镜头稍停，不要再说正式流程完全没有中间提示，但无需用户回答或最后确认。失败RAM新增分数/间隔/质量/恢复诊断。真人本版登记、听音、离场重返仍待验证。最新证据和回退 `deliverables/2026-10-19_windows_face_features/README.md`、失败诊断 `deliverables/2026-10-19_validation_diagnosis/README.md` 优先于下方旧路径与待验收表述。原视觉DPU/ByteTrack、原27B/ASR/OmniVoice16及参数保持；LLM数据仍D盘。

<!-- /windows-face-features-20261019 -->



# 本项目工作约定



<!-- simple-face-enrollment-20261019 -->

- 2026-10-19用户反馈操作太难，选择一句话“帮我登记身份，我叫……”。已部署简化流程：UI/相机`/home/root/aura-simple-enrollment-20261019/candidate-150c2b320248/runtime`，PC8792已重载，`sampling_guidance_version=3,confirmation_before_sampling=true`。正式ChannelConversationJobs启用simple模式；一句话请求和称呼后先复述，再明确确认一次（已有同名需“确认更新登记”），才启动采样。后续自动取样、验证和带采样token提交保存，不再要求末尾确认或左右/回正口令。授权绑定称呼/原ID/库修订/服务相机/采样token，取消或替换会话不能复用；只有明确拒绝未提交才等待重试，未知提交结果不重试，匹配COMMITTED才播成功。上一版自然视频选样15秒/最多24份RAM/后5份0.85及0.1身份间隔保持，固定原始特征恢复核对、DPU/ByteTrack、原27B/ASR/OmniVoice16和参数保持。PC109项、Linux183项、公开单图真实模型开头确认自动写临时库（逻辑时钟、不注入质量）及真实语音HTTP通过。部署用户库数量/修订/哈希未变，不当真人成功验收；真人简化登记已反馈验证失败（collect10/validate0超时），听音/重返未验收。当前源码默认VoiceEnrollment(simple=False)仅保留旧调用兼容，正式worker明确simple=True，不要误称正式仍需末尾确认。最新证据和回退`deliverables/2026-10-19_simple_face_enrollment/README.md`及`verification_summary.json`优先于下方旧活动路径。不保存视频或默认照片、不导出模板，LLM数据仍D盘。

<!-- /simple-face-enrollment-20261019 -->



<!-- natural-face-enrollment-20261019 -->

- 2026-10-19用户反馈固定左右姿势采样困难，要求自然慢转头、从视频自动筛查。已部署自然选样版：UI/相机`/home/root/aura-natural-enrollment-20261019/candidate-a9d5b4a5b042/runtime`，PC8792已重载，`identity_voice_enrollment.sampling_guidance_version=2`。至少15秒选样、至少10份合格帧、RAM最多24份，无左右姿势配额，选一个实际代表向量，后5份连续合格新帧逐份0.85且比其他身份高0.1；分数失败重置验证进度而保留选样，不绕过门槛。失脸立即隐藏身份/预览并暂停，选样窗口继续等待；新轨迹须以新合格SFace向量核对固定起始锚点>=0.85且比其他身份高0.1，才能绑定继续，锚点不滚动。同相机/服务/库版本和采样token必须保持；多人、相机/服务换代、库变动、超时禁止保存。确认时帧不合格或写入明确拒绝保留ready窗口并重新请求确认，不弱化写库条件。修复脸框裁剪边界关联，预测位移限制仅作用于人脸IoU，原人体DPU/ByteTrack和音频/模型参数保持。明确确认前不写库，已有称呼更新仍需“确认更新登记”。PC98项、Linux170项、公开素材真实模型（无姿态标签注入，逻辑时钟顺序驱动）及真实OmniVoice16三段HTTP通过；仅预检，非真人听音/自然转头/重返验收。部署前后库5条/修订8且哈希不变。失败原因保留在健康状态RAM，不导出现场照片、模板或称呼。最新入口`deliverables/2026-10-19_natural_face_enrollment/README.md`和`verification_summary.json`，优先于下方固定姿势版本路径；后者真人反馈已补为采样困难，不再描述为完全没有用户反馈。LLM数据仍D盘。

<!-- /natural-face-enrollment-20261019 -->





<!-- multiframe-enrollment-20261019 -->

- 2026-10-19用户同意多帧登记，现已部署：UI/相机`/home/root/aura-multiframe-enrollment-20261019/candidate-c4f2aaebaf87/runtime`，PC8792空闲重载，健康标志`identity_voice_enrollment.sampling_guidance_version=1`。正脸4、左3、右3选一份实测代表向量，后5份独立正脸须逐份达到0.85且超过其他身份0.1；通过后仍要明确确认才入库。已有同名称呼走原ID更新，语音需“确认更新登记”，不自动合并/覆盖。所有样本仅RAM；失脸/换代/库改动/取消/超时禁止保存。原DPU/ByteTrack、音频播放、模型/参数和0.85保持。PC80项、Linux161项、公开素材真实模型（注入姿态标签与逻辑时钟的顺序驱动）和真实OmniVoice16五段15.41秒HTTP通过，非真人听音。首次额外并发模型预检触发目标过期，未放宽正式期限。部署库仍5条/修订8、文件未变。真人采样/听音/重返尚待用户反馈，勿标完整身份验收。最新证据与回退见`deliverables/2026-10-19_multiframe_enrollment/README.md`和`verification_summary.json`，优先于下方旧活动路径；不要再把多帧采样说成尚未上线。

<!-- /multiframe-enrollment-20261019 -->



<!-- face-target-20261019 -->

- 最新真人结果覆盖本块随后较早的15秒观察：用户确认离场回来“仍显示未识别”。45秒观测103次有人脸目标、101次可登记、0次KNOWN；同生产112×112对齐裁剪的8次板端只读分数诊断最高0.583234–0.676908，均低于0.85，第一二名差距至少0.181961，不属于歧义拒绝。这批诊断库为5条/修订8且过程中文件不变；之前4条/修订7保留为历史，不推断期间库变化来源。不得把最高分身份直接认定为用户本人。纯人脸预览通过，真人识别失败；先检查登记样本与当前输入一致性，勿反复新建身份。诊断不保存/传出照片、模板或称呼。

- 2026-10-19人脸直接登记目标已部署：板端UI和相机均为`/home/root/aura-face-enrollment-20261019/candidate-a44f2c6b949f/runtime`，身份配置来自该candidate的`camera_live_config/board_identity.json`。独立YuNet人脸轨迹直接提供登记目标，SFace使用112×112对齐脸；无需先选人体，原人体DPU/ByteTrack源码及配置保持。登记窗口只显示RAM人脸裁剪，用户已确认“能稳定看到人脸预览”。Linux148项、真实模型临时库和素材/GTK预检通过，不能据此标真人重返识别通过。随后15秒只读观测为0次KNOWN、3次人脸目标、0次可登记，没有取得新的有效匹配结果；不能将这一段UNKNOWN都归因于0.85。最近核对身份库4条/修订7、0600，部署未改模板。阈值0.85、歧义间隔0.1保持，禁止绕过用户选择。最新证据、真人反馈和回退见`deliverables/2026-10-19_face_enrollment_ui/README.md`及`verification_summary.json`，优先于下面旧活动目录。普通聊天身份记忆、说话者验证及活体检测仍未实现。

<!-- /face-target-20261019 -->



- 2026-10-19模型状态只读实查：证据`deliverables/2026-10-19_model_status/status.json`及统一分析`当前模型运行状况_20261019.md`。原27B/IQ4_XS实际驻留GPU、上下文2048，Paraformer8791与OmniVoice16/8792实际监听192.168.50.1且ready；本机127.0.0.1不通不代表停机。GPU空闲约328MiB为单次采样；近5轮软件回答5.5–20.4秒，非新录音测试。身份库最新现场为4条、修订7，UNKNOWN提示先选当前对象，阈值仍0.85；旧2条/修订3是前面重登时历史，勿当当前值。本次未新增身份或拍照、未加载/改动模型、未重启服务。



- 2026-10-19身份登记最新：用户授权展示完整取景并确认是本人，随后授权重新登记。维护工具在原ID/称呼下更新该身份，库修订2→3，2条身份数量不变；原模板回退仅留板端私有目录。用户随后纠正“只拍人脸”，当前登记照片为`deliverables/2026-10-18_identity_validation/enrollment_review/face.png`，112×112实际模型输入，与已登记模板核对一致；本次电脑/板端全幅照片已移除，采集/提交工具改为只保存对齐脸，旧全幅诊断脚本禁用。此次允许保存人脸照片不代表未来登记默认保留照片。重登后实时仍0次KNOWN，8次分数0.734–0.818低于0.85。用户明确“保留0.85，暂不调整”，正式/开发配置均保持0.85，禁止自动运行0.363提案或换方式绕过此选择。仅照片重新登记已完成，重返识别未通过，不将维护工具登记冒作又一次语音播报验收。最新证据见该目录`verification_summary.json`、`enrollment_review/commit_receipt.json`及`face_only_cleanup.json`。



<!-- identity-voice-20261018 -->

- 2026-10-18 人脸身份识别与语音登记已加载：当前UI目录 `/home/root/aura-voice-enrollment-20261018/candidate-0fbb41aebfbd/runtime`，相机目录 `/home/root/aura-identity-validation-20261018/candidate-d843e37e7d4a/ui_runtime`，实际相机`--config`为该stage的`camera_live_config/board_camera_ui.json`，身份结果有效期3秒。原1.5秒导致登记入口闪烁，修复后20秒37次采样均可登记；匹配阈值、目标失效检查、DPU与跟踪配置保持。PC最终83项/26子用例、Linux124项、真实素材加载后语音任务初始化通过。语音流程为开始对话后“帮我登记身份”→“我叫……”→“确认登记”，也可取消/纠正。板端核对录音起点与当前目标、单人、boot/服务/轨迹代次和身份库修订；匹配COMMITTED后才播成功，LLM没有数据库动作。普通聊天仍原27B/OmniVoice16，无额外ASR/LLM；登记台词不写普通历史。身份库仅板端`/home/root/.local/share/aura/identities.sqlite3`，不打包模板/现场照片。真人登记、听音、离场重返是否通过必须查`deliverables/2026-10-18_identity_validation`的最新`verification_summary.json`、实录与`listening.json`，不能将加载就绪当真人闭环通过。尚非个人长期聊天记忆、说话者识别或防照片冒认认证。启动失败的旧候选已自动回退，历史素材脚本污染sys.path的根因已修复。回退先用`rollback_voice.py`恢复上一UI，再用`rollback.py`恢复更早UI/相机，均先结束对话，保留身份库和旧归档。LLM数据仍在D盘。

<!-- /identity-voice-20261018 -->



<!-- automatic-conversation-20261018 -->

- 2026-10-18 自动轮流对话最新活动目录为 `/home/root/aura-automatic-conversation-20261018/candidate-b1b08f8b0b2b/runtime`，取代旧stream-playback活动路径。已通过真实自动接话、结束后重新开始仍记得绿色、用户听音和结束停止验收；原27B已验证颜色偏好超出四轮仍可召回。 `automatic_turns=true`；700ms静音端点、200ms前导，录音与生成播放互斥，匹配完整播放ACK后500ms再听；结束/取消禁止过期事件重启。PC主批次65通过/26子用例、worker后续7项（重叠）、Linux53项通过；颜色记忆修复最终70项/26子用例通过。board_model_host增加同boot/session的明确颜色偏好，完整播放ACK后确认、超出原四轮时预算内补原问答2条，问候前缀parser_revision=2，支持更改/否定/忘记；不新增模型调用，不修改系统人设提示，尚非通用或落盘长期记忆，8792/UI重建会清空。原27B/IQ4_XS/OmniVoice16与视觉模型配置保持；相机后来另有停止/启动，最终PID应动态查8790，不能称全程相同，另有UI服务重建记录。没有全双工/声音打断，不宣称稳定3秒。证据与回退入口 `deliverables/2026-10-18_automatic_conversation/README.md`；以前验收ZIP指纹不能当成本版源码清单。

<!-- /automatic-conversation-20261018 -->

- 2026-10-18 独立加速候选实测已完成：`deliverables/2026-10-18_dflash_trial/README.md` 与统一分析 `27B独立加速实测_20261018.md` 是本轮入口。当前5060 Ti 16GB上GPU DFlash与OmniVoice16共存变慢；TTS CPU停车更慢、清缓存无可靠收益、CUDA Graph扩展24次优势不足，均未接入正式通道。原27B/IQ4_XS、生成参数、声线、业务源码和五项延迟开关保持，原8792/ASR及真实27B回复恢复验证通过。只在model_storage.local.json增补draft_directory，草稿和分段位于D:/AIModels/dflash2-qwen3.8-27b，不允许复制到共享目录；候选未作为主模型使用。首PCM实验不是整机稳定3秒或板端新听音验收。相机应从8790/health动态获取PID；本轮核查时为141309，boot未变、YOLOX与DPU健康，不得继续硬编码987并宣称PID一直未变。`probe_cuda.json`曾被辅助实验覆盖，DFlash整组依据改用dflash_summary_retained.json、四组runner日志和独立pipeline JSON；首次CPU回退数据明确排除。



- 用户2026-10-18明确：KV260不新增语音模型或语音模型FPGA加速；语音识别、27B对话和TTS仍在电脑端。优化方向是电脑与板端之间的流式音频/控制传输、播放与同步，不更换已有视觉DPU/FPGA配置。



- 用户最新要求：大语言模型权重、下载分段及Ollama模型缓存统一放在项目外本地 `D:\AIModels`，禁止保存到 `E:\Win共享文件` 及其任何子目录。实际路径由 `aura/config/model_storage.local.json` 指定；代码、路径配置、模型分析和运行验证记录允许保存在共享目录。分析统一入口为 `E:\Win共享文件\语言模型分析\README.md`。ASR和TTS位置按原运行配置保持。



- 当前工作根目录为 `E:\Win共享文件\语音共享文件`。用户已明确：后续项目文件均保存在此目录，重点是已接通板端的本地大语言模型语音项目。

- 新增/修改的源码、配置、运行日志、生成音频、测试与交接记录写入本目录；D盘原项目为历史副本，不再作为默认开发或输出目录。

- 当前基线：Paraformer → Qwen3.8-27B Huihui破甲版 UD-IQ4_XS → OmniVoice16 → KV260 MCP01播放/口型。模型身份为 `aura-qwen3.8-27b-abliterated:iq4_xs`，Ollama本机11435，配置见 `aura/config/board_dialogue_model.json`。27B历史录音HTTP链路实测7.187秒通过；不当作新录音听音验收。已选“柔亮俏皮”参考、16步参数及原始参考转写保持，除非用户另行要求。

- 先读根目录 README.md 和 deliverables/2026-10-18_board_dialogue/README.md。验收范围以实录证据为准，不把服务就绪称为整机完成。

- 本机Python环境和SSH私钥可保留在原本机路径，不能将不可移植虚拟环境或SSH私钥当作共享交付物复制；换主机需独立配置。



- 板端起音修复基线：`gstreamer_audio_engine.py` 每次播放前置1秒启动静音，内容时钟扣除该时段。用户实测500ms仍首字不清、1秒及正式对话已通过；缩短前置需重新听音验证。详见 `deliverables/2026-10-18_voice_clarity/acceptance.json`。



- 2026-10-18后续已接入常驻音频和流式对话：本地 `aura/config/board_avatar_gtk.json` 的 `persistent_audio`、`streaming_conversation` 为true；活动板端目录为 `/home/root/aura-stream-playback-20261018/candidate-ec77f48a63de/runtime`。一次预热后保持设备打开，不再逐段增加1秒静音；用户已确认测试开头清楚、正式界面新录音听到完整回答。69项回归、真实提示/回答取消和MCP01共存检查通过；新录音单次正式回答约6.102秒，复杂题缓存提示约0.542秒、正式答案约26.658秒，均非外部声学测量。旧1秒引擎与原运行目录保留回退。详见 `deliverables/2026-10-18_stream_playback/README.md`。不要将缓存提示称为1秒有效作答或整机验收完成。



- 2026-10-18关机前首段优化：电脑端 `aura/config/voice_latency.json` 使用reply_first/early_sentence/coalesce_chat三个开关。短聊天在台词字段闭合时整段TTS，避免碎句间停顿；复杂题保留分句，原27B/IQ4_XS/OmniVoice16保持。74项回归通过。首版3.419秒主机首PCM不能当最终板端延迟；用户反馈首版停顿不自然，最终听音以 `deliverables/2026-10-18_latency_optimization` 的最新实录及反馈为准。下次启动与回退步骤见该目录README，模型权重仍在项目外D盘。





2026-10-18 关机前补记：连续回答已获用户确认；普通闲聊取消固定等待语音的代码已保存，75 项回归通过。该提示语策略尚未重启载入，下次启动生效，需再次试听。详见 deliverables/2026-10-18_latency_optimization/README.md。





2026-10-18 复启补记：用户已明确同意启动并测试；取消普通闲聊固定等待语音的修复现已载入8792服务，真实模型HTTP验证0次提示、1次整段TTS、首PCM5.203秒。该测试不实际播放，最新玩偶实录与听音以本轮resume证据为准；相机新boot的PID987，勿继续硬编码历史PID976。





2026-10-18 本轮复启听音已通过：用户确认“没有等待提示，回答自然”；新录音、无thinking事件、整段1次TTS和匹配播放ACK已验证。正式回答软件开口约5.293秒，未达到1秒。最新依据为resume_live_playback.json、resume_listening.json及verification_summary.json；不要继续将提示语修复标为尚未载入或听音待定。ASR仍将汐蓝转写为西兰，本轮未修正。





2026-10-18 内部字段优化：OllamaReplyStream 的reply_first映射已从长别名改为a/b/c，应用恢复reply_text/emotion/avatar_action。原27B、量化、上下文、思考参数、OmniVoice16、连续合成与无闲聊提示保持；75项回归通过。8次对照台词字段就绪中位数2.763→2.288秒，真实HTTP首PCM4.444秒；本轮新录音验收以 deliverables/2026-10-18_compact_reply_fields 的live_playback/listening/verification_summary为准。旧优化归档保持，不要将其旧指纹清单当作本轮源码清单；改前源码在本轮before中。





2026-10-18 短字段优化最终验收：正式界面新录音、匹配播放ACK及用户听音“连续自然，开头清楚”均通过；本轮软件正式开口约4.595秒，非声学测量或固定保证。最新归档在2026-10-18_compact_reply_fields/verified_source.zip，verification_summary状态应为PASS_COMPACT_FIELDS_FRESH_PLAYBACK_AND_LISTENING。75项回归通过，尚未达到1秒。





2026-10-18 称呼误听容错：新增common/spoken_input.py，仅在明确玩偶呼唤语境中解释已知同音名，原始transcript.text保留，input_adjustments记录改变；原ASR模型及8791不变，原27B提示补充语音容错、身份区分和关键信息确认。104项回归、4项真实27B文字探针及真实录音HTTP已通过，正式服务已载入。最新现场验收/归档为deliverables/2026-10-18_speech_tolerance；不要把以前已验收版本的源码指纹当成本版清单。未宣称任意发音错误都已解决，最终听音以该目录最新证据为准。





2026-10-18 称呼容错现场验证：本轮新录音原始西兰→理解汐蓝、自然回复无纠名、完整播放ACK均通过；本次软件正式开口3.742秒（单次、非声学）。用户听感仍以本轮speech_tolerance/listening.json及verification_summary为准。





2026-10-18 称呼容错最终听音验收通过：用户确认“直接自然接话，不再纠名”；新录音、称呼理解调整、自然回复及匹配完整播放ACK均通过。最终依据为2026-10-18_speech_tolerance/listening.json、live_playback.json及verification_summary.json；不要继续标为听音待定。104项回归通过，仅覆盖已确认称呼误听，保留原始ASR。





2026-10-18 思考路由修复已载入电脑服务：比较程度副词、普通话题及否定请求不再单凭子串强制深思；明确比较/计算等保留。106项回归、26个语境子用例通过，真实数学HTTP仍原生思考且174正确。称呼容错/27B/OmniVoice16/板端程序源码指纹保持。本轮归档和现场听音依据位于deliverables/2026-10-18_thinking_routing，不能用此前听音作为本轮比较语境验收。





2026-10-18 思考路由最终听音验收通过：同一现场转写“今天比较开心陪我聊聊”，旧规则reasoning、新规则chat；实录无等待提示、thinking字符0、一次整段TTS和匹配完整播放ACK通过，用户确认“直接聊天，没有等待提示”。本次软件开口4.953秒，不与其他台词时延直接比较。106项回归、26个子用例及真实数学174正确，最新证据/归档在2026-10-18_thinking_routing。不要继续标为本轮听音待定。



2026-10-18 多轮历史复用：voice_latency增加reuse_history=true，普通聊天在匹配完整播放ACK后保存原始JSON回复供下轮使用；原文字历史仍保留四轮，预算不足/快照失效/原生思考退回原路径，不新增长期记忆。118项回归及26子用例通过。两轮正式界面新录音正确记住绿色，第二轮日志exact_json/confirmed_history/2条消息，完整播放且用户确认“记住绿色，回答自然”；第二轮软件开口3.483秒为单例，不与不同台词首轮作提速A/B。最新归档在deliverables/2026-10-18_history_reuse，之前验收ZIP保留。另有开放缺陷：3次无历史HTTP探针2次复述问句，发生时未使用新缓存；新旧无历史请求体相同、两组固定种子流式回复相同，仍不能声称复述已解决，错误短答和TTS缓存耗时不作为提速成绩。后续优先完善回复质量检查与根因定位。原27B、量化、人设提示、ASR、OmniVoice16、板端及视觉源码保持，LLM数据仍在D盘。



2026-10-18 普通聊天防复述保护：common/reply_quality.py识别至少8规范字符的整句问句复制（可省略开头问候），OllamaReplyStream暂存仍与问句匹配的前缀，出现不同内容立即释放；确认复制时仅允许一次带纠正提示的27B再生成，沿用剩余预算与取消，错误文本/PCM/原始JSON不进入待播放或记忆。正常路径模型请求体、生产人设及采样保持，合法复述不拦；原生长思考与旧WAV接口保持原路径。138项回归及26子用例通过；真实原27B四轮后小林/绿色/十五、主动复述/错字改写通过；被拒绝的候选提示seed3可复现复制，真实纠正成功但台词就绪7.325秒，不能冒充提速。两个固定种子ABBA正常回复相同、纠正0次。服务已空闲重启加载，两次实际ASR/LLM/TTS HTTP首PCM3.618/3.929秒，均单段、无等待插播、纠正0次，尚未达到1秒。本轮新录音听音以deliverables/2026-10-18_reply_quality的live_playback/listening/verification_summary为准，不能沿用前轮验收；保护只缓解已知复制模式，完整底层根因仍开放。模型数据继续D盘，旧归档保留。



2026-10-18 防复述保护正常聊天现场听音已通过：用户确认“正常接话，清楚自然”，本轮新capture及request cb6615cb8a9a4a8d9c89bcffcef2e4be的完整播放ACK匹配，无等待插播、一次TTS、纠正0次、复制标记false，相机保持。软件开口5.726秒，台词准备2.813秒、TTS2.406秒，单例且非声学；下一步重点仍是27B台词准备与TTS。最新验证/ZIP仍在reply_quality目录，不再标为正常播放听音待定。原始ASR“你好啊西来今天过得怎么样”未被称呼规则改写，回复有“我是汐蓝哦”；不要宣称所有姓名误听已解决或自动把西来加入别名。错误纠正路径仅有单元/真实模型压力验证，未实际板端触发听音；完整底层根因仍开放。





2026-10-18 紧凑JSON通道最终验收：voice_latency增加compact_grammar=true，仅普通reply_first聊天经tools/native_grammar.py连接11435的Ollama所属唯一runner，核对外部模型路径、完整模板、2048上下文、1slot和已验证build b1-620d2225c；动态发现端口，不把实验51742写死进生产。保持原三字段、台词自由生成、表情枚举、空动作，约束JSON空白，保留原人设/采样/27B/IQ4_XS/OmniVoice16。每轮无prompt保活不生成词元；准备阶段不兼容则回退原Ollama，复杂思考与旧WAV仍原路径。新模块、dialogue_stream/voice_channel_source/board_model_host和开关已加载。150项回归、26子用例通过，真实新通道四轮后小林/绿色/十五、主动复述/错字改写、注入复制故障后一次纠正通过。实际自由生成+未缓存TTS的4次ABBA同台词/同PCM对照首PCM中位数2949.41→2826.22ms，约123ms/4.2%，各2个样本、范围重叠，不能保证固定收益或沿用固定台词约0.58秒实验。省略空动作字段和串行TTS实验被拒绝，生产继续三字段和重叠流水线。两次正式HTTP主机首PCM3.297/2.918秒；本轮新录音request dd3011e4027542ed9001b3871e6cbb4b确认新后端、无提示、单段TTS、纠正0次、完整播放ACK，用户确认“正常接话，连续自然”，软件正式开口4.095秒（单例非声学），相机PID987及boot保持。最新验证/听音/源码ZIP在deliverables/2026-10-18_gpu_scheduling，统一分析报告为紧凑JSON与GPU调度_20261018.md；不再标听音待定。内部runner接口依赖版本，首次发现有0.88–1.72秒开销，启动预热已覆盖；下次升级/换机需重验或回退。将compact_grammar=false并空闲重启8792即可回退，旧归档保留，LLM数据仍D盘。防复述完整根因和1秒有效作答目标仍未完成。



2026-10-18 原生流式TTS验证：见 deliverables/2026-10-18_streaming_tts_validation/RESULTS.md、verification_summary.json。原27B/IQ4_XS及62个原文件已校验；正式OmniVoice16和五项延迟选项保持。独立CosyVoice.cpp v0.2.0 + GGML b11723测试：Vulkan慢；默认CUDA快但内容不符；实际K=F16/V=F32、LLM与Flow FlashAttention关闭、25-token模式4条内容检查零差异，首PCM0.63–0.65秒。用户接受quick-1候选声线；不代表完整链路听音。与原27B三次文本联动首PCM3.12–4.32秒，未含ASR/板端。明确reasoning样本首字15.69秒且58×3算为156，后续需正确性校验，勿将其标为通过。自由回复还有待听音确认的转写/数字边界问题，未正式切换。所有候选TTS模型/分段均在D:/AIModels/cosyvoice3-streaming-validation，原LLM存储路径未变。最后恢复验证使用上一阶段完整权重SHA+不变文件标识/时间的复核，不伪称再次全量计算；源码62项重新核对。5090笔记本未实测。相机PID当前141309，仍必须动态读取健康状态，不硬编码。

