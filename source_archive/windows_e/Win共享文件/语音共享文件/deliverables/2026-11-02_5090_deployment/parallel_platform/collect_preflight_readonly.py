"""Current-boot, metadata-only prerequisite check for a FUTURE normal camera stop.

No project imports, writes, locks, inference, FPGA changes, /dev opens, audio, database
opens or register access. Passing this script NEVER authorizes a platform switch:
the sole live camera still has to stop normally and seal a new final checkpoint.
"""
import datetime
import hashlib
import http.client
import json
import os
from pathlib import Path
import stat
import subprocess
import time

BOOT = '903cfade-b93c-48fa-804e-379be1967313'
STARTUP_SHA = '07c5aa3b1c8da060e5a7d8520021bce7f167a8cf303b48a0a24f8e2a8b63035d'
CAMERA_PID = 1333
CAMERA_BIRTH = 2359
CAMERA_CMD = 'acf3ee123d7674fdea6e90e79252909ca396249c870269169910879d940c27dd'
LAUNCHER_SHA = '5b15a8cf1813935679e5f4d30eb788e9c8d6ae18826669009d06c92cba152e03'
BUSINESS = Path('/home/root/aura-board-business-20261030/production-5259eab11e42af13')
RELEASE = Path('/home/root/aura-pan-wide-20261028/release-6a4b645a5bbfd35c')
MANIFEST_SHA = '6a4b645a5bbfd35c9107976edf27886cf8e0c91e40f48be6f052a95e1172c1cf'
APP = 'aura-visual-servo-b4096-wide-v1'
FW = Path('/lib/firmware/xilinx') / APP
OPS = Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
CAMERA_AURA = Path('/home/root/aura-native-live-20261024/candidates/native-r4-metrics-fix/aura')
NATIVE_MANIFEST_SHA = '5e08f7cf587d74334ef24104ea01f79701629b48f2004fb772ce3f8ea82afd0d'
OPERATOR_MANIFEST_SHA = '74e011db30a9d943a9512f7648190ac0c01060af06df1280d1e8ea006dc882ad'
BENCHMARK_VART = 'firmware: /lib/firmware/xilinx/kv260-benchmark-b4096/kv260-benchmark-b4096.xclbin\n'

def regular(path, limit=2000000):
    path = Path(path)
    if path.is_symlink():
        raise ValueError('Read target is a symlink: ' + str(path))
    if path.suffix.lower() in ('.db', '.sqlite', '.sqlite3'):
        raise ValueError('Database read forbidden')
    fd = os.open(str(path), os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        meta = os.fstat(fd)
        if not stat.S_ISREG(meta.st_mode) or meta.st_size > limit:
            raise ValueError('Not a bounded public regular file: ' + str(path))
        with os.fdopen(fd, 'rb', closefd=False) as handle:
            raw = handle.read(limit + 1)
        if len(raw) > limit:
            raise ValueError('Public file exceeds read limit')
        return raw
    finally:
        os.close(fd)

def digest(path, limit=64000000):
    return hashlib.sha256(regular(path, limit)).hexdigest()

def document(path):
    return json.loads(regular(path))

def unit(name):
    properties = 'MainPID,ActiveState,SubState,Restart,SendSIGKILL,TimeoutStopUSec,KillMode,Job,Result,ExecMainStatus'
    p = subprocess.run(['systemctl', 'show', name, '--property=' + properties],
                       capture_output=True, text=True, timeout=5)
    if p.returncode:
        raise RuntimeError('systemctl inspection failed: ' + name)
    return dict(row.split('=', 1) for row in p.stdout.splitlines() if '=' in row)

def owner(pid):
    p = Path('/proc') / str(pid)
    raw = regular(p / 'cmdline', 100000)
    tail = regular(p / 'stat', 100000).decode().rsplit(')', 1)[1].split()
    return {'pid': pid, 'birth_ticks': int(tail[19]), 'command_sha256': hashlib.sha256(raw).hexdigest()}

def dpu_users():
    values = []
    motion = []
    incomplete = []
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        try:
            mapped = (proc / 'maps').read_text()
        except OSError:
            if proc.exists():
                incomplete.append(int(proc.name))
            continue
        handles = []
        motion_handles = []
        try:
            for fd in (proc / 'fd').iterdir():
                try:
                    target = os.readlink(fd)
                except OSError:
                    continue
                if target.startswith(('/dev/dri/renderD', '/dev/dpu')):
                    handles.append(target)
                if target == '/dev/mem':
                    motion_handles.append(target)
        except OSError:
            if proc.exists():
                incomplete.append(int(proc.name))
        library = 'libvart' in mapped or 'libaura_native_operator' in mapped
        if library or handles:
            row = owner(int(proc.name))
            row.update(mapped_dpu_library=library, device_handles=sorted(set(handles)))
            values.append(row)
        if 'libvsrv.so' in mapped or motion_handles:
            row = owner(int(proc.name))
            row.update(mapped_motion_library='libvsrv.so' in mapped,
                       device_handles=sorted(set(motion_handles)))
            motion.append(row)
    return {'owners': sorted(values, key=lambda row: row['pid']),
            'motion_or_raw_mem_owners': sorted(motion, key=lambda row: row['pid']),
            'unreadable_live_processes': sorted(set(incomplete))}

def sample():
    connection = http.client.HTTPConnection('127.0.0.1', 8790, timeout=2)
    try:
        connection.request('GET', '/health')
        response = connection.getresponse()
        raw = response.read(1048577)
        if response.status != 200 or len(raw) > 1048576:
            raise RuntimeError('Camera metadata response unavailable')
        h = json.loads(raw)
    finally:
        connection.close()
    s = h.get('dpu_schedule', {})
    identity = h.get('identity', {})
    face = identity.get('face_targets', {})
    feature = identity.get('feature_inference', {})
    result = {key: h.get(key) for key in ('pid', 'board_boot_id', 'service_epoch', 'camera_epoch',
              'capture_frames', 'detected_frames', 'capture_age_ms', 'observation_age_ms',
              'camera_error', 'detector_error', 'motion_command_emitted')}
    result.update(monotonic=time.monotonic(), identity_ready=identity.get('ready'),
                  identity_error=bool(identity.get('error')),
                  identity_shutdown_incomplete=identity.get('shutdown_incomplete', False),
                  face_processed=face.get('processed'), sface_completed=feature.get('completed'),
                  native_critical=s.get('native_critical'), native_abi=s.get('native_abi'),
                  owner_fenced=s.get('owner_fenced'), quiesced=s.get('quiesced'),
                  primary_calls=s.get('primary_calls'),
                  primary_period_overruns=s.get('primary_period_overruns'))
    result['optional'] = {task: {key: s.get('optional', {}).get(task, {}).get(key) for key in
                          ('disabled', 'overruns', 'completed', 'native_failures')}
                          for task in ('yunet', 'sface')}
    return result

boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert boot == BOOT, 'New boot requires a new reviewed context'
startup = document(BUSINESS / 'startup/config.json')
runtime = Path(startup['runtime']).resolve()
assert digest(BUSINESS / 'startup/config.json') == STARTUP_SHA, 'Startup context changed'
assert digest(BUSINESS / 'startup/launcher.py') == LAUNCHER_SHA, 'Installed launcher changed'
components = startup.get('component_sha256', {})
assert len(components) == 380
for relative, expected in components.items():
    path = (runtime / 'aura' / relative).resolve()
    assert path.is_relative_to((runtime / 'aura').resolve()), 'Component path escapes runtime'
    assert digest(path) == expected, 'Source component differs: ' + relative

readback = document(runtime / 'aura/config/face_gallery_readback.local.json')
assert len(readback['source_sha256']) == 14
for path, expected in readback['source_sha256'].items():
    assert digest(path) == expected, 'Camera source differs'
assert readback['board_boot_id'] == BOOT and readback['camera_pid'] == CAMERA_PID
assert int(readback['camera_start_ticks']) == CAMERA_BIRTH
assert readback['camera_cmdline_sha256'] == CAMERA_CMD
native_manifest = CAMERA_AURA.parent / 'camera-python-manifest.json'
assert digest(native_manifest) == NATIVE_MANIFEST_SHA
native_files = document(native_manifest)
assert native_files.get('schema') == 'aura-native-python-source-2'
native_actual = {str(p.relative_to(CAMERA_AURA)): digest(p) for p in CAMERA_AURA.rglob('*.py') if not p.is_symlink()}
assert native_actual == native_files['files'], 'Full original Native Python closure differs'
operator_manifest = OPS / 'pan-face-edge-v5/native-operator-v1/runtime-manifest.json'
assert digest(operator_manifest) == OPERATOR_MANIFEST_SHA
operator_files = document(operator_manifest)['files']
for path, expected in operator_files.items():
    assert digest(path) == expected, 'Native operator closure differs'

camera = unit('aura-camera-ui.service')
gui = unit('aura-avatar-ui.service')
assert camera['MainPID'] == str(CAMERA_PID) and camera['ActiveState'] == 'active'
assert not camera.get('Job') and camera['Restart'] == 'no'
assert camera['SendSIGKILL'] == 'no' and camera['TimeoutStopUSec'] == 'infinity'
assert camera['KillMode'] == 'process'
assert gui['MainPID'] == '0' and not gui.get('Job'), 'GUI owner appeared'
assert document('/home/root/.local/share/aura-board-business/listening_preference.json') == {'version': 1, 'enabled': False}
current_owner = owner(CAMERA_PID)
assert current_owner['birth_ticks'] == CAMERA_BIRTH and current_owner['command_sha256'] == CAMERA_CMD
users = dpu_users()
assert [row['pid'] for row in users['owners']] == [CAMERA_PID], 'Unexpected DPU owner'
assert not users['unreadable_live_processes'], 'Cannot prove full DPU owner inventory'
assert not users['motion_or_raw_mem_owners'], 'Existing motion or raw-memory owner'
assert Path('/proc/device-tree/fpga-full/firmware-name').read_bytes().rstrip(b'\0').decode() == 'kv260-benchmark-b4096.bit.bin'
assert Path('/sys/class/fpga_manager/fpga0/state').read_text().strip() == 'operating'
assert regular('/etc/vart.conf').decode() == BENCHMARK_VART

assert digest(RELEASE / 'candidate-manifest.json') == MANIFEST_SHA
manifest = document(RELEASE / 'candidate-manifest.json')
assert manifest['app'] == APP and manifest['build_id'] == 0x10282601
for path, expected in manifest['runtime_files'].items():
    target = Path(path)
    assert target.parent == FW, 'Unexpected wide runtime target'
    assert digest(target, 16000000) == expected, 'Wide runtime file differs'
for name, expected in manifest['payload_files'].items():
    assert Path(name).name == name, 'Unexpected driver filename'
    assert digest(RELEASE / 'driver' / name) == expected, 'Wide driver differs'

samples = [sample()]
time.sleep(1.05)
samples.append(sample())
for h in samples:
    assert h['pid'] == CAMERA_PID and h['board_boot_id'] == BOOT
    assert h['camera_error'] == '' and h['detector_error'] == ''
    assert h['identity_ready'] is True and not h['identity_error'] and not h['identity_shutdown_incomplete']
    assert h['native_critical'] is True and h['native_abi'] == 2
    assert h['owner_fenced'] is False and h['quiesced'] is False
    assert h['motion_command_emitted'] is False
assert samples[-1]['capture_frames'] > samples[0]['capture_frames']
assert samples[-1]['detected_frames'] > samples[0]['detected_frames']
assert samples[-1]['service_epoch'] == samples[0]['service_epoch']
assert samples[-1]['camera_epoch'] == samples[0]['camera_epoch']
assert owner(CAMERA_PID) == current_owner
assert unit('aura-avatar-ui.service')['MainPID'] == '0'
assert digest(BUSINESS / 'startup/config.json') == STARTUP_SHA
print(json.dumps({'schema': 'aura-platform-normal-stop-prerequisites-1',
    'phase': 'READONLY_PREFLIGHT_OK_NORMAL_CAMERA_STOP_STILL_REQUIRED', 'boot_id': boot,
    'board_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'startup_sha256': STARTUP_SHA, 'components_verified': len(components),
    'camera_source_files_verified': len(readback['source_sha256']), 'camera_owner': current_owner,
    'native_python_files_verified': len(native_actual),
    'native_operator_files_verified': len(operator_files),
    'camera_unit': camera, 'gui_unit': gui, 'dpu_users': users, 'camera_samples': samples,
    'wide_runtime_files_verified': len(manifest['runtime_files']),
    'wide_driver_files_verified': len(manifest['payload_files']),
    'wide_manifest_sha256': MANIFEST_SHA, 'fdt_sha256': digest('/sys/firmware/fdt'),
    'platform_switch_permitted': False, 'final_checkpoint_created_or_fabricated': False,
    'board_mutations': False, 'device_opened': False, 'database_opened': False,
    'project_imported': False, 'motion_requested': False}, sort_keys=True))
