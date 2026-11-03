"""Read wide manifest/driver/source as text; never import or instantiate a driver."""
import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

BOOT = '903cfade-b93c-48fa-804e-379be1967313'
ROOT = Path('/home/root/aura-pan-wide-20261028/release-6a4b645a5bbfd35c')
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == BOOT

def public(path):
    p = Path(path)
    result = {'path': str(p), 'exists': p.exists()}
    if p.is_file() and not p.is_symlink():
        data = p.read_bytes()
        result.update(size=len(data), sha256=hashlib.sha256(data).hexdigest())
        if len(data) <= 500000 and b'\0' not in data[:4096]:
            result['text'] = data.decode('utf-8', 'replace')
    return result

manifest = json.loads((ROOT / 'candidate-manifest.json').read_bytes())
paths = [ROOT / 'candidate-manifest.json', ROOT / 'bench_identity_stop.py']
parent_inventory = [{'path': str(p), 'is_dir': p.is_dir()} for p in sorted(ROOT.parent.iterdir())]
rtl_paths = list(ROOT.parent.rglob('*.sv'))[:30] + list(ROOT.parent.rglob('*.v'))[:30]
paths.extend(rtl_paths)
for name in manifest['payload_files']:
    assert Path(name).name == name
    paths.append(ROOT / 'driver' / name)
inventory = []
for child in sorted(ROOT.rglob('*')):
    if child.is_symlink():
        continue
    if len(inventory) >= 200:
        break
    inventory.append({'path': str(child), 'is_dir': child.is_dir(),
                      'size': child.stat().st_size if child.is_file() else None})
    if child.suffix.lower() in ('.v', '.sv', '.md', '.tcl', '.xdc'):
        paths.append(child)
dtc = shutil.which('dtc')
dtbo_source = None
if dtc:
    decoded = subprocess.run([dtc, '-I', 'dtb', '-O', 'dts', str(Path('/lib/firmware/xilinx') / 'aura-visual-servo-b4096-wide-v1/aura-visual-servo-b4096-wide-v1.dtbo')],
                             capture_output=True, text=True, timeout=10)
    dtbo_source = {'returncode': decoded.returncode, 'stdout': decoded.stdout, 'stderr': decoded.stderr}
print(json.dumps({'schema': 'aura-wide-contract-readonly-1', 'boot_id': BOOT,
                  'board_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  'files': {str(p): public(p) for p in paths}, 'release_inventory': inventory,
                  'platform_parent_inventory': parent_inventory,
                  'dtbo_source': dtbo_source,
                  'board_mutations': False, 'device_opened': False, 'database_opened': False,
                  'project_imported': False, 'motion_requested': False}, sort_keys=True))
