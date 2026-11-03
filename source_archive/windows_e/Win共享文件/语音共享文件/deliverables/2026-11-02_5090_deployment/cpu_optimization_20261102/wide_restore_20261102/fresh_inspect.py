"""Granted-phase public metadata only; original source-closure checks, no stop."""
import hashlib
import http.client
import json
import os
from pathlib import Path
import subprocess
import time

space = {'__name__': 'reviewed_original_stop_metadata'}
exec(compile(STOP_SOURCE, '<pinned-original-stop-helper>', 'exec'), space)
regular, digest, owner = space['regular'], space['digest'], space['owner']
require = space['require']

def show(name, properties):
    r = subprocess.run(['systemctl', 'show', name, '--property=' + properties],
                       capture_output=True, text=True, timeout=5)
    require(r.returncode == 0, 'Service metadata unavailable')
    return dict(row.split('=', 1) for row in r.stdout.splitlines() if '=' in row)

def get(port, path):
    c = http.client.HTTPConnection('127.0.0.1', port, timeout=3)
    try:
        c.request('GET', path)
        r = c.getresponse(); raw = r.read(2097153)
        require(r.status == 200 and len(raw) <= 2097152, 'Public metadata unavailable')
        return json.loads(raw)
    finally:
        c.close()

boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
require(boot == GRANT['boot_id'], 'Boot differs from active phase')
startup_path = '/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json'
startup_raw = regular(startup_path)
require(digest(startup_raw) == GRANT['startup_sha256'], 'Startup differs from active phase')
startup = json.loads(startup_raw); aura = Path(startup['runtime']) / 'aura'
pins = startup['component_sha256']
require(pins == GRANT['component_sha256'] and len(pins) == 380, 'Phase component closure differs')
for name, sha in pins.items():
    require(digest(regular(aura / name)) == sha, 'Component source changed')
for key in ('gui_owner', 'gtk_owner', 'camera_owner'):
    require(owner(GRANT[key]) == GRANT[key], 'Phase process owner differs')
properties = 'MainPID,ControlPID,ActiveState,SubState,Job,Result,ExecMainStatus,Restart,KillMode,SendSIGKILL,TimeoutStopUSec'
gui = show('aura-avatar-ui.service', properties)
camera = show('aura-camera-ui.service', properties)
for state, key in ((gui, 'gui_owner'), (camera, 'camera_owner')):
    require(state['MainPID'] == str(GRANT[key]['pid']) and state['ControlPID'] == '0'
            and state['ActiveState'] == 'active' and state['SubState'] == 'running'
            and not state['Job'] and state['Result'] == 'success', 'Original service is not idle/running')
view = get(8783, '/api/state')
hands = view['handsfree_dialogue']; business = view['board_business']
speaker = business['speaker']; face = business['dialogue']['voice_enrollment']
require(hands.get('enabled') is False and hands.get('microphone_open') is False
        and hands.get('state') == 'PAUSED' and view.get('phase') == 'IDLE'
        and view.get('playing') is False and not view.get('pending_job')
        and speaker.get('active') is False and speaker.get('queued_or_active') == 0
        and face.get('active') is False and face.get('stage') == 'idle'
        and view['manual_pan'].get('automatic_following') is False
        and view['runtime_faults'].get('count') == 0, 'GUI business is not paused/idle')
require(speaker.get('identity_match_threshold') == 0.35, 'Accepted voice threshold differs')
require(json.loads(regular('/home/root/.local/share/aura-board-business/listening_preference.json'))
        == {'version': 1, 'enabled': False}, 'Saved listening preference changed')
health = get(8790, '/health'); camera_view = get(8790, '/v1/ui/status')
schedule = health['dpu_schedule']; features = health['identity']['feature_inference']
require(health['pid'] == GRANT['camera_owner']['pid'] and health['board_boot_id'] == boot
        and health['motion_command_emitted'] is False and health['identity']['ready'] is True
        and not health['identity'].get('error')
        and not any(health.get(k) for k in ('camera_error', 'detector_error', 'preview_error')),
        'Original camera is not healthy')
require(camera_view['modules']['identity']['enrollment_sampling']['stage'] == 'idle', 'Camera sampler is not idle')
require(schedule['native_critical'] is True and schedule['native_abi'] == 2
        and schedule['owner_fenced'] is False and schedule['quiesced'] is False, 'Native owner state differs')
require(all(type(features[k]) is int and features[k] >= 0 for k in space['FEATURES']), 'SFace current bounds unavailable')
for task in ('yunet', 'sface'):
    optional = schedule['optional'][task]
    require(all(type(optional[k]) is int and optional[k] >= 0 for k in
                ('calls', 'native_completed', 'native_failures', 'not_submitted', 'overruns')), 'Optional current bounds unavailable')
    recovery = optional['recovery']
    require(all(type(recovery[k]) is int and recovery[k] >= 0 for k in
                ('faults', 'attempts', 'recoveries', 'probe_successes'))
            and type(recovery['history_opaque']) is bool, 'Recovery current bounds unavailable')
ui = json.loads(regular(aura / 'config/board_avatar_gtk.json'))
selected = ui['board_business']['face_readback']
require(selected == {k: GRANT['selected_face_binding'][k] for k in ('path', 'sha256')}, 'Selected binding changed')
binding = json.loads(space['pinned'](selected)); run_path = binding['camera_config']
run_raw = regular(run_path); run = json.loads(run_raw); native = run['native_execution']
operator = space['OPERATOR']
entry = show('aura-camera-ui.service', 'ExecStart,ExecStop,FragmentPath,DropInPaths')
unit_paths = {entry['FragmentPath']} | set(entry['DropInPaths'].split())
closure = dict(selected_readback=selected,
               owner_run_config=dict(path=run_path, sha256=digest(run_raw)),
               native_python_manifest=dict(path=native['source_manifest'], sha256=native['source_manifest_sha256']),
               native_operator_manifest=dict(path=str(operator / 'runtime-manifest.json'), sha256=digest(regular(operator / 'runtime-manifest.json'))),
               native_c_unit_manifest=dict(path=str(operator / 'source-manifest.json'), sha256=space['NATIVE_UNIT']),
               native_library=dict(path=str(operator / 'libaura_native_operator.so'), sha256=space['NATIVE_LIBRARY']),
               camera_systemd=dict(properties=entry, source_sha256={path: digest(regular(path)) for path in unit_paths}))
expected = dict(schema='aura-camera-normal-stop-expected-1', boot_id=boot,
                all_other_writers_frozen=True, startup=dict(path=startup_path, sha256=digest(startup_raw)),
                camera_owner=GRANT['camera_owner'], stopped_gui_owners=[GRANT['gui_owner'], GRANT['gtk_owner']],
                transaction_directory=SESSION + '/camera-stop', source_closure=closure)
space['source_closure'](expected, aura, pins)
observed_ns = time.monotonic_ns()
handoff = schedule.get('protection_handoff') or {}
archive_directory = Path(native['new_boot_marker_directory']) / 'archive'
archives = []
for path in sorted(archive_directory.glob('*.json')):
    raw = regular(path, 262144); doc = json.loads(raw)
    archives.append(dict(path=str(path), sha256=digest(raw), schema=doc.get('schema'),
                         current_boot=doc.get('current_boot'), source_boot=doc.get('source_boot'),
                         source_checkpoint_sha256=doc.get('source_checkpoint_sha256'),
                         history_is_lower_bound=doc.get('history_is_lower_bound')))
require(regular(startup_path) == startup_raw and owner(GRANT['camera_owner']) == GRANT['camera_owner'], 'Source changed during fresh inspection')
print(json.dumps(dict(schema='aura-cpu-protected-wide-fresh-inspection-1', status='FRESH_SOURCE_AND_PAUSED_CAMERA_METADATA_VERIFIED',
                     boot_id=boot, startup_sha256=digest(startup_raw), component_count=380,
                     gui_owner=GRANT['gui_owner'], gtk_owner=GRANT['gtk_owner'], camera_owner=GRANT['camera_owner'],
                     gui_unit=gui, camera_unit=camera, normal_stop_expected=expected,
                     prestop_source_observation=dict(schema='aura-live-native-prestop-source-1', boot_id=boot,
                         source_owner=GRANT['camera_owner'], observed_mono_ns=observed_ns,
                         head=handoff.get('previous_kernel_history'), original_protection_handoff=handoff,
                         archive_directory_metadata=archives),
                     current_observed_bounds=dict(primary_calls=schedule['primary_calls'],
                         primary_period_overruns=schedule['primary_period_overruns'],
                         sface={k: features[k] for k in space['FEATURES']}, optional=schedule['optional']),
                     board_files_written=False, service_actions=False, native_context_created=False,
                     model_database_or_media_opened=False), sort_keys=True))
