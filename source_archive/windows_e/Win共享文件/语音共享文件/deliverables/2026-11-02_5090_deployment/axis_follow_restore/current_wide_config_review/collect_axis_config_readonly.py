"""Read original control/configuration metadata only; no controller imports or actions."""
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import time

ROOT = Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
CONTROL = Path('/home/root/aura-pan-wide-20261028/control-10282601')
BOOT = '903cfade-b93c-48fa-804e-379be1967313'

def read(path, limit=16000000):
    p = Path(path)
    assert p.is_file() and not p.is_symlink() and p.resolve() == p
    assert p.suffix.lower() not in ('.db', '.sqlite', '.sqlite3')
    assert p.stat().st_size <= limit
    return p.read_bytes()

def digest(path):
    return hashlib.sha256(read(path)).hexdigest()

boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert boot == BOOT
startup_raw = read(ROOT / 'startup/config.json')
startup = json.loads(startup_raw)
aura = Path(startup['runtime']) / 'aura'
pins = startup['component_sha256']
assert len(pins) == 380
names = ('config/pan_manual.local.json', 'config/pan_face.local.json',
         'config/pan_direction.current.json', 'board/motion/manual.py',
         'board/motion/manual_vsrv.py', 'board/motion/manual_process.py',
         'board/motion/manual_live_config.py', 'tools/face_pan_controls.py')
sources = {}
for name in names:
    value = digest(aura / name)
    assert value == pins[name]
    sources[name] = value
manual = json.loads(read(aura / names[0]))
face = json.loads(read(aura / names[1]))
direction = json.loads(read(aura / names[2]))
zone_path = Path(face['arguments']['zone-settings'])
zone = json.loads(read(zone_path))
context_path = Path(face['arguments']['context'])
old_context = json.loads(read(context_path))
release_path = Path(manual['release_manifest'])
release = json.loads(read(release_path))
assert digest(release_path) == manual['release_manifest_sha256']
manifest = json.loads(read(CONTROL / 'deployment-manifest.json'))
assert digest(CONTROL / 'deployment-manifest.json') == '5c8206ee626c91c9f311ee870245813e169ac14e554e2579554c74489066f562'
assert len(manifest['files']) == 25
assert all(digest(row['destination']) == row['sha256'] for row in manifest['files'])
services = {}
for name in ('aura-avatar-ui.service', 'aura-camera-ui.service'):
    p = subprocess.run(['systemctl', 'show', name, '--property=MainPID,ActiveState,SubState,Job'],
                       capture_output=True, text=True, timeout=4)
    assert p.returncode == 0
    services[name] = dict(line.split('=', 1) for line in p.stdout.splitlines() if '=' in line)
firmware = Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode()
platform = {'boot_id': boot, 'fdt_sha256': digest('/sys/firmware/fdt'), 'firmware_name': firmware,
            'fpga_state': Path('/sys/class/fpga_manager/fpga0/state').read_text().strip(),
            'vart': read('/etc/vart.conf').decode()}
assert read(ROOT / 'startup/config.json') == startup_raw
print(json.dumps({'schema': 'aura-current-original-axis-config-readonly-1',
    'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'board_monotonic_ms': int(time.monotonic()*1000),
    'boot_id': boot, 'startup_sha256': hashlib.sha256(startup_raw).hexdigest(),
    'runtime_aura': str(aura), 'services': services, 'source_sha256': sources,
    'manual_config': manual,
    'face_config_summary': {k: face[k] for k in ('arguments', 'duration_s', 'follow_semantics', 'manifest_sha256', 'mode', 'release_root')},
    'direction_summary': {k: direction.get(k) for k in ('boot_id', 'status', 'axis_camera_mirrored_control_polarity', 'camera_moves_with_axis', 'mechanical_zero_calibrated', 'physical_angle_measured', 'command_return_stop_verified', 'trial_sha256')},
    'zone_path': str(zone_path), 'zone_sha256': digest(zone_path), 'zone': zone,
    'previous_context_path': str(context_path), 'previous_context': old_context,
    'release_summary': {k: release.get(k) for k in ('status', 'scope', 'boot_id', 'physical_range_verified', 'mechanical_reference_calibrated')},
    'current_platform': platform, 'original_control_files_verified': 25,
    'current_boot_manual_binding_valid': manual.get('boot_id') == boot,
    'current_boot_direction_evidence': direction.get('boot_id') == boot,
    'current_boot_zone_binding_valid': zone.get('board_boot_id') == boot,
    'board_mutations': False, 'controller_imported': False, 'MMIO_opened': False,
    'device_tested': False, 'database_opened': False}, sort_keys=True))
