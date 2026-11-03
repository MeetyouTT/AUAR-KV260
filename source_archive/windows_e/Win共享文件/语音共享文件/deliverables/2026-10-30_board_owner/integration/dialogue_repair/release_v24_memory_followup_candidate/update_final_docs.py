"""Update twelve continuation entries from final v24 backlog and quiet evidence."""
import argparse
import copy
import datetime
import json
from pathlib import Path

import seal_followup as seal


REPAIR = seal.common.REPAIR
BASE = Path(r'E:\Win共享文件')
HERE = REPAIR / 'docs_state_v24_final'
CURRENT = REPAIR / 'current_observation_v24_final.json'
PRIOR = REPAIR / 'docs_state_v24/HANDOFF.json'
PREVIOUS = REPAIR / 'current_observation_v24.json'
STATUS = 'V24_READY_PAUSED_TRACKED_MEMORY_BACKLOG_CLEARED'
STARTUP = '888faff24fef9d85ad75bbe19bc34d63956820ccd3e6dd3f674cfe4525ed0863'
PINS = {
    'spec.json': '9015c45aa735035e2185b998ae68f97ddeb7bcbf5252301143a235dce2f3ffe1',
    'ready.json': 'a2f7deeb9da617fd3b602e8c6f7c48c746f786ce9ea0d1d16a206939f8ddd046',
    'installed.json': '7191e13c52f86d82ee2b8bb906b236d277a2f90ad171d8568cf9a5d5f04aa919',
    'source_mapping.json': '6fb9899571078207b7460ae71d6da52ccd211c150b7d39f54f4003e672ec21c9',
}
OBSERVATION_SHA = 'e7fbb0db441e29b3637834e1ed9d511f9c3613ec4049aaf5ab916edfdfc43cde'
DISPLAY_SHA = 'cb68f8c6d08bdac8f5808d2f130dcfefd8dfacba5e1e3975b093931a588db395'
PRODUCTS = {
    'board/runtime/board_memory_policy.py': 'd6e459f913a6c3d9827e0d90322cb9a2fb17ada87144b853dfdf02ed300f36c6',
}
VALIDATION = 'memory_negation_model_validation_v24/'
FIXED = {
    'docs_state_v24/HANDOFF.json': '5d955f41ce9d34a5a81d3fc89bf5fd3f0da7534e0368eefc5b478d6f0414f75c',
    'current_observation_v24.json': 'b029918b6c21a45a2053043275a3bb510bb999ac83cc550bfaab84788508a4cf',
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
    'progress_followup_20261031/after_v24_memory_counts_1793520568637913600.json': 'ff45e9b642e29cc2f4d10f2ecb1fada0b29895b1122cfce49f2f997cf50c85c6',
    'progress_followup_20261031/v24_retry_rate_baseline_1793520362687023400.json': '275a71c64cb014d2d257937cafb633c7894fbc98f5556861d50b25887b9a0dcf',
    'progress_followup_20261031/v24_live_observe_1793519187600802100.json': '83587740e72fe554e28142f94b187b16d9fc5075178085c5af678070227bfb21',
    'release_v25_memory_retry_candidate/OFFLINE_STATUS.json': '2fc8fba3668ff3ba9abe1c1d4adae7c53fdf5b0cef683d8e00a81eb702aebed5',
    'memory_source_cooldown_v25_candidate/HANDOFF.json': '2d959e41a2c8d8f61d4132483564a6989c5ead9ad73993f259eae171c83a25e5',

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
    need(value.get('status') == 'METADATA_RETRY_OBSERVATION_COMPLETE'
         and value.get('full_380_and_same_owners_before_after') is True
         and value.get('model_calls_by_observer') == 0 and value.get('database_write_statements') == 0
         and value.get('task_identity_or_content_exported') is False
         and value.get('error_class') == 'none' and value.get('observed_attempt_increment_total') == 0
         and value.get('observed_repeat_interval_count') == 0, 'final_read_only_quiet_window_required')
    rows = value.get('samples', [])
    need(len(rows) == 46 and rows[-1]['elapsed_seconds'] >= 90
         and all(left['elapsed_seconds'] < right['elapsed_seconds'] for left, right in zip(rows, rows[1:])),
         'ordered_final_46_sample_window_required')
    need(all(row.get('pending_failed_tasks_observed') == 0 and row.get('accepted_llm_total') == 1010
         and row.get('inference_active') is False and row.get('inference_pending') == 0
         and row.get('failure_streak') == 0 and row.get('memory_error_present') is False
         and row.get('runtime_faults') == 0 and type(row.get('native_visible')) is bool
         and row.get('visual_errors') == 0 and row.get('worker_discarded') == 68 for row in rows),
         'quiet_zero_pending_zero_errors_no_new_llm_or_discard_required')
    need(all(left['worker_completed'] <= right['worker_completed'] and left['visual_steps'] <= right['visual_steps']
         for left, right in zip(rows, rows[1:])), 'same_process_monotone_counts_required')
    need(rows[0]['native_visible'] is True and rows[-1]['native_visible'] is True,
         'first_and_final_native_visible_required')
    prior_path = REPAIR / 'progress_followup_20261031/v24_live_observe_1793519187600802100.json'
    prior = json.loads(seal.common.pinned(prior_path, FIXED[str(prior_path.relative_to(REPAIR)).replace('\\', '/')]))
    need(prior['startup_sha256'] == spec['startup_sha256'] and prior['source_mapping_sha256'] == PINS['source_mapping.json'],
         'previous_same_release_metadata_required')
    state = copy.deepcopy(prior['samples'][-1])
    last = rows[-1]
    state.update(observed_mono=None, startup_sha256=STARTUP, board_boot_id=spec['boot_id'],
        native={'visible': True, 'other_native_metrics_available_in_final_window': False},
        runtime_faults={'count': 0, 'last': None},
        visual_timeline={'steps': last['visual_steps'], 'errors': last['visual_errors'],
            'other_visual_metrics_available_in_final_window': False})
    state['memory'] = {'completed': last['worker_completed'], 'discarded': last['worker_discarded'],
        'error_present': False, 'running_field_available': False}
    state['memory_retry'] = {'failure_streak': 0, 'other_retry_fields_available': False}
    state['memory_reason'] = {'source': 'Final quiet metadata', 'worker': state['memory'],
        'retry': state['memory_retry'], 'error_present': False, 'pending_failed_tasks': 0,
        'detailed_failure_code_available': False}
    state['observation_window'] = {
        'samples': len(rows), 'elapsed_seconds': rows[-1]['elapsed_seconds'],
        'sample_span_seconds': rows[-1]['elapsed_seconds'] - rows[0]['elapsed_seconds'],
        'absolute_monotonic_timestamps_available': False,
        'full_380_and_same_owners_before_after': True,
        'completed_first_last': [rows[0]['worker_completed'], last['worker_completed']],
        'discarded_first_last': [rows[0]['worker_discarded'], last['worker_discarded']],
        'failure_streak_values': [0], 'new_rejections_observed': False,
        'gui_runtime_fault_maximum': 0,
        'visual_steps_first_last': [rows[0]['visual_steps'], last['visual_steps']],
        'visual_errors_maximum': 0, 'worker_fault_metadata_available': False,
        'pending_failed_tasks_first_last': [0, 0], 'accepted_llm_first_last': [1010, 1010],
        'inference_active_any': False, 'inference_pending_maximum': 0,
        'native_visibility_false_samples': sum(row['native_visible'] is False for row in rows),
        'native_visibility_false_elapsed_seconds': [row['elapsed_seconds'] for row in rows if row['native_visible'] is False],
        'first_and_final_native_visible': True,
        'retained_metadata_from_prior_181_window': ['listening', 'phase', 'playing', 'speaker', 'capture', 'capabilities'],
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
    prior = bundle['fixed']['docs_state_v24/HANDOFF.json']
    targets = {row['key']: Path(row['path']) for row in prior['changed_documents']}
    need(len(targets) == 12 and all(path.is_relative_to(BASE) for path in targets.values()), 'exact_twelve_local_targets_required')
    need(all(reference(Path(row['path'])) == {key: row[key] for key in ('path', 'sha256', 'bytes')}
             for row in prior['changed_documents']), 'prior_document_bytes_changed')
    originals = {key: path.read_bytes() for key, path in targets.items()}
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    worker, retry, reason = state.get('memory', {}), state.get('memory_retry', {}), state.get('memory_reason', {})
    window = state['observation_window']
    new_discarded = window['discarded_first_last'][1] - window['discarded_first_last'][0]
    value = copy.deepcopy(bundle['fixed']['current_observation_v24.json'])
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
            'summary_rejection_stability_unresolved': False, 'current_status': 'TRACKED_BACKLOG_CLEARED_FINAL_QUIET_WINDOW_PASS',
            'current_tracked_backlog_cleared': True, 'historical_rejections_preserved': True,
            'original_source_retained_until_successful_validated_summary': True},
        runtime_observation_window=state['observation_window'],
        previous_display_finalization=value['display_finalization'],
        display_finalization={'reference': reference(bundle['arguments'][2]), 'observation': bundle['display'],
            'physical_panel_observed': False, 'external_input_not_excluded': True},
        next_priority='保持现役v24与用户暂停选择，后续按现场安排完成真人听音、声纹标定与长时间稳定性验收。')
    for name in ('supervisor', 'gtk', 'camera'):
        value[name + '_pid'] = mapping[name]['pid']
        value[name + '_birth_ticks'] = mapping[name]['birth_ticks']
    for name in ('native', 'runtime_faults', 'visual_timeline', 'visual_collector', 'visual_queries',
                 'visual_social', 'speaker', 'capabilities'):
        value[name] = state.get(name)
    value['renderer_worker_faults'] = state.get('renderer_worker_faults', state.get('worker_faults', {'available': False}))
    value['memory_backlog_comparison'] = {
        'source': 'Three separately timed root read-only database count snapshots',
        'before': bundle['fixed']['progress_followup_20261031/before_v24_memory_counts_1793518294467065900.json'],
        'during_v24': bundle['fixed']['progress_followup_20261031/during_v24_memory_counts_1793519190115584800.json'],
        'after': bundle['fixed']['progress_followup_20261031/after_v24_memory_counts_1793520568637913600.json'],
        'raw_content_or_ids_exported': False, 'tracked_user_and_played_bodies_cleared': True,
        'failed_groups_with_pending_bodies_cleared': True,
        'global_summary_count_is_separate_from_final_90_second_window': True,
    }
    after = value['memory_backlog_comparison']['after']
    need(after['pending_user_said_bodies'] == after['pending_assistant_played_bodies']
         == after['failed_candidate_tasks_with_pending_bodies'] == 0
         and after['committed_summary_count'] == 2879 and after['read_only_database'] is True
         and after['raw_content_or_ids_exported'] is False, 'separate_zero_backlog_count_snapshot_required')
    retry_history = bundle['fixed']['progress_followup_20261031/v24_retry_rate_baseline_1793520362687023400.json']
    need(retry_history['full_380_and_same_owners_before_after'] is True
         and retry_history['observed_repeat_interval_count'] == 6
         and retry_history['samples'][0]['pending_failed_tasks_observed'] == 3
         and retry_history['samples'][-1]['pending_failed_tasks_observed'] == 0,
         'historical_retry_observation_required')
    value['historical_v24_retry_observation'] = retry_history
    value['offline_v25_retry_candidate'] = bundle['fixed']['release_v25_memory_retry_candidate/OFFLINE_STATUS.json']
    need(value['offline_v25_retry_candidate']['status'] == 'OFFLINE_CANDIDATE_NOT_DEPLOYED'
         and value['offline_v25_retry_candidate']['execution_enabled'] is False, 'v25_remains_offline_required')
    value['pending']['memory_rejection_stability_under_review'] = False
    value['retained_mechanical_boundary'] = {'required_state': 'FAULT/null', 'tracking_enabled': False,
        'new_actuation_test_performed': False, 'scope': 'Inherited protected release boundary'}
    value['finalization_stage'] = 'V24_TRACKED_BACKLOG_CLEARED_FINAL_QUIET_OBSERVATION'
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
    display = bundle['display']
    counts, discarded = window['completed_first_last'], window['discarded_first_last']
    visual = window['visual_steps_first_last']
    note = (
        'v24 现役保持，本次跟踪的记忆积压已清空\n\n'
        f'运行根 {spec["target"]}。startup SHA {STARTUP}，manifest SHA {spec["source_manifest_sha256"]}，config SHA {spec["configuration_sha256"]}，380份组件。\n'
        f'现役为v24的d6e摘要提示单源修订。supervisor {mapping["supervisor"]["pid"]}、GTK {mapping["gtk"]["pid"]}、原A相机 {mapping["camera"]["pid"]}。最终观察前后380组件及同owner核验通过，后续操作先现读。\n'
        '用户选择暂时保持暂停。现役READY和保存偏好为enabled=false、PAUSED、mic=false，界面可见。ASR 2线程、GTCRN 1线程与原8帧队列、GTK每5秒保活继续使用。自动迎宾关闭，机械FAULT/null和跟随关闭边界保持。\n'
        '三次独立只读计数中，待处理用户原文38→13→0、待处理已播助手原文20→12→0、仍带待处理原文的失败摘要任务33→14→0，已提交摘要2807→2826→2879。2879属于单独清空计数的时点，最终90秒窗口仅记录进程计数。\n'
        '历史181样本中的negation_missing拒绝和原文保留均真实保留。后续4分钟观察，待处理失败任务3→0，记录6次同批重试，间隔约10–54秒，LLM已接受请求累计1001→1010。随后已有积压经原校验继续处理完成。\n'
        f'最后{window["elapsed_seconds"]:.3f}秒共{window["samples"]}点，失败待处理0→0、LLM已接受计数1010→1010，推理active=false/pending=0全窗。worker completed {counts[0]}→{counts[1]}、discarded {discarded[0]}→{discarded[1]}，failure_streak=0、memory error=false，未新增拒绝。完成计数增加不等同模型调用增加。\n'
        f'最后窗口GUI运行故障0，native可见标记首末为true，其中{window["native_visibility_false_samples"]}点曾为false，发生在约2–12秒；视觉steps {visual[0]}→{visual[1]}、errors=0。worker故障字段仍未提供，早期缺失默认0的值不能证明无异常。声纹尚未标定，新真人对话、扬声器首声和多小时稳定性继续待验。\n'
        f'显示维护已恢复原600秒策略和DPMS启用。此前同v24的{len(display["samples"])}点被动观察有{display["idle_drop_count"]}次idle下降，最大{display["max_idle_ms"]}ms，观察器复位0次。外部输入未排除，物理面板未观测。历史v21的635.886秒观察独立保留。JPEG对照存在场景与吞吐混杂，继续使用原A。\n'
        '公开15样例经真实模型和两名assistant语义复核通过，最终R2有16次模型调用、0取消，原human_semantic_review仍为PENDING，容量301字节。v25冷却重试方案仅离线27项通过，未部署，gate=false且无APPROVED/实际spec。600秒冷却可能延后失败批次压缩，当前保持已清空积压的v24。\n'
        'v20功能与92项公开ARM证据按历史版本保留。两个旧测试模块依赖缺口、11个公共临时目录约10.3MB清理被自动审批拒绝的记录保留。\n'
        f'最终接续入口 {CURRENT}。本次12入口改前原字节与证据在 {HERE}，原docs_state_v24及全部中途失败记录保留。\n'
    )
    short = ('现役v24保持暂停，本次跟踪的用户原文、已播助手原文与失败摘要任务积压均已清空。最后90秒未新增已接受模型请求或拒绝，v25保持离线候选。真人听音、声纹标定与多小时稳定性待验。\n\n'
        f'详见[最终观测]({CURRENT.as_posix()})和[接续简记]({(HERE / "current_note.txt").as_posix()})。')
    body = '\n'.join('- ' + line for line in note.strip().splitlines() if line)
    updates = {'project_AGENTS': replace_block(originals['project_AGENTS'], 'board-business-live-20261030', body),
        'project_README': replace_block(originals['project_README'], 'dialogue-current-20261031', short)}
    analysis = replace_block(originals['analysis_README'], 'current-v24-20261031', short, 'current-v24-final-20261031')
    analysis = replace_block(analysis, 'board-business-live-20261030', body)
    updates['analysis_README'] = replace_block(analysis, 'performance-dialogue-plan-20261031',
        f'- [性能与对话平衡优化方案]({(BASE / "语言模型分析/性能与对话平衡优化方案_20261031.txt").as_posix()})已补充v24摘要修正与待验范围。')
    old_note = (REPAIR / 'docs_state_v24/current_note.txt').read_bytes()
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
        'windows_inference_health', 'runtime_observation_window', 'memory_backlog_comparison',
        'historical_v24_retry_observation', 'offline_v25_retry_candidate', 'retained_mechanical_boundary', 'finalization_stage')}
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
        verification_scope_notice='v24 source remains current and paused. Tracked user/played bodies and failed tasks reached zero in a separate count snapshot. Final 90-second observation had zero pending failed tasks, no accepted LLM count increase and no new discards. Historical failures are preserved. Physical dialogue and sustained stability remain open.')
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
        'status': 'DRY_V24_FINAL_DOC_PLAN_VALIDATED_NO_WRITES', 'documents': 12, 'startup_sha256': STARTUP, 'listening_enabled': False}))


if __name__ == '__main__':
    main()
