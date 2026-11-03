"""One-shot, local metadata/document continuation update. No runtime imports or IO."""
import copy
import datetime
import hashlib
import json
from pathlib import Path
import re

BASE = Path(r'E:\Win共享文件')
PROJECT = BASE / '语音共享文件'
ANALYSIS = BASE / '语言模型分析'
OWNER = PROJECT / 'deliverables/2026-10-30_board_owner'
INTEGRATION = OWNER / 'integration'
REPAIR = INTEGRATION / 'dialogue_repair'
HERE = REPAIR / 'docs_state_v16'
V16 = REPAIR / 'paraformer_small_validation/v16_evidence'
STARTUP = 'bf6cdd70768ea5fac4e5be874a387f444c0834d67db5e7a2a744671d9019d63c'
MANIFEST = 'e488f45660e78904d04ba57fe4210e2bcf9eeffa6282219096e9d7b6115df718'
CONFIG = '8c35161e766c53728c75c592a074845e35e01502e8438aaf649b4a8e078a6101'
STATUS = 'V16_SMALL_ASR_READY_USER_PAUSED_HUMAN_WAITING_UNVERIFIED'
NOW = datetime.datetime.now(datetime.timezone.utc).isoformat()
TARGETS = {
    'project_AGENTS': PROJECT / 'AGENTS.md',
    'project_README': PROJECT / 'README.md',
    'analysis_README': ANALYSIS / 'README.md',
    'dialogue_STATUS': REPAIR / 'STATUS.json',
    'implementation': OWNER / 'IMPLEMENTATION_STATE.json',
    'owner_continuation': OWNER / '板端业务正式接管与实测接续_20261030.txt',
    'performance_plan': REPAIR / '板端性能分配与优化计划.txt',
    'analysis_performance_plan': ANALYSIS / '性能与对话平衡优化方案_20261031.txt',
    'production_live': INTEGRATION / 'PRODUCTION_BUSINESS_LIVE.json',
    'resume_verification': INTEGRATION / 'RESUME_VERIFICATION.json',
    'character_switch': INTEGRATION / 'CHARACTER_SWITCH.json',
    'windows_coordination': OWNER / 'coordination/runtime_windows.json',
}

def sha(b):
    return hashlib.sha256(b).hexdigest()

def dump(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode('utf-8')

def read_json(path):
    return json.loads(path.read_bytes())

def ref(path):
    b = path.read_bytes()
    return {'path': path.relative_to(BASE).as_posix(), 'path_base': str(BASE),
            'sha256': sha(b), 'bytes': len(b)}

def save_new(path, b):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as f:
        f.write(b)

if (HERE / 'HANDOFF.json').exists() or (HERE / 'before_manifest.json').exists():
    raise RuntimeError('one_shot_already_started')

installed = read_json(V16 / 'installed.json')
ready = read_json(V16 / 'ready.json')
spec = read_json(V16 / 'spec.json')
mapping = read_json(V16 / 'source_mapping.json')
initial = read_json(V16 / 'observation.json')
latest = read_json(REPAIR / 'v16_memory_code.json')
screen = read_json(REPAIR / 'paraformer_small_validation/RESULT_HANDOFF.json')
allocation = read_json(REPAIR / 'frontend_allocation_candidate/public_probe/DECISION.json')
assert installed['startup_sha256'] == spec['startup_sha256'] == mapping['startup_sha256'] == initial['startup_sha256'] == latest['startup_sha256'] == STARTUP
assert installed['configuration_sha256'] == spec['configuration_sha256'] == CONFIG
assert installed['source_manifest_sha256'] == mapping['source_manifest_sha256'] == MANIFEST
assert installed['component_pins'] == spec['component_pins'] == len(mapping['component_pins']) == 378
assert mapping['status'] == 'V16_SOURCE_AND_SERVICE_VERIFIED'
assert ready['status'] == 'PRODUCTION_BOARD_BUSINESS_READY'
assert latest['listening']['state'] == 'PAUSED' and latest['listening']['enabled'] is False
assert latest['listening']['microphone_open'] is False and latest['phase'] == 'IDLE' and latest['playing'] is False
assert latest['memory']['completed'] == 29 and latest['memory']['discarded'] == 18
assert latest['memory_retry']['failure_streak'] == 0 and not latest['memory']['error']['present']
assert initial['memory']['completed'] == 11 and initial['memory']['discarded'] == 10
assert initial['memory_retry']['failure_streak'] == 5 and initial['memory_retry']['last_delay_seconds'] == 48.0
assert allocation['status'] == 'DO_NOT_DEPLOY_ABBA_INCOMPLETE_AFTER_OVERFLOW'

originals = {k: p.read_bytes() for k, p in TARGETS.items()}
before = []
for k, p in TARGETS.items():
    archived = HERE / 'before' / p.relative_to(BASE)
    save_new(archived, originals[k])
    before.append({'key': k, 'path': p.relative_to(BASE).as_posix(),
                   'archive': archived.relative_to(BASE).as_posix(),
                   'sha256': sha(originals[k]), 'bytes': len(originals[k])})
save_new(HERE / 'before_manifest.json', dump({'schema': 'aura.docs-original-bytes.v1', 'files': before}))

source_paths = [V16 / n for n in ['installed.json', 'ready.json', 'spec.json', 'source_mapping.json', 'observation.json']]
source_paths += [REPAIR / 'v16_memory_code.json', REPAIR / 'paraformer_small_validation/RESULT_HANDOFF.json',
                 REPAIR / 'frontend_allocation_candidate/public_probe/DECISION.json']
sources = []
for f in source_paths:
    dest = HERE / 'evidence' / f.relative_to(REPAIR)
    save_new(dest, f.read_bytes())
    sources.append({'original': ref(f), 'sealed_copy': ref(dest)})
evidence = {f.name: ref(f) for f in source_paths}

notice = ('v16 source/installation/READY verified; user manual PAUSED is preserved. '
          'Public 16-decode Small screening is not new human waiting/accuracy acceptance. '
          'No v16 continuous capture, controls or long-run pass is inferred from v15. '
          'Initial memory retries recovered at a later saved observation; root cause and whole-store health remain unverified.')
acceptance = {k: False for k in ['continuous_capture_passed', 'priority_scope_passed', 'controls_verified',
    'short_capture_verified', 'pause_resume_disk_preference_verified', 'cancel_rearm_verified',
    'owned_arecord_release_verified', 'model_worker_reused_verified', 'operator_asr_acceptance_passed',
    'operator_playback_acceptance_passed', 'physical_audio_acceptance_passed',
    'full_physical_dialogue_acceptance', 'audible_first_sound_measured', 'cold_boot_listening_verified',
    'actual_restart_pause_verified', 'multi_hour_stability_verified', 'controlled_whole_board_cpu_reduction_proven']}
acceptance.update({'source_and_service_verified': True, 'installation_ready_verified': True,
                   'user_manual_pause_preserved': True, 'small_asr_production_selected': True,
                   'audio_continuity_user_confirmed': None, 'waiting_improvement': None,
                   'false_means_not_verified_for_v16_not_failed_test': True})
observation = {
    'schema': 'aura.current-runtime-observation.v1', 'revision': 'v16', 'status': STATUS, 'updated_utc': NOW,
    'root': spec['target'], 'startup_sha256': STARTUP, 'source_manifest_sha256': MANIFEST,
    'configuration_sha256': CONFIG, 'component_pins': 378, 'board_boot_id': spec['boot_id'],
    'source_observed_mono': mapping['observed_mono'], 'observed_mono': latest['observed_mono'],
    'supervisor_pid': ready['main_pid'], 'supervisor_birth_ticks': mapping['supervisor']['birth_ticks'],
    'gtk_pid': ready['gtk_pid'], 'camera_pid': mapping['camera']['pid'], 'camera_birth_ticks': mapping['camera']['birth_ticks'],
    'state_is_saved_observation_not_live_claim': True, 'phase': latest['phase'], 'playing': latest['playing'],
    'automatic_listening_startup_option': True, 'listening': latest['listening'],
    'user_manual_pause_confirmed': True, 'automatic_listening_restored': False,
    'frontend_options': installed['business_options'], 'retention': latest['retention'],
    'runtime_faults': latest['runtime_faults'],
    'capture': {'snapshot_available': latest['safe_capture']['snapshot_available'],
                'counters': latest['safe_capture']['counters'], 'failure_count': None,
                'failure_count_available': False, 'v16_zero_counters_prove_v15_capture_fixed': False,
                'notice': 'Paused since startup; no current capture snapshot/performance count. v15 failures remain historical.'},
    'memory': {'initial_observed_mono': initial['observed_mono'], 'initial_worker': initial['memory'],
               'initial_retry': initial['memory_retry'], 'latest_observed_mono': latest['observed_mono'],
               'latest_worker': latest['memory'], 'latest_retry': latest['memory_retry'],
               'clock': {k: latest['clock'][k] for k in ['safe_for_compaction', 'verified_age_seconds'] if k in latest['clock']},
               'counters_are_process_local': True, 'transient_error_recovered_observed': True,
               'original_error_enum_directly_observed': False, 'root_cause_confirmed': False,
               'whole_store_health_verified': False, 'discarded_means_source_body_deleted': False},
    'public_small_screening': {'reference': ref(REPAIR / 'paraformer_small_validation/RESULT_HANDOFF.json'),
               'unique_public_wavs': 8, 'rounds_each': 2, 'decodes_each': 16, 'threads_each': 3,
               'old_mean_decode_ms': screen['engines']['paraformer']['total']['wall_mean_ms'],
               'small_mean_decode_ms': screen['engines']['paraformer_small']['total']['wall_mean_ms'],
               'background_changed': True, 'human_gold': False, 'causal_percentage_claimed': False,
               'user_accepts_homophones': True, 'new_human_waiting_acceptance': False,
               'name_character_accuracy_still_limited': True, 'production_selection_now_v16': True,
               'historical_screening_receipt_not_rewritten_as_acceptance': True},
    'windows': {'changed_by_v16': False, 'role': 'fixed_27b_and_omnivoice_inference_only',
                'llm_context': 2048, 'llm_output_budget': 120, 'omnivoice_steps': 16,
                'llm_weights_location': 'D:/AIModels', 'fresh_host_health_called_by_doc_update': False},
    'pending': {'frontend_allocation_deployed': False, 'phasehold_deployed': False,
                'allocation_decision': ref(REPAIR / 'frontend_allocation_candidate/public_probe/DECISION.json'),
                'allocation_abba_complete': False, 'allocation_measured_gain_claimed': False,
                'visual_speaker_routing_fixes_accepted_by_this_receipt': False},
    'current_revision_acceptance': acceptance, 'verification_scope_notice': notice,
    'evidence': evidence, 'document_update_actions': {'devices_models_private_dbs_accessed': False,
                'production_or_candidate_source_changed': False, 'strict_verified_state_updater_run': False},
}
canonical = REPAIR / 'current_observation_v16.json'
save_new(canonical, dump(observation))
current = dict(ref(canonical), status=STATUS, revision='v16', startup_sha256=STARTUP,
               source_manifest_sha256=MANIFEST, configuration_sha256=CONFIG, component_pins=378,
               observations_are_not_full_acceptance=True)

summary = (
    'v16 当前接续：Paraformer Small 已生产接入并 READY，保留用户手动 PAUSED。\n\n'
    f'运行根 {spec["target"]}；startup SHA {STARTUP}；manifest SHA {MANIFEST}；378 份组件；config SHA {CONFIG}。\n'
    f'保存观测 mono{latest["observed_mono"]}：IDLE/no playing，enabled=false、PAUSED、mic=false，GUI 故障0；supervisor{ready["main_pid"]}/GTK{ready["gtk_pid"]}，camera260102/birth784437，同boot {spec["boot_id"]}。下次必须现读，不能写已恢复自动监听。\n'
    'Small/3线程已选中；8个公开合成WAV各2轮的16次decode均值 old5.789s→Small2.057s 是背景有变化的筛选，非真人首声、准确率gold或端到端提速验收。用户接受同音字，姓名字形仍有限制；v16真人等待尚未重新验收。\n'
    'Windows保持现有27B/2048/120和OmniVoice16，LLM权重仍D:/AIModels；板端业务、存储、显示和统一五分钟时间轴不改。combined前端1线程/capture nice-10/原8帧保留；每包新鲜权限检查与完整ACK保留。\n'
    '新进程armed/speech/submitted=0且capture snapshot不可用，不能证明v15采集故障已修复；v15连续采集/控制通过仅属旧startup，不能移作v16验收。\n'
    '早期mono56240.522488149 memory completed11/discarded10、streak5、48s退避、脱敏error other；后续mono56590.97092797已完成29/丢弃18、error清空、streak0、clock safe_compaction=true。只证明后续恢复推进，未直接观测原错误枚举，原因和全库健康仍未确认；丢弃任务不等于删除源正文。\n'
    'frontend allocation候选A1通过、B1在原8帧队列pcm_input_queue_overflow，B2/A2停止，未部署且无收益结论；phasehold未部署。视觉/声纹路由后续修订不纳入本回执。\n'
    '接续入口 current_observation_v16.json、paraformer_small_validation/v16_evidence 和 docs_state_v16/HANDOFF.json。本次接续文档修订只读封存metadata，未访问设备/模型/私库，未修改生产或候选代码；root此前实机发布与公开试验记录保留。\n'
)
save_new(HERE / 'current_note.txt', summary.encode('utf-8'))

def replace_block(raw, marker, body):
    start = ('<!-- ' + marker + ' -->').encode()
    end = ('<!-- /' + marker + ' -->').encode()
    assert raw.count(start) == raw.count(end) == 1, marker
    a = raw.index(start); b = raw.index(end, a) + len(end)
    old = raw[a:b]
    archive_marker = 'archived-' + marker + '-pre-v16-' + sha(old)[:12]
    archived = ('\n\n<!-- ' + archive_marker + ' -->\n以下旧段完整原字节保留为历史，仅适用于原startup。\n').encode('utf-8') + old + ('\n<!-- /' + archive_marker + ' -->').encode()
    return raw[:a] + start + b'\n' + body.encode('utf-8') + b'\n' + end + archived + raw[b:]

agent_body = '\n'.join('- ' + x for x in summary.strip().split('\n') if x)
readme_body = ('现役 v16（378组件）已生产接入 Paraformer Small/3线程并 READY；保留用户手动 `PAUSED`，enabled=false、mic=false。'
    '公开16次 decode 均值5.789s→2.057s只作筛选；用户接受同音字，真人等待和v16连续采集尚未重新验收。\n\n'
    '早期记忆streak5/48s退避，后续29完成/18丢弃、error清空/streak0；原因和全库健康未确认。新进程capture计数0不证明旧故障修复。'
    'Windows27B/OmniVoice16及D盘权重不变；allocation/phasehold未部署。详见[当前观测](deliverables/2026-10-30_board_owner/integration/dialogue_repair/current_observation_v16.json)、'
    '[接续简记](deliverables/2026-10-30_board_owner/integration/dialogue_repair/docs_state_v16/current_note.txt)和[状态](deliverables/2026-10-30_board_owner/integration/dialogue_repair/STATUS.json)。旧正文按原字节归档。')
updates = {}
updates['project_AGENTS'] = replace_block(originals['project_AGENTS'], 'board-business-live-20261030', agent_body)
updates['project_README'] = replace_block(originals['project_README'], 'dialogue-current-20261031', readme_body)
analysis_readme = replace_block(originals['analysis_README'], 'performance-dialogue-plan-20261031',
    '- [性能与对话平衡优化方案](性能与对话平衡优化方案_20261031.txt)：原v10阶段规划全文保留；现役v16 Small，当前暂停、尚无新真人等待验收，按当前观测区分已部署与候选。')
analysis_readme = replace_block(analysis_readme, 'idle-cpu-v15-report-20261031',
    '- [v15空闲CPU观测历史报告](板端空闲CPU减负与v15当前观测_20261031.txt)：保留原v15数据，不能当v16通过或最新状态。')
if b'<!-- board-business-live-20261030 -->' in analysis_readme:
    analysis_readme = replace_block(analysis_readme, 'board-business-live-20261030', agent_body)
analysis_prefix = ('<!-- current-v16-20261031 -->\n- [v16当前观测](../语音共享文件/deliverables/2026-10-30_board_owner/integration/dialogue_repair/current_observation_v16.json)与'
    '[接续简记](../语音共享文件/deliverables/2026-10-30_board_owner/integration/dialogue_repair/docs_state_v16/current_note.txt)：Small已生产接入且READY，用户手动PAUSED；公开筛选非新真人等待验收，记忆退避后恢复但原因未明。\n<!-- /current-v16-20261031 -->\n\n').encode('utf-8')
updates['analysis_README'] = analysis_prefix + analysis_readme
for key in ['owner_continuation', 'performance_plan', 'analysis_performance_plan']:
    updates[key] = summary.encode('utf-8') + b'\n\n' + '以下为此前各阶段原文，完整原字节保留为历史；不代表当前已部署或验收状态。\n\n'.encode('utf-8') + originals[key]

common = {'status': STATUS, 'updated_utc': NOW, 'current_revision': 'v16', 'root': spec['target'],
    'startup_sha256': STARTUP, 'source_manifest_sha256': MANIFEST, 'configuration_sha256': CONFIG,
    'component_pins': 378, 'board_boot_id': spec['boot_id'], 'supervisor_pid': ready['main_pid'],
    'gtk_pid': ready['gtk_pid'], 'camera_pid': mapping['camera']['pid'], 'camera_birth_ticks': mapping['camera']['birth_ticks'],
    'automatic_listening': True, 'wake_word_required': False, 'conversation_mode': 'half_duplex',
    'frontend_options': installed['business_options'], 'retention_enabled': True,
    'physical_microphone_opened': False, 'microphone_open': False, 'physical_audio_played': False,
    'playing': False, 'last_observed_listening_enabled': False, 'last_observed_listening_state': 'PAUSED',
    'user_manual_pause_preserved': True, 'automatic_listening_restored': False,
    'maintenance_pause_for_public_asr_test': False, 'current_live_state_claimed': False,
    'current_observation': current, 'verification_scope_notice': notice,
    'current_revision_acceptance': acceptance, 'evidence': evidence,
    'audio_continuity_user_confirmed': None, 'waiting_improvement': None,
    'latest_memory_runtime_counters': {'process_revision': 'v16', 'observed_mono': latest['observed_mono'],
           'completed': 29, 'discarded': 18, 'failure_streak': 0, 'error_present': False,
           'counters_are_process_local': True, 'whole_store_health_verified': False},
    'memory_retry_history': observation['memory'], 'later_capture_failure_count': None,
    'v16_zero_capture_counters_prove_v15_fixed': False,
    'frontend_allocation_deployed': False, 'phasehold_deployed': False,
}
common.update({k: v for k, v in acceptance.items() if k.endswith('_passed') or k.endswith('_verified') or k in ['full_physical_dialogue_acceptance', 'audible_first_sound_measured']})

def update_object(d):
    d.update(copy.deepcopy(common))
    for k in ['main_pid', 'last_observed_ui_supervisor_pid', 'last_verified_ui_supervisor_pid']:
        if k in d: d[k] = ready['main_pid']
    for k in ['last_observed_gtk_pid', 'last_verified_gtk_pid']:
        if k in d: d[k] = ready['gtk_pid']
    for k in ['last_known_camera_pid', 'last_observed_camera_pid', 'last_verified_camera_pid']:
        if k in d: d[k] = mapping['camera']['pid']
    if 'last_observed_camera_birth_ticks' in d: d['last_observed_camera_birth_ticks'] = mapping['camera']['birth_ticks']
    if 'last_verified_pid_fields_revision' in d: d['last_verified_pid_fields_revision'] = 'v16_source_mapping'
    if 'frontend_worker_pid' in d: d['frontend_worker_pid'] = None
    if 'audio_played' in d: d['audio_played'] = False
    if 'microphone_or_playback_started' in d: d['microphone_or_playback_started'] = False
    if 'audio_played_evidence_scope' in d: d['audio_played_evidence_scope'] = 'none_since_v16_startup_user_paused'
    if 'following' in d: d['following'] = None
    if 'pan_state' in d: d['pan_state'] = None
    if 'pulse_us' in d: d['pulse_us'] = None
    if 'listening' in d: d['listening'] = False
    if 'listening_policy' in d: d['listening_policy'] = {'entry_mode': 'direct_speech', 'wake_word_required': False, 'conversation_mode': 'half_duplex', 'manual_pause_preserved': True}
    if 'evidence_digest' in d: d['evidence_digest'] = sha(dump(evidence))
    if 'last_detailed_memory_observation' in d: d['last_detailed_memory_observation'] = {'current_v16_detailed_store_snapshot_available': False, 'runtime_only': observation['memory']}
    d['verified_listening'] = {'revision': 'v16', 'startup_sha256': STARTUP, 'status': 'NOT_REVALIDATED_USER_PAUSED',
         'continuous_capture_passed': False, 'priority_scope_passed': False, 'controls_verified': False, 'current_observation': current}
    d['response_latency'] = {'revision': 'v16', 'startup_sha256': STARTUP, 'dialogue_output_format': 'dialogue_abc_v1',
         'ordinary_reply_sentence_streaming': True, 'audio_continuity_user_confirmed': None,
         'waiting_improvement': None, 'audible_first_sound_measured': False, 'new_human_waiting_acceptance': False,
         'public_screening': observation['public_small_screening'], 'current_observation': current}

for key in ['dialogue_STATUS', 'implementation', 'production_live', 'resume_verification', 'character_switch', 'windows_coordination']:
    d = json.loads(originals[key])
    original_owner = copy.deepcopy(d.get('windows_model_owner'))
    hist = {'superseded_by_revision': 'v16', 'superseded_by_startup_sha256': STARTUP,
            'original_bytes_archive': next(row for row in before if row['key'] == key),
            'previous_status': d.get('status'), 'previous_current_observation': copy.deepcopy(d.get('current_observation'))}
    d.setdefault('continuation_history', []).append(hist)
    update_object(d)
    for field in ['production', 'production_business_live']:
        if isinstance(d.get(field), dict): update_object(d[field])
    if key == 'character_switch':
        d['current_pair_observation'] = 'Character/persona unchanged by v16; Small ASR selected, no new render performance acceptance.'
    if key == 'dialogue_STATUS':
        d['latest_human_feedback'] = {'user_accepts_homophones': True, 'user_manual_pause_confirmed': True,
              'v16_human_waiting_feedback_available': False, 'previous_continuity_feedback_is_historical': True,
              'full_physical_dialogue_acceptance': False}
        d['feedback_turn_timing_association'] = 'not_obtained_for_v16'
    if key == 'windows_coordination':
        d['updated_at'] = NOW
        for field in ['production_UI_switch', 'production_business_cutover']:
            if isinstance(d.get(field), dict):
                d[field].update({'state': STATUS, 'current_revision': 'v16', 'updated_utc': NOW,
                       'startup_sha256': STARTUP, 'source_manifest_sha256': MANIFEST,
                       'configuration_sha256': CONFIG, 'component_pins': 378,
                       'current_observation': current, 'physical_microphone_opened': False, 'physical_audio_played': False})
        assert d.get('windows_model_owner') == original_owner
    updates[key] = dump(d)

# Compare-and-swap before each write: other agents' work is never overwritten.
for key, p in TARGETS.items():
    assert p.read_bytes() == originals[key], 'concurrent_document_change:' + key
for key, p in TARGETS.items():
    p.write_bytes(updates[key])

checks = []
def check(name, value):
    checks.append({'check': name, 'passed': bool(value)})
    assert value, name

for row in before:
    check('archive_exact:' + row['key'], sha((BASE / row['archive']).read_bytes()) == row['sha256'])
for row in sources:
    check('evidence_unchanged:' + Path(row['original']['path']).name,
          sha((BASE / row['original']['path']).read_bytes()) == row['original']['sha256'] == sha((BASE / row['sealed_copy']['path']).read_bytes()))
for key in ['dialogue_STATUS', 'implementation', 'production_live', 'resume_verification', 'character_switch', 'windows_coordination']:
    d = read_json(TARGETS[key])
    for field in [None] + [f for f in ['production', 'production_business_live'] if isinstance(d.get(f), dict)]:
        x = d if field is None else d[field]
        label = key + ':' + str(field)
        check('current_pins:' + label, x['startup_sha256'] == STARTUP and x['source_manifest_sha256'] == MANIFEST and x['configuration_sha256'] == CONFIG and x['component_pins'] == 378)
        check('paused_not_restored:' + label, not x['microphone_open'] and x['last_observed_listening_state'] == 'PAUSED' and not x['automatic_listening_restored'])
        check('no_inherited_acceptance:' + label, not x['controls_verified'] and not x['continuous_capture_passed'] and not x['full_physical_dialogue_acceptance'])
        check('canonical_ref:' + label, x['current_observation']['sha256'] == sha(canonical.read_bytes()))
        check('no_capture_fix_claim:' + label, x['later_capture_failure_count'] is None and not x['v16_zero_capture_counters_prove_v15_fixed'])
        check('memory_recovery_with_limits:' + label, x['latest_memory_runtime_counters']['completed'] == 29 and not x['latest_memory_runtime_counters']['whole_store_health_verified'] and not x['memory_retry_history']['root_cause_confirmed'])
for key in ['owner_continuation', 'performance_plan', 'analysis_performance_plan']:
    check('historic_full_bytes_suffix:' + key, TARGETS[key].read_bytes().endswith(originals[key]))
for key in ['project_AGENTS', 'project_README', 'analysis_README']:
    raw = TARGETS[key].read_bytes()
    markers = re.findall(rb'<!-- ([^\n]*?) -->', raw)
    old = originals[key]
    check('no_new_unbalanced_markers:' + key, all(
        raw.count(b'<!-- ' + m + b' -->') - raw.count(b'<!-- /' + m + b' -->')
        == old.count(b'<!-- ' + m + b' -->') - old.count(b'<!-- /' + m + b' -->')
        for m in markers if not m.startswith(b'/')))
check('windows_owner_unchanged', read_json(TARGETS['windows_coordination'])['windows_model_owner'] == json.loads(originals['windows_coordination'])['windows_model_owner'])
check('public_means_are_screening', observation['public_small_screening']['old_mean_decode_ms'] == 5788.5254375 and observation['public_small_screening']['small_mean_decode_ms'] == 2056.501 and not observation['public_small_screening']['new_human_waiting_acceptance'])
check('memory_initial_and_recovered_both_retained', observation['memory']['initial_retry']['failure_streak'] == 5 and observation['memory']['latest_retry']['failure_streak'] == 0)
check('runtime_source_inputs_untouched', all(sha((BASE / row['original']['path']).read_bytes()) == row['original']['sha256'] for row in sources))
save_new(HERE / 'consistency.json', dump({'status': 'PASS', 'checks': checks, 'checks_passed': len(checks),
    'devices_models_private_databases_accessed': False, 'production_or_candidate_code_changed': False}))
handoff = {'schema': 'aura.docs-state-handoff.v1', 'status': 'V16_DOCUMENT_CONTINUATION_FROZEN',
    'revision': 'v16', 'created_utc': NOW, 'startup_sha256': STARTUP, 'source_manifest_sha256': MANIFEST,
    'configuration_sha256': CONFIG, 'component_pins': 378, 'current_observation': ref(canonical),
    'before_manifest': ref(HERE / 'before_manifest.json'), 'consistency': ref(HERE / 'consistency.json'),
    'current_note': ref(HERE / 'current_note.txt'), 'updater': ref(Path(__file__)),
    'changed_documents': [dict(ref(p), key=k) for k, p in TARGETS.items()], 'evidence': sources,
    'checks_passed': len(checks), 'strict_verified_state_updater_run': False,
    'scope': 'documents_and_already_saved_public_metadata_only',
    'historical_bytes_preserved': True, 'device_model_or_private_database_actions': False,
    'new_source_or_configuration_deployed': False, 'verification_scope_notice': notice}
save_new(HERE / 'HANDOFF.json', dump(handoff))
print(json.dumps({'status': handoff['status'], 'checks_passed': len(checks),
    'handoff_sha256': sha((HERE / 'HANDOFF.json').read_bytes()),
    'current_observation_sha256': sha(canonical.read_bytes()), 'documents_updated': len(TARGETS)}, ensure_ascii=True))
