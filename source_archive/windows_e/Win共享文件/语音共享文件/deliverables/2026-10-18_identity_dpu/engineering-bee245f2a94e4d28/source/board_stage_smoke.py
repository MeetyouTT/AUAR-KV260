"""Verify the isolated UART bundle, then execute its bounded smoke test."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import zipfile

assert os.uname().machine == 'aarch64'
assert Path('/sys/block/mmcblk1/device/cid').read_text().strip() == '0353445345333247805558c00401a100'
root = Path('/home/root/aura-adaptation-20261006/identity_dpu_engineering_20261018/bee245f2a94e4d28')
archive = root/'engineering.zip'
assert hashlib.sha256(archive.read_bytes()).hexdigest() == 'ea7b20719e883cafc084fb37d683f2aacdb567d2bcd294f3c7a797a9f09a69db'
with zipfile.ZipFile(archive) as z:
    manifest = json.loads(z.read('manifest.json'))
    assert set(z.namelist()) == {'manifest.json', 'sface_engineering.xmodel', 'hardware-reference.npz', 'board_engineering_smoke.py'}
    for name, meta in manifest['files'].items():
        assert Path(name).name == name
        data = z.read(name)
        assert len(data) == meta['bytes'] and hashlib.sha256(data).hexdigest() == meta['sha256']
        p = root/name
        if p.exists():
            assert not p.is_symlink() and p.read_bytes() == data
        else:
            with p.open('xb') as stream:
                stream.write(data)
    data = json.dumps(manifest, indent=2)+'\n'
    p = root/'manifest.json'
    if p.exists():
        assert not p.is_symlink() and p.read_text() == data
    else:
        with p.open('x') as stream:
            stream.write(data)
try:
    p = subprocess.run(['python3', '-B', str(root/'board_engineering_smoke.py')], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=28)
    if p.returncode:
        print(p.stdout.decode(errors='replace')[-4000:])
        raise SystemExit(p.returncode)
    print(p.stdout.decode(), end='')
except subprocess.TimeoutExpired:
    print(json.dumps({'status': 'SMOKE_SUBPROCESS_TIMEOUT', 'services_changed': False}))
    raise SystemExit(1)
