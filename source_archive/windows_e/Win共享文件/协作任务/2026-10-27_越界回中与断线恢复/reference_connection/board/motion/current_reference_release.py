"""Qualify current-reference STATUS/STOP access, never manual motion permission."""
import hashlib
import json
import math
from pathlib import Path

STATUS = 'CURRENT_REFERENCE_CONNECTION_VSRV2'
SCOPE = 'face_follow_reference_connection_only'
INTEGER_FIELDS = ('flags', 'lease_left_ms', 'width_us', 'target_us', 'reference_us', 'session', 'epoch', 'ack_seq', 'reason')
BOOL_FIELDS = ('active', 'armed', 'referenced', 'bound')


def require(condition, message):
    if not condition:
        raise RuntimeError(message + '; no manual motion authority')


def connection_scope(release):
    return release.get('status') == STATUS or release.get('scope') == SCOPE


def reject_manual_motion(release):
    if connection_scope(release):
        raise ValueError('当前连接仅供人脸随动读取参考，未授权手动点动')


def stopped(value):
    return (isinstance(value, dict) and all(type(value.get(k)) is int for k in INTEGER_FIELDS)
            and all(value[k] == 0 for k in ('flags', 'lease_left_ms', 'reason'))
            and all(value.get(k) is False for k in BOOL_FIELDS)
            and all(0 <= value[k] <= 0xffffffff for k in ('session', 'epoch', 'ack_seq'))
            and all(1400 <= value[k] <= 1600 for k in ('width_us', 'target_us', 'reference_us')))


def same_readback(first, second):
    return stopped(first) and stopped(second) and all(first[k] == second[k] for k in INTEGER_FIELDS + BOOL_FIELDS)


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def qualified_reference_stop(release, config, root):
    require(release.get('status') == STATUS and release.get('scope') == SCOPE
            and release.get('boot_id') == config.get('boot_id')
            and release.get('manual_motion_enabled') is False
            and all(release.get(k) is False for k in
                    ('physical_range_verified', 'mechanical_reference_calibrated', 'external_waveform_verified'))
            and [release.get('manual_minimum_us'), release.get('manual_maximum_us')] == [1400, 1600]
            and [config.get('manual_minimum_us'), config.get('manual_maximum_us')] == [1400, 1600]
            and config.get('maximum_step_us') == 20 and config.get('maximum_duration_s') == 2,
            'CURRENT_REFERENCE_CONNECTION_SCOPE_REQUIRED')
    qualification = release['qualification']
    values = {}
    for key in ('reference', 'control_report', 'observer_report'):
        item = qualification[key]
        relative = Path(item['file'])
        require(not relative.is_absolute() and '..' not in relative.parts, 'QUALIFICATION_FILE_MUST_BE_LOCAL')
        path = Path(root) / relative
        require(path.is_file() and not path.is_symlink(), 'QUALIFICATION_FILE_NOT_REGULAR')
        raw = path.read_bytes()
        require(hashlib.sha256(raw).hexdigest() == item['sha256'], 'QUALIFICATION_HASH_MISMATCH')
        values[key] = json.loads(raw)
    ref, report, observer = (values[k] for k in ('reference', 'control_report', 'observer_report'))
    result = report['result']
    boot = config['boot_id']
    require(ref.get('schema') == 'aura-user-observed-fixed-reference-1'
            and ref.get('boot_id') == report.get('boot_id') == result.get('boot_id') == boot
            and ref.get('fdt_sha256') == config['fdt_sha256']
            and ref.get('user_present') is True and ref.get('confirmed_current_position') is True
            and isinstance(ref.get('user_observation'), str) and ref['user_observation'].strip()
            and type(ref.get('reference_us')) is int and ref['reference_us'] == 1420
            and ref.get('bounds_us') == [1402, 1420] and ref.get('camera_moves_with_axis') is True
            and ref.get('polarity') == 1, 'CURRENT_BOOT_USER_REFERENCE_REQUIRED')
    require(report.get('reference_receipt_sha256') == qualification['reference']['sha256']
            and result.get('authorization_id') == result.get('observation_id') == ref.get('authorization_id')
            and isinstance(ref.get('authorization_id'), str) and ref['authorization_id'], 'REFERENCE_TRIAL_BINDING_MISMATCH')
    started, completed, deadline = (result[k] for k in ('started_mono_s', 'completed_mono_s', 'absolute_deadline_mono_s'))
    authorized = ref.get('authorization_recorded_mono_s', ref.get('observed_mono_s'))
    observed, expires = ref.get('observed_mono_s'), ref.get('expires_mono_s')
    require(all(finite(v) for v in (observed, authorized, started, completed, deadline, expires))
            and 0 <= observed <= authorized <= started < completed <= deadline <= expires <= authorized + 600
            and abs(deadline - started - 5.) < 1e-6 and result.get('requested_duration_s') == 5.,
            'ORIGINAL_FINITE_TRIAL_AUTHORIZATION_INVALID')
    require(report.get('status') == 'FIXED_TRAJECTORY_STOPPED_OBSERVATION_PENDING'
            and result.get('status') == 'FIXED_BENCH_ACK_AND_STOP_PASS_OBSERVATION_PENDING'
            and report.get('physical_motion_verified') is False and result.get('physical_motion_verified') is False
            and result.get('stop_confirmed') is True and result.get('error') is None and result.get('stop_error') is None
            and result.get('source_kind') == 'EXPLICIT_FINITE_BENCH_NO_FACE_PACKETS'
            and same_readback(result['initial_readback'], ref['stopped_readback'])
            and same_readback(result['finish_readback'], result['stopped_readback']), 'FIXED_TRIAL_STOP_PROOF_REQUIRED')
    final = result['stopped_readback']
    require(final['width_us'] == final['target_us'] == final['reference_us'] == 1420
            and final['epoch'] == result['initial_readback']['epoch'] + 1, 'FIXED_TRIAL_REFERENCE_RETURN_REQUIRED')
    commands = result['commands']
    require(isinstance(commands, list) and 2 <= len(commands) <= 248 and final['ack_seq'] == len(commands),
            'COMPLETE_FIXED_TRIAL_COMMANDS_REQUIRED')
    last_time, previous = started, 1420
    for seq, command in enumerate(commands, 1):
        ack = command['acknowledgement'];rb = ack['readback']
        submitted, received, sampled = command['submitted_mono_s'], command['returned_mono_s'], ack['observed_mono_s']
        target = command['target_us']
        require(all(finite(v) for v in (submitted, received, sampled)) and last_time <= submitted <= sampled <= received <= completed
                and type(target) is int and 1405 <= target <= 1420 and abs(target - previous) <= 1
                and ack.get('outcome') == 'ACCEPTED' and rb['flags'] == 15 and rb['reason'] == 0
                and rb['session'] == final['session'] and rb['epoch'] == final['epoch'] and rb['ack_seq'] == seq
                and rb['target_us'] == target and 1405 <= rb['width_us'] <= 1420 and 0 < rb['lease_left_ms'] <= 100,
                'FIXED_TRIAL_COMMAND_CONTEXT_INVALID')
        last_time, previous = received, target
    require(min(c['target_us'] for c in commands) == 1405 and commands[0]['target_us'] == commands[-1]['target_us'] == 1420,
            'COMPLETE_FIFTEEN_US_RETURN_REQUIRED')
    require(observer.get('scope') == 'NUMERIC_CACHED_PREVIEW_BACKGROUND_DISPLACEMENT'
            and observer.get('images_saved') is False and observer.get('actuator_access') is False
            and observer.get('observer_alive') is False and observer.get('close_after_output_stop') is True
            and observer.get('baseline_ready') is True
            and observer.get('control_report_path') == qualification['control_report']['source_path']
            and observer.get('control_status') == report['status']
            and observer.get('control_started_mono_s') == started and observer.get('control_completed_mono_s') == completed,
            'OBSERVER_NOT_BOUND_TO_FIXED_TRIAL')
    baseline = observer['baseline']
    require(baseline.get('state') == 'BASELINE_READY' and baseline.get('board_boot_id') == boot
            and baseline.get('corners', 0) >= 20 and baseline.get('spatial_cells', 0) >= 4
            and baseline.get('span_x_ratio', 0) >= .30 and baseline.get('span_y_ratio', 0) >= .25
            and type(baseline.get('captured_mono_ms')) is int and baseline['captured_mono_ms'] / 1000. <= started,
            'BACKGROUND_BASELINE_REQUIRED')
    measured = [v for v in observer['samples'] if v.get('state') == 'MEASURED_BACKGROUND_SHIFT']
    require(len(measured) == observer.get('measured_samples') and len(measured) >= 12, 'ENOUGH_MEASURED_BACKGROUND_SAMPLES_REQUIRED')
    during = []
    stamps = []
    for value in measured:
        capture = value.get('captured_mono_ms');dx,dy = value.get('dx_px'),value.get('dy_px')
        require(value.get('board_boot_id') == boot and value.get('camera_epoch') == baseline['camera_epoch']
                and value.get('reference_frame_id') == baseline['frame_id']
                and value.get('reference_captured_mono_ms') == baseline['captured_mono_ms']
                and type(capture) is int and capture > baseline['captured_mono_ms']
                and finite(dx) and finite(dy) and value.get('inliers', 0) >= 20
                and .65 <= value.get('inlier_ratio', -1) <= 1 and value.get('spatial_cells', 0) >= 4
                and value.get('span_x_ratio', 0) >= .30 and value.get('span_y_ratio', 0) >= .25
                and 0 <= value.get('median_fb_error_px320', -1) <= .75
                and 0 <= value.get('median_flow_residual_px320', -1) <= 1.5
                and .95 <= value.get('affine_scale', 0) <= 1.05
                and abs(value.get('affine_rotation_degrees', 999)) <= 3,
                'BACKGROUND_MEASUREMENT_QUALITY_INVALID')
        stamps.append(capture)
        if started <= capture / 1000. <= completed: during.append(value)
    require(stamps == sorted(set(stamps)) and len(during) >= 12 and max(abs(v['dx_px']) for v in during) > 2.,
            'ACTUAL_BACKGROUND_SHIFT_DURING_TRIAL_REQUIRED')
    require(finite(observer.get('maximum_abs_dx_px'))
            and abs(observer['maximum_abs_dx_px'] - max(abs(v['dx_px']) for v in measured)) < 1e-6,
            'OBSERVER_SUMMARY_NOT_BACKED_BY_SAMPLES')
    return dict(final)
