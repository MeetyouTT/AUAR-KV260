"""Append to the exact reviewed precheck; change selected binding/config pin only."""
import os
import stat
import uuid

TX = DEST.parent
PARENT = TX.parent
STARTUP = BUSINESS / 'startup/config.json'
UI = AURA / 'config/board_avatar_gtk.json'
EXPECTED_BINDING = '99c53c5992355a2a4dfdedceb3cc90d813981328456b987e503459fe6d0691b5'
EXPECTED_UI = '8b9556b8c7a12cda0d90de2076a144bef4a106316bc74a4e5639ffa5106f1fb5'
EXPECTED_STARTUP = '9a9a709a7b2e898879bac595758f9b7ece6f2ff2e75a4c9f42ed9c38e043072a'
assert hashlib.sha256(raw_candidate).hexdigest() == EXPECTED_BINDING
assert hashlib.sha256(ui_after).hexdigest() == EXPECTED_UI
assert hashlib.sha256(startup_after).hexdigest() == EXPECTED_STARTUP
assert startup['component_sha256']['board/identity/voice_enrollment.py'] == 'a9113ba40efc49828ee158554b2dae70485858396680918458f6f96bba16bacb'
before = {STARTUP: raw(STARTUP), UI: raw(UI)}
assert hashlib.sha256(before[STARTUP]).hexdigest() == STARTUP_SHA
assert hashlib.sha256(before[UI]).hexdigest() == UI_SHA
after = {UI: ui_after, STARTUP: startup_after}
assert not TX.exists() and not TX.is_symlink()
assert os.geteuid() == 0

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
    assert raw(path) == expected, 'Concurrent configuration change'
    temp = path.with_name('.' + path.name + '.binding26-' + uuid.uuid4().hex + '.tmp')
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, stat.S_IMODE(info.st_mode))
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        assert raw(path) == expected, 'Concurrent configuration change'
        os.replace(temp, path); sync_dir(path.parent)
        assert raw(path) == data
    finally:
        if temp.exists(): temp.unlink()

units(); owner()
assert all(raw(p) == b for p, b in before.items())
if not PARENT.exists():
    assert PARENT.parent == Path('/home/root') and PARENT.parent.resolve() == PARENT.parent
    PARENT.mkdir(mode=0o700); sync_dir(PARENT.parent)
assert not PARENT.is_symlink() and PARENT.resolve(strict=True) == PARENT and PARENT.stat().st_uid == 0
TX.mkdir(mode=0o700); sync_dir(PARENT)
create(TX / 'apply-intent.json', (json.dumps({'boot_id': BOOT, 'board_monotonic': time.monotonic(),
       'startup_before_sha256': STARTUP_SHA, 'startup_after_sha256': EXPECTED_STARTUP,
       'changed_component_keys': ['config/board_avatar_gtk.json'], 'services_to_be_started': False}) + '\n').encode())
create(TX / 'startup.before.json', before[STARTUP])
create(TX / 'board_avatar_gtk.before.json', before[UI])
create(TX / 'selected_binding.before.json', raw(spec['path']))
create(DEST, raw_candidate)
space['_verify'](json.loads(raw(DEST)))
changed = []
try:
    for p in (UI, STARTUP):
        units(); owner()
        assert raw(p) == before[p]
        changed.append(p)
        replace(p, before[p], after[p])
    assert digest(STARTUP) == EXPECTED_STARTUP and digest(UI) == EXPECTED_UI
    assert all(digest(AURA / k) == v for k, v in new_startup['component_sha256'].items())
    space['_verify'](json.loads(raw(DEST)))
    units(); owner()
except Exception:
    for p in reversed(changed):
        units(); owner()
        if raw(p) == after[p]: replace(p, after[p], before[p])
    raise
receipt = {'schema': 'aura-current-boot-binding26-applied-1', 'status': 'BINDING26_APPLIED_GUI_STOPPED',
      'boot_id': BOOT, 'board_monotonic': time.monotonic(), 'startup_before_sha256': STARTUP_SHA,
      'startup_after_sha256': EXPECTED_STARTUP, 'ui_after_sha256': EXPECTED_UI,
      'selected_binding_path': str(DEST), 'selected_binding_sha256': EXPECTED_BINDING,
      'old_source_pins_preserved': 25, 'selected_source_pins_verified': 26, 'components_verified': 380,
      'native_python_files_verified': 222, 'operator_files_verified': 7,
      'voice_fix_preserved': True, 'camera_pid': 1332, 'camera_birth_ticks': '2236',
      'services_started_or_stopped': False, 'identity_or_memory_store_opened_or_modified': False,
      'axis_or_mmio_operations': False, 'old_boot_seed_or_checkpoint_replayed': False,
      'changed_component_keys': ['config/board_avatar_gtk.json']}
create(TX / 'applied.json', (json.dumps(receipt, sort_keys=True, indent=2) + '\n').encode())
print(json.dumps(receipt))
