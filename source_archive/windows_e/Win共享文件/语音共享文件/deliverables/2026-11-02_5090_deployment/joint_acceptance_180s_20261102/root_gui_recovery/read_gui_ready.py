import hashlib
from pathlib import Path
assert Path("/proc/sys/kernel/random/boot_id").read_text().strip()=='a6d4a069-e9b0-4065-8df7-dc23556b168e'
assert hashlib.sha256(Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13/startup/config.json').read_bytes()).hexdigest()=='c1154308fcd25a9c8d957f33c5e2a4db0a0ef73e7656eb5aa437e29af9cd123b'
"""Fresh GUI/camera/enrollment readiness metadata only. No axis or identity values."""
import ast
import copy
import datetime
import hashlib
import http.client
import json
from pathlib import Path
import subprocess
import time

ROOT = Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
TARGET = 'board/identity/voice_enrollment.py'
EXPECTED = 'a9113ba40efc49828ee158554b2dae70485858396680918458f6f96bba16bacb'

def digest(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def owner(pid):
    if not pid: return None
    path = Path('/proc') / str(pid)
    if not path.is_dir(): return None
    return {'pid': int(pid), 'birth_ticks': path.joinpath('stat').read_text().rsplit(')', 1)[1].split()[19],
            'command_sha256': digest(path / 'cmdline')}

def unit(name):
    r = subprocess.run(['systemctl', 'show', name, '--property=MainPID,ActiveState,SubState,Job,Result,ExecMainStatus'], capture_output=True, text=True, timeout=4)
    assert r.returncode == 0
    return dict(row.split('=', 1) for row in r.stdout.splitlines() if '=' in row)

def get(port, path):
    c = http.client.HTTPConnection('127.0.0.1', port, timeout=3)
    try:
        c.request('GET', path); r = c.getresponse(); data = r.read(2097153)
        assert r.status == 200 and len(data) <= 2097152
        return json.loads(data)
    finally: c.close()

def known(v, choices): return v if type(v) is str and v in choices else None

raw = (ROOT / 'startup/config.json').read_bytes(); startup = json.loads(raw); aura = Path(startup['runtime']) / 'aura'
pins = startup['component_sha256']
result = {'schema': 'aura-voice-retry-readiness-1', 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip(), 'startup_sha256': hashlib.sha256(raw).hexdigest(),
          'component_count': len(pins), 'all_component_pins_match': all(digest(aura / k) == v for k, v in pins.items()),
          'voice_fix_source_and_pin_match': digest(aura / TARGET) == pins[TARGET] == EXPECTED,
          'gui_unit': unit('aura-avatar-ui.service'), 'camera_unit': unit('aura-camera-ui.service'),
          'read_only': True, 'raw_state_or_identity_values_exported': False, 'axis_read_or_changed': False}
result['gui_owner'] = owner(int(result['gui_unit']['MainPID']))
result['camera_owner'] = owner(int(result['camera_unit']['MainPID']))
if result['gui_owner']:
    launch = json.loads((Path(startup['runtime']) / 'launch.json').read_bytes())
    result['launch_owner_matches_current_service'] = launch['boot_id'] == result['boot_id'] and launch['supervisor_pid'] == result['gui_owner']['pid'] and launch['service'] == 'aura-avatar-ui.service'
    result['gtk_owner'] = owner(launch['pid'])
    source_mtime = (aura / TARGET).stat().st_mtime
    mtime_comparable = source_mtime <= time.time() and bool(result['gtk_owner'])
    result['voice_source_mtime_comparison_applicable'] = mtime_comparable
    result['voice_source_mtime_before_gtk_start'] = (source_mtime < time.time() - time.monotonic() + int(result['gtk_owner']['birth_ticks']) / 100) if mtime_comparable else None
ui = json.loads((aura / 'config/board_avatar_gtk.json').read_bytes()); spec = ui['board_business']['face_readback']; binding_raw = Path(spec['path']).read_bytes(); binding = json.loads(binding_raw)
verifier = aura / 'board/runtime/audio/face_gallery_readback.py'; source = verifier.read_bytes()
assert hashlib.sha256(source).hexdigest() == 'b77c32b3863b9464006ac1bb7f16c8f767113925d9142d77e4755f1ce365527e'
tree = ast.parse(source); klass = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'FaceGalleryReadback')
method = copy.deepcopy(next(n for n in klass.body if isinstance(n, ast.FunctionDef) and n.name == '_verify')); method.decorator_list = []
space = {'Path': Path, 'hashlib': hashlib, 'json': json}
exec(compile(ast.Module(body=[method], type_ignores=[]), str(verifier) + '::<metadata-only-verify>', 'exec'), space)
space['_verify'](binding)
result['selected_face_binding'] = {'path': spec['path'], 'sha256': hashlib.sha256(binding_raw).hexdigest(),
             'configured_sha_matches': hashlib.sha256(binding_raw).hexdigest() == spec['sha256'],
             'source_pin_count': len(binding['source_sha256']), 'source_and_live_owner_verified': True}
if not result['gui_owner']:
    log_path = Path(startup['runtime']) / 'stage.log'
    log = log_path.read_text()
    clock_tree = ast.parse((aura / 'common/board_timeline_clock.py').read_bytes())
    reasons = {n.args[0].value for n in ast.walk(clock_tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'ClockUnavailable' and n.args and isinstance(n.args[0], ast.Constant) and isinstance(n.args[0].value, str)}
    result['gui_api_available'] = False
    result['failure_clock_unavailable'] = 'ClockUnavailable' in log
    result['failure_clock_fixed_reason_codes'] = sorted(r for r in reasons if r in log)
    result['stage_log_sha256'] = digest(log_path)
    result['saved_listening_enabled'] = json.loads(Path('/home/root/.local/share/aura-board-business/listening_preference.json').read_bytes()).get('enabled')
    print(json.dumps(result))
    raise SystemExit(0)
result['samples'] = []
for index in range(3):
    v = get(8783, '/api/state'); camera = get(8790, '/v1/ui/status')
    hands = v.get('handsfree_dialogue') or {}; business = v.get('board_business') or {}; speaker = business.get('speaker') or {}
    face = (business.get('dialogue') or {}).get('voice_enrollment') or {}; identity = (camera.get('modules') or {}).get('identity') or {}; sampling = identity.get('enrollment_sampling') or {}
    result['samples'].append({'sequence': v.get('sequence'), 'main_page': v.get('ui_page') == 'main',
        'pair_ready': (v.get('character_pair') or {}).get('state') == 'READY', 'avatar_visible': (v.get('avatar_display') or {}).get('visible'),
        'handsfree': {'enabled': hands.get('enabled'), 'microphone_open': hands.get('microphone_open'), 'state': known(hands.get('state'), {'PAUSED','CONVERSATION','WAITING_SERVICE','WAITING_SPEECH','WAITING_WAKE','COOLDOWN'})},
        'playing': v.get('playing'), 'pending_job': bool(v.get('pending_job')), 'business_started': business.get('started'),
        'clock_anchored': (business.get('clock') or {}).get('anchored'), 'single_writer_held': (business.get('writer') or {}).get('held'),
        'speaker': {k: speaker.get(k) for k in ('conversation_address','identity_match_threshold','identity_ambiguity_margin','enrollment_consistency','speaker_calibrated','ready','active','queued_or_active','submitted','complete','evidence_errors')},
        'face_enrollment': {'available': face.get('available'), 'active': face.get('active'), 'stage': known(face.get('stage'), {'idle','name','authorize','await_confirmation','confirm','sampling','ready','done'}),
                            'entry_mode': known(face.get('entry_mode'), {'face','voice'}), 'entry_name_pending': face.get('entry_name_pending') if type(face.get('entry_name_pending')) is bool else None},
        'camera_sampling_stage': known(sampling.get('stage'), {'idle','collect','validate','ready','failed','done','cancelled'}),
        'face_people_count': len(identity.get('people') or []), 'face_db_version': identity.get('db_version'),
        'runtime_fault_count': (v.get('runtime_faults') or {}).get('count')})
    if index < 2: time.sleep(.8)
result['startup_unchanged_during_read'] = (ROOT / 'startup/config.json').read_bytes() == raw
result['saved_listening_enabled'] = json.loads(Path('/home/root/.local/share/aura-board-business/listening_preference.json').read_bytes()).get('enabled')
result['gui_owner_stable'] = owner(int(result['gui_unit']['MainPID'])) == result['gui_owner']
result['camera_owner_stable'] = owner(int(result['camera_unit']['MainPID'])) == result['camera_owner']
value = get(8783, '/api/state')
pan = value.get('manual_pan') or {}; rb = pan.get('readback') or {}
result['manual_pan'] = {'state': known(pan.get('state'), {'CONNECTING','FAULT','UNAVAILABLE','READY','MOVING','CLOSED','STOPPED'}), 'automatic_following': pan.get('automatic_following'), 'error_present': bool(pan.get('error')), 'pulse_us': pan.get('pulse_us'), 'target_us': pan.get('target_us'), 'backend_pid': pan.get('backend_pid'), 'readback': {k:rb.get(k) for k in ('flags','lease_left_ms','width_us','target_us','active','armed','referenced','bound')}}
if type(pan.get('backend_pid')) is int and pan.get('backend_pid'): result['manual_backend_owner'] = owner(pan['backend_pid'])
print(json.dumps(result))
