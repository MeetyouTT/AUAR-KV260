"""Read-only follow-up of the existing quarantine. No MMIO or control commands."""
import fcntl
import json
import os
import urllib.request
from pathlib import Path

root = Path('/home/root/aura-pan-incident-20261020')
guard = json.loads((root/'lock-status.json').read_text())
boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert guard['boot_id'] == boot
pid = guard['pid']
assert str(root/'lock_guard.py').encode() in Path('/proc/%d/cmdline' % pid).read_bytes()
assert '/dev/mem' not in [os.readlink(str(f)) for f in Path('/proc/%d/fd' % pid).iterdir()]
fd = os.open('/run/aura-vsrv.lock', os.O_RDWR | os.O_NOFOLLOW)
try:
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        blocked = True
    else:
        raise AssertionError('Existing safety mutex is not held')
finally:
    os.close(fd)
value = dict(boot_id=boot, guard=guard, native_mutex_blocks_new_owner=blocked,
             guard_has_no_mmio=True, movement_commands_sent=0, files_modified=0,
             center=json.loads((root/'center_observation.json').read_text()))
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
for port, path in [(8783, '/api/state'), (8790, '/health')]:
    try:
        with opener.open('http://127.0.0.1:%d%s' % (port, path), timeout=1) as response:
            data = json.load(response)
        keys = ['phase', 'sequence', 'error', 'manual_pan'] if port == 8783 else [
            'pid', 'capture_hz', 'detection_hz', 'camera_error', 'detector_error']
        value[str(port)] = {key:data.get(key) for key in keys}
    except Exception as exc:
        value[str(port)] = dict(unavailable=type(exc).__name__)
print(json.dumps(value), flush=True)
