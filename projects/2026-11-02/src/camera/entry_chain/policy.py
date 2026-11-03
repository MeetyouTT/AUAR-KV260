"""Decisions only; no service, device or filesystem operations."""
def condition(source_boot, current_boot, phase, role):
    if role not in ('camera','gui'):raise ValueError('Unknown maintenance role')
    if current_boot == source_boot:return phase in ('PREPARED','ARMING','ARMED','CANCELLED')
    if phase in ('PREPARED','ARMING','CANCELLED','OLD_RESTORED'):return True
    if role == 'camera':return phase in ('NATIVE_START','NATIVE_READY','OBSERVING','ACCEPTED','ROLLBACK_READY')
    return phase in ('NATIVE_READY','OBSERVING','ACCEPTED','ROLLBACK_READY')


def benchmark_safe(report, checkpoint, returncode, process_alive):
    if process_alive:return False
    if report and report.get('unsafe'):return False
    if report and report.get('cleanup_confirmed') is True:return True
    if checkpoint and checkpoint.get('stage') == 'finished_confirmed_idle':
        return not checkpoint.get('completion_unconfirmed') and not checkpoint.get('unsafe')
    # CLI status2 is only the reviewed pre-model Blocked exit. A partial
    # execution has a journal and must prove confirmed cleanup instead.
    return returncode == 2 and not checkpoint


def require_native_healthy(health):
    schedule=health['dpu_schedule']
    if health.get('camera_error') or health.get('detector_error'):raise ValueError('Camera path failed')
    if not schedule.get('native_critical') or schedule.get('native_abi') != 2:
        raise ValueError('Expected native execution path')
    if schedule['owner_fenced'] or schedule.get('quiesced'):raise ValueError('Native owner unavailable')
    identity=health['identity'];face=identity['face_targets']
    if not face['worker_alive'] or face.get('error'):raise ValueError('Face worker unavailable')
    if face['backend'] != 'DPU_YUNET_INT8' or not identity['feature_inference']['ready']:
        raise ValueError('All three model paths must be available')
    if any(schedule['optional'][name]['disabled'] for name in ('yunet','sface')):
        raise ValueError('Optional protection active')
    return True


def counters(health):
    schedule=health['dpu_schedule'];face=health['identity']['face_targets']
    return dict(pid=health['pid'],detected=health['detected_frames'],
        primary_overruns=schedule['primary_period_overruns'],
        faults={name:schedule['optional'][name]['overruns'] for name in ('yunet','sface')},
        gaps=face['freshness_metrics']['counters']['observed_gap_intervals'],
        sface_completed=health['identity']['feature_inference']['completed'])


def window_result(before, after, seconds):
    if seconds <= 0:raise ValueError('Positive interval required')
    if before['pid'] != after['pid']:raise ValueError('Counter process changed')
    primary=after['primary_overruns']-before['primary_overruns']
    gaps=after['gaps']-before['gaps']
    faults={k:after['faults'][k]-before['faults'][k] for k in before['faults']}
    frames=after['detected']-before['detected']
    sface=after['sface_completed']-before['sface_completed']
    if min(primary,gaps,frames,sface,*faults.values()) < 0:raise ValueError('Counters decreased')
    return dict(seconds=seconds,yolo_hz=frames/seconds,new_primary_overruns=primary,
        new_gaps=gaps,new_optional_faults=faults,new_sface_completions=sface,
        short_window_passed=frames/seconds>=9.5 and not primary and not gaps and not any(faults.values()),
        sustained_three_model_load_verified=sface>0)
