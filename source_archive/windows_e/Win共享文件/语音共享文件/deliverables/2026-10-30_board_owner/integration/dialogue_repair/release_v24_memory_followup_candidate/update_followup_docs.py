"""Update twelve local continuation entries from sealed v24 observations."""
import argparse
import copy
import datetime
import json
from pathlib import Path

import seal_followup as seal


REPAIR = seal.common.REPAIR
BASE = Path(r'E:\Win共享文件')
HERE = REPAIR / 'docs_state_v24'
CURRENT = REPAIR / 'current_observation_v24.json'
PRIOR = REPAIR / 'docs_state_v23/HANDOFF.json'
PREVIOUS = REPAIR / 'current_observation_v23.json'
STATUS = 'V24_MEMORY_PROMPT_READY_PAUSED_PRODUCTION_OBSERVATION'
STARTUP = '888faff24fef9d85ad75bbe19bc34d63956820ccd3e6dd3f674cfe4525ed0863'
PINS = {
    'spec.json': '9015c45aa735035e2185b998ae68f97ddeb7bcbf5252301143a235dce2f3ffe1',
    'ready.json': 'a2f7deeb9da617fd3b602e8c6f7c48c746f786ce9ea0d1d16a206939f8ddd046',
    'installed.json': '7191e13c52f86d82ee2b8bb906b236d277a2f90ad171d8568cf9a5d5f04aa919',
    'source_mapping.json': '6fb9899571078207b7460ae71d6da52ccd211c150b7d39f54f4003e672ec21c9',
}
OBSERVATION_SHA = '83587740e72fe554e28142f94b187b16d9fc5075178085c5af678070227bfb21'
DISPLAY_SHA = 'cb68f8c6d08bdac8f5808d2f130dcfefd8dfacba5e1e3975b093931a588db395'
PRODUCTS = {
    'board/runtime/board_memory_policy.py': 'd6e459f913a6c3d9827e0d90322cb9a2fb17ada87144b853dfdf02ed300f36c6',
}
VALIDATION = 'memory_negation_model_validation_v24/'
FIXED = {
    'docs_state_v23/HANDOFF.json': 'c4b58840b1908fe8fdb45192edf06b34850b2a1da770389981b5d78111f26d5d',
    'current_observation_v23.json': '869ce976872681ea0eeadfe6756adc4c9accfc69e8cab3dd2d26232cfe233b35',
    VALIDATION + 'ACTUAL_BEFORE_ALL_1793517473207779600.json': '5808159329d0b0a90d9cc0eb4c246a0a14f85f4ce547d6cc1d38f7be95a58f8d',
    VALIDATION + 'ACTUAL_CANDIDATE_ALL_1793517584698901600.json': '522a5c3b9e0a63be3b1ecfbc5daf7236ff4187e67aabd5ea8b48a46a2bf15d7f',
    VALIDATION + 'ACTUAL_CANDIDATE_R2_ALL_1793518296885058600.json': 'b0b42b950a2bd598c87f1760a55cfff45a9c2b57201c4093c38e2170e67c0365',
    VALIDATION + 'independent_semantic_review_r2/ALL_ASSISTANT_REVIEW.json': 'ca8bc51aa20fbdbdeff4ae010bdfee8d78f0e82cd4623ef1e0e450a4d7c1fc35',
    VALIDATION + 'ROOT_ADOPTION_R2_DECISION.json': 'b893ee9688ea021b446941e7dcf862dc280225e0b032a16567ce9b678c160b01',
    'progress_followup_20261031/memory_v24_display_maintenance_finish_1793518958720137300.json': 'a0fe6db03e425c83c7b17c5781bd3c24c453da33da1896d1e645aacc20bae996',
    'performance_review_newboot/failed_summary_ab_v24/actual_pair_1793517245658076600.json': '34162335c69b8c5eb799dcc9ef876728ec63f725c8c17607169d98fb6dfe444c',
    'performance_review_newboot/v24_public_and_publisher_review/FINAL_FREEZE_REVIEW.json': '0343d1433e0671f2c268744df76a778e6882bfa014055ceb178f33946f944237',
    'progress_followup_20261031/before_v24_memory_counts_1793518294467065900.json': 'c1e6155b1673384bfbb0d43e0fb32a9ee80a157827b16fc1c495119f78391f4e',
    'progress_followup_20261031/during_v24_memory_counts_1793519190115584800.json': '95d9ede0d0850c7dd27772ac92b00b0d5cd27186c2a5ec4a6121b0289053824e',
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
    need(value.get('status') == 'V24_PAUSED_METADATA_OBSERVATION_COMPLETE'
         and value.get('startup_sha256') == STARTUP and value.get('boot_id') == spec['boot_id']
         and value.get('source_mapping_sha256') == PINS['source_mapping.json'],
         'actual_post_seal_v24_snapshot_required')
    rows = value.get('samples', [])
    need(len(rows) == 181 and all(type(row.get('observed_mono')) in (int, float) for row in rows)
         and mapping['observed_mono'] <= rows[0]['observed_mono']
         and all(left['observed_mono'] < right['observed_mono'] for left, right in zip(rows, rows[1:])),
         'ordered_post_seal_181_sample_window_required')
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
    need(len(PINS) == 4 and seal.common.valid_sha(STARTUP), 'actual_v24_seal_pins_required')
    need(seal.common.valid_sha(OBSERVATION_SHA) and observation_sha == OBSERVATION_SHA and display_sha == DISPLAY_SHA,
         'exact_final_runtime_and_display_receipts_required')
    raws = {name: seal.common.pinned(seal.EVIDENCE / name, pin) for name, pin in PINS.items()}
    spec, ready, installed, mapping = [json.loads(raws[name]) for name in
        ('spec.json', 'ready.json', 'installed.json', 'source_mapping.json')]
    seal.validate_mapping(mapping, spec, ready, installed)
    marker = json.loads((seal.EVIDENCE / 'canonical_update_state.json').read_bytes())
    need(marker == {'phase': 'COMMITTED', 'spec_sha256': PINS['spec.json'], 'ready_sha256': PINS['ready.json']}
         and (seal.CANONICAL / 'spec.json').read_bytes() == raws['spec.json']
         and (seal.CANONICAL / 'actual_ready.json').read_bytes() == raws['ready.json'],
         'sealed_v24_must_still_be_current')
    base = seal.common.baseline()
    need(spec['startup_sha256'] == STARTUP and mapping['source_files'] == PRODUCTS
         and spec['configuration_sha256'] == base['configuration_sha256']
         and set(spec['component_sha256']) == set(base['component_sha256'])
         and {key for key in spec['component_sha256'] if spec['component_sha256'][key]
              != base['component_sha256'][key]} == set(PRODUCTS), 'only_selected_policy_messages_source_may_change')
    fixed = {name: json.loads(seal.common.pinned(REPAIR / name, pin)) for name, pin in FIXED.items()}
    restored = fixed['progress_followup_20261031/memory_v24_display_maintenance_finish_1793518958720137300.json']
    need(restored.get('status') == 'ORIGINAL_DISPLAY_POLICY_RESTORED_AFTER_MEMORY_MAINTENANCE'
         and restored.get('after') == {'dpms_enabled': True, 'dpms_level': 0,
             'dpms_timeouts': [600, 600, 600], 'screen_saver': [600, 600, 1, 1]}
         and restored.get('microphone_changed') is False, 'actual_display_maintenance_restoration_required')
    actual = fixed[VALIDATION + 'ACTUAL_CANDIDATE_R2_ALL_1793518296885058600.json']['result']
    review = fixed[VALIDATION + 'independent_semantic_review_r2/ALL_ASSISTANT_REVIEW.json']
    decision = fixed[VALIDATION + 'ROOT_ADOPTION_R2_DECISION.json']
    count_snapshots = [fixed['progress_followup_20261031/' + name] for name in (
        'before_v24_memory_counts_1793518294467065900.json',
        'during_v24_memory_counts_1793519190115584800.json')]
    need(all(row.get('read_only_database') is True and row.get('raw_content_or_ids_exported') is False
             for row in count_snapshots), 'root_read_only_count_metadata_required')
    need(len(actual['cases']) == 15 and all(row['accepted'] is True and row['human_semantic_review'] == 'PENDING'
         for row in actual['cases']) and actual['actual_model_calls'] == 16 and actual['cancel_calls'] == 0
         and actual['final_summary_max_utf8_bytes'] == 301
         and review['review_kind'] == 'independent_semantic_review_public_actual_v24_r2'
         and review['assessment']['assistant_semantic_pass'] == 15
         and review['human_review_status'] == 'PENDING_IN_ORIGINAL_RESULTS'
         and review['human_review_fields_modified'] is False
         and decision['reviewer'] == 'root_assistant'
         and decision['selected_sources'][seal.common.POLICY_RELATIVE]['sha256'] == PRODUCTS[seal.common.POLICY_RELATIVE],
         'bounded_public_assistant_review_required')
    observed = validate_observation(json.loads(seal.common.pinned(observation_path, observation_sha)), spec, mapping)
    display = validate_display(json.loads(seal.common.pinned(display_path, display_sha)), spec, mapping)
    inputs = [seal.EVIDENCE / name for name in PINS] + [seal.EVIDENCE / 'canonical_update_state.json']
    inputs += [REPAIR / name for name in FIXED] + [observation_path, display_path]
    return {'spec': spec, 'ready': ready, 'installed': installed, 'mapping': mapping, 'fixed': fixed,
        'observed': observed, 'display': display, 'evidence': [reference(path) for path in inputs],
        'arguments': (observation_path, observation_sha, display_path, display_sha)}


def build_plan(bundle):
    spec, ready, mapping, state = [bundle[key] for key in ('spec', 'ready', 'mapping', 'observed')]
    prior = bundle['fixed']['docs_state_v23/HANDOFF.json']
    targets = {row['key']: Path(row['path']) for row in prior['changed_documents']}
    need(len(targets) == 12 and all(path.is_relative_to(BASE) for path in targets.values()), 'exact_twelve_local_targets_required')
    need(all(reference(Path(row['path'])) == {key: row[key] for key in ('path', 'sha256', 'bytes')}
             for row in prior['changed_documents']), 'prior_document_bytes_changed')
    originals = {key: path.read_bytes() for key, path in targets.items()}
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    worker, retry, reason = state.get('memory', {}), state.get('memory_retry', {}), state.get('memory_reason', {})
    window = state['observation_window']
    new_discarded = window['discarded_first_last'][1] - window['discarded_first_last'][0]
    value = copy.deepcopy(bundle['fixed']['current_observation_v23.json'])
    value.update(revision='v24', status=STATUS, updated_utc=now, startup_sha256=STARTUP,
        source_manifest_sha256=spec['source_manifest_sha256'], configuration_sha256=spec['configuration_sha256'],
        source_observed_mono=mapping['observed_mono'], runtime_observed_mono=state['observed_mono'],
        phase=state['phase'], playing=state['playing'], listening=state['listening'], source_files=PRODUCTS,
        publication_ready=ready, publication_saved_listening_preference=mapping['saved_listening_preference'],
        native_visible=mapping['native_visible'], previous_current_snapshot=reference(PREVIOUS),
        evidence=bundle['evidence'], finalization_ready=True,
        public_summary_validation={'before_accepted': 11, 'after_accepted': 15, 'cases': 15,
            'actual_llm_calls': 16, 'capacity_utf8_bytes': 301, 'long_record_source_fragments': 2,
            'long_record_reduction_rounds': 0, 'assistant_semantic_passed': 15,
            'reviewers': ['root_assistant', 'independent_assistant'], 'human_signoff': 'PENDING',
            'whole_store_health_verified': False, 'original_rejected_candidates_preserved': True},
        memory={'current_runtime_available': True, 'worker': worker, 'retry': retry, 'current_diagnosis': reason,
            'counters_are_process_local': True, 'completion_counter_is_not_model_call_count': True,
            'whole_store_health_verified': False, 'multi_hour_summary_stability_verified': False,
            'summary_rejection_stability_unresolved': True, 'current_status': 'PRODUCTION_REJECTIONS_OBSERVED' if new_discarded else 'NO_NEW_REJECTIONS_IN_SHORT_WINDOW',
            'original_source_retained_until_successful_validated_summary': True},
        runtime_observation_window=state['observation_window'],
        previous_display_finalization=value['display_finalization'],
        display_finalization={'reference': reference(bundle['arguments'][2]), 'observation': bundle['display'],
            'physical_panel_observed': False, 'external_input_not_excluded': True},
        next_priority='继续定位真实数据摘要的否定信息丢失，保持校验与失败原文保留，后续完成真人听音及声纹标定。')
    for name in ('supervisor', 'gtk', 'camera'):
        value[name + '_pid'] = mapping[name]['pid']
        value[name + '_birth_ticks'] = mapping[name]['birth_ticks']
    for name in ('native', 'runtime_faults', 'visual_timeline', 'visual_collector', 'visual_queries',
                 'visual_social', 'speaker', 'capabilities'):
        value[name] = state.get(name)
    value['renderer_worker_faults'] = state.get('renderer_worker_faults', state.get('worker_faults', {'available': False}))
    value['memory_backlog_comparison'] = {
        'source': 'Two root read-only database count snapshots, separate from the 181-sample runtime window',
        'before': bundle['fixed']['progress_followup_20261031/before_v24_memory_counts_1793518294467065900.json'],
        'during_v24': bundle['fixed']['progress_followup_20261031/during_v24_memory_counts_1793519190115584800.json'],
        'raw_content_or_ids_exported': False,
        'all_pending_bodies_cleared': False,
        'failed_groups_cleared': False,
    }
    value['worker_fault_probe_correction'] = {
        'current_metadata_available': value['renderer_worker_faults'].get('available') is True,
        'earlier_missing_field_default_zero_was_not_an_observed_zero': True,
        'worker_fault_absence_verified': value['renderer_worker_faults'].get('available') is True
            and value['renderer_worker_faults'].get('count') == 0}
    value['windows_inference_health']['revision_when_observed'] = 'v22'
    value['current_revision_acceptance'].update(actual_arm_public_synthetic_tests_passed=False,
        public_true_model_summary_cases_passed=True, public_assistant_semantic_review_passed=True)
    value['operator_instruction'] = {'publisher': str(seal.common.HERE / 'publish_followup.py'),
        'spec': reference(seal.EVIDENCE / 'spec.json'), 'sole_publisher': 'root',
        'publication_expected_listening_enabled': False,
        'usage': 'Recheck actual owners, source closure and saved listening preference before later operations.'}
    errors = window['rejection_reasons']
    display = bundle['display']
    counts = window['completed_first_last']
    discarded = window['discarded_first_last']
    visual = window['visual_steps_first_last']
    current_memory = ('本观察窗口内仍有拒绝，原因枚举为' + repr(errors)) if new_discarded else '本观察窗口内无新增discarded'
    note = (
        'v24 记忆提示单源修订已发布，真实数据仍有校验拒绝\n\n'
        f'运行根 {spec["target"]}。startup SHA {STARTUP}，manifest SHA {spec["source_manifest_sha256"]}，config SHA {spec["configuration_sha256"]}，380份组件。\n'
        f'本次只更新摘要提示方法所在的一份policy源码，其余379组件和界面配置通过核验。supervisor {mapping["supervisor"]["pid"]}、GTK {mapping["gtk"]["pid"]}、原A相机 {mapping["camera"]["pid"]}。操作前现读owner。\n'
        '用户选择暂时保持暂停，enabled=false、PAUSED、mic=false，界面可见。ASR 2线程、GTCRN 1线程与原8帧队列、GTK每5秒保活继续使用。\n'
        '同一组15个公开样例经真实模型处理，机械通过由11项增至15项。最终R2共16次调用、0取消，两名assistant语义复核通过，原human_semantic_review仍为PENDING。长记录两片覆盖全部64遍问句并保持提问性质，容量301字节和原默认预算保持。\n'
        f'生产{window["samples"]}样本观察{window["elapsed_seconds"]:.3f}秒至mono{state["observed_mono"]:.3f}，completed {counts[0]}→{counts[1]}、discarded {discarded[0]}→{discarded[1]}，最终连续失败{retry.get("failure_streak", "未取得")}次、退避{retry.get("last_delay_seconds", "未取得")}秒。{current_memory}。计数属于本进程，完成批数不能推作模型调用次数，长期稳定性仍待验证。\n'
        '两次只读库计数中，待处理用户原文38→13、待处理已播助手原文20→12、仍带待处理原文的失败摘要任务33→14，已提交摘要2807→2826。积压已有减少，剩余失败任务继续处理。此范围与181样本进程计数分别记录。\n'
        f'失败批次原文在成功校验压缩前保留。窗口内GUI运行故障最大{window["gui_runtime_fault_maximum"]}，视觉steps {visual[0]}→{visual[1]}、errors最大{window["visual_errors_maximum"]}。worker故障字段未提供，早期缺失默认0的值不能证明无异常。声纹尚未标定，新真人对话和扬声器首声继续待验。\n'
        f'显示维护已恢复原600秒策略和DPMS启用。当前{len(display["samples"])}点被动观察有{display["idle_drop_count"]}次idle下降，最大{display["max_idle_ms"]}ms，观察器复位0次。外部输入未排除，物理面板未观测。历史v21的635.886秒观察独立保留。JPEG对照有人数和吞吐混杂，当前继续使用原A相机，自动迎宾保持关闭。\n'
        '同RAM A/B支持证据来自前一版80de提示，原提示拒绝、新提示通过，耗时5.703/6.347秒。最终d6e使用公开15例验证，未单独复测该私有样例。各失败候选与原回执保留。\n'
        'v20功能与92项公开ARM证据作为历史保留。两个旧测试模块的依赖缺口、11个公共临时目录约10.3MB清理被自动审批拒绝的记录保留。\n'
        f'接续入口 {CURRENT}。本次12入口的原字节与证据在 {HERE}，历史快照独立保留。\n'
    )
    short = ('v24已发布摘要提示单源修订并完成READY，用户仍保持暂停。公开15样例经真实模型及assistant语义复核通过，生产真实数据仍有negation_missing校验拒绝，失败批次原文保留并继续修复。\n\n'
        f'详见[当前观测]({CURRENT.as_posix()})和[接续简记]({(HERE / "current_note.txt").as_posix()})。')
    body = '\n'.join('- ' + line for line in note.strip().splitlines() if line)
    updates = {'project_AGENTS': replace_block(originals['project_AGENTS'], 'board-business-live-20261030', body),
        'project_README': replace_block(originals['project_README'], 'dialogue-current-20261031', short)}
    analysis = replace_block(originals['analysis_README'], 'current-v23-20261031', short, 'current-v24-20261031')
    analysis = replace_block(analysis, 'board-business-live-20261030', body)
    updates['analysis_README'] = replace_block(analysis, 'performance-dialogue-plan-20261031',
        f'- [性能与对话平衡优化方案]({(BASE / "语言模型分析/性能与对话平衡优化方案_20261031.txt").as_posix()})已补充v24摘要修正与待验范围。')
    old_note = (REPAIR / 'docs_state_v23/current_note.txt').read_bytes()
    for key in ('owner_continuation', 'performance_plan', 'analysis_performance_plan'):
        need(originals[key].startswith(old_note), 'previous_note_prefix_changed')
        updates[key] = note.encode() + originals[key][len(old_note):]
    observation_raw = encoded(value)
    current = {'path': str(CURRENT), 'sha256': seal.common.sha(observation_raw), 'bytes': len(observation_raw),
        'revision': 'v24', 'status': STATUS, 'startup_sha256': STARTUP, 'component_pins': 380,
        'source_manifest_sha256': spec['source_manifest_sha256'], 'configuration_sha256': spec['configuration_sha256'],
        'observations_are_not_full_acceptance': True}
    common = {key: value[key] for key in ('status', 'updated_utc', 'root', 'startup_sha256',
        'source_manifest_sha256', 'configuration_sha256', 'component_pins', 'board_boot_id',
        'supervisor_pid', 'gtk_pid', 'camera_pid', 'camera_birth_ticks', 'current_revision_acceptance',
        'operator_instruction', 'evidence', 'display_finalization', 'public_summary_validation', 'worker_fault_probe_correction',
        'windows_inference_health', 'runtime_observation_window', 'memory_backlog_comparison')}
    common.update(current_revision='v24', current_observation=current, last_observed_listening_enabled=False,
        last_observed_listening_state='PAUSED', microphone_open=False, playing=False,
        physical_microphone_opened=False, physical_audio_played=False, automatic_listening_restored=False,
        latest_user_listening_choice=False, user_manual_pause_preserved=True,
        memory_retry_history=value['memory'], memory_failure_metadata=reason,
        latest_memory_runtime_counters={'process_revision': 'v24', 'boot_id': spec['boot_id'],
            'observed_mono': state['observed_mono'], 'completed': worker.get('completed'),
            'discarded': worker.get('discarded'), 'failure_streak': retry.get('failure_streak'),
            'current_runtime_available': True, 'whole_store_health_verified': False},
        last_detailed_memory_observation={'current_detailed_store_snapshot_available': False, 'runtime_only': value['memory']},
        verification_scope_notice='v24 sealed one-policy messages revision and paused READY. Fifteen public model cases and assistant review passed. Current process counters and rejection reasons are from the post-seal observation only. Failed sources remain until successful validated compaction. Physical dialogue and sustained production stability remain open.')
    for key in ('dialogue_STATUS', 'implementation', 'production_live', 'resume_verification', 'character_switch', 'windows_coordination'):
        document = json.loads(originals[key])
        document.setdefault('continuation_history', []).append({'superseded_by_revision': 'v24',
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
                item['last_verified_pid_fields_revision'] = 'v24_source_mapping'
            if 'listening' in item:
                item['listening'] = False
            item['verified_listening'] = {'revision': 'v24', 'startup_sha256': STARTUP,
                'state': 'PAUSED', 'enabled': False, 'continuous_capture_passed': False}
            item['response_latency'] = {'revision': 'v24', 'startup_sha256': STARTUP,
                'new_human_waiting_acceptance': False, 'audible_first_sound_measured': False, 'current_observation': current}
        if key == 'character_switch':
            document['current_pair_observation'] = 'v24 preserves original A camera and visible UI. Physical FPS and new human audio remain open.'
        if key == 'windows_coordination':
            document['updated_at'] = now
            for name in ('production_UI_switch', 'production_business_cutover'):
                document[name].update(state=STATUS, current_revision='v24', updated_utc=now,
                    startup_sha256=STARTUP, source_manifest_sha256=spec['source_manifest_sha256'],
                    component_pins=380, current_observation=current, physical_microphone_opened=False, physical_audio_played=False)
        updates[key] = encoded(document)
    return {'bundle': bundle, 'targets': targets, 'originals': originals, 'updates': updates,
        'observation': value, 'observation_raw': observation_raw, 'note': note, 'evidence': bundle['evidence']}


def apply_plan(plan):
    read_bundle(*plan['bundle']['arguments'])
    need(not HERE.exists() and not CURRENT.exists(), 'v24_snapshot_already_exists')
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
    handoff = {'schema': 'aura.docs-state-handoff.v1', 'status': STATUS, 'revision': 'v24',
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
        'status': 'DRY_V24_DOC_PLAN_VALIDATED_NO_WRITES', 'documents': 12, 'startup_sha256': STARTUP, 'listening_enabled': False}))


if __name__ == '__main__':
    main()
