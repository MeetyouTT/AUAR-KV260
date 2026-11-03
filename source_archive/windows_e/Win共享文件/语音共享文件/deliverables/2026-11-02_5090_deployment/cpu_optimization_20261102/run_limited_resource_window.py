"""One granted 40 s passive sample, with fresh metadata guards and no controls."""
import datetime
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
HANDOFF = HERE.parent / 'other_components_20261102/live_enrollment_20261102/THRESHOLD_035_READONLY_WINDOW_HANDOFF.json'
REVOCATION = HERE / 'LIMITED_RESOURCE_WINDOW_REVOCATION.json'
LABEL = 'a6d4_main_gtk_after_035'
assert not REVOCATION.exists(), 'This single-use window was revoked; do not run this prepared observer.'
receipt = json.loads(HANDOFF.read_text(encoding='utf-8-sig'))
assert receipt['schema'] == 'aura-limited-cpu-readonly-window-1'
assert datetime.datetime.now(datetime.timezone.utc) < datetime.datetime.fromisoformat(receipt['may_start_before_host_utc'])
assert receipt['paused_idle_observed'] is True and receipt['voice_and_face_sampling_idle'] is True
assert receipt['no_business_jobs_or_playback'] is True
assert receipt['no_service_or_source_or_config_or_axis_or_model_operations'] is True
expected = {name + '_pid': receipt[key]['pid'] for name, key in
            (('camera', 'camera_owner'), ('gui', 'gui_owner'), ('gtk', 'gtk_owner'))}
source_path = HERE.parent / 'performance_check_20261102/collect_board_performance.py'
source = source_path.read_text(encoding='utf-8')
guard = r'''
def check_pin(path, expected_sha):
    path = Path(path)
    assert path.is_absolute() and not path.is_symlink() and path.resolve() == path, 'PUBLIC_PIN_REDIRECTED'
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == expected_sha, 'PUBLIC_PIN_CHANGED'
    return raw

def current_owner(expected_owner):
    root = Path('/proc') / str(expected_owner['pid'])
    birth = root.joinpath('stat').read_text().rsplit(')', 1)[1].split()[19]
    result = dict(pid=expected_owner['pid'], birth_ticks=birth,
                  command_sha256=hashlib.sha256(root.joinpath('cmdline').read_bytes()).hexdigest())
    assert root.joinpath('stat').read_text().rsplit(')', 1)[1].split()[19] == birth, 'OWNER_CHANGED_DURING_READ'
    assert result == expected_owner, 'OWNER_CHANGED'
    return result

def window_guard(stage, full_source=False):
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == HANDOFF['boot_id'], 'BOOT_CHANGED'
    for key in ('camera_owner', 'gui_owner', 'gtk_owner'):
        current_owner(HANDOFF[key])
    startup_path = Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json')
    raw = check_pin(startup_path, HANDOFF['startup_sha256'])
    checked_sources = None
    if full_source:
        startup = json.loads(raw)
        aura = Path(startup['runtime']) / 'aura'
        pins = startup['component_sha256']
        assert len(pins) == 380, 'COMPONENT_COUNT_CHANGED'
        for name, sha in pins.items():
            check_pin(aura / name, sha)
        for name, sha in HANDOFF['source_after'].items():
            assert pins[name] == sha, 'AUTHORIZED_VOICE_SOURCE_CHANGED'
        for name, sha in {
            'board/interaction/ui_services.py': 'e4dedf9b3d56d22d9eb93de1e96ad1a69870d553ea50f7dd5082b21e19f381c9',
            'tools/board_camera_preview.py': '67d6c0f2b24ea97e20fdcc7b3383b6444269a6e26f5deb566f2b88746b7daf9b'
        }.items():
            assert pins[name] == sha, 'GTK_OPTIMIZATION_SOURCE_CHANGED'
        ui = json.loads((aura / 'config/board_avatar_gtk.json').read_bytes())
        spec = ui['board_business']['face_readback']
        binding_pin = HANDOFF['selected_face_binding']
        assert spec['path'] == binding_pin['path'] and spec['sha256'] == binding_pin['sha256'], 'SELECTED_BINDING_CHANGED'
        binding = json.loads(check_pin(spec['path'], spec['sha256']))
        assert len(binding['source_sha256']) == binding_pin['source_pin_count'], 'SELECTED_SOURCE_COUNT_CHANGED'
        for path, sha in binding['source_sha256'].items():
            check_pin(path, sha)
        camera = HANDOFF['camera_owner']
        assert (binding['board_boot_id'] == HANDOFF['boot_id'] and binding['camera_pid'] == camera['pid']
                and str(binding['camera_start_ticks']) == camera['birth_ticks']
                and binding['camera_cmdline_sha256'] == camera['command_sha256']), 'SELECTED_OWNER_CHANGED'
        assert startup_path.read_bytes() == raw, 'STARTUP_CHANGED_DURING_CHECK'
        checked_sources = dict(component_count=380, selected_source_count=len(binding['source_sha256']),
                               GTK_optimization_sources_match=True, authorized_voice_sources_match=True)
    value, _ = get(8783, '/api/state')
    camera_status, _ = get(8790, '/v1/ui/status')
    hands = value['handsfree_dialogue']
    business = value['board_business']
    speaker = business['speaker']
    face = business['dialogue']['voice_enrollment']
    sampling = camera_status['modules']['identity']['enrollment_sampling']
    assert value.get('phase') == 'IDLE' and value.get('playing') is False and not value.get('pending_job'), 'BUSINESS_NOT_IDLE'
    assert hands.get('enabled') is False and hands.get('microphone_open') is False and hands.get('state') == 'PAUSED', 'LISTENING_CHANGED'
    assert speaker.get('active') is False and speaker.get('queued_or_active') == 0, 'VOICE_RETEST_OR_JOB_STARTED'
    assert speaker.get('identity_match_threshold') == 0.35, 'VOICE_THRESHOLD_CHANGED'
    assert face.get('active') is False and face.get('stage') == 'idle' and sampling.get('stage') == 'idle', 'ENROLLMENT_STARTED'
    assert value.get('ui_page') == 'main' and value['character_pair'].get('state') == 'READY' and value['avatar_display'].get('visible') is True, 'GUI_SCENE_CHANGED'
    assert value['runtime_faults'].get('count') == 0, 'GUI_RUNTIME_FAULT'
    assert value['manual_pan'].get('automatic_following') is False, 'FOLLOW_STATE_CHANGED'
    return dict(stage=stage, monotonic=time.monotonic(), sequence=value.get('sequence'),
                main_ready_visible=True, paused_idle=True, voice_and_face_sampling_idle=True,
                voice_match_threshold=0.35, full_source=checked_sources)
'''
marker = '# Only metadata supplied by the host; no application code is loaded.'
assert source.count(marker) == 1
source = source.replace(marker, guard + '\n' + marker)
source = source.replace('snapshots = []\nhealth_samples = []', 'snapshots = []\nhealth_samples = []\nwindow_guards = []\nwindow_stop_reason = None')
needle = '    snapshots.append(sample())'
assert source.count(needle) == 1
source = source.replace(needle, """    try:
        window_guards.append(window_guard(index, full_source=index in (0, 20)))
    except (OSError, ValueError, KeyError, TypeError, AssertionError, http.client.HTTPException) as exc:
        window_stop_reason = dict(type=type(exc).__name__, fixed_reason=str(exc) if isinstance(exc, AssertionError) else 'READ_ONLY_GUARD_UNAVAILABLE')
        break
    snapshots.append(sample())""")
source = source.replace("assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == BOOT\nprint", """if window_stop_reason is None:
    try:
        window_guards.append(window_guard('after', full_source=True))
    except (OSError, ValueError, KeyError, TypeError, AssertionError, http.client.HTTPException) as exc:
        window_stop_reason = dict(type=type(exc).__name__, fixed_reason=str(exc) if isinstance(exc, AssertionError) else 'FINAL_READ_ONLY_GUARD_UNAVAILABLE')
print""")
source = source.replace("'duration_seconds':snapshots[-1]['monotonic']-snapshots[0]['monotonic'],", "'duration_seconds':snapshots[-1]['monotonic']-snapshots[0]['monotonic'] if snapshots else 0,\n    'window_guards':window_guards,'window_stop_reason':window_stop_reason,'limited_window_completed':len(snapshots)==21 and window_stop_reason is None,")
code = 'EXPECTED = ' + repr(expected) + '\nHANDOFF = ' + repr(receipt) + '\n' + source
compile(code, '<limited-passive-window>', 'exec')
helper = HERE.parent.parent / '2026-10-18_board_dialogue/board_ssh.py'
assert hashlib.sha256(helper.read_bytes()).hexdigest() == '6aefec94f620c6c86fa6b17c83613b22c8599e899cb2c2fcaf36c9cdd17c7373'
attempt = HERE / ('ATTEMPT_' + LABEL + '.json')
output = HERE / ('RESOURCE_' + LABEL + '.json')
assert not output.exists()
started = datetime.datetime.now(datetime.timezone.utc).isoformat()
with attempt.open('x', encoding='utf-8') as stream:
    json.dump(dict(host_started_utc=started, handoff_sha256=hashlib.sha256(HANDOFF.read_bytes()).hexdigest(),
                   collector_sha256_lf=hashlib.sha256(code.encode()).hexdigest(), no_retry=True), stream, indent=2)
spec = importlib.util.spec_from_file_location('limited_resource_transport', helper)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
assert not REVOCATION.exists(), 'Limited window revoked before SSH submission'
assert datetime.datetime.now(datetime.timezone.utc) < datetime.datetime.fromisoformat(receipt['may_start_before_host_utc'])
result = json.loads(module.ssh('/usr/bin/python3 -B -I -S -', code, timeout=65))
with output.open('x', encoding='utf-8') as stream:
    json.dump(dict(stage='gtk_after', run_label=LABEL, host_started_utc=started,
                   host_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   time_basis='Host UTC chronology; board monotonic durations; board wall clock may be unsynchronised',
                   collector_sha256_lf=hashlib.sha256(code.encode()).hexdigest(),
                   observer_change='Original /proc resource formulas; 2 s metadata guards added for the bounded handoff. This overhead differs from the old baseline.',
                   board_result=result), stream, indent=2)
    stream.write('\n')
print(json.dumps(dict(output=str(output), completed=result['limited_window_completed'],
                      stop_reason=result['window_stop_reason'], duration=result['duration_seconds'])))
