"""Read a bounded explicit list of current camera wrapper and public service sources."""
import hashlib
import json
import os
from pathlib import Path
import stat

assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == 'bebd3e7d-e984-4517-8cbb-211df7f1c6dc'
base = Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
paths = [base/'pan-face-edge-v5/face-source-v17/entry.py',
    Path('/etc/systemd/system/aura-camera-ui.service'),
    Path('/etc/systemd/system/aura-camera-ui.service.d/zzzzzzzzzzzzzzzzzzzzzzzzzzzzzz-aura-face-measure-v17.conf'),
    base/'native_entry.py', base/'native_startup.py']
files = []
for path in paths:
    try:
        info = path.lstat()
        assert stat.S_ISREG(info.st_mode) and info.st_size <= 80000
        with path.open('rb') as handle: raw = handle.read(80001)
        assert len(raw) <= 80000
        files.append(dict(path=str(path),sha256=hashlib.sha256(raw).hexdigest(),content=raw.decode('utf-8')))
    except FileNotFoundError:
        files.append(dict(path=str(path),unavailable=True))
print(json.dumps(dict(files=files,services_changed=False)))
