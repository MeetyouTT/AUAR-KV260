"""Read-only, private-content-free check of the restored original Native camera."""
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
PID, BIRTH = 79866, 2265436
CMD = 'acf3ee123d7674fdea6e90e79252909ca396249c870269169910879d940c27dd'
SHA = 'c6c8baab1de423e27740137330f8315796a7778e36735c93a0c87f2a56029471'
OPS = Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
CAMERA = Path('/home/root/aura-native-live-20261024/candidates/native-r4-metrics-fix')
ROOT = OPS / 'pan-face-edge-v5/native-operator-v1'
TX = Path('/home/root/aura-5090-recovery-20261102-903cfade/original-axis-restore-v1')

def read(path):
    path = Path(path)
    assert path.suffix.lower() not in ('.db','.sqlite','.sqlite3')
    fd = os.open(str(path), os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        meta = os.fstat(fd)
        assert stat.S_ISREG(meta.st_mode) and meta.st_size <= 2000000
        with os.fdopen(fd, 'rb', closefd=False) as stream: raw = stream.read(2000001)
        assert len(raw) <= 2000000
        return raw
    finally: os.close(fd)

def digest(value): return hashlib.sha256(value).hexdigest()
def doc(path): return json.loads(read(path))
def unit():
    p = subprocess.run(['systemctl','show','aura-camera-ui.service',
        '--property=MainPID,ActiveState,SubState,Job,Result,Restart,KillMode,SendSIGKILL,TimeoutStopUSec'],
        capture_output=True, text=True, timeout=5)
    assert p.returncode == 0
    return dict(row.split('=',1) for row in p.stdout.splitlines() if '=' in row)

def owner():
    root = Path('/proc') / str(PID)
    return {'pid':PID, 'birth_ticks':int((root/'stat').read_text().rsplit(')',1)[1].split()[19]),
            'command_sha256':digest((root/'cmdline').read_bytes())}

def sample():
    connection = http.client.HTTPConnection('127.0.0.1',8790,timeout=3)
    try:
        connection.request('GET','/health'); reply=connection.getresponse(); raw=reply.read(1048577)
        assert reply.status==200 and len(raw)<=1048576
        h=json.loads(raw)
    finally: connection.close()
    schedule, identity = h.get('dpu_schedule',{}), h.get('identity',{})
    recovery_keys=('phase','reason','faults','attempts','recoveries','enabled','history_opaque','attempt_count','probe_successes')
    optional={}
    for task in ('yunet','sface'):
        value=schedule.get('optional',{}).get(task,{})
        optional[task]={key:value.get(key) for key in ('disabled','overruns','completed','native_failures','not_submitted','admissions')}
        optional[task]['recovery']={key:value.get('recovery',{}).get(key) for key in recovery_keys}
    return {'monotonic_ns':time.monotonic_ns(),
        'camera':{key:h.get(key) for key in ('pid','board_boot_id','capture_frames','detected_frames','capture_age_ms','observation_age_ms','motion_command_emitted')},
        'camera_error_present':any(bool(h.get(k)) for k in ('camera_error','detector_error','preview_error')),
        'identity_ready':identity.get('ready'), 'identity_error_present':bool(identity.get('error')),
        'identity_shutdown_incomplete':bool(identity.get('shutdown_incomplete')),
        'native':{key:schedule.get(key) for key in ('native_critical','native_abi','owner_fenced','quiesced','primary_calls','primary_period_overruns')},
        'optional':optional,
        'sface_counters':{key:identity.get('feature_inference',{}).get(key) for key in ('requests','execution_attempts','completed','features_returned','deferred','slot_denials','expired_after_admission')}}

assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==BOOT
expected={'pid':PID,'birth_ticks':BIRTH,'command_sha256':CMD}
before=owner(); camera_unit=unit()
assert before==expected
checkpoint=CAMERA/'state/native-protection-checkpoint.json'
sealed=TX/('native-final-'+SHA+'.json')
sealed_raw=read(sealed); current_raw=read(checkpoint)
assert digest(sealed_raw)==SHA and current_raw==sealed_raw
sealed_doc=json.loads(sealed_raw)
audit_path=ROOT/('recovery-audit-'+str(PID)+'.json')
audit_raw=read(audit_path); audit=json.loads(audit_raw)
run_path=OPS/('native-run-'+BOOT+'-'+str(PID))/'config.json'
run_raw=read(run_path); run=json.loads(run_raw)
marker=Path(str(checkpoint)+'.native-consumed-'+SHA); marker_raw=read(marker)
settings=doc(ROOT/'settings.json')
samples=[sample()];time.sleep(1.1);samples.append(sample())
checks={
    'same_boot_owner_and_active_service':before==owner()==expected and camera_unit['MainPID']==str(PID) and camera_unit['ActiveState']=='active' and camera_unit['SubState']=='running' and not camera_unit['Job'],
    'original_shutdown_protections':all(camera_unit.get(k)==v for k,v in {'Restart':'no','KillMode':'process','SendSIGKILL':'no','TimeoutStopUSec':'infinity'}.items()),
    'checkpoint_and_sealed_bytes_equal_expected':digest(read(checkpoint))==SHA and read(sealed)==sealed_raw,
    'run_pin_is_actual_final_checkpoint':run['native_execution']['seed']=={'path':str(checkpoint),'sha256':SHA},
    'audit_checkpoint_pin_and_unit_match':audit['checkpoint_sha256']==SHA and audit['checkpoint_unit_sha256']==sealed_doc['source_unit_sha256'],
    'audit_exact_seed_before_operator_request_equals_sealed_seed':audit['exact_seed_before_operator_request']==sealed_doc['seed'],
    'consumed_marker_exact_original_sha_line':marker_raw==(SHA+'\n').encode(),
    'operator_request_from_other_boot_and_unchanged':settings['request_boot_id']!=BOOT and settings==audit['request'],
    'operator_artificial_counter_reset_false':audit.get('artificial_counter_reset') is False,
    'operator_mechanical_actions_zero':audit.get('mechanical_actions')==0,
    'frames_and_detections_advancing':samples[1]['camera']['capture_frames']>samples[0]['camera']['capture_frames'] and samples[1]['camera']['detected_frames']>samples[0]['camera']['detected_frames'],
    'primary_and_overrun_history_preserved':all(s['native']['primary_calls']>=sealed_doc['seed']['primary_calls'] and s['native']['primary_period_overruns']>=sealed_doc['seed']['primary_period_overruns'] for s in samples),
    'all_sface_counter_lower_bounds_preserved':all(all(type(s['sface_counters'][key]) is int and s['sface_counters'][key]>=value for key,value in sealed_doc['auxiliary']['sface_counters'].items()) for s in samples),
    'current_native_healthy_no_fence_or_quiesce':all(s['native']['native_critical'] is True and s['native']['native_abi']==2 and s['native']['owner_fenced'] is False and s['native']['quiesced'] is False for s in samples),
    'current_source_and_identity_healthy':all(s['camera']['pid']==PID and s['camera']['board_boot_id']==BOOT and s['identity_ready'] is True and not s['identity_error_present'] and not s['identity_shutdown_incomplete'] and not s['camera_error_present'] and s['camera']['motion_command_emitted'] is False for s in samples),
    'both_optional_running_and_enabled':all(all(s['optional'][task]['disabled'] is False and s['optional'][task]['recovery']['phase']=='RUNNING' and s['optional'][task]['recovery']['enabled'] is True for task in ('yunet','sface')) for s in samples),
    'audit_and_run_config_unchanged_during_probe':read(audit_path)==audit_raw and read(run_path)==run_raw,
}
print(json.dumps({'schema':'aura-camera-restore-video-readonly-audit-1','observed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'status':'PASS' if all(checks.values()) else 'HOLD','checks':checks,'camera_owner':before,'camera_service':camera_unit,
    'actual_run_config_path':str(run_path),'actual_run_config_sha256':digest(run_raw),'checkpoint_sha256':SHA,
    'audit_path':str(audit_path),'audit_sha256':digest(audit_raw),'audit_status':audit.get('status'),
    'operator_request_boot_id':settings['request_boot_id'],'audit_status_describes_operator_request_not_native_restore':True,
    'marker_path':str(marker),'marker_sha256':digest(marker_raw),'marker_bytes':len(marker_raw),
    'sealed_seed_sha256_canonical':digest(json.dumps(sealed_doc['seed'],sort_keys=True,separators=(',',':')).encode()),
    'audit_seed_sha256_canonical':digest(json.dumps(audit['exact_seed_before_operator_request'],sort_keys=True,separators=(',',':')).encode()),
    'seed_source_owner':{key:sealed_doc['seed'][key] for key in ('source_pid','source_birth_ticks')},
    'seed_counter_lower_bounds':{key:sealed_doc['seed'][key] for key in ('primary_calls','primary_period_overruns')},
    'sface_counter_lower_bounds':sealed_doc['auxiliary']['sface_counters'],
    'samples':samples,'board_mutations':False,'services_changed':False,'device_or_mmio_opened':False,'project_imported':False,'database_opened_or_copied':False},sort_keys=True))
