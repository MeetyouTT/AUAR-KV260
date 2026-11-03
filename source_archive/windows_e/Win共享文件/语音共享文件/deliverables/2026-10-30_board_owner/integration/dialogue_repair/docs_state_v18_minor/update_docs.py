"""Update current document pointers from saved minor-release metadata only."""
import copy
import datetime
import hashlib
import json
from pathlib import Path


BASE = Path(r'E:\Win共享文件')
PROJECT = BASE / '语音共享文件'
REPAIR = PROJECT / 'deliverables/2026-10-30_board_owner/integration/dialogue_repair'
HERE = REPAIR / 'docs_state_v18_minor'
EVIDENCE = REPAIR / 'release_v18_minor_ui_candidate/minor_evidence'
REVISION = 'v18_minor'
STATUS = 'V18_MINOR_READY_LISTENING_ENABLED_STABILITY_AND_MEMORY_UNDER_REVIEW'
STARTUP = '90f6c6c40f6501362aa77483235a7260a212de6e3357615311bdaa5cc193ebbe'
MANIFEST = '6d03c1d7aa95a9c5615f540606699f67c4ee7a44be1e50dcb2983c6c555e3637'


def load(path):
    return json.loads(path.read_bytes())


def encode(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')


def reference(path):
    raw = path.read_bytes()
    return {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}


def create(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as handle:
        handle.write(raw)


def replace_block(raw, marker, body, new_marker=None):
    first = ('<!-- ' + marker + ' -->').encode()
    last = ('<!-- /' + marker + ' -->').encode()
    start = raw.index(first)
    end = raw.index(last, start) + len(last)
    marker = new_marker or marker
    replacement = ('<!-- ' + marker + ' -->\n' + body + '\n<!-- /' + marker + ' -->').encode('utf-8')
    return raw[:start] + replacement + raw[end:]


assert not (HERE / 'before_manifest.json').exists(), 'one_shot_already_started'
now = datetime.datetime.now(datetime.timezone.utc).isoformat()
previous_handoff_path = REPAIR / 'docs_state_v18/HANDOFF.json'
previous_handoff_ref = reference(previous_handoff_path)
previous_handoff = load(previous_handoff_path)
previous_observation_path = REPAIR / 'current_observation_v18.json'
previous_observation_ref = reference(previous_observation_path)
previous = load(previous_observation_path)
targets = {row['key']: Path(row['path']) for row in previous_handoff['changed_documents']}
assert len(targets) == 12 and all(path.is_relative_to(BASE) for path in targets.values())
spec, ready, installed, mapping = [load(EVIDENCE / name) for name in ('spec.json', 'ready.json', 'installed.json', 'source_mapping.json')]
resume_path = REPAIR / 'progress_followup_20261031/normal_resume_1793496887984885700.json'
resume = load(resume_path)
measurement_path = REPAIR / 'progress_followup_20261031/minor_ui_measurement.json'
measurement = load(measurement_path)
first_samples_path = Path(measurement['sample_file'])
first_samples = load(first_samples_path)['samples']
later_samples_path = REPAIR / 'progress_followup_20261031/worker_observation_1793497379321820800.json'
later_samples = load(later_samples_path)['samples']
reason_path = REPAIR / 'memory_reason_candidate/actual_v18_minor_current.json'
reason = load(reason_path)
leftovers_path = REPAIR / 'cold_boot_recovery_candidate/LOCAL_TEMP_LEFTOVERS.json'
leftovers = load(leftovers_path)
assert all(value['startup_sha256'] == STARTUP for value in (spec, installed['spec'], mapping, resume))
assert all(value['source_manifest_sha256'] == MANIFEST for value in (spec, installed['spec'], mapping))
assert spec['boot_id'] == mapping['boot_id'] == previous['board_boot_id']
assert spec['component_pins'] == len(mapping['component_pins']) == 379
assert mapping['component_pins'] == spec['component_sha256']
assert len(installed['source_files']) == 3
assert all(mapping['component_pins'][name] == value for name, value in installed['source_files'].items())
assert 'board/runtime/history_delete.py' not in mapping['component_pins']
assert ready['status'] == 'PRODUCTION_BOARD_BUSINESS_READY' and ready['listening_enabled'] is True
assert resume['enabled_after'] is True and resume['preference_verified'] is True
assert all(sample['startup_sha256'] == STARTUP for sample in first_samples + later_samples)
assert all(sample['board_boot_id'] == spec['boot_id'] for sample in first_samples + later_samples)
assert len(first_samples) == 40 and len(later_samples) == 30
assert reason['boot_match'] and reason['configuration_file_pin_match']
assert reason['worker']['completed'] == 1 and reason['worker']['discarded'] == 9
assert reason['summary']['rejection_reasons'] == ['negation_missing']

windows = []
for samples, path in ((first_samples, first_samples_path), (later_samples, later_samples_path)):
    first, last = samples[0], samples[-1]
    seconds = last['observed_mono'] - first['observed_mono']
    frames = last['native']['frames'] - first['native']['frames']
    assert all(sample['phase'] == 'IDLE' and not sample['playing'] for sample in samples)
    assert all(sample['safe_capture']['counters']['speech_starts'] == 0 and sample['safe_capture']['counters']['submitted'] == 0 for sample in samples)
    assert all(sample['runtime_faults']['count'] == sample['renderer_worker_faults']['count'] == 0 for sample in samples)
    armed = [first['safe_capture']['counters']['armed'], last['safe_capture']['counters']['armed']]
    assert armed[0] == armed[1]
    windows.append({'reference': reference(path), 'samples': len(samples),
        'first_mono': first['observed_mono'], 'last_mono': last['observed_mono'],
        'seconds': seconds, 'native_completions': frames, 'native_completions_per_second': frames / seconds,
        'phase': 'IDLE', 'capture_armed_start_end': armed, 'speech_starts': 0, 'submitted': 0,
        'gui_faults': 0, 'worker_faults': 0,
        'capture_failures_start_end': [first['capture_performance']['capture_failures'], last['capture_performance']['capture_failures']],
        'physical_audio_acceptance': False, 'physical_screen_fps_verified': False})
last = later_samples[-1]
assert last['memory']['completed'] == 1 and last['memory']['discarded'] == 15
assert last['memory_retry']['failure_streak'] == 7
assert last['capture_performance']['capture_failures'] == 2
assert last['last_capture_failure']['error']['code'] == 'pcm_input_queue_overflow'
cleanup = {'reference': reference(leftovers_path), 'directory_count': len(leftovers['directories']),
    'regular_file_bytes': sum(item['bytes'] for directory in leftovers['directories'] for item in directory['entries'] if item['kind'] == 'regular_file'),
    'data_scope': 'Public synthetic temporary test databases only',
    'status': 'AUTOMATIC_APPROVAL_REJECTED_CLEANUP_STOPPED',
    'inventory_records_prefix_rejection': leftovers['broad_prefix_cleanup_approval'],
    'coordinator_report': 'Root exact LiteralPath cleanup was also rejected by automatic approval review. User was informed and retries stopped.',
    'cleanup_executed_by_document_task': False}
source_paths = [EVIDENCE / name for name in ('spec.json', 'ready.json', 'installed.json', 'source_mapping.json')]
source_paths += [resume_path, measurement_path, first_samples_path, later_samples_path, reason_path,
                 leftovers_path, previous_handoff_path, previous_observation_path]
source_paths += [REPAIR / 'animation_thinking_collaboration/ui_final_values_candidate/TEST_RESULTS.json',
                 REPAIR / 'performance_review_newboot/worker_fault_candidate_v2/TEST_RESULT.json',
                 REPAIR / 'release_v18_minor_ui_candidate/LOCAL_TEST_RESULT.json']
source_refs = [reference(path) for path in source_paths]
originals = {key: path.read_bytes() for key, path in targets.items()}
before = []
for key, path in targets.items():
    archive = HERE / 'before' / path.relative_to(BASE)
    create(archive, originals[key])
    before.append({'key': key, 'original': reference(path), 'archive': reference(archive)})
create(HERE / 'before_manifest.json', encode({'schema': 'aura.docs-original-bytes.v1', 'files': before}))

memory = {'latest_runtime_reference': reference(later_samples_path), 'observed_mono': last['observed_mono'],
    'worker': last['memory'], 'retry': last['memory_retry'], 'counters_are_process_local': True,
    'last_specific_failure_reference': reference(reason_path), 'last_specific_failure_mono': reason['observed_mono'],
    'last_specific_failure': reason['summary'], 'specific_failure_worker': reason['worker'],
    'all_discards_same_cause_verified': False, 'whole_store_health_verified': False,
    'interpretation': 'Latest saved runtime has completed1/discarded15/streak7 and 60-second retry backoff. Earlier dedicated probe observed negation_missing at completed1/discarded9. The current rejection series remains under investigation. Rejected sources remain protected by the original validator.'}
operator = {'publisher': str(REPAIR / 'release_v18_minor_ui_candidate/publish_minor.py'),
    'spec': reference(EVIDENCE / 'spec.json'), 'sole_publisher': 'root',
    'usage': 'Use the matching applied minor spec and exact spec hash. Fresh-read owners and use normal-close/start/ready through this publisher.',
    'old_887_publisher_allowed': False, 'new_boot_requires_fresh_camera_readback_pin': True}
acceptance = copy.deepcopy(previous['current_revision_acceptance'])
acceptance.update(controls_verified=False, continuous_capture_passed=False,
    short_capture_verified=False, full_physical_dialogue_acceptance=False,
    physical_audio_acceptance_passed=False, multi_hour_stability_verified=False,
    normal_ui_listening_restore_verified=True, source_and_service_verified=True,
    installation_ready_verified=True, worker_fault_metadata_persistence_deployed=True,
    final_widget_value_deduplication_deployed=True, prior_autonomous_cancel_cause_resolved=False)
observation = copy.deepcopy(previous)
observation.update(revision=REVISION, status=STATUS, updated_utc=now, startup_sha256=STARTUP,
    source_manifest_sha256=MANIFEST, configuration_sha256=spec['configuration_sha256'],
    source_observed_mono=mapping['observed_mono'], observed_mono=last['observed_mono'],
    supervisor_pid=mapping['supervisor']['pid'], supervisor_birth_ticks=mapping['supervisor']['birth_ticks'],
    gtk_pid=mapping['gtk']['pid'], gtk_birth_ticks=mapping['gtk']['birth_ticks'],
    camera_pid=mapping['camera']['pid'], camera_birth_ticks=mapping['camera']['birth_ticks'],
    phase=last['phase'], playing=last['playing'], listening=last['listening'],
    runtime_faults=last['runtime_faults'], renderer_worker_faults=last['renderer_worker_faults'],
    latest_audio_metadata=last['audio_output'], latest_capture_metadata=last['safe_capture'],
    last_capture_failure=last['last_capture_failure'], capture_performance=last['capture_performance'],
    publication_ready=ready, user_authorized_resume=resume, memory=memory,
    performance={'windows': windows, 'target_fps': 16,
        'first_window_sampled_full_callback_wall_ms_p50': measurement['stats']['ui_callback_previous']['wall_ms']['p50'],
        'callback_statistics_are_sparse_latest_samples': True,
        'original_cancel_cause_resolved': False, 'human_audio_acceptance': False,
        'same_workload_controlled_ab_verified': False},
    minor_overrides=spec['minor_overrides'], current_revision_acceptance=acceptance,
    operator_instruction=operator, previous_current_snapshot=previous_observation_ref,
    public_test_cleanup=cleanup, evidence=source_refs)
observation['pending'].update(capture_cancellation_cause_unknown=True, capture_overflow_observed=True,
    memory_rejection_stability_under_review=True, new_human_listening_feedback_pending=True,
    m03_date_delete_deployed=False, m03_newboot_arm_revalidation_in_progress=True)
observation['verification_scope_notice'] = ('Saved minor release source/READY and normal UI resume receipts establish the current instance. '
    'Two idle observation windows measured render completion and stable within-window capture generations. '
    'Earlier autonomous cancellation causality, recorded input overflow, memory rejection stability and current human audio acceptance remain open.')
canonical = REPAIR / 'current_observation_v18_minor.json'
create(canonical, encode(observation))
current = {**reference(canonical), **{key: observation[key] for key in ('revision', 'status', 'startup_sha256', 'source_manifest_sha256', 'configuration_sha256', 'component_pins')}, 'observations_are_not_full_acceptance': True}
note = (
    'v18 minor 当前接续，性能、记忆与真人验收继续进行\n\n'
    f'运行根 {spec["target"]}。startup SHA {STARTUP}，manifest SHA {MANIFEST}，379份组件，config SHA {spec["configuration_sha256"]}。\n'
    f'保存的boot为 {spec["boot_id"]}，supervisor {ready["main_pid"]}/birth{mapping["supervisor"]["birth_ticks"]}，GTK {ready["gtk_pid"]}/birth{mapping["gtk"]["birth_ticks"]}，camera {mapping["camera"]["pid"]}/birth{mapping["camera"]["birth_ticks"]}。操作前现读归属与入口。\n'
    '本版已READY，正常界面恢复命令及偏好落盘核验通过。末次采样为enabled=true、WAITING_SPEECH、mic=true，界面可见，采用免唤醒词半双工。\n'
    '本次接入GTK最终控件值处理、业务控件去重、worker异常持久化与native_tid三份源码。root独立的8项、14项、18项相关检查通过。\n'
    f'两段全IDLE观察分别为{windows[0]["seconds"]:.3f}秒/{windows[0]["native_completions_per_second"]:.3f}次native完成每秒和{windows[1]["seconds"]:.3f}秒/{windows[1]["native_completions_per_second"]:.3f}次每秒，目标16fps。首段完整callback抽样中位60.209ms。两窗口各自armed保持2和3，语音提交0，GUI与worker故障计数0。物理FPS、真人音频和多小时稳定性仍待验收。\n'
    '原自主取消原因尚未证实解决。较晚快照累计capture_failures=2，最后错误为pcm_input_queue_overflow，来自第2代原8帧输入队列。第3代在第二观察窗口内稳定，两个窗口不能拼成全程无中断。\n'
    '记忆最新通用快照mono13239.839为完成1/丢弃15/streak7/60秒退避。专用原因探针mono13055.278在完成1/丢弃9时记录negation_missing，仅明确该次拒绝原因。后台仍在运行，摘要保真拒绝与退避正在排查，失败来源受原保真规则保护。\n'
    '新版试听反馈尚待用户回复。上一boot声音连续、人数正确和未校准声纹答复保留为历史。M03日期删除候选及其新boot重绑仍在验证，尚未部署。声纹未校准，全状态自然动作及24fps候选尚待验证。\n'
    f'公开合成测试遗留5个临时目录，文件合计约{cleanup["regular_file_bytes"] / 1000000:.2f}MB。自动审批拒绝了清理请求，root已通知用户并停止重试，记录见 {leftovers_path}。\n'
    f'接续入口 {canonical}。匹配发布器 {operator["publisher"]}，由root持匹配spec与哈希操作。上一70a2快照保存在docs_state_v18，本次改前文档原字节归档在 {HERE / "before"}。\n'
)
create(HERE / 'current_note.txt', note.encode('utf-8'))
short = ('v18 minor已READY并恢复自动聆听。两段全IDLE采样约13.02与11.84次native完成/秒，目标16fps，首段完整callback抽样中位60.209ms。新版真人试听待反馈。\n\n'
    '原自主取消因果、已记录的输入队列溢出及记忆摘要拒绝/退避仍在排查。M03日期删除候选尚未部署。\n\n'
    f'详见[当前观测]({canonical.as_posix()})、[接续简记]({(HERE / "current_note.txt").as_posix()})和[状态]({(REPAIR / "STATUS.json").as_posix()})。')
updates = {}
agent_body = '\n'.join('- ' + line for line in note.strip().splitlines() if line)
updates['project_AGENTS'] = replace_block(originals['project_AGENTS'], 'board-business-live-20261030', agent_body)
updates['project_README'] = replace_block(originals['project_README'], 'dialogue-current-20261031', short)
analysis = replace_block(originals['analysis_README'], 'current-v18-20261031', short, 'current-v18-minor-20261031')
analysis = replace_block(analysis, 'board-business-live-20261030', agent_body)
analysis = replace_block(analysis, 'performance-dialogue-plan-20261031', f'- [性能与对话平衡优化方案]({(BASE / "语言模型分析/性能与对话平衡优化方案_20261031.txt").as_posix()})已补充minor现役采样和未完成事项。')
updates['analysis_README'] = analysis
old_note = (REPAIR / 'docs_state_v18/current_note.txt').read_bytes()
for key in ('owner_continuation', 'performance_plan', 'analysis_performance_plan'):
    assert originals[key].startswith(old_note), key
    updates[key] = note.encode('utf-8') + originals[key][len(old_note):]

common = {key: observation[key] for key in ('status', 'updated_utc', 'root', 'startup_sha256', 'source_manifest_sha256',
    'configuration_sha256', 'component_pins', 'board_boot_id', 'supervisor_pid', 'gtk_pid', 'camera_pid',
    'camera_birth_ticks', 'current_revision_acceptance', 'operator_instruction', 'verification_scope_notice', 'evidence')}
common.update(current_revision=REVISION, current_observation=current,
    last_observed_listening_enabled=True, last_observed_listening_state=last['listening']['state'],
    microphone_open=last['listening']['microphone_open'], playing=last['playing'],
    automatic_listening_restored=True, latest_user_listening_choice=True, user_manual_pause_preserved=False,
    memory_retry_history=memory, memory_failure_metadata=reason,
    latest_memory_runtime_counters={'process_revision': REVISION, 'boot_id': spec['boot_id'],
        'observed_mono': last['observed_mono'], 'completed': 1, 'discarded': 15, 'failure_streak': 7,
        'error_present': True, 'counters_are_process_local': True, 'whole_store_health_verified': False},
    last_detailed_memory_observation={'current_detailed_store_snapshot_available': False, 'runtime_only': memory},
    later_capture_failure_count=2, public_test_cleanup=cleanup,
    m03_date_delete_deployed=False, current_live_state_claimed=False)


def refresh(document):
    document.update(copy.deepcopy(common))
    for key in ('main_pid', 'last_verified_ui_supervisor_pid', 'last_observed_ui_supervisor_pid'):
        if key in document:
            document[key] = ready['main_pid']
    for key in ('last_verified_gtk_pid', 'last_observed_gtk_pid'):
        if key in document:
            document[key] = ready['gtk_pid']
    if 'last_verified_pid_fields_revision' in document:
        document['last_verified_pid_fields_revision'] = REVISION + '_source_mapping'
    for key in acceptance:
        if key in document:
            document[key] = acceptance[key]
    document['verified_listening'] = {'revision': REVISION, 'startup_sha256': STARTUP,
        'status': 'NORMAL_UI_RESTORE_AND_PREFERENCE_CONFIRMED', 'restore_reference': reference(resume_path),
        'controls_verified': False, 'continuous_capture_passed': False,
        'prior_autonomous_cancel_cause_resolved': False}
    document['response_latency'] = {'revision': REVISION, 'startup_sha256': STARTUP,
        'dialogue_output_format': 'dialogue_abc_v1', 'new_human_waiting_acceptance': False,
        'audible_first_sound_measured': False, 'new_listening_feedback_pending': True,
        'historical_feedback': previous['historical_user_feedback'], 'current_observation': current}


json_keys = ('dialogue_STATUS', 'implementation', 'production_live', 'resume_verification', 'character_switch', 'windows_coordination')
for key in json_keys:
    document = json.loads(originals[key])
    document.setdefault('continuation_history', []).append({'superseded_by_revision': REVISION,
        'previous_status': document.get('status'),
        'original_bytes_archive': next(row['archive'] for row in before if row['key'] == key)})
    refresh(document)
    for field in ('production', 'production_business_live'):
        if isinstance(document.get(field), dict):
            refresh(document[field])
    if key == 'character_switch':
        document['current_pair_observation'] = 'Minor UI/worker source and service verified. Native b243/pair998710 current. Two idle completion-rate windows observed. Physical FPS and current human audio acceptance pending.'
    if key == 'windows_coordination':
        document['updated_at'] = now
        for field in ('production_UI_switch', 'production_business_cutover'):
            document[field].update(state=STATUS, current_revision=REVISION, updated_utc=now,
                startup_sha256=STARTUP, source_manifest_sha256=MANIFEST,
                configuration_sha256=spec['configuration_sha256'], current_observation=current)
    updates[key] = encode(document)

assert all(path.read_bytes() == originals[key] for key, path in targets.items()), 'concurrent_document_change'
assert all(reference(Path(row['path'])) == row for row in source_refs), 'evidence_changed'
for key, path in targets.items():
    path.write_bytes(updates[key])
checks = []
for row in before:
    checks.append({'check': 'archive_exact:' + row['key'], 'passed': Path(row['archive']['path']).read_bytes() == originals[row['key']]})
for key in json_keys:
    document = load(targets[key])
    for field in (None,) + tuple(name for name in ('production', 'production_business_live') if isinstance(document.get(name), dict)):
        item = document if field is None else document[field]
        passed = (item['startup_sha256'] == STARTUP and item['current_observation']['sha256'] == reference(canonical)['sha256']
            and item['latest_memory_runtime_counters']['discarded'] == 15
            and item['memory_failure_metadata']['worker']['discarded'] == 9
            and item['m03_date_delete_deployed'] is False
            and item['current_revision_acceptance']['full_physical_dialogue_acceptance'] is False)
        checks.append({'check': 'current_scope:' + key + ':' + str(field), 'passed': passed})
for row in source_refs:
    checks.append({'check': 'evidence_unmodified:' + Path(row['path']).name, 'passed': reference(Path(row['path'])) == row})
for key in ('owner_continuation', 'performance_plan', 'analysis_performance_plan'):
    checks.append({'check': 'historical_text_suffix_exact:' + key,
        'passed': targets[key].read_bytes()[len(note.encode('utf-8')):] == originals[key][len(old_note):]})
assert reference(previous_handoff_path) == previous_handoff_ref
assert reference(previous_observation_path) == previous_observation_ref
assert all(check['passed'] for check in checks)
create(HERE / 'consistency.json', encode({'status': 'PASS', 'checks_passed': len(checks), 'checks': checks}))
handoff = {'schema': 'aura.docs-state-handoff.v1', 'status': 'V18_MINOR_CURRENT_POINTER_SNAPSHOT_DIAGNOSIS_OPEN',
    'revision': REVISION, 'updated_utc': now, 'startup_sha256': STARTUP, 'source_manifest_sha256': MANIFEST,
    'configuration_sha256': spec['configuration_sha256'], 'board_boot_id': spec['boot_id'], 'component_pins': 379,
    'current_observation': reference(canonical), 'previous_handoff': previous_handoff_ref,
    'before_manifest': reference(HERE / 'before_manifest.json'), 'current_note': reference(HERE / 'current_note.txt'),
    'consistency': reference(HERE / 'consistency.json'), 'updater': reference(Path(__file__)),
    'changed_documents': [{**reference(path), 'key': key} for key, path in targets.items()],
    'evidence': source_refs, 'checks_passed': len(checks), 'optimization_task_complete': False,
    'capture_and_memory_diagnosis_open': True, 'human_audio_acceptance_pending': True,
    'device_model_or_private_database_actions': False,
    'production_tools_candidates_or_runtime_receipts_modified': False, 'historical_bytes_preserved': True}
create(HERE / 'HANDOFF.json', encode(handoff))
print(json.dumps({'status': handoff['status'], 'documents_updated': 12, 'checks_passed': len(checks),
    'handoff_sha256': reference(HERE / 'HANDOFF.json')['sha256'],
    'current_observation_sha256': reference(canonical)['sha256']}, ensure_ascii=False))
