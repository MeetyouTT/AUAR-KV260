"""Build a readable ownership catalogue from the saved runtime inventory."""
import json
from pathlib import Path
H=Path(__file__).resolve().parent
v=json.loads((H/'runtime_inventory.json').read_text(encoding='utf-8'))
assert not v['board']['component_hash_mismatches']
assert v['board']['camera_health']['identity']['backend']=='DPU_SFACE_INT8'
assert v['windows_health']['8792']['identity_features']['processed']==0
def feature(name,windows,board,status,source):
    return {'功能':name,'Windows负责':windows,'板卡负责':board,'状态':status,'源码或证据':source}
rows=[
feature('人声活动检测','8795：GTCRN降噪后交给Silero v5判断是否有人声；返回判定，不用处理后的PCM替换现有识别输入',
        'MCP01采集、端点起止和静音门槛、请求时序','已部署；当前监听关闭',
        ['deliverables/2026-10-21_environment_frontend/pc_service/aura/tools/audio_frontend_host.py','board/runtime/audio/remote_frontend.py']),
feature('语音识别ASR','CPU Paraformer：8791独立识别；8792内部也加载同一识别模型','发送本轮PCM、显示识别结果','已部署',
        ['tools/asr_server.py','tools/board_model_host.py']),
feature('唤醒及文字意图','语音转文字、称呼修正、汐蓝/哎/欸文字规则、身份/视觉/声纹/记忆命令路由',
        '监听开关、初始唤醒/连续接话状态、采集和打断执行；语音不以人脸为前提','汐蓝通过既有合成实测；哎/欸及即时唤醒仍待验',
        ['common/voice_wake.py','tools/board_model_host.py','tools/device_client.py','board deployed tools/voice_first_recording.py']),
feature('对话模型推理','11435：项目Ollama的Qwen 27B，回答和情绪/动作文本输出；按需加载',
        '提交请求、消费流式回答、展示交互状态','服务就绪；快照时该27B未驻留，核查未触发加载',
        ['config/board_dialogue_model.json','tools/dialogue_stream.py','configured_llm_residency']),
feature('语音合成TTS与短反馈','OmniVoice CUDA工作进程：分句合成、音色、思考/入镜招呼短音频预生成及缓存',
        '扬声器播放、PCM时钟、暂停/取消、回声与打断、完整播放确认','已部署；本次无声音播放',
        ['board/runtime/audio/omnivoice_voice.py','tools/voice_channel_source.py','tools/social_feedback.py']),
feature('对话编排与上下文','问题准备、聊天/思考路由、上下文预算、历史选择、首句策略、LLM/TTS调度和服务端取消/结果版本校验',
        '现场会话状态机、采集/播放与客户端取消、请求代次和播放确认','两端共同完成；知识检索和模型编排仍在Windows',
        ['tools/voice_channel_source.py','common/conversation_context.py','tools/board_model_host.py']),
feature('会话与个人事实','权威SQLite会话档案、输入登记、完整播放后提交回复、明确记住/更正/遗忘和跨会话个人事实',
        '会话标识、个人记忆选择入口和用户交互','已部署；权威写入者未移交PS',
        ['common/conversation_store.py','common/profile_memory.py','tools/board_model_host.py']),
feature('个人档案授权','访问授权、短期能力令牌、权限检查、撤销和旧请求拒绝',
        '提供显式选档入口和携带授权；不因看到人脸或未标定声纹自动解锁','已部署；授权服务仍在Windows',
        ['common/profile_access.py','tools/profile_control.py']),
feature('时间轴与后台摘要','对话/视觉日期主题检索、情节/日摘录摘要、容量/保留期、删除失效、来源版本及上下文注入；摘要不调用LLM',
        '提供boot、相机epoch、帧与请求来源','r2 / device-timeline-v2已部署；记忆权威仍Windows',
        ['common/timeline_conversations.py','common/timeline_observations.py','common/timeline_summaries.py','tools/memory_timeline_host.py']),
feature('视觉语义问答','8810：Qwen3-VL-2B CPU，理解单张图片并回答；8792适配和语音回复',
        '现有相机拥有者、帧新鲜度和来源绑定、取图及回传；原图不落盘','已部署；语义推理仍在Windows',
        ['tools/visual_question_host.py','tools/visual_voice_host.py','board/runtime/visual_capture.py']),
feature('定时视觉观察','8812接收图像，调用8810生成文字描述；保存短期观察和跨boot视觉事件',
        '监听开启时每15秒调度一次、取现有画面；关闭监听时停止调度','已部署；当前监听关闭，无持续观察',
        ['tools/device_hub.py','board deployed board/runtime/device_observer.py']),
feature('声纹全流程','8812：ECAPA CPU特征提取、质量/三样本一致性、确认/取消/删除流程、模板SQLite和相似度匹配',
        '采集实际语音并绑定同一请求和PCM摘要，播放引导','已部署；现场未标定，不自动解锁个人记忆',
        ['common/speaker_identity.py','tools/speaker_device.py','tools/device_hub.py']),
feature('动画画面合成','8796 CPU：动作素材解码/缓存、表情眼嘴叠加、缩放，合成423×438 RGB画面',
        '交互状态、音频播放时钟和口型参数、帧过期/代次检查、唯一显示出口；断线本地8fps回退','当前实际选择Windows合成，目标16fps',
        ['tools/portrait_renderer.py','tools/portrait_host.py','board/runtime/portrait_offload.py']),
feature('人脸识别主链','8792中仍有SFace CPU服务就绪，但本次服务进程启动以来调用0次；不能当作当前主链',
        '实际相机服务DPU_SFACE_INT8已ready并持续处理；人脸检测/特征、身份登记与库/匹配管理在板端','主链已在板卡；Windows服务为保留能力，非自动回退承诺',
        ['windows_health.8792.identity_features','board.camera_health.identity','board.camera_service']),
feature('入镜社交','预生成指定音色的嗯和邀请短音频，提供缓存音频',
        '稳定入镜、无发言等待、冷却与忙碌让路策略，播放/打断','流程已接通；现场社交体验待验',
        ['tools/social_feedback.py','board deployed tools/voice_first_recording.py','common/visual_social.py']),
feature('开发和运维辅助','项目启动器、WMI后台进程、模型路径/指纹校验、Windows测试、迁移探针和脱敏报告',
        'systemd实际入口、运行版本校验与现有设备控制边界','属于辅助工具；不代表所有源码已在Windows执行业务',
        ['start_voice.ps1','start_portrait.ps1','deliverables/2026-10-29_runtime_ownership/runtime_inventory.json'])
]
catalog={'核对时间UTC':v['checked_utc'],'范围':'整个玩偶项目的实际执行、数据存储和两端协作；源码所在目录不作为归属判断依据',
         '功能归属':rows,
         'Windows监听服务':{'8791':'独立ASR','8792':'整合语音/记忆/授权/保留SFace特征','8795':'GTCRN+Silero人声判定',
                             '8796':'CPU动画合成','8810':'视觉语言模型','8812':'声纹+视觉观察+时间轴','11435':'项目对话模型Ollama'},
         '板卡已有功能':['摄像头采集与预览','板端视觉检测/跟踪，DPU用于检测和人脸特征','人脸登记、匹配与身份库','麦克风采集与录音起止',
                         '现场监听/交互/入镜社交状态机','音频播放、PCM时钟和客户端打断','触摸界面与显示提交','机械精确绑定与转轴控制'],
         '数据位置':{'会话及个人事实':'Windows项目model_host/conversations.sqlite3',
                     '视觉短期观察和时间轴':'Windows实际服务用户AppData/Local/Aura/device-memory/observations.sqlite3',
                     '声纹模板':'Windows实际服务用户AppData/Local/Aura/device-memory/speakers.sqlite3',
                     '人脸身份库':'板端；不复制模板或照片进行本次核对',
                     'LLM和Ollama':'D:/AIModels，保持既有存储约束',
                     'ASR及OmniVoice资源':'现有明确授权的Windows项目资源目录',
                     '注意':'AppData实际文件视图以独立WMI服务为准；本次只核对进程/健康/源码，不读取库内容'},
         '核对发现':['8791和8792各自构造Paraformer；现有独立识别与整合通话加载重复，后续按调用者分析再精简',
                     '当前人脸主链是板卡DPU_SFACE_INT8；Windows SFace服务ready但processed=0；两者model_id不同，不能直接互换模板',
                     '当前27B未驻留；服务就绪与模型一直驻留不同，本次没有加载或卸载模型'],
         '待验或未接入':['哎/欸短词及专用流式KWS','TalkNet等声画归属整合','声纹现场标定与自动身份关联',
                        '板端ASR/声纹特征/轻量TTS迁移候选','PS权威记忆服务接管','事实有效期/更正历史及对话按日期主题删除'],
         '优先迁移建议':['权威记忆、权限和上下文构建','声纹模板库及登记状态管理；特征计算可暂留Windows','本地VAD','板端ASR及声纹特征实测'],
         '检查改动':{'应用源码或配置':False,'服务重启或终止':False,'模型加载或卸载':False,'开麦播放或运动':False,'读取身份模板或图像':False},
         '证据文件':'runtime_inventory.json'}
(H/'ownership_catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
assert len(rows)==16
print(json.dumps({'status':'COMPLETE','feature_rows':len(rows),'windows_endpoints':7,'face_primary':'BOARD_DPU_SFACE_INT8','no_runtime_changes':True}))
