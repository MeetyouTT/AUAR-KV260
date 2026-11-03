"""Record completed short-voice fix and release this task's serial maintenance."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo

TASK = Path(__file__).resolve().parent
BASE = TASK.parent
DEPLOY = BASE / '2026-11-02_5090_deployment'
PROGRESS = DEPLOY / 'project_progress_20261102'
COORD = DEPLOY / 'CHAT_COORDINATION.json'
PROG = PROGRESS / 'PROJECT_PROGRESS.json'
TEXT = PROGRESS / 'PROJECT_PROGRESS.txt'
PHASE = TASK / 'DEVICE_MAINTENANCE.json'
ROOT = '01a1994e-f547-74e1-903d-3591021d67c8'
RECEIVER = '01a1a069-bf82-70c0-bd91-dcc31ea1e7a6'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')


def read(path):
    return json.loads(Path(path).read_bytes())


def create(path, raw):
    with Path(path).open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


now = datetime.now(timezone.utc)
stamp = now.isoformat()
local = now.astimezone(ZoneInfo('America/Los_Angeles')).strftime('%Y-%m-%d %H:%M')
before = {path: path.read_bytes() for path in (COORD, PROG, TEXT, PHASE)}
c, p, phase = (json.loads(before[path]) for path in (COORD, PROG, PHASE))
owner = c['board_maintenance_owner']
assert c['global_document_writer_thread_id'] == ROOT
assert owner['thread_id'] == ROOT and owner['permission_active']
assert owner['phase_receipt'] == str(PHASE) and owner['phase_receipt_sha256'] == sha(PHASE)
assert phase['permission_active'] and phase['operator_thread_id'] == ROOT
final_path = TASK / 'final_read_2_RESULT.json'
final = read(final_path)
state = final['board_result']
assert state['status'] == 'DEPLOYED_READY_SHORT_ORDINARY_VOICE_SYNTHETIC_VERIFIED'
assert state['ready'] and state['all380_actual_bytes_match'] and not state['errors']
assert state['installed_ARM_short_voice_checks']['cases_passed'] == 5
assert state['installed_ARM_short_voice_checks']['original_worker_closed']
assert state['installed_ARM_short_voice_checks']['temporary_synthetic_files_removed']
ui = state['current_state']
assert ui['handsfree_state'] == 'PAUSED' and not ui['listening_enabled'] and not ui['microphone_open']
assert not ui['playing'] and not ui['pending_job'] and ui['runtime_fault_count'] == 0
manifest = read(TASK / 'SOURCE_MANIFEST.json')
assert len(manifest['changed_files']) == 1
assert manifest['startup_after_sha256'] == state['startup_sha256']
feedback_path = TASK / 'USER_FEEDBACK.json'
feedback = read(feedback_path)
assert feedback['off_camera_long_sentence_naming_human_confirmed']
e = read(TASK / 'EXPECTED_AFTER.json')
release_path = TASK / 'RELEASE_RESULT.json'
return_path = TASK / 'DEVICE_RETURN_TO_THINKING.json'
release = dict(schema='aura-short-ordinary-voice-release-1', status='DEPLOYED_READY_LISTENING_PAUSED',
    completed_utc=stamp, direct_human_request='离开摄像头，用声音识别他不通过', operator_thread_id=ROOT,
    cause='The observed 2.52-second recording was rejected by the original 3-second total-audio gate before VAD or ECAPA.',
    original_voice_entry_did_not_require_a_face=True,
    off_camera_long_sentence_naming_human_confirmed=True,
    human_feedback_receipt=str(feedback_path), human_feedback_sha256=sha(feedback_path),
    ordinary_short_voice_fix_human_acceptance=False,
    ordinary_short_voice_minimum_effective_ms=1500, original_enrollment_quality_preserved=True,
    original_similarity_threshold=.35, original_ambiguity_margin=.1, match_thresholds_changed=False,
    fallback_runs_only_after_original_quality_rejection=True, fallback_uses_original_single_CPU_worker=True,
    encoders_per_eligible_capture=1, cross_turn_audio_combining=False,
    short_candidates_not_used_as_enrollment_or_formal_identity_proofs=True,
    personal_memory_authority_added=False, face_voice_association_required=False,
    new_short_worker_checks_passed=17, new_short_LLM_and_TTS_integration_checks_passed=2,
    original_voice_checks_passed=21, original_named_reply_checks_passed=19,
    actual_ARM_synthetic_cases_passed=5, real_user_short_voice_accuracy_test_performed=False,
    formal_two_speaker_switching_rounds_added=0, field_calibrated=False,
    startup_before_sha256=manifest['startup_before_sha256'], startup_sha256=state['startup_sha256'],
    changed_runtime_files=manifest['changed_files'], other_components_preserved=379,
    normal_GUI_stops=1, normal_GUI_starts=1,
    last_readonly_state_receipt=str(final_path), last_readonly_state_sha256=sha(final_path),
    last_readonly_state=state, transaction_backups=read(TASK / 'TRANSACTIONS.json'),
    pending_SSH_HTTP_observers_or_control_transactions=0, unknown_operations_remaining=0,
    maintenance_active=False, next_requested_maintenance_return=str(return_path))
release_raw = encode(release)
release_sha = hashlib.sha256(release_raw).hexdigest()
phase.update(status='DEPLOYED_VERIFIED_SCOPE_CLOSED', permission_active=False, closed_utc=stamp,
    release_receipt=str(release_path), release_receipt_sha256=release_sha,
    active_SSH=0, active_HTTP=0, background_observers=0, pending_controls=0,
    unknown_operations_remaining=0, listening_enabled=False, microphone_open=False)
phase_raw = encode(phase)
phase_sha = hashlib.sha256(phase_raw).hexdigest()
request = dict(schema='aura-inbound-maintenance-request-source-1', received_during='voice-only diagnosis',
    recorded_utc=stamp, source_kind='inbound codex_delegation message', source_thread_id=RECEIVER,
    request='Finish or safely close current diagnosis and publish explicit device return for a subsequent thinking-mode test.',
    source_reports_explicit_human_approval=True, source_reports_no_GUI_deployment_or_reload_yet=True,
    source_reports_waiting_for_handoff=True, outbound_cross_chat_message_sent_by_this_task=False)
request_path = TASK / 'THINKING_TEST_HANDOFF_REQUEST.json'
request_raw = encode(request)
return_record = dict(schema='aura-short-voice-maintenance-return-for-thinking-1',
    status='CLOSED_READY_FOR_RECEIVER_FRESH_CLAIM', issued_utc=stamp,
    relinquishing_thread_id=ROOT, requested_receiver_thread_id=RECEIVER,
    returned_objects=['KV260 original GUI serial maintenance', 'public runtime source and startup pins'],
    actual_loaded_mode='short ordinary voice naming fix loaded in original GUI; live listening paused',
    publication_result='APPLIED_AND_READY', rollback_needed=False,
    startup_sha256=state['startup_sha256'], source_map=str(TASK / 'startup.after.json'),
    source_map_sha256=sha(TASK / 'startup.after.json'), identity_four_core=e['identity_four_core'],
    board_dialogue_sha256=e['component_sha256']['board/runtime/board_dialogue.py'],
    gui_owner=state['gui_owner'], gtk_owner=state['gtk_owner'], camera_owner=state['camera_owner'],
    boot_id=state['boot_id'], selected_face_binding=e['selected_face_binding'],
    original_GUI_properties=e['original_GUI_properties'], camera_config=e['camera_config'],
    last_saved_state=ui, observed_utc=final['host_utc'],
    original_27B_IQ4_XS_and_OmniVoice16_preserved=True, thinking_switch_changed_by_this_task=False,
    listening_enabled=False, microphone_open=False,
    SSH_in_flight=0, HTTP_in_flight=0, background_observers=0, pending_control_transactions=0,
    unknown_operations_remaining=0, permission_active=False,
    closed_phase=str(PHASE), closed_phase_sha256=phase_sha,
    release_receipt=str(release_path), release_receipt_sha256=release_sha,
    request_source=str(request_path), request_source_sha256=hashlib.sha256(request_raw).hexdigest(),
    receiver_acknowledgement_recorded=False,
    next_step='Receiver must verify CHAT_COORDINATION no longer grants active maintenance here, then establish its own human-authorized phase and freshly reconcile sources, ownership, configuration and paused state. Rebase startup pins onto this actual 380-component source map. Do not replay this task scripts.')
return_raw = encode(return_record)
return_sha = hashlib.sha256(return_raw).hexdigest()
closed_owner = dict(owner, title='纯声纹短句修复已部署，维护已归还', status='DEPLOYED_VERIFIED_SCOPE_CLOSED_IDLE',
    permission_active=False, maintenance_holder_active_work=False, phase_receipt_sha256=phase_sha,
    release_receipt=str(release_path), release_receipt_sha256=release_sha, startup_sha256=state['startup_sha256'],
    closed_utc=stamp, pending_calls_or_observers=0, unknown_operations_remaining=0,
    device_return_receipt=str(return_path), device_return_receipt_sha256=return_sha)
c['board_maintenance_owner'] = closed_owner
p['current_gui_maintenance'] = dict(closed_owner, global_owner_registry=str(COORD))
work = dict(c['current_voice_only_diagnosis'], status='DEPLOYED_VERIFIED_SCOPE_CLOSED',
    completed_utc=stamp, phase_receipt=str(PHASE), phase_receipt_sha256=phase_sha,
    release_receipt=str(release_path), release_receipt_sha256=release_sha,
    startup_sha256=state['startup_sha256'], ordinary_voiced_minimum_ms=1500,
    short_sentence_human_acceptance_pending=True, listening_enabled=False, microphone_open=False,
    pending_calls_or_observers=0)
pending = dict(thread_id=RECEIVER, status='RETURN_AVAILABLE_AWAITING_RECEIVER_FRESH_PHASE',
    source='inbound codex_delegation', return_receipt=str(return_path), return_receipt_sha256=return_sha,
    requires_fresh_reconciliation=True, receiver_acknowledged=False, microphone_enable_authorized=False)
for doc in (c, p):
    doc['updated_utc'] = stamp
    doc['current_voice_only_diagnosis'] = work
    doc['pending_gui_maintenance_request'] = pending
    voice = doc['current_voice_speaker_recognition']
    voice.update(actual_startup_sha256=state['startup_sha256'], actual_source_map=str(TASK / 'startup.after.json'),
        actual_source_map_sha256=sha(TASK / 'startup.after.json'),
        latest_voice_only_fix_release=str(release_path), latest_voice_only_fix_release_sha256=release_sha,
        ordinary_short_voice_minimum_effective_ms=1500, ordinary_short_voice_human_acceptance=False,
        off_camera_long_sentence_human_confirmed=True, current_listening_enabled=False,
        current_microphone_open=False, saved_listening_enabled=False)
    voice.setdefault('current_component_sha256', {})['board/runtime/board_speaker_business.py'] = manifest['changed_files'][0]['after_sha256']
    assert voice['formal_test_rounds'] == 0 and voice['human_switching_acceptance'] is None
p.update(overall='工程包已封存。画外长句声纹称呼经用户确认可用，短句识别限制已修复并部署，真人短句效果待复测。原角色主页面就绪，聆听暂停；正式两人切换验收仍待测。',
    latest_voice_only_fix_release=release, latest_saved_board_receipt=str(final_path),
    latest_saved_board_receipt_sha256=sha(final_path), latest_saved_board_receipt_issued_utc=final['host_utc'],
    live_board_observed_utc=final['host_utc'], current_boot_id=state['boot_id'],
    startup_sha256_at_latest_saved_board_receipt=state['startup_sha256'])
axis = dict(source_receipt=str(final_path), source_receipt_sha256=sha(final_path),
    observed_utc=final['host_utc'], automatic_following=ui['follow'], readback=ui['axis_readback'],
    axis_commands_by_this_context_task=0, scope='Short voice fix final public readback only')
p['latest_saved_axis_readback'] = axis
for module in p['modules']:
    if module['module'] == '板端业务/角色UI':
        module.update(status='原角色主页面就绪，故障零，聆听暂停。',
            latest_runtime_startup_sha256=state['startup_sha256'], latest_saved_UI_state=ui,
            latest_voice_only_fix_release=str(release_path))
    elif module['module'] == '身份与语言协同':
        module.update(status='画外长句称呼已获用户确认，短句修复已部署，真人短句及两人切换待测。',
            facts='普通称呼新增至少1.5秒有效人声的单轮短句匹配。原声纹录入门槛、相似度阈值、CPU模型与个人记忆授权保持。任一路确认后每轮回答带登记名。',
            latest_voice_only_fix_release=str(release_path))
    elif module['module'] == '转轴跟随':
        module['latest_saved_readback'] = axis
assert p['face_voice_association_required'] is False
assert p['voice_recognition_accuracy_acceptance_complete'] is False
prefix = (f'画外声纹短句修复已部署（洛杉矶 {local}）\n'
    '用户反馈画外仍能回答但没有名字。本轮公开状态显示2.52秒录音、INSUFFICIENT_SPEECH，代码复现确认原3秒整段录音门槛会在声纹提取前拒绝该录音。用户随后确认镜头外5至8秒长句能叫出正确名字。\n'
    '已仅更新board_speaker_business.py和启动绑定，另379项实读匹配。普通称呼新增至少1.5秒有效人声的独立短句匹配，仍用现有单CPU工作线程及原匹配阈值，不拼接不同轮录音，不把短句结果作为录入或正式身份凭据。录入门槛保持原样。\n'
    '17项短句工作线程检查、2项短句到模型/TTS全链路检查、原21项声纹和19项称呼检查通过。板端5项合成用例通过，原主页面正常、故障零、聆听和麦克风关闭。修复后的真人短句效果尚未复测，正式两人切换仍为零轮。\n'
    f'发布 {release_path}，SHA-256 {release_sha}。现役startup {state["startup_sha256"]}。\n'
    f'本笔维护SSH、HTTP、观察和控制在途均为零，已结束。思考模式测试窗口可读取 {return_path}，SHA-256 {return_sha}，建立自己的新鲜维护阶段后串行接续。尚未登记接收签收或开启思考开关。\n\n')
rollback = ('继续与回退\n\n'
    '当前聆听暂停。用户确认旧版本镜头外长句已能叫对名字；本次新增短句规则仍需真人复测。下一次测试请明确开始，再核对当前维护持有人和运行版本后通过原UI开麦。建议先使用2至3秒完整短句，至少1.5秒须为有效人声；极短句或匹配失败仍用中性称呼。\n\n'
    f'本次唯一改动 board/runtime/board_speaker_business.py。事务备份 {release["transaction_backups"]["stop"]}\n'
    'context-source-0.before.py为该文件的改前字节，context-startup.before.json为本次改前启动配置。\n'
    f'改前startup {release["startup_before_sha256"]}\n改后startup {state["startup_sha256"]}\n'
    '未来回退先新鲜核对来源、归属、运行状态及之后新增改动，再正常停GUI并反向CAS本文件及其启动pin。如果后续窗口已有新发布，须保留其其他源码与pin，不能直接覆盖整份旧启动配置。不得重放本目录已执行的一次性脚本。\n\n'
    f'思考测试维护返还 {return_path}。本笔对board_dialogue.py无改动，其SHA保持 {e["component_sha256"]["board/runtime/board_dialogue.py"]}，后续窗口必须基于新的380项实际map重建startup。\n'
    '未改摄像头、转轴、DPU、模型权重、录入模板及冻结工程交付包。\n')
backup = PROGRESS / ('before_voice_only_fix_close_' + now.strftime('%Y%m%dT%H%M%SZ'))
backup.mkdir(exist_ok=False)
for path, raw in before.items():
    create(backup / path.name, raw)
create(TASK / 'DEVICE_MAINTENANCE.active.before.json', before[PHASE])
create(release_path, release_raw)
create(request_path, request_raw)
create(return_path, return_raw)
create(TASK / 'CONTINUE_AND_ROLLBACK.txt', rollback.encode('utf-8'))
updates = {PHASE: phase_raw, PROG: encode(p), TEXT: (prefix + before[TEXT].decode('utf-8-sig')).encode('utf-8'), COORD: encode(c)}
staged, applied = {}, []
try:
    for path, raw in updates.items():
        temp = path.with_name(path.name + '.voice-only-close.part')
        create(temp, raw)
        staged[path] = temp
    assert all(path.read_bytes() == raw for path, raw in before.items())
    for path, raw in updates.items():
        assert path.read_bytes() == before[path]
        os.replace(staged[path], path)
        applied.append(path)
except BaseException:
    for path in reversed(applied):
        if path.read_bytes() == updates[path]:
            temp = path.with_name(path.name + '.voice-only-close.rollback.part')
            create(temp, before[path])
            os.replace(temp, path)
    raise
finally:
    for temp in staged.values():
        temp.unlink(missing_ok=True)
assert all(path.read_bytes() == raw for path, raw in updates.items())
print(json.dumps(dict(status=release['status'], startup_sha256=state['startup_sha256'],
    release_receipt=str(release_path), release_sha256=release_sha, maintenance_closed=True,
    pending_calls_or_observers=0, return_receipt=str(return_path), return_sha256=return_sha), ensure_ascii=False))
