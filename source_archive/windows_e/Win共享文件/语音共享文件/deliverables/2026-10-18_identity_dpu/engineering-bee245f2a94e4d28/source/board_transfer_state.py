import hashlib
import json
import os
from pathlib import Path

assert os.uname().machine == 'aarch64'
assert Path('/sys/block/mmcblk1/device/cid').read_text().strip() == '0353445345333247805558c00401a100'
root = Path('/home/root/aura-adaptation-20261006/identity_dpu_engineering_20261018/bee245f2a94e4d28')
out = {}
for name in ('engineering.zip', 'engineering.zip.partial'):
    path = root/name
    if path.exists():
        out[name] = {'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'symlink': path.is_symlink()}
print(json.dumps(out))
