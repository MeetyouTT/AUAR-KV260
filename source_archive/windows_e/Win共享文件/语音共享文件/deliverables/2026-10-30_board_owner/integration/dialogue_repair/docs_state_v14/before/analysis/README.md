<!-- performance-dialogue-plan-20261031 -->
- [性能与对话平衡优化方案（2026-10-31）](性能与对话平衡优化方案_20261031.txt)：基于v10及已有实测的后续规划，按对话阶段分配资源；先解决采集余量和启动并发，再处理后台整理及回答延迟。候选改动尚未执行，现役状态仍以下方回执为准。
<!-- /performance-dialogue-plan-20261031 -->

<!-- board-business-live-20261030 -->
- 板端正式业务当前入口：/home/root/aura-board-business-20261030/production-5259eab11e42af13；startup SHA 1129a2a7af2b401537710d1a67651c79961c1b10198f5625ae6802e7ac99fd77，375份组件，source manifest SHA c575f5fc8eb55536e4ea1a8b926d5843e54f2068337691bba7bab61c8a3f01a5。
- 本次实读supervisor 811772、GTK 811885、相机 260102、boot 8100a7fd-0c6a-46c4-82b8-f874988a1521；PID仅为本次观测，下次先现读。
- 已取消唤醒词门槛，就绪后自动聆听、直接说话即可，无需称呼或开始按钮；连续采集与优先级作用域两门槛均有真实通过回执。当前采用半双工：生成/播放期间不启插话采集，完整播放ACK后自动恢复聆听。实际暂停/恢复后的磁盘偏好false→true往返已核验；实际取消本轮后自动rearm已核验。未新增实际冷启动/重启验收声明。
- 采用的前端配置仅按最终installed回执记录：{"asr_threads": 3, "capture_priority_nice": -10, "frontend_capture_process": true, "frontend_optimization": "baseline", "frontend_process": true, "frontend_threads": 1}；不将此前候选或静态hash当作已上线。
- physical_microphone_opened=true；physical_audio_acceptance_passed=false。真人ASR、实际播放/听感/口型和长稳仍未验收；采集通过不等于整机语音闭环通过。跟随false、机械FAULT/null，真实业务库及身份权限保留。
- Windows继续仅模型推理，固定27B/OmniVoice16与其他模型保护不变；不恢复旧Windows业务写者。
- 生产诊断只保存白名单metadata，不归档正文/PCM/窗口截图。来源：integration/listening_entry_fix/actual_automatic-listening-v10-null-status-fix.json SHA 06eac613790ceb4bccd5b9c55ec5d0aa60fe5e06464326ac777fe29e1ec7a43e；integration/production_business_acceptance/actual_ready.json SHA 1299ddd9d42f886ea909faf6a3b30ea287acb8392eedf1373a7a06662fc21628；integration/listening_entry_fix/actual_live_listening.json SHA bc933c67f52c7d86997311254b3861eb4f08e76cb7be5fd0d0142f033ba72299；integration/listening_entry_fix/actual_control_semantics.json SHA 85d6ae8f83879f00f271be8874e04a000150b286369ab9ca310c99899bacdcb3。
- v10显示空值修复及语音保活的最终接续见deliverables/2026-10-30_board_owner/integration/dialogue_repair/STATUS.json和板端性能分配与优化计划.txt。用户已确认v7连接复用的一轮声音连续完整（239次检查平均7.43ms、1个欠载包、完整ACK），不扩展为v10新听音验收；v10实际274.383秒同一采集流无GUI故障/重开/新增采集失败，8帧队列峰值5。启动初期第1代另有1次队列溢出已恢复，必须保留这个待优化项。直接语音监听开启或播放时每5秒保活显示；暂停且不播放时沿用原600秒熄屏，10分钟无人操作尚未专门验收。
<!-- /board-business-live-20261030 -->

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
[板端正式业务与真实记忆已接管](../语音共享文件/deliverables/2026-10-30_board_owner/板端业务正式接管与实测接续_20261030.txt)：311轮对话、239条旧视觉历史及原声纹库已迁入板端，唯一写者与持久receipt通过；空闲27B摘要已实际提交后清正文。当前e345/368来源，构图配色保持。Windows仅模型8797无TTL，常用入口已转model-only，新增临时原文snapshot已清除。真人音频与长稳仍待[现场剧本](../语音共享文件/deliverables/2026-10-30_board_owner/实机音频测试剧本_20261030.txt)，不能把自动/静音验证当真人验收。下方“真实库未迁/清理未开”属于此前阶段。
<!-- /archived-board-business-live-ac9be342ffbf933a-863ec603a48d -->




<!-- board-owner-resume-20261030 -->

[当前构图与配色](../语音共享文件/deliverables/2026-10-30_board_owner/构图配色调整_20261030.txt)：雪妃已改为腰部以上近景、占满423×516角色区，界面采用奶白、藏蓝与酒红；实际画面与导航条检查通过，默认启动配置更新。当前来源为4c788/304pins，后续以本记录为准。



[雪妃形象与人格已正式切换](../语音共享文件/deliverables/2026-10-30_board_owner/形象人格正式切换记录_20261030.txt)：按用户“依据既有减负潜力直接切换、不再继续测试”的最新授权，板端已使用新原生形象和同版本978B人格，持久启动入口生效，画面与配对就绪。原记忆、身份及业务设置路径保留；业务迁库、实际语音与长稳收尾仍待后续调试。下方“仍为候选/原形象恢复”属于此前评审阶段。



[最新形象与人格替换评审](../语音共享文件/deliverables/2026-10-30_board_owner/character_persona_candidate/替换评审_20261031.txt)：新原生形象与板端完整业务、雪妃人格已实际就绪；两次正常优先级公开音频队列测试通过。空闲约15.83fps，同时处理音频约14.21fps，仍未通过16fps显示门槛或有人长稳。可以继续规划替换，正式形象仍保留；试验后原入口和286份组件已核对恢复，临时guard已移除。



[Qwen 视觉模型清理回执](../语音共享文件/deliverables/2026-10-30_visual_simplification/model_removal.json)：重新核对板端现役 286 份绑定、图片上传停用与旧端口关闭后，已删除 D 盘该视觉模型的三份文件，共 1,552,463,811 字节。下方早期“尚未删除”是历史状态；其他语言模型及语音资源保持。



[重启后的实施与实测状态](../语音共享文件/deliverables/2026-10-30_board_owner/IMPLEMENTATION_STATE.json)：实际板端可信时间、自然经过五分钟后的真实27B摘要入库再删公开夹具正文、检索遗忘与27B/OmniVoice链路已通过。真实用户库尚未迁移，生产正文清理未开启；有人时正常优先级音频仍有容量缺口。200ms重复检测候选与同权重优化、自身优先级组合两次通过公开音频采集/端点/ASR，但显示帧率仍有下降，未当作整机验收。相机短测已继承最新checkpoint恢复原r17入口。



[Windows模型运行看板](../语音共享文件/打开模型运行看板.cmd)已可用，展示真实任务状态、CPU/内存/GPU/显存与一分钟趋势；[交付和证据](../语音共享文件/deliverables/2026-10-30_runtime_dashboard/handoff.json)。仅观测运行数据，不改变业务归属。



用户已允许在确认减负潜力后规划新形象，并要求同步人格。[形象与人格替换方案](../语音共享文件/deliverables/2026-10-30_yuki_native_validation/native_integration/replacement_planning/REPLACEMENT_PLAN.txt)与[板端人格候选](../语音共享文件/deliverables/2026-10-30_board_owner/character_persona_candidate/REVIEW.txt)已整理；内存和渲染模块CPU收益明确，整板收益仍待综合负载验证。当前形象未正式替换，称呼/唤醒/人格/渲染将按同一版本联动。

<!-- /board-owner-resume-20261030 -->



<!-- shutdown-handoff-20261030 -->

[本轮关机接续回执](../语音共享文件/deliverables/2026-10-30_board_owner/SHUTDOWN_HANDOFF.json)：候选合并回归271通过、1项平台跳过，五个现有生产库只读完整性检查通过。KV260正常Power down、Ubuntu由用户确认正常关机，Windows由用户手动关闭。源码、证据和待办已保存；真实库未迁、生产正文清理未启用、人物未替换。下方旧阶段描述按其当时时点阅读，下一轮以本回执和实施状态重新核验。

<!-- /shutdown-handoff-20261030 -->



<!-- board-business-owner-20261030 -->

[最新硬边界：板端业务主控与 Windows 模型接口](统一时间轴记忆与稳定性优先_20261030.md)：全部业务处理和持久存储归板端，Windows只通过网线运行现有27B与OmniVoice、返回输出。板端负责五分钟详细记忆、空闲摘要调度、校验/入库/删原文与检索。旧保留Windows权威库、迁移后置安排已被替代；当前部署尚未全部符合，Ubuntu提示词已更新，本次未部署或迁库。

<!-- /board-business-owner-20261030 -->



<!-- five-minute-summary-only-20261030 -->

[最新方案：五分钟详细记忆与摘要检索](统一时间轴记忆与稳定性优先_20261030.md)：用户明确长期只留摘要。近五分钟保留详细内容，超时闭合内容空闲压缩、核验保存后删正文，必要事件/权限/版本索引保留；对话优先，不新增常驻模型。Ubuntu提示词已同步；新机制与生产原文清理尚未实施。

<!-- /five-minute-summary-only-20261030 -->



<!-- timeline-stability-priority-20261030 -->

[最新方向：统一时间轴记忆与稳定性优先](统一时间轴记忆与稳定性优先_20261030.md)：用户明确先简化并稳定记忆效果。复用现有权威库和模块统一事件来源、写入/查询、当前事实与遗忘规则，迁库、ASR迁移和视觉扩展后置；Ubuntu提示词同步更新。本次是方案与交接更新，没有新部署。

<!-- /timeline-stability-priority-20261030 -->



<!-- board-vision-handoff-20261030 -->

[当前：板端视觉信息采集记录与处理](板端视觉信息采集记录与处理_20261030.md)：用户决定移除Qwen视觉模型，收拢至YOLO/跟踪/人脸。Windows r12及160回归、真实公开语音通过，8810关闭；板端上传器停用补丁两次因日志路径校验自动回退，交Ubuntu接续。原记录保持、监听关闭；权重清理、结构化视觉事件落库、ASR和记忆迁板端尚未完成。[接续提示词](../语音共享文件/deliverables/2026-10-30_visual_simplification/Ubuntu接续提示词.md)。

<!-- /board-vision-handoff-20261030 -->



<!-- identity-gpu-r11-20261030 -->

[当前：渐进身份关联与显存协调 r11](../语音共享文件/deliverables/2026-10-29_parallel_interaction/README.md)：代码已部署，637 合并回归、真实非缓存语音及 ARM 公开输入通道通过；最终采样最低空闲显存 1656 MiB，其他模型和原始记忆来源保持。a1/a2 临时代号、明确本人登记后的姓名/人脸/声纹关联及冲突/撤销已实现，现场声纹仍未标定。真实人脸 ID/模板指纹到 Windows 的网络验收被自动审批拦截，待用户具体授权，未冒作通过。当前 voice voice-identity-gpu-20261030-r11，板端286绑定；下方 r9/279pins 为历史。监听关闭，机械原 FAULT/null 保持，整机和真人验收仍未完成。

<!-- /identity-gpu-r11-20261030 -->



<!-- audio-animation-polish-20261029 -->

[最新：句中断续与动作素材修复](../语音共享文件/deliverables/2026-10-29_audio_animation_polish/README.md)：已部署并通过自动验证。供音IPC阻塞路径修复，真实界面静音长句18.28ms/0欠载；恢复四套现有身体及短轮素材变化。其他模型、记忆、相机和机械保护保持。真人听感待集中复测，说话长帧与整机仍未最终验收；当前监听关闭。

<!-- /audio-animation-polish-20261029 -->



<!-- windows-services-recovered-20261029 -->

[最新：Windows服务恢复与板卡环境核对](../语音共享文件/deliverables/2026-10-29_service_recovery/README.md)：现有r9七类服务恢复，两轮板端真实语音通过；原数据、模型与并行启动优化保留。转轴因boot/FDT/benchmark固件/VART与wide驱动不符保护停用，未复机。当前监听关闭，迁移暂缓；整机尚未最终验收。

<!-- /windows-services-recovered-20261029 -->



<!-- chat-memory-r9-20261029 -->

[当前：对话/记忆分流与TTS空闲显存管理r9](../语音共享文件/deliverables/2026-10-29_chat_latency/README.md)：355回归、14步真实记忆、5项ARM检查通过。普通日期聊天不再误触历史，TTS首次就绪观测归还约2.71GiB空闲缓存且模型保持驻留。原数据/其他模型/板端保持，监听关闭、迁移暂缓；延迟长尾及整机仍未验收。

<!-- /chat-memory-r9-20261029 -->



<!-- voice-handoff-fixed-20261029 -->

[当前：识别后回聆听的503交接修复r6](../语音共享文件/deliverables/2026-10-29_listening_bounce/README.md)：285相关回归、真实板端三种取消后立即接话及两项唤醒检查通过。取消时保留已运行TTS、丢弃旧结果，交接最多5秒且不增加原预算；其他模型、用户记忆与板端保持。下方r4记忆功能保留，本次故障用户已确认正常，普通聊天长尾等整体待验项保持，迁移暂缓。

<!-- /voice-handoff-fixed-20261029 -->



<!-- windows-dialogue-memory-polish-20261029 -->

[当前：Windows对话与记忆r4实现及效果验证](../语音共享文件/deliverables/2026-10-29_dialogue_memory_polish/README.md)：明确事实自然直答、1—32中文/数字索引历史和旧写入来源保护已部署。267相关回归（含旧210）、12步实际记忆、7项语音功能及板端网线两轮通过。重复事实首PCM中位数2.656→0.110秒，后三次TTS缓存命中；首次双方未命中缓存的单次4.641→1.453秒。普通聊天对照未提速，长尾仍开放。原记忆/视觉/声纹来源哈希、其他模型与板端保持，迁移暂缓；整机与跨天真人验收未完成。

<!-- /windows-dialogue-memory-polish-20261029 -->



<!-- windows-memory-controls-20261029 -->

[Windows对话与记忆r3：已部署](../语音共享文件/deliverables/2026-10-29_memory_controls/README.md)：遵照用户“先完善后考虑迁移”，权威库仍Windows。新增事实更正历史、按时间/主题删除的预览确认、来源链失效和记忆指令跳过无用上下文。210项相关回归及实际语音记忆/取消恢复通过，原始来源哈希保持；保留compact_grammar=false和其他模型/板端。普通语音与前端仍有长尾，跨天真人体验待验，迁移暂缓。



<!-- voice-latency-repaired-20261029 -->

[语音延迟修复实际回执及两端前后实测](../协作任务/2026-10-29_语音延迟修复/Windows_执行回执.md)：r2仅关闭compact_grammar，限定重载已READY、板端实读false。LF配置SHA与Ubuntu一致；其余开关、27B/Paraformer/OmniVoice16、音色和记忆能力保持。启动约150秒；原生fallback检查路径已移除，本机暖态首PCM仍有长尾，未声称稳定整体提速。其他服务及板端保持。

<!-- /voice-latency-repaired-20261029 -->



<!-- runtime-ownership-audit-20261029 -->

[全项目Windows/板端功能归属清单](../语音共享文件/deliverables/2026-10-29_runtime_ownership/ownership_catalog.json)：结合实际监听进程、健康、板端入口/源码核对16类功能。Windows保留语音/视觉推理、记忆与权限、声纹和动画合成；实际人脸主链已经在板卡DPU，Windows SFace仅保留服务。8791/8792存在两份Paraformer加载。核查无运行变更，不能把目录中的离线候选算作已部署功能。



<!-- timeline-summaries-deployed-20261028 -->

[时间轴后台情节/日摘要：已部署并通过自动验收](../语音共享文件/deliverables/2026-10-28_timeline_summaries/README.md)：用户明确允许实际部署，r2 / device-timeline-v2已提交。169 Windows / 64 ARM相关回归互有重叠；实际画面日摘要、板卡历史语音、单探针删除/迟到ACK拒绝、普通语音取消恢复及原数据库来源哈希保持通过。保护并行任务新的279项板端绑定及READY/1576µs，UI/相机未重启。首次冷启动超时回退、第二次就绪，波动仍待观察；权威库仍Windows，PS迁库和跨天真人验收待后续。下方各阶段状态为历史。



<!-- timeline-memory-deployed-20261028 -->

[时间轴记忆第一版：已部署](../语音共享文件/deliverables/2026-10-28_timeline_memory/README.md)：统一来源和日期/主题检索、跨开机视觉事件、30天/10000事件上限及派生回复遗忘已接入。144 Windows/39 ARM专项互有重叠；实际27B、公开录音语音及真实视觉事件重启保留通过。数据库权威仍Windows，后台日摘要和PS迁库待后续。



<!-- timeline-memory-design-20261028 -->

[时间轴记忆与视觉融合方案](时间轴记忆与视觉融合方案_20261028.md)：按用户提出的时间轴方向，统一对话、视觉事件和个人事实的来源索引，规划情节摘要、时间检索、时钟校准与级联遗忘。当前视觉仍为 24 小时/同 boot 缓存；本项为设计，未改生产库或部署。



<!-- device-skills-deployed-20261028 -->

[语音独立与板端外设接入](../语音共享文件/deliverables/2026-10-28_device_skills/README.md)：新版已部署；实际语音/视觉问答/定时观察与历史回忆/声纹流程通过相应自动验证。短呼唤词、说话长帧、现场声纹标定与整机真人验收仍开放。



<!-- consolidated-interaction-20261027 -->

[玩偶集中自动验收与待验事项](../语音共享文件/deliverables/2026-10-27_final_interaction/README.md)：软件回归、真实公开录音链路、静音PCM/暂停取消恢复完成；机械因重启绑定不匹配保持FAULT，整个玩偶尚未最终通过。



<!-- interaction-polish-final-20261027 -->

[玩偶交互提示修复与当前进度](../语音共享文件/deliverables/2026-10-27_interaction_polish/README.md)：GUI正式部署，16fps门槛通过；麦克风引导、播放/处理提示、语音配置提示及送显帧率修复。跟随按授权停止，现场验收仍未全部完成。



<!-- windows-portrait-final-20261027 -->

[Windows画面已部署16fps与验收报告](../语音共享文件/deliverables/2026-10-27_windows_portrait/README.md)：12/16fps原生送显通过，24fps未达间隔门槛而保留16；实际UI断线本地8fps/恢复、静音真实PCM口型和设置页布局通过。跟随/麦克风关闭，等待心跳已删除；其他模型及D盘存储保持。持续实聊稳定性及新版真人验收仍待完成。下列等待部署描述为历史。



<!-- windows-portrait-implementation-20261027 -->

[Windows画面合成实现与等待部署](../语音共享文件/deliverables/2026-10-27_windows_portrait/README.md)：CPU合成、PCM时钟归属、取消和断网回退已实现并通过隔离测试；实际12/16/24fps尚未验收，正式仍8fps。用户选择保留当前持续跟随，当前聊天心跳只读等待其结束后接续，不能停止跟随或提前重启UI。四项Windows服务可达，其他模型保持，LLM仍D盘。



<!-- animation-dialogue-auto-20261026 -->

[最新：动画与对话自动验证及正式界面接续](../语音共享文件/deliverables/2026-10-26_animation_dialogue/README.md)：新版正式UI已部署，访客/监听关闭；Windows三服务r3健康。四动作、嘴型/身体及真实网线公开WAV链路通过，短时原生待机约8.08fps。新版真人体验、视觉就绪和机械随动仍待完成。[Windows合成提帧初测](../语音共享文件/deliverables/2026-10-26_animation_dialogue/fps_probe/README.md)显示CPU合成及24fps原始RGB网线传输有余量，正式送显尚未迁移，不能称屏幕已24fps。

<!-- /animation-dialogue-auto-20261026 -->



<!-- system-completion-auto-20261026 -->

[个人档案与长期记忆接入（2026-10-26）](../语音共享文件/deliverables/2026-10-26_profile_memory/README.md)：Windows明确授权的个人记忆后端已加载并通过真实公开WAV检查，303项相关回归/27子测试通过；默认访客、跨会话明确事实、更正遗忘及旧ACK屏障已实现。板端选档按钮基于实际活动版本最小合并并通过独立客户端/隐藏GTK检查，正式UI尚未切换。无真实个人档案创建，声纹自动解锁未启用，现场与整机任务仍待继续。



[玩偶自动修复与验收（2026-10-26）](../语音共享文件/deliverables/2026-10-26_system_completion/README.md)：用户不在现场，先自动测试、迁移后置。本轮323项回归及27子测试通过，公开录音真实Windows链路/取消恢复、板端网线两轮接收与600帧并发前端通过；8791/8792/8795就绪。语音超时/归属/健康/完整启动修复生效，转轴r11仅独立候选未切换，监听false保持。项目仍有绝对源期限、个人身份挂接、平顺跟随及现场/长稳验收缺口。



<!-- board-migration-simulation-20261026 -->

[板端迁移实施方案（2026-10-26）](板端迁移实施方案_20261026.md)：按业务状态/协议拆分→单独VAD→ASR与声纹→TTS/小模型四批推进，明确板端唯一记忆写入者、真实数据一致迁移、播放ACK/遗忘版本屏障及回退。当前仅设计，未改生产接口或迁库。



[Windows功能迁往KV260：离线模拟与候选核验（2026-10-26）](板端迁移模拟_20261026/README.md)：155项不同逻辑回归及7组标准库集成场景通过；真实CPU测试覆盖ASR、VAD、公开声纹和两种已有轻量TTS。记忆/上下文/规则/声纹库优先迁PS；单独VAD有历史板测余量，ASR/ECAPA仍待ARM和整机负载验证；VITS内容与Kokoro速度存在限制。未进行ARM仿真或本轮上板，未部署/切换生产模型，未复制LLM或个人库。



<!-- identity-motion-followup-20261021 -->

[人脸、声纹和机电接续](../语音共享文件/deliverables/2026-10-21_identity_motion_followup/README.md)：人脸原因诊断与提示修正、声纹归属校验离线候选及机电只读预检已完成；正式服务未切换。现场转轴Boot/FDT不匹配，当前为benchmark固件而非视觉舵机联合固件，不能只改boot ID恢复。声纹公开同人跨句约0.729、异人约0.055，不能直接使用0.80；现场标定仍待完成。



<!-- environment-front-end-evaluation-20261021 -->



<!-- local-open-source-selected-20261021 -->

[本地开源首阶段已接入](../语音共享文件/deliverables/2026-10-21_environment_frontend/INTEGRATION.md)：用户已选择本地开源，GTCRN+Silero v5在电脑CPU运行，313回归通过、监听保留。正式入口更新，声纹/电视及旁人人声仍待后续接入和实测；下方隔离与路线未选状态为历史。



[环境声成熟前端隔离验证（2026-10-21）](../语音共享文件/deliverables/2026-10-21_environment_frontend/README.md)：GTCRN＋Silero v5及现有ECAPA复用验证完成。板端组合不实时，电脑CPU流式路径337帧往返P95约3.71ms（不含算法/回答延迟）。117相关回归/1跳过；真实环境和说话者过滤尚未验收，正式922dab入口、监听及回声保护保持。未新增个人录音/模型服务，未部署候选。



<!-- motion-binding-followup-20261021 -->

[动画动作绑定调度优化（2026-10-21）](../语音共享文件/deliverables/2026-10-21_motion_binding/README.md)：正式de989bf024a9从fe6f保留音频前端/预算/回声/记忆/渲染，修复上一动作期间静默丢控制、迟到反应和间隔基准，增加有限跳过原因记录。254回归/真实素材及15专项通过，UI-only新60秒约8.02fps/P95约145ms，非渲染收益声明。最终音频就绪/无错，原监听false保持，未主动播放/开麦，新真人动作效果未验收。



<!-- snapshot-budget-20261021 -->

[状态快照优化与阶段性能日志上线](../语音共享文件/deliverables/2026-10-20_avatar_24fps/SNAPSHOT_OPTIMIZATION_20261021.md)：最新正式922dab49a74f，保留语音/回声/记忆/身体动作/pan，PC未动。同输入复制26.51→8.97ms；176回归+4专项通过，新版受控90秒8.012fps/P95约135ms/CPU约93%，恢复监听true/音频就绪。新增按阶段的后台有界性能记录，不记正文/录音；受控前后历史不同及新版真实长稳边界明确，下文bd9e真人通过不自动沿用新版。



<!-- human-dialogue-render-check-20261021 -->

[真人对话通过与画面日志核查](../语音共享文件/deliverables/2026-10-20_avatar_24fps/HUMAN_DIALOGUE_RENDER_CHECK_20261021.md)：用户确认bd9e真实对话通过，16轮流式回答完整播放；当前滚动约7.90fps/P95 191ms/P99 246ms，仍有长帧。没有整轮分阶段渲染历史，严格稳定8帧与长稳不能填通过；本轮仅只读核查，服务与监听保持。



<!-- interaction-render-fix-20261021 -->

[实际交互复查与渲染合成修复（2026-10-21）](../语音共享文件/deliverables/2026-10-20_avatar_24fps/INTERACTION_RECHECK_20261021.md)：实际监听/实聊0e98约6.5–7.3fps、P95约267–351ms，旧暂停短测不能代表实聊稳定8。bd9e合成修复已上线，身体采样21.92→5.67ms且40采样像素完全一致；176回归通过，受控同场UI CPU约112%→92%、送显P95约201→132ms，缓存语音约8帧/P95 138ms。恢复监听true后另做被动观察，PC、回声、动作、记忆与pan保持，下文旧入口为历史。



<!-- speech-motion-connected-20261021 -->

[说话与丰富动作已连接（2026-10-21）](../语音共享文件/deliverables/2026-10-20_avatar_24fps/ACTION_CONNECTION_20261021.md)：最新正式UI为0e98f7830e27，保留固定8帧并复用真实身体序列，确认/否定/惊讶/困惑按PCM时钟调用对应素材，取消旧代次。90秒7.994fps，缓存语音7.891fps/P95约155ms；176板端、73项PC与20项素材/合成专项通过，正式ASR→27B→TTS控制先于PCM验证通过。PC首句/模型/记忆规则与回声/pan保持，监听true/IDLE_READY。语义规则保守，不强加动作；连续真人体验和长稳尚未验收，下文f8e/a3c8“当前”入口为历史。



<!-- stable-avatar-20261021 -->

[板端稳定8帧与动作连接（2026-10-21）](../语音共享文件/deliverables/2026-10-20_avatar_24fps/README.md)：10帧与无固定送显8帧均失败回退；固定deadline单帧送显8帧f8e已提交，90秒平均7.991fps/P95约131ms，缓存语音8.176fps，UI CPU约148%降到88%。176回归与4项调度/取消测试通过，监听true/IDLE_READY，保留a3c8回声保护和PC首句/记忆规则。非持续真人实聊长稳结论。动作与持续说话身体帧仍在隔离验证，PC未改；下文旧UI根为历史。



<!-- environment-speaker-research-20261021 -->

[环境干扰与声纹：成熟方案调研（2026-10-21）](环境干扰与声纹_成熟方案调研_20261021.md)：遵循用户优先复用成熟组件的要求，保留已有SpeechBrain声纹原型，普通噪声优先比较WebRTC/RNNoise与Silero VAD；旁人/电视人声另考察Quail Voice Focus，明确其非固定身份锁及授权联网要求。Krisp近场限制、NVIDIA Speaker Focus Early Access、成品阵列和Light-ASD的适配边界均已核对官方资料。本轮仅调研，无新模型、开麦或部署，未占用动画设备窗口。



<!-- latency-human-accepted-20261021 -->

[回答延迟真人验收（2026-10-21）](../语音共享文件/deliverables/2026-10-21_response_latency/human_latency_acceptance.json)：用户确认“明显快了，等待可以接受”。结合此前安静播放和真人插话通过，当前首句优化与回声保护组合受控体验验收通过。噪声/多人和持续实聊长稳仍未验收；下方待反馈状态保留作历史。



<!-- echo-human-accepted-20261021 -->

[回声与插话真人验收（2026-10-21）](../语音共享文件/deliverables/2026-10-21_echo_barge_in/human_acceptance.json)：用户确认“安静时正常播放，插话后停下并回答新问题”，a3c8一次受控自身播音连续性和真人插话通过。回答延迟、噪声/多人和长稳仍待验收；下方待复测状态为历史。



<!-- echo-current-20261021 -->

[回声误打断修复（2026-10-21）](../语音共享文件/deliverables/2026-10-21_echo_barge_in/README.md)：用户报告自身播音被当成插话，已上线取消前转写核验保护，当前UI为a3c8，免点击监听开启，原PC首句优化保留。104项PC/304项板端及隐藏界面通过；安静实放9.21秒未误触发，但无待核验候选，不能称现场ASR否决或真人通过。真人安静播放、真实插话及延迟待复测；长稳仍未验收。下方旧根与阶段验收保留作历史。



[回答延迟首句优化（2026-10-21）](../语音共享文件/deliverables/2026-10-21_response_latency/README.md)：已上线并恢复监听，原27B/OmniVoice16保持；同文字多句对照首PCM约5.35→3.36秒，短句无明确提速。等待真人开口延迟与连续性反馈，长稳未填通过。



最新验收：e064合并版已获用户“两轮都有声音，开头完整，无需重复”确认，受控两轮接话通过。[验收证据](../语音共享文件/deliverables/2026-10-20_listening_timing/human_integrated_acceptance.json)。30分钟长聊等待准备反馈，尚未验收。下方旧阶段状态保留。



最新运行基线：动画任务已将5a0聆听修复合并到e064渲染版并交还，监听开启；新组合真人接话和长稳尚未验收，原5a0两轮真人通过记录保留。见[合并交接记录](../语音共享文件/deliverables/2026-10-20_listening_timing/render_handoff.json)。



[实时对话开始聆听时机（2026-10-20）](../语音共享文件/deliverables/2026-10-20_listening_timing/README.md)：提前准备收音、视觉短缺保留、ACK/尾音期间下一句无缝交接已上线5a0，保留RGB565/pan及记忆；289板端/225PC/完整隐藏界面通过，监听true；用户确认“两句都接住，开头完整，无需重复”，本版受控两轮聆听时机真人验收通过。原单次声音插话及记忆更正/遗忘真人已通过，长稳未完成。



[当前对话可控记忆（2026-10-20）](../语音共享文件/deliverables/2026-10-20_memory_controls/README.md)：查看、更正、遗忘和清空已加载8792，206项相关回归及原27B/正式HTTP检查通过；保留新RGB565/pan和声音打断，用户已恢复免点击，真人声音插话及记忆更正/遗忘单次验收通过；个人长期记忆和长稳仍待完成。



[玩偶系统完成度评估（2026-10-20）](玩偶系统完成度评估_20261020.md)：核心语音聊天、免点击两轮、声音打断、会话记忆更正/遗忘及最新聆听时机均有受控真人通过；当前监听开启。个人长期记忆、身份稳定性、动作接入和整机长稳尚未完成。下方各日期专题保留历史阶段记录，当前状态以本段和最新交付为准。



## 板端动画24fps候选（2026-10-20）



[原生渲染验证记录](../语音共享文件/deliverables/2026-10-20_avatar_24fps/README.md)：最新e064三线程/200ms诊断调度版在5a0聆听时序上受控保留，同场待机17.2→21.1fps、p95间隔99.7→72.6ms，CPU基本持平；原RGB565/CUBIC库和全部聆听业务保持，143回归/画质/完整显示检查通过，监听true已恢复，pan及原启动覆盖保留。仍未稳定24fps，21.1仅暂停监听待机短测；旧版真实说话10–12fps未被本轮复测覆盖。动作接通后置，已交还对话任务窗口，后续查状态快照及线程争用。



## 最新：免点击对话与接续修复（2026-10-20）



[声音打断与接话实施记录](声音打断与接话_20261020.md)：新版已合并原生双线程渲染并启用；本次9.22秒受控安静播放0误触发，原生初始化警告及旧失败保留。活动源码/原免点击/相机身份数据核对通过，真人插话及新回答听音尚待用户反馈。



[免点击对话与连续交谈修复](免点击对话与连续交谈修复_20261020.md)：本轮文字慢卡与黑屏记为失败，确认显示休眠并唤醒，用户确认恢复。恢复版已上线，增加交谈防休眠、已提交回答播完后再核对下一轮，修正实际HOME下开关恢复，继承动画优化并完成跨任务协调；电脑对话101项/板端完整176项通过，7项电脑动画测试缺cv2的失败记录保留、由板端覆盖。保留相机运动配置，用户已确认连续两轮均听到回答，本轮免点击和两轮听音通过，声音打断/全双工未完成。



## 已确认的角色身份（2026-10-19）



[汐蓝自我身份确认](汐蓝自我身份确认_20261019.md)：移除旧DeepSeek鲸鱼娘描述，正式为名字叫汐蓝的桌面玩偶助手；已加载，相关回归与原27B身份文字验证通过，其他配置保持。



[声纹身份原型（2026-10-19，10-20接续）](声纹身份原型_20261019.md)及[实施计划](声纹实施计划_20261019.md)：独立CPU环境、固定模型、标定工具及8项测试完成；新增板端可见点击采样，用户4段MCP01实录中前三段临时登记、第四段独立匹配0.8571通过原实验门槛，库1身份/1模板。同会话单次本人验证通过；陌生人、跨天标定及正式接入未完成。最新证据见[声纹开发记录](../语音共享文件/deliverables/2026-10-19_speaker_identity/README.md)。



## 当前优先：长对话能力（2026-10-19）



[持久会话与上下文第一版](长对话第一版_持久会话与上下文_20261019.md)已部署，原27B真实50轮文字五项指定检查及实际服务重启接续通过；真人长对话/听音待验收。接下来完成通用记忆管理与打断，降低延迟后置；人脸识别不阻塞匿名会话开发。个人档案、通用遗忘、声音插话仍未完成。



<!-- identity-failure-audit-20261019 -->

[身份认证失败详细审查与解决措施](身份认证失败详细审查与解决措施_20261019.md)：含活动版本核对、25图重算、官方公式/后端对照和优先实施路线；尚未部署变更。

<!-- /identity-failure-audit-20261019 -->



<!-- controlled-frontal-failure-20261019 -->

[登记后本人正脸识别实测](登记后正脸识别实测_20261019.md)：未通过，最高0.643/门槛0.80；登记照片及模板一致，检测/新画面匹配待定位。

<!-- /controlled-frontal-failure-20261019 -->



<!-- actual-enrollment-photos-20261019 -->

[本轮真实登记照片与证据](../语音共享文件/deliverables/2026-10-19_identity_capture_snapshot/README.md)：25张实际人脸图已保存、COMMITTED/成功播报通过；后续身份查询仍UNKNOWN，识别稳定性未通过。

<!-- /actual-enrollment-photos-20261019 -->



<!-- identity-capture-snapshot-20261019 -->

[语音登记入口快照修复](语音登记入口快照修复_20261019.md)：已加载；取消字幕不再使录音起点人脸状态失效，照片服务保持，新照片待采集。

<!-- /identity-capture-snapshot-20261019 -->



<!-- enrollment-photo-archive-20261019 -->

[身份登记照片保存与查看](身份登记人脸照片保存与查看_20261019.md)：已加载、真实新登记照片待采集，真实用户照片待采集；保留原语音与视觉配置。

<!-- /enrollment-photo-archive-20261019 -->



# 语言模型分析统一入口



[最新正脸模板选样修复](正脸模板选择与独立验证_20261019.md)：静止对照已完成；原身份保留，新版需明确更新后验收。



## 最新：称呼和身份问句分流修复



[本轮证据](称呼与身份问句路由修复_20261019.md)：真人“我是谁呀”转写/身份查询路由已通过，同轮完整播放但人脸仍UNKNOWN；含称呼的声学识别与真人听音未单独验收。





## 最新：登记成功，“我是谁”接入摄像头结果



[身份查询接入](我是谁接入当前人脸识别_20261019.md)：真人0.80登记已COMMITTED，库1条/修订14；新只读问句用当前有效人脸身份回答，不让聊天模型猜姓名。查询预检通过，真人新问句/重返仍待反馈。





## 最新：0.80试用已加载



[本轮加载与验证](人脸0.80试用加载_20261019.md)：用户同意后已改0.80，保留0.1分差及连续5新帧；边界/公开模型预检通过，库0条/修订13，重启后配置与原语音/人脸服务已恢复核实。真人本轮登记和重返尚待验证。





## 最新：阈值离线对比及清空身份库



[对比与删除记录](人脸阈值对照与身份库清空_20261019.md)：按用户要求已清空全部5条身份/模板，当前0条/修订13；0.80在失败会话末24帧的分数回放中24/24通过，正式仍0.85，缺不同人对照，最终阈值未标定。





## 最新：最后验证的真实失败分数



[真人失败诊断](人脸最后验证失败_实测分数_20261019.md)：77次验证仅16次通过、61次低于0.85，最佳连续3/要求5，超时；已确认分数稳定性仍未解决。提速/提示均生效，身份库5条/修订8保持。





## 最新：人脸验证失败与Windows CPU提速



[失败诊断与本轮部署](身份验证失败与CPU提速_20261019.md)：上一版真人验证超时且一直慢转头；已接入同一SFace CPU后端并补回自动看镜头提示，保留0.85，真人本版结果待验收。





## 最新：登记操作简化



[登记操作简化实施](登记操作简化实施_20261019.md)：一句话说登记和姓名，开头明确确认一次，后续自动取样验证保存。PC109项、Linux183项及预检通过，0.85保持；真人随后反馈验证失败，collect10/validate0后超时。





## 最新：自然转头视频自动选样



[自然转头视频选样实施](自然转头视频选样实施_20261019.md)：已替代固定左右姿势流程，从至少15秒视频画面自动选清晰人脸，保留0.85和明确确认。PC98项、Linux170项及真实模型/语音HTTP预检通过；部署库5条/修订8未变，真人自然转头和重返识别待验证。







## 最新：多帧人脸登记与独立验证



[多帧人脸登记实施](多帧人脸登记实施_20261019.md)：用户同意后已部署正脸4、左右各3选样和后续5份独立验证；保留0.85，验证和明确确认后才保存。PC80项、Linux161项和真实模型/语音HTTP预检通过，真人采样及重返识别仍待验收。



## 最新：人脸直接登记目标已部署



[人脸独立登记目标修复](人脸独立登记目标修复_20261019.md)：已去除登记对人体选择的依赖，登记窗口只显示112×112人脸，用户确认预览稳定。板端148项和真实模型预检通过；用户重返仍未识别，8次有效匹配最高0.583–0.677，低于保留的0.85。最新只读诊断库5条/修订8且过程中文件保持。UI/相机活动路径已更新，下面较早的状态检查保留为历史。



## 最新：当前模型运行状况



[2026-10-19模型现场检查](当前模型运行状况_20261019.md)：原27B/IQ4_XS实际驻留GPU，Paraformer与OmniVoice16服务ready，视觉DPU运行。GPU空闲328MiB；近5轮软件日志4轮5.5–7.9秒、1轮20.4秒。身份模块当前UNKNOWN、4条记录、门槛0.85，识别闭环未通过。本次只读检查，未发起生成或改动模型。



## 最新：人脸身份识别与语音登记



[人脸身份识别与语音登记](人脸身份识别与语音登记_20261018.md)：真实语音登记已COMMITTED，用户确认听到成功，但离场重返仍未识别。2026-10-19用户确认取景是本人并授权重新登记，已更新原身份并展示本次实际登记照片，库修订3、2条身份；实时识别仍未通过。用户明确保留0.85门槛，不部署0.363提案。既有CPU模型、DPU人体检测/跟踪及原27B/OmniVoice16保持。PC83项/26子用例、Linux124项与真实初始化预检通过；个人长期聊天记忆尚未接入。



<!-- automatic-conversation-20261018 -->

## 最新：自动轮流对话



[自动轮流对话实现与验收](自动轮流对话实现与验收_20261018.md)：已通过真实自动接话、结束后重新开始仍记得绿色、用户听音和结束停止验收；原27B已验证颜色偏好超出四轮仍可召回。 点击一次开始、停顿自动提交、完整播放及记忆确认后继续聆听；保持原27B与OmniVoice16。尚不支持声音打断或全双工，也未达到稳定3秒。

<!-- /automatic-conversation-20261018 -->

更新日期：2026-10-18。



## 人设与记忆：重新设计



[汐蓝人设与记忆重新设计](汐蓝人设与记忆_重新设计_20261018.md)：用户要求重新构思后，改为先建立本轮说话者与稳定身份的可靠归属，再分层处理交谈、个人事实和临时状态。本次只读现场确认身份识别未启用，语音协议未含用户身份；持久记忆尚未接入，正式业务源码已恢复改前状态，服务未重启。个人事实确认、助手完整播放及遗忘使用不同提交事件，不能全部绑定播放ACK。详见方案中的实施顺序与拟议验收。



## 最新：原生流式语音验证



[27B原生流式语音实测_20261018.md](27B原生流式语音实测_20261018.md)：Windows/5060 Ti独立测试已完成。保留原27B，CosyVoice3的CUDA高精度缓存、关闭FlashAttention、25-token分块首PCM约0.63–0.65秒，用户接受候选样本声线；与27B联动约3.12–4.32秒（不含ASR及板端播放），尚未稳定3秒。明确思考样本约15.69秒才出首文字，且算错58×3，需要正确性校验。自由回复存在待核对的内容/数字读法差异，正式服务仍原OmniVoice16；5090笔记本未实测。



## 存储约定



此目录保存分析、规划、测试报告和配置说明，不保存大语言模型权重、下载分段或Ollama模型数据。



- 当前27B模型：`D:\AIModels\qwen3.8-27b-abliterated`。

- 当前27B的Ollama模型库：`D:\AIModels\Ollama-AURA`。

- 当前业务代码：`E:\Win共享文件\语音共享文件`。

- 模型路径配置：业务目录的 `aura/config/model_storage.local.json`。



## 当前部署事实



当前模型为 Qwen3.8-27B Huihui社区破甲版 UD-IQ4_XS，服务标识 `aura-qwen3.8-27b-abliterated:iq4_xs`。模型权重大小14,403,496,864字节，已完成SHA256核验和导入。SHA256为 `d83adbbbaace8acdfcfe28004f779326176b9df00b4ec99dc6c24d749723d3b9`。



模型端口为本机11435，板端完整语音接口仍使用 `192.168.50.1:8792`。健康接口与真实回答已验证使用27B。主机为RTX 5060 Ti 16GB显存、约32GB内存。



真实多轮测试通过：首轮包含冷启动约87.875秒，后两轮约4.172/4.297秒；第二轮正确记住“小林”。历史录音完整语音HTTP链路为7.187秒，含识别约156ms、语言模型约3984ms、语音合成约3032ms；不包含录音时间、板端1秒启动静音及新录音实际听音验收。以上均为小样本，不能当作稳定延迟承诺。



## 文件索引



- [27B独立加速实测](27B独立加速实测_20261018.md)：用户授权后已完成DFlash与三种同声线TTS优化对照；GPU DFlash共存变慢，Graph扩展无可靠优势，均未上线，原运行路径恢复。含实际数据、质量一致性与证据限制。

- [保留27B：KV260与三秒交互方案](27B保留模型_KV260与三秒交互方案_20261018.md)：2026-10-18 GitHub与论文研究稿；说明KV260、现有Huihui权重、移动5090和三秒目标的边界。用户随后已授权独立验证，结果以上方实测为准，候选未正式启用。

- [27B首段延迟优化与关机前交接](27B首段延迟优化_20261018.md)：正文优先、完整短句合成与分段计时；73项回归及真实模型对照，含下次启动和回退说明。

- [汐蓝待完善清单与建议顺序](汐蓝待完善清单_20261018.md)：仅作缺口核对与规划，涵盖人设记忆、语气表情动作、自然语音轮转、可靠性、目标设备和整机接口；本轮不实施后续加速。

- [流式播放、思考提示与正式实录验收](27B流式播放与思考提示_实测_20261018.md)：已接入正式界面；69项回归与用户新录音通过，保留27B和原声线，明确缓存提示与有效答案的耗时区别。

- [两项方案复查与实测](../语音共享文件/deliverables/2026-10-18_voice_recheck/README.md)：当前完成范围、真实板端接收耗时，以及同一27B开启/关闭原生思考的单题测试。

- [保留27B质量的实施进展](27B保留质量_实施进展_20261018.md)：电脑端流式通道与分句流水线第一版；明确实际耗时、未完成播放接入和后续优化顺序。

- [5090移动端亚秒交互研究](5090移动端_亚秒交互研究_20261018.md)：Windows / 24GB，保留27B流式主线、声线与端到端模型对照、动作记忆协议及验收预算；研究完成，候选待目标设备实测。

- [研究来源清单](5090研究来源_20261018.json)：GitHub、官方文档和论文的结论与适用限制。

- [目标设备验证矩阵](5090验证矩阵_20261018.csv)：20项拟议实验；不将外部仓库性能填成本机结果。

- [人设与记忆规划](memory_persona_plan_20261018.md)：规划稿，当前尚未实施。

- [语音输出逻辑与低延迟方案](voice_output_and_latency_plan_20261018.md)：当前逻辑、已测数据和后续候选方案。

- [27B多轮测试](model_27b_candidate_verification.json)：原业务证据的报告副本。

- [27B完整语音HTTP测试](model_27b_verification.json)：历史录音测试报告副本。

- [部署状态归档](model_27b_upgrade_status.json)：整理时的状态快照；后续实时状态以业务目录 `deliverables/2026-10-18_board_dialogue/model_27b_upgrade_status.json` 为准。



原始证据继续保留在业务目录中，本目录归档报告便于统一查看。





- [27B内部短字段优化与复测（2026-10-18）](27B内部短字段优化_20261018.md)：保持27B和原音色，缩短内部JSON字段，75项回归及8次模型对照；正式界面实录与听音以报告最新证据为准。





- [汐蓝称呼误听容错（2026-10-18）](汐蓝称呼误听容错_20261018.md)：明确呼唤玩偶时解释同音称呼，保留原始ASR及其他词；104项回归、4项原27B文字探针和真实录音HTTP验证通过。现场听音以报告最新证据为准。





- [思考误触发修复（2026-10-18）](思考误触发修复_20261018.md)：区分“比较开心”等闲聊与真正比较请求，106项回归及26个语境子用例；复杂数学原27B实际计算保留。现场听音以最新证据为准。



- [多轮历史复用优化（2026-10-18）](多轮历史复用优化_20261018.md)：118项回归、26个子用例及两轮正式录音/播放/听音验收通过，原27B、声线和四轮历史保持；模型小样本台词准备中位数2.186→1.791秒。偶发复述问句仍为开放缺陷，不计作提速成功。[实测摘要](多轮历史复用优化_实测摘要_20261018.json)。



- [防复述保护与延迟核查（2026-10-18）](防复述保护与延迟核查_20261018.md)：138项回归、26子用例及真实27B四轮记忆、主动复述和固定种子错误纠正通过；普通回答维持单次推理。完整语音HTTP已验证，新录音听音以[最新摘要](防复述保护与延迟核查_实测摘要_20261018.json)为准。仅覆盖已知整句复制，完整根因仍开放；错误纠正会额外等待。



- [紧凑JSON与GPU调度对照（2026-10-18）](紧凑JSON与GPU调度_20261018.md)：150项回归、26子用例及新录音听音通过，原27B/声线保持；实际通道4次同台词对照首PCM中位数2.949→2.826秒，小样本不保证固定提速。本次现场软件开口4.095秒；未采用省略动作字段和串行TTS方案。[最终摘要](紧凑JSON与GPU调度_实测摘要_20261018.json)。

<!-- long-term-memory-plan-20261021 -->

[长期记忆存储管理实施与验收规划（2026-10-21）](长期记忆存储管理_实施与验收规划_20261021.md)：依据原人设与记忆方案，分P0合同迁移、P1单常用用户/访客与跨会话事实、P2全链遗忘和备份恢复、P3摘要/临时状态/待办、P4实机验收。保留SQLite、原27B/2048基线及播放ACK，不新增常驻向量模型。仅规划，未迁库、部署或删除数据。



<!-- board-owner-implementation-20261030 -->

最新执行与真实验收状态见[板端业务主控实施记录](../语音共享文件/deliverables/2026-10-30_board_owner/IMPLEMENTATION_STATE.json)。用户已要求开始执行并允许并行；候选已有实板同模型和真实27B摘要验证，生产迁移尚未完成。人物形象替换需另过同条件A/B降低板端开销的门槛，再交用户确认；[跨任务边界](../语音共享文件/deliverables/2026-10-30_board_owner/coordination/character_boundary.json)与运行窗口统一登记。

<!-- /board-owner-implementation-20261030 -->



