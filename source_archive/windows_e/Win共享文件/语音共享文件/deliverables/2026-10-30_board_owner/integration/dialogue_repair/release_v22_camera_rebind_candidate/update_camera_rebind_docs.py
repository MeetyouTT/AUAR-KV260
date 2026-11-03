"""Update local v22 continuation documents from sealed, pinned observations."""
import argparse
import copy
import datetime
import json
from pathlib import Path

import seal_rebind as seal


REPAIR = seal.common.REPAIR
BASE = Path(r'E:\Win共享文件')
HERE = REPAIR / 'docs_state_v22'
CANONICAL_OBSERVATION = REPAIR / 'current_observation_v22.json'
PRIOR = REPAIR / 'docs_state_v21/HANDOFF.json'
PREVIOUS_OBSERVATION = REPAIR / 'current_observation_v21.json'
STARTUP = '48cb1a3a1fc62eae32c93a5be02df0bd60926cd064884a06990dd24b62762885'
STATUS = 'V22_ORIGINAL_CAMERA_REBOUND_READY_PHYSICAL_AND_MEMORY_VALIDATION_OPEN'
PINS = {
    'spec.json': 'ecdc034bd06cdd15bffe004a3ac1be3a6bc350dc3c879d91d3a19403f5c0f74a',
    'ready.json': '7ca292f5ad7d8e66de59b45f41cc2370e737e741c907db365e86485380297036',
    'installed.json': '822dded51de787e32b3dbd7f2cea6571d3f13f46d310d9365c28d965c94255f6',
    'source_mapping.json': '25762cca701602c8ea5d3c0fea649e0b89ebf220b9b66948fc68b11c05ba4a6f',
}
FIXED = {
    'docs_state_v21/HANDOFF.json': '8434b07632c3dbb5c508ce4bee85046d05b68c8725ff4ade0f6d995652cb6333',
    'current_observation_v21.json': 'd4115751f376dbea6f15dfe22876fc1867202836563e1b6fde183a2c639400b3',
    'docs_state_v21/DISPLAY_FULL_PERIOD_ADDENDUM.json': '5ebc9397428956d498f29f3aeba2b6c8450ed2e9866b22bc4bc79bbcf8d92ae7',
    'docs_state_v21/MEMORY_REASON_ADDENDUM.json': 'b3dd083e0d8ff48cd25e46cbb2be913570859f8d1a596bd123e4e368f56ba46b',
    'jpeg_demand_camera_trial_analysis_v21/ACTUAL_REVIEW.json': '3ea96cb662373f459cfa146e09906c5a60249e6ce34c96748c31e02ff59f4d0b',
    'progress_followup_20261031/model_health_1793509521568071300.json': '70358e243c216f84384f75a9b515bd6def6afd5bbf99e8eaa17d67b1fbba5814',
    'progress_followup_20261031/v22_display_observe_1793509353239944900.json': 'db7b0164c4faf2a38470f9d7102fd996210ef623d008b26507f7dbe7e14bb0eb',
}
TRIAL = REPAIR / 'jpeg_demand_camera_trial_v21'
TRIAL_RECEIPTS = (
    'ACTUAL_stop-candidate_1793508846114881200.json',
    'ACTUAL_stop-candidate_1793508867972333700.json',
    'ACTUAL_finalize_1793509016452524000.json',
)
WAKE = REPAIR / 'progress_followup_20261031/camera_trial_display_wake_1793508914286925000.json'


def need(condition, reason):
    if not condition:
        raise ValueError(reason)


def load(path):
    return json.loads(path.read_bytes())


def reference(path):
    raw = path.read_bytes()
    return {'path': str(path), 'sha256': seal.common.sha(raw), 'bytes': len(raw)}


def validate_observation(value, bundle):
    spec, mapping = bundle['spec'], bundle['mapping']
    need(value.get('startup_sha256') == STARTUP and value.get('board_boot_id') == spec['boot_id'],
         'current_v22_snapshot_required')
    listening = value.get('listening', {})
    need(listening.get('enabled') is False and listening.get('state') == 'PAUSED'
         and listening.get('microphone_open') is False
         and value.get('phase') == 'IDLE' and value.get('playing') is False,
         'latest_user_pause_required')
    need(type(value.get('observed_mono')) in (int, float)
         and value['observed_mono'] >= mapping['observed_mono'], 'post_seal_runtime_snapshot_required')
    return value


def validate_display(value, bundle):
    mapping, spec = bundle['mapping'], bundle['spec']
    owners = value.get('owners', {})
    need(value.get('status') == 'XCB_READONLY_OBSERVATION_COMPLETE' and value.get('startup_sha256') == STARTUP
         and value.get('policy_left') == 'original' and value.get('policy_modified') is False
         and value.get('observer_reset_calls') == 0 and value.get('full_component_checks') == [380, 380]
         and value.get('observed_periodic_idle_resets') is True and value.get('external_input_not_excluded') is True
         and all(owners.get(key) == mapping[key] for key in ('supervisor', 'gtk', 'camera'))
         and all(owners.get(key) == spec[key] for key in ('boot_id', 'startup_sha256', 'configuration_sha256', 'source_manifest_sha256')),
         'current_original_policy_display_observation_required')
    rows = value.get('samples', [])
    need(len(rows) == 31 and value.get('idle_drop_count') == 6 and value.get('max_idle_ms') == 4928,
         'actual_v22_display_sample_counts_required')
    need(all(row.get('screen_saver') == {'allow_exposures': 1, 'interval': 600, 'prefer_blank': 1, 'timeout': 600}
             and row.get('dpms_enabled') is True and row.get('dpms_level') == 0
             and row.get('dpms_timeouts') == [600, 600, 600] and row.get('xss_state') == 0
             and row.get('enabled') is False and row.get('microphone_open') is False
             and row.get('state') == 'PAUSED' and row.get('playing') is False for row in rows),
         'all_display_samples_must_preserve_user_pause_and_original_policy')
    need(bundle['observed'] is not None and mapping['observed_mono'] <= value['observed_mono'] <= bundle['observed']['observed_mono'],
         'display_observation_must_follow_seal_and_precede_final_snapshot')
    return value


def read_bundle(observation_path=None, observation_sha=None, display_path=None, display_sha=None):
    raws = {name: seal.common.pinned(seal.EVIDENCE / name, digest) for name, digest in PINS.items()}
    spec, ready, installed, mapping = [json.loads(raws[name]) for name in PINS]
    seal.validate_mapping(mapping, spec, ready, installed)
    marker = load(seal.EVIDENCE / 'canonical_update_state.json')
    need(marker == {'phase': 'COMMITTED', 'spec_sha256': PINS['spec.json'], 'ready_sha256': PINS['ready.json']}
         and (seal.CANONICAL / 'spec.json').read_bytes() == raws['spec.json']
         and (seal.CANONICAL / 'actual_ready.json').read_bytes() == raws['ready.json'],
         'sealed_v22_must_still_be_current')
    need(spec['startup_sha256'] == STARTUP and spec['component_pins'] == 380,
         'exact_v22_component_set_required')
    fixed = {name: json.loads(seal.common.pinned(REPAIR / name, digest)) for name, digest in FIXED.items()}
    old_mapping = load(REPAIR / 'release_v21_asr2_display_candidate/asr2_display_evidence/source_mapping.json')
    changed = {key for key in mapping['component_pins']
               if mapping['component_pins'][key] != old_mapping['component_pins'].get(key)}
    need(set(mapping['component_pins']) == set(old_mapping['component_pins'])
         and changed == {'config/board_avatar_gtk.json'}, 'only_face_readback_configuration_component_may_change')
    prior_functions = load(REPAIR / 'current_observation_v20.json')['source_files']
    need(all(mapping['component_pins'].get(key) == digest for key, digest in prior_functions.items()),
         'v20_six_function_sources_must_still_match')
    trial = [load(TRIAL / name) for name in TRIAL_RECEIPTS]
    need(trial[0]['returncode'] == 2 and trial[0]['result']['status'] == 'REFUSED'
         and trial[0]['result']['reason'] == 'stop_owner_reused_or_changed'
         and trial[1]['returncode'] == 0 and trial[1]['result']['phase'] == 'CANDIDATE_STOPPED'
         and trial[2]['returncode'] == 0 and trial[2]['result']['phase'] == 'COMPLETE'
         and trial[2]['result']['restored_pid'] == mapping['camera']['pid']
         and all(row['result']['forced_kill'] is False and row['result']['old_checkpoint_restored'] is False for row in trial),
         'actual_refused_then_normal_stop_and_complete_history_required')
    wake = load(WAKE)
    need(wake == {'periodic_helper_started': False, 'reset_calls': 1,
                 'status': 'ONE_DISPLAY_WAKE_DURING_GUI_MAINTENANCE', 'timeout_policy_changed': False},
         'maintenance_wake_must_remain_separate')
    bundle = {'raws': raws, 'spec': spec, 'ready': ready, 'installed': installed, 'mapping': mapping,
              'fixed': fixed, 'trial': trial, 'observation_path': observation_path,
              'observation_sha': observation_sha, 'display_path': display_path, 'display_sha': display_sha}
    bundle['observed'] = None
    bundle['display'] = None
    if observation_path is not None:
        bundle['observed'] = validate_observation(json.loads(seal.common.pinned(observation_path, observation_sha)), bundle)
    if display_path is not None:
        bundle['display'] = validate_display(json.loads(seal.common.pinned(display_path, display_sha)), bundle)
    return bundle


def replace_block(raw, marker, body, new_marker=None):
    first = ('<!-- ' + marker + ' -->').encode()
    last = ('<!-- /' + marker + ' -->').encode()
    start = raw.index(first)
    end = raw.index(last, start) + len(last)
    name = new_marker or marker
    return raw[:start] + ('<!-- ' + name + ' -->\n' + body + '\n<!-- /' + name + ' -->').encode('utf-8') + raw[end:]


def build_plan(bundle):
    spec, ready, mapping = [bundle[key] for key in ('spec', 'ready', 'mapping')]
    observed = bundle['observed']
    need(observed is not None and bundle['display'] is not None, 'final_runtime_and_display_receipts_required')
    previous = bundle['fixed']['current_observation_v21.json']
    prior = bundle['fixed']['docs_state_v21/HANDOFF.json']
    targets = {row['key']: Path(row['path']) for row in prior['changed_documents']}
    need(len(targets) == 12 and all(path.is_relative_to(BASE) for path in targets.values()), 'exact_twelve_local_targets_required')
    originals = {key: path.read_bytes() for key, path in targets.items()}
    need(all(reference(Path(row['path'])) == {key: row[key] for key in ('path', 'sha256', 'bytes')}
             for row in prior['changed_documents']), 'prior_document_bytes_changed')
    history_display = bundle['fixed']['docs_state_v21/DISPLAY_FULL_PERIOD_ADDENDUM.json']
    history_memory = bundle['fixed']['docs_state_v21/MEMORY_REASON_ADDENDUM.json']
    jpeg = bundle['fixed']['jpeg_demand_camera_trial_analysis_v21/ACTUAL_REVIEW.json']
    need(jpeg['causal_JPEG_CPU_savings_established'] is False and jpeg['A1_repeated'] is True,
         'JPEG_confounding_and_repeated_A1_must_be_preserved')
    inputs = [seal.EVIDENCE / name for name in PINS] + [seal.EVIDENCE / 'canonical_update_state.json']
    inputs += [REPAIR / name for name in FIXED] + [TRIAL / name for name in TRIAL_RECEIPTS]
    inputs += [WAKE, bundle['observation_path'], bundle['display_path']]
    evidence = [reference(path) for path in inputs]
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    reason = observed.get('memory_reason', {})
    need(reason.get('summary', {}).get('stage') == 'full_source_validation'
         and reason['summary'].get('rejection_reasons') == ['negation_missing']
         and reason.get('retry', {}).get('last_failure_code') == 'candidate_rejected'
         and all(value == 0 for value in reason.get('unknown_counts', {}).values()),
         'actual_current_negation_diagnosis_required')
    model_health = bundle['fixed']['progress_followup_20261031/model_health_1793509521568071300.json']
    need(model_health.get('ok') is True and model_health.get('role') == 'model_inference_only'
         and model_health.get('tts_ready') is True and model_health.get('num_step') == 16,
         'actual_windows_inference_health_required')
    display = bundle['display']
    display_summary = {key: display[key] for key in ('status', 'startup_sha256', 'observed_mono',
        'full_component_checks', 'idle_drop_count', 'max_idle_ms', 'observer_reset_calls',
        'policy_left', 'policy_modified', 'external_input_not_excluded')}
    display_summary.update(samples=31, observation_seconds=display['samples'][-1]['elapsed_seconds'],
        core_timeout_seconds=600, dpms_enabled=True, dpms_timeouts_seconds=[600, 600, 600],
        physical_panel_observed=False, reference=reference(bundle['display_path']),
        first_probe_failure_preserved=True,
        first_probe_cause_reported_by_root='Read-only probe omitted ACTION, TOKEN and WINDOW environment parameters. Retried with the original execution environment.',
        first_probe_failure_reference=reference(REPAIR / 'progress_followup_20261031/v22_display_observe_1793509353239944900.json'))
    prior_display_summary = {key: history_display[key] for key in ('startup_sha256', 'status', 'elapsed_seconds',
        'samples', 'idle_drop_count', 'max_idle_ms', 'observer_reset_calls', 'external_input_not_excluded',
        'physical_panel_observed', 'physical_unattended_panel_acceptance')}
    prior_display_summary['reference'] = reference(REPAIR / 'docs_state_v21/DISPLAY_FULL_PERIOD_ADDENDUM.json')
    memory = {'current_runtime_available': True, 'observed_mono': observed['observed_mono'],
        'worker': observed.get('memory'), 'retry': observed.get('memory_retry'),
        'counters_are_process_local': True, 'whole_store_health_verified': False,
        'specific_failure_reason_available': True, 'summary_rejection_stability_unresolved': True,
        'current_diagnosis': reason, 'completion_counter_is_not_model_call_count': True,
        'previous_v21_fixed_diagnosis': {'observed_mono': history_memory['observed_mono'],
            'summary': history_memory['summary'], 'reference': reference(REPAIR / 'docs_state_v21/MEMORY_REASON_ADDENDUM.json')},
        'original_source_retained_until_successful_validated_summary': True,
        'current_status': 'SUMMARY_COMPACTION_PROGRESS_WITH_NEGATION_REJECTIONS'}
    observation = copy.deepcopy(previous)
    observation.update(revision='v22', status=STATUS, updated_utc=now, startup_sha256=STARTUP,
        source_manifest_sha256=spec['source_manifest_sha256'], configuration_sha256=spec['configuration_sha256'],
        source_observed_mono=mapping['observed_mono'], runtime_observed_mono=observed['observed_mono'],
        phase=observed['phase'], playing=observed['playing'], listening=observed['listening'],
        source_files=mapping['source_files'], publication_ready=ready,
        publication_saved_listening_preference=mapping['saved_listening_preference'],
        native_visible=mapping['native_visible'], later_runtime_observation_supplied=True, memory=memory,
        previous_current_snapshot=reference(PREVIOUS_OBSERVATION), evidence=evidence,
        display_finalization=display_summary, historical_v21_display_full_period=prior_display_summary,
        windows_inference_health={'reference': reference(REPAIR / 'progress_followup_20261031/model_health_1793509521568071300.json'),
            **{key: model_health[key] for key in ('ok', 'role', 'model', 'tts', 'tts_ready', 'num_step', 'active', 'pending')}},
        worker_fault_probe_correction={'current_metadata_available': False,
            'earlier_missing_field_default_zero_was_not_an_observed_zero': True,
            'worker_fault_absence_verified': False},
        jpeg_actual_ABA={'reference': reference(REPAIR / 'jpeg_demand_camera_trial_analysis_v21/ACTUAL_REVIEW.json'),
            'causal_CPU_savings_established': False, 'A1_repeated_preserved': True, 'B_permanently_adopted': False,
            'original_A_restored': True, 'restored_camera_pid': mapping['camera']['pid'],
            'stop_refusal_preserved': True, 'finalize_complete': True, 'forced_kill': False, 'old_checkpoint_restored': False},
        next_priority='继续对话性能优化，处理摘要否定信息校验拒绝，后续再做真人对话与声纹标定验收。')
    for name in ('supervisor', 'gtk', 'camera'):
        observation[name + '_pid'] = mapping[name]['pid']
        observation[name + '_birth_ticks'] = mapping[name]['birth_ticks']
    for name in ('native', 'runtime_faults', 'visual_timeline', 'visual_collector', 'visual_queries',
                 'visual_social', 'speaker', 'capabilities'):
        observation[name] = observed.get(name)
    observation['renderer_worker_faults'] = observed.get('renderer_worker_faults', observed.get('worker_faults'))
    observation['operator_instruction'] = {'publisher': str(seal.common.HERE / 'publish_rebind.py'),
        'spec': reference(seal.EVIDENCE / 'spec.json'), 'sole_publisher': 'root',
        'publication_expected_listening_enabled': False,
        'usage': 'Recheck current owners, exact source closure and the latest saved listening preference before later operations.'}
    observation['finalization_ready'] = True
    return finish_plan(bundle, targets, originals, observation, evidence, now)


def finish_plan(bundle, targets, originals, observation, evidence, now):
    mapping, state = bundle['mapping'], bundle['observed']
    worker, retry = state.get('memory', {}), state.get('memory_retry', {})
    faults = state.get('renderer_worker_faults', state.get('worker_faults', {}))
    note = (
        'v22 原相机方案恢复并完成界面重绑定，当前保持暂停\n\n'
        f'运行根 {observation["root"]}。startup SHA {STARTUP}，manifest SHA {observation["source_manifest_sha256"]}，config SHA {observation["configuration_sha256"]}，380份组件。\n'
        f'封存boot {observation["board_boot_id"]}，supervisor {mapping["supervisor"]["pid"]}，GTK {mapping["gtk"]["pid"]}，原A相机 {mapping["camera"]["pid"]}。本次仅更新face_readback的路径和SHA，379份其他组件原样保持。操作前现读入口与owner。\n'
        '用户最新选择“暂时保持暂停”，enabled=false、PAUSED、mic=false，界面已可见。ASR 2线程、GTCRN 1线程与原8帧队列、GTK每5秒保活继续使用。\n'
        '实际相机A/B/A已完成并恢复原A。B观测CPU比两端A低22.83%和34.56%，每次采集完成CPU低22.71%和20.24%。A1人数混合、B无人、A2一人，A2采集吞吐高约22%，结果存在混杂。早一轮A1完整保留。B峰值RSS比重启后的A2高7.50MiB，本轮继续使用原A。\n'
        'B首次停止回执为stop_owner_reused_or_changed，继续观察后确认CANDIDATE_STOPPED，最终COMPLETE。新checkpoint已由恢复A消费，全程forced_kill=false、old_checkpoint_restored=false。GUI恢复使用新的22pin私有readback闭包。\n'
        'v21暂停保活已完成635.886秒、651样本的软件观察。v22恢复后另有31样本、6次idle下降、最大4928ms，原600秒屏保和DPMS策略保持，观察器复位0次。外部输入未排除，物理面板未摄取。相机维护时的单次wake单独记录。首个v22显示探针缺少执行参数而拒绝，补齐后通过，失败回执保留。\n'
        f'新进程快照mono{state["observed_mono"]:.3f}，GUI故障{state.get("runtime_faults", {}).get("count", "未取得")}、worker故障{faults.get("count", "未取得")}。记忆完成{worker.get("completed", "未取得")}/丢弃{worker.get("discarded", "未取得")}，连续失败{retry.get("failure_streak", "未取得")}次、退避{retry.get("last_delay_seconds", "未取得")}秒，计数仅属于本进程。\n'
        'worker故障字段当前available=false，无法确认其故障计数。早期探针曾把缺失字段默认记为0，此值不能作为worker无异常的证据。\n'
        '当前固定诊断仍为full_source_validation/negation_missing。摘要完成45批并伴随5批拒绝，完成批数不能推作模型调用次数，成功压缩前保留失败批次原文。声纹未标定，新的真人听音与端点至首声继续待验。\n'
        'Windows最新健康回执为model_inference_only，27B与OmniVoice16就绪，active=true、pending=0。\n'
        'v20单日对话删除、自然身份查询、同轮图库证据和声纹事务检查的六份功能源码保持，历史92项公开ARM验证继续独立保留。自然解绑/重关联和单独登记统一命名仍有缺口。两个旧记忆测试模块缺依赖的收集失败、11个临时目录约10.3MB清理被自动审批拒绝的记录继续保留。\n'
        f'接续入口 {CANONICAL_OBSERVATION}。完整证据与原文档字节归档在 {HERE}，旧v21快照和追加回执保持独立。\n'
    )
    short = ('v22已恢复原A相机并完成界面重绑定，380份组件，仅face_readback配置变化。用户选择暂时保持暂停，ASR 2线程、GTCRN 1线程和GTK每5秒保活继续使用。\n\n'
        'JPEG实际A/B/A观测到CPU下降，但人数和采集吞吐变化带来混杂，本轮继续使用原A。新进程运行与显示补查见当前观测。记忆否定信息校验拒绝、声纹标定和新的真人对话体验继续待验。\n\n'
        f'详见[当前观测]({CANONICAL_OBSERVATION.as_posix()})、[接续简记]({(HERE / "current_note.txt").as_posix()})和[状态]({(REPAIR / "STATUS.json").as_posix()})。')
    body = '\n'.join('- ' + line for line in note.strip().splitlines() if line)
    updates = {'project_AGENTS': replace_block(originals['project_AGENTS'], 'board-business-live-20261030', body),
               'project_README': replace_block(originals['project_README'], 'dialogue-current-20261031', short)}
    analysis = replace_block(originals['analysis_README'], 'current-v21-20261031', short, 'current-v22-20261031')
    analysis = replace_block(analysis, 'board-business-live-20261030', body)
    updates['analysis_README'] = replace_block(analysis, 'performance-dialogue-plan-20261031',
        f'- [性能与对话平衡优化方案]({(BASE / "语言模型分析/性能与对话平衡优化方案_20261031.txt").as_posix()})已补充v22原相机恢复、JPEG对照混杂和待验范围。')
    old_note = (REPAIR / 'docs_state_v21/current_note.txt').read_bytes()
    for key in ('owner_continuation', 'performance_plan', 'analysis_performance_plan'):
        need(originals[key].startswith(old_note), 'previous_note_prefix_changed')
        updates[key] = note.encode('utf-8') + originals[key][len(old_note):]
    observation_raw = seal.common.encoded(observation)
    current = {'path': str(CANONICAL_OBSERVATION), 'sha256': seal.common.sha(observation_raw), 'bytes': len(observation_raw),
        'revision': 'v22', 'status': STATUS, 'startup_sha256': STARTUP,
        'source_manifest_sha256': observation['source_manifest_sha256'],
        'configuration_sha256': observation['configuration_sha256'], 'component_pins': 380,
        'observations_are_not_full_acceptance': True}
    common = {key: observation[key] for key in ('status', 'updated_utc', 'root', 'startup_sha256',
        'source_manifest_sha256', 'configuration_sha256', 'component_pins', 'board_boot_id',
        'supervisor_pid', 'gtk_pid', 'camera_pid', 'camera_birth_ticks', 'current_revision_acceptance',
        'operator_instruction', 'evidence', 'display_finalization', 'jpeg_actual_ABA', 'historical_v21_display_full_period')}
    common['worker_fault_probe_correction'] = observation['worker_fault_probe_correction']
    common['windows_inference_health'] = observation['windows_inference_health']
    common.update(current_revision='v22', current_observation=current,
        last_observed_listening_enabled=False, last_observed_listening_state='PAUSED', microphone_open=False,
        playing=False, physical_microphone_opened=False, physical_audio_played=False,
        automatic_listening_restored=False, latest_user_listening_choice=False, user_manual_pause_preserved=True,
        memory_retry_history=observation['memory'], memory_failure_metadata={
            'specific_current_failure_reason_available': True, 'stage': 'full_source_validation',
            'rejection_reasons': ['negation_missing']},
        latest_memory_runtime_counters={'process_revision': 'v22', 'boot_id': observation['board_boot_id'],
            'observed_mono': state['observed_mono'], 'completed': worker.get('completed'),
            'discarded': worker.get('discarded'), 'failure_streak': retry.get('failure_streak'),
            'current_runtime_available': True, 'whole_store_health_verified': False},
        last_detailed_memory_observation={'current_detailed_store_snapshot_available': False, 'runtime_only': observation['memory']},
        controlled_whole_board_cpu_reduction_proven=False,
        verification_scope_notice='Actual v22 one-config camera-owner rebind and READY. JPEG ABA scene/throughput confounded. Prior v21 full display period and v20 92 ARM tests remain historical. New human audio and memory stability remain open.')
    for key in ('dialogue_STATUS', 'implementation', 'production_live', 'resume_verification', 'character_switch', 'windows_coordination'):
        document = json.loads(originals[key])
        document.setdefault('continuation_history', []).append({'superseded_by_revision': 'v22',
            'previous_status': document.get('status'), 'original_bytes_archive': str(HERE / 'before' / targets[key].relative_to(BASE))})
        for item in [document] + [document[name] for name in ('production', 'production_business_live') if isinstance(document.get(name), dict)]:
            item.update(copy.deepcopy(common))
            for name in ('main_pid', 'last_verified_ui_supervisor_pid', 'last_observed_ui_supervisor_pid'):
                if name in item:
                    item[name] = mapping['supervisor']['pid']
            for name in ('last_verified_gtk_pid', 'last_observed_gtk_pid'):
                if name in item:
                    item[name] = mapping['gtk']['pid']
            if 'last_known_camera_pid' in item:
                item['last_known_camera_pid'] = mapping['camera']['pid']
            if 'last_verified_pid_fields_revision' in item:
                item['last_verified_pid_fields_revision'] = 'v22_source_mapping'
            if 'listening' in item:
                item['listening'] = False
            item['verified_listening'] = {'revision': 'v22', 'startup_sha256': STARTUP,
                'state': 'PAUSED', 'enabled': False, 'continuous_capture_passed': False}
            item['response_latency'] = {'revision': 'v22', 'startup_sha256': STARTUP,
                'new_human_waiting_acceptance': False, 'audible_first_sound_measured': False, 'current_observation': current}
        if key == 'character_switch':
            document['current_pair_observation'] = 'v22 original camera and native visibility sealed. Physical FPS and new human audio acceptance remain open.'
        if key == 'windows_coordination':
            document['updated_at'] = now
            for name in ('production_UI_switch', 'production_business_cutover'):
                document[name].update(state=STATUS, current_revision='v22', updated_utc=now,
                    startup_sha256=STARTUP, source_manifest_sha256=observation['source_manifest_sha256'],
                    component_pins=380, current_observation=current, physical_microphone_opened=False, physical_audio_played=False)
        updates[key] = seal.common.encoded(document)
    return {'bundle': bundle, 'targets': targets, 'originals': originals, 'updates': updates,
            'observation': observation, 'observation_raw': observation_raw, 'note': note, 'evidence': evidence}


def apply_plan(plan):
    bundle = plan['bundle']
    read_bundle(bundle['observation_path'], bundle['observation_sha'], bundle['display_path'], bundle['display_sha'])
    need(not HERE.exists() and not CANONICAL_OBSERVATION.exists(), 'v22_snapshot_already_exists')
    need(all(path.read_bytes() == plan['originals'][key] for key, path in plan['targets'].items()), 'concurrent_document_change')
    need(all(reference(Path(row['path'])) == row for row in plan['evidence']), 'source_evidence_changed')
    HERE.mkdir()
    archives = []
    for key, path in plan['targets'].items():
        destination = HERE / 'before' / path.relative_to(BASE)
        destination.parent.mkdir(parents=True, exist_ok=True)
        seal.exact_file(destination, plan['originals'][key])
        archives.append({'key': key, 'original': reference(path), 'archive': reference(destination)})
    seal.exact_file(HERE / 'before_manifest.json', seal.common.encoded({'files': archives}))
    seal.exact_file(CANONICAL_OBSERVATION, plan['observation_raw'])
    seal.exact_file(HERE / 'current_note.txt', plan['note'].encode('utf-8'))
    for key, path in plan['targets'].items():
        path.write_bytes(plan['updates'][key])
    need(all(Path(row['archive']['path']).read_bytes() == plan['originals'][row['key']] for row in archives), 'archive_readback_mismatch')
    need(all(path.read_bytes() == plan['updates'][key] for key, path in plan['targets'].items()), 'document_readback_mismatch')
    need(all(reference(Path(row['path'])) == row for row in plan['evidence']), 'evidence_readback_mismatch')
    handoff = {'schema': 'aura.docs-state-handoff.v1', 'status': STATUS, 'revision': 'v22',
        'startup_sha256': STARTUP, 'source_manifest_sha256': plan['observation']['source_manifest_sha256'],
        'configuration_sha256': plan['observation']['configuration_sha256'], 'component_pins': 380,
        'current_observation': reference(CANONICAL_OBSERVATION), 'previous_handoff': reference(PRIOR),
        'current_note': reference(HERE / 'current_note.txt'), 'before_manifest': reference(HERE / 'before_manifest.json'),
        'updater': reference(Path(__file__)),
        'changed_documents': [{**reference(path), 'key': key} for key, path in plan['targets'].items()],
        'evidence': plan['evidence'], 'historical_bytes_preserved': True, 'optimization_task_complete': False,
        'device_model_or_private_database_actions': False, 'production_tools_candidates_or_runtime_receipts_modified': False}
    seal.exact_file(HERE / 'HANDOFF.json', seal.common.encoded(handoff))
    seal.exact_file(HERE / 'READBACK_VERIFICATION.json', seal.common.encoded({
        'status': 'PASS', 'changed_documents': 12, 'original_byte_archives': 12,
        'all_document_and_archive_bytes_match': True, 'all_evidence_hashes_unchanged': True,
        'current_observation': reference(CANONICAL_OBSERVATION), 'handoff': reference(HERE / 'HANDOFF.json')}))
    return {'status': STATUS, 'documents_updated': 12, 'handoff': reference(HERE / 'HANDOFF.json')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('observation', 'display'):
        parser.add_argument('--' + name, required=True, type=Path)
        parser.add_argument('--' + name + '-sha256', required=True)
    parser.add_argument('--apply-local-docs', action='store_true')
    args = parser.parse_args()
    plan = build_plan(read_bundle(args.observation, args.observation_sha256, args.display, args.display_sha256))
    if args.apply_local_docs:
        print(json.dumps(apply_plan(plan)))
    else:
        print(json.dumps({'status': 'DRY_V22_DOC_PLAN_VALIDATED_NO_WRITES', 'documents': 12,
                          'startup_sha256': STARTUP, 'listening_enabled': False}))


if __name__ == '__main__':
    main()
