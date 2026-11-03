"""Post-stop-only checkpoint precheck, for main operator review. NOT executed during preparation.

Reads the real installed final file and OS metadata. It never creates, repairs,
consumes or changes a checkpoint. The main operator still runs the hash-verified
original load_business_checkpoint validation and seals exact original bytes.
"""
import base64
import datetime
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import time

BOOT = '903cfade-b93c-48fa-804e-379be1967313'
SOURCE_PID = 1333
SOURCE_BIRTH = 2359
SOURCE_UNIT = '7cf7eaeecd70e62301d3e12e95d5df6a23bd3e5847ed854200c712598b703c32'
SOURCE_MANIFEST = '5e08f7cf587d74334ef24104ea01f79701629b48f2004fb772ce3f8ea82afd0d'
OLD_CHECKPOINT_SHA = '5b26714b0be9d52bf99fe14c07a0f810105379171712328b63454beb314bc6bb'
CHECKPOINT = Path('/home/root/aura-native-live-20261024/candidates/native-r4-metrics-fix/state/native-protection-checkpoint.json')
ARCHIVE = Path('/home/root/aura-native-critical-20261024/candidates/native-v2-d7256b06808509c9/state/kernel-history/archive') / (BOOT + '-' + OLD_CHECKPOINT_SHA + '.json')
MIN_PRIMARY_CALLS = 78923
MIN_PRIMARY_OVERRUNS = 1
MIN_SFACE_COMPLETED = 427
PREFLIGHT_OBSERVED_NS = 7955181645887

def read(path, limit=262144):
    path = Path(path)
    assert path.is_absolute() and not path.is_symlink() and path.resolve() == path
    assert path.suffix not in ('.sqlite', '.sqlite3', '.db')
    fd = os.open(str(path), os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        st = os.fstat(fd)
        assert stat.S_ISREG(st.st_mode) and st.st_size <= limit
        with os.fdopen(fd, 'rb', closefd=False) as handle:
            raw = handle.read(limit + 1)
        assert len(raw) <= limit
        return raw
    finally:
        os.close(fd)

def unit(name):
    p = subprocess.run(['systemctl', 'show', name,
        '--property=MainPID,ActiveState,SubState,Job,Result,ExecMainStatus,Restart,SendSIGKILL,TimeoutStopUSec,KillMode'],
        capture_output=True, text=True, timeout=5)
    assert p.returncode == 0
    return dict(row.split('=', 1) for row in p.stdout.splitlines() if '=' in row)

def integer(value, maximum=2**64-1):
    assert type(value) is int and 0 <= value <= maximum
    return value

assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == BOOT
camera = unit('aura-camera-ui.service')
assert camera['MainPID'] == '0' and not camera['Job']
assert camera['ActiveState'] == 'inactive' and camera['Result'] == 'success' and camera['ExecMainStatus'] == '0'
assert camera['Restart'] == 'no' and camera['SendSIGKILL'] == 'no'
assert camera['TimeoutStopUSec'] == 'infinity' and camera['KillMode'] == 'process'
gui = unit('aura-avatar-ui.service')
assert gui['MainPID'] == '0' and not gui['Job']
source = Path('/proc') / str(SOURCE_PID)
if source.exists():
    birth = int((source / 'stat').read_text().rsplit(')', 1)[1].split()[19])
    assert birth != SOURCE_BIRTH, 'Original camera still alive; no handoff'
users = []
for proc in Path('/proc').iterdir():
    if not proc.name.isdigit():
        continue
    try:
        mapped = (proc / 'maps').read_text()
        handles = []
        for fd in (proc / 'fd').iterdir():
            try:
                target = os.readlink(fd)
            except OSError:
                continue
            if target.startswith(('/dev/dri/renderD', '/dev/dpu')) or target == '/dev/mem':
                handles.append(target)
        if any(library in mapped for library in ('libvart', 'libaura_native_operator', 'libvsrv.so')) or handles:
            users.append(int(proc.name))
    except OSError:
        assert not proc.exists(), 'Cannot inspect a live process; no owner proof'
assert not users, 'DPU or raw-memory owner remains'

raw = read(CHECKPOINT)
sha = hashlib.sha256(raw).hexdigest()
assert sha != OLD_CHECKPOINT_SHA, 'Still the historical predecessor file'
j = json.loads(raw)
assert j['schema'] == 'aura-native-protection-checkpoint-2'
assert j['scope'] == 'final_quiescent_before_native_owner_close'
assert j['source_unit_sha256'] == SOURCE_UNIT
s, a = j['seed'], j['auxiliary']
assert s['abi_version'] == 2 and s['checkpoint_kind'] == 1
assert s['purpose'] == 'final_quiescent_business_checkpoint'
assert s['boot_id'] == BOOT and s['source_pid'] == SOURCE_PID and s['source_birth_ticks'] == SOURCE_BIRTH
assert s['source_manifest_sha256'] == SOURCE_MANIFEST
assert s['fenced'] == 0
assert PREFLIGHT_OBSERVED_NS < integer(s['captured_mono_ns']) <= time.monotonic_ns()
assert integer(s['primary_calls']) >= MIN_PRIMARY_CALLS
assert integer(s['primary_period_overruns']) >= MIN_PRIMARY_OVERRUNS
assert a['active'] == 0 and a['primary_waiting'] == 0 and a['fenced'] == 0
assert a['pending_result_tokens'] == [0, 0, 0]
for key in ('admissions', 'overruns', 'completed', 'native_failures', 'not_submitted', 'disabled'):
    assert isinstance(s[key], list) and len(s[key]) == 3
    for value in s[key]:
        integer(value, maximum=1 if key == 'disabled' else 2**64-1)
assert isinstance(s['recovery'], list) and len(s['recovery']) == 2
for recovery in s['recovery']:
    assert recovery['enabled'] in (0, 1) and 0 <= recovery['phase'] <= 3 and 0 <= recovery['reason'] <= 5
    assert recovery['attempt_count'] <= 2 and recovery['history_opaque'] in (0, 1)
    assert len(recovery['attempt_times_ns']) == 2
    for key in ('faults', 'attempts', 'recoveries', 'attempt_count', 'opaque_attempt_count',
                'observed_ns', 'cooldown_until_ns', 'fault_primary_calls', 'fault_primary_overruns', 'probe_successes'):
        integer(recovery[key])
    for stamp in recovery['attempt_times_ns']:
        integer(stamp)
c = a['sface_counters']
assert set(c) == {'requests', 'execution_attempts', 'completed', 'features_returned',
                  'deferred', 'slot_denials', 'expired_after_admission'}
for value in c.values():
    integer(value)
assert c['features_returned'] <= c['completed'] <= c['execution_attempts'] <= c['requests']
assert c['completed'] >= MIN_SFACE_COMPLETED
assert set(a['inherited_optional']) == {'yunet', 'sface'}
marker = CHECKPOINT.with_name(CHECKPOINT.name + '.native-consumed-' + sha)
assert not marker.exists(), 'Checkpoint already consumed; never reuse it'
history = j['previous_kernel_history']
assert history['archive_path'] == str(ARCHIVE)
assert history['source_boot'] == '3c94e7a0-3f4d-4b66-801c-fa0a1b749bfb'
assert history['source_checkpoint_sha256'] == OLD_CHECKPOINT_SHA
archive_raw = read(ARCHIVE)
assert hashlib.sha256(archive_raw).hexdigest() == history['archive_sha256']
archive = json.loads(archive_raw)
assert archive['current_boot'] == BOOT and archive['source_checkpoint_sha256'] == OLD_CHECKPOINT_SHA
assert archive['checkpoint']['seed']['boot_id'] == history['source_boot']
assert hashlib.sha256(read(CHECKPOINT)).hexdigest() == sha, 'Checkpoint changed during validation'
assert unit('aura-camera-ui.service')['MainPID'] == '0'
print(json.dumps({'schema': 'aura-final-checkpoint-readonly-precheck-1', 'boot_id': BOOT,
    'board_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'checkpoint_path': str(CHECKPOINT), 'checkpoint_sha256': sha,
    'checkpoint_exact_bytes_base64': base64.b64encode(raw).decode('ascii'),
    'source_pid': SOURCE_PID, 'source_birth_ticks': SOURCE_BIRTH,
    'primary_calls': s['primary_calls'], 'primary_period_overruns': s['primary_period_overruns'],
    'sface_counters': c, 'previous_kernel_history': history, 'camera_unit': camera,
    'dpu_and_raw_mem_users': users,
    'original_load_business_checkpoint_validation_still_required': True,
    'stop_intent_time_must_be_crosschecked_by_main_operator': True,
    'checkpoint_sealed_by_this_probe': False, 'checkpoint_consumed': False,
    'board_mutations': False, 'device_opened': False, 'database_opened': False,
    'project_imported': False, 'motion_requested': False}, sort_keys=True))
