"""Replace one reviewed GUI-side enrollment source and its current startup pin."""
import base64
import datetime
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import uuid

PAYLOAD = __PAYLOAD__
ROOT = Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
STARTUP = ROOT / 'startup/config.json'
TX = Path('/home/root/aura-5090-recovery-20261102-903cfade/voice-start-sync-v2')
RELATIVE = 'board/identity/voice_enrollment.py'

def digest(data): return hashlib.sha256(data).hexdigest()

def show(name):
    result = subprocess.run(['systemctl', 'show', name, '--property=MainPID,ActiveState,SubState,Job,Result,ExecMainStatus'], capture_output=True, text=True, timeout=5)
    assert result.returncode == 0
    return dict(row.split('=', 1) for row in result.stdout.splitlines() if '=' in row)

def stopped():
    assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == PAYLOAD['boot_id']
    assert show('aura-avatar-ui.service') == {'MainPID': '0', 'ActiveState': 'inactive', 'SubState': 'dead', 'Job': '', 'Result': 'success', 'ExecMainStatus': '0'}
    assert show('aura-camera-ui.service')['MainPID'] == '79866'
    assert Path('/proc/79866/stat').read_text().rsplit(')', 1)[1].split()[19] == '2265436'
    for pid, birth in ((97308, '2694906'), (97312, '2695022')):
        path = Path('/proc') / str(pid)
        if path.exists(): assert (path / 'stat').read_text().rsplit(')', 1)[1].split()[19] != birth

def create(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data); stream.flush(); os.fsync(stream.fileno())

def replace(path, expected, data):
    info = path.lstat()
    assert stat.S_ISREG(info.st_mode) and info.st_uid == 0 and info.st_nlink == 1
    assert path.read_bytes() == expected
    temporary = path.with_name('.' + path.name + '.start-sync-' + uuid.uuid4().hex)
    try:
        fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, stat.S_IMODE(info.st_mode))
        with os.fdopen(fd, 'wb') as stream:
            os.fchmod(stream.fileno(), stat.S_IMODE(info.st_mode)); stream.write(data); stream.flush(); os.fsync(stream.fileno())
        assert path.read_bytes() == expected
        os.replace(temporary, path)
        fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(fd)
        finally: os.close(fd)
        assert path.read_bytes() == data
    finally:
        if temporary.exists(): temporary.unlink()

stopped()
assert TX.resolve() == TX and not (TX / 'apply-intent.json').exists()
assert json.loads((TX / 'stop-result.json').read_bytes())['status'] == 'GUI_NORMAL_STOPPED'
before_startup = STARTUP.read_bytes()
assert digest(before_startup) == PAYLOAD['startup_before_sha256']
startup = json.loads(before_startup); aura = Path(startup['runtime']) / 'aura'
target = aura / RELATIVE
assert target.is_file() and not target.is_symlink()
before_source = target.read_bytes()
assert digest(before_source) == startup['component_sha256'][RELATIVE] == PAYLOAD['source_before_sha256']
assert all(digest((aura / key).read_bytes()) == value for key, value in startup['component_sha256'].items())
ui = json.loads((aura / 'config/board_avatar_gtk.json').read_bytes())
spec = ui['board_business']['face_readback']; binding_raw = Path(spec['path']).read_bytes()
assert digest(binding_raw) == spec['sha256'] == PAYLOAD['selected_binding_sha256']
binding = json.loads(binding_raw)
assert str(target) not in binding['source_sha256']
assert all(digest(Path(key).read_bytes()) == value for key, value in binding['source_sha256'].items())
after_source = base64.b64decode(PAYLOAD['source_after_base64'], validate=True)
assert digest(after_source) == PAYLOAD['source_after_sha256']
compile(after_source, str(target), 'exec')  # Syntax validation only; no project import.
updated = json.loads(before_startup)
updated['component_sha256'][RELATIVE] = PAYLOAD['source_after_sha256']
after_startup = (json.dumps(updated, sort_keys=True, indent=2) + '\n').encode()
assert [key for key in startup['component_sha256'] if startup['component_sha256'][key] != updated['component_sha256'][key]] == [RELATIVE]
create(TX / 'startup.before.json', before_startup)
create(TX / 'voice_enrollment.before.py', before_source)
create(TX / 'apply-intent.json', (json.dumps({key: value for key, value in PAYLOAD.items() if key != 'source_after_base64'}, sort_keys=True, indent=2) + '\n').encode())
try:
    stopped(); replace(target, before_source, after_source)
    stopped(); replace(STARTUP, before_startup, after_startup)
    assert all(digest((aura / key).read_bytes()) == value for key, value in updated['component_sha256'].items())
    assert Path(spec['path']).read_bytes() == binding_raw
    assert all(digest(Path(key).read_bytes()) == value for key, value in binding['source_sha256'].items())
    stopped()
except BaseException:
    current_startup = STARTUP.read_bytes()
    if current_startup == after_startup: replace(STARTUP, after_startup, before_startup)
    elif current_startup != before_startup:
        assert json.loads(current_startup)['component_sha256'][RELATIVE] == PAYLOAD['source_before_sha256'], 'Concurrent startup change requires reconciliation'
    if target.read_bytes() == after_source: replace(target, after_source, before_source)
    raise
receipt = {'schema': 'aura-voice-start-sync-single-component-apply-1', 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'status': 'SYNC_FIX_V2_APPLIED_GUI_STOPPED', 'boot_id': PAYLOAD['boot_id'],
           'startup_before_sha256': digest(before_startup), 'startup_after_sha256': digest(after_startup),
           'source_before_sha256': digest(before_source), 'source_after_sha256': digest(after_source),
           'changed_component': RELATIVE, 'components_verified': len(updated['component_sha256']),
           'gui_configuration_unchanged': True, 'selected_camera_sources_unchanged': True,
           'source_target_separate_from_native_camera': True, 'camera_pid': 79866,
           'identity_store_or_model_or_threshold_modified': False, 'service_start_requested': False}
create(TX / 'applied.json', (json.dumps(receipt, sort_keys=True, indent=2) + '\n').encode())
print(json.dumps(receipt))
