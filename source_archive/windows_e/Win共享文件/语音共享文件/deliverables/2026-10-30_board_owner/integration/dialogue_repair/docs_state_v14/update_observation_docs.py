"""Docs/metadata only: distinguish the installed v14 observation from old gates.

No production imports, devices, services, models, or business databases.  The
strict listening updater is deliberately not called or changed.  All replaced
documents are preserved byte-for-byte before a compare-and-swap update.
"""
import argparse
import copy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import statistics

HERE = Path(__file__).resolve().parent
REPAIR = HERE.parent
OWNER = REPAIR.parents[1]
PROJECT = OWNER.parents[1]
SHARED = PROJECT.parent
STARTUP = '39b102a4a505db491cf06b90e3a5232bfb656c79cb0a3c221551d76d414a9a0a'
MANIFEST = 'a2545970650f60b95cdc6e4f0a31c234f37adb5f0662c9f04ded791352f53353'
CONFIG = 'faa5bead11f6c212412cf295db7d11c092c51848a5b08b49d78449ed613ba6d7'
STATUS = 'V14_INSTALLED_READY_CURRENT_OBSERVATIONS_ACCEPTANCE_INCOMPLETE'
OBSERVATION_PATH = REPAIR / 'current_observation_v14.json'
TARGETS = {
    'project/AGENTS.md': PROJECT / 'AGENTS.md',
    'project/README.md': PROJECT / 'README.md',
    'analysis/README.md': SHARED / '语言模型分析/README.md',
    'owner/板端业务正式接管与实测接续_20261030.txt': OWNER / '板端业务正式接管与实测接续_20261030.txt',
    'owner/IMPLEMENTATION_STATE.json': OWNER / 'IMPLEMENTATION_STATE.json',
    'owner/integration/PRODUCTION_BUSINESS_LIVE.json': OWNER / 'integration/PRODUCTION_BUSINESS_LIVE.json',
    'owner/integration/RESUME_VERIFICATION.json': OWNER / 'integration/RESUME_VERIFICATION.json',
    'owner/integration/CHARACTER_SWITCH.json': OWNER / 'integration/CHARACTER_SWITCH.json',
    'owner/coordination/runtime_windows.json': OWNER / 'coordination/runtime_windows.json',
    'owner/integration/dialogue_repair/STATUS.json': REPAIR / 'STATUS.json',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n').encode('utf-8')


def load(path):
    raw = path.read_bytes()
    return json.loads(raw.decode('utf-8-sig')), raw


def relative(path):
    return path.relative_to(SHARED).as_posix()


def main(apply=False):
    assert PROJECT.name == '语音共享文件' and OWNER.name == '2026-10-30_board_owner'
    assert not (HERE / 'journal.json').exists(), 'This observation update is single-use.'
    originals = {name: path.read_bytes() for name, path in TARGETS.items()}
    evidence, evidence_raw = {}, {}

    def source(name, path):
        value, raw = load(path)
        evidence[name] = {'path': relative(path), 'sha256': sha(raw), 'bytes': len(raw)}
        evidence_raw[path] = raw
        return value

    installed = source('installed', OWNER / 'integration/listening_entry_fix/actual_automatic-listening-v14-compact-dialogue-memory.json')
    ready = source('ready', OWNER / 'integration/production_business_acceptance/actual_ready.json')
    spec = source('spec', OWNER / 'integration/production_business_acceptance/spec.json')
    initial = source('memory_initial', REPAIR / 'first_wait_integration/actual_memory_v14_initial.json')
    followup = source('memory_followup', REPAIR / 'first_wait_integration/actual_memory_v14_followup.json')
    post = source('memory_latest', REPAIR / 'first_wait_integration/actual_memory_v14_postresearch.json')
    human = source('human_round', REPAIR / 'compact_human_round.json')
    runtime = source('runtime_followup', REPAIR / 'resume_v14_runtime.json')
    paused = source('maintenance_pause', REPAIR / 'asr_trial_paused.json')
    chain = source('public_model_chain', REPAIR / 'first_wait_integration/actual_public_compact_chain.json')
    abba = source('public_name_abba', REPAIR / 'realtime_dialogue_research/direct_comparison_v2/benchmark_runs/direct_name_abba_8b8643d9d18b.json')
    host_latest = source('windows_host_latest', OWNER / 'integration/production_model_host/latest.json')
    host = source('windows_host_status', OWNER / ('integration/production_model_host/sessions/' + host_latest['session_id'] + '/status.json'))
    host_install = source('windows_host_install', REPAIR / 'first_wait_integration/host_install_receipt.json')
    old_live = source('listening_live_not_v14', OWNER / 'integration/listening_entry_fix/actual_live_listening.json')
    old_control = source('listening_controls_not_v14', OWNER / 'integration/listening_entry_fix/actual_control_semantics.json')
    updater = OWNER / 'integration/listening_entry_fix/update_verified_state.py'
    evidence['strict_updater_not_executed'] = {'path': relative(updater), 'sha256': sha(updater.read_bytes())}

    assert installed['startup_sha256'] == spec['startup_sha256'] == STARTUP
    assert installed['source_manifest_sha256'] == MANIFEST
    assert installed['configuration_sha256'] == spec['configuration_sha256'] == CONFIG
    assert installed['component_pins'] == spec['component_pins'] == 378
    assert ready['status'] == 'PRODUCTION_BOARD_BUSINESS_READY'
    assert installed['target'] == spec['target'] == ready['root']
    assert ready['data_origin'] == 'board' and ready['guard_removed'] is True
    assert host['session_id'] == host_latest['session_id'] and host['status'] == 'READY'
    assert host['role'] == 'model_inference_only' and host['business_database_opened'] is False
    for value in (initial, followup, post, runtime, paused, chain):
        assert value['startup_sha256'] == STARTUP
    samples = human['samples']
    assert samples and all(s['startup_sha256'] == STARTUP for s in samples)
    assert runtime['board_boot_id'] == spec['boot_id']
    assert paused['board_boot_id'] == spec['boot_id'] and paused['phase'] == 'IDLE'
    assert paused['listening']['state'] == 'PAUSED' and paused['listening']['enabled'] is False
    assert paused['playing'] is False and paused['dialogue']['pending'] is False
    assert all(s['board_boot_id'] == spec['boot_id'] for s in samples)
    assert old_live['startup_sha256'] != STARTUP and old_control['startup_sha256'] != STARTUP

    rounds, seen = [], set()
    for s in samples:
        latency, preparation = s.get('latency', {}), s.get('prepare_latency', {})
        if latency.get('complete') is True and latency.get('asr_completed') is True and preparation.get('complete') is True:
            key = (latency.get('asr_ms'), preparation.get('llm_rpc_ms'), latency.get('first_audio_queued_ms'))
            if key not in seen:
                seen.add(key)
                rounds.append({'first_observed_mono': s['observed_mono'], 'asr_ms': key[0],
                               'llm_rpc_ms': key[1], 'first_audio_queued_ms': key[2]})
    assert len(rounds) == 4, 'Expected four distinct completed metadata snapshots.'
    short = [r for r in rounds if r['asr_ms'] < 5000]
    assert len(short) == 3
    arms = {arm: [t['llm_wall_ms'] for t in abba['trials'] if t['arm'] == arm] for arm in ('A', 'B')}
    assert len(abba['trials']) == 4 and len(arms['A']) == len(arms['B']) == 2
    gains = 100 * (1 - statistics.median(arms['B']) / statistics.median(arms['A']))

    def memory(value):
        return {'observed_mono': value['observed_mono'], 'worker': value['worker'],
                'retry': value['retry'], 'store': value['store'],
                'backlog_source_counts': value['backlog_source_counts'],
                'latest_16_task_counts': value.get('latest_16_task_counts', []),
                'missing_body_classification': value.get('missing_body_classification', {}),
                'summary_diagnostics': value['summary_diagnostics']}

    updated = datetime.now(timezone.utc).isoformat()
    gates = {'controls_verified': False, 'continuous_capture_passed': False,
             'priority_scope_passed': False, 'short_capture_verified': False,
             'full_physical_dialogue_acceptance': False, 'physical_audio_acceptance_passed': False,
             'operator_asr_acceptance_passed': False, 'operator_playback_acceptance_passed': False,
             'multi_hour_stability_verified': False, 'controlled_whole_board_cpu_reduction_proven': False,
             'audible_first_sound_measured': False, 'cold_boot_listening_verified': False,
             'actual_restart_pause_verified': False}
    windows = {'session_id': host_latest['session_id'], 'launcher_pid': host_latest['owner']['pid'],
               'host_pid': host['pid'], 'tts_pid': host['same_unique_tts_pid'],
               'fixed_daemon_pid': host['fixed_daemon_pid'], 'status': host['status'],
               'status_ready_utc': host['ready_utc'], 'role': host['role'],
               'endpoint': '%s:%s' % (host['listen'], host['port']),
               'configuration_sha256': host['configuration_sha256'],
               'host_source_sha256': next(x['sha256'] for x in host_install['sources'] if x['path'] == 'tools/model_inference_host.py'),
               'business_database_opened': False, 'request_logging': False, 'raw_audio_archived': False,
               'observed_from_saved_receipts_only': True, 'fresh_health_called_by_document_updater': False}
    observation = {
        'schema': 'aura.current-observation.v1', 'status': STATUS, 'updated_utc': updated,
        'evidence_path_base': str(SHARED),
        'revision': 'v14', 'root': ready['root'], 'startup_sha256': STARTUP,
        'source_manifest_sha256': MANIFEST, 'component_pins': 378, 'configuration_sha256': CONFIG,
        'board_boot_id': spec['boot_id'], 'supervisor_pid': ready['main_pid'], 'gtk_pid': ready['gtk_pid'],
        'camera_pid': None, 'last_known_camera_pid': 260102,
        'camera_pid_caveat': 'No v14 camera-PID receipt in this document update; older same-boot records only.',
        'scope': 'Existing saved public metadata only; no new runtime/device/model/database operation.',
        'time_basis': 'Board monotonic seconds are comparable only within the recorded board boot.',
        'data_origin': 'board', 'retention_enabled': installed['retention_enabled'],
        'automatic_listening': installed['automatic_listening'], 'wake_word_required': installed['wake_word_required'],
        'conversation_mode': installed['conversation_mode'], 'voice_barge_in': installed['gui_options']['voice_barge_in'],
        'business_options': installed['business_options'],
        'readiness_observed': {'status': ready['status'], 'guard_removed': ready['guard_removed'],
                               'physical_microphone_opened': ready['physical_microphone_opened'],
                               'listening_state': ready['listening_state'], 'physical_audio_played_at_ready': ready['physical_audio_played']},
        'current_revision_acceptance': gates,
        'missing_or_incomplete': ['v14 pause/resume/cancel controls did not pass initial waiting',
                                  'No v14 continuously quiet capture and priority-scope acceptance receipt',
                                  'Audible speaker first sound has not been measured',
                                  'Human response-wait acceptance and multi-hour stability remain incomplete'],
        'strict_listening_updater': {'executed': False, 'code_changed': False,
            'reason': 'Its same-revision live and control gates are not satisfied; this is an observation update, not verified-listening promotion.',
            'saved_live_startup_sha256': old_live['startup_sha256'],
            'saved_live_continuous_capture_passed': old_live['continuous_capture_passed'],
            'saved_control_startup_sha256': old_control['startup_sha256']},
        'human_dialogue_window': {'sample_count': len(samples),
            'seconds': samples[-1]['observed_mono'] - samples[0]['observed_mono'],
            'completed_round_metadata': rounds,
            'short_asr_round_count': len(short),
            'short_asr_ms_range': [min(r['asr_ms'] for r in short), max(r['asr_ms'] for r in short)],
            'short_llm_rpc_ms_range': [min(r['llm_rpc_ms'] for r in short), max(r['llm_rpc_ms'] for r in short)],
            'short_first_audio_queued_ms_range': [min(r['first_audio_queued_ms'] for r in short), max(r['first_audio_queued_ms'] for r in short)],
            'speaker_first_audio_measured': False,
            'capture_failure_max_in_window': max(s.get('capture_performance', {}).get('capture_failures', 0) for s in samples),
            'runtime_fault_max_in_window': max(s.get('runtime_faults', {}).get('count', 0) for s in samples),
            'feedback': '用户仍反馈回答等待太久；不宣称端到端等待问题已解决。',
            'limitations': 'Uncontrolled human rounds; no input content, duration matching, or acoustic first-sound measurement. Four rounds are retained, including the 15.8s ASR outlier.'},
        'runtime_followup': {'observed_mono': runtime['observed_mono'], 'phase': runtime['phase'],
            'playing': runtime['playing'], 'listening': runtime['listening'],
            'runtime_fault_count': runtime['runtime_faults']['count'],
            'capture_failures': runtime['capture_performance']['capture_failures'],
            'last_capture_failure_code': runtime['last_capture_failure']['error']['code'],
            'memory': {k: runtime['memory'][k] for k in ('running', 'completed', 'discarded')},
            'memory_failure_streak': runtime['memory_retry']['failure_streak'],
            'asr_ms': runtime['latency']['asr_ms'], 'llm_rpc_ms': runtime['prepare_latency']['llm_rpc_ms'],
            'first_audio_queued_ms': runtime['latency']['first_audio_queued_ms'],
            'speaker_first_audio_measured': False, 'last_ack_committed': runtime['last_ack']['committed'],
            'limitations': 'Later uncontrolled observation during SPEAKING, input length unknown; not a paired latency comparison or all-window health proof.'},
        'latest_runtime_observation': {'observed_mono': paused['observed_mono'], 'phase': paused['phase'],
            'playing': paused['playing'], 'listening': paused['listening'], 'pending': paused['dialogue']['pending'],
            'runtime_fault_count': paused['runtime_faults']['count'], 'maintenance_pause': True,
            'reason': 'Root temporarily paused listening for a public ASR candidate test; persisted automatic-listening selection remains true.',
            'resume_verified': False, 'current_live_state_claimed': False},
        'memory_observations': {'initial': memory(initial), 'followup': memory(followup), 'latest': memory(post),
            'initial_to_followup_seconds': followup['observed_mono'] - initial['observed_mono'],
            'scope': 'Initial 287→298 valid summaries, 869→858 total backlog, camera 618→607. Later 361 summaries, total backlog 927, camera 592 with new dialogue/device inflow.',
            'limitations': 'Counters are boot/window-specific. Cancelled/discarded tasks do not prove source-body deletion. Partial visual progress does not prove whole-store health or continuous total-backlog decline.'},
        'public_name_abba': {'trials': 4, 'per_arm': 2,
            'A_median_llm_wall_ms': statistics.median(arms['A']), 'B_median_llm_wall_ms': statistics.median(arms['B']),
            'median_llm_wall_reduction_percent': gains, 'tts_requests': abba['tts_requests'],
            'all_cross_arm_speech_identical': abba['all_cross_arm_speech_identical'],
            'scope': 'Tiny public-name LLM-only ABBA; approximately 19% is a local model-call observation, not human/end-to-end or acoustic acceptance.'},
        'windows_model_owner': windows,
        'unchanged_boundaries': {'business_and_storage': 'board', 'windows': 'model_inference_only',
            'fixed_model': host['model'], 'num_ctx': 2048, 'num_predict': 120, 'omnivoice_num_step': 16,
            'weights_root': 'D:/AIModels', 'following': False, 'pan_state': 'FAULT', 'pulse_us': None,
            'motion_state_claim': 'Existing safety boundary retained; document update performs no fresh motion I/O.',
            'private_data_replayed': False, 'raw_dialogue_or_pcm_exported': False},
        'evidence': evidence,
    }
    obs_raw = encoded(observation)
    pointer = {'path': relative(OBSERVATION_PATH), 'sha256': sha(obs_raw),
               'path_base': str(SHARED),
               'status': STATUS, 'revision': 'v14', 'startup_sha256': STARTUP,
               'source_manifest_sha256': MANIFEST, 'configuration_sha256': CONFIG,
               'component_pins': 378, 'observations_are_not_acceptance': True}
    current = {'status': STATUS, 'updated_utc': updated, 'root': ready['root'],
        'startup_sha256': STARTUP, 'source_manifest_sha256': MANIFEST, 'configuration_sha256': CONFIG,
        'component_pins': 378, 'supervisor_pid': ready['main_pid'], 'gtk_pid': ready['gtk_pid'],
        'board_boot_id': spec['boot_id'], 'camera_pid': None, 'last_known_camera_pid': 260102,
        'current_observation': pointer, 'automatic_listening': True, 'wake_word_required': False,
        'conversation_mode': 'half_duplex', 'frontend_options': installed['business_options'],
        'physical_microphone_opened': True, 'physical_audio_played': None,
        'microphone_open': paused['listening']['microphone_open'], 'playing': paused['playing'],
        'last_observed_listening_enabled': False, 'last_observed_listening_state': 'PAUSED',
        'maintenance_pause_for_public_asr_test': True, 'current_live_state_claimed': False,
        'retention_enabled': True, 'following': False, 'pan_state': 'FAULT', 'pulse_us': None,
        **gates}
    outputs = {}

    def archive_ref(name):
        return {'path': relative(HERE / 'before' / name), 'sha256': sha(originals[name]),
                'scope': 'Exact full pre-update document; historical flags apply only to their recorded revision.'}

    def historic(value, name):
        previous = {k: copy.deepcopy(value[k]) for k in
            ('status', 'updated_utc', 'startup_sha256', 'source_manifest_sha256', 'component_pins',
             'supervisor_pid', 'gtk_pid', 'camera_pid', 'board_boot_id', 'verified_listening', 'response_latency') if k in value}
        previous['archive'] = archive_ref(name)
        value.setdefault('continuation_history', []).append(previous)
        if 'verified_listening' in value:
            value.setdefault('historical_verified_listening', []).append(copy.deepcopy(value['verified_listening']))
            value['verified_listening'] = None
        if 'response_latency' in value:
            value.setdefault('historical_response_latency', []).append(copy.deepcopy(value['response_latency']))
            value['response_latency'] = None
        value['updated_utc'] = updated
        value['status'] = STATUS
        value['current_observation'] = pointer
        value['verification_scope_notice'] = 'Current v14 is an installed/ready observation, not a new verified-listening receipt. Prior passed gates remain in explicit history/archive.'

    live_name = 'owner/integration/PRODUCTION_BUSINESS_LIVE.json'
    live = json.loads(originals[live_name].decode('utf-8-sig'))
    historic(live, live_name)
    live.update(copy.deepcopy(current))
    live['windows_model_owner'] = windows
    live['windows_endpoint'] = windows['endpoint']
    live['evidence'] = evidence
    live['evidence_digest'] = sha(encoded(evidence))
    live['listening_policy'] = {'automatic_on_ready': True, 'no_start_button_required': True,
        'wake_word_required': False, 'entry_mode': 'direct_speech', 'conversation_mode': 'half_duplex',
        'explicit_pause_persistence': 'v14_not_verified', 'cancel_current_turn_rearm': 'v14_not_verified',
        'actual_restart_pause_verified': False, 'cold_boot_listening_verified': False}
    outputs[live_name] = encoded(live)

    for name in ('owner/IMPLEMENTATION_STATE.json', 'owner/integration/RESUME_VERIFICATION.json',
                 'owner/integration/CHARACTER_SWITCH.json', 'owner/coordination/runtime_windows.json'):
        value = json.loads(originals[name].decode('utf-8-sig'))
        historic(value, name)
        if 'production' in value:
            production = value['production']
            production.update({k: copy.deepcopy(current[k]) for k in
                ('root', 'startup_sha256', 'source_manifest_sha256', 'configuration_sha256', 'component_pins',
                 'current_observation', 'physical_microphone_opened', 'physical_audio_acceptance_passed',
                 'operator_asr_acceptance_passed', 'operator_playback_acceptance_passed')})
            production['last_observed_ui_supervisor_pid'] = ready['main_pid']
            production['last_observed_gtk_pid'] = ready['gtk_pid']
            pid_fields = ('last_verified_ui_supervisor_pid', 'last_verified_gtk_pid', 'last_verified_camera_pid')
            production['historical_verified_processes'] = {'startup_sha256':
                json.loads(originals[name].decode('utf-8-sig'))['production']['startup_sha256'],
                **{k: production.get(k) for k in pid_fields}}
            for key in pid_fields:
                production[key] = None
            production['last_verified_pid_fields_revision'] = 'No current v14 listening verification; previous processes retained in historical_verified_processes'
            production['audio_played'] = None
        if 'production_business_live' in value:
            value['production_business_live'] = copy.deepcopy(live)
        if name.endswith('CHARACTER_SWITCH.json'):
            value.update(copy.deepcopy(current))
            value['listening'] = paused['listening']['enabled']
            value['historical_display'] = copy.deepcopy(value['display'])
            value['display'] = {'kind': 'native_yuki_egl', 'frames': paused['native']['frames'],
                'visible': paused['native']['visible'], 'target_fps': paused['native']['target_fps'],
                'observed_mono': paused['observed_mono'], 'live_state_claimed': False}
            value['current_pair_observation'] = 'Character/profile unchanged by v14; earlier paired-render receipt retained in historical fields.'
        if name.endswith('runtime_windows.json'):
            value['updated_at'] = updated
            value['production_UI_switch'].update({k: copy.deepcopy(current[k]) for k in
                ('root', 'startup_sha256', 'source_manifest_sha256', 'configuration_sha256', 'component_pins', 'current_observation')})
            value['production_UI_switch']['runtime'] = ready['root']
            value['production_business_cutover']['current_observation'] = pointer
            value['windows_model_owner'] = windows
        outputs[name] = encoded(value)

    name = 'owner/integration/dialogue_repair/STATUS.json'
    value = json.loads(originals[name].decode('utf-8-sig'))
    historic(value, name)
    value['historical_v10_bounded_listening'] = {
        'startup_sha256': json.loads(originals[name].decode('utf-8-sig'))['startup_sha256'],
        'archive': archive_ref(name), 'applies_to_current_v14': False}
    for key in ('observation', 'fixes', 'latest_human_confirmation', 'evidence', 'detail'):
        if key in value:
            value.setdefault('historical_v10_fields', {})[key] = value.pop(key)
    value.update(copy.deepcopy(current))
    value['main_pid'] = ready['main_pid']
    value['current_revision_acceptance'] = gates
    value['latest_human_feedback'] = observation['human_dialogue_window']['feedback']
    value['latest_memory_observation'] = {'evidence': evidence['memory_latest'], **memory(post)}
    value['later_capture_failure_count'] = runtime['capture_performance']['capture_failures']
    value['diagnostic_text_or_pcm_saved'] = False
    value['evidence'] = evidence
    outputs[name] = encoded(value)

    prose = (
        '- 当前为v14已安装/READY及实际观测，尚非本轮完整验收：板端入口%s；startup SHA %s，378份组件；source manifest SHA %s；config SHA %s。\n'
        '- v14 READY回执记录supervisor %s、GTK %s、boot %s；PID只代表该次观测，下次先实读。相机PID260102仅列为较旧同boot记录，不冒充本轮新核验。\n'
        '- 板端负责ASR、视觉、时间轴记忆、调度、播放及雪妃显示；Windows只运行现有27B/2048/120与OmniVoice16。权重仍在D:/AIModels；不恢复旧Windows业务写者。无唤醒词，READY后自动聆听；半双工，生成/播放期间不启插话采集，完整ACK后恢复。\n'
        '- automatic_listening=true是持久配置/已有READY记录，不是当前时刻正在录音的声明：最新保存观测为root公开ASR试验维护暂停，PAUSED/IDLE、pending=false、麦克风与播放关闭；恢复回执待root补。正式startup未变。\n'
        '- 现役配置：前端独立进程与采集进程、combined、前端1线程、capture nice -10、ASR3线程、dialogue_abc_v1；完整JSON验证/来源权限/播放ACK保持。静态安装与READY不等于控制、连续采集或长稳验收。\n'
        '- 真人仍反馈等待太久：三次短回合ASR约3.3–3.9秒、LLM约3.8–4.2秒、首音频入队约8.4–9.4秒；这是入队时间，不是扬声器首声。另保留一轮ASR15.8秒/入队21.6秒；后续未控输入长度一轮ASR6.59秒/LLM4.95秒/入队12.76秒，不作配对结论。\n'
        '- 小样本公共名字ABBA仅4次模型调用，中位模型用时约降低19%%；不能外推到整机、真人等待或听感。\n'
        '- 初始约187秒记忆观测：有效摘要287→298、积压869→858、视觉618→607；最新观测摘要361/积压927/视觉592，worker完成90/丢弃10、最近16任务13提交3取消、streak0。新对话入流后总积压增大；取消/丢弃不等于删除正文，局部视觉推进不代表全库健康。\n'
        '- 初始63秒真人采样内无采集失败/GUI故障；较长后续已有1次pcm_input_queue_overflow、GUI故障0，worker当时74/6。不得沿用初始0次扩展为长期稳定。跟随false、机械FAULT/null安全边界保留。\n'
        '- v14暂停/恢复/取消控制尚未通过初始等待；缺少本轮连续静音采集/优先级作用域、冷启动/暂停重启、扬声器首声及多小时长稳验收。旧v10/v12/v13控制与连续采集回执仅历史，不作v14通过。update_verified_state.py严格门槛保持，未运行--apply。\n'
        '- 本次仅依据已保存metadata修正接续，未访问设备、模型或业务库，未改生产/候选代码。完整当前关联见%s；改前原字节与一致性记录见%s。\n'
    ) % (ready['root'], STARTUP, MANIFEST, CONFIG, ready['main_pid'], ready['gtk_pid'], spec['boot_id'],
         'deliverables/2026-10-30_board_owner/integration/dialogue_repair/current_observation_v14.json',
         'deliverables/2026-10-30_board_owner/integration/dialogue_repair/docs_state_v14/')

    def replace_block(raw, tag, body, old_title):
        open_tag = ('<!-- ' + tag + ' -->').encode()
        close_tag = ('<!-- /' + tag + ' -->').encode()
        pattern = re.compile(re.escape(open_tag) + b'(.*?)' + re.escape(close_tag), re.S)
        matches = list(pattern.finditer(raw))
        assert len(matches) == 1, tag
        match = matches[0]
        old_inner = match.group(1)
        archive_tag = 'archived-' + tag + '-v10-' + sha(match.group(0))[:12]
        inserted = (open_tag + b'\n' + body.encode('utf-8') + close_tag +
            ('\n\n<!-- ' + archive_tag + ' -->\n' + old_title + '\n').encode('utf-8') +
            old_inner + ('\n<!-- /' + archive_tag + ' -->').encode())
        result = raw[:match.start()] + inserted + raw[match.end():]
        assert old_inner in result and raw[match.end():] in result
        return result

    for name in ('project/AGENTS.md', 'analysis/README.md'):
        outputs[name] = replace_block(originals[name], 'board-business-live-20261030', prose,
            '以下旧现役段逐字保留为历史，仅适用于其原startup；以上v14当前观测不继承旧验收。')
    outputs['analysis/README.md'] = replace_block(outputs['analysis/README.md'], 'performance-dialogue-plan-20261031',
        '- [性能与对话平衡优化方案（2026-10-31）](性能与对话平衡优化方案_20261031.txt)：保留为基于v10实测的阶段性规划；现役已到v14。哪些改动已部署、仍有哪些缺口，以下方当前观测与回执关联为准。\n',
        '以下为该规划原先的阶段说明，逐字保留为历史：')
    readme_body = ('当前正式部署为v14：板端负责业务与存储，Windows仅现有27B/OmniVoice推理。'
        '雪妃形象及人格保持；无唤醒词，自动聆听，半双工。现役378份组件，startup `' + STARTUP + '`。\n\n'
        '自动聆听为持久选择及已有READY记录；最新保存状态是公开ASR试验维护暂停（PAUSED/IDLE、pending=false、麦克风及播放关闭），不声称当前时刻正聆听，待root恢复回执。\n\n'
        '真人仍反馈等待太久：短回合ASR约3.3–3.9秒、LLM约3.8–4.2秒、首音频入队约8.4–9.4秒，未测扬声器首声。'
        '后续有1次采集溢出，未完成v14控制及长稳验收。小样本模型约19%的提速不代表端到端已达标；'
        '视觉摘要局部推进也不代表全库健康，最新摘要361/总积压927。\n\n'
        '以[当前观测](deliverables/2026-10-30_board_owner/integration/dialogue_repair/current_observation_v14.json)和'
        '[接续状态](deliverables/2026-10-30_board_owner/integration/dialogue_repair/STATUS.json)为准。'
        '旧v10/v12/v13回执及下文早期“尚未迁移”等保留为各自历史，不能当作现役验收。权重仍在D盘。\n')
    outputs['project/README.md'] = replace_block(originals['project/README.md'], 'dialogue-current-20261031', readme_body,
        '以下为旧v10当前段的完整原文，已转为历史：')
    continuation_name = 'owner/板端业务正式接管与实测接续_20261030.txt'
    outputs[continuation_name] = ('v14接续：实际已安装/READY；等待过长及控制/长稳仍未验收。\n\n' + prose +
        '\n以下完整保留更新前记录，旧版本通过项不适用于v14：\n\n').encode('utf-8') + originals[continuation_name]

    before_manifest = {name: {'target': relative(TARGETS[name]), 'sha256': sha(raw), 'bytes': len(raw),
        'archive': relative(HERE / 'before' / name)} for name, raw in originals.items()}
    plan = {'status': 'DOCS_OBSERVATION_UPDATE_ONLY', 'updated_utc': updated, 'before': before_manifest,
            'after': {name: {'target': relative(TARGETS[name]), 'sha256': sha(raw), 'bytes': len(raw)} for name, raw in outputs.items()},
            'current_observation': pointer, 'strict_updater_modified_or_called': False,
            'production_or_candidate_source_modified': False}
    if not apply:
        print(json.dumps({'status': 'DRY_RUN', 'targets': list(TARGETS), 'observation_sha256': sha(obs_raw)}, ensure_ascii=False))
        return

    assert not OBSERVATION_PATH.exists(), 'Do not overwrite another current observation.'
    for path, raw in evidence_raw.items():
        assert path.read_bytes() == raw, 'Evidence changed during preparation: ' + relative(path)
    for name, path in TARGETS.items():
        assert path.read_bytes() == originals[name], 'Document changed during preparation: ' + name
    for name, raw in originals.items():
        archived = HERE / 'before' / name
        archived.parent.mkdir(parents=True, exist_ok=True)
        assert not archived.exists()
        archived.write_bytes(raw)
        assert archived.read_bytes() == raw
    (HERE / 'before_manifest.json').write_bytes(encoded(before_manifest))
    (HERE / 'plan.json').write_bytes(encoded(plan))
    OBSERVATION_PATH.write_bytes(obs_raw)
    written = []
    try:
        for name, raw in outputs.items():
            path = TARGETS[name]
            assert path.read_bytes() == originals[name], 'Document changed before write: ' + name
            temporary = path.with_name(path.name + '.v14-doc-update.tmp')
            assert not temporary.exists()
            temporary.write_bytes(raw)
            os.replace(temporary, path)
            written.append(name)
            assert path.read_bytes() == raw
    except BaseException:
        for name in reversed(written):
            if TARGETS[name].read_bytes() == outputs[name]:
                TARGETS[name].write_bytes(originals[name])
        raise
    journal = {'status': 'APPLIED_DOCUMENT_OBSERVATION_ONLY', 'updated_utc': updated,
        'modified_existing_documents': len(written), 'before_manifest_sha256': sha(encoded(before_manifest)),
        'plan_sha256': sha(encoded(plan)), 'current_observation_sha256': sha(obs_raw),
        'strict_updater_sha256_unchanged': sha(updater.read_bytes()) == evidence['strict_updater_not_executed']['sha256'],
        'all_before_files_byte_exact': all((HERE / 'before' / n).read_bytes() == r for n, r in originals.items()),
        'no_v14_acceptance_promoted': all(v is False for v in gates.values())}
    (HERE / 'journal.json').write_bytes(encoded(journal))
    print(json.dumps(journal, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true')
    main(parser.parse_args().apply)
