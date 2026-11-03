"""Read exact public startup/Native sources as data, never import or execute them."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import time

BOOT = '903cfade-b93c-48fa-804e-379be1967313'
BUSINESS = Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
OPS = Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
AURA = Path('/home/root/aura-native-live-20261024/candidates/native-r4-metrics-fix/aura')
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == BOOT

def file(path, cap=350000):
    p = Path(path)
    result = {'path': str(p), 'exists': p.exists()}
    if p.is_file():
        raw = p.read_bytes()
        result.update(size=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        if len(raw) <= cap and b'\0' not in raw[:4096]:
            result['text'] = raw.decode('utf-8', 'replace')
    return result

sources = [Path('/usr/bin/xlnx-firmware-detect'),
           Path('/etc/systemd/system/kv260-repaired-zocl.service'),
           BUSINESS / 'startup/launcher.py', OPS / 'boot_ops.py', OPS / 'native_entry.py',
           OPS / 'native_entry_pan_face_v5.py',
           OPS / 'pan-face-edge-v5/face-source-v17/entry.py',
           OPS / 'pan-face-edge-v5/native-operator-v1/native_entry_operator.py',
           OPS / 'pan-face-edge-v5/native-operator-v1/identity_recovery.py', OPS / 'policy.py',
           AURA / 'board/vision/native_startup.py',
           AURA / 'board/vision/native_protection.py',
           AURA / 'board/vision/native_binding.py',
           AURA / 'board/__init__.py', AURA / 'board/vision/__init__.py',
           AURA / 'board/vision/native_boot.py',
           AURA / 'board/vision/ui_camera_service.py',
           Path('/usr/local/lib/kv260-runtime-repair/load-repaired-zocl.sh'),
           Path('/etc/dfx-mgrd/kv260-benchmark-b4096'),
           Path('/proc/device-tree/fpga-full/firmware-name')]
result = {'schema': 'aura-startup-source-readonly-1', 'boot_id': BOOT,
          'board_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'board_monotonic': time.monotonic(), 'sources': {str(p): file(p) for p in sources},
          'startup_sha256': hashlib.sha256((BUSINESS / 'startup/config.json').read_bytes()).hexdigest(),
          'board_mutations': False, 'project_imported': False, 'device_opened': False,
          'database_opened': False, 'motion_requested': False}
unit = subprocess.run(['systemctl', 'show', 'aura-camera-ui.service',
                       '--property=MainPID,ActiveState,Job'], capture_output=True, text=True, timeout=5)
result['camera_unit'] = {'returncode': unit.returncode, 'stdout': unit.stdout, 'stderr': unit.stderr}
print(json.dumps(result, ensure_ascii=False, sort_keys=True))
