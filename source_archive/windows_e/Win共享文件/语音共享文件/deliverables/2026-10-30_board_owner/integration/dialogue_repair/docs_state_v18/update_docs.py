"""One-shot local documentation reconciliation from saved metadata only."""
import argparse
import copy
import datetime
import hashlib
import json
from pathlib import Path
import statistics


BASE = Path(r'E:\Win共享文件')
PROJECT = BASE / '语音共享文件'
OWNER = PROJECT / 'deliverables/2026-10-30_board_owner'
REPAIR = OWNER / 'integration/dialogue_repair'
HERE = REPAIR / 'docs_state_v18'
EVIDENCE = REPAIR / 'release_v18_newboot_candidate/newboot_evidence'
REVISION = 'v18_newboot'
STATUS = 'V18_NEWBOOT_LISTENING_ENABLED_CAPTURE_CANCELLATION_UNRESOLVED'
STARTUP = '70a2f7fa5440f2b65004d66d5c4984b664ccc2b60131a0abd9a8351591c8d4e6'
MANIFEST = 'e105159fea9a71a347b6564ef77d1db23f6596199ed27a5e8684d6b025b5bacb'
BOOT = 'bebd3e7d-e984-4517-8cbb-211df7f1c6dc'


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def load(path):
    return json.loads(path.read_bytes())


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def reference(path):
    raw = path.read_bytes()
    return {'path': str(path), 'sha256': digest(raw), 'bytes': len(raw)}


def create(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as handle:
        handle.write(raw)


def replace_block(raw, marker, body, new_marker=None):
    start_marker = ('<!-- ' + marker + ' -->').encode()
    end_marker = ('<!-- /' + marker + ' -->').encode()
    start = raw.index(start_marker)
    end = raw.index(end_marker, start) + len(end_marker)
    marker = new_marker or marker
    replacement = ('<!-- ' + marker + ' -->\n' + body + '\n<!-- /' + marker + ' -->').encode('utf-8')
    return raw[:start] + replacement + raw[end:]


parser = argparse.ArgumentParser()
parser.add_argument('--performance', required=True, type=Path)
args = parser.parse_args()
assert not (HERE / 'before_manifest.json').exists(), 'one_shot_already_started'
now = datetime.datetime.now(datetime.timezone.utc).isoformat()
prior_handoff = load(REPAIR / 'docs_state_v17/HANDOFF.json')
targets = {row['key']: BASE / row['path'] for row in prior_handoff['changed_documents']}
assert len(targets) == 12 and all(path.is_relative_to(BASE) for path in targets.values())
spec = load(EVIDENCE / 'spec.json')
ready = load(EVIDENCE / 'ready.json')
installed = load(EVIDENCE / 'installed.json')
mapping = load(EVIDENCE / 'source_mapping.json')
resume_path = REPAIR / 'progress_followup_20261031/new_boot_resume_1793495501909742600.json'
resume = load(resume_path)
reason_path = REPAIR / 'memory_reason_candidate/actual_v18_newboot_ready.json'
reason = load(reason_path)
windows_path = REPAIR / 'progress_followup_20261031/windows_model_start_1793495145082884700.json'
windows = load(windows_path)
linux_path = REPAIR / 'progress_followup_20261031/cold_boot_public_linux_1793495342501782300.json'
linux = load(linux_path)
performance = load(args.performance)
samples = performance['samples']
assert len(samples) >= 2
assert all(sample['startup_sha256'] == STARTUP for sample in samples)
assert all(data['startup_sha256'] == STARTUP for data in (spec, mapping, installed['spec']))
assert all(data['source_manifest_sha256'] == MANIFEST for data in (spec, mapping, installed['spec']))
assert spec['boot_id'] == mapping['boot_id'] == BOOT
assert spec['component_pins'] == len(mapping['component_pins']) == 379
assert mapping['component_pins'] == spec['component_sha256']
assert all(mapping['component_pins'][key] == row['sha256'] for key, row in spec['source_overrides'].items())
assert len(spec['source_overrides']) == 5
assert ready['status'] == 'PRODUCTION_BOARD_BUSINESS_READY'
assert ready['listening_enabled'] is True and ready['listening_state'] == 'WAITING_SPEECH'
assert ready['physical_microphone_opened'] is True and resume['listening']['enabled'] is True
assert reason['boot_match'] and reason['configuration_file_pin_match']
assert reason['worker']['completed'] == 29 and reason['worker']['discarded'] == 1
assert reason['summary']['rejection_reasons'] == ['negation_missing']
assert linux['tests_run'] == 10 and linux['failures'] == linux['errors'] == 0
assert windows['state']['status'] == 'READY' and windows['health']['ok'] is True

source_paths = [EVIDENCE / name for name in ('spec.json', 'ready.json', 'installed.json', 'source_mapping.json')]
source_paths += [resume_path, reason_path, windows_path, linux_path, args.performance,
                 HERE / 'previous_boot_evidence.json',
                 REPAIR / 'feature_trigger_collaboration/review_m03_r2_root_agent/REVIEW.json']
source_refs = [reference(path) for path in source_paths]
originals = {key: path.read_bytes() for key, path in targets.items()}
before = []
for key, path in targets.items():
    archive = HERE / 'before' / path.relative_to(BASE)
    create(archive, originals[key])
    before.append({'key': key, 'original': reference(path), 'archive': reference(archive)})
create(HERE / 'before_manifest.json', encode({'schema': 'aura.docs-original-bytes.v1', 'files': before}))

first, last = samples[0], samples[-1]
elapsed = last['observed_mono'] - first['observed_mono']
frames = last['native']['frames'] - first['native']['frames']
frame_rate = frames / elapsed
perf_summary = {
    'reference': reference(args.performance), 'boot_id': BOOT, 'startup_sha256': STARTUP,
    'samples': len(samples), 'first_mono': first['observed_mono'], 'last_mono': last['observed_mono'],
    'elapsed_seconds': elapsed, 'native_frame_completions': frames,
    'native_completions_per_second': frame_rate, 'target_fps': 16,
    'physical_screen_fps_verified': False, 'controlled_same_boot_ab_proven': False,
    'human_speaking_acceptance': False,
    'sampled_completed_callback_wall_ms_median': statistics.median(sample['ui_callback_previous']['wall_ms'] for sample in samples),
    'sampled_completed_callback_thread_cpu_ms_median': statistics.median(sample['ui_callback_previous']['thread_cpu_ms'] for sample in samples),
    'sampled_completed_callback_publish_ms_median': statistics.median(sample['ui_callback_previous']['publish_ms'] for sample in samples),
    'callback_values_are_sparse_latest_samples': True,
    'speech_starts': [first['safe_capture']['counters']['speech_starts'], last['safe_capture']['counters']['speech_starts']],
    'submitted': [first['safe_capture']['counters']['submitted'], last['safe_capture']['counters']['submitted']],
    'capture_armed': [first['safe_capture']['counters']['armed'], last['safe_capture']['counters']['armed']],
    'frontend_generation': [first['safe_capture']['audio_frontend']['worker_generation'], last['safe_capture']['audio_frontend']['worker_generation']],
    'continuous_capture_acceptance': False,
    'capture_cancellation': {
        'sample_index': 20, 'observed_mono': 11478.906242156,
        'state': 'CANCELLED', 'previous_listening_seconds': 74.04,
        'conversation_entered': False, 'cause_confirmed': False,
        'normal_silence_timeout_proven': False,
        'zero_gui_faults_proves_whole_pipeline_healthy': False,
    },
}
memory = {
    'reference': reference(reason_path), 'observed_mono': reason['observed_mono'],
    'worker': reason['worker'], 'retry': reason['retry'], 'summary': reason['summary'],
    'clock': reason['clock'], 'unknown_counts': reason['unknown_counts'],
    'counters_are_process_local': True, 'whole_store_health_verified': False,
    'snapshot_atomicity_verified': False,
    'interpretation': '29 completed summary tasks demonstrate progress in this process. One candidate was rejected for missing negation. Existing validation retains rejected source bodies until a successful verified commit.',
}
windows_state = windows['state']
windows_owner = {
    'session_id': windows['session_id'], 'launcher_pid': windows['owner']['pid'],
    'host_pid': windows_state['pid'], 'tts_pid': windows_state['same_unique_tts_pid'],
    'fixed_daemon_pid': windows_state['fixed_daemon_pid'], 'status': windows_state['status'],
    'status_ready_utc': windows_state['ready_utc'], 'role': windows_state['role'],
    'endpoint': f"{windows_state['listen']}:{windows_state['port']}",
    'configuration_sha256': windows_state['configuration_sha256'],
    'business_database_opened': False, 'request_logging': False, 'raw_audio_archived': False,
    'observed_from_saved_receipts_only': True, 'fresh_health_called_by_document_updater': False,
    'reference': reference(windows_path),
}
prior_observation = load(REPAIR / 'current_observation_v17.json')
acceptance = {key: False for key in prior_observation['current_revision_acceptance']}
acceptance.update(source_and_service_verified=True, installation_ready_verified=True,
                  small_asr_production_selected=True, cold_boot_recovery_code_deployed=True,
                  actual_linux_journal_recovery_tests_passed=True, normal_ui_listening_restore_verified=True,
                  feature_v3_source_deployed=True, memory_h01_and_summary_r2_deployed=True,
                  speaker_close_deployed=True, ui_redundant_setter_reduction_deployed=True)
operator = {
    'publisher': str(REPAIR / 'release_v18_newboot_candidate/publish_newboot.py'),
    'spec': reference(EVIDENCE / 'spec.json'),
    'usage': 'Use matching applied spec, its exact --spec-sha256 and --execute-root-only. Fresh-read owners before guard/window-inspect/normal-close/start/ready.',
    'sole_publisher': 'root', 'old_887_publisher_allowed': False,
    'new_boot_requires_fresh_camera_readback_pin': True,
}
historical_feedback = {
    'boot_id': '8100a7fd-0c6a-46c4-82b8-f874988a1521', 'revision': 'v17_human_session',
    'source': 'User replies in the coordinator conversation before the v18 restart',
    'audio_feedback': '声音连续，等待可以接受', 'visual_feedback': '人数回答正确',
    'voiceprint_feedback': '说明尚未校准，无法可靠确认身份',
    'exact_voice_status_turn_timing_bound': False, 'new_boot_human_acceptance': False,
}
notice = ('Saved new-boot source/379-pin/READY and normal UI resume receipts establish this recovered instance. '
          'Previous-boot human feedback, synthetic tests and audio counters remain separately scoped. '
          'New-boot human dialogue and long-run acceptance remain pending.')
observation = {
    'schema': 'aura.current-document-observation.v1', 'revision': REVISION, 'status': STATUS,
    'updated_utc': now, 'root': spec['target'], 'startup_sha256': STARTUP,
    'source_manifest_sha256': MANIFEST, 'configuration_sha256': spec['configuration_sha256'],
    'component_pins': 379, 'board_boot_id': BOOT,
    'native_library_sha256': spec['native_library_sha256'],
    'character_pair_selection_sha256': spec['character_pair_selection_sha256'],
    'source_observed_mono': mapping['observed_mono'],
    'supervisor_pid': mapping['supervisor']['pid'], 'supervisor_birth_ticks': mapping['supervisor']['birth_ticks'],
    'gtk_pid': mapping['gtk']['pid'], 'gtk_birth_ticks': mapping['gtk']['birth_ticks'],
    'camera_pid': mapping['camera']['pid'], 'camera_birth_ticks': mapping['camera']['birth_ticks'],
    'observed_mono': last['observed_mono'], 'phase': last['phase'], 'playing': last['playing'],
    'listening': last['listening'], 'runtime_faults': last['runtime_faults'],
    'latest_audio_metadata': last['audio_output'], 'latest_capture_metadata': last.get('safe_capture'),
    'publication_ready': ready, 'user_authorized_resume': resume,
    'frontend_options': prior_observation['frontend_options'],
    'memory': memory, 'performance': perf_summary, 'windows_model_owner': windows_owner,
    'new_boot_overrides': spec['source_overrides'],
    'current_revision_acceptance': acceptance, 'operator_instruction': operator,
    'historical_user_feedback': historical_feedback,
    'previous_boot': reference(HERE / 'previous_boot_evidence.json'),
    'pending': {
        'capture_cancellation_cause_unknown': True,
        'm03_date_delete_deployed': False, 'm03_r2_independent_local_tests_passed': 38,
        'reasoning_d01_deployed': False, 'two_field_output_deployed': False,
        'speaker_calibrated': False, 'automatic_profile_access': False,
        'new_multicomponent_motion_deployed': False, 'target_24fps_deployed': False,
        'full_physical_dialogue_acceptance': False, 'multi_hour_stability_verified': False,
    },
    'verification_scope_notice': notice, 'current_live_state_claimed': False,
    'evidence': source_refs,
}
canonical = REPAIR / 'current_observation_v18.json'
create(canonical, encode(observation))
current = {**reference(canonical), 'revision': REVISION, 'status': STATUS,
           'startup_sha256': STARTUP, 'source_manifest_sha256': MANIFEST,
           'configuration_sha256': spec['configuration_sha256'], 'component_pins': 379,
           'observations_are_not_full_acceptance': True}

note = (
    'v18 新 boot 恢复接续\n\n'
    f'运行根 {spec["target"]}。startup SHA {STARTUP}，manifest SHA {MANIFEST}，379份组件，config SHA {spec["configuration_sha256"]}。\n'
    f'新 boot {BOOT}。保存的主进程为 {ready["main_pid"]}，GTK {ready["gtk_pid"]}，相机 {mapping["camera"]["pid"]}。操作前重新核对实时入口与进程归属。\n'
    '已恢复 READY，并按用户本轮授权通过正常界面命令恢复自动聆听。恢复回执为 enabled=true、WAITING_SPEECH、mic=true，界面可见。当前采用免唤醒词半双工，生成和播放期间暂停采集。\n'
    '本轮接入 SQLite 热日志恢复三处改动与 GTK/X11 两处减负。真实 Linux 临时库的10项恢复与锁测试通过，界面16项及发布器21项本地测试通过。历史检索H01、摘要来源r2与声纹关闭修复已随现役源码保留。\n'
    f'恢复后 {len(samples)} 个被动采样中，native完成计数速率约 {frame_rate:.2f} 次/秒，目标16fps。窗口无语音提交，采集代次3→4。该计数观察用于定位显示调度，物理屏幕帧率、持续采集和真人说话负载仍待验收。\n'
    '第20号采样在mono11478.906记录CANCELLED，前一采样已聆听74.04秒且conversation_entered=false。取消原因仍在定位，正常静默超时尚未证实。GUI故障0仅覆盖当前界面诊断路径。\n'
    '新进程记忆探针记录29次完成、1次拒绝，拒绝原因是摘要缺少否定信息。摘要任务正在推进，失败来源按原校验规则保留，继续等待通过校验的摘要。此观测未覆盖全库健康。\n'
    '上一boot用户反馈声音连续且等待可接受、人数回答正确、声纹说明未校准。旧boot H01公开替身集成23项通过，其中2项验证的是处理器仍缺失。旧boot音频31累计欠载/末轮7包、两字段更慢和D01思考截断均保存为独立历史，当前boot尚无新版真人验收。\n'
    'M03日期删除仅完成本地候选独审38项与作者回归，尚未发布。声纹仍未校准，全状态自然动作及24fps候选仍待后续验证。\n'
    f'Windows模型会话 {windows["session_id"]} 已READY，职责为27B与OmniVoice16推理。业务和记忆归板端，LLM权重路径为D:/AIModels。\n'
    f'接续依据为 {canonical}。发布入口为 {operator["publisher"]}，由root使用匹配spec及哈希操作。旧文档完整原字节归档在 {HERE / "before"}。\n'
)
create(HERE / 'current_note.txt', note.encode('utf-8'))
short = (
    'v18 已在新boot恢复READY，并通过正常界面命令恢复自动聆听。SQLite启动恢复与GTK/X11减负已接入，现役379份组件。'
    f'恢复后的被动采样约 {frame_rate:.2f} 次native完成/秒，物理FPS和新版真人对话仍待验收。'
    '记忆摘要正在推进，29次完成与1次否定信息保真拒绝属于本次进程。M03日期删除仍为未发布候选。\n\n'
    '采集出现CANCELLED后重新开启，原因仍在定位，持续采集验收尚未通过。\n\n'
    f'详见[当前观测]({canonical.as_posix()})、[接续简记]({(HERE / "current_note.txt").as_posix()})和[状态]({(REPAIR / "STATUS.json").as_posix()})。'
)
updates = {}
agent_body = '\n'.join('- ' + line for line in note.strip().splitlines() if line)
updates['project_AGENTS'] = replace_block(originals['project_AGENTS'], 'board-business-live-20261030', agent_body)
updates['project_README'] = replace_block(originals['project_README'], 'dialogue-current-20261031', short)
analysis = replace_block(originals['analysis_README'], 'current-v17-20261031', short, 'current-v18-20261031')
analysis = replace_block(analysis, 'board-business-live-20261030', agent_body)
analysis = replace_block(analysis, 'performance-dialogue-plan-20261031',
    f'- [性能与对话平衡优化方案]({(BASE / "语言模型分析/性能与对话平衡优化方案_20261031.txt").as_posix()})已补充新boot恢复和采样范围。')
updates['analysis_README'] = analysis
old_note = (REPAIR / 'docs_state_v17/current_note.txt').read_bytes()
for key in ('owner_continuation', 'performance_plan', 'analysis_performance_plan'):
    assert originals[key].startswith(old_note), key
    updates[key] = note.encode('utf-8') + originals[key][len(old_note):]

common = {
    'status': STATUS, 'updated_utc': now, 'current_revision': REVISION,
    'root': spec['target'], 'startup_sha256': STARTUP, 'source_manifest_sha256': MANIFEST,
    'configuration_sha256': spec['configuration_sha256'], 'component_pins': 379,
    'board_boot_id': BOOT, 'native_library_sha256': spec['native_library_sha256'],
    'character_pair_selection_sha256': spec['character_pair_selection_sha256'],
    'supervisor_pid': ready['main_pid'], 'gtk_pid': ready['gtk_pid'], 'camera_pid': mapping['camera']['pid'],
    'camera_birth_ticks': mapping['camera']['birth_ticks'], 'current_observation': current,
    'verification_scope_notice': notice, 'current_live_state_claimed': False,
    'last_observed_listening_enabled': last['listening']['enabled'],
    'last_observed_listening_state': last['listening']['state'],
    'microphone_open': last['listening']['microphone_open'], 'playing': last['playing'],
    'automatic_listening_restored': True, 'user_manual_pause_preserved': False,
    'latest_user_listening_choice': True, 'automatic_listening': True, 'wake_word_required': False,
    'conversation_mode': 'half_duplex', 'physical_microphone_opened': True,
    'physical_audio_played': ready['physical_audio_played'],
    'current_revision_acceptance': acceptance, 'operator_instruction': operator,
    'latest_memory_runtime_counters': {
        'process_revision': REVISION, 'boot_id': BOOT, 'observed_mono': reason['observed_mono'],
        'completed': 29, 'discarded': 1, 'failure_streak': 1, 'error_present': True,
        'counters_are_process_local': True, 'whole_store_health_verified': False,
    },
    'memory_retry_history': memory, 'memory_failure_metadata': reason,
    'last_detailed_memory_observation': {'current_detailed_store_snapshot_available': False, 'runtime_only': memory},
    'latest_human_feedback': historical_feedback,
    'audio_continuity_user_confirmed': None, 'waiting_improvement': None,
    'feedback_turn_timing_association': 'Previous-boot user feedback separately scoped in current_observation.',
    'evidence': source_refs, 'windows_model_owner': windows_owner,
    'new_multicomponent_motion_deployed': False, 'm03_date_delete_deployed': False,
    'reasoning_d01_deployed': False, 'two_field_output_deployed': False,
}


def refresh(document):
    document.update(copy.deepcopy(common))
    for key in ('main_pid', 'last_verified_ui_supervisor_pid', 'last_observed_ui_supervisor_pid'):
        if key in document:
            document[key] = ready['main_pid']
    for key in ('last_verified_gtk_pid', 'last_observed_gtk_pid'):
        if key in document:
            document[key] = ready['gtk_pid']
    for key in ('last_known_camera_pid', 'last_verified_camera_pid'):
        if key in document:
            document[key] = mapping['camera']['pid']
    if 'last_verified_pid_fields_revision' in document:
        document['last_verified_pid_fields_revision'] = REVISION + '_source_mapping'
    for key in acceptance:
        if key in document:
            document[key] = acceptance[key]
    if 'listening' in document:
        document['listening'] = last['listening']['enabled']
    if 'microphone_or_playback_started' in document:
        document['microphone_or_playback_started'] = True
    document['verified_listening'] = {
        'revision': REVISION, 'startup_sha256': STARTUP,
        'status': 'RESTORED_BY_NORMAL_UI_COMMAND', 'restore_reference': reference(resume_path),
        'controls_verified': False, 'continuous_capture_passed': False,
        'cold_boot_automatic_rearm_retested': False,
    }
    document['response_latency'] = {
        'revision': REVISION, 'startup_sha256': STARTUP, 'dialogue_output_format': 'dialogue_abc_v1',
        'new_human_waiting_acceptance': False, 'audible_first_sound_measured': False,
        'historical_feedback': historical_feedback, 'current_observation': current,
    }


json_keys = ('dialogue_STATUS', 'implementation', 'production_live', 'resume_verification',
             'character_switch', 'windows_coordination')
for key in json_keys:
    document = json.loads(originals[key])
    document.setdefault('continuation_history', []).append({
        'superseded_by_revision': REVISION,
        'previous_status': document.get('status'),
        'original_bytes_archive': next(row['archive'] for row in before if row['key'] == key),
    })
    refresh(document)
    for field in ('production', 'production_business_live'):
        if isinstance(document.get(field), dict):
            refresh(document[field])
    if key == 'character_switch':
        document['current_pair_observation'] = 'New-boot source verified. Native b243 and pair998710 retained. UI/X11 responsiveness changes deployed. Physical FPS and new-boot human dialogue pending.'
    if key == 'windows_coordination':
        document['updated_at'] = now
        for field in ('production_UI_switch', 'production_business_cutover'):
            document[field].update(state=STATUS, current_revision=REVISION, updated_utc=now,
                startup_sha256=STARTUP, source_manifest_sha256=MANIFEST,
                configuration_sha256=spec['configuration_sha256'], component_pins=379,
                current_observation=current, physical_microphone_opened=True,
                physical_audio_played=ready['physical_audio_played'])
    updates[key] = encode(document)

assert all(path.read_bytes() == originals[key] for key, path in targets.items()), 'concurrent_document_change'
assert all(reference(Path(row['path'])) == row for row in source_refs), 'source_evidence_changed'
for key, path in targets.items():
    path.write_bytes(updates[key])

checks = []
for row in before:
    ok = Path(row['archive']['path']).read_bytes() == originals[row['key']]
    checks.append({'check': 'original_bytes_preserved:' + row['key'], 'passed': ok})
for key in json_keys:
    document = load(targets[key])
    for field in (None,) + tuple(name for name in ('production', 'production_business_live') if isinstance(document.get(name), dict)):
        item = document if field is None else document[field]
        ok = (item['startup_sha256'] == STARTUP and item['board_boot_id'] == BOOT
              and item['current_observation']['sha256'] == reference(canonical)['sha256']
              and item['automatic_listening_restored'] is True
              and item['user_manual_pause_preserved'] is False
              and item['m03_date_delete_deployed'] is False
              and item['current_revision_acceptance']['full_physical_dialogue_acceptance'] is False)
        checks.append({'check': 'current_scope_and_references:' + key + ':' + str(field), 'passed': ok})
for row in source_refs:
    checks.append({'check': 'evidence_unmodified:' + Path(row['path']).name,
                   'passed': reference(Path(row['path'])) == row})
assert all(check['passed'] for check in checks)
create(HERE / 'consistency.json', encode({'status': 'PASS', 'checks_passed': len(checks), 'checks': checks}))
handoff = {
    'schema': 'aura.docs-state-handoff.v1', 'status': 'V18_NEWBOOT_CURRENT_POINTER_SNAPSHOT_DIAGNOSIS_OPEN',
    'revision': REVISION, 'updated_utc': now, 'startup_sha256': STARTUP,
    'source_manifest_sha256': MANIFEST, 'configuration_sha256': spec['configuration_sha256'],
    'board_boot_id': BOOT, 'component_pins': 379, 'current_observation': reference(canonical),
    'before_manifest': reference(HERE / 'before_manifest.json'),
    'current_note': reference(HERE / 'current_note.txt'),
    'consistency': reference(HERE / 'consistency.json'), 'updater': reference(Path(__file__)),
    'changed_documents': [{**reference(path), 'key': key} for key, path in targets.items()],
    'evidence': source_refs, 'checks_passed': len(checks),
    'device_model_or_private_database_actions': False,
    'production_tools_candidates_or_runtime_receipts_modified': False,
    'historical_bytes_preserved': True,
    'optimization_task_complete': False,
    'capture_cancellation_diagnosis_open': True,
}
create(HERE / 'HANDOFF.json', encode(handoff))
print(json.dumps({'status': handoff['status'], 'documents_updated': len(targets),
                  'checks_passed': len(checks), 'handoff_sha256': reference(HERE / 'HANDOFF.json')['sha256'],
                  'current_observation_sha256': reference(canonical)['sha256']}, ensure_ascii=False))
