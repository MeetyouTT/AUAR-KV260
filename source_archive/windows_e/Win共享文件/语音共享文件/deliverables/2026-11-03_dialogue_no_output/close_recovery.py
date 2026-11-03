"""Close no-output recovery from saved diagnostics and a completed real UI playback."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo

TASK = Path(__file__).resolve().parent
DEPLOY = TASK.parent / '2026-11-02_5090_deployment'
PROGRESS = DEPLOY / 'project_progress_20261102'
COORD, PROG, TEXT = DEPLOY / 'CHAT_COORDINATION.json', PROGRESS / 'PROJECT_PROGRESS.json', PROGRESS / 'PROJECT_PROGRESS.txt'
PHASE = TASK / 'DEVICE_MAINTENANCE.json'
ROOT = '01a1994e-f547-74e1-903d-3591021d67c8'


def read(path):
    return json.loads(Path(path).read_bytes())


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')


def create(path, raw):
    with Path(path).open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


before = {path: path.read_bytes() for path in (COORD, PROG, TEXT, PHASE)}
c, p, phase = (json.loads(before[path]) for path in (COORD, PROG, PHASE))
assert c['global_document_writer_thread_id'] == ROOT
owner = c['board_maintenance_owner']
assert owner['thread_id'] == ROOT and owner['permission_active']
assert owner['phase_receipt'] == str(PHASE) and owner['phase_receipt_sha256'] == sha(PHASE)
initial = read(TASK / 'diagnosis_read_1_RESULT.json')['board_result']
recovery_path = TASK / 'disable_thinking_once_RESULT.json'
recovery = read(recovery_path)
off = recovery['board_result']
assert off['status'] == 'TEMPORARY_THINKING_DISABLED_ORDINARY_MODE_RESTORED'
assert off['flag_absent'] and off['next_turn_thinking_options'] == {}
assert off['listening_controls'] == off['microphone_enable_calls'] == off['GUI_restarts'] == 0
matrix_path = TASK / 'public_thinking_diagnostics_3_RESULT.json'
matrix = read(matrix_path)['board_result']['checks']
assert matrix[0]['case'] == 'THINK_192' and matrix[0]['valid_final_reply']
assert matrix[1]['case'] == 'THINK_120' and matrix[1]['http_status'] == 502
assert matrix[1]['error']['code'] == 'backend_invalid_result'
assert matrix[2]['case'] == 'NORMAL_120' and matrix[2]['valid_final_reply']
final_path = TASK / 'final_read_1_RESULT.json'
final = read(final_path)
board = final['board_result']
current = board['current_state']
dialogue = current['dialogue']
latency = dialogue['latency']
assert latency['complete'] and latency['error_class'] == 'none'
assert latency['prepare']['complete'] and latency['prepare']['tts_calls'] == 2
assert dialogue['last_playback_ack']['committed'] is True
assert initial['current_state']['dialogue']['last_playback_ack'] in (None, {})
assert initial['current_state']['dialogue']['latency']['prepare']['tts_calls'] == 0
assert not board['actual_component_mismatches'] and board['component_count'] == 380
assert board['thinking_flag'] is None and board['startup_sha256'] == off['startup_sha256']
assert board['model_health']['ok'] and not board['model_health']['active'] and board['model_health']['pending'] == 0
assert current['fault_count'] == 0 and current['pair_state'] == 'READY'
assert not current['playing'] and not current['pending_job']
assert not current['handsfree']['enabled'] and not current['handsfree']['microphone_open']
assert current['handsfree']['state'] == 'PAUSED'
assert all(board[key] == initial[key] for key in ('gui_owner', 'gtk_owner', 'camera_owner'))
now = datetime.now(timezone.utc)
stamp = now.isoformat()
local = now.astimezone(ZoneInfo('America/Los_Angeles')).strftime('%Y-%m-%d %H:%M')
ui = dict(ui_page=current['ui_page'], phase=current['phase'], pair_ready=True,
    runtime_fault_count=0, listening_enabled=False, microphone_open=False, handsfree_state='PAUSED',
    playing=False, pending_job=False, follow=current['following'])
result = dict(schema='aura-dialogue-no-output-recovery-1', status='ORDINARY_DIALOGUE_RESTORED_PLAYBACK_ACK_OBSERVED',
    completed_utc=stamp, user_report='刚刚测试了对话，没有返回输出',
    initial_stage=dict(asr_completed=True, llm_rpc_ms=initial['current_state']['dialogue']['latency']['prepare']['llm_rpc_ms'],
        error_class='RuntimeError', tts_calls=0, complete=False),
    exact_original_model_error_code='Not exposed by public UI; no private context replay performed.',
    public_reproduction=dict(receipt=str(matrix_path), sha256=sha(matrix_path),
        think_192_valid=True, think_120_error='backend_invalid_result', normal_120_valid=True,
        normal_120_elapsed_seconds=matrix[2]['elapsed_seconds']),
    conclusion='Temporary thinking selection has a reproducible final-output failure under its fallback budget. Disabling the volatile selection restored ordinary UI replies and complete playback.',
    recovery_action='Disabled /run/aura-dialogue-thinking-test.json only',
    recovery_receipt=str(recovery_path), recovery_receipt_sha256=sha(recovery_path),
    flag_backup=off['flag_backup'], thinking_enabled=False, source_changes=0, GUI_restarts=0,
    model_configuration_changes=0, microphone_enable_calls=0, listening_controls=0,
    voice_short_fix_and_named_replies_preserved=True,
    startup_sha256=board['startup_sha256'], source380_actual_bytes_match=True,
    GUI_and_camera_owners_unchanged=True, current_state=ui,
    recovery_playback=dict(real_UI_turn_completed=True, generation=current['last_voice_route']['generation'],
        llm_calls=latency['prepare']['llm_calls'], llm_rpc_ms=latency['prepare']['llm_rpc_ms'],
        tts_calls=latency['prepare']['tts_calls'], tts_rpc_ms=latency['prepare']['tts_rpc_ms'],
        streamed_chunks=latency['prepare']['streamed_chunks'], complete_playback_ack=True,
        physical_first_audio_measured=False, human_hearing_confirmation_received=False),
    last_readonly_state_receipt=str(final_path), last_readonly_state_sha256=sha(final_path),
    last_readonly_observed_utc=final['host_utc'],
    diagnostic_limitations=[
        'An earlier public diagnostic included an incompatible explicit format option while thinking; its two invalid_options responses were request-construction errors and are not production-failure evidence.',
        'The extra stand-alone LLM/TTS probe exited without a captured detail and is not counted as passing. Subsequent readback confirmed model idle, zero pending, and a completed real GUI dialogue with playback ACK.',
        'No private utterance/context was exported or replayed. No formal two-speaker acceptance or new short-voice acceptance was performed.'
    ],
    pending_SSH_HTTP_observers_or_control_transactions=0, unknown_control_operations_remaining=0,
    maintenance_active=False)
result_path = TASK / 'RECOVERY_RESULT.json'
raw_result = encode(result)
result_sha = hashlib.sha256(raw_result).hexdigest()
phase.update(status='RECOVERED_ORDINARY_MODE_SCOPE_CLOSED', permission_active=False, closed_utc=stamp,
    result_receipt=str(result_path), result_receipt_sha256=result_sha,
    active_SSH=0, active_HTTP=0, background_observers=0, pending_controls=0, unknown_operations_remaining=0,
    thinking_enabled=False, listening_enabled=False, microphone_open=False)
phase_raw = encode(phase)
phase_sha = hashlib.sha256(phase_raw).hexdigest()
closed = dict(owner, status='RECOVERED_ORDINARY_MODE_SCOPE_CLOSED_IDLE', permission_active=False,
    maintenance_holder_active_work=False, phase_receipt_sha256=phase_sha,
    result_receipt=str(result_path), result_receipt_sha256=result_sha,
    startup_sha256=board['startup_sha256'], gui_owner=board['gui_owner'], gtk_owner=board['gtk_owner'],
    camera_owner=board['camera_owner'], closed_utc=stamp,
    pending_calls_or_observers=0, unknown_operations_remaining=0)
c['board_maintenance_owner'] = closed
p['current_gui_maintenance'] = dict(closed, global_owner_registry=str(COORD))
work = dict(c['current_dialogue_no_output_work'], status='RECOVERED_ORDINARY_MODE_SCOPE_CLOSED',
    completed_utc=stamp, result_receipt=str(result_path), result_receipt_sha256=result_sha,
    thinking_enabled=False, completed_playback_ack_observed=True, pending_calls_or_observers=0)
for doc in (c, p):
    doc['updated_utc'] = stamp
    doc['current_dialogue_no_output_work'] = work
    thinking = doc['temporary_model_thinking_test']
    thinking.update(enabled=False, status='DISABLED_AFTER_REAL_DIALOGUE_OUTPUT_FAILURE',
        disabled_utc=recovery['host_utc'], latest_runtime_recovery_receipt=str(result_path),
        latest_runtime_recovery_sha256=result_sha, live_user_acceptance=False,
        failure_reproduced_with_public_input=True, ordinary_UI_playback_restored=True)
    voice = doc['current_voice_speaker_recognition']
    voice.update(current_listening_enabled=False, current_microphone_open=False, saved_listening_enabled=False)
    assert voice['formal_test_rounds'] == 0 and voice['ordinary_short_voice_human_acceptance'] is False
p.update(overall='工程包已封存。画外长句称呼可用，短句修复保留且真人短句待测。临时思考测试出现输出失败，已关闭临时开关恢复普通对话，并观测到完整播放确认。主页面正常，聆听暂停，正式两人切换待测。',
    latest_dialogue_no_output_recovery=result, latest_saved_board_receipt=str(final_path),
    latest_saved_board_receipt_sha256=sha(final_path), latest_saved_board_receipt_issued_utc=final['host_utc'],
    live_board_observed_utc=final['host_utc'], startup_sha256_at_latest_saved_board_receipt=board['startup_sha256'],
    current_boot_id=board['boot_id'])
for module in p['modules']:
    if module['module'] == '板端业务/角色UI':
        module.update(status='主页面正常，普通对话恢复，故障零，聆听暂停。',
            latest_saved_UI_state=ui, latest_runtime_startup_sha256=board['startup_sha256'])
    elif module['module'] == '基础语音对话':
        module.update(status='关闭临时思考测试后普通对话恢复，已有完整播放确认。',
            latest_recovery_receipt=str(result_path), latest_recovery_sha256=result_sha,
            temporary_thinking_test=p['temporary_model_thinking_test'])
assert p['face_voice_association_required'] is False
prefix = (f'对话无输出已恢复普通模式（洛杉矶 {local}）\n'
    '用户报告对话无输出。初始回读确认ASR已完成，模型调用约9.2秒后RuntimeError，TTS为零。公开输入对照复现思考120生成预算返回502/backend_invalid_result，思考192本次通过，普通120正常返回。未取得该原始私有轮次的具体服务错误码。\n'
    '本次只关闭当前开机的临时思考开关，未更换源码、模型或GUI进程，声纹短句与带名回复保留。随后实机轮次已完整完成一次LLM、两次TTS、两段流式音频，并收到完整播放ACK。该记录证明软件播放链恢复，不替代物理首声或听感验收。\n'
    '最终回读主页面READY、故障零、模型空闲无待处理、聆听暂停、麦克风关闭。未开麦、未发起新的用户录音，未增加正式身份验收轮次。诊断中构造错误的公开请求和未记录详情的额外探针均保留并排除通过计数。\n'
    f'恢复回执 {result_path}，SHA-256 {result_sha}。startup保持 {board["startup_sha256"]}。本笔维护已结束，SSH、HTTP、观察和控制均无在途。\n\n')
notes = ('恢复结果与接续\n\n'
    '临时思考开关已关闭，普通模式恢复。原模型、源文件、声纹短句和带名规则保留。最终聆听暂停，后续测试通过原UI开启。\n'
    '本次仅删除/run/aura-dialogue-thinking-test.json，原开关备份见恢复回执flag_backup。重新开启会回到尚有已复现输出失败的实验模式，应先解决思考预算回退和失败处理后再单独验证。禁止把本次公开对照误当作修复思考模式本身。\n'
    '下一次维护先核对最新CHAT_COORDINATION、startup、GUI/相机归属及当前聆听状态，不重放本目录一次性关闭脚本。\n')
backup = PROGRESS / ('before_no_output_recovery_close_' + now.strftime('%Y%m%dT%H%M%SZ'))
backup.mkdir(exist_ok=False)
for path, raw in before.items():
    create(backup / path.name, raw)
create(TASK / 'DEVICE_MAINTENANCE.active.before.json', before[PHASE])
create(result_path, raw_result)
create(TASK / 'CONTINUE.txt', notes.encode('utf-8'))
updates = {PHASE: phase_raw, PROG: encode(p), TEXT: (prefix + before[TEXT].decode('utf-8-sig')).encode('utf-8'), COORD: encode(c)}
staged, applied = {}, []
try:
    for path, raw in updates.items():
        temp = path.with_name(path.name + '.no-output-close.part')
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
            temp = path.with_name(path.name + '.no-output-close.rollback.part')
            create(temp, before[path])
            os.replace(temp, path)
    raise
finally:
    for temp in staged.values():
        temp.unlink(missing_ok=True)
assert all(path.read_bytes() == raw for path, raw in updates.items())
print(json.dumps(dict(status=result['status'], result_receipt=str(result_path), result_sha256=result_sha,
    thinking_enabled=False, complete_playback_ack=True, maintenance_active=False,
    pending_task_calls_or_observers=0), ensure_ascii=False))
