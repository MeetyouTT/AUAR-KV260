"""Write a source-pinned field catalog; no HTTP, SSH, imports or device access."""
from pathlib import Path
import hashlib
import json

REVIEW = Path(__file__).resolve().parents[1]
TASK = REVIEW.parents[1]
BUSINESS = TASK.parents[1]
OWNER = BUSINESS / 'deliverables/2026-10-30_board_owner/integration'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    v24 = read(OWNER / 'dialogue_repair/release_v24_memory_followup_candidate/memory_followup_evidence/source_mapping.json')
    snapshot = read(OWNER / 'resume_camera_pin/actual_metadata_snapshot_v4.json')
    protected = json.loads(snapshot['files']['meta']['content'])['protected']
    proofs = []

    def proof(role, path, expected, basis, markers):
        assert sha(path) == expected, role
        lines = path.read_text(encoding='utf-8').splitlines()
        anchors = {marker: next(i for i, line in enumerate(lines, 1) if marker in line) for marker in markers}
        proofs.append(dict(role=role, source=str(path), sha256=expected,
            pin_basis=basis, verified_locally=True, live_source_verified=False, line_anchors=anchors))

    for role, rel, markers in (
            ('gui_pan_state', 'aura/tools/pan_controls.py', ["state['manual_pan'] = self.pan.read()", 'def refresh_pan_dialog']),
            ('candidate_report_projection', 'aura/tools/face_pan_controls.py', ['FOLLOW_REPORT_TTL_MS=1500', 'def refresh_pan_dialog']),
            ('controller_lock_diagnostics', 'controller/continuous_session.py', ['target_lock=self.target_lock.status()', 'heartbeat_mono_ms='])):
        path = REVIEW / 'candidate_r2' / rel if role != 'gui_pan_state' else TASK / 'candidate' / rel
        expected = sha(path)
        if role == 'gui_pan_state':
            assert expected == v24['component_pins'][rel[5:]]
        proof(role, path, expected, 'V24_COMPONENT' if role == 'gui_pan_state' else 'OFFLINE_R2_CANDIDATE', markers)
    for role, key, markers in (
            ('camera_health_and_ui', 'actual_board/vision/ui_camera_service.py', ['def snapshot(self)', 'def health(self)']),
            ('face_detector_health', 'actual_board/identity/face_targets.py', ['def view(self)', 'def health(self)']),
            ('current_face_observation', 'r17_face_observation.py', ['def observation(state)', "face_detection_mono_ms=value['anchor_stamp']"]),
            ('face_pixel_measurements', 'r17_face_flow.py', ['def diagnostics(self)', 'def measure(self, image, fid, stamp, detector)'])):
        path = TASK / 'audit_sources/camera' / (key.replace('/', '__') + '.txt')
        proof(role, path, snapshot['files'][key]['sha256'], 'OLD_BOOT_8100_CAMERA_SOURCE_SNAPSHOT', markers)

    old_sources = BUSINESS / 'deliverables/2026-10-24_native_critical_live/source/aura'
    for role, rel, markers in (
            ('identity_health_recency', 'board/identity/live.py', ['def view(self)', 'def health(self)', "'match_diagnostics'"]),
            ('native_schedule_health', 'board/vision/native_schedule.py', ['def optional_status(self, kind)', 'def health(self)'])):
        path = old_sources / rel
        expected = {v for name, v in protected.items() if name.endswith('/' + rel)}
        assert sha(path) in expected, role
        copy = REVIEW / 'audit_sources' / (rel + '.txt')
        copy.parent.mkdir(parents=True, exist_ok=True)
        copy.write_bytes(path.read_bytes())
        proof(role, copy, sha(path), 'OLD_BOOT_8100_PROTECTED_SOURCE_PIN', markers)
    visual = TASK / 'audit_sources/v23/board/runtime/visual_memory.py.txt'
    proof('visual_worker_counts', visual, v24['component_pins']['board/runtime/visual_memory.py'],
          'V24_COMPONENT', ['def public(self)', 'closed=self.closed,steps=self.steps,errors=self.errors'])
    save(REVIEW / 'evidence/field_source_proofs.json', proofs)

    fields = []
    def add(name, source, pointer, kind, meaning, candidate_only=False):
        fields.append(dict(name=name, source=source, json_pointer=pointer, type=kind,
            missing=None, candidate_only=candidate_only, meaning=meaning))
    for name, pointer, kind in (
            ('listening_enabled', '/handsfree_dialogue/enabled', 'boolean'),
            ('microphone_open', '/handsfree_dialogue/microphone_open', 'boolean'),
            ('listening_state', '/handsfree_dialogue/state', 'enum:PAUSED,OTHER,UNKNOWN'),
            ('manual_state', '/manual_pan/state', 'bounded_enum'),
            ('follow_enabled', '/manual_pan/automatic_following', 'boolean'),
            ('pulse_us', '/manual_pan/pulse_us', 'finite_number'),
            ('flags', '/manual_pan/readback/flags', 'nonnegative_integer'),
            ('lease_left_ms', '/manual_pan/readback/lease_left_ms', 'nonnegative_integer'),
            ('visual_worker_steps', '/board_business/visual_timeline/steps', 'nonnegative_integer'),
            ('visual_worker_errors', '/board_business/visual_timeline/errors', 'nonnegative_integer')):
        add(name, 'gui_state', pointer, kind, 'Cached GUI/business state; not a current camera/actuator owner proof')
    for name, pointer, kind in (
            ('follow_report_fresh', '/manual_pan/face_follow/report_fresh', 'boolean'),
            ('follow_report_age_ms', '/manual_pan/face_follow/report_age_ms', 'finite_number')):
        add(name, 'gui_state', pointer, kind, 'Display-only report freshness; never extends motion authority', True)
    for name, pointer, kind in (
            ('camera_pid', '/pid', 'positive_integer'),
            ('person_detection_count', '/detected_frames', 'nonnegative_integer'),
            ('capture_count', '/capture_frames', 'nonnegative_integer'),
            ('capture_age_ms', '/capture_age_ms', 'finite_number'),
            ('person_observation_age_ms', '/observation_age_ms', 'finite_number'),
            ('identity_ready', '/identity/ready', 'boolean'),
            ('identity_backend', '/identity/backend', 'enum:DPU_SFACE_INT8,OTHER,UNKNOWN'),
            ('identity_processed', '/identity/processed', 'nonnegative_integer'),
            ('face_detector_processed', '/identity/face_targets/processed', 'nonnegative_integer'),
            ('face_detector_source_age_ms', '/identity/face_targets/source_age_ms', 'finite_number'),
            ('face_worker_alive', '/identity/face_targets/worker_alive', 'boolean'),
            ('face_worker_faults', '/identity/face_targets/worker_faults', 'nonnegative_integer'),
            ('face_fault_latched', '/identity/face_targets/fault_latched', 'boolean'),
            ('primary_calls', '/dpu_schedule/primary_calls', 'nonnegative_integer'),
            ('primary_period_overruns', '/dpu_schedule/primary_period_overruns', 'nonnegative_integer'),
            ('native_owner_fenced', '/dpu_schedule/owner_fenced', 'boolean'),
            ('yunet_overruns', '/dpu_schedule/optional/yunet/overruns', 'nonnegative_integer'),
            ('yunet_native_failures', '/dpu_schedule/optional/yunet/native_failures', 'nonnegative_integer'),
            ('sface_overruns', '/dpu_schedule/optional/sface/overruns', 'nonnegative_integer'),
            ('sface_native_failures', '/dpu_schedule/optional/sface/native_failures', 'nonnegative_integer')):
        add(name, 'camera_health', pointer, kind, 'Separate actual camera/model counters; compare only with unchanged owner')
    for name, pointer in (('camera_error_present', '/camera_error'),
            ('detector_error_present', '/detector_error'), ('identity_error_present', '/identity/error')):
        add(name, 'camera_health', pointer, 'string_presence_to_nullable_boolean', 'Do not return the string')
    for name, pointer, kind in (
            ('face_source_state', '/state', 'bounded_enum'),
            ('source_frame_id', '/source_frame_id', 'positive_integer'),
            ('source_mono_ms', '/source_mono_ms', 'nonnegative_integer'),
            ('source_deadline_ms', '/deadline_mono_ms', 'nonnegative_integer'),
            ('face_anchor_mono_ms', '/face_detection_mono_ms', 'nonnegative_integer'),
            ('motion_track_id', '/target/track_id', 'positive_integer'),
            ('motion_track_generation', '/target/track_generation', 'positive_integer'),
            ('face_measurement_count', '/face_tracking/valid_measurements', 'nonnegative_integer'),
            ('face_measurement_rounds', '/face_tracking/processed', 'nonnegative_integer'),
            ('face_anchor_refreshes', '/face_tracking/anchor_refreshes', 'nonnegative_integer'),
            ('detection_miss', '/detection_miss', 'boolean')):
        add(name, 'face_observation', pointer, kind, 'Anonymous motion pixels/anchor; not biological identity')
    for name, pointer, kind in (
            ('current_identity_state', '/modules/identity/state', 'bounded_enum'),
            ('identity_source_frame_id', '/modules/identity/source_frame_id', 'positive_integer'),
            ('identity_source_mono_ms', '/modules/identity/source_mono_ms', 'nonnegative_integer'),
            ('frontal', '/modules/identity/face_attention/frontal', 'boolean'),
            ('yaw_ratio', '/modules/identity/face_attention/yaw_ratio', 'finite_number'),
            ('roll_degrees', '/modules/identity/face_attention/roll_degrees', 'finite_number')):
        add(name, 'camera_ui', pointer, kind, 'Project on board; private names and identity IDs must not leave raw response')
    for name, pointer, kind in (
            ('session_target_locked', '/result/target_lock/locked', 'boolean'),
            ('session_track_id', '/result/target_lock/track_id', 'positive_integer'),
            ('session_track_generation', '/result/target_lock/track_generation', 'positive_integer')):
        add(name, 'controller_report', pointer, kind, 'Not forwarded into GUI face_follow; requires current report provenance', True)
    catalog = dict(schema='aura-visual-axis-static-readonly-fields-1',
        generated_from_local_source_only=True, device_accessed=False,
        sources={
            'gui_state': dict(endpoint='127.0.0.1:8783/api/state', method='GET'),
            'camera_health': dict(endpoint='127.0.0.1:8790/health', method='GET'),
            'face_observation': dict(endpoint='127.0.0.1:8790/v1/motion/face/observation', method='GET'),
            'camera_ui': dict(endpoint='127.0.0.1:8790/v1/ui/status', method='GET',
                raw_payload_has_private_information=True, raw_payload_export_allowed=False),
            'controller_report': dict(endpoint=None, path_from='CURRENT_CHILD_FIXED_REPORT_REFERENCE_ONLY')},
        fields=fields,
        unresolved_without_fresh_main_check={
            'firmware_kind':'UNKNOWN', 'vart_kind':'UNKNOWN', 'fdt_context_matches':None,
            'paired_firmware_and_native_hashes_match':None, 'current_reference_us':None,
            'current_direction_qualified':None, 'camera_mounting_confirmed':None,
            'current_camera_identity_threshold':None, 'speaker_field_calibrated':None,
            'blur_variance_calibrated':None, 'mechanical_angle_degrees':None,
            'generic_native_error_count':None},
        prohibited_interpretations=[
            'visual_worker_steps are not face source FPS',
            'camera health match_diagnostics may describe an old result; use fresh camera UI identity source',
            'same motion key is not a biological identity or personal permission',
            'face_attention.target is the detector key; compare it with current face_target, not motion key',
            'stream packet count is not distinct-source FPS',
            'a missing counter is not zero errors'],
        delta_rule='Same boot/PID/birth/service/camera epoch; both finite integer counters present and nondecreasing; otherwise null',
        export_rule='fixed enums, finite numbers and booleans only; project before crossing board boundary')
    save(REVIEW / 'field_catalog.json', catalog)
    print(json.dumps(dict(status='STATIC_FIELD_CATALOG_BUILT', fields=len(fields),
                         source_proofs=len(proofs), live_device_verified=False)))


if __name__ == '__main__':
    main()
