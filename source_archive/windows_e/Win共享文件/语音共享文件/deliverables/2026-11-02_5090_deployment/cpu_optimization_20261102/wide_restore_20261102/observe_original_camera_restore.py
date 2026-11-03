"""Observe the one real original start; no restart, consume, binding or Native call."""
platform(); paused_gui(); source = source_snapshot()
intent = json.loads(regular(TX/'camera-start-intent.json'))
require(intent['checkpoint_pin'] == SEAL['genuine_checkpoint_pin'] and intent['boot_id'] == BOOT, 'Start intent differs')
deadline = time.monotonic() + 35
first = None
while True:
    state = show('aura-camera-ui.service')
    require(state['ActiveState'] != 'failed', 'Original camera failed; no restart allowed')
    try:
        current, health, state = alive_camera()
        if first and first[0] == current and health['capture_frames'] > first[1]['capture_frames'] and health['detected_frames'] > first[1]['detected_frames']:
            break
        first = current, health
    except (OSError, ValueError, KeyError, RuntimeError, http.client.HTTPException):
        first = None
    if time.monotonic() >= deadline:
        print(json.dumps(dict(status='ORIGINAL_CAMERA_START_PENDING_OBSERVE_ONLY', camera_unit=state,
                              start_resubmitted=False, GUI_started=False, motion_requested=False)))
        raise SystemExit(0)
    time.sleep(1)

require(current['pid'] != FRESH['camera_owner']['pid'], 'Original old owner was not replaced')
checkpoint_raw = pinned(SEAL['sealed_identical_final_pin']); checkpoint = json.loads(checkpoint_raw)
require(regular(CP) == checkpoint_raw, 'Original checkpoint changed after start')
seed, auxiliary = checkpoint['seed'], checkpoint['auxiliary']
handoff = health['dpu_schedule']['protection_handoff']
require(handoff['mode'] == 'native_exact_same_boot' and handoff['seed_sha256'] == CP_SHA
        and handoff['source_pid'] == seed['source_pid']
        and str(handoff['source_birth_ticks']) == str(seed['source_birth_ticks'])
        and handoff['previous_kernel_history'] == checkpoint['previous_kernel_history'], 'Original bootstrap did not inherit exact final/history')
require(handoff['native_unit_sha256'] == original['NATIVE_UNIT']
        and handoff['predecessor_unit_sha256'] == checkpoint['source_unit_sha256']
        and handoff['native_abi_compatible_migration'] is True, 'Original in-memory migration differs')
audit_path = OP/('recovery-audit-' + str(current['pid']) + '.json')
require(handoff['operator_recovery_audit'] == str(audit_path), 'Actual bootstrap audit pointer differs')
audit_raw = regular(audit_path); audit = json.loads(audit_raw)
settings = json.loads(regular(OP/'settings.json'))
require(audit['checkpoint_sha256'] == CP_SHA and audit['checkpoint_unit_sha256'] == checkpoint['source_unit_sha256']
        and audit['exact_seed_before_operator_request'] == seed and audit['request'] == settings
        and audit['artificial_counter_reset'] is False and audit['mechanical_actions'] == 0, 'Original audit exact-seed proof differs')
marker_path = Path(str(CP) + '.native-consumed-' + CP_SHA)
marker_raw = regular(marker_path)
require(marker_raw == (CP_SHA + '\n').encode(), 'Original consumption marker differs')

run_path = OPS/('native-run-' + BOOT + '-' + str(current['pid']))/'config.json'
run_raw = regular(run_path); run = json.loads(run_raw); native = run['native_execution']
old_run = json.loads(pinned(FRESH['normal_stop_expected']['source_closure']['owner_run_config']))
require(native['seed'] == SEAL['genuine_checkpoint_pin'] and native['checkpoint_output'] == str(CP), 'Original writer used a different final/output')
old_native, actual_native = copy.deepcopy(old_run['native_execution']), copy.deepcopy(native)
old_native.pop('seed'); actual_native.pop('seed')
require(old_native == actual_native, 'Original persisted native configuration changed beyond final pointer')
require(native['source_manifest'] == FRESH['normal_stop_expected']['source_closure']['native_python_manifest']['path']
        and native['source_manifest_sha256'] == FRESH['normal_stop_expected']['source_closure']['native_python_manifest']['sha256'], 'Original Native manifest changed')
writer_sources = []
for path, sha in source['selected']['source_sha256'].items():
    if path.endswith('.py'):
        raw = regular(path)
        if b'native-run-' in raw and b'config.json' in raw:
            writer_sources.append(dict(path=path, sha256=sha))
require(writer_sources, 'Pinned original native run-config writer not present in selected source closure')
owners = hardware_owners()
require(owners == dict(dpu=[current], motion=[]), 'Original camera is not the sole DPU owner or motion owner exists')

bound_checks = dict(primary=True, sface=True, optional=True, recovery=True)
for sample in (first[1], health):
    schedule = sample['dpu_schedule']; features = sample['identity']['feature_inference']
    for key in ('primary_calls', 'primary_period_overruns'):
        require(schedule[key] >= seed[key], 'Restored primary cumulative counter regressed')
    for key in original['FEATURES']:
        require(features[key] >= auxiliary['sface_counters'][key], 'Restored SFace cumulative counter regressed')
    for i,task in enumerate(('yunet', 'sface'), 1):
        now, prior = schedule['optional'][task], auxiliary['inherited_optional'][task]
        for key in ('calls', 'native_completed', 'native_failures', 'not_submitted', 'overruns'):
            require(now[key] >= prior[key], 'Restored optional cumulative counter regressed')
        require(now['native_completed'] >= seed['completed'][i], 'Restored Native completion counter regressed')
        for key in ('native_failures', 'not_submitted', 'overruns'):
            require(now[key] >= seed[key][i], 'Restored Native task cumulative counter regressed')
        for key in ('faults', 'attempts', 'recoveries'):
            require(now['recovery'][key] >= max(prior['recovery'][key], seed['recovery'][i-1][key]), 'Restored recovery cumulative counter regressed')
        require(now['recovery']['history_opaque'] == prior['recovery']['history_opaque'], 'Restored opaque history changed')
        if all(now['recovery'][k] == prior['recovery'][k] for k in ('faults', 'attempts')):
            require(now['recovery']['probe_successes'] >= prior['recovery']['probe_successes'], 'Same-generation recovery probe progress regressed')

require(regular(audit_path) == audit_raw and regular(run_path) == run_raw and process(current['pid']) == current,
        'Original owner or provenance changed during observation')
for pin in (SEAL['expected_pin'], SEAL['original_validation_pin']): pinned(pin)
samples = [dict(monotonic_ns=time.monotonic_ns(), capture_frames=s['capture_frames'], detected_frames=s['detected_frames'],
                capture_age_ms=s['capture_age_ms'], observation_age_ms=s['observation_age_ms'],
                primary_calls=s['dpu_schedule']['primary_calls'], primary_period_overruns=s['dpu_schedule']['primary_period_overruns'],
                sface_counters={k:s['identity']['feature_inference'][k] for k in original['FEATURES']}) for s in (first[1],health)]
result = dict(status='ORIGINAL_CAMERA_EXACT_FINAL_RESTORED_AND_VERIFIED', boot_id=BOOT, camera_owner=current,
              camera_service=state, checkpoint_pin=SEAL['genuine_checkpoint_pin'],
              checkpoint_source_owner=FRESH['camera_owner'], bootstrap_handoff=handoff,
              run_config=dict(path=str(run_path), sha256=digest(run_raw)), original_writer_source_pins=writer_sources,
              audit_pin=dict(path=str(audit_path), sha256=digest(audit_raw)), audit_status=audit.get('status'),
              audit_status_is_operator_request_state_not_native_completion=True,
              marker=dict(path=str(marker_path), sha256=digest(marker_raw), bytes=len(marker_raw)),
              exact_seed_preserved=True, original_current_cumulative_lower_bounds_checked=bound_checks,
              complete_19_history_original_validation_preserved=SEAL['original_validation_pin'],
              history_head_unchanged=True, original_native_Python222_operator7_C6_library704_verified=True,
              startup_sha256=digest(source['startup_raw']), selected_source_count_before=len(source['selected']['source_sha256']),
              source_progress_samples=samples, sole_hardware_owners=owners,
              GUI_started=False, motion_requested=False, binding_written=False,
              Native_seed_counter_marker_or_source_modified_by_this_script=False)
require(not os.path.lexists(TX/'camera-restore-verified.json'), 'Existing verification receipt: reconcile it')
create(TX/'camera-restore-verified.json', result)
print(json.dumps(result))
