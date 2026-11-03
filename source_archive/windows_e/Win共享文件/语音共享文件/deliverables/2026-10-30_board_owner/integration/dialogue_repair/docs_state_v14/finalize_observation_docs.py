"""One-shot final documentation delta; only existing public metadata is read."""
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
REPAIR = HERE.parent
OWNER = REPAIR.parents[1]
PROJECT = OWNER.parents[1]
SHARED = PROJECT.parent


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')


def rel(path):
    return path.relative_to(SHARED).as_posix()


def main():
    assert not (HERE / 'journal_final.json').exists(), 'Final delta is single-use.'
    initial_plan = json.loads((HERE / 'plan.json').read_text(encoding='utf-8'))
    paths = {k: SHARED / v['target'] for k, v in initial_plan['after'].items()}
    paths['observation/current_observation_v14.json'] = REPAIR / 'current_observation_v14.json'
    paths['metadata/HANDOFF.json'] = HERE / 'HANDOFF.json'
    before = {k: p.read_bytes() for k, p in paths.items()}
    observation = json.loads(before['observation/current_observation_v14.json'].decode('utf-8-sig'))
    startup, boot = observation['startup_sha256'], observation['board_boot_id']
    assert startup == '39b102a4a505db491cf06b90e3a5232bfb656c79cb0a3c221551d76d414a9a0a'
    updated = datetime.now(timezone.utc).isoformat()
    frozen, source_raw = {}, {}

    def freeze(key, path):
        raw = path.read_bytes()
        value = json.loads(raw.decode('utf-8-sig'))
        assert len(raw) <= 100000, 'Only small public metadata receipts are frozen.'
        destination = HERE / 'evidence_final' / (key + '.json')
        assert not destination.exists()
        frozen[key] = {'path': rel(destination), 'sha256': sha(raw), 'bytes': len(raw),
                       'source_path': rel(path), 'copy_mode': 'byte_exact_public_metadata'}
        source_raw[path] = raw
        return value

    control = freeze('control', OWNER / 'integration/listening_entry_fix/actual_control_semantics.json')
    live = freeze('live', OWNER / 'integration/listening_entry_fix/actual_live_listening.json')
    resume = freeze('resume', REPAIR / 'frontend_balance_candidate/maintenance_resume.json')
    post = freeze('post_streaming_trial', REPAIR / 'post_streaming_trial.json')
    abba = freeze('asr_abba', REPAIR / 'first_wait_asr_candidate/actual_abba_210925ca35fb_1793445203606433200.json')
    streaming = freeze('streaming_asr', REPAIR / 'first_wait_streaming_candidate/actual_streaming_1793445680498242800.json')
    root_result = freeze('streaming_root_result', REPAIR / 'first_wait_streaming_candidate/ROOT_RESULT.json')
    assert control['startup_sha256'] == live['startup_sha256'] == post['startup_sha256'] == startup
    assert post['board_boot_id'] == live['board_boot_id'] == boot
    assert live['source_manifest_sha256'] == observation['source_manifest_sha256'] and live['component_pins'] == 378
    assert control['main_pid'] == int(live['unit']['MainPID']) == observation['supervisor_pid']
    assert control['gtk_pid'] == live['gtk_pid'] == observation['gtk_pid']
    assert all(control[k] is True for k in ('pause_preference_false_observed', 'resume_preference_true_observed',
        'cancel_rearm_passed', 'pause_closed_microphone', 'pause_released_owned_arecord', 'model_worker_reused_on_rearm'))
    assert control['actual_restart_pause_verified'] is False
    assert live['continuous_capture_passed'] is False and live['priority_scope_passed'] is True
    assert resume['enabled'] is True and resume['microphone_open'] is True and resume['state'] == 'WAITING_SPEECH'
    assert post['listening']['enabled'] is True and post['listening']['microphone_open'] is True
    assert post['listening']['state'] == 'WAITING_SPEECH' and post['phase'] == 'IDLE' and post['playing'] is False
    assert post['dialogue']['pending'] is False and post['runtime_faults']['count'] == 0
    assert abba['before']['startup_sha256'] == abba['after']['startup_sha256'] == startup
    assert abba['before']['boot_id'] == abba['after']['boot_id'] == boot
    assert abba['before']['camera']['pid'] == abba['after']['camera']['pid'] == live['camera_pid'] == 260102
    assert abba['before']['camera']['birth'] == abba['after']['camera']['birth'] == 784437
    assert abba['comparison']['gain_claim_allowed'] is False and abba['production_changed'] is False
    assert all(r['background_changed'] is True and r['audio_seconds'] == 5.614625 for r in abba['results'])
    assert streaming['asr_threads'] == 1 and len(streaming['rounds']) == 4
    assert streaming['baseline_is_gold'] is False and streaming['reference_sha256'] is None
    assert streaming['formal_pipeline_integrated'] is False and streaming['production_configuration_changed'] is False
    assert root_result['production_startup_sha256'] == startup and root_result['production_asr_threads'] == 3
    assert root_result['executed_probe_sha256'] == streaming['probe_sha256'] == '941bad1dfeb3c72f1704b9d1a4ddf84c15b92e6153fc55eb99774714a8fa43e2'
    assert all(r['public_result_chars'] == 27 and r['gold_reference_supplied'] is False and r['accuracy'] is None
               and r['baseline_exact_text_sha256_match'] is False for r in streaming['rounds'])
    assert all(r['characters'] == 29 for r in abba['results'])

    # Retain all immutable prior evidence; replace mutable live/control references.
    evidence = copy.deepcopy(observation['evidence'])
    evidence.pop('listening_live_not_v14', None)
    evidence.pop('listening_controls_not_v14', None)
    for key in ('ready', 'spec', 'windows_host_latest', 'windows_host_status'):
        old = evidence[key]
        source = SHARED / old['path']
        assert sha(source.read_bytes()) == old['sha256']
        freeze('prior_' + key, source)
        evidence[key] = frozen['prior_' + key]
    for key in ('control', 'live', 'resume', 'post_streaming_trial', 'asr_abba', 'streaming_asr', 'streaming_root_result'):
        evidence[key + '_final'] = frozen[key]
    observation['evidence'] = evidence
    observation['updated_utc'] = updated
    observation['status'] = 'V14_RESTORED_CONTROL_PRIORITY_VERIFIED_CONTINUOUS_CAPTURE_PENDING'
    observation['observation_revision_history'] = [{
        'path': rel(HERE / 'before_final/observation/current_observation_v14.json'),
        'sha256': sha(before['observation/current_observation_v14.json']),
        'scope': 'Earlier observation during the public ASR maintenance pause; preserved byte-for-byte.'}]
    observation['camera_pid'] = 260102
    observation['camera_birth_ticks'] = 784437
    observation['camera_pid_caveat'] = 'Fresh public ASR ABBA health metadata confirms same PID/birth before and after, on this recorded boot.'
    gates = observation['current_revision_acceptance']
    gates['controls_verified'] = True
    gates['priority_scope_passed'] = True
    assert sum(v is True for v in gates.values()) == 2
    observation['control_observation'] = {k: control[k] for k in (
        'pause_preference_false_observed', 'resume_preference_true_observed', 'cancel_rearm_passed',
        'pause_closed_microphone', 'pause_released_owned_arecord', 'model_worker_reused_on_rearm',
        'capture_priority_restored_on_pause', 'actual_restart_pause_verified', 'operator_dialogue_acceptance')}
    observation['missing_or_incomplete'] = [
        'Continuous quiet capture did not pass: the three actual samples include real speech/turn transitions.',
        'Audible speaker first sound and acceptable human response wait remain unverified.',
        'Cold boot, paused restart and multi-hour stability remain unverified.']
    observation['strict_listening_updater'].update({
        'reason': 'Current controls and priority scope passed, but continuous_capture_passed is false; strict verified-listening updater remains unexecuted.',
        'saved_live_startup_sha256': startup, 'saved_live_continuous_capture_passed': False,
        'saved_control_startup_sha256': startup})
    observation['latest_runtime_observation'] = {
        'observed_mono': post['observed_mono'], 'phase': post['phase'], 'playing': post['playing'],
        'listening': post['listening'], 'pending': post['dialogue']['pending'],
        'runtime_fault_count': post['runtime_faults']['count'],
        'capture_failures': post['capture_performance']['capture_failures'],
        'memory': {k: post['memory'][k] for k in ('running', 'completed', 'discarded')},
        'memory_failure_streak': post['memory_retry']['failure_streak'],
        'maintenance_pause': False, 'resume_verified': True, 'current_live_state_claimed': False,
        'reason': 'Final saved post-trial receipt: restored WAITING_SPEECH/microphone open; this is a point-in-time observation.'}
    observation['memory_observations']['latest_runtime_counters'] = {
        'observed_mono': post['observed_mono'], 'completed': post['memory']['completed'],
        'discarded': post['memory']['discarded'], 'failure_streak': post['memory_retry']['failure_streak'],
        'backlog_recounted': False,
        'caveat': '361 summaries / 927 backlog remains the earlier detailed store snapshot, not a fresh post-trial total.'}
    observation['asr_public_abba'] = {
        'status': abba['status'], 'audio_seconds': 5.614625, 'sequence': abba['sequence'],
        'asr_ms': [r['asr_ms'] for r in abba['results']],
        'background_changed_every_round': True, 'gain_claim_allowed': False,
        'production_asr_threads': 3, 'production_changed': False}
    observation['asr_candidate_note'] = {'path': rel(HERE / 'current_note.txt'),
        'state': 'PUBLIC_ISOLATED_CANDIDATE_NOT_DEPLOYED',
        'executed_probe_sha256': root_result['executed_probe_sha256'],
        'final_after_scheduled_input_end_ms': [r['final_after_scheduled_input_end_ms'] for r in streaming['rounds']],
        'formal_pipeline_integrated': False, 'accuracy_accepted': False, 'end_to_end_gain_claimed': False}

    observation_raw = encoded(observation)
    pointer = {'path': rel(paths['observation/current_observation_v14.json']), 'path_base': str(SHARED),
        'sha256': sha(observation_raw), 'status': observation['status'], 'revision': 'v14',
        'startup_sha256': startup, 'source_manifest_sha256': observation['source_manifest_sha256'],
        'configuration_sha256': observation['configuration_sha256'], 'component_pins': 378,
        'observations_are_not_full_acceptance': True}
    policy = {'automatic_on_ready': True, 'no_start_button_required': True, 'wake_word_required': False,
        'entry_mode': 'direct_speech', 'conversation_mode': 'half_duplex',
        'explicit_pause_persistence': 'v14_actual_disk_false_true_roundtrip_verified',
        'cancel_current_turn_rearm': 'v14_actual_cancel_rearm_verified',
        'actual_restart_pause_verified': False, 'cold_boot_listening_verified': False}

    def current(value):
        value['updated_utc'] = updated
        value['status'] = observation['status']
        value['current_observation'] = pointer
        value['verification_scope_notice'] = 'v14 controls and priority scope passed; continuous quiet capture did not. Full audio/latency/long-run acceptance remains incomplete.'
        if 'controls_verified' in value:
            value['controls_verified'] = True
        if 'priority_scope_passed' in value:
            value['priority_scope_passed'] = True
        if 'camera_pid' in value:
            value['camera_pid'] = 260102
            value['camera_birth_ticks'] = 784437
        if 'current_revision_acceptance' in value:
            value['current_revision_acceptance'] = copy.deepcopy(gates)
        if 'microphone_open' in value:
            value['microphone_open'] = True
        if 'listening' in value and isinstance(value['listening'], bool):
            value['listening'] = True
        if 'last_observed_listening_enabled' in value:
            value['last_observed_listening_enabled'] = True
            value['last_observed_listening_state'] = 'WAITING_SPEECH'
        if 'maintenance_pause_for_public_asr_test' in value:
            value['maintenance_pause_for_public_asr_test'] = False
        if 'playing' in value:
            value['playing'] = False
        if 'listening_policy' in value:
            value['listening_policy'] = copy.deepcopy(policy)
        if 'evidence' in value:
            value['evidence'] = copy.deepcopy(evidence)
        if 'evidence_digest' in value:
            value['evidence_digest'] = sha(encoded(evidence))
        assert value.get('continuous_capture_passed', False) is False
        if 'verified_listening' in value:
            assert value['verified_listening'] is None

    outputs = {'observation/current_observation_v14.json': observation_raw}
    json_names = [k for k in paths if k.startswith('owner/') and k.endswith('.json')]
    for name in json_names:
        value = json.loads(before[name].decode('utf-8-sig'))
        current(value)
        if 'production_business_live' in value:
            current(value['production_business_live'])
        if 'production' in value:
            value['production']['current_observation'] = pointer
            value['production']['last_observed_camera_pid'] = 260102
            value['production']['last_observed_camera_birth_ticks'] = 784437
        if name.endswith('runtime_windows.json'):
            value['updated_at'] = updated
            value['production_UI_switch']['current_observation'] = pointer
            value['production_business_cutover']['current_observation'] = pointer
        if name.endswith('CHARACTER_SWITCH.json'):
            value['display'].update({'frames': post['native']['frames'], 'visible': post['native']['visible'],
                'target_fps': post['native']['target_fps'], 'observed_mono': post['observed_mono']})
        if name.endswith('dialogue_repair/STATUS.json'):
            value['last_detailed_memory_observation'] = value.pop('latest_memory_observation')
            value['latest_memory_runtime_counters'] = copy.deepcopy(observation['memory_observations']['latest_runtime_counters'])
        outputs[name] = encoded(value)

    prose = (
        '- 现役v14：/home/root/aura-board-business-20261030/production-5259eab11e42af13；startup SHA %s，378份组件；manifest SHA %s；config SHA %s。\n'
        '- 最终恢复回执mono47956.819：自动聆听enabled=true、WAITING_SPEECH、mic=true，IDLE、无播放、GUI故障0；supervisor887170/GTK887178，同boot8100a7fd-0c6a-46c4-82b8-f874988a1521。相机health metadata核对PID260102/birth784437。以上均为保存时点，不代替下次现读。\n'
        '- v14实际暂停磁盘false→true、取消本轮rearm、麦克风/arecord释放及worker复用已通过；优先级作用域通过。continuous_capture_passed=false：采样期间有实际语音/轮次，不能冒填全quiet通过。冷启动/暂停重启、扬声器首声、真人等待满意度和多小时长稳仍未验收。\n'
        '- 正式仍板端业务/存储/雪妃显示，Windows仅27B/2048/120与OmniVoice16推理；权重在D:/AIModels。无唤醒词、半双工；combined前端1线程/capture nice-10、原ASR3线程保持，未上线新ASR。跟随false、机械FAULT/null安全边界保留。\n'
        '- 真人仍反馈等待太久，短回合首音频入队8.4–9.4秒不等于扬声器首声；小样本名字ABBA约19%%仅模型调用局部结果。最终runtime累计采集失败1、memory完成252/丢弃23/streak0；361摘要/927积压是较早详细库快照，不能当最终全库计数或健康通过。\n'
        '- root已完成本轮公开实机ASR对照与隔离流式候选测试；候选未上线，简记见docs_state_v14/current_note.txt。本次接续文档修订仅处理已保存metadata，未再操作设备/模型/私库或改生产/候选代码。当前证据固化于docs_state_v14/evidence_final，完整关联见current_observation_v14.json，旧文档原字节归档保留。\n'
    ) % (startup, observation['source_manifest_sha256'], observation['configuration_sha256'])

    def block(raw, tag, body):
        opening, closing = ('<!-- ' + tag + ' -->').encode(), ('<!-- /' + tag + ' -->').encode()
        pattern = re.compile(re.escape(opening) + b'(.*?)' + re.escape(closing), re.S)
        assert len(list(pattern.finditer(raw))) == 1
        return pattern.sub(lambda _: opening + b'\n' + body.encode('utf-8') + closing, raw, count=1)

    for name in ('project/AGENTS.md', 'analysis/README.md'):
        outputs[name] = block(before[name], 'board-business-live-20261030', prose)
    outputs['project/README.md'] = block(before['project/README.md'], 'dialogue-current-20261031',
        '现役v14（378组件）已在本轮公开试验后恢复自动聆听：保存回执为WAITING_SPEECH/mic=true、IDLE/no playing、GUI故障0；启动指纹未变。暂停/恢复/取消控制及优先级作用域通过，连续全quiet采集未通过，完整听音/首声及长稳仍未验收。正式ASR保持原3线程，新流式ASR仅为未上线候选；27B/OmniVoice16与板端业务存储归属不变。\n\n'
        '真人仍反馈等待太久，首音频入队不等于扬声器首声。以[当前观测](deliverables/2026-10-30_board_owner/integration/dialogue_repair/current_observation_v14.json)、'
        '[状态](deliverables/2026-10-30_board_owner/integration/dialogue_repair/STATUS.json)和[候选简记](deliverables/2026-10-30_board_owner/integration/dialogue_repair/docs_state_v14/current_note.txt)为准；此前版本及维护暂停记录保留为历史。权重仍在D盘。\n')
    name = 'owner/板端业务正式接管与实测接续_20261030.txt'
    boundary = '以下完整保留更新前记录，旧版本通过项不适用于v14：'.encode('utf-8')
    assert before[name].count(boundary) == 1
    suffix = before[name][before[name].index(boundary):]
    outputs[name] = ('v14接续：本轮试验后已恢复；控制/优先级通过，连续quiet与长稳未通过。\n\n' + prose + '\n').encode('utf-8') + suffix
    note = ('公开ASR试验简记（候选未上线）\n\n'
        '原3/4线程ABBA：同一5.614625秒公开WAV，3线程11.126/9.902秒、4线程12.238/12.138秒；四轮后台memory均变化，回执明确CONTAMINATED_NO_GAIN_CLAIM，不能声称四线程提速。正式保持原3线程。\n\n'
        '隔离流式CTC候选：1线程、一个recognizer重用，同一公开WAV按实时节奏输入。计划输入结束到最终结果为435.846/354.027/379.524/377.206ms；这是final_after_scheduled_input_end_ms，额外tail_wait_ms参数为0，并非扬声器首声或正式ASR耗时。四轮输出均27字，与旧输出29字不一致；旧输出也不是gold，无准确率通过结论。未接正式GTCRN/Silero/录音端点管线，未验证真实录音/渲染FPS或端到端提速，后台memory有变化。\n\n'
        '实际执行probe SHA941bad1dfeb3c72f1704b9d1a4ddf84c15b92e6153fc55eb99774714a8fa43e2：root将pacing sleep钳制为非负的一行修正后重过2项现有检查；并非原agent冻结3bc版直接执行。详见evidence_final/streaming_root_result.json。正式startup未变，原ASR3线程、27B/2048/120、OmniVoice16均保持；试验后已按post_streaming_trial回执恢复聆听。\n').encode('utf-8')

    for path, raw in source_raw.items():
        assert path.read_bytes() == raw, 'Receipt changed during preparation.'
    for key, path in paths.items():
        assert path.read_bytes() == before[key], 'Documentation changed during preparation.'
    (HERE / 'evidence_final').mkdir(exist_ok=False)
    for item in frozen.values():
        (SHARED / item['path']).write_bytes(source_raw[SHARED / item['source_path']])
    (HERE / 'evidence_final/manifest.json').write_bytes(encoded(frozen))
    archives = {}
    for key, raw in before.items():
        path = HERE / 'before_final' / key
        path.parent.mkdir(parents=True, exist_ok=True)
        assert not path.exists()
        path.write_bytes(raw)
        archives[key] = {'target': rel(paths[key]), 'archive': rel(path), 'sha256': sha(raw), 'bytes': len(raw)}
    (HERE / 'before_final_manifest.json').write_bytes(encoded(archives))
    (HERE / 'current_note.txt').write_bytes(note)
    outputs['metadata/HANDOFF.json'] = encoded({
        'status': 'FINAL_V14_RESTORED_PARTIAL_GATES_VERIFIED', 'updated_utc': updated,
        'current_observation': pointer, 'modified_existing_continuation_documents': 10,
        'history': 'Initial before/ and journals preserved unchanged; all immediately previous documents, observation and handoff additionally preserved byte-for-byte in before_final/.',
        'current_acceptance': gates, 'latest_restore_observed_mono': post['observed_mono'],
        'final_receipt_manifest': rel(HERE / 'evidence_final/manifest.json'),
        'candidate_note': rel(HERE / 'current_note.txt'), 'production_or_candidate_code_changed_by_doc_revision': False,
        'root_public_board_asr_tests_were_performed': True,
        'document_revision_device_model_private_database_access': False,
        'strict_verified_state_updater_executed_or_modified': False,
        'initial_109_check_scope': 'Historical initial write, before later root receipts and this final delta; final consistency is a separate report.'})
    final_plan = {'updated_utc': updated, 'before': archives,
        'after': {key: {'target': rel(paths[key]), 'sha256': sha(raw), 'bytes': len(raw)} for key, raw in outputs.items()},
        'evidence_final': frozen, 'current_note_sha256': sha(note)}
    (HERE / 'plan_final.json').write_bytes(encoded(final_plan))
    written = []
    try:
        for key, raw in outputs.items():
            path = paths[key]
            assert path.read_bytes() == before[key]
            temp = path.with_name(path.name + '.v14-final-doc.tmp')
            assert not temp.exists()
            temp.write_bytes(raw)
            os.replace(temp, path)
            written.append(key)
    except BaseException:
        for key in reversed(written):
            if paths[key].read_bytes() == outputs[key]:
                paths[key].write_bytes(before[key])
        raise
    journal = {'status': 'APPLIED_FINAL_DOC_METADATA_DELTA', 'updated_utc': updated,
        'documents': 10, 'observation_and_handoff_updated': True,
        'current_observation_sha256': sha(observation_raw), 'current_note_sha256': sha(note),
        'exact_frozen_small_receipts': len(frozen), 'verified_gates': ['controls', 'priority_scope'],
        'continuous_quiet_capture_passed': False, 'strict_updater_called': False}
    (HERE / 'journal_final.json').write_bytes(encoded(journal))
    print(json.dumps(journal, ensure_ascii=False))


if __name__ == '__main__':
    main()
