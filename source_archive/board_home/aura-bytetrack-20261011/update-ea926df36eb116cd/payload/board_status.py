from pathlib import Path
STAGE=str(Path(__file__).resolve().parent.parent)
"""Verify the new live camera/UI services and exact deployed source hashes."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.request

root = Path('/home/root/aura-avatar-gtk-stage/runtime-1a8677ce-20261009')
stage = Path(STAGE)
manifest = json.loads((stage / 'payload/manifest.json').read_text())
applied = json.loads((stage / 'APPLIED.json').read_text())
before = applied['before']
boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert boot == before['boot_id']

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def get(url):
    with urllib.request.urlopen(url, timeout=4) as response:return json.load(response)
def run(args):
    return subprocess.check_output(args, stderr=subprocess.STDOUT, text=True, timeout=15)

end = time.monotonic() + 90
errors = []
while time.monotonic() < end:
    try:
        health = get('http://127.0.0.1:8790/health')
        ui = get('http://127.0.0.1:8783/api/state')
        assert health['role'] == 'DPU_YOLOX_PERSON_PREVIEW' and health['detected_frames'] >= 5
        assert health['detector']['tracking_backend'] == 'BYTETRACK_PINNED_NUMPY'
        assert health['capture_age_ms'] < 1000 and health['observation_age_ms'] < 750
        assert not health['camera_error'] and not health['detector_error'] and not health['preview_error']
        assert ui['ui_runtime']['link'] == 'READY' and ui['ui_runtime']['frame_visible']
        snapshot = ui['ui_runtime']['snapshot']
        assert snapshot['source_kind'] == 'actual'
        assert snapshot['service_epoch'] == health['service_epoch']
        assert snapshot['modules']['vision']['count_kind'] == 'people'
        assert snapshot['modules']['npu']['state'] == 'READY'
        break
    except Exception as exc:
        errors.append(type(exc).__name__ + ': ' + str(exc))
        time.sleep(.4)
else:
    raise RuntimeError('YOLO/UI startup did not settle: ' + repr(errors[-5:]))

hashes = {name: sha(root / name) for name in manifest['runtime_files']}
assert all(value == manifest['files'][name]['sha256'] for name, value in hashes.items())
assert sha('/etc/systemd/system/aura-avatar-ui.service') == manifest['files']['startup/aura-avatar-ui.service']['sha256']
assert sha('/etc/systemd/system/aura-camera-ui.service') == manifest['files']['aura/scripts/board_camera_ui/aura-camera-ui.service']['sha256']
protected = {name: sha(name) for name in before['protected']}
assert protected == before['protected']
settings = json.loads((root / 'avatar_user_settings.json').read_text())
assert settings == before['saved_preferences']
assert ui['ui_runtime']['connection'] == before['state']['ui_runtime']['connection']
for name in ['Xorg', 'dfx-mgrd', 'realtime_vision.py']:
    for p in before['processes'].get(name, []):
        stat = (Path('/proc') / str(p['pid']) / 'stat').read_text().split(') ')[1].split()
        assert stat[19] == p['start_ticks']

owners = []
for p in Path('/proc').iterdir():
    if not p.name.isdigit():continue
    try:
        if any(os.path.realpath(str(fd)) == '/dev/video0' for fd in (p / 'fd').iterdir()):owners.append(int(p.name))
    except OSError:pass
assert owners == [health['pid']], owners
services = {}
for unit in ['aura-camera-ui.service', 'aura-avatar-ui.service']:
    output = run(['systemctl', 'show', unit, '-p', 'ActiveState', '-p', 'SubState', '-p', 'MainPID', '-p', 'NRestarts', '-p', 'UnitFileState'])
    assert {'ActiveState=active', 'SubState=running', 'UnitFileState=enabled'} <= set(output.splitlines())
    services[unit] = output
print(json.dumps({'status': 'PASS', 'boot_id': boot, 'update_id': applied['update_id'],
    'acceptance_package_id': manifest['update_id'],
    'health': health, 'ui': ui, 'launch': json.loads((root / 'launch.json').read_text()),
    'services': services, 'camera_owners': owners, 'runtime_hashes': hashes, 'protected': protected,
    'saved_settings': settings, 'native_tests': applied['native_test_count'],
    'model_check': json.loads((stage / 'camera-check.json').read_text()),
    'hardware_changed': False, 'motion_command_emitted': False}, ensure_ascii=False))
