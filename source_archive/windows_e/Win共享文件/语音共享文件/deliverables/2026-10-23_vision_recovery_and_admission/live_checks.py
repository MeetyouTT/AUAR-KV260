"""Pinned parent may be latched after the already recorded guard fault."""
import time

PARENT_RELEASE='/home/root/aura-dpu-vision-20261021/postpower-retry-live/release-sface-int8-9025bd49fe52-333217'
PARENT_UNIT_SHA='a29082bae1d382d7a43505d5a1d3a51fa2203081423755900e9d72836385e343'
PARENT_CONFIG=PARENT_RELEASE+'/board_camera_ui.json'
PARENT_IDENTITY=PARENT_RELEASE+'/board_identity.sface_int8.json'


def camera_snapshot(m):
    value=m.get(8790,'/health');identity=value.get('identity') or {}
    result={k:value.get(k) for k in ('pid','capture_frames','detected_frames','capture_hz','detection_hz',
        'observation_age_ms','camera_error','detector_error','dpu_schedule','pipeline_metrics')}
    result.update(identity_backend=identity.get('backend'),face_targets=identity.get('face_targets'),
        feature_inference=identity.get('feature_inference'),identity_ready=identity.get('ready'),
        identity_error=identity.get('error'),identity_processed=identity.get('processed'),
        feature_status=identity.get('feature_status'))
    return result


def validate_state(state,*,injected=False,allow_completed_sface_fault=False):
    assert not injected
    assert not state['camera_error'] and not state['detector_error']
    assert state['identity_backend']=='DPU_SFACE_INT8' and state['identity_ready'] and not state['identity_error']
    assert state['observation_age_ms'] is not None and 0<=state['observation_age_ms']<750
    face=state['face_targets'];assert face['ready'] and not face['error']
    assert 0<=face['source_age_ms']<1000
    assert state['feature_inference']['kind']=='DPU_SFACE_INT8'
    assert state['feature_inference'].get('ready',True)
    jobs=state['dpu_schedule']['optional']
    sface=jobs.get('sface',{})
    if sface.get('disabled') or sface.get('overruns',0):
        assert allow_completed_sface_fault and sface['disabled'] and sface['overruns']>=1
        events=state['dpu_schedule']['optional_diagnostics']['fault_events']
        faults=[event for event in events if event['task_code']==2]
        assert len(faults)==sface['overruns']
        assert all(row['native_completed']==1 and row['native_status']==0 and not row['body_failed'] for row in faults)
    if jobs['yunet']['disabled']:
        # This is a preserved parent fault, not a candidate acceptance rule.
        policy=state['dpu_schedule']['yunet_recovery']
        assert face['backend']=='CPU_YUNET_FALLBACK_AFTER_DPU_OVERRUN'
        assert policy['phase']=='LATCHED' and policy['faults']==jobs['yunet']['overruns']==3
        assert policy['attempts']==policy['recoveries']==2
        events=state['dpu_schedule']['optional_diagnostics']['fault_events']
        faults=[row for row in events if row.get('task_code',1)==1]
        assert len(faults)==3 and faults[-1]['guard_exceeded']==1
        assert all(row['native_completed']==1 and row['native_status']==0 and not row['body_failed'] for row in faults)
    else:
        assert face['backend']=='DPU_YUNET_INT8'
        assert state['dpu_schedule']['yunet_recovery']['phase']=='RUNNING'


def validate_parent_state(state):
    return validate_state(state,allow_completed_sface_fault=True)


def validate_candidate_state(state):
    validate_state(state)
    schedule=state['dpu_schedule'];face=state['face_targets']
    assert face['backend']=='DPU_YUNET_INT8' and face['worker_alive'] and not face['fault_latched']
    assert face['worker_faults']==0
    assert all(not schedule['optional'].get(kind,{}).get('disabled',False)
               and schedule['optional'].get(kind,{}).get('overruns',0)==0
               for kind in ('yunet','sface'))
    assert schedule['yunet_recovery']['faults']==0
    assert schedule['diagnostic_failures']==0 and not schedule['diagnostic_snapshot_atomic_with_schedule']
    assert not schedule['owner_fenced']
    assert state['feature_inference']['ready'] and state['feature_status']['ready']
    assert face['freshness_metrics']['counters']['observed_gap_intervals']==0
    assert face['inference']['fallback_calls']==0


def wait_parent_ready(ops,*,clock=time.monotonic,sleep=time.sleep,timeout=30):
    until=clock()+timeout;previous=None;stable=0
    while clock()<until:
        try:
            assert ops.active('aura-avatar-ui.service') and ops.active('aura-camera-ui.service')
            state=ops.m.camera();validate_parent_state(state)
            stable=stable+1 if previous and state['pid']==previous['pid'] and state['capture_frames']>previous['capture_frames'] else 0
            previous=state
            if stable>=3:return state
        except Exception:previous=None;stable=0
        sleep(.5)
    raise RuntimeError('Pinned parent did not provide stable frames')


def rewrite_unit(raw,old_root,new_root,*,injected=False):
    assert not injected
    old_root,new_root=str(old_root),str(new_root)
    text=raw.decode();assert text.count(old_root)>=2 and '[Service]\n' in text
    text=text.replace(old_root,new_root)
    assert old_root not in text and text.count(new_root+'/runtime_entry.py')==1
    assert text.count(new_root+'/board_camera_ui.json')==1 and 'AURA_EXPERIMENT_GIL_MS=1' in text
    return text.encode()
