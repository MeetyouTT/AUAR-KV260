"""State checks distinguish a declared injected fault from unexpected failures."""
import time
PARENT_RELEASE = '/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-slot-wait-81e6463c3747-298300'
PARENT_UNIT_SHA = '048ee59cf4f01d84f0442825926b38ae0940e3c566a005449385d34536734e2f'
PARENT_CONFIG = PARENT_RELEASE+'/board_camera_ui.json'


def wait_parent_ready(ops,*,clock=time.monotonic,sleep=time.sleep,timeout=30):
    """A read-only bounded wait across an existing camera watchdog restart."""
    until=clock()+timeout;previous=None;stable=0
    while clock()<until:
        try:
            if not (ops.active('aura-avatar-ui.service') and ops.active('aura-camera-ui.service')):
                raise ValueError('Parent service restarting')
            state=ops.m.camera();validate_parent_state(state)
            if previous and state['pid']==previous['pid'] and state['capture_frames']>previous['capture_frames']:
                stable+=1
            else:stable=0
            previous=state
            if stable>=3:return state
        except Exception:previous=None;stable=0
        sleep(.5)
    raise RuntimeError('Parent did not provide stable fresh frames within the preflight window')


def common_health(state):
    assert not state['camera_error'] and not state['detector_error'], 'Camera/detector error'
    assert state['observation_age_ms'] is not None and 0 <= state['observation_age_ms'] < 750
    assert state['identity_backend'] in ('WINDOWS_CPU_SFACE_ORT','DPU_SFACE_INT8')
    face = state['face_targets']
    assert face['ready'] and not face['error']
    assert face['source_age_ms'] is not None and 0 <= face['source_age_ms'] < 1000
    assert state.get('shadow') is None
    other = state['dpu_schedule']['optional'].get('sface', {})
    assert not other.get('disabled') and not other.get('overruns', 0)
    return face, state['dpu_schedule']['optional']['yunet']


def camera_snapshot(m):
    value=m.get(8790,'/health')
    result={k:value.get(k) for k in ('pid','capture_frames','detected_frames','capture_hz','detection_hz',
        'observation_age_ms','camera_error','detector_error','dpu_schedule','pipeline_metrics')}
    identity=value.get('identity') or {}
    result.update(identity_backend=identity.get('backend'),face_targets=identity.get('face_targets'),
        shadow=(identity.get('feature_inference') or {}).get('shadow'),
        feature_inference=identity.get('feature_inference'),identity_ready=identity.get('ready'),
        identity_error=identity.get('error'),identity_processed=identity.get('processed'))
    result['match_diagnostics']=identity.get('match_diagnostics')
    return result


def validate_parent_state(state):
    """A pinned parent may already have safely recovered historical faults."""
    face, job = common_health(state)
    if not job['overruns']:
        validate_state(state)
        return
    assert face['backend'] == 'DPU_YUNET_INT8' and job['disabled'] is False
    policy = state['dpu_schedule']['yunet_recovery']
    assert policy['enabled'] and policy['phase'] == 'RUNNING'
    # The pinned policy can complete recovery only for a completed status-0,
    # hardcap-only fault. Diagnostic event rings may evict older details;
    # retain cumulative policy evidence rather than pretending it is zero.
    assert policy['faults'] == policy['recoveries'] == job['overruns']
    assert policy['attempts'] == policy['recoveries']
    counts = state['dpu_schedule']['optional_diagnostics']['counters']['yunet']
    assert counts['native_failed'] == face['slot_retry']['withdrawn_after_slot']
    for row in state['dpu_schedule']['optional_diagnostics']['fault_events']:
        if row.get('hardcap_exceeded') or row.get('guard_exceeded'):
            assert row['hardcap_exceeded'] == 1 and row['guard_exceeded'] == 0
            assert row['native_completed'] == 1 and row['native_status'] == 0 and not row['body_failed']


def validate_state(state, *, injected=False, allow_parent_fallback=False):
    face, job = common_health(state)
    if allow_parent_fallback and face['backend'] == 'CPU_YUNET_FALLBACK_AFTER_DPU_OVERRUN':
        assert job['disabled'] is True and job['overruns'] == 1
        events = state['dpu_schedule']['optional_diagnostics']['fault_events']
        hard = [row for row in events if row.get('hardcap_exceeded') or row.get('guard_exceeded')]
        assert len(hard) == 1
        row = hard[0]
        assert row['hardcap_exceeded'] == 1 and row['guard_exceeded'] == 0
        assert row['native_completed'] == 1 and row['native_status'] == 0 and not row['body_failed']
        return
    if not injected or job['overruns'] == 0:
        assert face['backend'] == 'DPU_YUNET_INT8' and not job['disabled'] and job['overruns'] == 0
        return
    assert job['overruns'] == 1, 'Unexpected additional overrun'
    policy = state['dpu_schedule']['yunet_recovery']
    assert policy['faults'] == 1 and policy['attempts'] <= 1 and policy['recoveries'] <= 1
    assert policy['phase'] in ('COOLDOWN', 'PROBATION', 'RUNNING')
    if policy['phase'] == 'COOLDOWN':
        assert job['disabled'] is True
        assert face['backend'] in ('CPU_YUNET_FALLBACK_AFTER_DPU_OVERRUN', 'DPU_YUNET_INT8')
    else:
        assert not job['disabled']
        assert face['backend'] in ('DPU_YUNET_INT8', 'CPU_YUNET_FALLBACK_AFTER_DPU_OVERRUN')
    events = state['dpu_schedule']['optional_diagnostics']['fault_events']
    hard = [row for row in events if row.get('hardcap_exceeded') or row.get('guard_exceeded')]
    assert len(hard) == 1
    row = hard[0]
    assert row['hardcap_exceeded'] == 1 and row['guard_exceeded'] == 0
    assert row['native_completed'] == 1 and row['native_status'] == 0 and not row['body_failed']


def completed_recovery(state):
    validate_state(state, injected=True)
    face, job = common_health(state)
    policy = state['dpu_schedule']['yunet_recovery']
    assert job['overruns'] == 1 and not job['disabled']
    assert face['backend'] == 'DPU_YUNET_INT8'
    assert policy['phase'] == 'RUNNING' and policy['recoveries'] == 1 and policy['attempts'] == 1
    assert policy['probe_successes'] == policy['required_successes'] == 3


def rewrite_unit(raw, old_root, new_root, *, injected=False):
    old_root, new_root = str(old_root), str(new_root)
    text = raw.decode()
    assert text.count(old_root) >= 2 and '[Service]\n' in text
    text = text.replace(old_root, new_root)
    old_config = '/home/root/aura-dpu-vision-20261021/runtime/81fdb11903abb71e-live-134783/board_camera_ui.json'
    if old_config in text:
        assert text.count(old_config) == 1
        text = text.replace(old_config, new_root+'/board_camera_ui.json')
    else:
        assert text.count(new_root+'/board_camera_ui.json') == 1
    assert text.count(new_root+'/runtime_entry.py') == 1
    if injected:
        text = text.replace(new_root+'/runtime_entry.py', new_root+'/injection_entry.py')
    assert old_root not in text and 'AURA_EXPERIMENT_GIL_MS=1' in text
    return text.encode()
