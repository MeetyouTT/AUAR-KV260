"""Prepare v19 current-pointer documents from root's committed seal only.

Default mode is read-only. --apply-local-docs updates local continuation files.
"""
import argparse
import copy
import datetime
import json
from pathlib import Path

import seal_stability as seal


BASE = Path(r'E:\Win共享文件')
REPAIR = seal.common.REPAIR
HERE = REPAIR / 'docs_state_v19'
REVISION = 'v19'
STATUS = 'V19_STABILITY_READY_USER_PAUSED_FUNCTION_VALIDATION_IN_PROGRESS'
PRIOR = REPAIR / 'docs_state_v18_minor/HANDOFF.json'
OBSERVATION_PATH = REPAIR / 'progress_followup_20261031/worker_observation_1793500853076730900.json'
VISUAL_PATH = REPAIR / 'progress_followup_20261031/visual_records_diagnostic_1793500851575609200.json'


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
        raise ValueError('committed_v19_seal_must_still_be_current')


def read_bundle():
    raws = {name: (seal.EVIDENCE / name).read_bytes() for name in ('spec.json', 'ready.json', 'installed.json')}
    spec, ready, installed = [json.loads(raws[name]) for name in ('spec.json', 'ready.json', 'installed.json')]
    products = seal.validate_inputs(spec, ready, installed)
    mapping = load(seal.EVIDENCE / 'source_mapping.json')
    seal.validate_mapping(mapping, spec, ready, products)
    marker = load(seal.EVIDENCE / 'canonical_update_state.json')
    current = {name: (seal.CANONICAL / name).read_bytes() for name in ('spec.json', 'actual_ready.json')}
    require_committed(raws, marker, current)
    samples = load(OBSERVATION_PATH)['samples']
    visual = load(VISUAL_PATH)
    assert len(samples) == 20 and all(sample['startup_sha256'] == spec['startup_sha256'] for sample in samples)
    assert visual['startup_sha256'] == spec['startup_sha256'] and visual['board_boot_id'] == spec['boot_id']
    assert all(sample['listening']['enabled'] is False and sample['safe_capture']['counters']['armed'] == 0 for sample in samples)
    assert all(sample['runtime_faults']['count'] == sample['renderer_worker_faults']['count'] == 0 for sample in samples)
    assert 'board/runtime/history_delete.py' not in mapping['component_pins']
    return {'raws': raws, 'spec': spec, 'ready': ready, 'mapping': mapping, 'samples': samples, 'visual': visual}


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
    samples, visual = bundle['samples'], bundle['visual']
    prior = load(PRIOR)
    targets = {row['key']: Path(row['path']) for row in prior['changed_documents']}
    assert len(targets) == 12 and all(path.is_relative_to(BASE) for path in targets.values())
    originals = {key: path.read_bytes() for key, path in targets.items()}
    previous_observation = REPAIR / 'current_observation_v18_minor.json'
    previous = load(previous_observation)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    last = samples[-1]
    inputs = [seal.EVIDENCE / name for name in ('spec.json', 'ready.json', 'installed.json', 'source_mapping.json', 'canonical_update_state.json')]
    inputs += [OBSERVATION_PATH, VISUAL_PATH, PRIOR, previous_observation,
               seal.HERE / 'APPROVED_PAYLOAD.json', seal.HERE / 'SEAL_HANDOFF.json']
    evidence = [reference(path) for path in inputs]
    memory = {'observed_mono': last['observed_mono'], 'reference': reference(OBSERVATION_PATH),
        'worker': last['memory'], 'retry': last['memory_retry'], 'counters_are_process_local': True,
        'specific_failure_reason_available': False, 'whole_store_health_verified': False,
        'interpretation': 'This v19 process reported completed0/discarded5/streak5 with a redacted error. Earlier-process negation_missing does not identify this process failure.'}
    acceptance = dict(source_and_service_verified=True, installation_ready_verified=True,
        saved_pause_restore_verified=True, production_automatic_greeting_disabled_deployed=True,
        bounded_audio_consumption_deployed=True, full_physical_dialogue_acceptance=False,
        physical_audio_acceptance_passed=False, continuous_capture_passed=False,
        controls_verified=False, short_capture_verified=False, audible_first_sound_measured=False,
        prior_autonomous_cancel_cause_resolved=False, multi_hour_stability_verified=False)
    operator = {'publisher': str(seal.HERE / 'publish_stability.py'),
        'spec': reference(seal.EVIDENCE / 'spec.json'), 'sole_publisher': 'root',
        'usage': 'Fresh-read owners and saved preference before normal publication. Use the matching applied spec and its hash.',
        'expected_final_listening_enabled': False, 'old_887_publisher_allowed': False}
    observation = {
        'schema': 'aura.current-document-observation.v1', 'revision': REVISION, 'status': STATUS,
        'updated_utc': now, 'root': spec['target'], 'startup_sha256': spec['startup_sha256'],
        'source_manifest_sha256': spec['source_manifest_sha256'], 'configuration_sha256': spec['configuration_sha256'],
        'component_pins': 379, 'board_boot_id': spec['boot_id'],
        'native_library_sha256': spec['native_library_sha256'],
        'character_pair_selection_sha256': spec['character_pair_selection_sha256'],
        'source_observed_mono': mapping['observed_mono'], 'diagnostic_observed_mono': last['observed_mono'],
        'supervisor_pid': mapping['supervisor']['pid'], 'supervisor_birth_ticks': mapping['supervisor']['birth_ticks'],
        'gtk_pid': mapping['gtk']['pid'], 'gtk_birth_ticks': mapping['gtk']['birth_ticks'],
        'camera_pid': mapping['camera']['pid'], 'camera_birth_ticks': mapping['camera']['birth_ticks'],
        'phase': mapping['phase'], 'playing': mapping['playing'], 'listening': mapping['listening'],
        'saved_listening_preference': mapping['saved_listening_preference'],
        'native_visible': mapping['native_visible'], 'runtime_faults': last['runtime_faults'],
        'renderer_worker_faults': last['renderer_worker_faults'], 'publication_ready': ready,
        'frontend_options': previous['frontend_options'], 'windows_model_owner': previous['windows_model_owner'],
        'source_files': mapping['source_files'], 'current_revision_acceptance': acceptance,
        'memory': memory, 'visual_observation': visual,
        'passive_observation': {'reference': reference(OBSERVATION_PATH), 'samples': len(samples),
            'elapsed_seconds': last['observed_mono'] - samples[0]['observed_mono'],
            'state': 'PAUSED', 'armed': 0, 'gui_faults': 0, 'worker_faults': 0,
            'physical_audio_acceptance': False, 'continuous_listening_acceptance': False},
        'operator_instruction': operator, 'previous_current_snapshot': reference(previous_observation),
        'historical_user_feedback': previous['historical_user_feedback'],
        'public_test_cleanup': previous['public_test_cleanup'],
        'pending': {'m03_date_delete_deployed': False, 'identity_history_candidate_under_review': True,
            'memory_rejection_stability_under_review': True, 'speaker_calibrated': False,
            'automatic_profile_access': False, 'new_multicomponent_motion_deployed': False,
            'target_24fps_deployed': False, 'new_human_audio_acceptance': False},
        'current_live_state_claimed': False, 'evidence': evidence,
    }
    canonical = REPAIR / 'current_observation_v19.json'
    observation_raw = seal.common.encoded(observation)
    current = {'path': str(canonical), 'sha256': seal.common.sha(observation_raw), 'bytes': len(observation_raw),
        'revision': REVISION, 'status': STATUS, 'startup_sha256': spec['startup_sha256'],
        'source_manifest_sha256': spec['source_manifest_sha256'], 'configuration_sha256': spec['configuration_sha256'],
        'component_pins': 379, 'observations_are_not_full_acceptance': True}
    note = (
        'v19稳定性版本已发布，保留暂停选择，功能验收继续进行\n\n'
        f'运行根 {spec["target"]}。startup SHA {spec["startup_sha256"]}，manifest SHA {spec["source_manifest_sha256"]}，379份组件，config SHA {spec["configuration_sha256"]}。\n'
        f'封存boot {spec["boot_id"]}，supervisor {ready["main_pid"]}，GTK {ready["gtk_pid"]}，camera {mapping["camera"]["pid"]}。后续操作前现读入口和进程归属。\n'
        '实际READY与封存核对了持久偏好enabled=false、PAUSED、mic=false及可见原生画面。当前保留用户保存的暂停选择，自动聆听能力采用免唤醒词半双工。\n'
        '本次精确更新GTK与board_recording两份源码。生产自动招呼关闭，音频事件消费在处理下一事件前检查12ms预算，每轮最多8条。单次事件本身仍可能超过预算。\n'
        '20点暂停观察覆盖约57.726秒，armed保持0，GUI与worker故障计数0。该窗口没有开麦对话，持续聆听、完整听音、实际等待与旧自主取消问题的实机复验仍待进行。\n'
        '视觉末点steps368、accepted_frames368、emitted_events3、errors0，last_status为observed。板端视觉采集和时间轴工作线程有实际推进，人数问答的新版本真人复验仍待进行。\n'
        '本进程记忆末点mono16713.565为完成0、丢弃5、streak5、48秒退避，错误仍为脱敏other16。具体拒绝原因和摘要稳定性继续排查，旧进程negation_missing仅保留为历史原因。\n'
        'M03日期删除与身份协作新包正在准备，当前v19尚未部署这些增量。声纹未校准，全状态自然动作、24fps和多小时稳定性仍待验证。\n'
        f'接续入口 {canonical}。发布器 {operator["publisher"]}，使用已封存spec及哈希。原v18 minor文档按原字节归档在 {HERE / "before"}，旧快照独立保留。\n'
    )
    short = ('v19已发布并保留用户保存的暂停选择，当前为PAUSED、麦克风关闭。生产自动招呼关闭，音频消费有界处理已接入。\n\n'
        '暂停观察无GUI或worker故障，视觉采集正在推进。记忆摘要退避与新版本真人对话仍待继续验证，M03与身份协作增量尚未发布。\n\n'
        f'详见[当前观测]({canonical.as_posix()})、[接续简记]({(HERE / "current_note.txt").as_posix()})和[状态]({(REPAIR / "STATUS.json").as_posix()})。')
    body = '\n'.join('- ' + line for line in note.strip().splitlines() if line)
    updates = {'project_AGENTS': replace_block(originals['project_AGENTS'], 'board-business-live-20261030', body),
        'project_README': replace_block(originals['project_README'], 'dialogue-current-20261031', short)}
    analysis = replace_block(originals['analysis_README'], 'current-v18-minor-20261031', short, 'current-v19-20261031')
    analysis = replace_block(analysis, 'board-business-live-20261030', body)
    updates['analysis_README'] = replace_block(analysis, 'performance-dialogue-plan-20261031',
        f'- [性能与对话平衡优化方案]({(BASE / "语言模型分析/性能与对话平衡优化方案_20261031.txt").as_posix()})已补充v19暂停状态和待验范围。')
    old_note = (REPAIR / 'docs_state_v18_minor/current_note.txt').read_bytes()
    for key in ('owner_continuation', 'performance_plan', 'analysis_performance_plan'):
        assert originals[key].startswith(old_note), key
        updates[key] = note.encode('utf-8') + originals[key][len(old_note):]
    common = {key: observation[key] for key in ('status', 'updated_utc', 'root', 'startup_sha256', 'source_manifest_sha256',
        'configuration_sha256', 'component_pins', 'board_boot_id', 'supervisor_pid', 'gtk_pid', 'camera_pid',
        'camera_birth_ticks', 'current_revision_acceptance', 'operator_instruction', 'evidence')}
    common.update(current_revision=REVISION, current_observation=current,
        last_observed_listening_enabled=False, last_observed_listening_state='PAUSED',
        microphone_open=False, playing=False, physical_microphone_opened=False, physical_audio_played=False,
        automatic_listening_restored=False, latest_user_listening_choice=False, user_manual_pause_preserved=True,
        memory_retry_history=memory, memory_failure_metadata={'specific_current_failure_reason_available': False},
        latest_memory_runtime_counters={'process_revision': REVISION, 'boot_id': spec['boot_id'],
            'observed_mono': last['observed_mono'], 'completed': 0, 'discarded': 5, 'failure_streak': 5,
            'error_present': True, 'counters_are_process_local': True, 'whole_store_health_verified': False},
        last_detailed_memory_observation={'current_detailed_store_snapshot_available': False, 'runtime_only': memory},
        later_capture_failure_count=None, frontend_worker_pid=None,
        m03_date_delete_deployed=False, current_live_state_claimed=False,
        verification_scope_notice='Saved v19 source/READY/paused-state verification and a paused observation window. Current human audio, continuous capture and memory stability remain unverified.')
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
            for name in ('physical_audio_acceptance_passed', 'controls_verified', 'continuous_capture_passed',
                         'short_capture_verified', 'full_physical_dialogue_acceptance', 'multi_hour_stability_verified'):
                item[name] = False
            if 'listening' in item:
                item['listening'] = False
            if 'microphone_or_playback_started' in item:
                item['microphone_or_playback_started'] = False
            item['verified_listening'] = {'revision': REVISION, 'status': 'SAVED_PAUSE_RESTORED',
                'startup_sha256': spec['startup_sha256'], 'continuous_capture_passed': False}
            item['response_latency'] = {'revision': REVISION, 'startup_sha256': spec['startup_sha256'],
                'new_human_waiting_acceptance': False, 'audible_first_sound_measured': False, 'current_observation': current}
        if key == 'character_switch':
            document['current_pair_observation'] = 'v19 source and visible native surface verified while PAUSED. Physical FPS and human audio remain pending.'
        if key == 'windows_coordination':
            document['updated_at'] = now
            for name in ('production_UI_switch', 'production_business_cutover'):
                document[name].update(state=STATUS, current_revision=REVISION, updated_utc=now,
                    startup_sha256=spec['startup_sha256'], source_manifest_sha256=spec['source_manifest_sha256'],
                    current_observation=current, physical_microphone_opened=False, physical_audio_played=False)
        updates[key] = seal.common.encoded(document)
    return {'bundle': bundle, 'targets': targets, 'originals': originals, 'updates': updates,
        'observation': observation, 'observation_raw': observation_raw, 'canonical': canonical,
        'note': note, 'evidence': evidence, 'previous_handoff': reference(PRIOR)}


def apply_plan(plan):
    # Recheck the publication and local bytes immediately before any mutation.
    read_bundle()
    if HERE.exists() or plan['canonical'].exists():
        raise ValueError('v19_document_snapshot_already_exists')
    for key, path in plan['targets'].items():
        if path.read_bytes() != plan['originals'][key]:
            raise ValueError('concurrent_document_change')
    for row in plan['evidence']:
        if reference(Path(row['path'])) != row:
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
    for row in before:
        assert Path(row['archive']['path']).read_bytes() == plan['originals'][row['key']]
    for key, path in plan['targets'].items():
        assert path.read_bytes() == plan['updates'][key]
    assert all(reference(Path(row['path'])) == row for row in plan['evidence'])
    handoff = {'schema': 'aura.docs-state-handoff.v1', 'status': 'V19_CURRENT_POINTER_SNAPSHOT_FUNCTION_VALIDATION_OPEN',
        'revision': REVISION, 'startup_sha256': plan['observation']['startup_sha256'],
        'source_manifest_sha256': plan['observation']['source_manifest_sha256'],
        'configuration_sha256': plan['observation']['configuration_sha256'], 'component_pins': 379,
        'current_observation': reference(plan['canonical']), 'previous_handoff': plan['previous_handoff'],
        'current_note': reference(HERE / 'current_note.txt'), 'before_manifest': reference(HERE / 'before_manifest.json'),
        'updater': reference(Path(__file__)), 'changed_documents': [{**reference(path), 'key': key} for key, path in plan['targets'].items()],
        'evidence': plan['evidence'], 'historical_bytes_preserved': True, 'optimization_task_complete': False,
        'device_model_or_private_database_actions': False, 'production_tools_candidates_or_runtime_receipts_modified': False}
    seal.exact_file(HERE / 'HANDOFF.json', seal.common.encoded(handoff))
    return {'status': handoff['status'], 'documents_updated': 12, 'handoff': reference(HERE / 'HANDOFF.json')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply-local-docs', action='store_true')
    args = parser.parse_args()
    plan = build_plan(read_bundle())
    if not args.apply_local_docs:
        print(json.dumps({'status': 'DRY_COMMITTED_V19_DOC_PLAN_VALIDATED_NO_WRITES',
            'documents': len(plan['targets']), 'startup_sha256': plan['observation']['startup_sha256'],
            'listening_enabled': False}))
        return
    print(json.dumps(apply_plan(plan), ensure_ascii=False))


if __name__ == '__main__':
    main()
