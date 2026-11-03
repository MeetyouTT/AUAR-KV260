"""Read only current camera ownership, source entry paths and public service configuration."""
import hashlib
import http.client
import json
import os
from pathlib import Path
import subprocess

BOOT = 'bebd3e7d-e984-4517-8cbb-211df7f1c6dc'
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == BOOT
camera = 229296
proc = Path('/proc') / str(camera)
cmd = (proc / 'cmdline').read_bytes()
assert hashlib.sha256(cmd).hexdigest() == 'acf3ee123d7674fdea6e90e79252909ca396249c870269169910879d940c27dd'
argv = cmd.decode().split('\0')
services = {}
for name in ('aura-camera-ui.service', 'aura-business-ui.service', 'aura-native.service'):
    result = subprocess.run(['systemctl', 'show', name, '--no-pager',
        '--property=Id,MainPID,ActiveState,SubState,ExecStart,ExecStop,FragmentPath,DropInPaths,TimeoutStopUSec'],
        capture_output=True, text=True, timeout=5)
    services[name] = result.stdout[:16000]
conn = http.client.HTTPConnection('127.0.0.1', 8790, timeout=2)
try:
    conn.request('GET', '/health'); response = conn.getresponse(); raw = response.read(1048577)
    assert response.status == 200 and len(raw) <= 1048576
    health = json.loads(raw)
finally:
    conn.close()
print(json.dumps(dict(boot=BOOT, camera_pid=camera, argv=argv,
    camera_cwd=os.readlink(str(proc / 'cwd')), service_metadata=services,
    health_top_keys=sorted(health), health_identity_keys=sorted(health.get('identity', {})),
    camera_restarted=False, hardware_opened=False, service_commands='systemctl show only')))
