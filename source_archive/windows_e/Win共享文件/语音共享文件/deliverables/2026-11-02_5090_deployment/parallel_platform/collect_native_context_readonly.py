"""Read public Native provenance/counter metadata; never load project modules or a library."""
import datetime
import hashlib
import json
from pathlib import Path

BOOT = '903cfade-b93c-48fa-804e-379be1967313'
PID = 1333
OPS = Path('/home/root/aura-native-live-20261024/ops/be72669aa53de735')
AURA = Path('/home/root/aura-native-live-20261024/candidates/native-r4-metrics-fix/aura')
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip() == BOOT

def data(path):
    path = Path(path)
    assert not path.is_symlink() and path.suffix == '.json'
    raw = path.read_bytes()
    assert len(raw) <= 1000000
    return hashlib.sha256(raw).hexdigest(), json.loads(raw)

config_path = OPS / ('native-run-' + BOOT + '-' + str(PID)) / 'config.json'
config_sha, config = data(config_path)
settings_path = OPS / 'pan-face-edge-v5/native-operator-v1/settings.json'
settings_sha, settings = data(settings_path)
checkpoint_path = AURA.parent / 'state/native-protection-checkpoint.json'
checkpoint_sha, checkpoint = data(checkpoint_path)
audit_sha, audit = data(OPS / ('pan-face-edge-v5/native-operator-v1/recovery-audit-' + str(PID) + '.json'))
meta_sha, meta = data(OPS / 'meta.json')
state_sha, state = data(OPS / 'state.json')
result = {'schema': 'aura-native-public-context-readonly-1', 'boot_id': BOOT,
          'board_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'run_config': {'path': str(config_path), 'sha256': config_sha,
                         'native_execution': config['native_execution'],
                         'detector_backend': config.get('detector_backend'),
                         'identity_selection': config.get('identity')},
          'operator_settings': {'sha256': settings_sha, **{key: settings.get(key) for key in
               ('request_boot_id', 'unit_sha256', 'predecessor_unit_sha256', 'library_sha256', 'old_library_sha256')}},
          'existing_checkpoint': {'path': str(checkpoint_path), 'sha256': checkpoint_sha,
              'schema': checkpoint.get('schema'), 'scope': checkpoint.get('scope'),
              'source_unit_sha256': checkpoint.get('source_unit_sha256'), 'seed': checkpoint.get('seed'),
              'auxiliary': checkpoint.get('auxiliary'), 'previous_kernel_history': checkpoint.get('previous_kernel_history'),
              'current_camera_still_alive': Path('/proc/1333').exists(),
              'not_final_checkpoint_for_current_camera': True},
          'current_recovery_audit': {'sha256': audit_sha, 'status': audit.get('status'),
              'checkpoint_sha256': audit.get('checkpoint_sha256'),
              'checkpoint_unit_sha256': audit.get('checkpoint_unit_sha256'),
              'exact_seed_before_operator_request': audit.get('exact_seed_before_operator_request')},
          'ops_meta': {'sha256': meta_sha, 'source_boot': meta.get('source_boot'),
                       'candidate_root': meta.get('candidate_root'), 'candidate_config': meta.get('candidate_config')},
          'ops_state': {'sha256': state_sha, 'phase': state.get('phase'), 'updated_boot': state.get('updated_boot')},
          'dfx_daemon_sha256': hashlib.sha256(Path('/usr/local/lib/kv260-dfx-state-repair-20261003/dfx-mgrd').read_bytes()).hexdigest(),
          'board_mutations': False, 'device_opened': False, 'database_opened': False,
          'project_imported': False, 'motion_requested': False}
print(json.dumps(result, sort_keys=True))
