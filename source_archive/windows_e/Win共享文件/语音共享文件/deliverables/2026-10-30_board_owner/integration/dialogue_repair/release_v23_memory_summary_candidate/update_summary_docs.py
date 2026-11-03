"""Update twelve local continuation entries from sealed v23 observations."""
import argparse
import copy
import datetime
import json
from pathlib import Path

import seal_summary as seal


REPAIR = seal.common.REPAIR
BASE = Path(r'E:\Win共享文件')
HERE = REPAIR / 'docs_state_v23'
CURRENT = REPAIR / 'current_observation_v23.json'
PRIOR = REPAIR / 'docs_state_v22/HANDOFF.json'
PREVIOUS = REPAIR / 'current_observation_v22.json'
STATUS = 'V23_MEMORY_SUMMARY_READY_PAUSED_RUNTIME_VALIDATION_OPEN'
STARTUP = 'd848dc90cf9a890fb8bc66b2c494b78c2ae39a7e22a4743fe0ab917ca3edbae8'
PINS = {
    'spec.json': '8376770e832d82add3ae207da3228c46c34ada89b95830cdd7536f8291224ec2',
    'ready.json': 'ab81bbc36ad34cbdcbc36a5830a36b2937e7975c40bd44accc7fb258c9a70aaa',
    'installed.json': '0c60f434447bf3704b326ff98a4af76d3a9eb44730db92f816a701bdd8f581ea',
    'source_mapping.json': 'b053291dd3af5f5bc6e441288b5db91521226b903958bcbf3ca939a6541945d6',
}
OBSERVATION_SHA = 'b9ff2af933d66e50a9c7dd474a82916953c6104f9ef1780178147cd4a7e8fde4'
DISPLAY_SHA = '2ba100e90a6a4a6723657970ef16b413670e299712969218fbf88d7ac0171c5b'
PRODUCTS = {
    'common/board_memory.py': '8905770197f114cc063addb2dd40bc745d9af942f674140f43e597ff3a6b1905',
    'board/runtime/board_memory_policy.py': 'a862cc22f6c23ae90d17ef06614cdf90fa0eb4605ad0a8b74766d102aad404aa',
}
VALIDATION = 'memory_negation_model_validation_v23/'
FIXED = {
    'docs_state_v22/HANDOFF.json': '36a8ae2ab32a0bc6022a7973c4385c4b0a33949bca724c3b6969763402a7c28d',
    'current_observation_v22.json': 'ecacd54ca1a3de19a02266c50a0ea1cdd5f34a6792c39c9b14a7acded1e5deb2',
    VALIDATION + 'ACTUAL_BEFORE_ALL_R2_1793512374377139200.json': 'eaa9ec1b6d6ed76bc20df70ad73224d9f3d4f131288a1a4f442109754b55fdb8',
    VALIDATION + 'ACTUAL_CANDIDATE_R4_ALL_1793514219912878400.json': '4c9c5df0f62f5c1b1d00feb2ee6f15ba96d8d0dadc01a63e2436b4afc5796558',
    VALIDATION + 'candidate_validation_r3/ASSISTANT_SEMANTIC_REVIEW.json': '9003f00ac8434313a21ec4b03c8900efe8b745ad11138fea6a76f1b5d0952337',
    VALIDATION + 'candidate_validation_r4/ASSISTANT_SEMANTIC_REVIEW.json': '2473570c41147f08eab8319f4168bb8afa4676193159d4f4c09f8286b0768e9a',
    VALIDATION + 'candidate_validation_r4/ROOT_ADOPTION_DECISION.json': '8925ca91287561dc756b1aecd2874f57d7d1f5c0b97cbd66d6642e85ec527657',
    'progress_followup_20261031/memory_v23_display_maintenance_finish_1793514589340700200.json': '46c90a2b8e8528cea658207366779bca1f0fad2c9da66e7a65b2ac156f13f559',
}
need = seal.common.need
encoded = seal.common.encoded


def reference(path):
    raw = path.read_bytes()
    return {'path': str(path), 'sha256': seal.common.sha(raw), 'bytes': len(raw)}


def replace_block(raw, marker, body, new_marker=None):
    first = ('<!-- ' + marker + ' -->').encode()
    last = ('<!-- /' + marker + ' -->').encode()
    start = raw.index(first)
    end = raw.index(last, start) + len(last)
    name = new_marker or marker
    return raw[:start] + ('<!-- ' + name + ' -->\n' + body + '\n<!-- /' + name + ' -->').encode() + raw[end:]


def validate_observation(value, spec, mapping):
    need(value.get('status') == 'V23_PAUSED_METADATA_OBSERVATION_COMPLETE'
         and value.get('startup_sha256') == STARTUP and value.get('boot_id') == spec['boot_id']
         and value.get('source_mapping_sha256') == PINS['source_mapping.json'],
         'actual_post_seal_v23_snapshot_required')
    rows = value.get('samples', [])
    need(len(rows) == 61 and all(type(row.get('observed_mono')) in (int, float) for row in rows)
         and mapping['observed_mono'] <= rows[0]['observed_mono']
         and all(left['observed_mono'] < right['observed_mono'] for left, right in zip(rows, rows[1:])),
         'ordered_post_seal_61_sample_window_required')
    need(all(row.get('listening', {}).get('enabled') is False
         and row['listening'].get('state') == 'PAUSED' and row['listening'].get('microphone_open') is False
         and row.get('phase') == 'IDLE' and row.get('playing') is False for row in rows),
         'latest_user_pause_required')
    state = copy.deepcopy(rows[-1])
    state.update(startup_sha256=STARTUP, board_boot_id=spec['boot_id'],
        memory=state['memory_reason']['worker'], memory_retry=state['memory_reason']['retry'])
    state['observation_window'] = {
        'samples': len(rows), 'start_mono': rows[0]['observed_mono'], 'end_mono': rows[-1]['observed_mono'],
        'elapsed_seconds': rows[-1]['observed_mono'] - rows[0]['observed_mono'],
        'completed_first_last': [rows[0]['memory_reason']['worker']['completed'], state['memory']['completed']],
        'discarded_first_last': [rows[0]['memory_reason']['worker']['discarded'], state['memory']['discarded']],
        'failure_streak_values': sorted({row['memory_reason']['retry']['failure_streak'] for row in rows}),
        'rejection_reasons': sorted({reason for row in rows for reason in row['memory_reason']['summary']['rejection_reasons']}),
        'gui_runtime_fault_maximum': max(row['runtime_faults']['count'] for row in rows),
        'visual_steps_first_last': [rows[0]['visual_timeline']['steps'], rows[-1]['visual_timeline']['steps']],
        'visual_errors_maximum': max(row['visual_timeline']['errors'] for row in rows),
        'worker_fault_metadata_available': False,
    }
    return state


def validate_display(value, spec, mapping):
    need(value.get('status') == 'XCB_READONLY_OBSERVATION_COMPLETE'
         and value.get('startup_sha256') == STARTUP and value.get('policy_left') == 'original'
         and value.get('policy_modified') is False
         and value.get('observer_reset_calls') == 0 and value.get('full_component_checks') == [380, 380]
         and value.get('observed_periodic_idle_resets') is True, 'current_original_policy_observation_required')
    owners = value.get('owners', {})
    need(all(owners.get(key) == mapping[key] for key in ('supervisor', 'gtk', 'camera'))
         and all(owners.get(key) == spec[key] for key in ('boot_id', 'startup_sha256',
             'configuration_sha256', 'source_manifest_sha256')), 'display_owner_closure_changed')
    rows = value.get('samples', [])
    need(len(rows) >= 31 and all(row.get('screen_saver') == {
        'allow_exposures': 1, 'interval': 600, 'prefer_blank': 1, 'timeout': 600}
        and row.get('dpms_enabled') is True and row.get('dpms_timeouts') == [600, 600, 600]
        and row.get('dpms_level') == 0 and row.get('enabled') is False
        and row.get('state') == 'PAUSED' and row.get('microphone_open') is False for row in rows),
        'original_600_second_policy_and_saved_pause_required')
    return value


def read_bundle(observation_path, observation_sha, display_path, display_sha):
    need(len(PINS) == 4 and seal.common.valid_sha(STARTUP), 'actual_v23_seal_pins_required')
    need(observation_sha == OBSERVATION_SHA and display_sha == DISPLAY_SHA,
         'exact_final_runtime_and_display_receipts_required')
    raws = {name: seal.common.pinned(seal.EVIDENCE / name, pin) for name, pin in PINS.items()}
    spec, ready, installed, mapping = [json.loads(raws[name]) for name in
        ('spec.json', 'ready.json', 'installed.json', 'source_mapping.json')]
    seal.validate_mapping(mapping, spec, ready, installed)
    marker = json.loads((seal.EVIDENCE / 'canonical_update_state.json').read_bytes())
    need(marker == {'phase': 'COMMITTED', 'spec_sha256': PINS['spec.json'], 'ready_sha256': PINS['ready.json']}
         and (seal.CANONICAL / 'spec.json').read_bytes() == raws['spec.json']
         and (seal.CANONICAL / 'actual_ready.json').read_bytes() == raws['ready.json'],
         'sealed_v23_must_still_be_current')
    base = seal.common.baseline()
    need(spec['startup_sha256'] == STARTUP and mapping['source_files'] == PRODUCTS
         and spec['configuration_sha256'] == base['configuration_sha256']
         and set(spec['component_sha256']) == set(base['component_sha256'])
         and {key for key in spec['component_sha256'] if spec['component_sha256'][key]
              != base['component_sha256'][key]} == set(PRODUCTS), 'only_selected_two_summary_sources_may_change')
    fixed = {name: json.loads(seal.common.pinned(REPAIR / name, pin)) for name, pin in FIXED.items()}
    restored = fixed['progress_followup_20261031/memory_v23_display_maintenance_finish_1793514589340700200.json']
    need(restored.get('status') == 'ORIGINAL_DISPLAY_POLICY_RESTORED_AFTER_MEMORY_MAINTENANCE'
         and restored.get('after') == {'dpms_enabled': True, 'dpms_level': 0,
             'dpms_timeouts': [600, 600, 600], 'screen_saver': [600, 600, 1, 1]}
         and restored.get('microphone_changed') is False, 'actual_display_maintenance_restoration_required')
    actual = fixed[VALIDATION + 'ACTUAL_CANDIDATE_R4_ALL_1793514219912878400.json']['result']
    review = fixed[VALIDATION + 'candidate_validation_r4/ASSISTANT_SEMANTIC_REVIEW.json']
    need(len(actual['cases']) == 11 and all(row['accepted'] is True and row['human_semantic_review'] == 'PENDING'
         for row in actual['cases']) and actual['actual_model_calls'] == 12
         and actual['final_summary_max_utf8_bytes'] == 301
         and review['reviewer'] == 'independent_assistant' and review['assistant_semantic_pass_count'] == 11
         and review['human_signoff'] == 'PENDING', 'bounded_public_assistant_review_required')
    observed = validate_observation(json.loads(seal.common.pinned(observation_path, observation_sha)), spec, mapping)
    display = validate_display(json.loads(seal.common.pinned(display_path, display_sha)), spec, mapping)
    inputs = [seal.EVIDENCE / name for name in PINS] + [seal.EVIDENCE / 'canonical_update_state.json']
    inputs += [REPAIR / name for name in FIXED] + [observation_path, display_path]
    return {'spec': spec, 'ready': ready, 'installed': installed, 'mapping': mapping, 'fixed': fixed,
        'observed': observed, 'display': display, 'evidence': [reference(path) for path in inputs],
        'arguments': (observation_path, observation_sha, display_path, display_sha)}


def build_plan(bundle):
    spec, ready, mapping, state = [bundle[key] for key in ('spec', 'ready', 'mapping', 'observed')]
    prior = bundle['fixed']['docs_state_v22/HANDOFF.json']
    targets = {row['key']: Path(row['path']) for row in prior['changed_documents']}
    need(len(targets) == 12 and all(path.is_relative_to(BASE) for path in targets.values()), 'exact_twelve_local_targets_required')
    need(all(reference(Path(row['path'])) == {key: row[key] for key in ('path', 'sha256', 'bytes')}
             for row in prior['changed_documents']), 'prior_document_bytes_changed')
    originals = {key: path.read_bytes() for key, path in targets.items()}
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    worker, retry, reason = state.get('memory', {}), state.get('memory_retry', {}), state.get('memory_reason', {})
    value = copy.deepcopy(bundle['fixed']['current_observation_v22.json'])
    value.update(revision='v23', status=STATUS, updated_utc=now, startup_sha256=STARTUP,
        source_manifest_sha256=spec['source_manifest_sha256'], configuration_sha256=spec['configuration_sha256'],
        source_observed_mono=mapping['observed_mono'], runtime_observed_mono=state['observed_mono'],
        phase=state['phase'], playing=state['playing'], listening=state['listening'], source_files=PRODUCTS,
        publication_ready=ready, publication_saved_listening_preference=mapping['saved_listening_preference'],
        native_visible=mapping['native_visible'], previous_current_snapshot=reference(PREVIOUS),
        evidence=bundle['evidence'], finalization_ready=True,
        public_summary_validation={'before_accepted': 3, 'after_accepted': 11, 'cases': 11,
            'actual_llm_calls': 12, 'capacity_utf8_bytes': 301, 'long_record_source_fragments': 2,
            'long_record_reduction_rounds': 0, 'assistant_semantic_passed': 11,
            'reviewers': ['root_assistant', 'independent_assistant'], 'human_signoff': 'PENDING',
            'whole_store_health_verified': False, 'original_rejected_candidates_preserved': True},
        memory={'current_runtime_available': True, 'worker': worker, 'retry': retry, 'current_diagnosis': reason,
            'counters_are_process_local': True, 'completion_counter_is_not_model_call_count': True,
            'whole_store_health_verified': False, 'multi_hour_summary_stability_verified': False,
            'summary_rejection_stability_unresolved': True, 'current_status': 'PRODUCTION_NEGATION_REJECTIONS_PERSIST',
            'original_source_retained_until_successful_validated_summary': True},
        runtime_observation_window=state['observation_window'],
        previous_display_finalization=value['display_finalization'],
        display_finalization={'reference': reference(bundle['arguments'][2]), 'observation': bundle['display'],
            'physical_panel_observed': False, 'external_input_not_excluded': True},
        next_priority='继续观察摘要任务和对话性能，后续完成真人听音及声纹标定。')
    for name in ('supervisor', 'gtk', 'camera'):
        value[name + '_pid'] = mapping[name]['pid']
        value[name + '_birth_ticks'] = mapping[name]['birth_ticks']
    for name in ('native', 'runtime_faults', 'visual_timeline', 'visual_collector', 'visual_queries',
                 'visual_social', 'speaker', 'capabilities'):
        value[name] = state.get(name)
    value['renderer_worker_faults'] = state.get('renderer_worker_faults', state.get('worker_faults', {'available': False}))
    value['worker_fault_probe_correction'] = {
        'current_metadata_available': value['renderer_worker_faults'].get('available') is True,
        'earlier_missing_field_default_zero_was_not_an_observed_zero': True,
        'worker_fault_absence_verified': value['renderer_worker_faults'].get('available') is True
            and value['renderer_worker_faults'].get('count') == 0}
    value['windows_inference_health']['revision_when_observed'] = 'v22'
    value['current_revision_acceptance'].update(actual_arm_public_synthetic_tests_passed=False,
        public_true_model_summary_cases_passed=True, public_assistant_semantic_review_passed=True)
    value['operator_instruction'] = {'publisher': str(seal.common.HERE / 'publish_summary.py'),
        'spec': reference(seal.EVIDENCE / 'spec.json'), 'sole_publisher': 'root',
        'publication_expected_listening_enabled': False,
        'usage': 'Recheck actual owners, source closure and saved listening preference before later operations.'}
    errors = reason.get('summary', {}).get('rejection_reasons', [])
    note = (
        'v23 记忆摘要修订已发布，真实数据仍有校验拒绝\n\n'
        f'运行根 {spec["target"]}。startup SHA {STARTUP}，manifest SHA {spec["source_manifest_sha256"]}，config SHA {spec["configuration_sha256"]}，380份组件。\n'
        f'本次更新两份记忆源码，378份其他组件与界面配置保持。supervisor {mapping["supervisor"]["pid"]}、GTK {mapping["gtk"]["pid"]}、原A相机 {mapping["camera"]["pid"]}。操作前现读owner。\n'
        '用户选择暂时保持暂停，enabled=false、PAUSED、mic=false，界面可见。ASR 2线程、GTCRN 1线程与原8帧队列、GTK每5秒保活继续使用。\n'
        '同一组11个公开样例经真实模型处理，机械通过由3项增至11项。第四版共12次调用，长记录分两片处理，摘要保留反复提问并消除了局部次数的范围误导。两名assistant逐条语义复核通过，原human_semantic_review仍为PENDING。容量301字节与原默认预算保持。\n'
        f'生产61样本观察至mono{state["observed_mono"]:.3f}，完成4→7、discarded计数5→9，最终连续失败{retry.get("failure_streak", "未取得")}次、退避{retry.get("last_delay_seconds", "未取得")}秒。真实数据仍在full_source_validation出现{errors}，修复继续进行。计数属于本进程，完成批数不能推作模型调用次数。\n'
        '失败批次原文在成功校验压缩前保留。61样本内GUI运行故障0、视觉steps189→369且errors0。worker故障字段未提供，早期缺失默认0的值不能证明无异常。声纹尚未标定，新真人对话和扬声器首声继续待验。\n'
        '显示维护临时设置已恢复为原600秒策略和DPMS启用。当前31点被动观察有6次idle下降，最大5012ms，观察器复位0次。外部输入未排除，物理面板未观测。历史v21的635.886秒观察独立保留。JPEG对照有人数和吞吐混杂，当前继续使用原A相机，自动迎宾保持关闭。\n'
        'v20功能与92项公开ARM证据作为历史保留。两个旧测试模块的依赖缺口、11个公共临时目录约10.3MB清理被自动审批拒绝的记录保留。前三版摘要候选及首次验证程序失败回执完整保留。\n'
        f'接续入口 {CURRENT}。本次12入口的原字节与证据在 {HERE}，历史快照独立保留。\n'
    )
    short = ('v23已发布两份记忆摘要源码并完成READY，用户仍保持暂停。公开11样例经真实模型及assistant语义复核通过，生产真实数据仍有negation_missing校验拒绝，失败批次原文保留并继续修复。\n\n'
        f'详见[当前观测]({CURRENT.as_posix()})和[接续简记]({(HERE / "current_note.txt").as_posix()})。')
    body = '\n'.join('- ' + line for line in note.strip().splitlines() if line)
    updates = {'project_AGENTS': replace_block(originals['project_AGENTS'], 'board-business-live-20261030', body),
        'project_README': replace_block(originals['project_README'], 'dialogue-current-20261031', short)}
    analysis = replace_block(originals['analysis_README'], 'current-v22-20261031', short, 'current-v23-20261031')
    analysis = replace_block(analysis, 'board-business-live-20261030', body)
    updates['analysis_README'] = replace_block(analysis, 'performance-dialogue-plan-20261031',
        f'- [性能与对话平衡优化方案]({(BASE / "语言模型分析/性能与对话平衡优化方案_20261031.txt").as_posix()})已补充v23摘要修正与待验范围。')
    old_note = (REPAIR / 'docs_state_v22/current_note.txt').read_bytes()
    for key in ('owner_continuation', 'performance_plan', 'analysis_performance_plan'):
        need(originals[key].startswith(old_note), 'previous_note_prefix_changed')
        updates[key] = note.encode() + originals[key][len(old_note):]
    observation_raw = encoded(value)
    current = {'path': str(CURRENT), 'sha256': seal.common.sha(observation_raw), 'bytes': len(observation_raw),
        'revision': 'v23', 'status': STATUS, 'startup_sha256': STARTUP, 'component_pins': 380,
        'source_manifest_sha256': spec['source_manifest_sha256'], 'configuration_sha256': spec['configuration_sha256'],
        'observations_are_not_full_acceptance': True}
    common = {key: value[key] for key in ('status', 'updated_utc', 'root', 'startup_sha256',
        'source_manifest_sha256', 'configuration_sha256', 'component_pins', 'board_boot_id',
        'supervisor_pid', 'gtk_pid', 'camera_pid', 'camera_birth_ticks', 'current_revision_acceptance',
        'operator_instruction', 'evidence', 'display_finalization', 'public_summary_validation', 'worker_fault_probe_correction',
        'windows_inference_health', 'runtime_observation_window')}
    common.update(current_revision='v23', current_observation=current, last_observed_listening_enabled=False,
        last_observed_listening_state='PAUSED', microphone_open=False, playing=False,
        physical_microphone_opened=False, physical_audio_played=False, automatic_listening_restored=False,
        latest_user_listening_choice=False, user_manual_pause_preserved=True,
        memory_retry_history=value['memory'], memory_failure_metadata=reason,
        latest_memory_runtime_counters={'process_revision': 'v23', 'boot_id': spec['boot_id'],
            'observed_mono': state['observed_mono'], 'completed': worker.get('completed'),
            'discarded': worker.get('discarded'), 'failure_streak': retry.get('failure_streak'),
            'current_runtime_available': True, 'whole_store_health_verified': False},
        last_detailed_memory_observation={'current_detailed_store_snapshot_available': False, 'runtime_only': value['memory']},
        verification_scope_notice='v23 sealed two-source summary revision and paused READY. Eleven public model cases and assistant review passed. Production negation_missing rejections persist with failed sources retained. Physical dialogue and sustained production summary stability remain open.')
    for key in ('dialogue_STATUS', 'implementation', 'production_live', 'resume_verification', 'character_switch', 'windows_coordination'):
        document = json.loads(originals[key])
        document.setdefault('continuation_history', []).append({'superseded_by_revision': 'v23',
            'previous_status': document.get('status'), 'original_bytes_archive': str(HERE / 'before' / targets[key].relative_to(BASE))})
        for item in [document] + [document[name] for name in ('production', 'production_business_live') if isinstance(document.get(name), dict)]:
            item.update(copy.deepcopy(common))
            for name in ('main_pid', 'last_verified_ui_supervisor_pid', 'last_observed_ui_supervisor_pid'):
                if name in item:
                    item[name] = mapping['supervisor']['pid']
            for name in ('last_verified_gtk_pid', 'last_observed_gtk_pid'):
                if name in item:
                    item[name] = mapping['gtk']['pid']
            if 'last_verified_pid_fields_revision' in item:
                item['last_verified_pid_fields_revision'] = 'v23_source_mapping'
            if 'listening' in item:
                item['listening'] = False
            item['verified_listening'] = {'revision': 'v23', 'startup_sha256': STARTUP,
                'state': 'PAUSED', 'enabled': False, 'continuous_capture_passed': False}
            item['response_latency'] = {'revision': 'v23', 'startup_sha256': STARTUP,
                'new_human_waiting_acceptance': False, 'audible_first_sound_measured': False, 'current_observation': current}
        if key == 'character_switch':
            document['current_pair_observation'] = 'v23 preserves original A camera and visible UI. Physical FPS and new human audio remain open.'
        if key == 'windows_coordination':
            document['updated_at'] = now
            for name in ('production_UI_switch', 'production_business_cutover'):
                document[name].update(state=STATUS, current_revision='v23', updated_utc=now,
                    startup_sha256=STARTUP, source_manifest_sha256=spec['source_manifest_sha256'],
                    component_pins=380, current_observation=current, physical_microphone_opened=False, physical_audio_played=False)
        updates[key] = encoded(document)
    return {'bundle': bundle, 'targets': targets, 'originals': originals, 'updates': updates,
        'observation': value, 'observation_raw': observation_raw, 'note': note, 'evidence': bundle['evidence']}


def apply_plan(plan):
    read_bundle(*plan['bundle']['arguments'])
    need(not HERE.exists() and not CURRENT.exists(), 'v23_snapshot_already_exists')
    need(all(path.read_bytes() == plan['originals'][key] for key, path in plan['targets'].items()), 'concurrent_document_change')
    need(all(reference(Path(row['path'])) == row for row in plan['evidence']), 'source_evidence_changed')
    HERE.mkdir()
    archives = []
    for key, path in plan['targets'].items():
        destination = HERE / 'before' / path.relative_to(BASE)
        destination.parent.mkdir(parents=True, exist_ok=True)
        seal.exact_file(destination, plan['originals'][key])
        archives.append({'key': key, 'original': reference(path), 'archive': reference(destination)})
    seal.exact_file(HERE / 'before_manifest.json', encoded({'files': archives}))
    seal.exact_file(CURRENT, plan['observation_raw'])
    seal.exact_file(HERE / 'current_note.txt', plan['note'].encode())
    for key, path in plan['targets'].items():
        path.write_bytes(plan['updates'][key])
    need(all(Path(row['archive']['path']).read_bytes() == plan['originals'][row['key']] for row in archives), 'archive_readback_mismatch')
    need(all(path.read_bytes() == plan['updates'][key] for key, path in plan['targets'].items()), 'document_readback_mismatch')
    need(all(reference(Path(row['path'])) == row for row in plan['evidence']), 'evidence_readback_mismatch')
    handoff = {'schema': 'aura.docs-state-handoff.v1', 'status': STATUS, 'revision': 'v23',
        'startup_sha256': STARTUP, 'source_manifest_sha256': plan['observation']['source_manifest_sha256'],
        'configuration_sha256': plan['observation']['configuration_sha256'], 'component_pins': 380,
        'current_observation': reference(CURRENT), 'previous_handoff': reference(PRIOR),
        'current_note': reference(HERE / 'current_note.txt'), 'before_manifest': reference(HERE / 'before_manifest.json'),
        'updater': reference(Path(__file__)), 'changed_documents': [{**reference(path), 'key': key} for key, path in plan['targets'].items()],
        'evidence': plan['evidence'], 'historical_bytes_preserved': True, 'optimization_task_complete': False,
        'device_model_or_private_database_actions': False, 'production_tools_candidates_or_runtime_receipts_modified': False}
    seal.exact_file(HERE / 'HANDOFF.json', encoded(handoff))
    seal.exact_file(HERE / 'READBACK_VERIFICATION.json', encoded({'status': 'PASS', 'changed_documents': 12,
        'original_byte_archives': 12, 'all_document_and_archive_bytes_match': True,
        'all_evidence_hashes_unchanged': True, 'current_observation': reference(CURRENT), 'handoff': reference(HERE / 'HANDOFF.json')}))
    return {'status': STATUS, 'documents_updated': 12, 'handoff': reference(HERE / 'HANDOFF.json')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('observation', 'display'):
        parser.add_argument('--' + name, required=True, type=Path)
        parser.add_argument('--' + name + '-sha256', required=True)
    parser.add_argument('--apply-local-docs', action='store_true')
    args = parser.parse_args()
    plan = build_plan(read_bundle(args.observation, args.observation_sha256, args.display, args.display_sha256))
    print(json.dumps(apply_plan(plan) if args.apply_local_docs else {
        'status': 'DRY_V23_DOC_PLAN_VALIDATED_NO_WRITES', 'documents': 12, 'startup_sha256': STARTUP, 'listening_enabled': False}))


if __name__ == '__main__':
    main()
