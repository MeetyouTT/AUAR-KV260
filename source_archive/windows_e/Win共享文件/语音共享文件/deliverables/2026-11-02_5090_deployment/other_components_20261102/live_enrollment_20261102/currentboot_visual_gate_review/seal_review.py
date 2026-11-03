"""Seal filtered public visual-gate observations and source branch analysis."""
import datetime
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OBS = HERE / 'VISUAL_ENTRY_PRECONDITIONS.json'
data = json.loads(OBS.read_text(encoding='utf-8'))
checks = [s['camera_current_single_unknown_entry_gates_pass'] for s in data['camera_samples']]
assert checks == [True, True]
assert data['gui_cache']['camera_current_single_unknown_entry_gates_pass']
assert data['gui_cache_owner_matches_first_camera'] and data['gui_cache_owner_matches_second_camera']
assert data['gui_cache_context_matches_first_camera']
report = {
    'schema': 'aura-currentboot-visual-enrollment-gate-review-1',
    'sealed_host_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'verdict': 'CURRENT_VISUAL_ENTRY_GATES_PASS_HISTORICAL_CONFIRMATION_CAUSE_UNPROVED',
    'observation_host_utc': data['host_observed_utc'],
    'observation_sha256': hashlib.sha256(OBS.read_bytes()).hexdigest(),
    'camera_samples_count': 2,
    'gui_cache_samples_count': 1,
    'snapshot_camera_age_ms': [s['age_ms'] for s in data['camera_samples']],
    'snapshot_camera_ttl_ms': [s['ttl_ms'] for s in data['camera_samples']],
    'gui_cache_age_ms': data['gui_cache']['age_ms'],
    'current_boot_selected_camera_birth_cmdline_and_identity_pin_checks_pass': all(data[k] for k in (
        'current_boot_equals_expected_reboot', 'selected_binding_sha_matches_gui_pin',
        'selected_binding_boot_current', 'selected_camera_process_running',
        'selected_camera_birth_matches_process', 'selected_camera_cmdline_matches_process',
        'camera_run_identity_matches_selected_binding', 'identity_schema_expected',
        'identity_backend_kind_expected', 'identity_ttl_matches_selected_binding')),
    'current_camera_and_gui_visual_projection_pass_original_validator': True,
    'current_gui_cache_context_and_full_owner_match_camera': True,
    'current_face_count': 1,
    'current_body_people_count': 2,
    'body_count_two_is_not_multi_face_failure_in_original_face_mode': True,
    'current_identity_state': 'UNKNOWN',
    'current_database_revision': 2,
    'current_sampling_stage': 'idle',
    'current_sampling_total': 0,
    'current_sample_start_capability': True,
    'current_identity_enroll_capability': False,
    'identity_enroll_false_is_expected_before_validated_sampling_ready': True,
    'current_frontal_false_does_not_reject_original_entry_when_sample_start_capability_true': True,
    'confirmation_capture_start_snapshot_inspected': False,
    'historical_confirmation_same_owner_context_and_visual_boundary_evidence_proved': False,
    'branches': [
        {'component': 'VoiceEnrollment.handle', 'condition': 'Current snapshot invalid or capture source/owner/single-target unavailable',
         'code_if_workflow_active': 'changed', 'code_if_workflow_inactive': 'face_unavailable', 'resets_flow': True},
        {'component': 'VoiceEnrollment.handle', 'condition': 'Active FSM owner differs from current owner, except original ready recovery',
         'code': 'changed', 'resets_flow': True},
        {'component': 'VoiceEnrollment.handle', 'condition': 'Current identity KNOWN',
         'code': 'already_known', 'resets_flow': True},
        {'component': 'VoiceEnrollment.handle', 'condition': 'Neither identity_enroll nor sampling plus identity_sample_start/FSM_sampling is allowed',
         'code': 'face_unavailable', 'resets_flow': True, 'current_condition_observed': False},
        {'component': 'UnifiedBindingRouter.route', 'condition': 'Registry.confirm throws ValueError or TimeoutError',
         'reason': 'BINDING_CONFIRMATION_VISUAL_UNAVAILABLE',
         'possible_fixed_causes': ['UNAVAILABLE_VISUAL_ENVELOPE', 'NON_DISTINCT_CONFIRMATION_CAPTURE', 'EXPIRED_ATTEMPT', 'NOT_AWAITING_CONFIRMATION', 'REGISTRY_BUSY'],
         'not_specific_evidence_of_bad_face_quality': True},
        {'component': 'IdentityLinkRegistry.confirm', 'condition': 'Valid boundary guard differs from original guard',
         'reason': 'FACE_LIFECYCLE_CHANGED', 'cancels_attempt': True},
        {'component': 'speaker_visual.build_visual', 'condition': 'Capture-start and current end boundary checks',
         'checks': ['ACTUAL_SOURCE', 'SAME_CURRENT_BOOT', 'SAME_CAMERA_SERVICE', 'CAMERA_READY', 'SINGLE_FACE',
                    'SAME_FACE_TARGET_AND_DATABASE_REVISION', 'SAME_PREVIEW_CAMERA_EPOCH',
                    'SOURCE_FRAME_AND_TIME_INCREASE', 'SOURCE_BOUNDARY_AGES_UNDER_3000MS'],
         'does_not_require': ['BODY_COUNT_ONE', 'FRONTAL_TRUE', 'KNOWN_IDENTITY']}],
    'cache_source': {
        'original_provider': 'UiServiceClient.identity_snapshot',
        'requires_link_READY': True,
        'validates_original_gate_value_at_current_monotonic_time': True,
        'presentation_read_masks_are_not_passed_to_identity_provider': True,
        'default_cached_poll_seconds': 0.6,
        'current_link_READY_and_error_absent': data['gui_service_link']=='READY' and not data['gui_service_error_present']},
    'next_safe_diagnostic': 'At the next authorized confirmation retain only active_stage, original fixed reply_code, capture_snapshot_valid, owner_equal, source/preview age and build_visual fixed reason; root owns the live flow',
    'existing_optional_public_diagnostic': 'ChannelConversationJobs.last_voice_route has capture_snapshot_valid, capture_face_count, capture_identity_state and reply_code; availability on current BoardBusiness path is not assumed',
    'recommended_product_change_now': 'No threshold/quality/permission weakening justified by these observations; exact failing branch is still required',
    'reviewer_more_gets_or_production_changes_planned': False,
    'private_databases_photos_audio_transcripts_names_personids_axis_or_commands_accessed': False}
(HERE / 'REVIEW_VERDICT.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
text = '''本boot视觉登记入口只读审阅：当前条件通过；尚未证明先前确认失败的精确原因。

主机时间11:32:43Z，一次严格SSH内顺序GET两次8790状态和一次GUI公开cache。相机状态actual/READY，单张face目标有效、UNKNOWN、库版本2、sample_start能力true，采样idle0/15。相机快照age14/15ms、TTL2000ms；GUI cache age303ms、link READY且无error；本boot、完整owner、context与两次相机状态一致。selected绑定的boot、camera birth/cmd和identity配置逐值核对通过，a911/UIservices/runtime源与startup pin一致。

people_count2而face_count1。原VoiceEnrollment.single_target和speaker_visual在face模式按face_count判断，因此身体框2不能直接当多人脸拒绝。frontalfalse但sample_starttrue；原入口不以frontal为前提。identity_enroll=false在尚未采样验证ready时正常，不能单独作失败证据。

“需要清晰人脸”至少覆盖不同分支：
1. VoiceEnrollment：当前快照/捕获起点或单目标/owner验证失败时，active=true通常返回changed，active=false返回face_unavailable；capability不足时，active确认阶段也会返回face_unavailable并reset。
2. UnifiedBindingRouter：registry.confirm里的ValueError/TimeoutError共映射BINDING_CONFIRMATION_VISUAL_UNAVAILABLE，可能是capture边界视觉不可用、确认不是独立capture、attempt已过期/状态不符或registry忙，不能从提示文本认定光照或生物匹配分数。
3. 合法guard与原guard不同会走FACE_LIFECYCLE_CHANGED并取消，必须与“视觉不可用”区分。

原speaker_visual需要capture-start与本轮处理时的end两端：actual、同boot/service、cameraREADY、单脸、同target/库版本/preview相机epoch，帧与源时间前进且边界源age<3000ms；不要求身体框仅1、frontal=true或已识别KNOWN。本次两快照与GUI缓存一致不能替代用户那句确认的capture-start证据。

UiServices.identity_snapshot直接验证原gate.value，要求linkREADY并按当前单调时间检验TTL；未使用带显示掩码的SnapshotGate.read()结果。当前没有发现GUI cache/context失配。V2只解决accepted start后的缓存发布竞态；本次没有进入采样，不能将它当成同一问题或重发start。

下一步应由root在原确认流程留最少RAM固定诊断：active stage、原reply_code、capture_snapshot_valid、owner_equal、源/preview年龄和build_visual固定reason。ChannelJobs已有last_voice_route的部分字段；当前BoardBusiness路径是否暴露要核实，不可假设。此刻没有证据支持降阈值、放宽授权/TTL、要求用户盲调灯光或改face/body人数规则。

审阅结束后不再追加GET。本轮未读取私库、照片、语音、对话原文/称呼、personID或轴状态，未发命令、重启或修改生产源。
'''
(HERE / 'REVIEW.txt').write_text(text, encoding='utf-8')
print(json.dumps({name: hashlib.sha256((HERE/name).read_bytes()).hexdigest()
                  for name in ('REVIEW_VERDICT.json', 'REVIEW.txt', 'VISUAL_ENTRY_PRECONDITIONS.json')}))
