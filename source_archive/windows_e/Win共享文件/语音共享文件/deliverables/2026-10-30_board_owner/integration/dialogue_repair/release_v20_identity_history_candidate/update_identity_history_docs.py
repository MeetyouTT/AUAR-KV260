"""Read-only v20 document planning until root has sealed the actual release.

An optional pinned observation supplies the later listening/runtime state.
--apply-local-docs writes the twelve continuation pointers after all checks.
"""
import argparse
import copy
import datetime
import json
from pathlib import Path

import seal_stability as seal


BASE = Path(r'E:\Win共享文件')
REPAIR = seal.common.REPAIR
HERE = REPAIR / 'docs_state_v20'
REVISION = 'v20'
STATUS = 'V20_IDENTITY_HISTORY_READY_PHYSICAL_AND_MEMORY_VALIDATION_OPEN'
EXPECTED_STARTUP = 'd24b0d0007e2aa2b417f459891c7f39f168502a58374334ceab69e31af5881dd'
PRIOR = REPAIR / 'docs_state_v19/HANDOFF.json'
ARM_PATH = REPAIR / 'feature_trigger_collaboration/joint_m03_identity_arm_v2/ACTUAL_ARM_ROOT_1793502073822897400.json'
VOICE_PATH = REPAIR / 'voice_visual_timeline_review_v90/HANDOFF.json'
COLD_LEFTOVERS = REPAIR / 'cold_boot_recovery_candidate/LOCAL_TEMP_LEFTOVERS.json'
MEMORY_LEFTOVERS = REPAIR / 'memory_negation_stability/INITIAL_FIXTURE_LEFTOVERS.json'
DEFAULT_OBSERVATION = REPAIR / 'progress_followup_20261031/v20_features_live_1793502556510434800.json'
DEFAULT_OBSERVATION_SHA = 'a92208f7df7b9af517a29a6a154869f1650b1951bddf9977b95d5039c8baa11a'


def load(path):
    return json.loads(path.read_bytes())


def reference(path):
    raw = path.read_bytes()
    return {'path': str(path), 'sha256': seal.common.sha(raw), 'bytes': len(raw)}


def require_committed(raws, marker, current):
    if (marker.get('phase') != 'COMMITTED'
            or marker.get('spec_sha256') != seal.common.sha(raws['spec.json'])
            or marker.get('ready_sha256') != seal.common.sha(raws['ready.json'])
            or current['spec.json'] != raws['spec.json']
            or current['actual_ready.json'] != raws['ready.json']):
        raise ValueError('committed_v20_seal_must_still_be_current')


def validate_observation(value, spec):
    if value.get('startup_sha256') != EXPECTED_STARTUP or value.get('board_boot_id') != spec['boot_id']:
        raise ValueError('observation_must_match_current_v20_boot_and_sources')
    listening = value.get('listening', {})
    if (type(listening.get('enabled')) is not bool or type(listening.get('microphone_open')) is not bool
            or not isinstance(listening.get('state'), str) or not listening['state']
            or type(value.get('observed_mono')) not in (int, float)):
        raise ValueError('explicit_observed_listening_metadata_required')
    if listening['enabled'] is not False or listening['microphone_open'] is not False or listening['state'] != 'PAUSED':
        raise ValueError('latest_user_explicit_pause_must_be_preserved')
    return value


def read_bundle(observation_path=DEFAULT_OBSERVATION, observation_sha=DEFAULT_OBSERVATION_SHA):
    raws = {name: (seal.EVIDENCE / name).read_bytes() for name in ('spec.json', 'ready.json', 'installed.json')}
    spec, ready, installed = [json.loads(raws[name]) for name in ('spec.json', 'ready.json', 'installed.json')]
    products = seal.validate_inputs(spec, ready, installed)
    if spec['startup_sha256'] != EXPECTED_STARTUP or spec['component_pins'] != 380 or len(products) != 6:
        raise ValueError('exact_six_source_v20_seal_required')
    mapping = load(seal.EVIDENCE / 'source_mapping.json')
    seal.validate_mapping(mapping, spec, ready, products)
    marker = load(seal.EVIDENCE / 'canonical_update_state.json')
    current = {name: (seal.CANONICAL / name).read_bytes() for name in ('spec.json', 'actual_ready.json')}
    require_committed(raws, marker, current)
    observed = None
    if observation_path is not None:
        observed = validate_observation(json.loads(seal.common.pinned(observation_path, observation_sha)), spec)
        if observed['observed_mono'] < mapping['observed_mono']:
            raise ValueError('later_runtime_observation_required')
    arm = load(ARM_PATH)
    result = arm['result']
    if (arm['process_exit_code'] != 0 or arm['stderr'] != '' or result['status'] != 'PASS'
            or result['tests'] != 92 or result['failures'] != 0 or result['errors'] != 0
            or result['temporary_stores_removed'] is not True or result['new_threads_remaining'] != 0):
        raise ValueError('actual_public_arm_result_required')
    return {'raws': raws, 'spec': spec, 'ready': ready, 'mapping': mapping,
            'observed': observed, 'observation_path': observation_path, 'arm': arm}


def cleanup_inventory():
    cold, memory = load(COLD_LEFTOVERS), load(MEMORY_LEFTOVERS)
    cold_bytes = sum(item['bytes'] for directory in cold['directories'] for item in directory['entries']
                     if item['kind'] == 'regular_file')
    total = cold_bytes + sum(item['bytes'] for item in memory)
    assert len(cold['directories']) == 5 and len(memory) == 6 and total == 10316348
    return {'cold_boot_directories': 5, 'memory_directories': 6, 'total_directories': 11,
            'regular_file_bytes': total, 'status': 'AUTOMATIC_APPROVAL_BLOCKED_RETRIES_STOPPED',
            'scope': 'Public synthetic temporary test files',
            'references': [reference(COLD_LEFTOVERS), reference(MEMORY_LEFTOVERS)]}


def replace_block(raw, marker, body, new_marker=None):
    first = ('<!-- ' + marker + ' -->').encode()
    last = ('<!-- /' + marker + ' -->').encode()
    start = raw.index(first)
    end = raw.index(last, start) + len(last)
    marker = new_marker or marker
    replacement = ('<!-- ' + marker + ' -->\n' + body + '\n<!-- /' + marker + ' -->').encode('utf-8')
    return raw[:start] + replacement + raw[end:]


def build_plan(bundle):
    spec, ready, mapping = [bundle[key] for key in ('spec', 'ready', 'mapping')]
    observed = bundle['observed']
    state = observed or {'observed_mono': mapping['observed_mono'], 'phase': mapping['phase'],
                        'playing': mapping['playing'], 'listening': mapping['listening']}
    listening = state['listening']
    prior = load(PRIOR)
    targets = {row['key']: Path(row['path']) for row in prior['changed_documents']}
    assert len(targets) == 12 and all(path.is_relative_to(BASE) for path in targets.values())
    originals = {key: path.read_bytes() for key, path in targets.items()}
    previous_path = REPAIR / 'current_observation_v19.json'
    previous = load(previous_path)
    voice = load(VOICE_PATH)
    cleanup = cleanup_inventory()
    inputs = [seal.EVIDENCE / name for name in ('spec.json', 'ready.json', 'installed.json', 'source_mapping.json', 'canonical_update_state.json')]
    inputs += [ARM_PATH, VOICE_PATH, COLD_LEFTOVERS, MEMORY_LEFTOVERS, PRIOR, previous_path]
    if bundle['observation_path'] is not None:
        inputs.append(bundle['observation_path'])
    evidence = [reference(path) for path in inputs]
    memory = {'current_runtime_available': observed is not None and 'memory' in observed,
        'observed_mono': state['observed_mono'], 'worker': state.get('memory'),
        'retry': state.get('memory_retry'), 'counters_are_process_local': True,
        'specific_failure_reason_available': False, 'whole_store_health_verified': False,
        'summary_rejection_stability_unresolved': True}
    acceptance = dict(source_and_service_verified=True, installation_ready_verified=True,
        date_deletion_deployed=True, identity_cooperation_deployed=True,
        speaker_evidence_retry_and_transaction_guard_deployed=True,
        actual_arm_public_synthetic_tests_passed=True, full_physical_dialogue_acceptance=False,
        physical_audio_acceptance_passed=False, continuous_capture_passed=False,
        controls_verified=False, multi_hour_stability_verified=False, audible_first_sound_measured=False)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    operator = {'publisher': str(seal.HERE / 'publish_stability.py'),
        'spec': reference(seal.EVIDENCE / 'spec.json'), 'sole_publisher': 'root',
        'publication_expected_listening_enabled': spec['expected_final_listening_enabled'],
        'usage': 'Recheck current owners and the latest saved listening choice before any later publication.'}
    observation = {
        'schema': 'aura.current-document-observation.v1', 'revision': REVISION, 'status': STATUS,
        'updated_utc': now, 'root': spec['target'], 'startup_sha256': spec['startup_sha256'],
        'source_manifest_sha256': spec['source_manifest_sha256'], 'configuration_sha256': spec['configuration_sha256'],
        'component_pins': 380, 'board_boot_id': spec['boot_id'],
        'native_library_sha256': spec['native_library_sha256'],
        'character_pair_selection_sha256': spec['character_pair_selection_sha256'],
        'source_observed_mono': mapping['observed_mono'], 'runtime_observed_mono': state['observed_mono'],
        'supervisor_pid': mapping['supervisor']['pid'], 'supervisor_birth_ticks': mapping['supervisor']['birth_ticks'],
        'gtk_pid': mapping['gtk']['pid'], 'gtk_birth_ticks': mapping['gtk']['birth_ticks'],
        'camera_pid': mapping['camera']['pid'], 'camera_birth_ticks': mapping['camera']['birth_ticks'],
        'phase': state['phase'], 'playing': state['playing'], 'listening': listening,
        'publication_ready': ready, 'publication_saved_listening_preference': mapping['saved_listening_preference'],
        'later_runtime_observation_supplied': observed is not None, 'native_visible': mapping['native_visible'],
        'runtime_faults': state.get('runtime_faults'),
        'renderer_worker_faults': state.get('renderer_worker_faults', state.get('worker_faults')),
        'visual_timeline': state.get('visual_timeline'), 'visual_collector': state.get('visual_collector'),
        'visual_queries': state.get('visual_queries'), 'visual_social': state.get('visual_social'),
        'speaker': state.get('speaker'), 'capabilities': state.get('capabilities'),
        'latest_user_listening_instruction': '暂时保持暂停',
        'next_priority': '用户要求部署后优先继续性能优化，先进行公开ASR与音频前端线程对照。',
        'frontend_options': previous['frontend_options'], 'windows_model_owner': previous['windows_model_owner'],
        'source_files': mapping['source_files'], 'current_revision_acceptance': acceptance,
        'memory': memory, 'arm_public_validation': {'reference': reference(ARM_PATH),
            'tests': 92, 'failures': 0, 'errors': 0, 'exit_code': 0,
            'temporary_stores_removed': True, 'new_threads_remaining': 0,
            'limits': bundle['arm']['result']['limits']},
        'legacy_collection_gap': voice['collection_gap'], 'public_test_cleanup': cleanup,
        'operator_instruction': operator, 'previous_current_snapshot': reference(previous_path),
        'historical_user_feedback': previous['historical_user_feedback'],
        'pending': {'m03_date_delete_deployed': True, 'speaker_calibrated': False,
            'automatic_profile_access': False, 'new_human_audio_acceptance': False,
            'memory_rejection_stability_under_review': True,
            'completed_link_natural_unlink_relink_complete': False,
            'standalone_identity_unified_naming_complete': False,
            'new_multicomponent_motion_deployed': False, 'target_24fps_deployed': False},
        'current_live_state_claimed': False, 'evidence': evidence,
    }
    canonical = REPAIR / 'current_observation_v20.json'
    observation_raw = seal.common.encoded(observation)
    current = {'path': str(canonical), 'sha256': seal.common.sha(observation_raw), 'bytes': len(observation_raw),
        'revision': REVISION, 'status': STATUS, 'startup_sha256': spec['startup_sha256'],
        'source_manifest_sha256': spec['source_manifest_sha256'], 'configuration_sha256': spec['configuration_sha256'],
        'component_pins': 380, 'observations_are_not_full_acceptance': True}
    listening_line = ('末次状态来自后续运行观测' if observed is not None else '末次状态来自发布封存回执')
    listening_line += f'，enabled={str(listening["enabled"]).lower()}、{listening["state"]}、mic={str(listening["microphone_open"]).lower()}。'
    diagnostic_line = '当前采用发布封存状态，运行计数另行采集。'
    if observed is not None:
        timeline = state.get('visual_timeline', {})
        collector = state.get('visual_collector', {})
        speaker = state.get('speaker', {})
        worker = state.get('memory', {})
        retry = state.get('memory_retry', {})
        worker_faults = state.get('renderer_worker_faults', state.get('worker_faults', {}))
        diagnostic_line = (
            f'运行快照mono{state["observed_mono"]:.3f}记录GUI故障{state.get("runtime_faults", {}).get("count", "未取得")}、worker故障{worker_faults.get("count", "未取得")}，'
            f'视觉steps{timeline.get("steps", "未取得")}、accepted{collector.get("accepted_frames", "未取得")}、'
            f'inflight={str(timeline.get("inflight", "未取得")).lower()}、errors{timeline.get("errors", "未取得")}、'
            f'emitted{collector.get("emitted_events", "未取得")}、rejected{collector.get("rejected_samples", "未取得")}，'
            f'声纹submitted{speaker.get("submitted", "未取得")}、evidence_errors{speaker.get("evidence_errors", "未取得")}。'
            f'新进程记忆完成{worker.get("completed", "未取得")}/丢弃{worker.get("discarded", "未取得")}/'
            f'streak{retry.get("failure_streak", "未取得")}/{retry.get("last_delay_seconds", "未取得")}秒退避，'
            '脱敏错误无法识别具体拒绝原因。')
    note = (
        'v20身份、历史与时间轴增量已发布，下一阶段优先继续性能优化\n\n'
        f'运行根 {spec["target"]}。startup SHA {spec["startup_sha256"]}，manifest SHA {spec["source_manifest_sha256"]}，380份组件，config SHA {spec["configuration_sha256"]}。\n'
        f'封存boot {spec["boot_id"]}，supervisor {ready["main_pid"]}，GTK {ready["gtk_pid"]}，camera {mapping["camera"]["pid"]}。操作前现读入口和进程归属。\n'
        + listening_line + '用户最新明确“暂时保持暂停”，真人测试留待后续。输入模式采用免唤醒词半双工。\n'
        '本次精确合入6份源码，新增单日对话删除的预览与完整播放确认流程、自然身份问句和同轮图库证据接线、声纹线索入时间轴的有界重试与事务有效性检查。日期删除保留原范围权限、60秒预览和更晚代次确认要求。\n'
        '板端实际执行公开合成链路92项全部通过，退出码0、stderr空、临时库已移除、线程遗留0。ASR、PCM、TTS、原生就绪与GUI使用明确夹具，真实听音、真人辨认率和时延仍待当前版本验收。\n'
        + diagnostic_line + '\n'
        '声纹仍未标定，候选身份不自动授予个人档案权限。已完成关联的自然解绑/重新关联入口、单独登记记录的统一命名仍有缺口。\n'
        '长期摘要保真拒绝和退避仍待处理。新Store改动用于事件写入有效性检查，本轮尚未形成摘要稳定性完成结论。旧test_board_memory_review.py与test_board_memory_completion.py因缺少映射内common.timeline_conversations未完成收集，保留原失败记录。\n'
        '下一阶段按用户要求优先继续性能优化，root正在准备公开ASR和音频前端线程对照。该阶段尚无新提速或真人效果验收结论。\n'
        f'公开测试临时遗留共11目录、{cleanup["regular_file_bytes"]}字节，约10.3MB，包含冷启动5目录与记忆6目录。自动审批阻止清理，已停止重试，清单原样保留。\n'
        f'接续入口 {canonical}。发布器 {operator["publisher"]}，以匹配spec及哈希操作。旧v19快照独立保留，本次原文档字节归档在 {HERE / "before"}。\n'
    )
    short = ('v20已发布6源增量，共380组件。单日记录删除、自然身份查询和声纹线索入时间轴已接入，板端公开合成链路92项通过。\n\n'
        + listening_line + '用户选择暂时保持暂停，下一阶段优先继续性能优化。声纹标定、真实听音与长期摘要稳定性继续验证，两个旧测试模块的依赖缺口仍保留。\n\n'
        f'详见[当前观测]({canonical.as_posix()})、[接续简记]({(HERE / "current_note.txt").as_posix()})和[状态]({(REPAIR / "STATUS.json").as_posix()})。')
    body = '\n'.join('- ' + line for line in note.strip().splitlines() if line)
    updates = {'project_AGENTS': replace_block(originals['project_AGENTS'], 'board-business-live-20261030', body),
        'project_README': replace_block(originals['project_README'], 'dialogue-current-20261031', short)}
    analysis = replace_block(originals['analysis_README'], 'current-v19-20261031', short, 'current-v20-20261031')
    analysis = replace_block(analysis, 'board-business-live-20261030', body)
    updates['analysis_README'] = replace_block(analysis, 'performance-dialogue-plan-20261031',
        f'- [性能与对话平衡优化方案]({(BASE / "语言模型分析/性能与对话平衡优化方案_20261031.txt").as_posix()})已补充v20功能和待验范围。')
    old_note = (REPAIR / 'docs_state_v19/current_note.txt').read_bytes()
    for key in ('owner_continuation', 'performance_plan', 'analysis_performance_plan'):
        assert originals[key].startswith(old_note), key
        updates[key] = note.encode('utf-8') + originals[key][len(old_note):]
    common = {key: observation[key] for key in ('status', 'updated_utc', 'root', 'startup_sha256', 'source_manifest_sha256',
        'configuration_sha256', 'component_pins', 'board_boot_id', 'supervisor_pid', 'gtk_pid', 'camera_pid',
        'camera_birth_ticks', 'current_revision_acceptance', 'operator_instruction', 'evidence')}
    worker, retry = memory['worker'] or {}, memory['retry'] or {}
    common.update(current_revision=REVISION, current_observation=current,
        last_observed_listening_enabled=listening['enabled'], last_observed_listening_state=listening['state'],
        microphone_open=listening['microphone_open'], playing=state['playing'],
        physical_microphone_opened=listening['microphone_open'], physical_audio_played=False,
        automatic_listening_restored=listening['enabled'], latest_user_listening_choice=listening['enabled'],
        user_manual_pause_preserved=not listening['enabled'], memory_retry_history=memory,
        memory_failure_metadata={'specific_current_failure_reason_available': False},
        latest_memory_runtime_counters={'process_revision': REVISION, 'boot_id': spec['boot_id'],
            'observed_mono': state['observed_mono'], 'completed': worker.get('completed'),
            'discarded': worker.get('discarded'), 'failure_streak': retry.get('failure_streak'),
            'current_runtime_available': memory['current_runtime_available'], 'whole_store_health_verified': False},
        last_detailed_memory_observation={'current_detailed_store_snapshot_available': False, 'runtime_only': memory},
        later_capture_failure_count=None, frontend_worker_pid=None, public_test_cleanup=cleanup,
        m03_date_delete_deployed=True, current_live_state_claimed=False,
        verification_scope_notice='Actual v20 source/READY seal plus 92 public synthetic ARM checks. Physical speech, speaker calibration, summary stability and legacy collection gaps remain open.')
    for key in ('dialogue_STATUS', 'implementation', 'production_live', 'resume_verification', 'character_switch', 'windows_coordination'):
        document = json.loads(originals[key])
        document.setdefault('continuation_history', []).append({'superseded_by_revision': REVISION,
            'previous_status': document.get('status'), 'original_bytes_archive': str(HERE / 'before' / targets[key].relative_to(BASE))})
        for item in [document] + [document[name] for name in ('production', 'production_business_live') if isinstance(document.get(name), dict)]:
            item.update(copy.deepcopy(common))
            for name in ('main_pid', 'last_verified_ui_supervisor_pid', 'last_observed_ui_supervisor_pid'):
                if name in item:
                    item[name] = ready['main_pid']
            for name in ('last_verified_gtk_pid', 'last_observed_gtk_pid'):
                if name in item:
                    item[name] = ready['gtk_pid']
            if 'last_verified_pid_fields_revision' in item:
                item['last_verified_pid_fields_revision'] = REVISION + '_source_mapping'
            for name in ('physical_audio_acceptance_passed', 'controls_verified', 'continuous_capture_passed',
                         'short_capture_verified', 'full_physical_dialogue_acceptance', 'multi_hour_stability_verified'):
                item[name] = False
            if 'listening' in item:
                item['listening'] = listening['enabled']
            item['verified_listening'] = {'revision': REVISION, 'startup_sha256': spec['startup_sha256'],
                'state': listening['state'], 'enabled': listening['enabled'], 'continuous_capture_passed': False}
            item['response_latency'] = {'revision': REVISION, 'startup_sha256': spec['startup_sha256'],
                'new_human_waiting_acceptance': False, 'audible_first_sound_measured': False, 'current_observation': current}
        if key == 'character_switch':
            document['current_pair_observation'] = 'v20 sources and native visibility sealed. Current physical FPS and human audio acceptance remain open.'
        if key == 'windows_coordination':
            document['updated_at'] = now
            for name in ('production_UI_switch', 'production_business_cutover'):
                document[name].update(state=STATUS, current_revision=REVISION, updated_utc=now,
                    startup_sha256=spec['startup_sha256'], source_manifest_sha256=spec['source_manifest_sha256'],
                    component_pins=380, current_observation=current,
                    physical_microphone_opened=listening['microphone_open'], physical_audio_played=False)
        updates[key] = seal.common.encoded(document)
    return {'bundle': bundle, 'targets': targets, 'originals': originals, 'updates': updates,
        'observation': observation, 'observation_raw': observation_raw, 'canonical': canonical,
        'note': note, 'evidence': evidence, 'previous_handoff': reference(PRIOR)}


def apply_plan(plan):
    read_bundle()
    if HERE.exists() or plan['canonical'].exists():
        raise ValueError('v20_document_snapshot_already_exists')
    if any(path.read_bytes() != plan['originals'][key] for key, path in plan['targets'].items()):
        raise ValueError('concurrent_document_change')
    if any(reference(Path(row['path'])) != row for row in plan['evidence']):
        raise ValueError('source_evidence_changed')
    HERE.mkdir()
    before = []
    for key, path in plan['targets'].items():
        archive = HERE / 'before' / path.relative_to(BASE)
        archive.parent.mkdir(parents=True, exist_ok=True)
        seal.exact_file(archive, plan['originals'][key])
        before.append({'key': key, 'original': reference(path), 'archive': reference(archive)})
    seal.exact_file(HERE / 'before_manifest.json', seal.common.encoded({'files': before}))
    seal.exact_file(plan['canonical'], plan['observation_raw'])
    seal.exact_file(HERE / 'current_note.txt', plan['note'].encode('utf-8'))
    for key, path in plan['targets'].items():
        path.write_bytes(plan['updates'][key])
    assert all(Path(row['archive']['path']).read_bytes() == plan['originals'][row['key']] for row in before)
    assert all(path.read_bytes() == plan['updates'][key] for key, path in plan['targets'].items())
    assert all(reference(Path(row['path'])) == row for row in plan['evidence'])
    handoff = {'schema': 'aura.docs-state-handoff.v1', 'status': 'V20_CURRENT_POINTER_SNAPSHOT_PHYSICAL_AND_MEMORY_VALIDATION_OPEN',
        'revision': REVISION, 'startup_sha256': plan['observation']['startup_sha256'],
        'source_manifest_sha256': plan['observation']['source_manifest_sha256'],
        'configuration_sha256': plan['observation']['configuration_sha256'], 'component_pins': 380,
        'current_observation': reference(plan['canonical']), 'previous_handoff': plan['previous_handoff'],
        'current_note': reference(HERE / 'current_note.txt'), 'before_manifest': reference(HERE / 'before_manifest.json'),
        'updater': reference(Path(__file__)), 'changed_documents': [{**reference(path), 'key': key} for key, path in plan['targets'].items()],
        'evidence': plan['evidence'], 'historical_bytes_preserved': True, 'optimization_task_complete': False,
        'device_model_or_private_database_actions': False, 'production_tools_candidates_or_runtime_receipts_modified': False}
    seal.exact_file(HERE / 'HANDOFF.json', seal.common.encoded(handoff))
    return {'status': handoff['status'], 'documents_updated': 12, 'handoff': reference(HERE / 'HANDOFF.json')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--observation', type=Path, default=DEFAULT_OBSERVATION)
    parser.add_argument('--observation-sha256', default=DEFAULT_OBSERVATION_SHA)
    parser.add_argument('--apply-local-docs', action='store_true')
    args = parser.parse_args()
    if bool(args.observation) != bool(args.observation_sha256):
        parser.error('--observation and --observation-sha256 must be supplied together')
    plan = build_plan(read_bundle(args.observation, args.observation_sha256))
    if not args.apply_local_docs:
        print(json.dumps({'status': 'DRY_COMMITTED_V20_DOC_PLAN_VALIDATED_NO_WRITES',
            'documents': len(plan['targets']), 'startup_sha256': plan['observation']['startup_sha256'],
            'listening_enabled': plan['observation']['listening']['enabled']}))
        return
    print(json.dumps(apply_plan(plan), ensure_ascii=False))


if __name__ == '__main__':
    main()
