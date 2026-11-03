"""One-shot local continuation documents; no runtime imports or device access."""
import copy
import datetime
import hashlib
import json
from pathlib import Path
import re

BASE = Path(r'E:\Win共享文件')
PROJECT = BASE / '语音共享文件'
OWNER = PROJECT / 'deliverables/2026-10-30_board_owner'
INTEGRATION = OWNER / 'integration'
REPAIR = INTEGRATION / 'dialogue_repair'
HERE = REPAIR / 'docs_state_v17'
EVIDENCE = REPAIR / 'release_v17_candidate/v17_evidence'
STARTUP = '0cbc191b4bf9029b15a65ef15797e43e15459e06b88381025d28a2c9b573dd2a'
MANIFEST = '38a267a4f8d504803587c8be353452b146f1e232e926ac4e061a5e2832b33620'
CONFIG = 'd2511ee2b95f0ae9b2cbb18f16cde90719420d887e858926e8fd07a5c5b60013'
STATUS = 'V17_FEATURE_V3_ANIMATION_READY_USER_PAUSED_HUMAN_ACCEPTANCE_PENDING'
NOW = datetime.datetime.now(datetime.timezone.utc).isoformat()
def sha(b): return hashlib.sha256(b).hexdigest()
def load(p): return json.loads(p.read_bytes())
def dump(d): return (json.dumps(d, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
def put(p, b):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('xb') as f: f.write(b)
def ref(p):
    b = p.read_bytes()
    return dict(path=p.relative_to(BASE).as_posix(), path_base=str(BASE), sha256=sha(b), bytes=len(b))

if (HERE / 'before_manifest.json').exists(): raise RuntimeError('one_shot_already_started')
previous = load(REPAIR / 'docs_state_v16/HANDOFF.json')
targets = {row['key']: BASE / row['path'] for row in previous['changed_documents']}
assert len(targets) == 12
assert all(p.is_relative_to(BASE) for p in targets.values())
spec, ready, installed, mapping, observed = [load(EVIDENCE / n) for n in
    ['spec.json', 'ready.json', 'installed.json', 'source_mapping.json', 'observation.json']]
reason = load(REPAIR / 'memory_reason_candidate/actual_v17_ready.json')
visual_path = REPAIR / 'animation_thinking_collaboration/ROOT_VISUAL_REVIEW.json'
visual = load(visual_path)
preview_path = REPAIR / 'animation_thinking_collaboration/public_preview_actual_1793458551702278500/preview_result.json'
preview = load(preview_path)
feature_path = REPAIR / 'feature_trigger_collaboration/candidate_v3/HANDOFF.json'
feature = load(feature_path)
assert all(d['startup_sha256'] == STARTUP for d in [spec, installed, mapping, observed])
assert all(d['source_manifest_sha256'] == MANIFEST for d in [spec, installed, mapping])
assert all(d['configuration_sha256'] == CONFIG for d in [spec, installed, mapping])
assert spec['component_pins'] == installed['component_pins'] == len(mapping['component_pins']) == 379
assert mapping['status'] == 'V17_SOURCE_AND_SERVICE_VERIFIED' and ready['status'] == 'PRODUCTION_BOARD_BUSINESS_READY'
assert len(installed['source_files']) == 13 and all(mapping['component_pins'][k] == v for k, v in installed['source_files'].items())
assert observed['listening']['state'] == ready['listening_state'] == 'PAUSED'
assert observed['listening']['enabled'] is False and observed['listening']['microphone_open'] is False
assert reason['retry']['last_failure_code'] == 'candidate_rejected' and reason['summary']['stage'] == 'full_source_validation'
assert reason['summary']['error_class'] == 'CandidateRejected' and reason['summary']['rejection_reasons'] == ['observation_evidence_missing']
assert reason['worker']['completed'] == reason['worker']['discarded'] == reason['retry']['failure_streak'] == 1
assert reason['retry']['last_delay_seconds'] == 3 and all(v == 0 for v in reason['unknown_counts'].values())
assert visual['status'] == 'PUBLIC_CHARACTER_VISUAL_REVIEW_PASS' and preview['frames'] == 373
assert sha(preview_path.read_bytes()) == visual['preview_result_sha256'] and feature['source_files'] == 8
assert spec['native_library_sha256'] == installed['native_library_sha256'] == visual['overlay_pins']['tools/libaura_yuki.so']

originals = {k: p.read_bytes() for k, p in targets.items()}
before = []
for k, p in targets.items():
    archive = HERE / 'before' / p.relative_to(BASE)
    put(archive, originals[k])
    before.append(dict(key=k, original=ref(p), archive=ref(archive)))
put(HERE / 'before_manifest.json', dump(dict(schema='aura.docs-original-bytes.v1', files=before)))
source_paths = [EVIDENCE / n for n in ['spec.json', 'ready.json', 'installed.json', 'source_mapping.json', 'observation.json']]
source_paths += [REPAIR / 'memory_reason_candidate/actual_v17_ready.json', visual_path, preview_path, feature_path]
sources = []
for p in source_paths:
    q = HERE / 'evidence' / p.relative_to(REPAIR)
    put(q, p.read_bytes()); sources.append(dict(original=ref(p), sealed_copy=ref(q)))
evidence = {p.name if p.name != 'HANDOFF.json' else 'feature_v3_handoff': ref(p) for p in source_paths}

prior_obs = load(REPAIR / 'current_observation_v16.json')
obs = copy.deepcopy(prior_obs)
obs.update(revision='v17', status=STATUS, updated_utc=NOW, root=spec['target'],
    startup_sha256=STARTUP, source_manifest_sha256=MANIFEST, configuration_sha256=CONFIG,
    component_pins=379, board_boot_id=spec['boot_id'], source_observed_mono=mapping['observed_mono'],
    observed_mono=observed['observed_mono'], supervisor_pid=ready['main_pid'],
    supervisor_birth_ticks=mapping['supervisor']['birth_ticks'], gtk_pid=ready['gtk_pid'],
    gtk_birth_ticks=mapping['gtk']['birth_ticks'], camera_pid=mapping['camera']['pid'],
    camera_birth_ticks=mapping['camera']['birth_ticks'], phase=observed['phase'], playing=observed['playing'],
    listening=observed['listening'], retention=observed['retention'], runtime_faults=observed['runtime_faults'],
    native_library_sha256=spec['native_library_sha256'], character_pair_selection_sha256=spec['character_pair_selection_sha256'])
obs['frontend_options_source'] = 'Unchanged from v16; root v17 publication retains Small3/combined1/nice-10/raw8.'
obs['capture'] = dict(snapshot_available=False, counters=observed['safe_capture']['counters'], failure_count=None,
    failure_count_available=False, zero_new_process_counters_prove_old_capture_fixed=False,
    notice='Paused since startup; no current capture snapshot or v17 continuous acceptance.')
obs['memory'] = dict(observed_mono=reason['observed_mono'], worker=reason['worker'], retry=reason['retry'],
    summary=reason['summary'], clock=reason['clock'], unknown_counts=reason['unknown_counts'],
    current_rejection_class_captured=True, current_rejection='observation_evidence_missing',
    previous_redacted_error_causes_confirmed=False, whole_store_health_verified=False,
    rejected_task_means_source_deleted=False, counters_are_process_local=True,
    snapshot_atomicity_verified=False,
    interpretation='This observation captures candidate_rejected/full_source_validation/CandidateRejected/observation_evidence_missing. It does not establish that earlier operation_failed redactions had the same cause, or imply source deletion.')
obs['public_small_screening'].pop('production_selection_now_v16', None)
obs['public_small_screening'].update(production_selected_since_v16=True, current_asr='paraformer_small', current_asr_threads=3, new_human_waiting_acceptance=False)
obs['feature_v3'] = dict(deployed=True, files=8, source_handoff=ref(feature_path),
    actual_business_physical_acceptance=False, speaker_calibrated=False, automatic_profile_access=False)
obs['animation'] = dict(deployed=True, files=5, native_library_sha256=spec['native_library_sha256'],
    pure_character_visual_review_passed=True, reference=ref(visual_path), numeric_preview=ref(preview_path),
    states=9, frames=373, high_envelope_answer_mouth=3.40, thinking_eyes_closed=True, answer_eyes_open=True,
    pause_cancel_mouth_closed=True, physical_fps_acceptance=False, real_pcm_lipsync_acceptance=False,
    full_business_load_acceptance=False, human_dialogue_acceptance=False, preview_v1_v2_size_failures_preserved=True,
    v3_fixed_canvas_passed=True, v4_high_envelope_image_passed=True, new_multicomponent_motion_deployed=False)
obs['pending'].update(visual_speaker_routing_feature_v3_deployed=True,
    feature_v3_real_business_acceptance=False, new_multicomponent_motion_deployed=False)
obs['pending'].pop('visual_speaker_routing_fixes_accepted_by_this_receipt', None)
notice = ('v17 source/379 pins/installation/READY verified; manual PAUSED/micfalse preserved. '
    'Feature v3 and five animation files deployed; pure-character simulated visual preview passed, not physical FPS/voice/full-load acceptance. '
    'One evidence-preservation rejection captured; earlier redacted causes and whole-store health remain unverified. '
    'No fresh v17 human waiting, controls, continuous capture or long-run pass is inferred.')
obs['verification_scope_notice'] = notice
obs['current_revision_acceptance'].update(feature_v3_source_deployed=True, animation_visual_preview_passed=True,
    feature_v3_physical_acceptance=False, native_physical_fps_acceptance=False,
    small_asr_production_selected=True, whole_store_health_verified=False)
obs['operator_instruction'] = dict(publisher='release_v17_candidate/publish_v17_ready.py',
    allowed_commands='start/ready --execute-root-only', sole_publisher='root',
    old_887_publisher_allowed=False, future_normalclose_requires_new_matching_wrapper=True,
    notice='b243 native library requires v17 matching publisher; no old887 publisher or unreviewed normalclose wrapper.')
obs['evidence'] = evidence
canonical = REPAIR / 'current_observation_v17.json'
put(canonical, dump(obs))
current = dict(ref(canonical), revision='v17', status=STATUS, startup_sha256=STARTUP,
    source_manifest_sha256=MANIFEST, configuration_sha256=CONFIG, component_pins=379,
    observations_are_not_full_acceptance=True)

note = (
    'v17当前接续：功能v3与思考/回答动画已发布READY，保留用户手动PAUSED。\n\n'
    f'运行根 {spec["target"]}；startup SHA {STARTUP}；manifest SHA {MANIFEST}；379份组件；config SHA {CONFIG}；native SHA {spec["native_library_sha256"]}。\n'
    f'保存观测mono{observed["observed_mono"]}：IDLE/no playing、enabled=false、PAUSED、mic=false、GUI故障0；supervisor1134487/birth6085940、GTK1134492/birth6086055、camera260102/birth784437，同boot {spec["boot_id"]}。均为保存时点，下次须现读。\n'
    '本版部署feature_v3八份与animation五份；声纹未校准、不自动授予profile权限。纯角色公开模拟预览9状态/373帧及实图通过，thinking闭眼、answer睁眼，高幅mouth3.40可见张嘴、pause/cancel闭嘴。v1/v2尺寸失败保留，v3固定画布通过、v4补高幅截图；这不是声学口型、屏幕物理FPS、全业务负载或真人验收。另窗口全状态头晃/多部件新动画未部署。\n'
    'ASR仍为已在v16接入的Paraformer Small/3线程；公开16decode均值old5.789s→Small2.057s仅作背景变化的筛选。用户接受同音字，真人等待尚无新验收。Windows27B/2048/120与OmniVoice16未改，LLM权重仍D:/AIModels；combined前端1线程/capture nice-10/原8帧和每包权限/完整ACK保留。新进程0采集计数不证明v15问题已修复。\n'
    '本次memory原因探针实际捕获：completed1/discarded1、streak1/3s退避，candidate_rejected/full_source_validation/CandidateRejected/observation_evidence_missing。只解释这一次保真校验拒绝；之前other16来自operation_failed脱敏，原因不能倒推相同。拒绝不等于删除原文，也不能称全库健康。\n'
    'frontend allocation候选B1在原8帧队列溢出，ABBA未完成、未部署且无收益结论；phasehold未部署。v17控制/持续采集/真人等待/长稳尚未重新验收，不能承接v15通过项。\n'
    '操作边界：b243新库必须由release_v17_candidate/publish_v17_ready.py执行start/ready --execute-root-only；root仍唯一发布者。后续normalclose需新的匹配wrapper，不得用旧887 publisher。接续入口current_observation_v17.json与docs_state_v17/HANDOFF.json。\n'
    '本次接续文档修订仅用已封存metadata，未操作设备/模型/私库，未改生产工具、候选代码或运行回执。旧全文原字节保存在docs_state_v17/before。\n')
put(HERE / 'current_note.txt', note.encode('utf-8'))

def block(raw, marker, body, new_marker=None):
    a = ('<!-- ' + marker + ' -->').encode(); z = ('<!-- /' + marker + ' -->').encode()
    # Older current blocks also appear inside explicit archive wrappers: change first current occurrence only.
    begin = raw.index(a); end = raw.index(z, begin) + len(z); old = raw[begin:end]
    tag = 'archived-' + marker + '-pre-v17-' + sha(old)[:12]
    new_marker = new_marker or marker
    replacement = ('<!-- ' + new_marker + ' -->\n' + body + '\n<!-- /' + new_marker + ' -->').encode('utf-8')
    archived = ('\n\n<!-- ' + tag + ' -->\n以下旧段完整原字节保留为历史，仅适用于其原startup。\n').encode('utf-8') + old + ('\n<!-- /' + tag + ' -->').encode()
    return raw[:begin] + replacement + archived + raw[end:]

updates = {}
agent_body = '\n'.join('- ' + line for line in note.strip().split('\n') if line)
updates['project_AGENTS'] = block(originals['project_AGENTS'], 'board-business-live-20261030', agent_body)
updates['project_README'] = block(originals['project_README'], 'dialogue-current-20261031',
    '现役v17（379组件）已发布READY：功能v3及思考/回答动画接入，保留用户手动 `PAUSED`、mic=false。Small/3线程不变，真人等待尚未新验收。纯角色模拟预览9状态/373帧及实图通过，不能当物理FPS、声学口型或全业务验收。\n\n'
    '本次记忆拒绝已捕获为full_source_validation的observation_evidence_missing；只解释这一次，不推断早期脱敏错误，不等于删原文或全库健康。Windows不变，allocation/phasehold及新多部件动画未部署。见[当前观测](deliverables/2026-10-30_board_owner/integration/dialogue_repair/current_observation_v17.json)、[接续简记](deliverables/2026-10-30_board_owner/integration/dialogue_repair/docs_state_v17/current_note.txt)和[状态](deliverables/2026-10-30_board_owner/integration/dialogue_repair/STATUS.json)。')
analysis = block(originals['analysis_README'], 'current-v16-20261031',
    '- [v17当前观测](../语音共享文件/deliverables/2026-10-30_board_owner/integration/dialogue_repair/current_observation_v17.json)与[接续简记](../语音共享文件/deliverables/2026-10-30_board_owner/integration/dialogue_repair/docs_state_v17/current_note.txt)：功能v3/动画已发布READY，用户手动PAUSED；公开角色预览不等于真人/物理FPS验收，本次记忆保真拒绝已捕获，早期原因仍未知。', 'current-v17-20261031')
analysis = block(analysis, 'board-business-live-20261030', agent_body)
analysis = block(analysis, 'performance-dialogue-plan-20261031',
    '- [性能与对话平衡优化方案](性能与对话平衡优化方案_20261031.txt)：原阶段规划全文保留；现役v17 Small3与功能/动画接入，暂停偏好保留，按当前回执区分已部署和未验收。')
updates['analysis_README'] = analysis
for k in ['owner_continuation', 'performance_plan', 'analysis_performance_plan']:
    updates[k] = note.encode('utf-8') + '\n以下此前阶段全文原字节保留为历史，不代表当前状态或验收。\n\n'.encode('utf-8') + originals[k]

common = dict(status=STATUS, updated_utc=NOW, current_revision='v17', root=spec['target'], startup_sha256=STARTUP,
    source_manifest_sha256=MANIFEST, configuration_sha256=CONFIG, component_pins=379, board_boot_id=spec['boot_id'],
    native_library_sha256=spec['native_library_sha256'], character_pair_selection_sha256=spec['character_pair_selection_sha256'],
    supervisor_pid=ready['main_pid'], gtk_pid=ready['gtk_pid'], camera_pid=mapping['camera']['pid'],
    camera_birth_ticks=mapping['camera']['birth_ticks'], current_observation=current, verification_scope_notice=notice,
    frontend_options=obs['frontend_options'], current_revision_acceptance=obs['current_revision_acceptance'],
    last_observed_listening_enabled=False, last_observed_listening_state='PAUSED', user_manual_pause_preserved=True,
    automatic_listening_restored=False, microphone_open=False, physical_microphone_opened=False,
    physical_audio_played=False, playing=False, current_live_state_claimed=False, evidence=evidence,
    latest_memory_runtime_counters=dict(process_revision='v17', observed_mono=reason['observed_mono'], completed=1,
        discarded=1, failure_streak=1, error_present=True, counters_are_process_local=True, whole_store_health_verified=False),
    memory_retry_history=obs['memory'], memory_failure_metadata=reason,
    last_detailed_memory_observation=dict(current_v17_detailed_store_snapshot_available=False, runtime_only=obs['memory']),
    v16_zero_capture_counters_prove_v15_fixed=False, zero_new_process_capture_counters_prove_old_fixed=False,
    later_capture_failure_count=None, frontend_allocation_deployed=False, phasehold_deployed=False,
    feature_v3_deployed=True, animation_v17_deployed=True, new_multicomponent_motion_deployed=False,
    operator_instruction=obs['operator_instruction'])
def refresh(d):
    d.update(copy.deepcopy(common))
    for k in ['main_pid', 'last_verified_ui_supervisor_pid', 'last_observed_ui_supervisor_pid']:
        if k in d: d[k] = ready['main_pid']
    for k in ['last_verified_gtk_pid', 'last_observed_gtk_pid']:
        if k in d: d[k] = ready['gtk_pid']
    if 'audio_played' in d: d['audio_played'] = False
    if 'microphone_or_playback_started' in d: d['microphone_or_playback_started'] = False
    if 'listening' in d: d['listening'] = False
    if 'last_verified_pid_fields_revision' in d: d['last_verified_pid_fields_revision'] = 'v17_source_mapping'
    d['verified_listening'] = dict(revision='v17', startup_sha256=STARTUP, status='NOT_REVALIDATED_USER_PAUSED',
        controls_verified=False, continuous_capture_passed=False, priority_scope_passed=False, current_observation=current)
    d['response_latency'] = dict(revision='v17', startup_sha256=STARTUP, dialogue_output_format='dialogue_abc_v1',
        ordinary_reply_sentence_streaming=True, new_human_waiting_acceptance=False, waiting_improvement=None,
        audio_continuity_user_confirmed=None, audible_first_sound_measured=False, current_observation=current)
    if 'evidence_digest' in d: d['evidence_digest'] = sha(dump(evidence))
for k in ['dialogue_STATUS', 'implementation', 'production_live', 'resume_verification', 'character_switch', 'windows_coordination']:
    d = json.loads(originals[k])
    d.setdefault('continuation_history', []).append(dict(superseded_by_revision='v17', previous_status=d.get('status'),
        previous_current_observation=copy.deepcopy(d.get('current_observation')),
        original_bytes_archive=next(row for row in before if row['key'] == k)))
    refresh(d)
    for field in ['production', 'production_business_live']:
        if isinstance(d.get(field), dict): refresh(d[field])
    if k == 'character_switch': d['current_pair_observation'] = 'v17 animation selection/native b243 deployed; name/persona unchanged; pure-character preview passed, no physical/full-business acceptance.'
    if k == 'dialogue_STATUS': d['latest_human_feedback'].update(v17_human_waiting_feedback_available=False, v16_human_waiting_feedback_available=False)
    if k == 'windows_coordination':
        d['updated_at'] = NOW
        for field in ['production_UI_switch', 'production_business_cutover']:
            d[field].update(state=STATUS, current_revision='v17', updated_utc=NOW, startup_sha256=STARTUP,
                source_manifest_sha256=MANIFEST, configuration_sha256=CONFIG, component_pins=379,
                current_observation=current, physical_microphone_opened=False, physical_audio_played=False)
        assert d['windows_model_owner'] == json.loads(originals[k])['windows_model_owner']
    updates[k] = dump(d)

assert all(p.read_bytes() == originals[k] for k, p in targets.items()), 'concurrent_document_change'
for k, p in targets.items(): p.write_bytes(updates[k])
checks = []
def check(name, ok):
    checks.append(dict(check=name, passed=bool(ok)))
    assert ok, name
for row in before: check('archive_exact:' + row['key'], (BASE / row['archive']['path']).read_bytes() == originals[row['key']])
for row in sources: check('evidence_unchanged:' + Path(row['original']['path']).name,
    sha((BASE / row['original']['path']).read_bytes()) == row['original']['sha256'] == sha((BASE / row['sealed_copy']['path']).read_bytes()))
for k in ['dialogue_STATUS', 'implementation', 'production_live', 'resume_verification', 'character_switch', 'windows_coordination']:
    d = load(targets[k])
    for field in [None] + [v for v in ['production', 'production_business_live'] if isinstance(d.get(v), dict)]:
        x = d if field is None else d[field]; label=k+':'+str(field)
        check('v17_pins:' + label, all(x[v] == obs[v] for v in ['startup_sha256', 'source_manifest_sha256', 'configuration_sha256', 'component_pins', 'native_library_sha256']))
        check('v17_paused:' + label, x['microphone_open'] is False and x['last_observed_listening_state'] == 'PAUSED' and not x['automatic_listening_restored'])
        check('v17_no_inherited_acceptance:' + label, not x['controls_verified'] and not x['continuous_capture_passed'] and not x['full_physical_dialogue_acceptance'])
        check('v17_canonical_ref:' + label, x['current_observation']['sha256'] == sha(canonical.read_bytes()))
        check('one_rejection_not_history_or_deletion:' + label, x['memory_retry_history']['current_rejection'] == 'observation_evidence_missing' and not x['memory_retry_history']['previous_redacted_error_causes_confirmed'] and not x['memory_retry_history']['rejected_task_means_source_deleted'])
        check('pending_candidates_not_deployed:' + label, not x['frontend_allocation_deployed'] and not x['phasehold_deployed'] and not x['new_multicomponent_motion_deployed'])
for k in ['owner_continuation', 'performance_plan', 'analysis_performance_plan']: check('history_full_suffix:' + k, targets[k].read_bytes().endswith(originals[k]))
for k in ['project_AGENTS', 'project_README', 'analysis_README']:
    raw=targets[k].read_bytes(); markers=re.findall(rb'<!-- ([^\n]*?) -->',raw)
    def delta(b,m): return b.count(b'<!-- '+m+b' -->')-b.count(b'<!-- /'+m+b' -->')
    check('no_new_unbalanced_markers:' + k, all(delta(raw,m)==delta(originals[k],m) for m in markers if not m.startswith(b'/')))
check('windows_owner_unchanged', load(targets['windows_coordination'])['windows_model_owner'] == json.loads(originals['windows_coordination'])['windows_model_owner'])
check('visual_not_physical_or_business_acceptance', obs['animation']['pure_character_visual_review_passed'] and not obs['animation']['physical_fps_acceptance'] and not obs['animation']['real_pcm_lipsync_acceptance'] and not obs['animation']['full_business_load_acceptance'])
check('no_old_publisher', not obs['operator_instruction']['old_887_publisher_allowed'])
put(HERE / 'consistency.json', dump(dict(status='PASS', checks_passed=len(checks), checks=checks,
    devices_models_private_databases_accessed=False, production_or_candidate_source_changed=False)))
put(HERE / 'HANDOFF.json', dump(dict(schema='aura.docs-state-handoff.v1', status='V17_DOCUMENT_CONTINUATION_FROZEN',
    revision='v17', updated_utc=NOW, startup_sha256=STARTUP, source_manifest_sha256=MANIFEST,
    configuration_sha256=CONFIG, component_pins=379, current_observation=ref(canonical),
    before_manifest=ref(HERE / 'before_manifest.json'), current_note=ref(HERE / 'current_note.txt'),
    consistency=ref(HERE / 'consistency.json'), updater=ref(Path(__file__)),
    changed_documents=[dict(ref(p), key=k) for k,p in targets.items()], evidence=sources,
    checks_passed=len(checks), strict_verified_state_updater_run=False, device_model_or_private_database_actions=False,
    production_tools_candidates_or_runtime_receipts_modified=False, historical_bytes_preserved=True)))
print(json.dumps(dict(status='V17_DOCUMENT_CONTINUATION_FROZEN', documents_updated=len(targets), checks_passed=len(checks),
    handoff_sha256=sha((HERE/'HANDOFF.json').read_bytes()), current_observation_sha256=sha(canonical.read_bytes()))))
