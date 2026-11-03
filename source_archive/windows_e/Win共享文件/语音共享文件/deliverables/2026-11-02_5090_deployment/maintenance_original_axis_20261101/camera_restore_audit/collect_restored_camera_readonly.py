"""Read the original camera's actual same-boot recovery evidence, no project import."""
import ast
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
PID = 79866
BIRTH = 2265436
COMMAND = 'acf3ee123d7674fdea6e90e79252909ca396249c870269169910879d940c27dd'
OPS = Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
AURA = Path('/home/root/aura-native-live-20261024/candidates/native-r4-metrics-fix/aura')
TX = Path('/home/root/aura-5090-recovery-20261102-903cfade/original-axis-restore-v1')
CP_SHA = 'c6c8baab1de423e27740137330f8315796a7778e36735c93a0c87f2a56029471'
CP = AURA.parent / 'state/native-protection-checkpoint.json'
RUN = OPS / ('native-run-' + BOOT + '-' + str(PID)) / 'config.json'
RUN_SHA = 'c8df0795664d21d52eab3a4f1cf55e0d1a721577d547c512e83ee1931d80871d'
OP_ROOT = OPS / 'pan-face-edge-v5/native-operator-v1'

def raw(path, limit=64000000):
    path = Path(path)
    assert path.suffix.lower() not in ('.db', '.sqlite', '.sqlite3')
    assert path.resolve() == path and not path.is_symlink()
    fd = os.open(str(path), os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        st = os.fstat(fd)
        assert stat.S_ISREG(st.st_mode) and st.st_size <= limit
        with os.fdopen(fd, 'rb', closefd=False) as handle:
            value = handle.read(limit + 1)
        assert len(value) <= limit
        return value
    finally:
        os.close(fd)

def sha(path): return hashlib.sha256(raw(path)).hexdigest()
def doc(path): return json.loads(raw(path, 2000000))

def unit(name):
    p = subprocess.run(['systemctl', 'show', name,
        '--property=MainPID,ActiveState,SubState,Job,Restart,KillMode,SendSIGKILL,TimeoutStopUSec,Result,ExecMainStatus,ExecMainStartTimestampMonotonic'],
        capture_output=True, text=True, timeout=5)
    assert p.returncode == 0
    return dict(line.split('=', 1) for line in p.stdout.splitlines() if '=' in line)

def owner(pid):
    p = Path('/proc') / str(pid)
    return {'pid': pid, 'birth_ticks': int((p/'stat').read_text().rsplit(')', 1)[1].split()[19]),
            'command_sha256': hashlib.sha256((p/'cmdline').read_bytes()).hexdigest()}

def sample():
    connection = http.client.HTTPConnection('127.0.0.1', 8790, timeout=3)
    try:
        connection.request('GET', '/health')
        response = connection.getresponse()
        body = response.read(1048577)
        assert response.status == 200 and len(body) <= 1048576
        health = json.loads(body)
    finally:
        connection.close()
    schedule = health.get('dpu_schedule', {})
    identity = health.get('identity', {})
    target = identity.get('face_targets', {})
    feature = identity.get('feature_inference', {})
    values = {key: health.get(key) for key in ('pid', 'board_boot_id', 'service_epoch',
        'camera_epoch', 'capture_frames', 'detected_frames', 'capture_age_ms', 'observation_age_ms',
        'camera_error', 'detector_error', 'preview_error', 'motion_command_emitted')}
    values.update(monotonic_ns=time.monotonic_ns(), identity_ready=identity.get('ready'),
        identity_error=bool(identity.get('error')), identity_shutdown_incomplete=bool(identity.get('shutdown_incomplete')),
        face_processed=target.get('processed'), sface_completed=feature.get('completed'))
    values['native'] = {key: schedule.get(key) for key in ('native_critical', 'native_abi',
        'owner_fenced', 'quiesced', 'primary_calls', 'primary_period_overruns', 'native_execution_backend',
        'protection_handoff', 'seed_loaded', 'source_manifest_sha256', 'source_unit_sha256') if key in schedule}
    values['optional'] = {task: {key: schedule.get('optional', {}).get(task, {}).get(key) for key in
        ('disabled', 'overruns', 'completed', 'native_failures', 'not_submitted', 'admissions', 'recovery')}
        for task in ('yunet', 'sface')}
    values['sface_counters'] = {key: feature.get(key) for key in ('requests', 'execution_attempts',
        'completed', 'features_returned', 'deferred', 'slot_denials', 'expired_after_admission')}
    values['public_frame_metadata'] = {key: health[key] for key in ('width', 'height', 'frame_width',
        'frame_height', 'capture_width', 'capture_height', 'frame_shape', 'capture_shape', 'frame_size')
        if key in health and (type(health[key]) is int or
            (isinstance(health[key], list) and len(health[key]) <= 3 and all(type(v) is int for v in health[key])))}
    values['schedule_public_keys'] = sorted(schedule)
    return values

def inventory():
    dpu, motion, incomplete = [], [], []
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit(): continue
        try:
            mapped = (proc/'maps').read_text()
            handles = []
            for fd in (proc/'fd').iterdir():
                try: handles.append(os.readlink(fd))
                except FileNotFoundError: continue
            if any(value in mapped for value in ('libvart', 'libaura_native_operator')) or any(
                    target.startswith(('/dev/dri/renderD', '/dev/dpu')) for target in handles):
                dpu.append(owner(int(proc.name)))
            if 'libvsrv.so' in mapped or '/dev/mem' in handles:
                motion.append(owner(int(proc.name)))
        except (FileNotFoundError, ProcessLookupError):
            if proc.exists(): incomplete.append(int(proc.name))
        except (PermissionError, OSError):
            if proc.exists(): incomplete.append(int(proc.name))
    return {'dpu': sorted(dpu, key=lambda item:item['pid']),
            'motion_or_raw_mem': sorted(motion, key=lambda item:item['pid']),
            'unreadable_alive_processes': sorted(set(incomplete))}

assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == BOOT
camera = unit('aura-camera-ui.service')
actual = owner(PID)
assert actual == {'pid':PID, 'birth_ticks':BIRTH, 'command_sha256':COMMAND}
assert camera['MainPID'] == str(PID) and camera['ActiveState'] == 'active' and not camera['Job']
assert sha(RUN) == RUN_SHA
run = doc(RUN)
native = run['native_execution']
sealed_path = TX / ('native-final-' + CP_SHA + '.json')
sealed_raw = raw(sealed_path)
assert hashlib.sha256(sealed_raw).hexdigest() == CP_SHA
assert raw(CP) == sealed_raw
sealed = json.loads(sealed_raw)
audit_path = OP_ROOT / ('recovery-audit-' + str(PID) + '.json')
audit_raw = raw(audit_path)
audit = json.loads(audit_raw)
marker = Path(str(CP) + '.native-consumed-' + CP_SHA)
marker_raw = raw(marker)
marker_stat = marker.stat()
assert marker_raw == (CP_SHA + '\n').encode()

manifest_path = AURA.parent / 'camera-python-manifest.json'
assert sha(manifest_path) == '5e08f7cf587d74334ef24104ea01f79701629b48f2004fb772ce3f8ea82afd0d'
manifest = doc(manifest_path)
native_files = {str(path.relative_to(AURA)):sha(path) for path in AURA.rglob('*.py') if not path.is_symlink()}
operator_manifest = OP_ROOT / 'runtime-manifest.json'
assert sha(operator_manifest) == '74e011db30a9d943a9512f7648190ac0c01060af06df1280d1e8ea006dc882ad'
operator_files = doc(operator_manifest)['files']
operator_actual = {path:sha(path) for path in operator_files}
settings = doc(OP_ROOT/'settings.json')
worker_guard_source = None
for path in operator_files:
    if not path.endswith('.py'): continue
    text = raw(path).decode('utf-8')
    if 'class RecoveryWorker' not in text: continue
    tree = ast.parse(text)
    klass = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name=='RecoveryWorker')
    function = next(node for node in klass.body if isinstance(node, ast.FunctionDef) and node.name=='work')
    worker_guard_source = '\n'.join(text.splitlines()[function.lineno-1:function.lineno+8])

samples = [sample()]
time.sleep(1.1)
samples.append(sample())
owners = inventory()
unit_after = unit('aura-camera-ui.service')
checks = {
    'actual_camera_owner_unchanged': owner(PID) == actual and unit_after['MainPID'] == str(PID),
    'original_shutdown_protections': all(camera.get(k)==v for k,v in {
        'Restart':'no','KillMode':'process','SendSIGKILL':'no','TimeoutStopUSec':'infinity'}.items()),
    'native_python_closure_exact': native_files == manifest['files'] and len(native_files)==222,
    'operator_closure_exact': operator_actual == operator_files and len(operator_files)==7,
    'run_pin_is_actual_final': native['seed']=={'path':str(CP),'sha256':CP_SHA},
    'audit_exact_seed_equals_sealed_final_seed': audit['exact_seed_before_operator_request']==sealed['seed'],
    'audit_checkpoint_pin_and_unit_match': audit['checkpoint_sha256']==CP_SHA and audit['checkpoint_unit_sha256']==sealed['source_unit_sha256'],
    'checkpoint_original_and_seal_unchanged': sha(CP)==CP_SHA and raw(sealed_path)==sealed_raw,
    'marker_exact_original_sha_line': marker_raw == (CP_SHA+'\n').encode(),
    'operator_request_is_from_other_boot': settings['request_boot_id'] != BOOT,
    'operator_request_unchanged_from_audit': audit.get('request') == settings,
    'operator_did_not_reset_counters': audit.get('artificial_counter_reset') is False,
    'operator_no_mechanical_actions': audit.get('mechanical_actions') == 0,
    'sole_dpu_owner_is_restored_camera': owners['dpu']==[actual],
    'no_motion_or_raw_memory_owner': not owners['motion_or_raw_mem'],
    'complete_owner_inventory': not owners['unreadable_alive_processes'],
    'source_capture_and_detection_progress': samples[-1]['capture_frames'] > samples[0]['capture_frames'] and samples[-1]['detected_frames'] > samples[0]['detected_frames'],
    'yunet_natural_source_progress': samples[-1]['face_processed'] > samples[0]['face_processed'],
    'sface_completed_not_reset': all(item['sface_completed'] >= sealed['auxiliary']['sface_counters']['completed'] for item in samples),
    'primary_history_not_reset': all(item['native']['primary_calls'] >= sealed['seed']['primary_calls'] and item['native']['primary_period_overruns'] >= sealed['seed']['primary_period_overruns'] for item in samples),
    'healthy_native_and_identity': all(item['pid']==PID and item['board_boot_id']==BOOT and
        item['identity_ready'] is True and not item['identity_error'] and not item['identity_shutdown_incomplete'] and
        item['native'].get('native_critical') is True and item['native'].get('native_abi') == 2 and
        item['native'].get('owner_fenced') is False and item['native'].get('quiesced') is False and
        item['camera_error']=='' and item['detector_error']=='' and item['preview_error']=='' and
        item['motion_command_emitted'] is False for item in samples),
}
assert raw(audit_path)==audit_raw and sha(RUN)==RUN_SHA
print(json.dumps({'schema':'aura-restored-camera-readonly-audit-1',
    'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(), 'boot_id':BOOT,
    'status':'PASS' if all(checks.values()) else 'HOLD_REVIEW_REQUIRED', 'checks':checks,
    'camera_owner':actual, 'camera_service':camera, 'camera_service_after':unit_after,
    'run_config_path':str(RUN), 'run_config_sha256':RUN_SHA,
    'restored_final_checkpoint_sha256':CP_SHA, 'checkpoint_source_owner':{
        'pid':sealed['seed']['source_pid'],'birth_ticks':sealed['seed']['source_birth_ticks']},
    'audit_path':str(audit_path),'audit_sha256':hashlib.sha256(audit_raw).hexdigest(),
    'audit_status':audit.get('status'),'audit_status_is_operator_request_state_not_native_restore_result':True,
    'operator_request_boot_id':settings['request_boot_id'],'operator_worker_guard_source':worker_guard_source,
    'marker_path':str(marker), 'marker_sha256':hashlib.sha256(marker_raw).hexdigest(),
    'marker_bytes':len(marker_raw), 'marker_mtime_ns':marker_stat.st_mtime_ns,
    'native_python_files_verified':len(native_files),'operator_files_verified':len(operator_files),
    'samples':samples, 'owners':owners,
    'board_mutations':False,'project_imported':False,'native_context_or_library_called':False,
    'device_opened':False,'database_opened':False,'motion_requested':False},sort_keys=True))
