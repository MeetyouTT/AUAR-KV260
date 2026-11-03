"""Close only this root-owned maintenance phase from immutable recorded checks."""
from datetime import datetime, timezone
import hashlib, json, os
from pathlib import Path
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

TASK=Path(__file__).resolve().parent
DEPLOY=TASK.parent/'2026-11-02_5090_deployment'
COORD=DEPLOY/'CHAT_COORDINATION.json'
PROGRESS=DEPLOY/'project_progress_20261102/PROJECT_PROGRESS.json'
TEXT=PROGRESS.with_suffix('.txt')
PHASE=TASK/'DEVICE_MAINTENANCE.json'
ROOT='01a1994e-f547-74e1-903d-3591021d67c8'
def read(path):return json.loads(Path(path).read_bytes())
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def encode(value):return (json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n').encode()
def create(path,data):
    with Path(path).open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
def evidence(name):return dict(path=str(TASK/name),sha256=sha(TASK/name))

before={path:path.read_bytes() for path in (COORD,PROGRESS,TEXT,PHASE)}
c,p,phase=(json.loads(before[path]) for path in (COORD,PROGRESS,PHASE))
assert c['global_document_writer_thread_id']==ROOT
owner=c['board_maintenance_owner']
assert owner['thread_id']==ROOT and owner['permission_active'] and owner['phase_receipt']==str(PHASE)
assert owner['phase_receipt_sha256']==sha(PHASE) and phase['permission_active']
ready=read(TASK/'ready_read_1_RESULT.json')['board_result']
final=read(TASK/'final_read_1_RESULT.json'); board=final['board_result']; state=board['current_state']
assert ready['ready'] and board['status']=='FIVE_TURN_FINAL_RUNTIME_VERIFIED' and not board['errors']
assert board['all380_actual_bytes_match'] and board['component_sha256']==read(TASK/'startup.after.json')['component_sha256']
assert board['camera_owner']==read(TASK/'fresh_read_1_RESULT.json')['board_result']['camera_owner']
assert not board['thinking_enabled'] and board['model_health']['backend']['context_limit']==4096
assert not any(state[k] for k in ('listening_enabled','microphone_open','playing','pending_job','speaker_busy','follow'))
assert state['pair_ready'] and state['runtime_fault_count']==0 and state['axis_readback']['flags']==0
assert not board['model_health']['active'] and board['model_health']['pending']==0
test=read(TASK/'public_five_round_3_RESULT.json')['board_result']
assert test['status']=='FIVE_ROUND_MODEL_RECALL_AND_TTS_PASSED' and test['first_turn_recalled_on_fifth']
assert test['pet_name_correct'] and test['color_correct'] and len(test['rounds'])==5
assert all(row['ok'] and row['http_status']==200 and row['think'] is False for row in test['trace'])
assert test['model_active_after'] is False and test['model_pending_after']==0
assert test['private_store_reads']==test['microphone_enable_calls']==test['speaker_playback_calls']==0
cases=list(ET.parse(TASK/'CONTEXT_REGRESSION_RESULT.xml').getroot().iter('testcase'))
baseline=list(ET.parse(TASK/'BASELINE_REGRESSION_RESULT.xml').getroot().iter('testcase'))
failed=lambda rows:{row.get('name') for row in rows if row.find('failure') is not None or row.find('error') is not None}
assert len(cases)==80 and len(failed(cases))==3 and failed(cases)==failed(baseline)
names=list(ET.parse(TASK/'FULL_NAME_REGRESSION_RESULT.xml').getroot().iter('testcase'))
assert len(names)==21 and not failed(names)
model=read(TASK/'MODEL_START_RESULT.json'); residency=read(TASK/'MODEL_RESIDENCY_AFTER.json')
assert model['status']=='STARTED' and model['health']['backend']['tts_ready']
assert model['state']['fixed_daemon_pid']==read(TASK/'MODEL_BEFORE.json')['state']['fixed_daemon_pid']
assert residency['models'][0]['context_length']==4096
probe=read(TASK/'public_five_round_2_RESULT.json')['board_result']
assert probe['status']=='PUBLIC_PROBE_PREPARATION_ERROR' and probe['error_type']=='AttributeError'
assert probe['detail']=="'function' object has no attribute 'client'"
now=datetime.now(timezone.utc);stamp=now.isoformat();local=now.astimezone(ZoneInfo('America/Los_Angeles')).strftime('%Y-%m-%d %H:%M')
result=dict(schema='aura-five-turn-context-release-1',status='FIVE_TURN_CONTEXT_DEPLOYED_MODEL_RECALL_VERIFIED',completed_utc=stamp,
    direct_request='拍摄视频，支持五轮连续对话，第五轮清晰回忆第一轮',
    context_limit=4096,prior_user_turn_window=4,recent_completed_raw_turns_preserved=5,
    raw_retention='Latest five played turns per scope and conversation source remain as exact durable bodies beyond the original 300-second compaction window. Older eligible turns retain the existing summary policy.',
    context_priority='Current input and current recognition data, four prior dialogue turns, then optional facts and older continuity summary. If assistant replies are too long, preserve all four user originals first.',
    conversation_boundary='Same conversation and scope only. Explicit clear/forget, conversation changes and profile authorization retain original behavior.',
    model_test=dict(evidence('public_five_round_3_RESULT.json'),rounds=5,fifth_round_reply=test['rounds'][4]['reply'],
        first_turn_pet_name='团团',first_turn_color='蓝色',fifth_question_did_not_reveal_expected_values=True,
        llm_seconds=[row['seconds'] for row in test['trace'] if row['kind']=='llm'],
        fifth_reply_TTS_seconds=test['trace'][-1]['seconds'],valid_24k_audio=True,
        actual_human_voice_test=False,physical_speaker_playback=False,fixture_ACKs_only=True),
    tests=dict(context_and_memory_cases=80,passed=77,baseline_unchanged_old_character_alias_failures=3,
        added_five_turn_cases=9,added_five_turn_cases_passed=9,named_reply_regressions_passed=21,
        regression_receipt=evidence('CONTEXT_REGRESSION_RESULT.xml'),baseline_receipt=evidence('BASELINE_REGRESSION_RESULT.xml'),
        naming_receipt=evidence('FULL_NAME_REGRESSION_RESULT.xml')),
    source_manifest=evidence('SOURCE_MANIFEST.json'),startup_sha256=board['startup_sha256'],source380_actual_bytes_match=True,
    active_runtime_source_directory=str(TASK/'candidate_runtime'),model_host_source=evidence('host_candidate/model_inference_host.py'),
    normal_GUI_stop_submissions=1,normal_GUI_start_submissions=1,normal_owned_model_stop_submissions=1,normal_model_start_submissions=1,
    forced_termination=False,camera_owner_unchanged=True,selected_face_pin_verification_passed=True,
    model_session_id=model['session_id'],model_owner=model['owner'],model_worker_pid=model['state']['pid'],
    tts_pid=model['state']['same_unique_tts_pid'],fixed_daemon_preserved=True,model_weights_changed=False,
    model_context_length_actual=4096,model_residency=evidence('MODEL_RESIDENCY_AFTER.json'),
    GPU_guard_preserved=True,startup_observed_free_mib=model['state']['startup']['steady_admission']['llm']['observed_free_mib'],
    gpu_calibration_scope='Original adaptive guard values preserved; actual 4096 context residency and five-turn ordinary requests verified. No new worst-case GPU calibration is claimed.',
    current_state=state,thinking_enabled=False,latest_board_receipt=evidence('final_read_1_RESULT.json'),
    listening_enabled=False,microphone_open=False,private_memory_exported=False,existing_user_data_replaced=False,
    frozen_engineering_delivery_modified=False,face_voice_association_added=False,
    probe_reconciliation=dict(original_probe=evidence('public_five_round_1_RESULT.json'),
        explicit_failure=evidence('public_five_round_2_RESULT.json'),
        cause='Diagnostic helper named http shadowed the imported http module; failed before constructing its initial health connection. No inference request was reached. Fixed the diagnostic alias only before the successful check.',
        unknown_operations_remaining=0),
    active_SSH=0,active_HTTP=0,background_observers=0,pending_controls=0,unknown_operations_remaining=0,
    maintenance_active=False,video_human_acceptance_pending=True)
result_path=TASK/'RELEASE_RESULT.json';raw_result=encode(result);result_sha=hashlib.sha256(raw_result).hexdigest()
phase.update(status='FIVE_TURN_CONTEXT_VERIFIED_SCOPE_CLOSED',permission_active=False,closed_utc=stamp,
    result_receipt=str(result_path),result_receipt_sha256=result_sha,active_SSH=0,active_HTTP=0,background_observers=0,
    pending_controls=0,unknown_operations_remaining=0,startup_sha256=board['startup_sha256'])
phase_raw=encode(phase);phase_sha=hashlib.sha256(phase_raw).hexdigest()
closed=dict(owner,status='FIVE_TURN_CONTEXT_VERIFIED_SCOPE_CLOSED_IDLE',permission_active=False,maintenance_holder_active_work=False,
    phase_receipt_sha256=phase_sha,result_receipt=str(result_path),result_receipt_sha256=result_sha,
    startup_sha256=board['startup_sha256'],gui_owner=board['gui_owner'],gtk_owner=board['gtk_owner'],camera_owner=board['camera_owner'],
    closed_utc=stamp,pending_calls_or_observers=0,unknown_operations_remaining=0)
c['board_maintenance_owner']=closed;p['current_gui_maintenance']=dict(closed,global_owner_registry=str(COORD))
work=dict(c['current_five_turn_context_work'],status=result['status'],completed_utc=stamp,result_receipt=str(result_path),
    result_receipt_sha256=result_sha,production_context_limit=4096,model_five_round_recall_passed=True,
    recent_raw_turns_preserved=5,video_human_acceptance_pending=True,maintenance_active=False,pending_calls_or_observers=0)
for doc in (c,p):
    doc['updated_utc']=stamp;doc['current_five_turn_context_work']=work
    voice=doc['current_voice_speaker_recognition'];voice.update(current_listening_enabled=False,current_microphone_open=False,saved_listening_enabled=False)
    assert voice['formal_test_rounds']==0 and voice['ordinary_short_voice_human_acceptance'] is False
    assert doc['temporary_model_thinking_test']['enabled'] is False
p.update(overall='视频五轮上下文已部署，真实模型第五轮正确回忆首轮两项信息，语音合成通过。角色主页面就绪、故障零、聆听暂停。最近五轮原文持久保留，真人视频待拍；正式两人声纹验收仍待测。工程封存包未改。',
    latest_five_turn_context_release=result,latest_saved_board_receipt=str(TASK/'final_read_1_RESULT.json'),
    latest_saved_board_receipt_sha256=sha(TASK/'final_read_1_RESULT.json'),latest_saved_board_receipt_issued_utc=final['host_utc'],
    live_board_observed_utc=final['host_utc'],live_models_observed_utc=final['host_utc'],
    startup_sha256_at_latest_saved_board_receipt=board['startup_sha256'],current_boot_id=board['boot_id'])
for module in p['modules']:
    if module['module']=='板端业务/角色UI':
        module.update(status='五轮上下文已加载，主页面就绪，故障零，聆听暂停。',latest_saved_UI_state=state,latest_runtime_startup_sha256=board['startup_sha256'])
    elif module['module']=='基础语音对话':
        module.update(status='普通模式五轮模型对话通过，第五轮回忆首轮，语音合成通过；真人录制待开始。',five_turn_context_release=str(result_path),five_turn_context_release_sha256=result_sha)
    elif module['module']=='记忆':
        module.update(status='最近五轮原文持久保留，第五轮上下文包含首轮；老数据和显式记忆操作保留。',recent_raw_turns_preserved=5,context_limit=4096,five_turn_model_recall_verified=True)
    elif module['module']=='本机模型与LAN':
        module.update(status='原27B与OmniVoice16正常，模型上下文4096已实读，五轮公开请求全部成功。',context_limit=4096,model_session_id=model['session_id'])
assert p['face_voice_association_required'] is False
prefix=(f'视频五轮上下文已部署（洛杉矶 {local}）\n'
    '原2048上下文中角色提示及本轮识别信息占用较多，历史容易被挤出；已同步扩大板端与原27B上下文为4096，优先携带四轮历史和当前问题。长回答优先让出空间给用户原话。最近五轮已播放原文不再因原五分钟压缩窗口被删去，重开库仍可读取；显式清空、忘记及切换对话仍按原规则。\n'
    '真实生产模型用公开合成内容连续五轮，第五轮正确答出第一轮小猫“团团”、颜色“蓝色”，五次模型请求均成功、约1.8至2.3秒，第五轮语音合成0.83秒并生成有效24k音频。该检查使用临时数据库和合成ACK，没有真人录音或实物扬声器播放，不冒作真人视频验收。\n'
    '新增9项五轮用例通过；80项上下文/记忆检查77通过，3项旧角色别名失败与原基线相同；21项带名回复检查通过。三个板端文件及对应启动绑定已发布，其余377项与原来源一致，全380项实际字节校验通过，原27项视觉绑定校验通过。\n'
    '原GUI和模型服务均正常停启一次，固定模型守护进程保持，权重未变。模型实读context_length=4096，启动余量5473MiB，原GPU准入守卫保留。最终角色主页READY、故障零、聆听暂停、麦克风关闭；无SSH、HTTP、观察或控制在途。真人录制可从原面板开启聆听。封存工程包未改，真人短句声纹及正式两人切换仍待测。\n'
    f'发布回执 {result_path}，SHA-256 {result_sha}；startup {board["startup_sha256"]}。\n\n')
notes=('拍摄与接续\n\n同一段对话连续五轮，等每次回答结束再说下一句。拍摄时在原面板开启聆听；五轮中不要清空、切换对话或更换个人记忆范围。\n'
    '第一轮可说宠物名字与喜欢的颜色，第二至四轮自然换话题，第五轮追问第一轮内容；本次公开实测未在第五轮问题中透露答案。已有私人库、登记和音频未导出或替换。\n'
    '实际部署源保存在本目录candidate_runtime及host_candidate，源码清单和启动前后绑定均在本目录。E:/AUAR_工程交付_20261102未修改。\n\n'
    '回退只在新的明确维护阶段内执行：先确认暂停、无在途对话，正常停止原GUI和拥有模型的原服务；按SOURCE_MANIFEST中的after哈希核对现役三个文件后，逐一恢复baseline对应原字节及startup.before.json。'
    '主机tools/model_inference_host.py按MODEL_APPLY_RESULT.json核对后恢复host_baseline原字节。保持原固定守护进程，按原管理器正常启动模型，再按原启动路径启动GUI并重新验证380项、视觉绑定和就绪状态。不要单独只回退上下文的一端；不删除私人数据库，不开启思考实验，不重试结果不明的停启。\n')
create(result_path,raw_result);create(TASK/'CONTINUE_AND_ROLLBACK.txt',notes.encode())
backup=TASK/'close_before_records';backup.mkdir()
for path,data in before.items():create(backup/path.name,data)
updates={PHASE:phase_raw,PROGRESS:encode(p),TEXT:(prefix+before[TEXT].decode('utf-8-sig')).encode(),COORD:encode(c)}
staged={};applied=[]
try:
    for path,data in updates.items():
        temp=path.with_name(path.name+'.five-turn-close.part');create(temp,data);staged[path]=temp
    assert all(path.read_bytes()==raw for path,raw in before.items())
    for path,data in updates.items():
        assert path.read_bytes()==before[path];os.replace(staged[path],path);applied.append(path)
except BaseException:
    for path in reversed(applied):
        if path.read_bytes()==updates[path]:
            temp=path.with_name(path.name+'.five-turn-rollback.part');create(temp,before[path]);os.replace(temp,path)
    raise
finally:
    for temp in staged.values():temp.unlink(missing_ok=True)
assert all(path.read_bytes()==data for path,data in updates.items())
print(json.dumps(dict(status=result['status'],result_receipt=str(result_path),result_sha256=result_sha,
    maintenance_active=False,pending_calls_or_observers=0),ensure_ascii=False))
