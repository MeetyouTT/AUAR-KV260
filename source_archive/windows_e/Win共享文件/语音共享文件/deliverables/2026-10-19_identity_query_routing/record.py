"""Publish loaded intent repair evidence without claiming human ASR/face success."""
import json,re
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
ANALYSIS=ROOT.parent/'语言模型分析'
read=lambda name:json.loads((HERE/name).read_text(encoding='utf-8-sig'))
c,d,v,p=[read(n) for n in ('candidate.json','deployment.json','source_verification.json','preflight.json')]
assert d['status']=='SPOKEN_IDENTITY_QUERY_DEPLOYED_AWAITING_REAL_USER'
assert d['database_hash_unchanged'] and d['camera_pid_preserved']
assert all(p[k] for k in ('real_models_passed','bootstrap_passed','widget_passed'))
assert v['pc_health']['identity_voice_enrollment']['identity_query_intent_revision']==2
pc_log=(HERE/'tests_pc.log').read_text(encoding='utf-8')
board_log=(HERE/'tests_board.log').read_text(encoding='utf-8')
assert '129 passed, 2 deselected' in pc_log and 'Ran 202 tests' in board_log and board_log.rstrip().endswith('OK')
obs=read('live_query_observation.json') if (HERE/'live_query_observation.json').exists() else {}
consistency=read('face_consistency.json') if (HERE/'face_consistency.json').exists() else {}
assert '我是谁呀' in obs.get('question_transcripts',[])
route=obs['route_diagnostics']['4'];turn=obs['turn_routes']['4']
assert route['direct_identity_question'] and route['board_identity_route'] and route['reply_code']=='identity_unknown'
assert turn['backend']=='board_identity_workflow' and turn['identity_reply_code']=='identity_unknown' and turn['audio_complete']
live={'user_confirmed_actual_utterance':'我是谁呀','raw_asr':'我是谁呀','generation':4,
 'user_confirmed_no_character_vocative_in_this_sample':True,'asr_agrees_with_user':True,
 'board_identity_route':True,'reply_code':'identity_unknown','same_generation_audio_complete':True,
 'name_recognized':False,'character_vocative_acoustic_test':False,'human_listening_confirmation':None}
(HERE/'real_microphone_query.json').write_text(json.dumps(live,ensure_ascii=False,indent=2),encoding='utf-8')
summary={'client_date':'2026-10-19','status':'REAL_MICROPHONE_QUERY_ROUTE_PASSED_FACE_MATCH_STILL_UNKNOWN',
 'previous_revision_human_query_passed':False,
 'latest_user_feedback':'语音识别有问题，我说夕蓝，他识别不到',
 'reported_full_question_asr_recovered':False,
 'known_reproduced_missed_intents':['夕蓝我是谁','西兰我叫什么名字啊','汐蓝我是谁呀','你知道我是谁'],
 'repair':'whole direct question grammar with existing known vocatives, optional particles and missing 吗',
 'asr_raw_transcript_rewritten':False,'asr_model_changed':False,'new_unknown_vocatives_added':False,
 'general_spoken_input_interpreter_changed':False,'query_intent_revision':2,
 'actual_user_new_revision_asr_passed':True,'actual_user_new_revision_query_routing_passed':True,
 'actual_user_new_revision_query_passed':False,
 'actual_user_new_revision_character_vocative_asr_passed':None,
 'actual_user_new_revision_listening_passed':None,
 'actual_080_enrollment_still_passed':True,'database':d['database_after'],
 'threshold':.8,'ambiguity_margin':.1,'threshold_changed':False,
 'camera_restarted':False,'camera_pid_preserved':True,'database_hash_unchanged':True,
 'ui_runtime':c['runtime'],'camera_config_preserved':c['old_camera_config'],
 'pc_tests_passed':129,'pc_linux_only_tests_deselected':2,'linux_tests_passed':202,
 'public_models_and_asset_preflight_passed':True,
 'controlled_transcript_http_query_routing_passed':True,
 'acoustic_name_recognition_accuracy_proven_by_tests':False,
 'face_match_accuracy_fixed_by_routing':False,
 'prior_current_face_score_range':[.437618,.624089],
 'prior_current_face_score_samples':12,'prior_current_face_samples_passing_080':0,
 'single_bounded_route_diagnostic_in_ram_only':True,
 'diagnostic_has_raw_speech_names_or_images':False,
 'photos_or_templates_exported':False,'llm_weights_moved':False,
 'same_original_asr_27b_omnivoice16_and_five_latency_flags':True,
 'live_query_observation':obs,'current_face_consistency_read_only':consistency,
 'steady_face_check_status':'WAITING_FOR_USER_READINESS',
 'rollback_backup':d['backup']}
(HERE/'verification_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
(HERE/'listening.json').write_text(json.dumps({'status':'REAL_MIC_ASR_AND_ROUTE_PASSED_FACE_UNKNOWN_LISTENING_UNCONFIRMED',
 'previous_revision_human_query_passed':False,'new_revision_human_query_passed':False,
 'new_revision_human_asr_and_query_route_passed':True,'same_generation_audio_complete':True,
 'actual_human_listening_passed':None,'character_vocative_acoustic_test_passed':None,
 'user_confirmed_actual_utterance':'我是谁呀','new_revision':2},ensure_ascii=False,indent=2),encoding='utf-8')
text=f'''# 称呼和身份问句入口修复

用户反馈上一版仍走普通聊天，随后说明“我说夕蓝，他识别不到”。上一版真人查询已记为失败，登记成功仍保留：1身份/1模板/修订14。未恢复到报告当轮的完整ASR，不能断言实际误听成了哪几个字。

## 已复现的入口漏项

原通用称呼解释器在没有标点或问候时，不把“夕蓝我是谁”里的“夕蓝”按呼唤处理；遇到“我叫什么”又会保守保留姓名语境。原身份查询只匹配固定句子，也会漏掉“我是谁呀”“你知道我是谁”。这些确切文字输入可复现进入普通聊天，但并不证明它们就是本次用户的实际ASR。

新身份查询在整句范围内接受已有“汐蓝/夕蓝/西兰/西蓝/溪蓝/希蓝/汐兰”称呼、无标点连接、自然语气词及省略“吗”的直接问句。未添加未知词为别名，未改原始ASR、通用姓名解释或登记称呼。引用、否定、假设、询问玩偶是谁、复合删除指令等仍不会通过此查询入口。旧客户端、登记动作和普通聊天保持原路由。

板端保留最近一次路由诊断，只有字数、是否识别为身份问句、是否走板端、录音起点人脸数量/状态及回复码；单条RAM数据，无转写正文、称呼、图片或模板。自动续听清掉字幕后仍能查看这轮路由，过期代次不能改写诊断。

## 验证与当前状态

- Windows129项通过；2项依赖Linux fcntl的板端用例在Windows排除，在Linux完整202项中通过。初次Windows错误日志保留在 `tests_pc_linux_only_initial.log`，没有把平台缺依赖写成产品修复证据。
- 受控ASR转写的真实HTTP路由测试覆盖“夕蓝我是谁呀”“西兰我叫什么名字啊”及不应拦截的问句；公开Lena/原真实人脸模型临时库与UI启动预检通过。没有把受控转写或公开单图当作用户语音/人脸精度证明。
- PC8792已重载并报告 `identity_query_intent_revision=2`；UI `{c['runtime']}` 已加载，25份候选源码哈希核对。相机仍用 `{c['old_camera_config']}`，PID保持，DPU/ByteTrack/音频配置不变。
- 用户库部署前后1条/修订14、哈希不变；阈值0.80、间隔0.1保持。原Paraformer/27B IQ4_XS/OmniVoice16及5项延迟开关保持，LLM数据仍在D盘。

正式新录音已取到：generation4原始ASR为“我是谁呀”，用户确认原话就是“我是谁呀”，没有先叫称呼；录音起点为一张人脸、UNKNOWN，实际进入板端身份查询并返回identity_unknown，同代次完整播放。真实麦克风这句转写与用户原话一致，身份问句路由已通过；报出身份仍失败，用户听音未单独确认。本句不含“汐蓝/夕蓝”，所以不能据此声称称呼的声学识别问题已通过。证据 `real_microphone_query.json`、`live_query_observation.json`。

当前人脸准确度也未因此提高：上轮12帧同生产对齐脸匹配0.437618～0.624089，全部低于0.80。人脸未识别时应播“现在还没有认出镜头前的人”或失脸提示，不能从最近登记记录取名字充当实时识别。

最新只读连续8帧：与登记模板0.399185～0.696463，0帧达到0.80；这些当前帧彼此的余弦0.484475～0.937099（中位0.695921）。不能把失败只归结为登记模板：这段实时输入也有较大变化，且未取得静止正脸条件，无法区分真实姿态变化与关键点/对齐波动。`face_consistency.json`仅数值，无图像、向量或姓名。下一步等待用户准备好一小段静止正脸作只读对照，不改库/门槛。

证据：`user_feedback.json`、`tests_pc.log`、`tests_board.log`、`preflight.json`、`voice_host_reload_ready.json`、`deployment.json`、`source_verification.json`、`live_query_observation.json`、`verification_summary.json` 和 `verified_source.zip`。实际听音与真人识别依然以新反馈为准。

回退：结束对话后运行本目录 `rollback.py` 仅恢复上一UI；需要回退PC解析时，恢复本目录before中的common/voice_enrollment.py、tools/board_model_host.py并空闲重载8792。相机及身份库不回滚，备份 `{d['backup']}`。
'''
(HERE/'README.md').write_text(text,encoding='utf-8')
marker='<!-- identity-query-routing-20261019 -->'
block=(marker+'\n- 2026-10-19上一查询版真人反馈失败（仍普通聊天），随后用户说明“夕蓝”称呼识别有问题；实际当轮完整ASR未取回，不能断言具体误听字。'
 f'已复现并修复“夕蓝我是谁/西兰我叫什么名字啊”无标点称呼、语气词与省略吗的直接身份问句入口，PC8792 intent_revision2、UI `{c["runtime"]}` 已加载。'
 '只复用已知别名，不改ASR/通用姓名解释/登记/普通聊天，不宽泛子串路由。板端last_voice_route只保留单条RAM字数/路由/录音起点人脸数量与状态/回复码，不留正文、姓名、图片。'
 'Windows129项（2项Linux依赖用例移板端）、Linux202项及受控转写HTTP/原公开模型和UI预检通过；不能当真人声学称呼或识别验收。'
 '相机仍原8ad候选且PID保持，库1身份/1模板/修订14哈希不变，0.80/0.1和原语音模型/参数保持。'
 '最新真人第4轮ASR“我是谁呀”与用户确认原话一致，已进入board_identity_workflow/identity_unknown，同代次完整播放，真人问句转写/路由已通过；仍未识别人脸，称呼声学与听音未单独验收。上一版真人查询失败保留。12帧当前脸分0.437618～0.624089/0帧达0.80，路由修复未解决人脸准确度，不取最近登记姓名冒充识别。'
 '最新证据 `deliverables/2026-10-19_identity_query_routing/README.md`、verification_summary.json 优先；LLM数据D盘。\n<!-- /identity-query-routing-20261019 -->\n\n')
path=ROOT/'AGENTS.md';raw=path.read_text(encoding='utf-8')
if marker in raw:raw=re.sub(re.escape(marker)+r'.*?<!-- /identity-query-routing-20261019 -->\s*',block,raw,count=1,flags=re.S)
else:raw=block+raw
path.write_text(raw,encoding='utf-8')
note=('> **2026-10-19 称呼/身份问句入口修复已加载：** 上一查询版真人反馈失败；现补齐“夕蓝我是谁”“西兰我叫什么名字啊”及自然语气词，保留原ASR转写。'
 'Windows129/板端202项及隔离预检通过，库1条/修订14和0.80门槛保持；真人“我是谁呀”转写/路由已通过，同轮完整播放但仍未识别人脸，称呼声学尚未实测通过。'
 '[本轮证据与回退](deliverables/2026-10-19_identity_query_routing/README.md)。\n\n')
path=ROOT/'README.md';raw=path.read_text(encoding='utf-8')
if not raw.startswith('> **2026-10-19 称呼/身份问句入口修复已加载：**'):path.write_text(note+raw,encoding='utf-8')
report='称呼与身份问句路由修复_20261019.md'
(ANALYSIS/report).write_text(text,encoding='utf-8')
path=ANALYSIS/'README.md';raw=path.read_text(encoding='utf-8')
if report not in raw:
 entry='\n## 最新：称呼和身份问句分流修复\n\n[本轮证据]('+report+')：真人“我是谁呀”转写/身份查询路由已通过，同轮完整播放但人脸仍UNKNOWN；含称呼的声学识别与真人听音未单独验收。\n'
 raw=raw.replace('# 语言模型分析统一入口','# 语言模型分析统一入口\n'+entry,1)
path.write_text(raw,encoding='utf-8')
print(json.dumps({k:summary[k] for k in ('status','ui_runtime','database','pc_tests_passed','linux_tests_passed')},ensure_ascii=True))
