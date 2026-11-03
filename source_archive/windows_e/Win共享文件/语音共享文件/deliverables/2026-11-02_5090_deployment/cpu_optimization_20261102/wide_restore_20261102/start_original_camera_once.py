"""One original service start, after fresh original wide/STOP and sealed-final checks."""
context = platform(); paused_gui(); snapshot = source_snapshot()
validator = {'__name__': 'unchanged_original_protected_guard'}
exec(compile(VALIDATOR_SOURCE, '<unchanged-original-full-history-validator>', 'exec'), validator)
expected = FRESH['normal_stop_expected']
validator['guard'](expected)
for pin in (SEAL['expected_pin'], SEAL['original_validation_pin']): pinned(pin)
sealed_raw = pinned(SEAL['sealed_identical_final_pin'])
require(pinned(SEAL['genuine_checkpoint_pin']) == sealed_raw, 'Fresh original final differs from seal')
checkpoint = json.loads(sealed_raw)
require(checkpoint['source_unit_sha256'] == original['NATIVE_UNIT']
        and checkpoint['seed']['source_pid'] == FRESH['camera_owner']['pid']
        and str(checkpoint['seed']['source_birth_ticks']) == FRESH['camera_owner']['birth_ticks'], 'Fresh source owner or unit differs')
require(not os.path.lexists(str(CP) + '.native-consumed-' + CP_SHA), 'Fresh final is already consumed')
jobs = subprocess.run(['systemctl', 'list-jobs', '--no-legend', '--no-pager'], capture_output=True, text=True, timeout=5)
require(jobs.returncode == 0 and not jobs.stdout.strip(), 'Pending systemd job prevents original start')
require(not os.path.lexists(TX), 'Existing camera-restore transaction: observe; never resubmit')
TX.mkdir(mode=0o700)
intent = dict(schema='aura-original-camera-start-intent-2', boot_id=BOOT,
              utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), monotonic_ns=time.monotonic_ns(),
              checkpoint_pin=SEAL['genuine_checkpoint_pin'], source_owner=FRESH['camera_owner'],
              action='systemctl start --no-block aura-camera-ui.service', single_submission=True,
              original_wide_and_IDSTOP_verified=True, startup_sha256=digest(snapshot['startup_raw']))
create(TX/'camera-start-intent.json', intent)
require(regular(snapshot['startup_path']) == snapshot['startup_raw'] and regular(CP) == sealed_raw
        and not os.path.lexists(str(CP)+'.native-consumed-'+CP_SHA), 'Source changed immediately before start')
validator['guard'](expected)
started = subprocess.run(['systemctl', 'start', '--no-block', 'aura-camera-ui.service'], capture_output=True, text=True, timeout=8)
result = dict(status='ORIGINAL_CAMERA_START_REQUESTED_ONCE', boot_id=BOOT, start_returncode=started.returncode,
              checkpoint_pin=SEAL['genuine_checkpoint_pin'], context=context, intent_path=str(TX/'camera-start-intent.json'),
              camera_unit=show('aura-camera-ui.service'), GUI_started=False, motion_requested=False,
              Native_seed_counter_marker_or_source_modified_by_this_script=False)
create(TX/'camera-start-request.json', result)
print(json.dumps(result)); require(started.returncode == 0, 'Original start submission failed; observe without resending')
