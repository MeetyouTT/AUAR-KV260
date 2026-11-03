"""PAYLOAD is supplied from the frozen, tested two-file candidate by the host."""
import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import time
import uuid

ROOT = Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
STARTUP = ROOT / 'startup/config.json'
TX = Path('/home/root/aura-5090-recovery-20261102-a6d4a069/no-speech-enrollment-v1')
KEYS = {'board/runtime/audio/board_asr.py', 'board/runtime/audio/board_dialogue_jobs.py'}
assert set(PAYLOAD['files']) == KEYS

def raw(p):
    p = Path(p); s = p.lstat()
    assert stat.S_ISREG(s.st_mode) and s.st_uid == 0 and not p.is_symlink()
    return p.read_bytes()

def sha(p): return hashlib.sha256(raw(p)).hexdigest()

def unit(name):
    r = subprocess.run(['systemctl', 'show', name, '--property=MainPID,ActiveState,SubState,Job'], capture_output=True, text=True, timeout=4)
    assert r.returncode == 0
    return dict(line.split('=', 1) for line in r.stdout.splitlines() if '=' in line)

def owners():
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == 'a6d4a069-e9b0-4065-8df7-dc23556b168e'
    assert unit('aura-avatar-ui.service') == {'MainPID': '0', 'ActiveState': 'inactive', 'SubState': 'dead', 'Job': ''}
    assert not Path('/proc/2142').exists() and not Path('/proc/2151').exists()
    assert unit('aura-camera-ui.service') == {'MainPID': '1332', 'ActiveState': 'active', 'SubState': 'running', 'Job': ''}
    assert Path('/proc/1332/stat').read_text().rsplit(')', 1)[1].split()[19] == '2236'
    assert sha('/proc/1332/cmdline') == 'acf3ee123d7674fdea6e90e79252909ca396249c870269169910879d940c27dd'

def sync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(fd)
    finally: os.close(fd)

def create(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data); stream.flush(); os.fsync(stream.fileno())
    sync_dir(path.parent)

def replace(path, expected, data):
    info = path.lstat()
    assert stat.S_ISREG(info.st_mode) and info.st_uid == 0 and info.st_nlink == 1
    assert raw(path) == expected, 'Concurrent source change'
    temp = path.with_name('.' + path.name + '.no-speech-' + uuid.uuid4().hex + '.tmp')
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, stat.S_IMODE(info.st_mode))
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        assert raw(path) == expected, 'Concurrent source change'
        os.replace(temp, path); sync_dir(path.parent)
        assert raw(path) == data
    finally:
        if temp.exists(): temp.unlink()

owners()
assert json.loads(raw(TX / 'stop-result.json'))['status'] == 'GUI_NORMAL_STOPPED'
assert TX.resolve(strict=True) == TX and TX.stat().st_uid == 0
assert not (TX / 'apply-intent.json').exists() and not (TX / 'applied.json').exists()
startup_before = raw(STARTUP)
assert hashlib.sha256(startup_before).hexdigest() == PAYLOAD['base_startup_sha256'] == '9a9a709a7b2e898879bac595758f9b7ece6f2ff2e75a4c9f42ed9c38e043072a'
startup = json.loads(startup_before); aura = Path(startup['runtime']) / 'aura'
assert len(startup['component_sha256']) == 380
assert all(sha(aura / k) == v for k, v in startup['component_sha256'].items())
assert startup['component_sha256']['board/identity/voice_enrollment.py'] == 'a9113ba40efc49828ee158554b2dae70485858396680918458f6f96bba16bacb'
assert startup['component_sha256']['tools/unified_identity_binding.py'] == '85e415d00daa770d4d94ae58006a23ed9700067651a0448de80c99eb33ed1809'
assert startup['component_sha256']['config/board_avatar_gtk.json'] == '8b9556b8c7a12cda0d90de2076a144bef4a106316bc74a4e5639ffa5106f1fb5'
ui = json.loads(raw(aura / 'config/board_avatar_gtk.json')); selected = ui['board_business']['face_readback']
assert selected['sha256'] == sha(selected['path']) == '99c53c5992355a2a4dfdedceb3cc90d813981328456b987e503459fe6d0691b5'
binding = json.loads(raw(selected['path'])); assert len(binding['source_sha256']) == 26
assert all(sha(p) == v for p, v in binding['source_sha256'].items())
assert json.loads(raw('/home/root/.local/share/aura-board-business/listening_preference.json')) == {'version': 1, 'enabled': False}
before = {}; after = {}; new_startup = copy.deepcopy(startup)
for key in sorted(KEYS):
    spec = PAYLOAD['files'][key]; path = aura / key
    before[path] = raw(path)
    assert hashlib.sha256(before[path]).hexdigest() == spec['before_sha256'] == startup['component_sha256'][key]
    data = base64.b64decode(spec['payload_base64'], validate=True)
    assert hashlib.sha256(data).hexdigest() == spec['candidate_sha256']
    compile(data, str(path), 'exec')
    after[path] = data; new_startup['component_sha256'][key] = spec['candidate_sha256']
before[STARTUP] = raw(STARTUP)
assert before[STARTUP] == startup_before and hashlib.sha256(before[STARTUP]).hexdigest() == PAYLOAD['base_startup_sha256']
after[STARTUP] = (json.dumps(new_startup, sort_keys=True, indent=2) + '\n').encode()
assert {k: v for k, v in new_startup.items() if k != 'component_sha256'} == {k: v for k, v in startup.items() if k != 'component_sha256'}
assert {k for k in startup['component_sha256'] if startup['component_sha256'][k] != new_startup['component_sha256'][k]} == KEYS
owners(); assert all(raw(p) == b for p, b in before.items())
create(TX / 'apply-intent.json', (json.dumps({'board_monotonic': time.monotonic(), 'base_startup_sha256': PAYLOAD['base_startup_sha256'],
       'startup_after_sha256': hashlib.sha256(after[STARTUP]).hexdigest(), 'changed_files': sorted(KEYS)}) + '\n').encode())
create(TX / 'startup.before.json', before[STARTUP])
for key in sorted(KEYS): create(TX / (Path(key).stem + '.before.py'), before[aura / key])
changed = []
try:
    for path in [aura / key for key in sorted(KEYS)] + [STARTUP]:
        owners(); assert raw(path) == before[path]
        changed.append(path); replace(path, before[path], after[path])
    assert all(sha(aura / k) == v for k, v in new_startup['component_sha256'].items())
    assert raw(STARTUP) == after[STARTUP] and sha(selected['path']) == selected['sha256']
    owners()
except Exception:
    for path in reversed(changed):
        owners()
        if raw(path) == after[path]: replace(path, after[path], before[path])
    raise
receipt = {'schema': 'aura-no-speech-enrollment-fix-applied-1', 'status': 'NO_SPEECH_FIX_APPLIED_GUI_STOPPED',
           'board_boot_id': 'a6d4a069-e9b0-4065-8df7-dc23556b168e', 'board_monotonic': time.monotonic(),
           'startup_before_sha256': PAYLOAD['base_startup_sha256'], 'startup_after_sha256': hashlib.sha256(after[STARTUP]).hexdigest(),
           'source_pins_after': {k: PAYLOAD['files'][k]['candidate_sha256'] for k in sorted(KEYS)},
           'components_verified': 380, 'other_component_pins_preserved': 378,
           'selected_binding_sha256': selected['sha256'], 'selected_binding_source_count': 26,
           'camera_pid': 1332, 'camera_birth_ticks': '2236', 'voice_a911_and_router85_preserved': True,
           'identity_thresholds_or_time_policy_or_private_store_changed': False,
           'services_controlled_or_axis_operations': False, 'diagnostic_four_file_candidate_deployed': False}
create(TX / 'applied.json', (json.dumps(receipt, sort_keys=True, indent=2) + '\n').encode())
print(json.dumps(receipt))
