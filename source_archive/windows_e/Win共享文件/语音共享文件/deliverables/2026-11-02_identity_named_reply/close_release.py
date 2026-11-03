"""Close this coordinator's own completed maintenance and sync local records."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import xml.etree.ElementTree as ET
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


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read(path):
    return json.loads(Path(path).read_bytes())


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')


def counts(path):
    root = ET.parse(path).getroot()
    cases = list(root.iter('testcase'))
    failures = [(case.get('classname'), case.get('name')) for case in cases if case.find('failure') is not None]
    assert not any(case.find('error') is not None for case in cases)
    return len(cases), failures


now = datetime.now(timezone.utc)
stamp = now.isoformat()
local = now.astimezone(ZoneInfo('America/Los_Angeles')).strftime('%Y-%m-%d %H:%M')
before = {path: path.read_bytes() for path in (COORD, PROG, TEXT, PHASE)}
c, p, phase = (json.loads(before[path]) for path in (COORD, PROG, PHASE))
assert phase['permission_active'] and phase['operator_thread_id'] == ROOT
owner = c['board_maintenance_owner']
assert c['global_document_writer_thread_id'] == ROOT
assert owner['thread_id'] == ROOT and owner['permission_active']
assert owner['phase_receipt'] == str(PHASE) and owner['phase_receipt_sha256'] == sha(before[PHASE])
assert p['current_gui_maintenance']['phase_receipt'] == str(PHASE)
final_path = TASK / 'final_read_3_RESULT.json'
final = read(final_path)
state = final['board_result']
assert state['status'] == 'DEPLOYED_READY_EITHER_MODALITY_NAMED_REPLY_VERIFIED'
assert state['ready'] and not state['errors'] and state['all380_actual_bytes_match']
assert state['voice_priority_face_fallback_verified'] and state['missing_name_added_before_tts_verified']
assert state['model_host_ready_idle'] and not state['current_state']['microphone_open']
assert not state['current_state']['listening_enabled'] and state['current_state']['runtime_fault_count'] == 0
assert state['saved_listening_preference'] == dict(version=1, enabled=False)
assert counts(TASK / 'NAMED_REPLY_TEST_RESULT.xml') == (19, [])
assert counts(TASK / 'VOICE_REGRESSION_RESULT.xml') == (21, [])
assert counts(TASK / 'HOST_STARTUP_REGRESSION_RESULT.xml') == (25, [])
context_count, context_failures = counts(TASK / 'CONTEXT_REGRESSION_RESULT.xml')
baseline_count, baseline_failures = counts(BASE / '2026-11-02_multimodal_dialogue_context/CONTEXT_REGRESSION_RESULT.xml')
assert context_count == baseline_count == 46 and context_failures == baseline_failures and len(context_failures) == 3
apply = read(TASK / 'apply_context_1_RESULT.json')['board_result']
assert apply['other379_actual_components_preserved'] and len(apply['changed_files']) == 1
model = read(TASK / 'model_recovery_3_RESULT.json')
assert model['status'] == 'ORIGINAL_MODEL_HOST_RESTORED_AFTER_WINDOWS_REBOOT'
assert model['pending_calls'] == 0 and model['configuration_unchanged']
transactions = read(TASK / 'TRANSACTIONS.json')
transactions['start_after_windows_reboot'] = read(TASK / 'EXPECTED_RECOVERY_START.json')['transaction_path']
release = dict(schema='aura-either-identity-named-reply-release-1',
    status='DEPLOYED_READY_LISTENING_PAUSED', completed_utc=stamp,
    direct_human_request='声纹或者视觉对上了，每次回答带上我的名字', operator_thread_id=ROOT,
    startup_before_sha256=apply['startup_before'], startup_sha256=state['startup_sha256'],
    changed_runtime_files=apply['changed_files'], other379_actual_components_preserved=True,
    request_order=['original_persona', 'current_face_and_voice_results', 'memory_and_recent_dialogue', 'current_user_utterance'],
    addressing_policy=dict(voice_match='current utterance voice name',
        voice_unconfirmed_single_fresh_known_face='current single face name',
        disagreement='voice priority', neither_confirmed='neutral address'),
    selected_name_required_in_each_ordinary_reply=True, missing_name_added_before_TTS_and_persistence=True,
    already_named_reply_not_duplicated=True, overlength_uses_existing_one_corrective_retry=True,
    automatic_profile_or_personal_memory_authority_added=False, face_voice_association_required=False,
    new_recognition_encoders_or_inference_calls_added=False, new_named_reply_checks_passed=19,
    existing_voice_checks_passed=21, host_startup_checks_passed=25, existing_context_checks_passed=43,
    existing_context_baseline_failures=3, new_context_regressions=0,
    baseline_context_failure_reason='Same three older XiLan alias tests fail on the XueFei baseline and candidate.',
    actual_ARM_synthetic_address_and_request_verified=True, actual_private_recognition_values_collected=False,
    real_user_voice_test_performed=False, formal_two_speaker_acceptance_started=False,
    formal_two_speaker_acceptance='DEFERRED_BY_USER', normal_GUI_stops=1, normal_GUI_start_submissions=2,
    first_GUI_start='Confirmed failed after Windows reboot interrupted its model dependency.',
    second_GUI_start='Normal start from reconciled terminal failure after restoring original model host.',
    Windows_reboot_utc='2026-11-03T07:18:48Z', original_model_host_restored=True,
    original_model_parameters_and_endpoint_preserved=True, model_host_start_attempts=3,
    model_host_attempt_outcomes=['exited after metadata timeout', 'exited after startup metadata timeout', 'READY'],
    last_readonly_state_receipt=str(final_path), last_readonly_state_sha256=sha(final_path.read_bytes()),
    last_readonly_state=state, transaction_backups=transactions,
    pending_SSH_HTTP_observers_or_control_transactions=0, unknown_operations_remaining=0,
    maintenance_active=False)
release['host_recovery_evidence'] = [dict(path=str(TASK / name), sha256=sha((TASK / name).read_bytes())) for name in (
    'HOST_METADATA_TIMEOUT_REPAIR.json', 'HOST_STARTUP_GUARD_TIMEOUT_REPAIR.json',
    'original_daemon_handshake_RESULT.json', 'MODEL_COLD_PREFLIGHT_READ_RESULT.json', 'model_recovery_3_RESULT.json')]
release_path = TASK / 'RELEASE_RESULT.json'
release_raw = encode(release)
release_sha = sha(release_raw)
phase.update(status='DEPLOYED_VERIFIED_SCOPE_CLOSED', permission_active=False, closed_utc=stamp,
    release_receipt=str(release_path), release_receipt_sha256=release_sha,
    active_SSH=0, active_HTTP=0, background_observers=0, pending_controls=0,
    unknown_operations_remaining=0, listening_enabled=False, microphone_open=False)
phase_raw = encode(phase)
closed_owner = dict(owner, status='DEPLOYED_VERIFIED_SCOPE_CLOSED_IDLE',
    title='原窗口身份称呼维护已结束', permission_active=False, maintenance_holder_active_work=False,
    phase_receipt_sha256=sha(phase_raw), release_receipt=str(release_path), release_receipt_sha256=release_sha,
    closed_utc=stamp, pending_calls_or_observers=0, unknown_operations_remaining=0)
c['board_maintenance_owner'] = closed_owner
p['current_gui_maintenance'] = dict(closed_owner, global_owner_registry=str(COORD))
work = dict(c['current_named_reply_work'], status='DEPLOYED_VERIFIED_SCOPE_CLOSED',
    phase_receipt_sha256=sha(phase_raw), startup_sha256=state['startup_sha256'],
    release_receipt=str(release_path), release_receipt_sha256=release_sha,
    completed_utc=stamp, listening_enabled=False, microphone_open=False,
    real_human_acceptance='NOT_STARTED_USER_REQUESTED_PAUSED', pending_calls_or_observers=0)
for doc in (c, p):
    doc['updated_utc'] = stamp
    doc['current_named_reply_work'] = work
    voice = doc['current_voice_speaker_recognition']
    voice.update(actual_startup_sha256=state['startup_sha256'], actual_source_map=str(TASK / 'startup.after.json'),
        actual_source_map_sha256=sha((TASK / 'startup.after.json').read_bytes()),
        latest_named_reply_release=str(release_path), latest_named_reply_release_sha256=release_sha,
        current_listening_enabled=False, current_microphone_open=False, saved_listening_enabled=False)
    voice.setdefault('current_component_sha256', {}).update({item['path']: item['after_sha256'] for item in apply['changed_files']})
    assert voice['formal_test_rounds'] == 0 and voice['human_switching_acceptance'] is None
p.update(overall='工程包已封存。当前逐轮声纹和人脸结果已前置给大模型，任一路确认后每轮普通回答带登记名。原模型服务与角色主页面已恢复，聆听暂停，正式两人切换验收待测。',
    latest_named_reply_release=release, latest_saved_board_receipt=str(final_path),
    latest_saved_board_receipt_sha256=sha(final_path.read_bytes()), latest_saved_board_receipt_issued_utc=final['host_utc'],
    live_board_observed_utc=final['host_utc'], live_models_observed_utc=final['host_utc'],
    current_boot_id=state['boot_id'], startup_sha256_at_latest_saved_board_receipt=state['startup_sha256'])
axis = dict(source_receipt=str(final_path), source_receipt_sha256=sha(final_path.read_bytes()),
    observed_utc=final['host_utc'], automatic_following=state['current_state']['follow'],
    readback=state['current_state']['axis_readback'], axis_commands_by_this_context_task=0,
    scope='Named-reply maintenance final public readback only')
p['latest_saved_axis_readback'] = axis
for module in p['modules']:
    name = module['module']
    if name == '本机模型与LAN':
        module.update(status='Windows 重启后原 27B/OmniVoice 服务已恢复，板端健康读取通过。',
            facts='保留原27B IQ4_XS、OmniVoice16和8797端点。只读进程/端口检查的等待上限修复为15秒，原300秒启动总预算及推理时限保持。',
            latest_recovery_receipt=str(TASK / 'model_recovery_3_RESULT.json'))
    elif name == '板端业务/角色UI':
        module.update(status='原角色主页面就绪，故障零，聆听暂停。',
            facts='本次只更新一份板端对话源码与启动绑定，另379项实读匹配。原窗口本笔维护已结束。',
            latest_runtime_startup_sha256=state['startup_sha256'], latest_saved_UI_state=state['current_state'],
            named_reply_release=str(release_path))
    elif name == '身份与语言协同':
        module.update(status='声纹或单人视觉确认后，每轮普通回复带登记名；正式两人切换待测。',
            facts='声纹优先，未确认时回退到当前单人KNOWN视觉结果。模型输入保留两路结果，合成语音前补齐称呼。身份关联取消，个人记忆授权保持原规则。',
            named_reply_release=str(release_path))
    elif name == '转轴跟随':
        module['latest_saved_readback'] = axis
assert p['face_voice_association_required'] is False
assert p['voice_recognition_accuracy_acceptance_complete'] is False
assert p['voice_field_calibration_complete'] is False
prefix = (
    f'声纹或视觉确认后每轮回复带登记名（洛杉矶 {local}）\n'
    '本轮声纹匹配时使用声纹登记名；声纹未确认、当前单人视觉KNOWN时使用视觉登记名；两路冲突优先声纹，两路均未确认用中性称呼。每轮重新判断，模型缺少选定称呼时在合成语音和保存前补齐。两路识别结果继续位于本轮用户话语前。\n'
    '一份板端源码和启动绑定已发布，另379项实读匹配。新增19项、原声纹21项及主机启动25项检查通过。旧上下文43项通过、3项与基线相同旧角色别名失败，无新增回归。ARM合成数据验证通过，未采集真人新轮次。\n'
    '本机23:18重启导致原模型服务退出，首次GUI启动失败。已核对原进程归属、补全中断握手，修复两个只读进程/端口查询的短超时并恢复原27B和OmniVoice16。总启动预算和推理参数未改。主页面已就绪，故障零，聆听和麦克风保持关闭。\n'
    f'发布回执 {release_path}，SHA-256 {release_sha}。最新启动指纹 {state["startup_sha256"]}。正式A-B-A两人切换验收仍待用户明确开始。维护SSH、HTTP、观察和未决控制均为零。\n\n'
)
text_raw = (prefix + before[TEXT].decode('utf-8-sig')).encode('utf-8')
rollback = (
    '继续使用与回退\n\n'
    '当前主页面就绪，聆听暂停。用户可通过原UI启用聆听，或明确说开始后再建立现场观察。视觉需当前单人、清晰且已识别为登记名。声纹用普通连续句子约5至8秒，至少2.5秒有效人声。每轮使用本轮结果，不继承未知轮的上一姓名。\n'
    '正式两人切换未测，现场标定未完成。代码与合成检查不能替代真人准确率验收。\n\n'
    f'板端备份事务 {transactions["stop"]}\n'
    'context-source-0.before.py 对应本次唯一更新的 board/runtime/board_dialogue.py。context-startup.before.json 是本次改前启动配置。\n'
    f'改前启动 {apply["startup_before"]}\n改后启动 {state["startup_sha256"]}\n'
    '未来回退须新鲜核对持有人、启动代次、当前源码、相机归属和GUI空闲状态，经原正常停启和单独CAS执行。不得重放这里已使用的一次性停启脚本或旧事务。\n\n'
    'Windows重启恢复另见三个model_recovery回执和original_daemon_handshake_RESULT.json。两个主机元数据查询等待上限修复分别保存在HOST_METADATA_TIMEOUT_REPAIR.json与HOST_STARTUP_GUARD_TIMEOUT_REPAIR.json，其改前源码保存在本目录。它们只调整只读检查的等待上限，保留同一启动总预算、原模型、GPU/归属检查。\n'
    '原冻结工程交付包未修改。本目录为后续增量。\n'
)
backup = PROGRESS / 'before_named_reply_close'
backup.mkdir(exist_ok=False)
for path, raw in before.items():
    with (backup / path.name).open('xb') as stream:
        stream.write(raw)
with (TASK / 'DEVICE_MAINTENANCE.active.before.json').open('xb') as stream:
    stream.write(before[PHASE])
with release_path.open('xb') as stream:
    stream.write(release_raw)
with (TASK / 'CONTINUE_AND_ROLLBACK.txt').open('xb') as stream:
    stream.write(rollback.encode('utf-8'))
updates = {PHASE: phase_raw, COORD: encode(c), PROG: encode(p), TEXT: text_raw}
staged, applied = {}, []
try:
    for path, raw in updates.items():
        temp = path.with_name(path.name + '.named-reply-close.part')
        with temp.open('xb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        staged[path] = temp
    assert all(path.read_bytes() == raw for path, raw in before.items())
    for path, raw in updates.items():
        assert path.read_bytes() == before[path]
        os.replace(staged[path], path)
        applied.append(path)
except BaseException:
    for path in reversed(applied):
        if path.read_bytes() == updates[path]:
            temp = path.with_name(path.name + '.named-reply-close.rollback.part')
            with temp.open('xb') as stream:
                stream.write(before[path])
            os.replace(temp, path)
    raise
finally:
    for temp in staged.values():
        temp.unlink(missing_ok=True)
assert all(path.read_bytes() == raw for path, raw in updates.items())
print(json.dumps(dict(status=release['status'], release_receipt=str(release_path),
    release_sha256=release_sha, maintenance_permission_active=False,
    pending_calls_or_observers=0, board_ready=True, listening_enabled=False), ensure_ascii=False))
